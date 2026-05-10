# Codex Implementer Manifest Schema — Digest

**Consumer**: `/implement` Step 2 — dispatch-time: read manifest shape, validate returned manifests, route bail tokens. Load full `codex-manifest-schema.md` when editing dispatcher validation, implementer prompts, or Steps 4 / 8a / 9a / 9a.1 consumption blocks.

**Contract**: required-keys table, key validation rules, bail-reason token list. Full doc carries examples, atomic-write rule, Edit-in-sync list, and extended validation narrative.

**When to load**: Step 2 entry. Digest suffices for most dispatches. Load the full file when editing dispatcher, implementer prompts, or downstream consumption steps.

---

## Required keys per status

| Field | `complete` | `needs_qa` | `bailed` |
|-------|:----------:|:----------:|:--------:|
| `schema_version` (`"1"`), `status` | req | req | req |
| `files_touched` (`{path, lines_added, lines_removed}[]`) | req, non-empty | opt | opt |
| `tests_added_or_modified` (string[]), `todos_left` (string[]), `oos_observations` (`{title,description,phase}[]`) | req (may be []) | opt | opt |
| `summary_bullets` (string[], 1–5) | req | opt | opt |
| `commit_message` (string, non-empty) | req | opt | opt |
| `bail_reason` (string) | absent/empty | absent/empty | req, non-empty |
| `needs_qa.questions` (`{id,text}[]`) | absent | req, non-empty | absent |

`status` enum: `complete` · `needs_qa` · `bailed`

## Key validation rules

1. `schema_version == "1"`. 2. `status` in enum. 3. Per-status required keys per table; failure → `manifest-schema-invalid`. 4. Paths repo-relative (no `..`, no leading `/`); `.claude-plugin/plugin.json` and submodule paths rejected. 5. On `complete`: dispatcher runs `git add -A && git commit -F <redacted-msg>`. 6. Selected string fields (`summary_bullets`, `commit_message`, `todos_left`, `oos_observations[*].title/description`) are redacted via `scripts/redact-secrets.sh`; `bail_reason` and `needs_qa.questions[*].text` are NOT run through the redactor — see full doc §Sanitization.

## Bail-reason tokens

All tokens route to Step 12d.

**Partial-work group** (branch may be dirty — operator must inspect): `resume-incompatible` · `branch-changed` · `protected-path-modified` · `submodule-dirty` · `commit-failed` · `cursor-modified-history` · `gemini-modified-history`

**Clean-exit group**: `qa-loop-exceeded` · `manifest-schema-invalid` · `manifest-missing` · `qa-pending-missing` · `redactor-not-executable` · `dirty-state-after-timeout` · `wrapper-validation-failure` · `coder-mismatch-tmpdir-reuse` · `codex-runtime-failure` · `cursor-runtime-failure` · `cursor-bailed-no-reason` · `gemini-runtime-failure` · `gemini-bailed-no-reason`

Free-form: any other implementer-authored string; preserved verbatim (KV-sanitized, capped ~200 chars).
