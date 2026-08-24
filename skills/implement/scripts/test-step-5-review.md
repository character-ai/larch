# Step 5 review coverage

Coverage for the `/implement` Step 5 wrapper and Rust implementation contract lives in
`python/tests/implement/test_implement_shell_scripts.py` (Step 5 wrapper-shape
nodes), `crates/larch-cli/src/implement_review_commands.rs`, and the Rust-owned
adapter tests.

The shell wrapper is only strict-mode delegation. `bgjob adapt` owns launch and
reattachment. The Rust implement verb owns separate canonical review and resume
classification, child routing, and atomic merge publication without
launching real reviewers.

Update `python/tests/implement/test_implement_shell_scripts.py`,
`crates/larch-cli/src/implement_review_commands.rs`, and its Rust tests whenever
Step 5 result grammar, child arguments, or publication rules change.
