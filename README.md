# Try Win11

Try Win11 is a proposed open-source native macOS app that helps Apple Silicon Mac users install and run Windows 11 ARM with minimal host setup.

**Status: planning only.** There is no app, build, tested VM recipe, or release yet. No Windows boot was performed for this proposal. The planning environment is a Linux orb, not an M-series Mac.

## Start here

- [Implementation plan](docs/implementation-plan.md): scope, phased tasks, dependencies, risks, acceptance criteria, and go/no-go gates.
- [Assumption validation and sources](docs/assumptions.md): what primary documentation supports and what still needs a hardware test.
- [First milestone: reproducible boot](docs/boot-milestone.md): the work order and evidence needed before full UI development.
- [Architecture decisions](docs/adr/0001-runtime-and-process-boundary.md): proposed runtime, security state, and distribution decisions.
- [Contributing](CONTRIBUTING.md): how to turn this plan into reviewed work.
- [Project terms and constraints](CONTEXT.md).
- [CI checks](docs/ci.md): documentation validation now and macOS checks when app targets exist.

## Proposed direction

Use QEMU's ARM64 system emulator with Apple's Hypervisor.framework accelerator (HVF), controlled by a Swift app. First prove a repeatable install and cold boot on a real M-series Mac. Then prove that the same runtime can be signed and distributed. Build the full SwiftUI/AppKit interface only after those gates pass.

The first release targets ordinary desktop and development work, not gaming, GPU workloads, or nested virtualization. Start with a display-only console. Treat Windows 3D acceleration as a separate research track.

Windows is not included. Users must obtain official ARM64 installation media and a valid license for their use. Try Win11 must not claim Microsoft authorization or support without evidence. Successful activation is not proof of license rights.

## License

Try Win11's original code and documentation use the [MIT license](LICENSE). This does not relicense QEMU, firmware, guest drivers or other third-party components, or grant rights to Windows. Any future bundled runtime retains its own license and source-delivery obligations; see [ADR 0003](docs/adr/0003-distribution-and-licensing.md).
