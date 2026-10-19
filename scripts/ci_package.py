"""Deterministic, allowlisted original-source artifact. No runtime redistribution."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[1]
# Changes to the upload surface need an explicit review here; no recursive glob.
FILES = (
    "LICENSE", "README.md", "CONTEXT.md", "CONTRIBUTING.md", ".gitignore",
    ".github/workflows/ci.yml", "renovate.json",
    "config/hvf.entitlements.plist", "config/inputs.example.json", "config/ci-sources.lock.json",
    "docs/assumptions.md", "docs/boot-milestone.md", "docs/ci.md", "docs/developer-boot.md",
    "docs/implementation-plan.md", "docs/reports/2026-10-19-mac-preflight.md",
    "docs/adr/0001-runtime-and-process-boundary.md", "docs/adr/0002-vm-state-and-guest-security.md",
    "docs/adr/0003-distribution-and-licensing.md",
    "scripts/boot.py", "scripts/check_docs.py", "scripts/hvf_probe.c", "scripts/ci_sources.py",
    "scripts/ci_build_linux.sh", "scripts/ci_package.py", "tests/test_boot.py", "tests/test_ci.py",
)


def source_bytes(root, name):
    path = root / name
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Refusing non-regular/outside source: {name}")
    data = path.read_bytes()
    if len(data) > 1024 * 1024 or b"\0" in data:
        raise ValueError(f"Refusing binary/oversize source: {name}")
    data.decode("utf-8")
    return data


def build(root, destination):
    # Validate the complete allowlist before publishing any artifact.
    inputs = [(name, source_bytes(root, name)) for name in sorted(FILES)]
    destination.mkdir(mode=0o700)
    archive = destination / "try-win11-source.tar"
    inventory = []
    with tarfile.open(archive, "x", format=tarfile.USTAR_FORMAT) as output:
        for name, data in inputs:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            # TarInfo defaults: timestamp/uid/gid=0, no host paths or user names.
            output.addfile(info, io.BytesIO(data))
            inventory.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination / "try-win11-source.tar.sha256").write_text(f"{checksum}  {archive.name}\n")
    (destination / "source-inventory.json").write_text(json.dumps({
        "scope": "original project source only; no runtime/media/state; no gates passed",
        "files": inventory}, indent=2) + "\n")
    print(f"PASS: {len(inputs)} allowlisted text sources; SHA-256 {checksum}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new output directory")
    build(ROOT, parser.parse_args().destination)
