# ADR 0002: Treat disk, firmware variables and TPM state as one VM

Date: 2026-10-19

Status: **Proposed; requires gate G1 and security review at G2.**

## Context

Windows boot, activation identity and encrypted disks can depend on stable firmware and TPM state. A disk-only backup or automatic TPM reset can make data inaccessible. A software TPM does not defend guest secrets from a compromised host.

## Decision proposed

Use a versioned per-VM package containing a config manifest, stable VM UUID/MAC, qcow2 disk, writable UEFI variable store, and swtpm state. Bundle immutable AArch64 firmware code and a fresh variables template with the runtime; copy the template only when creating a VM. Keep sockets and locks in a private short runtime path, not inside a user-movable package. Use owner-only permissions for state.

Require UEFI, enrolled Secure Boot keys and TPM 2.0 for the baseline. Do not use installer registry bypasses, guest test-signing, or unsupported OOBE commands as acceptance paths. Keep normal Windows installation/account/activation prompts visible.

Permit one writer per package. Write config changes atomically. Back up or export only while fully shut down, including the disk, variables, TPM state, identity, config and required runtime IDs as a consistent set. Do not support live snapshots, cloning, suspend/resume across versions or automatic firmware/machine-type migration in the MVP. Handle BitLocker recovery keys inside Windows with user guidance; do not log or collect them.

Default clipboard and folder sharing off. Grant only explicit paths and modes. NAT networking has no default inbound forwarding but can still reach host/LAN resources; do not market it as malware containment. Camera, microphone and USB passthrough are out of scope.

## Alternatives and consequences

- Recreating variables/TPM on each start is simpler but breaks identity and recovery. Reject.
- Disk-only snapshots are cheap but do not capture coupled security state. Defer snapshots until consistency is proven.
- Default-on sharing makes setup look easier but expands guest access to host data. Reject.

Firmware or TPM updates require a shutdown backup, a compatibility check and an explicit recovery route. A host backup is not proof that an encrypted VM can be restored; test restoration. Protect host storage with FileVault and explain that copied TPM files are sensitive, not hardware-bound secrets.
