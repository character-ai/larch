# fluff-analysis.py contract

`skills/fluff-analysis/scripts/fluff-analysis.py` is the analyzer behind the
`/fluff-analysis` skill. Stdlib-only Python 3; run directly (no imports of this
module elsewhere — the hyphenated filename is intentional for a standalone
script).

## Purpose

Read committed larch run logs and print a markdown **review fluff** report:
acceptance baselines, low-acceptance semantic groups, a testing breakdown,
severity/quality/uncertain correlations, reviewer-lane splits, an
accepted-but-low-value proxy, an optional pre/post-cutoff comparison, and
data-driven recommendations.

## Inputs

- `larch-logs/implement/<run>/review-findings-full.jsonl` (+ per-round
  `round-*/findings-classification.tsv` for voter severity ratings).
- `larch-logs/design/<run>/**/findings-classification.tsv` joined with the
  sibling `findings.md` for content.
- `larch-logs/design/<run>/manifest.json` for manifest-enumerated guideline
  assessment coverage. This scan reads
  `architectural-guideline-assessment.md` independently of
  `findings-classification.tsv`.
- Optional (`--include-in-progress`): in-progress `/design` session temp dirs
  under `--sessions-dir` (default `~/.cache/larch/sessions`), keyed on
  `voting-tally.md`. Racy snapshot; off by default.

All parsers are defensive against format drift (the corpus spans many plugin
versions): missing fields degrade to empty, never crash a run.

## CLI

```text
--log-root DIR            larch-logs dir (default: <git toplevel>/larch-logs)
--include-in-progress     also read in-progress design session temp dirs
--sessions-dir DIR        session cache dir (default: ~/.cache/larch/sessions)
--inprogress-since ISO    skip in-progress sessions older than this mtime
--cutoff ISO8601          enable a pre/post comparison split at this time
--min-group N             min findings for a group to appear (default 20)
--out FILE                write report to FILE instead of stdout
```

## Output / exit codes

- Markdown to stdout (or `--out FILE`), beginning with `# Review Fluff Analysis`.
- Exit `0` on success; exit `2` when `--log-root` does not exist.

## Invariants

- Keyword tags are multi-label and **directional**; severity and outcome cuts
  are exact. The report states this — do not present tags as exact.
- Design analysis splits in-scope findings (`FINDING_*`) from OOS proposals
  (`OOS_*`). Implement uses the three-way `accepted` / `out_of_scope` /
  `rejected` outcome directly.
- Guideline assessment coverage is emitted from design run manifests even when
  no in-scope review findings exist. Clean assessment classification uses
  `body.rstrip("\n") == CLEAN_PRESENTATION_NOTE`, matching `audit-runs`.
- `accepted` is the only positive outcome; `exonerated` / `neutral` /
  `rejected` are all "not accepted" for design rate math.

## Harness

`skills/fluff-analysis/scripts/test-fluff-analysis.sh` (via
`make test-fluff-analysis`) runs the analyzer over a synthetic fixture and
asserts the report shape, the `--cutoff` section, and the missing-log-root exit
code. Skill-local Python is not covered by `make py-lint` (scoped to `python/`).
## Concise prune/log audit update

`--since-version X.Y.Z` bins committed runs by `manifest.json.larch_version` and prefers version mode over timestamp cutoff. Implement pre/post output includes per-severity acc/OOS/reject rows, accepted-low-value, tier composition, and reports malformed or missing versions as skipped.
