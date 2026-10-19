# Milestone 1: reproducible Windows 11 ARM boot

Status: **work order, not an executed or known-good recipe**. Gate G1 is open. No runtime versions, firmware filenames or device tuple are approved yet. Do not mistake illustrative QEMU options below for a runnable command.

## Objective and resources

Before full UI work, install official Windows 11 Pro ARM64 and cold-boot to an interactive desktop on a real M-series Mac using a standalone pinned QEMU + HVF stack. Keep UEFI Secure Boot, TPM 2.0 and Windows driver-signature checks enabled. A firmware menu, installer screen, TCG boot, or a VM that runs only inside UTM is not the deliverable.

Owner: runtime engineer; gate approver: maintainer. Assign named people before starting. Suggested timebox: 5–10 engineer-days, then stop for review instead of extending into an open-ended hypervisor fork.

Required resources:

- One real M-series Mac with 16 GB or more RAM and at least 160 GiB free working space; a second operator for reproduction. Prefer a second Mac for independent evidence.
- An exact supported macOS build. Start with macOS 14 or later if dependencies allow it; raise the proposed floor explicitly if required.
- Xcode Command Line Tools and build dependencies for the developer experiment only. Neither becomes an end-user requirement.
- Official Microsoft ARM64 ISO, its published checksum, suitable Windows license rights, and internet/account access for supported OOBE. Do not commit or record credentials.
- Source/build inputs for QEMU, firmware, swtpm/libtpms and drivers. UTM may be used as a diagnostic control, not as a hidden dependency.

## Work order

### B1. Identify and pin the input set

1. Record Mac model/chip/RAM, `sw_vers`, `uname -m`, and free storage. Confirm an ARM64 host, not an Intel Mac or an assumed virtualized CI host.
2. Obtain the ISO from Microsoft's ARM64 page. Compare `shasum -a 256` output with Microsoft's value for that exact release/language. Inspect `EFI/BOOT/BOOTAA64.EFI` and Windows image metadata; reject x64, corrupt or unknown media. Save edition/build/language/hash and hash-source URL, not the download's expiring token.
3. Select a released QEMU version with ARM64 HVF, the required device models, SPICE and TPM support. Prefer stock upstream. Record every required patch if UTM's integration is needed; bound the maintenance cost before proceeding.
4. Pin EDK II AArch64 firmware code and variable-template sources, build flags and hashes. Prove the build supports Secure Boot, TPM2 and the chosen QEMU ACPI/device model. Record flash sizes and key-enrollment method.
5. Build swtpm/libtpms for macOS ARM64 and pin all dependencies. Use TPM2 mode and a private Unix control socket; Linux CUSE is not a macOS design.
6. Inventory boot/storage/NIC/display/serial-agent drivers and user-mode tools. For every selected kernel driver, record ARM64 PE architecture, matching INF IDs, signed catalog chain, version, hash, provenance and redistribution terms. Test signature acceptance in Windows; a host file-signature check is not sufficient.

**Output:** a versioned input manifest plus build transcript. All chosen inputs need immutable revisions/checksums. Unresolved fields are allowed during research, not at G1.

### B2. Establish the virtual hardware and firmware tuple

Create a disposable new VM package with owner-only permissions. Keep immutable firmware code separate from writable per-VM variables and TPM state. Start with 4 vCPUs, 8 GB RAM and a 128 GiB sparse qcow2 disk. Record allocated and actual storage. Preserve free space for installation and updates.

Resolve these values experimentally and put the final values in the manifest and launch arguments:

| Component | First candidate / decision rule |
| --- | --- |
| Machine / CPU | Versioned `virt-<release>`, `-accel hvf`, `-cpu host`, GICv3 and Windows-compatible ACPI. Record high-memory/interrupt-controller flags, do not copy old workarounds blindly. Probe `-accel help`, `-machine help`, `-device help` and actual launch logs. No TCG fallback. |
| Firmware | Read-only AArch64 firmware code plus matching writable variable store; enrolled PK, Microsoft KEK/db and appropriate dbx. Record firmware verification mode and actual Windows Secure Boot state. ARM TrustZone `secure=on` is not a synonym for UEFI Secure Boot and must not be assumed compatible with HVF. |
| TPM | `-tpmdev emulator` connected to swtpm TPM2; ARM frontend candidate `tpm-tis-device`. Verify the chosen release's ACPI/PPI support. No host TPM or Secure Enclave claim. |
| Installation media | A bootable virtual USB optical/storage path supported by both firmware and Windows inbox drivers. Prove it can read the whole installer. |
| System disk | Test a QEMU NVMe device with Windows inbox ARM64 driver first. If incompatible, use virtio block/SCSI only with an accepted signed ARM64 storage driver loaded from separately mounted media during Setup. Freeze one tuple; never switch disk controllers after install without a migration test. |
| Network | `-netdev user` / libslirp plus a NIC with a proven signed ARM64 driver (virtio-net candidate). Load the driver before OOBE where required; do not rely on downloading a driver through a NIC that is not working. |
| Display / input | Firmware framebuffer (`ramfb` candidate) for Setup, then a tested signed display-only driver/device pairing. Check which devices require downstream patches. USB keyboard/tablet through an emulated xHCI controller. No 3D requirement. |
| Console / diagnostics | Existing QEMU Cocoa display or a local SPICE viewer for the experiment; QMP and serial/debug output where available. No network-accessible unauthenticated console. Record if an external viewer is required so M2 can remove that dependency. |

**Output:** full argument vector, environment allowlist, file layout, firmware enrollment steps, swtpm startup/readiness/shutdown steps, and exact driver-load steps. Commit a portable launch/build recipe during M1 implementation, not during this documentation task. Include failure checks for missing HVF, wrong inputs, occupied state and unavailable sockets.

### B3. Install and prove boot

1. Launch swtpm, wait for readiness, then launch QEMU with explicit HVF. Capture sanitized stderr/version/build configuration and confirm no fallback. Store runtime sockets in a private short path.
2. Enter the Windows installer through UEFI. Install to the empty disk; record all driver loads and prompts. Complete supported online OOBE. Do not disable TPM/Secure Boot checks, driver enforcement or account requirements to obtain a pass.
3. Reach an interactive Windows desktop. Record `winver`/OS build, edition and architecture. In elevated PowerShell, record `Confirm-SecureBootUEFI` (expected `True`) and `Get-Tpm` (expected present/ready). Confirm TPM specification version 2.0 through `tpm.msc` or `Win32_Tpm`. Capture `msinfo32` BIOS mode/Secure Boot state and Device Manager for the chosen devices. Check `bcdedit` for test-signing/integrity overrides; both must be absent/off.
4. Verify guest input, system disk writes, DHCP/DNS/HTTPS and Windows Update scan. Install one cumulative update when offered, then cold-boot. An absence of offered updates is not proof that updating works; retain the build and scan result and schedule an update test before beta.
5. Shut Windows down cleanly; stop QEMU and then swtpm; remove installation media. Perform three cold boots with persistent variables/TPM and verify a saved guest file after each boot. Record desktop time and failures; a suggested initial target is under 120 seconds per cold boot on the recorded machine, not a cross-device promise.
6. On a separate disposable instance, attempt to launch an unsigned EFI test image. Verify firmware rejects it while still allowing the Microsoft-signed bootloader. Do not modify the reference installed VM's keys.
7. Recreate from empty state with a second operator using only the recorded inputs and recipe. Repeat the install, security checks and cold boots. Do not distribute the installed Windows disk as the reproduction method.

### B4. Publish the evidence, not the guest

Create a sanitized M1 report with this checklist:

- [ ] Exact host pair, immutable runtime manifest, source/build transcript and patches.
- [ ] Full standalone launch instructions and driver/firmware/key-enrollment steps, no undocumented UTM dependency.
- [ ] Two clean installs performed by two operators, with desktop and cold-boot results.
- [ ] HVF evidence, three cold boots per install, persistent disk/UEFI/TPM state.
- [ ] Windows Secure Boot enabled, unsigned EFI rejection, TPM 2.0 ready, normal driver integrity.
- [ ] Input, storage and NIC pass; online OOBE and Windows Update scan results recorded.
- [ ] Display model/driver, `dxdiag` result and missing acceleration/compliance claims stated explicitly.
- [ ] Timings, host memory/CPU observations, actual disk usage, failure notes and unresolved risks.
- [ ] No Windows media/disks, product keys, account data or TPM state in public evidence.

## G1 decision

**Go:** every B4 item passes and the maintainer accepts the documented limitations and patch burden. Proceed only to packaging and console feasibility (M2), not the full UI.

**No-go / revisit:** install requires bypasses, HVF cannot be proved, required drivers are unsigned/unavailable, Secure Boot/TPM state is not persistent, independent reproduction fails, or the stack depends on an unmaintainable fork. Preserve the failure report. Reduce scope, seek an upstream fix, or stop. Do not use full UI development to defer these failures.

A desktop with a basic display can pass the technical experiment without proving Windows certification or DX12/WDDM compliance. If official Microsoft support or full graphics compliance is a launch requirement, that unresolved condition is a product no-go until separately established.
