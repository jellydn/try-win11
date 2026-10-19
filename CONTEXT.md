# Project context

Date: 2026-10-19. All architecture decisions are proposed, not approved implementation commitments.

License decision: original Try Win11 code and documentation use MIT. Third-party runtime and Windows terms remain separate; the packaging/license audit is still a release gate.

## Terms

- **Native app**: a macOS SwiftUI/AppKit host application. It does not mean Windows runs directly on Apple hardware.
- **Windows ARM / ARM64**: the AArch64 Windows guest. An AMD64/x64 installer is not interchangeable with it.
- **HVF**: QEMU's accelerator that uses Apple's low-level Hypervisor.framework. QEMU still supplies the virtual machine and devices.
- **Virtualization.framework / VZ**: Apple's higher-level VM API, distinct from Hypervisor.framework. Apple's documented guest paths are macOS and Linux.
- **Reproducible boot**: a second person can install from identified inputs and cold-boot the resulting Windows VM using recorded steps. It does not mean byte-identical Windows disks.
- **Minimal setup**: no Homebrew, Xcode, root helper, disabled SIP/Gatekeeper, or driver test-signing for end users. Windows download, licensing, terms, account steps, and installer time remain visible.
- **Validated in documentation**: supported by cited sources, not a Try Win11 hardware test.
- **Gate passed**: required evidence exists and the named human owner has recorded a decision. No gates have passed yet.

## Proposed initial support boundary

- Apple Silicon only. Establish one exact host/guest pair in milestone 1; expand only with tests.
- Candidate host floor: macOS 14 on a 16 GB Mac, 4 guest vCPUs, 8 GB guest RAM, 128 GiB sparse disk. This is a test profile, not a proven minimum.
- Target Windows 11 Pro ARM64 first. Enterprise and managed installations require separate rights and policy review. Home is not initially promised.
- No bundled Windows, activation bypass, TPM/Secure Boot check bypass, or forced local-account workaround.
- No promise of Microsoft certification, support, Windows Update eligibility, DX12 compliance, games, anti-cheat, GPU passthrough, nested Hyper-V/WSL2/VBS, USB passthrough, snapshots, or live migration.
- No Windows secrets, product keys, account details, TPM state, or user VM disks in source control or public test artifacts.

This document governs product terms. The [plan](docs/implementation-plan.md) governs sequencing; the [assumption register](docs/assumptions.md) governs evidence strength.
