"""Developer-recipe contract tests. These do not simulate a Windows boot."""

import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import boot


class BootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def media(self, machine=0xAA64, arch="12", compressed=False):
        (self.root / "efi/boot").mkdir(parents=True, exist_ok=True)
        (self.root / "sources").mkdir(exist_ok=True)
        pe = bytearray(134)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 60, 128)
        pe[128:132] = b"PE\0\0"
        struct.pack_into("<H", pe, 132, machine)
        (self.root / "efi/boot/bootaa64.efi").write_bytes(pe)
        xml = (f'<WIM><IMAGE INDEX="3"><WINDOWS><ARCH>{arch}</ARCH>'
               '<EDITIONID>Professional</EDITIONID><LANGUAGES><DEFAULT>en-US</DEFAULT></LANGUAGES>'
               '<VERSION><BUILD>26100</BUILD><SPBUILD>4349</SPBUILD></VERSION>'
               '</WINDOWS></IMAGE></WIM>').encode("utf-16")
        header = bytearray(208)
        header[:8] = b"MSWIM\0\0\0"
        struct.pack_into("<QQQ", header, 72, len(xml) | ((4 if compressed else 2) << 56), 208, len(xml))
        (self.root / "sources/install.wim").write_bytes(header + xml)

    def test_media_metadata_and_architecture_rejection(self):
        self.media()
        self.assertEqual(boot.inspect_tree(self.root)["images"], [{
            "index": "3", "edition": "Professional", "language": "en-US",
            "build": "26100", "revision": "4349"}])
        for machine, arch in ((0x8664, "12"), (0xAA64, "9")):
            self.media(machine, arch)
            with self.assertRaisesRegex(ValueError, "ARM64"):
                boot.inspect_tree(self.root)

    def test_compressed_or_truncated_wim_rejected(self):
        self.media(compressed=True)
        with self.assertRaisesRegex(ValueError, "compressed"):
            boot.inspect_tree(self.root)
        self.media()
        path = self.root / "sources/install.wim"
        path.write_bytes(path.read_bytes()[:-2])
        with self.assertRaisesRegex(ValueError, "Truncated"):
            boot.inspect_tree(self.root)

    def test_free_space_boundary(self):
        for free, blocked in ((160 * boot.GIB - 1, True), (160 * boot.GIB, False)):
            with patch.object(boot.shutil, "disk_usage", return_value=type("Usage", (), {"free": free})()), \
                 patch.object(boot.platform, "system", return_value="Linux"):
                errors = boot.host_check(self.root)["errors"]
            self.assertEqual(any("160 GiB" in error for error in errors), blocked)

    def test_existing_package_is_never_replaced(self):
        sentinel = self.root / "disk.qcow2"
        sentinel.write_bytes(b"keep my existing VM")
        with self.assertRaisesRegex(ValueError, "replace"):
            boot.create(self.root / "absent.json", self.root)
        self.assertEqual(sentinel.read_bytes(), b"keep my existing VM")

    def test_failed_preflight_creates_nothing(self):
        target = self.root / "new.trywin11"
        with patch.object(boot, "host_check", return_value={"errors": ["160 GiB required"]}):
            with self.assertRaisesRegex(ValueError, "160 GiB"):
                boot.create(self.root / "absent.json", target)
        self.assertFalse(target.exists())

    def test_input_hash_mismatch_rejected(self):
        example = Path(__file__).resolve().parents[1] / "config/inputs.example.json"
        m = json.loads(example.read_text())
        m.update(windows_use_confirmed=True, secure_boot_keys_reviewed=True, machine="virt-10.1")
        media = self.root / "media.iso"
        media.write_bytes(b"not the approved input")
        m["iso"].update(path=str(media), sha256="0" * 64, revision="26100.4349")
        manifest = self.root / "inputs.json"
        manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "iso: hash mismatch"):
            boot.load_inputs(manifest)

    def test_argument_paths_are_not_shell_or_comma_options(self):
        path = self.root / 'VM, space 雪 $(touch nope)'
        config = {"uuid": str(uuid.uuid4()), "mac": "52:54:00:01:23:45", "inputs": {
            "qemu": {"path": "/runtime/qemu"}, "machine": "virt-10.1",
            "firmware_code": {"path": '/firmware/code, "snow".fd'},
            "iso": {"path": str(path / "media.iso")}}}
        args = boot.qemu_args(config, path, Path("/tmp/tw"), True)
        blocks = [json.loads(args[i + 1]) for i, arg in enumerate(args) if arg == "-blockdev"]
        self.assertEqual(blocks[0]["filename"], config["inputs"]["firmware_code"]["path"])
        self.assertTrue(blocks[0]["read-only"])
        self.assertEqual(blocks[2]["file"]["filename"], str(path / "disk.qcow2"))
        self.assertIsNone(blocks[2]["backing"])
        self.assertEqual(blocks[3]["file"]["filename"], str(path / "media.iso"))
        self.assertEqual(args[args.index("-accel") + 1], "hvf")
        self.assertFalse(any("hostfwd" in arg or "tcg" in arg for arg in args))
        cold = boot.qemu_args(config, path, Path("/tmp/tw"), False)
        self.assertNotIn("iso", [json.loads(cold[i + 1])["node-name"]
                                for i, arg in enumerate(cold) if arg == "-blockdev"])

    def test_lock_survives_parent_release_while_child_owns_it(self):
        identity = str(uuid.uuid4())
        with boot.package_lock(identity) as (runtime, fd):
            child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                                     stdin=subprocess.PIPE, pass_fds=(fd,))
        try:
            with self.assertRaisesRegex(ValueError, "already owned"):
                with boot.package_lock(identity):
                    self.fail("second writer accepted")
        finally:
            child.communicate()
        with boot.package_lock(identity):
            pass
        (runtime / "lock").unlink()
        runtime.rmdir()

    def test_crash_marker_blocks_restart_without_mutating_package(self):
        identity = str(uuid.uuid4())
        (self.root / "config.json").write_text(json.dumps({"schema": 1, "uuid": identity}))
        with boot.package_lock(identity) as (runtime, _):
            (runtime / "active").write_text("prior run")
        with self.assertRaisesRegex(ValueError, "Previous run not closed"):
            boot.launch(self.root, False)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["config.json"])
        self.assertEqual((runtime / "active").read_text(), "prior run")
        (runtime / "active").unlink()
        (runtime / "lock").unlink()
        runtime.rmdir()

    def test_missing_tpm_is_not_recreated(self):
        (self.root / "tpm").mkdir()
        (self.root / "started").touch()
        (self.root / "disk.qcow2").write_bytes(b"disk")
        (self.root / "uefi-vars.fd").write_bytes(b"variables")
        identity = str(uuid.uuid4())
        (self.root / "config.json").write_text(json.dumps({"schema": 1, "uuid": identity}))
        with self.assertRaisesRegex(ValueError, "TPM state missing"):
            boot.launch(self.root, False)
        self.assertEqual((self.root / "uefi-vars.fd").read_bytes(), b"variables")
        self.assertEqual(list((self.root / "tpm").iterdir()), [])
        runtime = Path("/tmp") / f"try-win11-{os.getuid()}" / identity
        (runtime / "lock").unlink()
        runtime.rmdir()

    def test_qmp_shutdown_handles_events_and_errors(self):
        # A real local socket checks framing/handshake without a hypervisor.
        runtime = Path(tempfile.mkdtemp(prefix="tw-qmp-", dir="/tmp"))
        self.addCleanup(runtime.rmdir)
        for rejected in (False, True):
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(runtime / "qmp.sock"))
            server.listen(1)
            received = []

            def respond():
                with server.accept()[0] as connection, connection.makefile("rwb", buffering=0) as stream:
                    stream.write(b'{"QMP": {}}\r\n')
                    for _ in range(2):
                        request = json.loads(stream.readline())
                        received.append(request["execute"])
                        stream.write(b'{"event": "unrelated"}\r\n')
                        result = {"id": request["id"], "error" if rejected else "return": {}}
                        stream.write((json.dumps(result) + "\r\n").encode())
                        if rejected:
                            break

            thread = threading.Thread(target=respond)
            thread.start()
            try:
                if rejected:
                    with self.assertRaisesRegex(ValueError, "QMP rejected"):
                        boot.powerdown(runtime)
                else:
                    boot.powerdown(runtime)
                    self.assertEqual(received, ["qmp_capabilities", "system_powerdown"])
            finally:
                thread.join(timeout=5)
                server.close()
                (runtime / "qmp.sock").unlink()


if __name__ == "__main__":
    unittest.main()
