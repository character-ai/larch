Here is the normalized aggregator output. Merges follow same behavioral risk / same missing artifact; splits where fixes conflict (FINDING_2 vs FINDING_5) or where `[OUT_OF_SCOPE]` must stay isolated per source distinction. Verbatim revisions below are exactly as in the input (`Address the concern above.`).

---

### FINDING_1: Unrelated design log tree mixed with #2655 AGENTS work on one branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Unrelated issue #2654 design-run / design log material ships in the same branch or PR as #2655 AGENTS trim work, inflating diff and review surface, weakening story-per-PR isolation, and increasing merge or rebase conflict risk and signal-to-noise loss for reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Phase 1 include-probe evidence and BRANCH decision not retained on a committed path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: No committed artifact reproduces the Phase 1 BRANCH decision or per-agent transcripts from the ephemeral tmpdir; plan acceptance expects evidence (for example results with BRANCH and transcripts) so post-merge audit and reviewers cannot verify cross-agent include probes, strict decision rules, or that Branch B followed from failed gate conditions versus skipping Phase 1 using git or the PR alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: AGENTS.md polling / ScheduleWakeup bullet still more verbose than needed for Branch-B trim
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Under the 11000-character budget, the polling / ScheduleWakeup bullet keeps more wording than necessary versus a minimal trim; less headroom is reclaimed than possible while preserving canonical pointers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: AGENTS.md cross-reference to research SKILL understates where full ScheduleWakeup narrative lives
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The ScheduleWakeup trim bullet cites `skills/research/SKILL.md` for incident-level rationale, but that SKILL largely defers to `skills/shared/orchestrator-never.md`, so readers who open research/SKILL.md expecting the long “Why / How to apply” narrative find only a short forwarder and may distrust AGENTS cross-references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: AGENTS.md anti-polling bullet lost nuance not fully duplicated in cited NEVER / BASH passages
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The shortened anti-polling bullet no longer states nuanced failure modes (duplicate task notifications, stale poller, ScheduleWakeup as pseudo-/loop input); those are not fully duplicated in the cited NEVER #9, BASH_AUTHORING §4, and NEVER #16 passages, so operators who never open the harness doc may under-weight original #1011 motivation distinct from foreground-marker rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: AGENTS.md trimmed orchestration bullets may under-weight incidents unless one short outcome clause remains visible
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Incident-level rationale for orchestration NEVER rules (polling, ScheduleWakeup, session-env, session safety) moved mostly behind SKILL.md / BASH pointers; models or humans that reason only from AGENTS and skip linked files may under-weight concrete failure signatures and worst-case outcomes that previously discouraged mistakes at first read, within character budget constraints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Committed Cursor plan output exposes `file://` and home-prefixed cache paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Committed Cursor output includes `file://` URLs under `<OPERATOR_REPO_PATH>/...`, so clones and public mirrors can expose operator Unix username and local session cache paths from agent markdown links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Canonical sources list has uneven gloss for voting / point-competition paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: At AGENTS.md around the canonical sources list, voting and point-competition docs appear as bare paths while other entries carry gloss, weakening skimming UX and making it harder to pick the right doc from the list alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Session-env bullet lost compact script or symptom anchors for AGENTS-only triage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The session-env bullet no longer names representative scripts or missing-key symptom strings, so grep- or runbook-driven triage from AGENTS alone is weaker unless readers defer entirely to SKILL NEVER #14.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] AGENTS.md still names retired persist-post-plan-keys.sh as sanctioned writer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [OUT_OF_SCOPE] AGENTS still names `persist-post-plan-keys.sh` as a sanctioned session-env writer while NEVER #14 uses `persist-implement-run-flags.sh`; pre-existing drift with the wrong script name on both sides of the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Large unrelated design log bundle coexists with AGENTS change (intentional policy; review noise only)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [OUT_OF_SCOPE] A large unrelated design log bundle shares the branch diff with the AGENTS change; review noise only, does not change AGENTS semantics, characterized as intentional per run-log policy with filtering when reviewing this feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Phase 3 plan-required tests not provable from patch alone
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [OUT_OF_SCOPE] Plan-required test commands and exit codes are not provable from the diff alone; reviewer cannot see CI or local results from the patch in read-only review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge rationale (brief):** FINDING_1/9/17 were merged as one integration risk (mixed PR); FINDING_15 was kept separate because it is explicitly `[OUT_OF_SCOPE]` with a different stance (intentional policy, no AGENTS semantic change). FINDING_3/4/8/16 were merged as one auditability gap for Phase 1 evidence. FINDING_2 (shorten further) and FINDING_5 (restore nuance) stay separate because the suggested directions conflict. FINDING_11 and FINDING_12 were merged as one “inline vs pointer-only” risk on the AGENTS orchestration bullets. `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included because this output contains one or more `### FINDING_N:` blocks.
