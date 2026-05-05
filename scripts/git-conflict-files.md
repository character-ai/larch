# scripts/git-conflict-files.sh — contract

`scripts/git-conflict-files.sh` wraps `git ls-files -u` so callers don't invoke raw `git`. Lists files in merge-conflict state with per-stage presence (stage 1 = base, stage 2 = upstream/main during rebase, stage 3 = feature branch commit during rebase). Used by `/implement`'s Conflict Resolution Procedure Phase 1 to classify each conflicted file (trivial / high-confidence / uncertain) before the orchestrator decides whether to auto-resolve, ask the user, or escalate to the reviewer panel.
