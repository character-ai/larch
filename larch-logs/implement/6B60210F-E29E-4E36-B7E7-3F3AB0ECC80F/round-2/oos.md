### OOS_1: [OUT_OF_SCOPE] Unreachable `RuntimeError` in `python/retry.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unreachable `RuntimeError` after exhaustive loop; linters may warn with no runtime effect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; remove dead raise or satisfy linter.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] No streaming redact API in Python
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: `python/redact.py` only batch `redact(text)`; bash `--streaming` with `in_pem` state matters at Phase 7 for chunked logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Defer to cutover.)

---


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_11: [OUT_OF_SCOPE] Inconsistent bash redact pipeline order
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: Bash callers use both `tmpdir|secrets` and `secrets|tmpdir`; Python hard-codes tmpdir-then-secrets. Resolve at Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Resolve ordering at cutover.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] `create-one.sh` secrets-only redaction on live path
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: `skills/issue/scripts/create-one.sh` still uses `redact-secrets.sh` only; session tmpdir paths can reach public issue bodies pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Pre-existing; outside branch.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_13: [OUT_OF_SCOPE] Plan vs ship-pr six-line doc drift
- **Reviewer(s)**: dyn-strangler-boundary-output.txt
- **Severity**: nit
- **Concern**: Plan says `ship-pr.sh` untouched; branch adds six lines for CI replay — reconcile in follow-up docs, not a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Doc reconciliation only.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_14: [OUT_OF_SCOPE] Routing glob also omits `python/README.md`
- **Reviewer(s)**: dyn-strangler-boundary-output.txt
- **Severity**: nit
- **Concern**: Low severity: edits confined to `python/README.md` may skip py targets while affecting the tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Low severity; optional glob extension.)

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_15: [OUT_OF_SCOPE] No `LARCH_SHIP_PR_IMPL` wiring yet (expected Phase 1)
- **Reviewer(s)**: dyn-strangler-boundary-output.txt
- **Severity**: nit
- **Concern**: No reads of `LARCH_SHIP_PR_IMPL`; Python modules not wired into bash state machine before Phase 7; skills do not reference `python/` — expected strangler boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No action for Phase 1.)

---

**Summary**: 23 in-scope merged findings (`FINDING_1`–`FINDING_23`), 15 out-of-scope blocks (`OOS_1`–`OOS_15`). Highest-density merges: Makefile `lint` (7 slots), inline `gh --body` (4), transient `gh` tests (4), redact parity tests (2+3 dyn), `relevant-checks` pytest guard (3), ship-pr replay prereqs (2).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Large copied `python/.pylintrc`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: 660-line copied pylint config is repo noise only for Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; accept for Phase 1 or trim in follow-up.)

---


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Journal/breadcrumb writers do not redact payloads
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `python/logging_util.py` journal writers do not redact payloads; secrets in journal fields could hit disk when ship-pr Python path is wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; redact at write time when wiring ship-pr Python path.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] `test_stdlib_only.py` misses dynamic `__import__`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Stdlib test misses non-constant dynamic `__import__`; non-literal import could bypass stdlib enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; extend AST visitor or ban pattern in review.)

---


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] `docs/linting.md` CI bullet missing Python jobs
- **Reviewer(s)**: dyn-ci-pipeline-output.txt
- **Severity**: nit
- **Concern**: CI usage bullet still lists legacy jobs but not new `python-lint` / `python-tests` or split requirements files.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; doc pass for operators.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] `python/README.md` omits Node for pyright
- **Reviewer(s)**: dyn-ci-pipeline-output.txt
- **Severity**: nit
- **Concern**: README documents pip installs but not that `make py-lint` / pyright needs Node on the host (CI supplies via `setup-node`; local replay does not).
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] `retry.py` EOF/git-fetch ordering parity verified OK
- **Reviewer(s)**: dyn-process-retry-output.txt
- **Severity**: nit
- **Concern**: Reviewer attests ordered substring checks match bash `case` left-to-right semantics; parity vectors for non-transient cases are correct — informational, not a defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix; positive verification.)

---


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] `launch_tier` without `bash` prefix acceptable
- **Reviewer(s)**: dyn-process-retry-output.txt
- **Severity**: nit
- **Concern**: Reviewer attests `launch_tier` mirrors ship-pr executable-script invocation when `cwd` is repo root and scripts remain `+x`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix; positive verification.)

---


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] `make lint` Python deps intentional per reviewer
- **Reviewer(s)**: dyn-process-retry-output.txt
- **Severity**: nit
- **Concern**: Reviewer characterizes `make lint` requiring `py-lint`/`py-test` as intentional dev-ergonomics change, not a subprocess defect — conflicts with in-scope FINDING_1; retained as OOS opinion only.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix direction.)

---


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

