"""M1 developer experiment. No downloads, state reset, TCG or requirement bypass."""

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET


GIB = 1024 ** 3
ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(Path.home()), "LANG": "en_US.UTF-8"}


def run(args):
    return subprocess.check_output([str(a) for a in args], env=ENV, text=True).strip()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_tree(root):
    """Inspect PE architecture and bounded, uncompressed WIM XML, not filenames."""
    root = Path(root)
    with (root / "efi/boot/bootaa64.efi").open("rb") as stream:
        header = stream.read(64)
        require(header[:2] == b"MZ" and len(header) == 64, "Invalid EFI DOS header")
        offset = struct.unpack_from("<I", header, 60)[0]
        stream.seek(offset)
        pe = stream.read(6)
    require(pe == b"PE\0\0\x64\xaa", "EFI bootloader is not ARM64 PE")
    with (root / "sources/install.wim").open("rb") as stream:
        header = stream.read(208)
        require(len(header) == 208 and header[:8] == b"MSWIM\0\0\0", "Invalid WIM header")
        size_flags, offset, original = struct.unpack_from("<QQQ", header, 72)
        size = size_flags & ((1 << 56) - 1)
        require(not (size_flags >> 56) & 4 and 0 < size == original <= 1024 * 1024,
                "Unsupported/compressed WIM XML resource")
        require(offset + size <= os.fstat(stream.fileno()).st_size, "Truncated WIM XML")
        stream.seek(offset)
        xml = stream.read(size).decode("utf-16")
    require("<!DOCTYPE" not in xml.upper() and "<!ENTITY" not in xml.upper(), "Unsafe WIM XML")
    images = []
    for image in ET.fromstring(xml).findall("IMAGE"):
        windows = image.find("WINDOWS")
        require(windows is not None and windows.findtext("ARCH") == "12", "Non-ARM64 Windows image")
        images.append({"index": image.attrib["INDEX"], "edition": windows.findtext("EDITIONID"),
                       "language": windows.findtext("LANGUAGES/DEFAULT"),
                       "build": windows.findtext("VERSION/BUILD"),
                       "revision": windows.findtext("VERSION/SPBUILD")})
    require(any(i["edition"] == "Professional" for i in images), "Windows Pro image missing")
    return {"efi_machine": "AA64", "images": images}


def inspect_iso(path):
    require(platform.system() == "Darwin", "ISO inspection requires macOS hdiutil")
    path = Path(path).resolve(strict=True)
    # A private mount point makes detach apply only to our attachment, not another VM's mount.
    with tempfile.TemporaryDirectory(prefix="tw-media-") as mount:
        result = subprocess.check_output(
            ["/usr/bin/hdiutil", "attach", "-readonly", "-nobrowse", "-plist",
             "-mountpoint", mount, str(path)], env=ENV)
        entities = plistlib.loads(result)["system-entities"]
        device = entities[0]["dev-entry"]
        try:
            return {"bytes": path.stat().st_size, "sha256": digest(path), **inspect_tree(mount)}
        finally:
            run(["/usr/bin/hdiutil", "detach", device])


def host_check(location):
    result = {"system": platform.system(), "architecture": platform.machine(),
              "free_bytes": shutil.disk_usage(location).free, "required_free_bytes": 160 * GIB}
    errors = []
    if result["system"] != "Darwin" or result["architecture"] != "arm64":
        errors.append("A physical Apple Silicon Mac is required")
    else:
        for key, name in (("hv_support", "kern.hv_support"), ("ram_bytes", "hw.memsize"),
                          ("model", "hw.model"), ("chip", "machdep.cpu.brand_string")):
            result[key] = run(["/usr/sbin/sysctl", "-n", name])
        result["macos"] = run(["/usr/bin/sw_vers"])
        if result["hv_support"] != "1":
            errors.append("Hypervisor support unavailable; TCG is forbidden")
        if int(result["ram_bytes"]) < 16 * GIB:
            errors.append("At least 16 GiB host RAM required")
        if int(platform.mac_ver()[0].split(".")[0]) < 14:
            errors.append("Candidate host floor is macOS 14")
    if result["free_bytes"] < 160 * GIB:
        errors.append("At least 160 GiB free on the VM volume required by B1")
    result["errors"] = errors
    return result


def load_inputs(path):
    manifest = json.loads(Path(path).read_text())
    require(manifest["schema"] == 1, "Unsupported input schema")
    require(manifest["windows_use_confirmed"] is True, "Confirm permitted Windows use first")
    require(re.fullmatch(r"virt-\d+\.\d+", manifest["machine"]), "Pin a versioned virt machine")
    require(manifest["secure_boot_keys_reviewed"] is True, "Review firmware keys before B2")
    require(manifest["firmware_flash_bytes"] == 64 * 1024 * 1024, "Candidate requires 64 MiB flash banks")
    for name in ("iso", "qemu", "qemu_img", "swtpm", "firmware_code", "firmware_vars"):
        entry = manifest[name]
        require(Path(entry["path"]).is_absolute(), f"{name}: use an absolute path")
        require(re.fullmatch(r"[0-9a-f]{64}", entry["sha256"] or ""), f"{name}: SHA-256 required")
        require(entry["source"] and entry["revision"] and entry["license"], f"{name}: provenance required")
        require(digest(entry["path"]) == entry["sha256"], f"{name}: hash mismatch")
    require(manifest["iso"]["publisher_hash_source"].startswith("https://www.microsoft.com/"),
            "Record Microsoft's exact ISO checksum source; a local hash is not provenance")
    for name in ("firmware_code", "firmware_vars"):
        require(Path(manifest[name]["path"]).stat().st_size == manifest["firmware_flash_bytes"],
                f"{name}: flash size mismatch")
    return manifest


def preflight(manifest_path, location):
    host = host_check(location)
    require(not host["errors"], "; ".join(host["errors"]))
    manifest = load_inputs(manifest_path)
    qemu = manifest["qemu"]["path"]
    require("hvf" in run([qemu, "-accel", "help"]).split(), "QEMU lacks HVF")
    require(manifest["machine"] in run([qemu, "-machine", "help"]).split(), "Machine unavailable")
    devices = run([qemu, "-device", "help"])
    for name in ("nvme", "ramfb", "qemu-xhci", "usb-kbd", "usb-tablet", "usb-storage",
                 "tpm-tis-device", "virtio-net-pci"):
        require(f'"{name}"' in devices, f"QEMU lacks {name}")
    require("cocoa" in run([qemu, "-display", "help"]).split(), "Cocoa console unavailable")
    require("--tpm2" in run([manifest["swtpm"]["path"], "socket", "--help"]), "swtpm lacks TPM2")
    media = inspect_iso(manifest["iso"]["path"])
    require(media["sha256"] == manifest["iso"]["sha256"], "ISO changed during preflight")
    return manifest


def create(manifest_path, package):
    package = Path(package).absolute()
    require("," not in str(package), "swtpm state paths cannot contain commas")
    require(not package.exists() and not package.is_symlink(), "Refusing to replace existing VM data")
    manifest = preflight(manifest_path, package.parent)
    # No deletion or retry on partial failure: the operator must review that directory.
    package.mkdir(mode=0o700)
    (package / "tpm").mkdir(mode=0o700)
    shutil.copyfile(manifest["firmware_vars"]["path"], package / "uefi-vars.fd")
    os.chmod(package / "uefi-vars.fd", 0o600)
    run([manifest["qemu_img"]["path"], "create", "-f", "qcow2", package / "disk.qcow2", "128G"])
    os.chmod(package / "disk.qcow2", 0o600)
    identity = uuid.uuid4()
    mac = "52:54:00:" + ":".join(f"{b:02x}" for b in identity.bytes[-3:])
    config = {"schema": 1, "uuid": str(identity), "mac": mac, "inputs": manifest}
    with (package / "config.json").open("x") as stream:
        json.dump(config, stream, indent=2)
        stream.write("\n")
    os.chmod(package / "config.json", 0o600)
    print(f"Created {package}; preserve the entire package, not just the disk")


def qemu_args(config, package, runtime, installer):
    m = config["inputs"]
    args = [m["qemu"]["path"], "-name", "Try Win11 M1", "-uuid", config["uuid"],
            "-machine", m["machine"] + ",gic-version=3", "-accel", "hvf", "-cpu", "host",
            "-smp", "4", "-m", "8192", "-nodefaults", "-display", "cocoa", "-device", "ramfb",
            "-blockdev", json.dumps({"driver": "file", "filename": m["firmware_code"]["path"],
                                     "node-name": "code", "read-only": True}),
            "-blockdev", json.dumps({"driver": "file", "filename": str(package / "uefi-vars.fd"),
                                     "node-name": "vars"}),
            "-machine", "pflash0=code,pflash1=vars",
            "-blockdev", json.dumps({"driver": "qcow2", "node-name": "disk", "file": {
                "driver": "file", "filename": str(package / "disk.qcow2")}, "backing": None}),
            "-device", "nvme,drive=disk,serial=TW" + uuid.UUID(config["uuid"]).hex[:16],
            "-device", "qemu-xhci,id=usb", "-device", "usb-kbd,bus=usb.0",
            "-device", "usb-tablet,bus=usb.0", "-netdev", "user,id=nat",
            "-device", "virtio-net-pci,netdev=nat,mac=" + config["mac"],
            "-chardev", "socket,id=tpm,path=" + str(runtime / "tpm.sock"),
            "-tpmdev", "emulator,id=tpm,chardev=tpm", "-device", "tpm-tis-device,tpmdev=tpm",
            "-qmp", "unix:" + str(runtime / "qmp.sock") + ",server=on,wait=off"]
    if installer:
        args += ["-blockdev", json.dumps({"driver": "raw", "node-name": "iso", "read-only": True,
                 "file": {"driver": "file", "filename": m["iso"]["path"]}}),
                 "-device", "usb-storage,bus=usb.0,drive=iso,removable=on,bootindex=1"]
    return args


@contextlib.contextmanager
def package_lock(identity):
    root = Path("/tmp") / f"try-win11-{os.getuid()}"
    root.mkdir(mode=0o700, exist_ok=True)
    require(not root.is_symlink() and root.stat().st_uid == os.getuid()
            and root.stat().st_mode & 0o777 == 0o700, "Unsafe runtime directory")
    runtime = root / str(uuid.UUID(identity))
    runtime.mkdir(mode=0o700, exist_ok=True)
    require(not runtime.is_symlink() and runtime.stat().st_mode & 0o777 == 0o700,
            "Unsafe VM runtime directory")
    with (runtime / "lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("VM already owned; do not start another writer") from None
        yield runtime, lock.fileno()


def powerdown(runtime):
    """ACPI request only. Never QMP quit, kill, or a TPM/UEFI reset."""
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(3)
        client.connect(str(runtime / "qmp.sock"))
        with client.makefile("rwb", buffering=0) as stream:
            require("QMP" in json.loads(stream.readline()), "Missing QMP greeting")
            for command in ("qmp_capabilities", "system_powerdown"):
                stream.write((json.dumps({"execute": command, "id": command}) + "\n").encode())
                while True:
                    response = json.loads(stream.readline())
                    if response.get("id") == command:
                        require("return" in response, f"QMP rejected {command}: {response}")
                        break


def launch(package, installer):
    package = Path(package).resolve(strict=True)
    require("," not in str(package), "swtpm state paths cannot contain commas")
    config = json.loads((package / "config.json").read_text())
    require(config["schema"] == 1, "Unsupported VM schema")
    with package_lock(config["uuid"]) as (runtime, lock_fd):
        require(not (runtime / "active").exists(),
                "Previous run not closed; inspect both processes before manual recovery")
        # The package is local output only; arbitrary imported state is not supported.
        for name in ("disk.qcow2", "uefi-vars.fd", "tpm"):
            require((package / name).exists() and not (package / name).is_symlink(), f"Missing/linked {name}; no reset")
        require(any((package / "tpm").iterdir()) or not (package / "started").exists(),
                "TPM state missing after first start; restore the whole VM")
        with tempfile.TemporaryDirectory(prefix="tw-inputs-") as temporary:
            manifest_path = Path(temporary) / "inputs.json"
            manifest_path.write_text(json.dumps(config["inputs"]))
            m = preflight(manifest_path, package)
        require((package / "uefi-vars.fd").stat().st_size == m["firmware_flash_bytes"], "Invalid UEFI state")
        for name in ("qmp.sock", "tpm.sock"):
            require(not (runtime / name).exists(), "Stale socket; inspect surviving processes before recovery")
        args = qemu_args(config, package, runtime, installer)
        print(json.dumps({"qemu_argv": args}, indent=2), flush=True)
        # The crash marker also blocks restart if a child closes inherited descriptors.
        with (runtime / "active").open("x") as marker:
            marker.write(str(package) + "\n")
        with (package / "swtpm.log").open("a") as log:
            tpm = subprocess.Popen([m["swtpm"]["path"], "socket", "--tpm2", "--tpmstate",
                                    "dir=" + str(package / "tpm"), "--ctrl",
                                    "type=unixio,path=" + str(runtime / "tpm.sock"),
                                    "--flags", "not-need-init,startup-clear"], env=ENV,
                                   stdout=log, stderr=log, pass_fds=(lock_fd,), start_new_session=True)
            qemu = None
            previous = {}
            try:
                deadline = time.monotonic() + 10
                while not (runtime / "tpm.sock").exists():
                    require(tpm.poll() is None, "swtpm exited; inspect swtpm.log")
                    require(time.monotonic() < deadline, "swtpm readiness timeout")
                    time.sleep(0.1)
                (package / "started").touch(mode=0o600, exist_ok=True)

                def shutdown(signum, frame):
                    try:
                        powerdown(runtime)
                        print("Shutdown requested; waiting for guest. No forced stop.", flush=True)
                    except (OSError, ValueError) as error:
                        print(f"Shutdown not confirmed: {error}; use the guest console", file=sys.stderr)

                for sig in (signal.SIGINT, signal.SIGTERM):
                    previous[sig] = signal.signal(sig, shutdown)
                with (package / "qemu.log").open("a") as qemu_log:
                    qemu = subprocess.Popen(args, env=ENV, stderr=qemu_log, pass_fds=(lock_fd,),
                                            start_new_session=True)
                    warned = False
                    while qemu.poll() is None:
                        if tpm.poll() is not None and not warned:
                            print("TPM exited: shut down in the guest console; do not restart/reset TPM",
                                  file=sys.stderr, flush=True)
                            warned = True
                        time.sleep(0.2)
                    code = qemu.returncode
                require(code == 0, f"QEMU exited {code}; inspect qemu.log; state retained")
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
                # Do not terminate TPM while a guest might still be writing.
                if qemu is None or qemu.poll() is not None:
                    if tpm.poll() is None:
                        tpm.terminate()
                    tpm.wait()
                    for name in ("qmp.sock", "tpm.sock"):
                        (runtime / name).unlink(missing_ok=True)
                    (runtime / "active").unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("host").add_argument("location", type=Path)
    sub.add_parser("inspect-iso").add_argument("iso", type=Path)
    check = sub.add_parser("preflight")
    check.add_argument("manifest", type=Path)
    check.add_argument("location", type=Path)
    init = sub.add_parser("create")
    init.add_argument("manifest", type=Path)
    init.add_argument("package", type=Path)
    start = sub.add_parser("launch")
    start.add_argument("package", type=Path)
    start.add_argument("--installer", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == "host":
            report = host_check(args.location)
            print(json.dumps(report, indent=2))
            return bool(report["errors"])
        if args.command == "inspect-iso":
            print(json.dumps(inspect_iso(args.iso), indent=2))
        elif args.command == "preflight":
            preflight(args.manifest, args.location)
            print("Preflight passed; this is not a Windows boot or Secure Boot pass")
        elif args.command == "create":
            create(args.manifest, args.package)
        elif args.command == "launch":
            launch(args.package, args.installer)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError, ET.ParseError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
