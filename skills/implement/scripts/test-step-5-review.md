# Step 5 review coverage

Coverage for the `/implement` Step 5 wrapper and Rust implementation contract lives in
the inline tests in `crates/larch-cli/src/implement_review_commands.rs` and the
Rust-owned adapter tests.

The shell wrapper is only strict-mode delegation. `bgjob adapt` owns launch and
reattachment. The Rust implement verb owns separate canonical review and resume
classification, child routing, and atomic merge publication without
launching real reviewers.

Update `crates/larch-cli/src/implement_review_commands.rs` and its inline tests
whenever Step 5 result grammar, child arguments, or publication rules change.
