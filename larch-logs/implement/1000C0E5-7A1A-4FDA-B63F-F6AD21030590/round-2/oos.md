### FINDING_4: [OUT_OF_SCOPE] **[correctness]** [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh): The `{ emit_breadcrumb ...; } >&2` idiom and its interaction with `emit` / FD 3 is pre-existing; the new collector code mirrors the surface syntax without the same “stdout must stay parse-clean” constraint.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh): The `{ emit_breadcrumb ...; } >&2` idiom and its interaction with `emit` / FD 3 is pre-existing; the new collector code mirrors the surface syntax without the same “stdout must stay parse-clean” constraint.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-quiet.md:19-21`](scripts/lib-quiet.md) vs [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh): Documentation describes breadcrumbs as going to the “quiet log”; the default implementation writes via ordinary stdout (which is the quiet log only after init), not via FD 3. This predates the branch and is not introduced by the NS-retry change.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-quiet.md:19-21`](scripts/lib-quiet.md) vs [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh): Documentation describes breadcrumbs as going to the “quiet log”; the default implementation writes via ordinary stdout (which is the quiet log only after init), not via FD 3. This predates the branch and is not introduced by the NS-retry change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/*/collector-results.env
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] historical logs still reference REVIEWER_FILE on -ns-retry.txt paths Manual greps of old log shape do not reflect new REVIEWER_FILE=orig behavior until new runs are committed None in this diff; update playbooks if operators rely on the old suffix
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

