# lint-mermaid-fences.sh contract

## Purpose

Extract top-level ```` ```mermaid ```` fences from Markdown files and validate each fence with Mermaid CLI (`mmdc`). This is the broad syntax backstop for Mermaid classes outside the narrow write-time sanitizer.

## Interface

```
lint-mermaid-fences.sh <file.md> [<file.md> ...]
lint-mermaid-fences.sh --changed-only
```

`--changed-only` computes a Markdown changed-file set from CI context:

- pull requests: `origin/${GITHUB_BASE_REF}...HEAD` after a shallow base fetch;
- pushes: `${GITHUB_EVENT_BEFORE}..${GITHUB_SHA}`, falling back to `HEAD~1..HEAD`;
- local or workflow dispatch: `origin/main...HEAD`, or a no-op if `origin/main` is unavailable.

Pre-commit passes filenames directly and does not use `--changed-only`.

## Mermaid CLI Resolution

The script prefers `./node_modules/.bin/mmdc` resolved from the repo root, then falls back to `command -v mmdc`. If neither exists, it exits 2 with a missing-toolchain error so CI can distinguish setup failure from parse failure.

This repo pins `@mermaid-js/mermaid-cli` in `package.json`. Version 11.12.0 documents `mmdc` as the package bin and depends on Mermaid 11.x. The script probes `mmdc --help` for `--parseOnly`; when supported, it uses parse-only mode. Otherwise it renders to a temp `.svg` file because `mmdc` rejects extension-less outputs.

## Chromium sandbox workaround

When the script falls back to the SVG-render path (mmdc 11.x without `--parseOnly`), it forwards a repo-pinned puppeteer config via `--puppeteerConfigFile scripts/lint-mermaid-puppeteer.json`. The config passes `--no-sandbox` and `--disable-setuid-sandbox` to Chromium so the renderer launches on Ubuntu 23.10+ runners with restricted unprivileged user namespaces (otherwise puppeteer aborts with `[FATAL:zygote_host_impl_linux.cc] No usable sandbox!` before reaching any Mermaid syntax check). The config file is checked in alongside the script for auditability; if it is missing the script silently degrades to the un-flagged invocation (preserving older-runner behavior). macOS runners ignore `--no-sandbox` harmlessly.

## Fence Extraction

The extractor is a fenced-block state machine:

- A top-level Mermaid fence opens only on a column-0 backtick run of length 3 or more whose info string is `mermaid`.
- Any other column-0 backtick fence at top level opens an outer documentation fence.
- A fence closes only on a column-0 backtick run at least as long as the opener with whitespace-only remainder.
- Mermaid examples nested inside larger documentation fences are ignored.

This prevents large fenced documentation examples inside quadruple-backtick documentation fences from being linted as real diagrams.

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | All extracted fences parsed |
| 1 | One or more fences failed Mermaid CLI validation |
| 2 | Mermaid CLI missing |

## Edit-in-sync

Update `.pre-commit-config.yaml`, `.github/workflows/ci.yaml`, `package.json`, and `scripts/test-mermaid-fragments.sh` when changing this contract.
