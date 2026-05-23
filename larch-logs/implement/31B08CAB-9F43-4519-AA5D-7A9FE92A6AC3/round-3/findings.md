We have a single structured deliverable: merge the supplied reviewer slots’ findings, assign `FINDING_1`… in merge order, and preserve verbatim suggested revisions (merging identical wording across slots). No codebase reads or edits were required.

We merged these groups as one behavioral risk each:

- **FINDING_1, 14, 18**: `.pre-commit-config.yaml` header vs CI reality (`make lint` vs `make lint-only` / Makefile docs).
- **FINDING_3, 10, 22**: `BASH_AUTHORING.md` Section 4 / “Foreground Default” heading vs acceptance phrase discoverability.
- **FINDING_5, 16**: `scripts/test-lint-foreground-markers.md` out of sync with harness (fixture count / case ordering vs shell).
- **FINDING_6, 7**: `scripts/lint-foreground-markers.sh` `*.sh` fast-path and single-line parsing can miss denylisted invocations (including split basename across line continuation).
- **FINDING_11, 23**: Banner match is substring-anywhere in window vs plan/authoring “leading line” visibility.

All three slots for the pre-commit merge used the identical revision string **“Address the concern above.”** — one merged bullet per the merge rule. Same for the BASH heading merge, doc merge, `.sh`/line merge, and banner merge.

`[OUT_OF_SCOPE]` items stay separate; none were merged with in-scope text.

---

### FINDING_1: Pre-commit header vs CI lint entrypoint (`make lint` vs `make lint-only`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The top-of-file comment in `.pre-commit-config.yaml` implies CI runs full `make lint` via pre-commit, while Makefile comments / `docs/linting.md` describe a split where CI uses harness shards and `make lint-only` (pre-commit), with `make lint` as the local aggregate. Operators can misread which target CI runs and mis-triage lint vs harness failures, or skip running the full local aggregate before shipping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: CHANGELOG 42.0.10 bundles unrelated themes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The `[42.0.10]` release entry mixes unrelated bullets (disposition gate, OOS persistence, harness, foreground lint), making it hard to tell what changed for a given regression without reading the whole list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: BASH_AUTHORING Section 4 title vs acceptance phrase “Foreground Default for Blocking Script Calls”
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Section 4’s visible heading / title does not match the plan acceptance wording (“Foreground Default for Blocking Script Calls” and related §4 phrasing). Cross-doc searches, tracking-issue quotes, and audits that use the acceptance string may miss the normative section unless an alias line is added or the heading is aligned/renamed everywhere consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Harness case 24 label vs `.sh` substring gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Case 24’s label suggests continuation enforcement is covered, but a `.sh` substring gate skips lines without `.sh`, so maintainers may believe continuation anchoring is tested when the linter can skip that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `test-lint-foreground-markers.md` out of sync with harness cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The markdown doc drifts from the shell harness: fixture count / “16 fixtures” vs more cases, and the numbered contract list order does not match harness case numbers—slowing correlation from PASS/FAIL output to documented cases during debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: `*.sh` fast-path and single-line anchors can miss denylisted invocations
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: The `*'.sh'*` heuristic plus single-line anchor logic can miss rare fenced shapes (general latent risk), and specifically backslash/line breaks can split a denylisted `*.sh` basename so no single fence line contains the full basename token—then the `*.sh` fast-path skips anchor detection, allowing a fenced invocation without markers to pass lint and evade the Family B gate unless continuation joining is implemented, the fast-path removed, and/or a harness case locks the behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Family A harness counts `run_in_background: true` file-wide
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The regression check counts `run_in_background: true` substrings across the whole file, so unrelated literals can satisfy the floor while real Family A Bash fences lose `background=true`, weakening the test’s structural guarantee.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Unbraced `$CLAUDE_PLUGIN_ROOT/.../denylisted.sh` not matched by ERE branches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Unbraced `$CLAUDE_PLUGIN_ROOT/.../denylisted.sh` invocations are not matched by existing ERE branches, so omitted markers around valid unbraced expansion calls can pass lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Banner check allows substring-anywhere in window vs leading-line intent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The banner check matches substring-anywhere in the initial window, not a leading-line-only rule aligned with some authoring text and the plan’s operator-first visibility goal—CI can pass with the banner buried in unrelated prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Harness comment numbering skips case 16
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Harness comment numbering skips case 16—mild maintainability noise only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Large committed `larch-logs/**` churn
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Large committed run logs and transcripts; expected artifact churn per `docs/run-logs.md`; not a correctness defect of foreground/OOS logic; no product-correctness change required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: Missing positive harness for `VAR=$( ... denylisted.sh ... )`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No positive fixture for command-substitution assignment to a variable with a denylisted `.sh` path, though the plan listed that shape and production uses it (e.g. `dispatch-with-waterfall.sh`)—a bad refactor of the `=$(` ERE branch could ship if only the harness is run without full-repo lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] `GH_HOST` only dot-escaped in grep ERE URL patterns
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `GH_HOST` is only dot-escaped before interpolation into grep ERE patterns reused by strict URL counting; a contrived `GH_HOST` with other ERE metacharacters could distort URL matching—an inherited edge case, not introduced solely by the new counter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: `CLAUDE_PLUGIN_ROOT` anchor regex matches dangerous suffix substrings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The `CLAUDE_PLUGIN_ROOT` anchor ERE can match any suffix equal to a denylisted basename (e.g. a path ending in `.../test-review-and-fix.sh` treated like `review-and-fix.sh`), causing false violations or misleading marker placement unless matching is tightened to the final path segment or explicit `/basename` boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Very long lines silently skip anchor detection
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Lines over ~12000 characters skip anchor detection silently, so a pathological one-line fence could evade denylist enforcement without notice unless the linter warns/fails on skip or when denylist tokens appear on skipped lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] OOS disposition gate disjunctive pass paths vs per-OOS equality
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Disposition gate uses disjunctive pass paths (`filed > 0`, etc.), not per-OOS equality; accepted under-count vs `non_sec` remains possible depending on workflow—not new to this branch; track only if product intent changes; out of scope for foreground-marker review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Branch bundles unrelated work (foreground markers, OOS, run logs, version bump)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `git log merge-base..HEAD` bundles foreground-marker work with unrelated #2648 OOS changes, run-log flushes, and version bump—hurting plan fidelity and review focus when disentangling independent features in one diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Stderr splits “missing banner” / “missing comment” vs plan’s unified template
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Stderr uses split “missing banner” / “missing comment” messages instead of the plan’s unified template—minor mismatch for anyone grepping or documenting the exact plan error string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `rebase-rebump-subprocedure.md` listed for ci-wait markers but only prose
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan listed this file for ci-wait markers but there is no fenced ci-wait invocation—only prose; no failing linter expectation; “missing markers” would be a false alarm against fenced-only acceptance—plan wording cleanup only if desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

Because this output contains one or more `### FINDING_N:` blocks, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must **not** appear anywhere in this aggregate.
