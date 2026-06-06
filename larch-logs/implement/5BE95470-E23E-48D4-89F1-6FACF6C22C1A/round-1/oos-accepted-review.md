### FINDING_8: [OUT_OF_SCOPE] risk-integration: (branch)
[nit] Full branch diff includes unrelated larch-log and Codex launcher test changes from other merged commits. Merge CI/runtime failures may be attributed to Phase 7 while originating elsewhere. Split or clearly label unrelated commits in the PR.


### FINDING_9: [OUT_OF_SCOPE] risk-integration: scripts/design-pause-load.sh
[latent] Phase 7 commit updates pause-load docs but not the script; clearing behavior comes from #3529 on the same branch. Reverting #3529 while keeping Phase 7 would leave docs claiming behavior the script lacks. Ensure #3529 ships with Phase 7 or land the script change in the Phase 7 commit.


