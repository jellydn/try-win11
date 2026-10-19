"""Validate/fetch locked public sources. Never fetch guest media or runtime state."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
from urllib.parse import urlsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "config/ci-sources.lock.json"


def validate(lock):
    if lock.get("schema") != 1 or lock.get("profile") != "linux-diagnostic-only":
        raise ValueError("Unsupported source lock/profile")
    if set(lock["sources"]) != {"qemu", "libtpms", "swtpm"}:
        raise ValueError("Only the three reviewed public source inputs are permitted")
    for name, item in lock["sources"].items():
        if not re.fullmatch(r"\d+\.\d+\.\d+", item["version"]):
            raise ValueError(f"{name}: immutable release version required")
        if not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
            raise ValueError(f"{name}: SHA-256 required")
        url = urlsplit(item["url"])
        if name == "qemu":
            revision = f"qemu-{item['version']}"
            expected = f"https://download.qemu.org/{revision}.tar.xz"
        else:
            revision = item["revision"]
            if not re.fullmatch(r"[a-f0-9]{40}", revision):
                raise ValueError(f"{name}: full source commit required")
            expected = f"https://codeload.github.com/stefanberger/{name}/tar.gz/{revision}"
        if item["url"] != expected or url.scheme != "https":
            raise ValueError(f"{name}: unreviewed source URL")
        if item["revision"] != revision or item["root"] != (
                revision if name == "qemu" else f"{name}-{revision}"):
            raise ValueError(f"{name}: revision/archive root mismatch")
        if not item["license"] or not item["configure"] or not all(
                isinstance(flag, str) and flag.startswith("--") for flag in item["configure"]):
            raise ValueError(f"{name}: license and explicit configure flags required")
    qemu_flags = lock["sources"]["qemu"]["configure"]
    if not {"--disable-download", "--disable-install-blobs", "--enable-tpm"} <= set(qemu_flags):
        raise ValueError("QEMU must forbid configure downloads/firmware installation and include TPM")


def verify(path, expected):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    if checksum.hexdigest() != expected:
        raise ValueError(f"Source hash mismatch: {path.name}")


def extract(archive, destination, item, name):
    with tarfile.open(archive) as source:
        members = []
        for member in source.getmembers():
            parts = member.name.split("/")
            if parts[0] != item["root"]:
                raise ValueError(f"Unexpected source root: {name}")
            # No firmware build: omit QEMU's independent ROM source trees, including
            # EDK II's absolute host-X11 symlink. Never relax the data filter.
            if name == "qemu" and len(parts) > 1 and parts[1] == "roms":
                continue
            members.append(member)
        source.extractall(destination, members=members, filter="data")


def fetch(lock, destination):
    # Exclusive directory: do not reuse unchecked cache entries or replace source trees.
    destination.mkdir(mode=0o700)
    for name, item in lock["sources"].items():
        archive = destination / f"{name}.archive"
        with urlopen(item["url"], timeout=60) as response, archive.open("xb") as output:
            if urlsplit(response.url).scheme != "https":
                raise ValueError("HTTPS downgrade rejected")
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > 256 * 1024 * 1024:
                    raise ValueError("Source download exceeds bound")
                output.write(block)
        verify(archive, item["sha256"])
        # Python 3.12+ data filter rejects absolute/escaping links and device nodes.
        extract(archive, destination, item, name)
        print(f"VERIFIED {name} {item['revision']} {item['sha256']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", type=Path, help="new directory; verified public sources only")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    validate(lock)
    if args.fetch:
        fetch(lock, args.fetch)
    print("PASS: CI source pins; not a macOS runtime or licensing approval")


if __name__ == "__main__":
    main()
