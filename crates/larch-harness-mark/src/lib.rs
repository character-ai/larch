//! Dependency-free helpers used before the released CLI is available in CI.
//!
//! These helpers stay separate from the released CLI so a fresh runner does not
//! compile the full product to start a harness or enumerate residual Bash paths.

mod harness_mark;
mod residual_bash;

pub use harness_mark::{
    HARNESS_BOOTSTRAP_KIND_ENV, HARNESS_BOOTSTRAP_SENTINEL, HARNESS_BOOTSTRAP_START_NS_ENV,
    HARNESS_TIMING_SENTINEL, harness_mark,
};
pub use residual_bash::{RESIDUAL_BASH_MANIFEST, has_shell_suffix_bytes, read_residual_bash_paths};
