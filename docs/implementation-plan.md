# Try Win11 implementation plan

Date: 2026-10-19. Status: **proposed, documentation only; no gates passed**.

## Recommendation and scope

Fund a bounded Windows 11 ARM64 boot experiment on an M-series Mac first. Use QEMU + HVF as the candidate runtime, not Virtualization.framework. Only after reproducible boot and a distributable console/runtime proof should the project build a full native interface.

The [assumption register](assumptions.md) validates feasibility against 20 sources and separates upstream evidence from local tests. It covers media/licensing, UEFI/TPM/Secure Boot, drivers, graphics, network/audio, host integration and distribution. Read its limits before approving implementation.

### First public beta contract

- Native SwiftUI/AppKit app for tested Apple Silicon/macOS pairs. One running VM initially; no Intel host or AMD64 guest promise.
- User obtains official Windows 11 Pro ARM64 ISO and license. App validates media and creates a conservative VM profile; standard Windows Setup/OOBE/activation stays inside Windows.
- No end-user terminal, package manager, root helper, security downgrade or guest driver test mode.
- Guest console from firmware to desktop, working keyboard/pointer, NAT internet, audio output, graceful shutdown and explicit force-stop warning.
- Opt-in text clipboard and one selected read-only shared folder through proven guest tools. Read-write sharing is deferred until confinement tests pass and the maintainer accepts its risk.
- Stable per-VM disk/firmware/TPM identity, offline whole-VM backup/restore, useful sanitized diagnostics, direct signed/notarized distribution.

**Not in the first beta:** guaranteed Microsoft support/certification, seamless unattended Windows install, Windows license resale, gaming, accelerated 3D, DX12 compliance, GPU/USB passthrough, microphone/camera, bridged networking, snapshots/clones, live migration, saved-state upgrades, nested virtualization, WSL2/Hyper-V/VBS or a multi-backend VM platform. Guest x86/x64 app translation belongs to Windows and does not translate kernel drivers.

If users require these excluded features, decide whether a different product is more appropriate before implementation.

## Architecture and ownership

```text
SwiftUI app + AppKit guest console
  | configuration / consent / one lifecycle owner
  +--> QMP private Unix socket --> bundled QEMU ARM64 --> Hypervisor.framework
  |                                  |  disk, devices, firmware
  +<-> local SPICE display/input <----+
  |       optional guest-agent channels: clipboard and WebDAV
  +--> bundled swtpm <-------------- QEMU TPM frontend
             | persistent per-VM TPM state
VM package: config + identity + disk + UEFI variables + TPM state
```

No server backend is required. The proposed responsibilities are modules in one app, not independent services or new public frameworks:

| Responsibility | Contract / failure rule |
| --- | --- |
| Media/preflight | Check ARM64 media, known hash/provenance, host resources and runtime availability before disk creation. Reject unknown/corrupt inputs with a useful error. Do not collect Windows credentials. |
| VM store | Version config schema and runtime compatibility IDs. Stable UUID/MAC; one writer; atomic config replacement; explicit offline backup/restore of coupled state. No silent TPM/firmware recreation or unsupported import paths. |
| Runtime owner | Actor serializes `stopped → starting → running → stopping → stopped`, with explicit failure state and startup/stop deadlines. Start TPM first, connect QMP, then expose console. QMP events and child exits determine state, not button intent. Defer guest suspend. |
| Guest console | Local SPICE client embedded through AppKit; pixels/input independent of QMP control. Cover firmware/Setup without a guest agent. An agent adds integration only after drivers work. Handle reconnect, focus, key release, pointer capture, Retina scaling and resize. |
| Integration | Default-off text clipboard and selected-folder grants; guest channel disconnect revokes access. No default host home directory, microphone, camera or inbound forwarding. |
| Diagnostics/release | Bounded local logs with redaction and user-reviewed export; signed pinned runtime and dependency notices. Report exact manifest/build IDs; no telemetry by default. |

Startup failure must clean up only processes owned by that VM. Lost QMP/console is not permission to start a duplicate VM. On app crash/relaunch, inspect a verifiable process identity and package lock; do not signal a reused PID. On forced stop, warn of guest data loss. On host sleep, reconnect or give a recoverable error; do not advertise guest hibernation. App updates require shut-down VMs and a state backup.

Proposed ADRs:

1. [Runtime and process boundary](adr/0001-runtime-and-process-boundary.md).
2. [Coupled VM state and security](adr/0002-vm-state-and-guest-security.md).
3. [Direct distribution and licensing](adr/0003-distribution-and-licensing.md).

## Phased implementation backlog

Estimates are engineer-days for someone experienced with macOS/VMs, not calendar promises. Hardware access, licenses, legal review and signing wait time are excluded. Name actual owners at kickoff. Dependencies form the critical path: **M1 → M2 → M3 → M4 → M5**. No full UI before G2.

### M1 — Reproducible Windows 11 ARM boot (5–10 days)

Owner: runtime engineer; approval: maintainer. Dependencies: real Mac, permitted Windows use/media, build tools.

| ID | Task / deliverable | Acceptance |
| --- | --- | --- |
| M1.1 | Execute B1/B2 in the [boot work order](boot-milestone.md); pin sources, patches, firmware keys, drivers and machine tuple. | Inputs and commands are complete; no moving `latest`, unsupported host assumptions or hidden UTM runtime. |
| M1.2 | Install, enable/verify TPM2 and Secure Boot, complete supported OOBE, prove disk/input/NIC and update scan. | Desktop on HVF, normal signature enforcement, no requirement bypass; security evidence and unsigned EFI rejection recorded. |
| M1.3 | Package the developer recipe and have a second operator repeat from empty disk. | Two independent installs; three cold boots each with saved guest data and persistent security state; measurements and sanitized report. |

**G1:** maintainer reviews the full B4 checklist. No-go for bypass dependence, missing signed essential drivers, non-persistent security state, unbounded fork burden or failed reproduction. A UTM boot alone does not pass. At the timebox limit, review failures before spending more time.

### M2 — Packaged runtime, console and release feasibility (5–10 days)

Owner: runtime/release engineer; approval: maintainer plus security/license reviewers. Dependency: G1. A small throwaway host/console harness is allowed; no full setup UI.

| ID | Task / deliverable | Acceptance |
| --- | --- | --- |
| M2.1 | Build source-pinned QEMU, swtpm/libtpms, firmware and transitive dependencies into relocatable app paths. Record SBOM, licenses, corresponding-source obligations and minimum OS. | Standalone bundle contains all required libraries/resources; no `/opt/homebrew` or developer-checkout load paths; source rebuild documented. |
| M2.2 | Build a minimal Swift/AppKit SPICE console harness; audit client license and ARM64 macOS support. | Same VM's firmware, installer and desktop visible; keyboard/pointer, resize/fixed-resolution fallback and disconnect recovery work. No RDP or external viewer requirement for users. |
| M2.3 | Probe signed ARM64 guest tools, audio output and WebDAV/clipboard channels using the harness. | Each capability has a working candidate and license/provenance record. Record unresolved gaps; do not assume x64 drivers can substitute. |
| M2.4 | Review threat model, entitlements, MIT/third-party license compatibility and Windows usage/distribution claims. Sign the minimal bundle; with release-owner approval, notarize/staple and test a downloaded quarantined DMG. | On a clean nondeveloper Mac, install and boot without Homebrew/root/security bypass. `codesign --verify --deep --strict`, `spctl --assess`, `stapler validate` and actual launch pass; notary log reviewed. |

**G2:** maintainer approves the ADRs, selected license, support boundary, build/patch budget, guest integration candidates and direct-distribution proof. Block full UI if essential libraries cannot ship, console requires an unplanned rewrite, signing fails, or licensing has no acceptable path. If only optional integrations fail, explicitly reduce the beta contract and record the decision. Do not quietly relabel missing features as complete.

### M3 — VM lifecycle and guided native setup (10–15 days)

Owner: macOS engineer; approval: maintainer. Dependency: G2.

| ID | Task / deliverable | Acceptance |
| --- | --- | --- |
| M3.1 | Implement config/store schema, package locking, atomic writes, resource preflight, identity and state preservation. | Tests reject double-open, corrupt/future schema, unavailable disk and incompatible runtime without changing the VM; stopped-state backup/restore preserves security state. |
| M3.2 | Implement argument generation, runtime actor, QMP protocol/events, bounded logs and owned-process cleanup. | Start/stop/restart, TPM failure, QEMU exit, timeout and reconnect tests have correct observable state; no orphan process or duplicate VM. |
| M3.3 | Build small SwiftUI library and setup flow: host check → official media/license guidance → ISO import/validation → resources/storage → create → console/Windows Setup. | Fresh user reaches Windows desktop without host terminal; wrong-architecture/corrupt media and low disk fail before partial VM publication; cancellation preserves selected media. |
| M3.4 | Add start/shutdown/force-stop, disk location/free-space status, error recovery and diagnostics export. | Keyboard/VoiceOver navigation, explicit destructive confirmations, guest setup after reboot, host sleep/relaunch and failure recovery are demonstrated. UI never claims Windows is ready merely because QEMU started. |

**G3:** new-user setup and recovery scenarios pass on the reference host; no lost state in tested failure paths. Record manual actions and elapsed/active setup time. Do not add unattended XML installation until the baseline works and its terms/account/driver implications are reviewed.

### M4 — Guest integration and usability beta (7–12 days)

Owner: macOS/guest integration engineer; approval: maintainer and security reviewer. Dependency: G3; uses M2 candidates.

| ID | Task / deliverable | Acceptance |
| --- | --- | --- |
| M4.1 | Deliver pinned, signed guest-tools media through a documented install path; detect channel readiness without treating agent absence as VM failure. | Drivers load with Secure Boot; rollback/reinstall documented. Setup works with tools absent. Audit every shipped binary, not only the top-level installer. |
| M4.2 | Implement NAT reconnect/status and one tested audio-output path. | DNS/HTTPS/Windows Update, Wi-Fi change and host sleep recovery pass; 30-minute playback with no lost device or crash; no microphone permission prompt. |
| M4.3 | Add opt-in bounded text clipboard and a selected read-only WebDAV folder. | Bidirectional Unicode paste, disabled-state isolation, path/symlink confinement, host-enforced read-only access, reconnect and revocation tests pass. No silent home sharing or guest command execution. |
| M4.4 | Refine console scaling, resolution, focus and guest key handling; document limitations. | Firmware/Setup/desktop remain usable at 1280×720 and Retina/full-screen; Command/Windows key policy and capture release are clear; no stuck modifiers. No 3D claim. |

**G4:** the beta contract works on the hardware matrix below. If audio/sharing/clipboard cannot meet safety or driver requirements, stop or get explicit approval for a reduced beta scope. Keep experimental 3D out of this gate and out of the default driver set.

### M5 — Hardening, release and maintenance (7–12 days)

Owner: release maintainer; approval: release owner and security/license reviewers. Dependency: G4 and named maintenance capacity.

| ID | Task / deliverable | Acceptance |
| --- | --- | --- |
| M5.1 | Run complete regression/failure matrix, clean-machine setup, update/rollback and encrypted-guest restore tests. | No open data-loss, security, first-boot or signing blockers. Candidate OS floor and all advertised chip/OS pairs have results. |
| M5.2 | Produce versioned DMG, source bundle, checksums, SBOM, notices, security/contact policy, support matrix, user guide and recovery guide. | Binary rebuilt from published instructions (allow signing timestamp differences), signature/notary checks pass, sources match distributed build; no proprietary media/secrets included. |
| M5.3 | With explicit approval, publish a limited beta and monitor install failures, VM startup errors and reported regressions without default telemetry. | Release owner records go/no-go and rollback plan. Published assets remain immutable; withdraw broken release and point to prior compatible version if needed. Never automatically downgrade VM state. |

**G5:** release owner signs off on technical evidence, legal notices, support claims, known limitations and maintenance owner. No public launch if a release cannot be supported. This plan does not authorize uploading binaries, notarization submissions or publication.

## Dependencies and resource commitments

| Dependency | Needed by | Required output / fallback |
| --- | --- | --- |
| Real M-series test hardware + second operator | M1 | Reserve a Mac and permitted Windows use. Linux orb/ordinary hosted macOS VM is not a substitute for proven HVF access. No hardware means G1 stays open. |
| QEMU HVF, libslirp, EDK II, swtpm/libtpms | M1/M2 | Pinned build/device/key manifest. If downstream patches are essential, document upstream status and maintenance budget or stop. |
| Signed ARM64 storage/NIC/display/serial drivers and tools | M1/M2 | Binary/signature/license matrix. Prefer inbox drivers where tested. No custom kernel-driver development in the initial estimate. |
| ARM64 macOS SPICE client, WebDAV and audio components | M2 | Build/integration/redistribution proof. If no viable client, revisit console/runtime ADR before full UI. |
| Apple Developer Program, Developer ID, protected signing keys, notary access | M2/M5 | Signed clean-machine proof. Credentials managed outside source and logs; maintainer approval for submissions. |
| Qualified license/security review | G2 | MIT is selected for original work. Written decisions are still required on exact third-party dependencies, Windows use/claims and media/tools distribution. No assumption that an open-source app makes Windows free. |
| Physical Mac CI and ongoing maintenance owner | M3/M5 | Scheduled hardware tests, version upgrade triage, security patch and Windows driver/certificate update process. |

## Risk register

Likelihood/impact are planning estimates (H/M/L), not measured probabilities.

| Risk | L / I | Mitigation / trigger | Owner / decision |
| --- | --- | --- | --- |
| Windows boot depends on downstream CPU/ACPI/firmware fixes | M / H | Pin tuple, compare against UTM control, isolate first failure; stop at M1 timebox if maintenance cost is unbounded. | Runtime / G1 |
| Secure Boot or TPM appears present but is ineffective/nonpersistent | M / H | Windows checks plus unsigned EFI negative control and cold boots; backup coupled state. No bypass pass. | Runtime/security / G1 |
| ARM64 signed essential driver unavailable or update breaks it | H / H | Audit binary/catalog/IDs, keep inbox candidate, test supported current Windows media and updates; pin tested tools. No kernel emulation fallback. | Runtime / G1, G4 |
| Boot succeeds but Windows support/requirements/licensing claims cannot be met | H / H | Separate technical success from authorization; review graphics/CPU and usage rights. If official support is mandatory, no-go until established. | Maintainer/legal / G2 |
| Console or audio requires large new native integration | M / H | Minimal M2 harness before UI; cap effort and revisit scope rather than promise a full client/driver rewrite. | macOS / G2 |
| Experimental 3D increases instability or introduces restricted binaries | H / H | Separate optional research; no D3DMetal bundling or gaming claims without rights and test evidence. | Maintainer / future ADR |
| Sharing or control endpoints expose host data | M / H | Private sockets, minimal guest channels, default off, host-enforced folder access and redacted diagnostics. | Security / G4 |
| BitLocker/state reset/update causes data loss | M / H | No automatic state reset, stopped whole-VM backup/restore tests, recovery guidance; stop release for any loss. | Runtime / G3, G5 |
| Unsigned/transitive library or absolute path breaks clean distribution | M / H | M2 inside-out signing and quarantined clean-machine test; no blanket runtime exceptions. | Release / G2 |
| Large ISO/download/disk needs undermine minimal setup | H / M | Import official ISO, clear space/time guidance, sparse disk with real free-space checks; measure user actions/time. | Product / G3 |
| New Mac/macOS/Windows release breaks the pinned profile | H / H | Support only tested pairs; keep prior runtime for compatible VMs, staged upgrades and shutdown backup. | Maintenance / G5+ |

## Test strategy and evidence

### Layers

1. **Documentation checks now:** [CI](ci.md) checks text hygiene, inline relative file links and workflow syntax. Sources and unverified claims remain labeled; no product code or claimed Windows boot from this Linux orb.
2. **Unit tests in M3:** public configuration validation, safe argument generation with spaces/Unicode paths, schema compatibility, resource boundary checks and observable lifecycle outcomes. Inject only the process/QMP boundary needed to test failures; avoid testing private call order.
3. **Protocol integration tests:** QMP capability handshake/IDs/events/errors, partial messages, unexpected disconnect and child exit while starting/stopping. Assert no duplicate start or destroyed state. Test console reconnect and guest-agent absence separately.
4. **Real hardware tests:** install from ISO, security checks, input/network/audio/sharing, cold boots, update and restore on actual M-series hardware. Mocks and screenshots cannot replace these.
5. **Security/release checks:** audit dependency licenses/signatures, inspect rpaths with `otool -L`, verify all nested code, assess Gatekeeper and stapling, scan public artifacts for sensitive data. Test the downloaded quarantined release, not only a local Xcode build.
6. **Usability tests:** three new users unfamiliar with QEMU each complete setup with no host terminal or assistance. Record active actions, Windows prompts, download/install time separately. Proposed target: at most 10 active host-setup minutes excluding Windows interaction, ISO transfer and installation wait; revise from evidence, not marketing.

### Hardware/guest matrix

| Scope | Required cases |
| --- | --- |
| G1 | One exact M-series Mac/macOS build, one pinned official Windows Pro ARM64 release, two operators/clean installs. Prefer M1/M2 to expose baseline limitations. |
| G2 | Same guest in relocated signed bundle on a clean nondeveloper Mac; minimum proposed host OS. If macOS 14 cannot run the selected dependencies, raise the floor before advertising it. |
| G4/G5 | At least an older M1/M2 and newer available M-series Mac; minimum supported and latest stable macOS; current official Windows release and any older release still advertised. Include 16 GB host and larger-memory host. Untested chips/OS versions are not supported by inference. |
| Every runtime/firmware/driver change | Reference install/boot/security tests, update from last app version, consistent offline backup/restore and lost-connection recovery. Expand if the changed component affects integration. |

### High-value failure and boundary cases

- Wrong x64 ISO, wrong hash, expired/missing media; no HVF; missing or rejected ARM64 driver. Must stop clearly, not downgrade security or select TCG.
- Host free disk just below/above preflight threshold; disk fills during guest writes; removable VM storage disappears. Preserve recoverable state and report actual risk; sparse size is not free capacity.
- Open the same package twice; corrupt or newer schema; locked files; malicious imported paths or qcow2 external backing references. Do not auto-follow imported resources outside an approved package.
- QEMU or swtpm crashes, QMP disconnects, app quits mid-start, host sleeps during Setup, host restarts after forced stop. No automatic TPM reset, duplicate writer or unrelated process termination.
- Secure Boot disabled, wrong key store, unsigned EFI/driver and missing TPM negative controls on disposable VMs. These must not be accepted as a healthy profile.
- Folder traversal/symlink escape, attempted write on read-only share, revocation while open, clipboard oversize/Unicode and channel disabled. Assert no unintended host reads/writes or pasteboard changes.
- Offline restore of a BitLocker-enabled disposable VM with complete state; separate incomplete-state restore must fail safely or enter documented recovery. Never collect recovery keys.
- Manual app update with running VM must require shutdown; incompatible machine/firmware must not mutate state. Rollback only with matching runtime/state backup; no saved-state compatibility promise.

Store gate reports with manifest ID, exact commands, expected/actual results, sanitized logs, screenshots/short interaction recordings, counts and known failures. Public reports exclude Windows images, disks, account details and TPM state. Keep licensed fixtures private. Set up fast CI for source/unit/docs checks and a dedicated physical Mac lane for HVF tests; do not call hosted CI green a hardware pass.

## Gate ownership and next action

Each report must name an approver, date, evidence links, accepted limitations, open blockers and a decision: **go**, **no-go**, or **revisit with a bounded experiment**. All gates are currently open.

The next implementation action is M1.1/B1 on a real M-series Mac, after the maintainer names owners and accepts the proposed experiment scope. MIT is selected for original project work; third-party and Windows licensing reviews remain required. Do not scaffold the full application first. M2 needs explicit approval for signing submissions; M5 needs separate approval for publication. Maintenance must track QEMU/firmware/TPM/guest-driver security advisories and Windows certificate/revocation changes, triage reports, and repeat the matrix before changing the supported profile.
