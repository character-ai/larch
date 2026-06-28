Elide the Step 1d.5 entry fence only when `brainstorm_requested=false`. Preserve pause/resume by moving the skip-path prerequisite sentinel writes into `step1d7_main` before its pause check.
