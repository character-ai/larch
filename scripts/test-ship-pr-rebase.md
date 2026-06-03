# scripts/test-ship-pr-rebase.sh

Offline harness for Phase 1 (#3364) `scripts/ship-pr.sh` CI-fix rebase behavior: structural pins (defer-push only when `ci-behind-count` reports behind main; no per-PR bump hooks), fork postbump branch guard, `ship-pr-rrr-phase14` handoff validation, and legacy `--resume-phase step8b_rebase` tolerance.

Full plan acceptance concurrency (two disjoint PRs; second merges without rebase/re-bump) remains **manual-only** — operators reproduce per issue #3364 acceptance criteria; this harness pins the `BEHIND_COUNT > 0` gate that prevents unnecessary defer-rebase when already up to date.
