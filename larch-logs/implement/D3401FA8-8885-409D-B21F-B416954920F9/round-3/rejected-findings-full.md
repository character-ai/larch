### [rejected] FINDING_30

### FINDING_30: `audit-map-runs.sh` PR list parsing vs Bash 3.2 policy (reviewer disagreement)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt
- **Concern**: One reviewer claims `read -a` / array parsing is incompatible with macOS Bash 3.2 and fails at parse time; another reviewer asserts the shown `read -r -a` heredoc pattern is Bash 3.2-valid—leaves a portability/policy ambiguity that blocks confident “fix direction.”
- **Suggested revision**: Reconcile against repo `BASH_AUTHORING.md` / supported Bash baseline: either replace tokenization with explicitly approved 3.2-safe parsing **or** document/encode why the current approach is guaranteed safe on supported platforms.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

