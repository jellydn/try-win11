#!/usr/bin/env bash
# Diagnostic compile only. Never install a VM profile or upload these binaries.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
WORK=${1:?Usage: ci_build_linux.sh NEW_WORK_DIRECTORY}
mkdir "$WORK"
WORK=$(realpath "$WORK")
python3 "$ROOT/scripts/ci_sources.py" --fetch "$WORK/sources"
PREFIX="$WORK/prefix"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib64/pkgconfig"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib64"
export NOCONFIGURE=1
for NAME in libtpms swtpm qemu; do
    SOURCE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sources"][sys.argv[2]]["root"])' "$ROOT/config/ci-sources.lock.json" "$NAME")
    mapfile -t FLAGS < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["sources"][sys.argv[2]]["configure"]))' "$ROOT/config/ci-sources.lock.json" "$NAME")
    cd "$WORK/sources/$SOURCE"
    if [[ "$NAME" == qemu ]]; then
        mkdir "$WORK/qemu-build"
        cd "$WORK/qemu-build"
        "$WORK/sources/$SOURCE/configure" "${FLAGS[@]}" --prefix="$PREFIX"
        ninja -j2 qemu-system-aarch64 qemu-img
    else
        ./autogen.sh
        ./configure "${FLAGS[@]}" --prefix="$PREFIX"
        make -j2
        if [[ "$NAME" == libtpms ]]; then
            make check
        fi
        make install
    fi
done
"$PREFIX/bin/swtpm" --version
"$PREFIX/bin/swtpm" socket --print-capabilities | tee "$WORK/tpm-capabilities.json"
python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); assert "tpm-2.0" in c["features"], c' "$WORK/tpm-capabilities.json"
"$WORK/qemu-build/qemu-system-aarch64" --version
"$WORK/qemu-build/qemu-img" --version
"$WORK/qemu-build/qemu-system-aarch64" -accel help | tee "$WORK/accelerators.txt"
"$WORK/qemu-build/qemu-system-aarch64" -device help > "$WORK/devices.txt"
python3 - "$WORK" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
devices = (root / "devices.txt").read_text()
for name in ("tpm-tis-device", "nvme", "ramfb", "qemu-xhci", "usb-kbd", "usb-tablet", "usb-storage", "virtio-net-pci"):
    assert f'"{name}"' in devices, name
assert "hvf" not in (root / "accelerators.txt").read_text().split(), "Linux must not claim HVF"
print("PASS: Linux diagnostic build/device inventory only; no guest or hardware gate executed")
PY
