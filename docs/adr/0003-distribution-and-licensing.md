# ADR 0003: Direct signed distribution; user-supplied Windows

Date: 2026-10-19

Status: **MIT for original project work is accepted by maintainer request. Distribution/runtime decisions remain proposed and require gate G2 before public builds.**

## Context

End users should not need development tools or Homebrew. QEMU and its dependencies have redistribution obligations. Microsoft's ISO download and a successful Windows activation do not establish Try Win11 authorization, support, or media redistribution rights.

## Decision proposed

Ship a self-contained ARM64 app in a Developer ID-signed, notarized and stapled DMG through direct releases. Defer the Mac App Store: sandbox constraints, runtime packaging and review policy need a separate assessment. Start with manual app updates and a documented shutdown/backup flow, not an automatic VM/runtime migration.

Bundle pinned QEMU, swtpm/libtpms, AArch64 firmware, SPICE client/runtime dependencies and only reviewed redistributable guest tools. Inventory transitive libraries and codecs. Build from source with recorded flags and patches. Publish the required corresponding source, build instructions, notices, checksums and a software bill of materials with each binary release; a link to upstream alone may not meet the obligations. Have a qualified reviewer check the exact combination.

Original Try Win11 code and documentation use the [MIT license](../../LICENSE), as requested by the maintainer. This replaces the initial GPL-2.0-or-later recommendation. MIT permits reuse in GPL-covered distributions, but it does not relicense QEMU or remove obligations from a combined distribution. Preserve all third-party notices and supply corresponding source/build materials where required. Review the exact runtime, linking and packaging arrangement before release; the process boundary is not a legal shortcut.

Windows media and licenses stay outside the distribution. Initially open Microsoft's official ARM64 download page and import a user-selected ISO. Obtain licensing review before adding an automated download flow. Do not rehost ISO files, ship installed Windows disks, embed product keys, store Microsoft passwords, or advertise Microsoft authorization without approval. Keep activation inside Windows.

Sign nested code inside out with correct runtime paths. Give `com.apple.security.hypervisor` to the QEMU executable that uses HVF. Do not add `com.apple.security.virtualization` as a substitute. Enable Hardened Runtime; justify any runtime exception with a failing test. Sign all bundled libraries with the release identity rather than disable library validation by default. No TCG/JIT requirement is assumed.

## Alternatives and consequences

- User-installed Homebrew runtime: acceptable for the first experiment only; fails the end-user setup goal.
- App Store first: adds uncertainty before proving the runtime. Reassess after direct distribution works.
- Bundled Windows appliance: fastest first launch but unresolved Microsoft redistribution rights and identity/security problems. Reject.

Developer Program membership, signing credentials, a macOS build host, notarization service access, release hosting, license review, and ongoing security maintenance are release dependencies. Public publication and signing submissions require the release owner's approval; this plan does not authorize them.
