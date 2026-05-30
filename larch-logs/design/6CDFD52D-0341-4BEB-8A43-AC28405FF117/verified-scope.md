## VERIFIED SCOPE — checked against latest main (924345fba) on 2026-05-29

Issue #3120 (Breadcrumbs Deprecation Stage 5) was specced before Stages 1–4
(#3116–#3119) landed. A pre-design verification against latest main found that
3 of the 6 originally-scoped surfaces are ALREADY IMPLEMENTED. The operator
confirmed the refined scope: plan ONLY the genuinely-remaining items below.

Breadcrumb rip is complete: breadcrumb-monitor.sh, lib-redact-streaming.sh,
lint-foreground-markers.sh, emit_breadcrumb (lib-quiet.sh), and BASH_AUTHORING.md
§4 are all removed. The only surviving LARCH_BREADCRUMB* refs are the committed
forensics bridge in larch-log.sh/.md (intentionally preserved). Blocker
"Piece 4" (#3119) is DONE. #3063 Cluster 1 (breadcrumb-pipeline items) is moot.

### Already implemented — OUT OF SCOPE (do NOT re-plan these):
- `scripts/test-design-log-publish.sh` render-cache symlink harness — DONE
  (root / dangling-root / leaf / intermediate / race symlink rejection,
  lines ~978–1057).
- `SECURITY.md` render-cache hardening language — DONE (line ~207 documents the
  render-cache policy). EXCEPTION: its "Parent-directory replacement races … are
  not fully closed" caveat must be UPDATED by item A below if the race is closed.
- `scripts/test-mermaid-fragments.sh` + `.md` embedded-`=` regression — DONE
  (lines ~241–246, "warnings-token aggregation preserves embedded equals").

### Genuinely remaining — IN SCOPE:

**A. `scripts/design-log-publish.sh` parent-directory (ancestor) symlink TOCTOU rescan.**
Current state: symlink rejection, `find -type l` tree scan, path-escape `case`,
and per-file *leaf* `-L` recheck are all present for the plan-review, render-cache,
and `.completed` subtrees. Remaining gap (documented at `SECURITY.md:~207` as a
known limitation): a parent directory under the resolved physical root can be
swapped for a symlink AFTER the `find -type l` scan and BEFORE staging; the
per-file `-L "$f"` recheck catches only the leaf, not an ancestor. Close this with
an ancestor rescan at/just-before staging for all three subtrees. Then update the
`SECURITY.md` caveat and add an ancestor-race harness case to
`scripts/test-design-log-publish.sh`.

**B. `scripts/lib-quiet.sh` `sanitize_diagnostic_line` passthrough audit.**
`sanitize_diagnostic_line` exists (`lib-quiet.sh:86`) but is opt-in; `larch_err`
does not auto-sanitize (by design). Audit external-content passthrough call sites
that forward into `larch_err` / `larch_errf` and route high-risk ones through
`sanitize_diagnostic_line`. Record the audit outcome in `scripts/lib-quiet.md`.

**C. `scripts/ship-pr.sh` fallback-relay control-byte sanitization.**
`append_tool_failure_local`'s fallback relay (`ship-pr.sh:~894–901`) pipes the
captured failure log through `redact-secrets.sh` but NOT
`sanitize_diagnostic_line`, so C0 control bytes from CI/vendor stderr can still
reach operator-visible stderr. Add per-line control-byte sanitization on top of
the existing secret redaction, and add `scripts/test-ship-pr.sh` coverage.
