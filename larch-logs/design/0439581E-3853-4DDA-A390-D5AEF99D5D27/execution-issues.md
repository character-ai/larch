### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and inspecting the cited code paths.
Checking whether new tests require shard-assignment updates and scanning for other plan gaps.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
⏳ cursor agent: still running (8m elapsed)
⏳ cursor agent: still running (9m elapsed)
⏳ cursor agent: still running (10m elapsed)
⏳ cursor agent: still running (11m elapsed)
✓ cursor agent: completed (exit code 0, output 519 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	docs/configuration-and-permissions.md:266-268	`LARCH_REVIEWER_PRUNE` docs keep the old zero-accepted pruning rule	The plan updates `docs/point-competition.md`, but the canonical env-var docs would still tell users that rounds 3-4 skip only combos with zero accepted findings, contradicting the proposed precision-aware behavior for the same knob	Update this paragraph to describe net score ≤ 0 or acceptance rate below 1/3 over the last two launched rounds, while preserving the `off` override semantics.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/codex-primary-plan-requirements-output.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
✓ codex agent: completed (exit code 0, output 630 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt)

Reviewing round-window aggregation and predicate math in the codebase; searching for the relevant implementation and tests.
**Verdict:** The predicate math in `reviewer_prune_filter` and `voting.classify_result` matches the documented contract when the ledger is populated. Round 5 and `LARCH_REVIEWER_PRUNE=off` correctly bypass pruning. Two integration gaps break zero-yield history for rounds 3–4 pruning in production paths.

---

## Round-window aggregation (pruning)

**Contract** (`docs/configuration-and-permissions.md:268`, `docs/point-competition.md:72`): rounds 3–4 drop combos with **zero accepted findings** in their **last two launched rounds**.

**Implementation** (`python/review_pipeline.py`):

```405:458:python/review_pipeline.py
def _ledger_history(path: Path, round_num: int) -> dict[str, dict[int, int]]:
    ...
            if r >= round_num:
                continue
            key = f"{row.get('tool', '')}:{row.get('slot', '')}"
            per = hist.setdefault(key, {})
            per[r] = max(per.get(r, count), count)
    return hist

def reviewer_prune_filter(ledger: Path, round_num: int, manifest: Path, out: Path) -> PruneFilterResult:
    ...
    if prune_active == "false" or round_num <= 2 or round_num >= 5:
        ...
        shutil.copyfile(manifest, out)
        return PruneFilterResult(...)
    ...
        recent = sorted(hist.get(key, {}).items())[-2:]
        if len(recent) >= 2 and all(count == 0 for _, count in recent):
            pruned.append(key)
```

| Case | Behavior | Evidence |
|------|----------|----------|
| **< 2 ledger rows** | Not pruned | `len(recent) >= 2` guard at `review_pipeline.py:448` |
| **Last 2 rows all `accepted_count == 0`** | Pruned | `all(count == 0 ...)` at `448-449` |
| **Any accepted in window** | Kept | e.g. `[(1,0),(2,1)]` fails `all(count == 0)` |
| **Fail-open on bad ledger** | Unpruned manifest copied | `except` path at `438-442` |

**Recording predicate** — only `voting_result == "accepted"` rows count (`review_pipeline.py:348-359`). Neutral and rejected classification rows contribute **0** to `accepted_count`. That matches “zero accepted findings.”

**Tests:** `test_reviewer_prune_record_and_filter_round_three` (`python/test_review_pipeline.py:515-553`) and `test_panel_dispatch_prunes_round_three_empty_panel` (`python/test_plan_review_panel.py:245-281`) seed two zero rounds and assert full prune at round 3.

---

## Voting predicate math (1/3, neutral, rejected)

**Thresholds** (`python/voting.py:245-270`, `docs/voting-process.md:18-29`):

```245:270:python/voting.py
def accept_finding(yes: int, no: int, exonerate: int, eligible: int) -> bool:
    ...
    if eligible == 1:
        return yes == 1
    if eligible == 2:
        return yes == 2
    return yes >= 2

def classify_result(yes: int, no: int, exonerate: int, eligible: int) -> str:
    ...
    if accept_finding(yes, no, exonerate, eligible):
        return "accepted"
    if yes > 0:
        return "neutral"
    return "rejected"
```

| Scenario (`eligible=3`) | YES | Result | Evidence |
|-------------------------|-----|--------|----------|
| **Exact 1/3** | 1 | `neutral` | `test_voting.py:31-32` |
| **0/3** | 0 | `rejected` | `test_voting.py:33` |
| **2/3** | 2 | `accepted` | `test_voting.py:30` |

**Downstream handling** (`python/review_tally.py:571-600`):
- `neutral` → `REJECTED_COUNT`++, `NEUTRAL_COUNT`++, rejected file with subtype `"neutral (YES below acceptance threshold)"`
- `rejected` → rejected file with `"dismissed (0 YES)"`
- Plan review: 1 YES / 2 NO on `FINDING_2` lands in `rejected-findings.md` (`test_plan_review.py:708-732`)

---

## Round 5 and off-knob bypass

**Three independent bypass layers:**

1. **Filter early exit** — `round_num <= 2 or round_num >= 5` copies manifest unchanged (`review_pipeline.py:432-435`).
2. **Dispatch gating** — `prune_window_evaluated` is `"true"` only for rounds 3–4 (`review_pipeline.py:497-498`); dispatch forces `prune_active = "false"` otherwise (`1013`).
3. **Design panel** — `_filter_pruned` returns manifest unmodified when `prune_round_num not in {3, 4}` (`plan_review_panel.py:227-228`).

**Off knob** — exact `LARCH_REVIEWER_PRUNE=off` sets `prune_active = "false"` and skips history evaluation (`review_pipeline.py:428-435`). Non-`off` values warn and leave pruning enabled (`430-431`).

`derive_prune_status` maps non-evaluated rounds to `"skipped"` (`review_pipeline.py:486-487`).

---

## Findings


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt)

**Findings**

- **[P1] Native `/design` pruning has no ledger writer.**  
  `plan_review_panel._filter_pruned()` reads `reviewer-prune-ledger.tsv` for rounds 3 and 4, then fail-opens on helper failure. But the native plan-review round writes the classification and proceeds to status handling without recording prune history. The only in-process recorder shown is the code-review path, not the plan-review path. This means `/design` rounds 3 and 4 may keep every reviewer because the ledger never learns prior accepted counts.  
  **Evidence:** `python/plan_review_panel.py:226-255`, `python/plan_review.py:1154-1169`, `python/plan_review_round.py:490-507`, `python/plan_review_round.py:524-549`, `python/review_pipeline.py:1618-1628`.

- **[P2] Code-review zero-finding rounds do not record zero accepted counts.**  
  `_zero_findings_branch()` records the classification path, emits tally artifacts, then returns without `_record_prune_round()`. The caller returns immediately for `FINDINGS_COUNT=0` and `MERGED_COUNT=0`. A header-only classification would otherwise produce zero-count ledger rows for every manifest row. This breaks the “zero findings means zero accepted in the window” case.  
  **Evidence:** `python/review_pipeline.py:341-360`, `python/review_pipeline.py:392-402`, `python/review_pipeline.py:1697-1759`, `python/review_pipeline.py:1964-1967`, `python/review_pipeline.py:2000-2002`.

**Verified OK**

- **Exact 1/3 acceptance:** `eligible == 1` accepts `yes == 1`, and accepted rows count toward pruning. See `python/voting.py:245-270` and `python/review_pipeline.py:341-360`.
- **Neutral and rejected rows:** non-`accepted` `voting_result` rows are skipped for prune counts. See `python/review_pipeline.py:347-350`.
- **Round 5 and `off`:** both bypass pruning by copying the manifest unchanged. See `python/review_pipeline.py:423-435`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-precision-prune-correctness.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 1863 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt)

Searching the codebase for ledger writer/reader, rewrite paths, and plan-review fixtures.
**Verdict:** Filter-side fail-open is implemented in `review_pipeline.py` and mirrored in `plan_review_panel.py`, but **ledger recording is incomplete** on both `/design` and `/implement` zero-findings paths, **`ensure_reviewer_prune_ledger` is dead code**, and **harness coverage is far below what `docs/linting.md` claims**.

---

## Ledger writer (`reviewer_prune_record`)

**Behavior:** Builds rows from manifest + classification, then atomically rewrites the ledger for that round.

```392:402:python/review_pipeline.py
def reviewer_prune_record(ledger: Path, round_num: int, manifest: Path, classification: Path, label_map: Path | None = None) -> None:
    rows = _manifest_rows(manifest)
    label_mp = _read_label_map(label_map)
    plan_mode = bool(label_mp)
    slot_labels = [(row, label_mp.get(str(row.get("slot") or ""), _output_label(row))) for row in rows]
    counts = _read_classification_counts(classification, [label for _, label in slot_labels], plan_mode=plan_mode)
    ledger_rows = [
        [str(round_num), str(row.get("tool") or ""), str(row.get("slot") or ""), label, str(counts.get(label, 0))]
        for row, label in slot_labels
    ]
    _rewrite_prune_ledger(ledger, round_num, ledger_rows)
```

**Call sites today:**
- `/implement` settled rounds via `_record_prune_round` (`review_pipeline.py:1618-1628`, `2058`, `2064`)
- `/implement` zero-row clear via `review_and_fix._clear_reviewer_prune_round` (`review_and_fix.py:1230-1241`)
- **No `/design` call site** — `plan_review_round.execute_round` ends after tally with no `reviewer_prune_record` (`plan_review_round.py:503-559`)

**Record fail-soft (not fail-open):** exceptions become `WARN`, round continues.

```1618:1628:python/review_pipeline.py
def _record_prune_round(prune_ledger: str, round_num: int, panel_manifest: str, classification_file: str) -> None:
    ...
    try:
        reviewer_prune_record(Path(prune_ledger), round_num, manifest, classification)
    except Exception as exc:
        _emit_kv("WARN", f"reviewer-prune record failed for round {round_num}: {exc}")
```

---

## Ledger reader (`_ledger_history` / `reviewer_prune_filter`)

**Strict read:** requires `round`, `tool`, `slot`, `accepted_count`; missing columns raise.

```405:420:python/review_pipeline.py
def _ledger_history(path: Path, round_num: int) -> dict[str, dict[int, int]]:
    ...
        required = {"round", "tool", "slot", "accepted_count"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("missing ledger columns")
```

**Fail-open on filter (contract):** any read/parse failure copies the unfiltered manifest, disables pruning, emits `PRUNE_FAIL_OPEN=true`.

```436:442:python/review_pipeline.py
    try:
        hist = _ledger_history(ledger, round_num)
    except Exception as exc:  # fail open by contract
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest, out)
        fail_warn = f"reviewer-prune: fail-open ledger read failed: {exc}"
        return PruneFilterResult("false", len(rows), 0, "", "false", "true", fail_warn)
```

**Off switch:** only exact `LARCH_REVIEWER_PRUNE=off` disables; other values warn and leave pruning on (`review_pipeline.py:425-431`). Documented at `docs/configuration-and-permissions.md:266-268`.

**Malformed/old-schema outcomes on filter:**

| Ledger state | Filter behavior |
|---|---|
| Missing file | `FileNotFoundError` → fail-open |
| Empty / header-only | `fieldnames` None → `ValueError` → fail-open |
| Wrong/missing columns | `ValueError("missing ledger columns")` → fail-open |
| Non-integer `round` / `accepted_count` | `ValueError` from `int()` → fail-open |

---

## Rewrite path (`_rewrite_prune_ledger`)

**Per-round replace:** keeps rows for other rounds, drops current round, atomic `mkstemp` + `os.replace`.

```363:389:python/review_pipeline.py
def _rewrite_prune_ledger(path: Path, round_num: int, new_rows: list[list[str]]) -> None:
    ...
                try:
                    if int(row[0]) == round_num:
                        continue
                except ValueError:
                    continue
                if len(row) >= 5:
                    old_rows.append(row[:5])
    ...
            writer.writerow(["round", "tool", "slot", "label", "accepted_count"])
            writer.writerows(old_rows)
            writer.writerows(new_rows)
        os.replace(tmp, path)
```

**Malformed-row handling on write (silent, not fail-open):**
- Non-integer `round` → row skipped (`375-376`)
- `< 5` columns → row dropped (`377-378`)
- Extra columns → truncated to 5 (`378`)
- Missing/wrong header on read → not repaired here; rows still processed if they look numeric

**Unused repair helper:** `ensure_reviewer_prune_ledger` would rewrite a bad/missing header (`501-513`), but **has zero production callers** (grep finds only its definition).

---

## Plan-review integration and fixtures

**Filter wired:** `plan_review_panel._filter_pruned` calls `review reviewer-prune filter` on rounds 3–4 (`plan_review_panel.py:226-262`).

**Panel fail-open on CLI failure:**

```253:254:python/plan_review_panel.py
    if proc.returncode != 0:
        return manifest, {"PANEL_PRUNED_EMPTY": "false", "PRUNED_COUNT": "0", "PRUNE_FAIL_OPEN": "true"}
```

**Fixture seeds ledger manually** (not via `record`):

```257:260:python/test_plan_review_panel.py
    ledger_lines = ["round\ttool\tslot\tlabel\taccepted_count"]
    for round_num in (1, 2):
        ledger_lines.extend(f"{round_num}\t{tool}\t{slot}\t{slot}\t0" for tool, slot in rows)
    _ = (design / "reviewer-prune-ledger.tsv").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
```

**Label-map fixture** exists only for `compose-findings`, not `reviewer-prune record`:

```248:260:python/test_compose_review.py
def test_compose_findings_prune_label_map_normalizes_reviewer_slots(tmp_path: Path) -> None:
    ...
    _ = (design / "plan-review-prune-label-map.tsv").write_text(
        "cursor-plan-arch\tCursor-Arch\n",
```

---

## Cross-run migration / env knobs

**No cross-run migration:** ledgers are per-run (`IMPLEMENT_TMPDIR/reviewer-prune-ledger.tsv`, `DESIGN_TMPDIR/reviewer-prune-ledger.tsv`). No code upgrades an old ledger schema on read across runs.

**No new env knob:** only pre-existing `LARCH_REVIEWER_PRUNE` (`review_pipeline.py:425`). No ledger-schema or migration env var added.

**Implement bootstrap:** touches empty ledger, does not write header (`review_and_fix.py:2304-2306`). Empty file triggers filter fail-open on rounds 3–4 (all-eligible), which is safe but means pruning never activates without prior `record` rows.

---

## Issues (with evidence)


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt)

**Findings**

- **P1: Native `/design` plan-review never records the prune ledger.**  
  `panel-dispatch` reads `${design}/reviewer-prune-ledger.tsv` for pruning, but `execute_round()` only writes `findings-classification.tsv` and returns. It does not call `reviewer_prune_record`. The fixture seeds the ledger manually, so it does not cover the real writer path. Real native rounds 3-4 will fail-open from a missing/empty ledger and never prune.  
  Evidence: `python/plan_review_panel.py:226-247`, `python/plan_review_round.py:499-558`, `python/test_plan_review_panel.py:257-260`.

- **P2: Old-schema or malformed ledgers can be silently rewritten into the new schema.**  
  `_ledger_history()` fail-opens when required columns are missing. But `record` calls `_rewrite_prune_ledger()`, which preserves any existing row with a numeric first column and at least five cells, without validating the existing header. It then writes the current header over those preserved rows. That can turn an old/malformed ledger into a valid-looking current ledger instead of forcing fail-open.  
  Evidence: `python/review_pipeline.py:363-386`, `python/review_pipeline.py:392-402`, `python/review_pipeline.py:405-442`.

**Checked**

- **Standalone filter fail-open exists.**  
  Malformed/missing ledger reads raise through `_ledger_history()` and are caught by `reviewer_prune_filter()`, which copies the unpruned manifest and returns `PRUNE_FAIL_OPEN=true`.  
  Evidence: `python/review_pipeline.py:405-442`, `python/review_pipeline.py:578-588`.

- **No new env knob found.**  
  The only prune override I found is existing `LARCH_REVIEWER_PRUNE`.  
  Evidence: `python/review_pipeline.py:425-431`, `docs/configuration-and-permissions.md:266-268`.

- **No cross-run import/migration path found.**  
  The active paths use the per-run tempdir ledger and flush it as a replace batch. I did not find a path that reads committed prior-run ledgers back into a new run.  
  Evidence: `python/plan_review_panel.py:226-247`, `python/review_and_fix.py:2304-2309`, `python/run_logs.py:70-73`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-ledger-schema-risk.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
✓ codex agent: completed (exit code 0, output 2070 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and tracing the cited code paths.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
✓ cursor agent: completed (exit code 0, output 421 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt)

Reviewing the plan and tracing the cited code paths for precision-based pruning.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 425 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and inspecting the cited codebase paths.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 428 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt)

Reviewing the plan and tracing the pruning logic in the codebase.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-5/cursor-plan-innovation-output.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 409 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt)

Reading the plan and the code paths it cites.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
✓ cursor agent: completed (exit code 0, output 390 bytes)
  ```
### 1. **Critical — `/design` never records ledger rows**

`plan_review_round.execute_round` runs panel → collect → tally but never calls `reviewer_prune_record`. Filter on rounds 3–4 reads a missing/empty ledger and fail-opens to full panel every time.

- Missing record: `plan_review_round.py:503-559` (no prune record call)
- Filter reads ledger: `plan_review_panel.py:239-240`
- Contract says settled rounds should record: `skills/design/references/plan-review.md:63`

### 2. **Important — `/implement` zero-findings rounds skip ledger record**

`_zero_findings_branch` writes classification but never calls `_record_prune_round`, so rounds 1–2 with zero findings leave no strike history for round 3 pruning.

```1726:1759:python/review_pipeline.py
    classification = tally.get("FINDINGS_CLASSIFICATION_TSV_FILE", "")
    _record_classification(review_tmpdir, round_num, classification)
    ...
    _flush_round_log(review_tmpdir, run_id, round_num)
    _emit_core_common("zero-findings", round_num, review_tmpdir, panel_mode, panel_shape)
```

Compare settled-path record at `2064`.

### 3. **Important — `ensure_reviewer_prune_ledger` is dead code**

Defined at `review_pipeline.py:501-513`, never called from production Python or shell. Old-schema header repair on startup does not run.

### 4. **Important — Harness/docs overclaim coverage**

`docs/linting.md:308` says `make test-reviewer-prune` covers “ledger recording, exact attribution, per-round replacement, fail-open filtering, the off switch, and all-pruned markers.”

Actual `test-reviewer-prune` target:

```166:167:Makefile
test-reviewer-prune:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k reviewer_prune
```

Only one matching test: `test_reviewer_prune_record_and_filter_round_three` (`test_review_pipeline.py:515-553`). **No tests for:**
- corrupt/malformed ledger fail-open
- `LARCH_REVIEWER_PRUNE=off` / non-`off` warning
- per-round replace-rewrite (re-record same round)
- plan `label-map` / `finding_reviewers` tokenization
- `derive_prune_status` / `normalize_prune_eligible` / `prune_window_evaluated` / `write_prune_decision_env`

`test-lib-prune-decision` runs `pytest -k 'prune and not reviewer_prune'` (`Makefile:169-170`), which hits prune-nit / review-core tests, not prune-decision helpers.

### 5. **Minor — fail-open subprocess path leaves stale `pre-prune` sidecar**

`_filter_pruned` always writes `plan-review-slots.pre-prune.ndjson` before filter (`plan_review_panel.py:231`), but on `proc.returncode != 0` returns early without unlinking it (`253-254`), unlike the `pruned_count == 0` cleanup at `257-259`.

### 6. **Minor — stale migration doc**

`docs/python-migration.md:151` still describes gzip-embedded plan-review assets and `_LEGACY_ASSETS`; `test_plan_review.py:10-12` asserts those are removed and plan-review is native.

---

## Fail-open summary

| Path | Fail-open? | Evidence |
|---|---|---|
| **Filter** (malformed/missing/old-schema ledger) | **Yes** | `review_pipeline.py:436-442`, `586-587` |
| **Filter** (`LARCH_REVIEWER_PRUNE=off`) | **Yes** (skip pruning) | `review_pipeline.py:428-435` |
| **Panel wrapper** (CLI rc ≠ 0) | **Yes** | `plan_review_panel.py:253-254` |
| **Record** | **Soft-fail** (WARN, no abort) | `review_pipeline.py:1625-1628` |
| **Rewrite** (malformed old rows) | **Silent drop**, not fail-open | `review_pipeline.py:372-378` |
| **Header repair** | **Not exercised** | `ensure_reviewer_prune_ledger` unused |

---

## Bottom line

- **Reader/filter fail-open:** implemented and consistent with contract.
- **Writer/rewrite:** atomic per-round replace is sound; write-side silently drops bad historical rows.
- **Gaps:** `/design` record missing, `/implement` zero-findings record missing, `ensure_reviewer_prune_ledger` unwired, fixtures/tests do not match documented harness scope.
- **Migration/env:** no cross-run migration; no new env knob beyond existing `LARCH_REVIEWER_PRUNE`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-ledger-schema-risk.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 11458 bytes)
  ```
### FINDING_1: Zero-findings rounds do not record prune ledger (implement/review)

**Severity:** important  
**Concern:** `_zero_findings_branch` records classification but never calls `_record_prune_round`, so launched combos that produce no findings leave no ledger rows. Round-3 filter sees `len(recent) < 2` and keeps them, violating “zero accepted in last two launched rounds.”

**Evidence:**
- `_record_prune_round` only called from normal tally path (`review_pipeline.py:2058, 2064`), not from `_zero_findings_branch` (`1677-1759`)
- `_SETTLING_CORE_STATUSES` includes `"zero-findings"` (`review_and_fix.py:45`), so Step 5 does **not** clear the gap via `_clear_reviewer_prune_round` (`2349-2350`)

**Suggested fix:** Pass `prune_ledger` / `panel_manifest` into `_zero_findings_branch` and call `_record_prune_round` after `_record_classification` when the classification TSV exists (or synthesize a header-only TSV).

---

### FINDING_2: Design plan-review never records prune ledger

**Severity:** important  
**Concern:** Native `plan_review_round.execute_round` runs panel filter (`plan_review_panel._filter_pruned`) but never calls `reviewer-prune record` after tally. Rounds 1–2 history is not written unless externally seeded (as in tests).

**Evidence:**
- `execute_round` ends after tally/summary with no prune-record call (`plan_review_round.py:309-559`)
- Only prune **filter** reference in design Python is `plan_review_panel.py:237-240`
- Test manually seeds ledger (`test_plan_review_panel.py:257-260`)

**Suggested fix:** After successful tally in `execute_round`, call `reviewer_prune_record` with `plan-review-slots.ndjson`, round `prune_round_num`, and `findings-classification.tsv` (plus plan label-map when present).

---

### FINDING_3: Test coverage gaps (not logic bugs, but regression risk)

**Severity:** minor  
**Concern:** `make test-reviewer-prune` (`Makefile:166-167`) claims coverage of off-switch, fail-open, and round-5 bypass, but `test_reviewer_prune_record_and_filter_round_three` only exercises the all-pruned round-3 path. No pytest asserts `LARCH_REVIEWER_PRUNE=off`, round 5 passthrough, `derive_prune_status` matrix, or single-round non-prune.

**Evidence:** `docs/linting.md:308` vs. sole reviewer-prune test at `python/test_review_pipeline.py:515-553`; `derive_prune_status` / `prune_window_evaluated` have no direct unit tests.

---

## Summary table

| Behavior | Spec-compliant? | Notes |
|----------|-----------------|-------|
| Zero accepted in last 2 ledger rows → prune | **Yes** (math) | Recording gaps break real runs |
| Exact 1/3 YES (`eligible=3`) → neutral | **Yes** | `voting.py:268-269`, `test_voting.py:32` |
| Neutral rows → 0 accepted credit | **Yes** | `review_pipeline.py:349` |
| Rejected rows → 0 accepted credit | **Yes** | same filter |
| Round 5 bypass | **Yes** | filter + dispatch + design panel |
| `LARCH_REVIEWER_PRUNE=off` bypass | **Yes** (code) | Untested in pytest |

The aggregation and predicate formulas are correct; the main risk is **missing ledger writes** on zero-findings and design paths, which prevents the window predicate from firing in those scenarios.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-precision-prune-correctness.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 8126 bytes)
  ```
