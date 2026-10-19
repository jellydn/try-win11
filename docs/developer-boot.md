# M1 developer boot prototype

Status: **candidate code, not a known-good Windows recipe**. B1 is blocked on storage and input provenance. No gate is passed. See the [Mac report](reports/2026-10-19-mac-preflight.md) before using this code. Python 3.10+ and Xcode tools are developer dependencies only. There is no app or bundled runtime.

## 1. Read-only checks (B1)

Run from the repository root on a physical Apple Silicon Mac:

```bash
python3 scripts/boot.py host /path/to/existing/VM-parent
python3 scripts/boot.py inspect-iso /absolute/path/to/Windows11_ARM64.iso
```

`host` returns nonzero below 16 GiB host RAM, macOS 14, or 160 GiB available storage, or without host hypervisor support. A support flag is not proof of a working QEMU accelerator. `inspect-iso` mounts read-only at a private temporary mount point, reads the AArch64 PE header and uncompressed WIM XML, computes SHA-256, then detaches only its own attachment. It supports `sources/install.wim`, not ESD or compressed XML. It does not authenticate Microsoft signatures or prove that every WIM resource is intact. Compare the hash to Microsoft's exact release/language checksum separately. Do not mark a locally computed hash as publisher verification.

An isolated Hypervisor.framework prerequisite probe is available. It creates/destroys an empty VM; it does not execute a guest CPU or test QEMU. Run it inside the project's tmux session:

```bash
mkdir -p /tmp/try-win11-probe
clang -Wall -Wextra -Werror -framework Hypervisor scripts/hvf_probe.c -o /tmp/try-win11-probe/hvf-probe
codesign --force --sign - --entitlements config/hvf.entitlements.plist /tmp/try-win11-probe/hvf-probe
/tmp/try-win11-probe/hvf-probe
```

This ad-hoc signature is local only, not Developer ID or notarization. Use a new output path; do not overwrite another operator's binary.

## 2. Resolve and pin inputs before VM creation

Copy [the manifest template](../config/inputs.example.json) to `inputs.local.json`. Its unresolved values deliberately prevent launch. Do not replace them with guessed versions, fabricated hashes or unreviewed firmware. The manifest is local operator input, not a trusted import format. Review it before it can execute binaries.

Complete B1 in the [work order](boot-milestone.md):

- Select released QEMU and swtpm/libtpms builds for ARM64 macOS. A Homebrew developer runtime is allowed by the plan, but installing the moving formula is not a source-pinned rebuild. Record formula/package revision, binary hashes, full dependency versions, source commits, patches, build flags and local build transcript. Do not copy an installed UTM runtime.
- Pin the matching EDK II AArch64 code and variables template. This candidate expects two 64 MiB flash banks. Review Secure Boot/TPM2 build flags, ACPI support, and enrolled PK/KEK/db/dbx. Record certificate fingerprints, source and enrollment commands. A blank variables file or a `secure` filename is not proof. Key enrollment and firmware build commands remain unresolved, not supplied as a tested procedure here.
- Pin the ISO against Microsoft's published checksum for the exact build/language. Record the source URL in `publisher_hash_source`. Confirm Windows use rights before setting `windows_use_confirmed`.
- Resolve the signed ARM64 NIC/display drivers. The prototype tries inbox NVMe/USB drivers and virtio-net; it does not supply a driver ISO or prove NIC/OOBE compatibility. Record driver hashes, INF IDs, catalog chain, licenses and manual load commands before B3. Do not bypass OOBE or driver enforcement if the candidate NIC fails.
- Fill each artifact's absolute `path`, lowercase SHA-256, source, immutable revision and license. Record transitive libraries and source/build material alongside the manifest. Set `machine` to the exact versioned `virt-X.Y` supported by the selected build. Set `secure_boot_keys_reviewed` only after real review.

No build/download installer is provided while these inputs remain unresolved. A portable source rebuild and tested enrollment/driver instructions remain M1.1 work, not a passed deliverable. Do not advance to M2 to work around this gap.

## 3. Create one new disposable package (B2)

Only after B1 and permitted Windows use are established:

```bash
python3 scripts/boot.py preflight inputs.local.json /path/to/existing/VM-parent
python3 scripts/boot.py create inputs.local.json /path/to/existing/VM-parent/experiment.trywin11
python3 scripts/boot.py launch /path/to/existing/VM-parent/experiment.trywin11 --installer
```

`create` rejects an existing destination before any writes. It never replaces or removes partial state. Preflight checks available storage before creating the package; it rehashes artifacts, probes the exact QEMU's HVF/machine/devices/Cocoa support, checks TPM2 support, and inspects the ISO. A manifest declaration is a human review record, not cryptographic proof of Secure Boot. The runtime/device tuple has not been executed yet.

The candidate is 4 vCPUs, 8 GiB guest RAM, 128 GiB sparse qcow2, `-accel hvf -cpu host`, GICv3, read-only firmware code, writable per-VM variables, TPM2, NVMe, USB installer/input, ramfb/Cocoa display, NAT/virtio-net. No TCG, inbound forwarding, clipboard, folder sharing, microphone, custom guest command or installer bypass is added. Cocoa is an M1 console only; M2 must prove native SPICE. QEMU gets an argument array and JSON block nodes, not shell interpolation. Paths with spaces/Unicode work as arguments; package paths with commas are rejected because of swtpm's option grammar.

The launch prints its full QEMU argument vector. Keep it and local logs private until paths are sanitized. The child environment is restricted to PATH, HOME and LANG. Both processes run as the current user, without root. swtpm starts first with a 10-second socket deadline; QEMU starts afterward. SIGINT/SIGTERM request ACPI shutdown through QMP and wait; they do not force-stop Windows. If Setup ignores ACPI, shut down in the guest console. There is no automated forced stop, retry or state reset. If TPM exits, the launcher reports it; stop in the guest and investigate, not restart TPM under Windows.

## 4. Preserve state; then run B3/B4

```text
experiment.trywin11/           (0700)
  config.json                 identity + exact input manifest (0600)
  disk.qcow2                  guest disk (0600)
  uefi-vars.fd                copied once, never reset (0600)
  tpm/                        persistent state (0700)
  started                     fail closed if later TPM state is missing
  qemu.log, swtpm.log          local diagnostics; may contain private paths
```

Short private runtime sockets and a UUID-keyed advisory lock live under `/tmp/try-win11-UID/UUID/`. Children inherit the lock descriptor; actual QEMU/swtpm descriptor retention still needs a real crash test. An `active` marker written before starting TPM independently blocks a new launch after an unclean launcher exit, even if children close inherited descriptors. It is removed only after both children exit. QEMU's disk lock is an additional guard, not a substitute for the crash test. Stale sockets fail closed. After a crash, inspect both child process identities and confirm both are stopped before manual recovery of the marker/sockets; never delete a live lock or signal a PID from a stale file. No PID reuse signalling is implemented. No arbitrary VM imports, cloning or config editing is supported. Full M3 lifecycle/recovery is deferred.

After clean Windows shutdown, launch without `--installer` for cold boots. The ISO remains pinned/validated but is not attached to QEMU. Preserve the entire stopped package and matching immutable runtime/firmware together. Never back up disk alone or copy a running package. Do not delete/replace variables or TPM state to repair boot. Missing state requires a complete backup and explicit recovery review. This prototype has no backup/restore command; encrypted-guest restore remains untested.

Follow B3/B4 exactly: supported online OOBE, Windows Secure Boot/TPM checks, normal integrity enforcement, input/storage/NIC/update scan, three cold boots per operator, unsigned EFI rejection on a separate disposable VM, and independent second install. Keep all unchecked results open. The manifest is not frozen as a known-good profile until that evidence exists and the maintainer decides G1. Full UI, M2 packaging, paid actions, signing submissions and redistribution are outside this prototype.

## Recipe checks (no Windows required)

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
actionlint
```

Tests cover ARM64/metadata inspection and rejection, corrupt XML resources, storage boundary, no replacement/partial publication, pinned hash rejection, safe path arguments, installer removal, inherited writer lock, missing TPM preservation and QMP shutdown replies/events/errors. They do not prove QEMU option compatibility, firmware enrollment, real TPM persistence, boot, guest drivers, crash recovery or Windows security.
