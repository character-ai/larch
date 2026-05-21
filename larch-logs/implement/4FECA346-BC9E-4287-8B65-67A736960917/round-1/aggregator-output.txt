Here is the normalized structured finding list (merged by behavioral risk; reviewer slots preserved; `[OUT_OF_SCOPE]` kept where any merged source used it).

```text
### FINDING_1: [OUT_OF_SCOPE] skills/fix-issue/SKILL.md Step 0 shows misleading find-lock-issue argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Step 0 documents `find-lock-issue.sh ["$ISSUE_ARG"]`, which looks like executable shell but passes literal bracket characters in argv (or invites `test`/`[` misuse), so the lock step can target the wrong token or fail. Several reviewers treat this as high-impact correctness; others flag it as a pre-existing doc/copy-paste footgun suitable for a separate follow-up.
- **Suggested revision**: Replace with normal shell quoting, e.g. `find-lock-issue.sh "$ISSUE_ARG"` (and/or rewrite the snippet so it cannot be mistaken for literal argv).

### FINDING_2: Umbrella still documents/parses --go forwarded to /issue after /issue dropped --go
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Umbrella skill and parse-args emit/accept `--go` intended for `/issue`, but `/issue` no longer supports `--go`, creating undefined/error paths and operator confusion relative to README and other docs.
- **Suggested revision**: Remove `--go` from umbrella parsing, emitted CLI, SKILL examples, and umbrella tests; or define and test an explicit backward-compat shim if retention is intentional.

### FINDING_3: SECURITY.md still describes /issue --go approval tied to /fix-issue
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Security/ops guidance appears stale after GO removal, misleading readers about the supported workflow and approval surface.
- **Suggested revision**: Rewrite or remove the subsection so it matches the current `/issue` + `/fix-issue` contract.

### FINDING_4: docs/workflow-lifecycle.md still lists [--go] for standalone /issue
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Conflicts with updated README/skills and can steer users toward unsupported flags.
- **Suggested revision**: Drop `[--go]` from that bullet (and any adjacent wording that implies GO is part of the filing contract).

### FINDING_5: Stale exit 1 / “no candidate” documentation vs find-lock-issue.sh after auto-pick removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Multiple runbooks/reference layers still describe `find-lock-issue.sh` exiting `1` for no-candidate / empty-queue semantics and propagate that matrix into Step 3/8 cleanup and triage examples, but the script contract on this branch no longer produces that exit path—leading orchestrators/humans to implement dead branches or mis-triage real exits.
- **Suggested revision**: Remove exit-`1` “no candidate” handling from Step 0/3/8 and cross-skill digests; align all documented exit codes and meanings with `find-lock-issue.md` / the script’s actual `0/2/3/4/5` (or whatever is truly emitted).

### FINDING_6: Public docs still show /fix-issue issue argument as optional
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `README.md` and `docs/skills.md` tables/lines use optional-looking `[<number-or-url>]`, while the SKILL/script require a positional issue—users and automation may omit the argument until runtime failure.
- **Suggested revision**: Make `<number-or-url>` mandatory in the public matrices/lines (no optionality brackets) and add a single explicit “required” cue if helpful.

### FINDING_7: skills/fix-issue/scripts/umbrella-handler.md contract stale (auto-pick / --lock-no-go)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Intro and caller guidance still describe auto-pick and `--lock-no-go`, contradicting explicit-target-only `find-lock-issue.sh` and unified `--lock` semantics—risk of reintroducing removed flags or wrong lock behavior in umbrella integrations.
- **Suggested revision**: Rewrite to explicit-target-only framing; replace `--lock-no-go` with `--lock` and sweep stale mentions.

### FINDING_8: skills/fix-issue/scripts/test-find-lock-issue.sh comments/fixtures read as spec drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Harness comments/messages still reference `lock-no-go`, removed `--issue` invocation style, GO deletion narratives, and other pre-merge semantics—tests no longer read as authoritative contract for the current CLI and lifecycle.
- **Suggested revision**: Update comments/assert text/fixture labels to `--lock`, positional explicit target, and current lifecycle comments (including fixture 5/16 narratives called out by reviewers).

### FINDING_9: Fixture style still ends many threads with GO as last comment (weak contract signal)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Broad use of GO as the terminal comment weakens the test suite’s signal that GO is not part of the lock contract under the new model.
- **Suggested revision**: Where safe, migrate fixtures to benign last comments that don’t imply GO semantics.

### FINDING_10: skills/fix-issue/scripts/find-lock-issue.md stderr contract mentions deprecated-flag warnings that may no longer exist
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Maintainer-facing stderr contract may be stale after removing deprecated `--issue` handling, causing mistrust or noisy greps.
- **Suggested revision**: Reword the stderr bullet to match actual stderr sources on this branch.

### FINDING_11: skills/fix-issue/scripts/find-lock-issue.sh comments mis-describe post-auto-pick eligibility / failure modes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Comments still talk about auto-pick-era distinctions (e.g., “no candidate” vs lock failure) that are no longer produced here, risking incorrect future edits to gating/eligibility.
- **Suggested revision**: Rewrite comments for explicit-target-only reality and the real pass/fail distinctions.

### FINDING_12: skills/implement/SKILL.md still ties managed-prefix exclusion language to auto-pick
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Cross-skill mental model drift after auto-pick removal; readers may infer behavior that no longer exists.
- **Suggested revision**: Rewrite the passage to describe explicit-target eligibility only (no auto-pick framing).

### FINDING_13: [OUT_OF_SCOPE] CHANGELOG historical entries describe old GO / lock-no-go / auto-pick
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Historical changelog noise only; not a runtime contract for this change set, but reviewers note optional addendum if desired.
- **Suggested revision**: None required for correctness; optionally add a short clarifying addendum if the project wants the narrative tightened.

### FINDING_14: docs/installation-and-setup.md may be missing the mandatory-arg / workflow doc touch implied by checklist/plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Feature work expected an update in this file, but it appears untouched—potential mismatch vs stated rollout completeness.
- **Suggested revision**: Add a minimal sentence aligning install/setup guidance with mandatory `/fix-issue` issue argument / updated workflow, or explicitly justify no change if truly N/A.
```
