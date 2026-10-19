# Try Win11

Try Win11 is a proposed open-source native macOS app that helps Apple Silicon Mac users install and run Windows 11 ARM with minimal host setup.

**Status: M1 developer prototype; boot gate blocked.** Read-only ISO and host checks now run on a physical M2 Pro Mac. A candidate QEMU + HVF launcher and state-safety tests exist, but no Windows boot, known-good runtime recipe, app or release is established. The host lacks the plan's required free storage; media provenance and runtime/firmware/driver pins remain open.

## Start here

- [Implementation plan](docs/implementation-plan.md): scope, phased tasks, dependencies, risks, acceptance criteria, and go/no-go gates.
- [Assumption validation and sources](docs/assumptions.md): what primary documentation supports and what still needs a hardware test.
- [First milestone: reproducible boot](docs/boot-milestone.md): the work order and evidence needed before full UI development.
- [Developer prototype](docs/developer-boot.md): read-only preflight, candidate launch commands and coupled-state safeguards.
- [Mac preflight report](docs/reports/2026-10-19-mac-preflight.md): observed evidence, blockers and open gates.
- [Architecture decisions](docs/adr/0001-runtime-and-process-boundary.md): proposed runtime, security state, and distribution decisions.
- [Contributing](CONTRIBUTING.md): how to turn this plan into reviewed work.
- [Project terms and constraints](CONTEXT.md).
- [CI checks](docs/ci.md): source pins, diagnostic builds, contract tests and safe source-only artifacts; no hardware gate passes.

## Proposed direction

Use QEMU's ARM64 system emulator with Apple's Hypervisor.framework accelerator (HVF), controlled by a Swift app. First prove a repeatable install and cold boot on a real M-series Mac. Then prove that the same runtime can be signed and distributed. Build the full SwiftUI/AppKit interface only after those gates pass.

The first release targets ordinary desktop and development work, not gaming, GPU workloads, or nested virtualization. Start with a display-only console. Treat Windows 3D acceleration as a separate research track.

Windows is not included. Users must obtain official ARM64 installation media and a valid license for their use. Try Win11 must not claim Microsoft authorization or support without evidence. Successful activation is not proof of license rights.

## License

Try Win11's original code and documentation use the [MIT license](LICENSE). This does not relicense QEMU, firmware, guest drivers or other third-party components, or grant rights to Windows. Any future bundled runtime retains its own license and source-delivery obligations; see [ADR 0003](docs/adr/0003-distribution-and-licensing.md).
