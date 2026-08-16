//! `/implement` dispatch shared layer (#8610).
//!
//! Recovery-path resolution, porcelain helpers, lean manifest state, and
//! step-checks site mapping for later dispatch cutovers.

mod helpers;
mod manifest;
mod recovery;
mod step_checks;

pub use helpers::{
    RecoveryParse, load_digest_map, parse_porcelain_z, rel_under_tmp, resolve_tmpdir_path,
    sha256_file, tmpdir_rel_in_repo, write_bytes_atomic, write_digest_map,
};
pub use manifest::{
    DispatchState, clear_external_scout_paths, manifest_legacy_fingerprint, path_under_submodule,
};
pub use recovery::{RecoveryPorcelainInputs, compute_recovery_paths};
pub use step_checks::{
    CHECKS_TERMINAL_ACTIONS, STEP6_CHECKS_STEP, StepChecksSite, checks_step_for_site,
    public_args_for_site, resolve_step_and_budget, resolve_step_name,
};
