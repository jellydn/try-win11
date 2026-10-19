# Contributing

This repository contains a proposal only. Do not start the full UI before the boot and packaged-runtime gates pass.

1. Read [CONTEXT.md](CONTEXT.md), the [plan](docs/implementation-plan.md), and the relevant proposed ADR.
2. Original contributions use the [MIT license](LICENSE). Preserve third-party notices and terms. The maintainer names gate owners before implementation begins.
3. Take a task ID from the plan. State its inputs, output, acceptance test, and dependencies. Keep the first work focused on milestone 1.
4. Record exact dependency versions, source revisions, patches, build flags, checksums, and license notices. Do not use `latest` URLs as release inputs.
5. Submit small changes with reproducible commands and sanitized evidence. Distinguish a documentation claim, an upstream result, and a Try Win11 hardware result.
6. Record a human decision at each gate. Update an ADR when evidence changes the proposed design.

## Testing and reports

There are no product tests or build commands yet. Run `python3 scripts/check_docs.py` and actionlint as described in [CI checks](docs/ci.md) before submitting changes. Do not add a passing placeholder app build. Use the [boot work order](docs/boot-milestone.md) for the first hardware tests. The plan defines later test layers.

A useful VM failure report includes Mac model/chip, RAM, macOS build, Windows build/edition, runtime manifest ID, last successful step, expected and actual results, and sanitized logs. Remove account names, paths with personal data, tokens, keys, guest files, and TPM state. Never upload a Windows ISO or installed Windows disk with a public issue.

Treat a guest as untrusted. Keep shared folders, clipboard, microphone, and inbound network services off unless the test requires them. Request consent before destructive guest recovery, state reset, data deletion, signing submissions, or publication.
