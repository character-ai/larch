# scripts/git-push.sh — contract

`scripts/git-push.sh` is the plain-`git push` (fast-forward, no force) wrapper used when adding a new commit on top of the existing remote tip — primarily `/implement` Step 10 / 12c after a CI-fix commit. For force-with-lease updates after a rebase, use `scripts/git-force-push.sh` (or, end-to-end, `scripts/rebase-push.sh` without `--no-push`). Skills do NOT invoke raw `git push` so the force-vs-non-force decision is always a deliberate script choice.
