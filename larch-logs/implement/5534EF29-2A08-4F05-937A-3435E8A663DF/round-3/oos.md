### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/test-implement-bootstrap.sh
[nit] B8-plan-forked-target covers gh --repo upstream/repo only; forked gh without --repo path in implement-bootstrap.sh:567-568 is untested. Forked run omitting UPSTREAM_REPO might hit wrong gh default and fail in production without harness signal. Add B8-plan-forked-no-repo case asserting gh issue view without --repo.

