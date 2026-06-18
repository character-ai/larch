## Decision 1: prune-nit-findings.sh target module
- **Question**: Which Python module should receive prune-nit-findings logic?
- **Resolution**: `review_aggregate.py` — register as `review prune-nit-findings` CLI verb and update `review_pipeline.py` to use `_call_maybe_override` pattern
- **Source**: codebase

## Decision 2: review_legacy.py fate
- **Question**: Should review_legacy.py be deleted once its callers are ported in-process?
- **Resolution**: Yes — delete it. After G2 nothing calls run_review_shell.
- **Source**: codebase

## Decision 3: bash regression harness for prune-nit-findings
- **Question**: What happens to test-prune-nit-findings.sh and its .md sibling?
- **Resolution**: Convert coverage to pytest in test_review_aggregate.py; delete bash harness per recipe step 6.
- **Source**: docs/python-migration.md

## Decision 4: aggregate-findings-phrases.inc.bash fate
- **Question**: Should the sourced include be deleted alongside the main script?
- **Resolution**: Yes — its failure_see_phrase / committed_ref helpers move inline to review_aggregate.py.
- **Source**: codebase
