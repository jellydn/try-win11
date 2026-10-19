# M1 B1 report — 2026-10-19

Decision: **blocked / revisit after prerequisites**, not G1 go. Automated implementation operator: Amp on the requested physical Mac. Gate approver: maintainer (decision pending); independent second operator not assigned. Scope: read-only media and host inspection plus isolated empty-HVF prerequisite probe. No Windows install or existing VM changes.

## Observed host and input

- Mac14,10, Apple M2 Pro, ARM64, 34,359,738,368 bytes RAM (32 GiB).
- macOS 27.0.1, build 26A434. `sysctl -n kern.hv_support` returned `1`.
- Initial `df -h` showed approximately 25 GiB available on the data volume; B1 requires 160 GiB. No disk cleanup, VM creation or runtime installation was performed.
- Scripted host check: 26,012,540,928 bytes free versus 171,798,691,840 required; exit 1 with `At least 160 GiB free on the VM volume required by B1`.
- `clang -Wall -Wextra -Werror -framework Hypervisor` compiled the prerequisite probe. Local ad-hoc signing with only `com.apple.security.hypervisor` succeeded. Executing it returned `hv_vm_create=0x0`, `hv_vm_destroy=0x0`, exit 0. This is an empty host VM, not a QEMU guest or Windows boot.
- Xcode developer directory exists. `qemu-system-aarch64` and `swtpm` are absent from PATH; Homebrew reports neither installed. No approved runtime, firmware/key template or signed ARM64 driver set is pinned yet.
- Requested ISO basename: `Windows11_26100.4349_Professional_en-us_arm64.iso`, 5,268,480,000 bytes.
- SHA-256: `b54034fd37ef074c0c654c1c0f6587a1d495c5545c34cdface2eb5ab63b6dc34`.
- Read-only attachment: `hdiutil attach -readonly -nobrowse`; detached afterward. PE signature `PE\0\0`, machine `0xAA64` at `efi/boot/bootaa64.efi`.
- `sources/install.wim` XML: indexes 1 Home, 2 Home Single Language, **3 Professional**; all ARCH `12` (ARM64), en-US, build 26100, revision 4349. The filename alone was not used as architecture/edition evidence.
- Publisher checksum for this exact artifact was not found. A local hash plus readable metadata does **not** establish authentic/unmodified Microsoft media. Search results for other builds/architectures were not accepted. No download, media write or redistribution occurred.

## Evidence commands

From the repository root, run these inside tmux session `try-win11`:

```bash
python3 scripts/boot.py host .
python3 scripts/boot.py inspect-iso "$ISO"
python3 -m unittest discover -s tests -v
```

`ISO` denotes the user-supplied path (host home path omitted from this public report). Host inspection exited 1 for insufficient storage, before creating a VM. Scripted media inspection exited 0 with the same SHA-256 and three images reported above; both read-only attachments were detached. macOS emitted hdiutil deprecation warnings, not inspection failures. The ISO size and modification time remained unchanged (5,268,480,000 bytes; 2026-09-27 21:35:49 local host time).

Local verification results:

- `python3 -m unittest discover -s tests -v`: **11 tests, OK**, including crash-marker rejection without state mutation.
- `python3 scripts/check_docs.py`: **PASS**, 12 Markdown files, 34 relative file links.
- `go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7`: **exit 0**. The installed binary was older, so the pinned version was run explicitly.
- `python3 scripts/boot.py create config/inputs.example.json <new-local-scratch-package>`: **exit 1**, insufficient storage; destination did not exist afterward. This is an actual hardware preflight rejection, not a mocked result.
- A later `df -h` still showed no mounted volume meeting 160 GiB (data volume about 21 GiB available). No external disk was silently selected.

The [developer instructions](../developer-boot.md) explain the empty-HVF probe, candidate tuple, state safety and commands. Runtime manifests remain explicitly unresolved; no build transcript is invented.

## Open gates and required decision

1. Provide a VM volume with at least 160 GiB available, or approve a documented change to the experiment resource gate. Do not delete data or silently reduce it.
2. Provide Microsoft's checksum/provenance for the exact ISO, or choose different official ARM64 media with a verifiable publisher checksum. Confirm suitable Windows use rights before installation.
3. Complete B1 source/build pins, firmware enrollment and signed ARM64 essential-driver audit. The candidate launcher is unexecuted with real QEMU/swtpm; source rebuild/enrollment/driver procedures remain incomplete.
4. Perform B2/B3 and both operators' B4 evidence. Windows desktop, actual QEMU HVF, Secure Boot enabled/unsigned rejection, TPM 2.0 readiness/persistence, disk/input/NIC, online OOBE, update scan and all six cold boots remain **not tested**.
5. G1 remains open. ADRs 0001/0002 are not accepted as a proven stack; MIT stays selected. G2–G5 remain open and no work advances past them. No SPICE harness, packaged runtime, Developer ID, notarization, full UI or release claim.
