# ADR 0001: Prove QEMU + HVF before building the native interface

Date: 2026-10-19

Status: **Proposed; requires gate G1 and G2 evidence and maintainer approval.**

## Context

The app must run Windows ARM64 on Apple Silicon. Apple's Virtualization.framework documents macOS/Linux guest paths, not a complete supported Windows platform. QEMU supplies the device model and uses Hypervisor.framework for accelerated ARM64 CPU execution. UTM provides useful feasibility evidence but may include patches and integrations absent from stock QEMU. See [source validation](../assumptions.md).

## Decision proposed

Use a pinned ARM64 QEMU build with mandatory HVF and a pinned versioned `virt` machine. Prove a standalone command-line install/boot first. Do not add a second runtime backend or a generic plug-in architecture.

After the boot proof, use a SwiftUI application with AppKit for the guest console and input. Run one bundled QEMU child process and one swtpm child per running VM, as the logged-in user. Use a Swift actor to own lifecycle transitions. Use QMP over a private Unix socket for lifecycle/events; use a local SPICE connection for pixels, input and optional agent channels. Prove a usable, redistributable macOS ARM64 SPICE client before committing to the console implementation. Do not assume VZVirtualMachineView can display a QEMU VM.

Keep QEMU out of the UI process for crash containment and a clear protocol boundary. Do not introduce a root daemon or XPC service unless a later measured requirement needs it. Launch with an argument array, never a shell string or imported arbitrary QEMU arguments. QMP and SPICE are local privileged control surfaces, not network services.

## Alternatives

- **Virtualization.framework:** simpler native integration for documented guests, but an unproven Windows/device/TPM path. Revisit only if authoritative support and a complete boot/driver test change that assessment.
- **Embed QEMU as a library:** avoids process coordination but adds crash, linking, lifecycle and licensing complexity. Reject for the initial product.
- **Automate UTM:** useful as a control experiment, not an independent runtime or reproducible Try Win11 build. If essential patches cannot be maintained, consider contributing a setup flow upstream instead of building another VM engine.
- **TCG:** useful for diagnosis only. No automatic fallback or x64 Windows support claim.

## Consequences

The native UI does not make the emulated devices native. The project must maintain runtime builds, firmware, dependencies and a host display client. HVF solves CPU execution, not graphics acceleration, driver support, or Windows licensing. A SPICE integration failure blocks the full UI; revisit this ADR rather than hiding the failure behind RDP, which does not cover firmware or installation screens.
