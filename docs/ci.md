# Continuous integration

## Current checks

[CI](../.github/workflows/ci.yml) runs on pull requests, pushes to `main`, and manual dispatch. All jobs use `contents: read`, no secrets, immutable action commits, checkout without persisted credentials, timeouts and per-ref concurrency cancellation. No deployment, release, signing submission, VM creation or guest execution is allowed.

| Job | Hosted evidence only |
| --- | --- |
| Validate (Ubuntu 24.04) | Contract tests, Python compilation, documentation and actionlint 1.7.7; fail-closed source-pin checks. |
| Linux diagnostic source build | Fetch/checksum QEMU, libtpms and swtpm; build ARM-system device emulation for a Linux host, run libtpms upstream tests, inspect TPM2 capabilities and QEMU devices. No guest is launched. |
| ARM64 Mac probe compile (macOS 15) | Compile/link the existing C probe for ARM64/macOS 14, inspect architecture/load commands and entitlement XML, run portable contract tests. Never execute or sign the probe. |
| Original-source package | After all other jobs pass, build twice and compare bytes; check checksum; extract and rerun contract tests; upload only allowlisted original source, SHA-256 and inventory. Seven-day retention. |

The [source lock](../config/ci-sources.lock.json) pins QEMU 11.1.2 by release archive SHA-256 and swtpm/libtpms 0.10.2 by full source commits plus archive SHA-256. Configure flags are versioned in the same lock. Downloads must match before extraction; extraction uses Python's data filter, checked root paths and a new directory. QEMU's unbuilt `roms/` firmware-source tree is omitted (it contains an absolute EDK II host-X11 link); the data filter remains mandatory for every retained member. Sources over 256 MiB are rejected. QEMU configure downloads and firmware installation are disabled. SHA-256 establishes repeatable bytes from reviewed HTTPS sources, not signature verification or a security/licensing approval.

This is **not a hermetic or bit-identical runtime build**. Ubuntu apt dependencies, hosted runner images, system compiler/SDK and transitive libraries are not source-locked. Their versions are recorded in job logs; QEMU's vendored Python tools are covered by the archive checksum. A full transitive lock, macOS QEMU build, Secure Boot firmware build/enrollment, driver audit and matching runtime manifest remain B1 work. The diagnostic source lock does not populate or approve `inputs.local.json`. No CI output is a runnable Try Win11 distribution.

Linux intentionally enables TCG only to compile its diagnostic device model. It explicitly checks that HVF is absent; it never executes a guest or serves as a fallback for the physical-Mac launcher's mandatory HVF. The hosted Mac job is a compile check, not a nested virtualization test.

The GitHub repository is `jellydn/try-win11`. Only a real Actions run for the pushed commit is hosted-CI evidence; local checks and an Amp remote push are not substitutes. The recipe tests use synthetic media, subprocesses and local sockets, not Windows or QEMU. Hardware gates remain separate.

Run the same checks locally from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/ci_sources.py
python3 scripts/check_docs.py
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7
```

Python 3.12+ and Go 1.23+ are CI validation tools, not app dependencies; source fetching and its regression tests require safe tar extraction filters. The hosted Mac contract lane selects Python 3.14.8 explicitly (a current patch with a published GitHub ARM64 toolchain build). An installed actionlint 1.7.7 binary can replace the Go command. The workflow lists Ubuntu build dependencies. `bash scripts/ci_build_linux.sh /new/work/path` repeats the diagnostic recipe on Ubuntu; it installs only into that work path. Do not run it as root or reuse VM paths. The macOS-only empty-HVF probe may be run manually on physical hardware using the [developer instructions](developer-boot.md), never by this workflow.

## Artifact boundary

[The package builder](../scripts/ci_package.py) uses an explicit file allowlist, not a repository/workspace glob. It accepts only regular UTF-8 source files up to 1 MiB without NUL bytes and rejects symlinks. Archive timestamps, permissions and owner IDs are fixed; two builds must match. The upload action receives exactly three generated paths, never the working directory, build tree, caches, runner home or logs. No artifact upload runs after failed prerequisite jobs.

Only original project source is uploaded: no downloaded dependency archives, compiled QEMU/swtpm/probe binaries, firmware code or variables, TPM state, VM disk, ISO, WIM, Windows/driver content, credentials or local input manifests. Source-package artifacts are developer review material, not an application release, SBOM for a distribution, or fulfillment of a future combined-runtime source obligation. Changing the upload surface requires editing/reviewing the allowlist. Do not add secrets to tracked source; an allowlist is not a credential scanner.

## Gates hosted CI cannot pass

G1 stays open for physical Apple Silicon HVF execution, the local ISO's authenticity and license rights, Windows installation/OOBE, signed ARM64 drivers, disk/input/NIC, updates, TPM2/Secure Boot persistence, unsigned EFI rejection, two independent operators and three cold boots each. Current physical-Mac storage/provenance blockers remain in the [report](reports/2026-10-19-mac-preflight.md). G2–G5 and the ADR approval gates remain open: no hosted compile proves licensing, source redistribution obligations, SPICE console usability, encrypted restore, Developer ID/notarization or clean-machine distribution. Do not label this matrix a Windows boot lane.

The documentation check covers Markdown, workflow YAML, Python scripts and LICENSE whitespace/newlines/conflict markers. It checks inline relative file links outside fenced examples, including fragment-bearing paths, but does not validate heading fragments, reference-style links or external websites. actionlint validates workflow semantics and embedded shell when ShellCheck is available. Neither check proves Windows boot, HVF access, or macOS signing.

## Oak patterns used

Reviewed [jellydn/oak CI](https://github.com/jellydn/oak/blob/main/.github/workflows/ci.yml), [test-build workflow](https://github.com/jellydn/oak/blob/main/.github/workflows/macos-test-build.yml), and [local hooks](https://github.com/jellydn/oak/blob/main/prek.toml). Reused the design patterns of PR/main checks, read-only permissions, per-PR/ref concurrency, and whitespace/conflict checks. Oak's hygiene hooks are local; running documentation checks and actionlint in Actions is a Try Win11 adaptation, not an existing Oak workflow copied verbatim.

Oak's [test-build history](https://github.com/jellydn/oak/commit/010268346bdc34e316f1b0883661df2da82e7231) and [implementation thread](https://ampcode.com/threads/T-01a07aff-b60d-70d8-a117-b1a4a6ff7ed8) show the useful method: inspect existing workflows, validate locally, run on the target runner, then inspect the actual result/artifact. No Oak-specific app scripts or substantial workflow bodies were copied.

Do not add Pages deployment, release-on-push, Sparkle/Homebrew publishing, write tokens, signing secrets or empty Xcode jobs at this stage.

## Planned macOS checks

When M2/M3 introduces real host harness/app targets, add a separate macOS job with the actual project/scheme and an explicit Xcode version. Follow Oak's strict SwiftLint and unsigned build/test pattern only after those tools and targets exist. Keep PR validation read-only and secret-free. A hosted macOS build is not evidence of working HVF; boot tests need a proven physical M-series lane.

Add downloadable ARM64 test artifacts only when useful: build, sign with the exact HVF entitlement on the QEMU process, verify nested signatures/architecture, package, upload with short retention, and inspect the downloaded artifact. An ad-hoc-signed test bundle is not a notarized release. Do not copy Oak's blanket deep-signing command into the future bundled QEMU release process; sign nested code inside out.

Developer ID signing, notarization and publication remain separately approved M2/M5 work, as described in the [plan](implementation-plan.md). Never automatically publish an app on each documentation push.
