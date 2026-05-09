# Anchor Comment — Execution Issues Format

**Consumer**: `/implement` Step 2 (Q/A progressive `execution-issues` upsert) and Step 11 (post-execution refresh). Load when composing the `execution-issues` anchor section fragment, i.e., wrapping `$IMPLEMENT_TMPDIR/execution-issues.md` content into a `<details>` block and writing it to `$IMPLEMENT_TMPDIR/anchor-sections/execution-issues.md`.

**Contract**: execution-issues anchor section format — the `<details><summary>Execution Issues</summary>` wrapper template and the compose-time sanitization rule (secrets/URL/PII redaction) for Step 2 Q/A entries and Step 11 refresh. Single normative source for how to compose the `execution-issues` section.

**When to load**: at Step 2 before each Q/A entry append + anchor upsert, and when Step 11 refreshes the `execution-issues` section. Do NOT load outside these contexts.

**Sibling files**:
- `anchor-template-canonical-body.md` — canonical template + section markers (Steps 0.5, 11)
- `anchor-template-oos-pipeline.md` — OOS pipeline (Step 9a.1)
- `anchor-template-quick-mode.md` — Quick-mode guidance
- `anchor-comment-template.md` — thin overview

---

## Execution Issues section format

The `execution-issues` section wraps the full contents of `$IMPLEMENT_TMPDIR/execution-issues.md` in a collapsible `<details>` block. Preserve load-bearing blank lines (required for GitHub Markdown rendering inside `<details>` blocks).

Section content template:

```markdown
<!-- section:execution-issues -->
<details><summary>Execution Issues</summary>

<verbatim contents of $IMPLEMENT_TMPDIR/execution-issues.md — categorized entries: Pre-existing Code Issues, Tool Failures, Permission Prompts, External Reviewer Issues, CI Issues, Warnings, Q/A (Step 2 opportunistic questions + mid-coding ambiguity resolutions)>

</details>

<!-- section-end:execution-issues -->
```

The opening `<details><summary>Execution Issues</summary>` line and the closing `</details>` line are required verbatim; the blank line after the opening tag is load-bearing for GitHub Markdown.

## Compose-time sanitization rule

Every fragment composed into the anchor-comment body must apply prompt-level sanitization at compose time, parallel to the rule stated in `skills/implement/SKILL.md` "Execution Issues Tracking" section:

- Redact session tmpdir paths → `<TMPDIR>`.
- Redact secrets / API keys / OAuth / JWT / passwords / certificates → `<REDACTED-TOKEN>`.
- Internal hostnames / URLs / private IPs → `<INTERNAL-URL>`.
- PII (emails, names, account IDs linked to a real user) → `<REDACTED-PII>`.

This is a defense-in-depth layer above `scripts/redact-tmpdir-paths.sh` and `scripts/redact-secrets.sh`'s outbound scrubbers: the scrubbers catch session tmpdir paths and covered token families mechanically, but internal URLs and PII are out of their coverage and MUST be sanitized at compose time. `tracking-issue-write.sh`'s structural choke point (compose → redact → truncate) ensures no bypass path exists, but it does NOT invent redactions the helpers do not cover — compose-time prompt-level sanitization is the first and primary defense for those classes.
