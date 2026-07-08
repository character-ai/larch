Fix the Step 5 orphan loop by preserving the real Claude session PID across the generated `implement-run-$PPID.sh` launcher, then pin it with session-env and implement fence tests.
