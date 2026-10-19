# Continuous integration

## Current checks

[CI](../.github/workflows/ci.yml) runs on pull requests, pushes to `main`, and manual dispatch. One Linux job checks text hygiene, inline relative Markdown file links, and GitHub Actions syntax with actionlint 1.7.7. It has read-only permissions, no secrets, no publication steps, a ten-minute timeout, and cancellation of obsolete runs for the same PR/ref. Checkout is pinned to an immutable revision and does not retain credentials.

The repository currently uses an Amp-hosted Git remote. GitHub Actions will execute only when these files are pushed to a GitHub repository with Actions enabled. A push to the Amp remote is not a hosted Actions run; run the checks locally until a GitHub remote or mirror is configured.

Run the same checks locally from the repository root:

```bash
python3 scripts/check_docs.py
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7
```

Python 3.9+ and Go 1.23+ are validation tools, not app dependencies. An installed actionlint 1.7.7 binary can replace the Go command. The Linux runner supplies Python and Go; no package manifest or app toolchain is needed yet.

The documentation check covers Markdown, workflow YAML, Python scripts and LICENSE whitespace/newlines/conflict markers. It checks inline relative file links outside fenced examples, including fragment-bearing paths, but does not validate heading fragments, reference-style links or external websites. actionlint validates workflow semantics and embedded shell when ShellCheck is available. Neither check proves Windows boot, HVF access, or macOS signing.

## Oak patterns used

Reviewed [jellydn/oak CI](https://github.com/jellydn/oak/blob/main/.github/workflows/ci.yml), [test-build workflow](https://github.com/jellydn/oak/blob/main/.github/workflows/macos-test-build.yml), and [local hooks](https://github.com/jellydn/oak/blob/main/prek.toml). Reused the design patterns of PR/main checks, read-only permissions, per-PR/ref concurrency, and whitespace/conflict checks. Oak's hygiene hooks are local; running documentation checks and actionlint in Actions is a Try Win11 adaptation, not an existing Oak workflow copied verbatim.

Oak's [test-build history](https://github.com/jellydn/oak/commit/010268346bdc34e316f1b0883661df2da82e7231) and [implementation thread](https://ampcode.com/threads/T-01a07aff-b60d-70d8-a117-b1a4a6ff7ed8) show the useful method: inspect existing workflows, validate locally, run on the target runner, then inspect the actual result/artifact. No Oak-specific app scripts or substantial workflow bodies were copied.

Do not add Pages deployment, release-on-push, Sparkle/Homebrew publishing, write tokens, signing secrets or empty Xcode jobs at this stage.

## Planned macOS checks

When M2/M3 introduces real host harness/app targets, add a separate macOS job with the actual project/scheme and an explicit Xcode version. Follow Oak's strict SwiftLint and unsigned build/test pattern only after those tools and targets exist. Keep PR validation read-only and secret-free. A hosted macOS build is not evidence of working HVF; boot tests need a proven physical M-series lane.

Add downloadable ARM64 test artifacts only when useful: build, sign with the exact HVF entitlement on the QEMU process, verify nested signatures/architecture, package, upload with short retention, and inspect the downloaded artifact. An ad-hoc-signed test bundle is not a notarized release. Do not copy Oak's blanket deep-signing command into the future bundled QEMU release process; sign nested code inside out.

Developer ID signing, notarization and publication remain separately approved M2/M5 work, as described in the [plan](implementation-plan.md). Never automatically publish an app on each documentation push.
