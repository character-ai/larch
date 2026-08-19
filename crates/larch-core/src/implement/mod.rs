//! `/implement` dispatch shared layer (#8610).
//!
//! Recovery-path resolution, porcelain helpers, lean manifest state, and
//! step-checks site mapping for later dispatch cutovers.

mod helpers;
mod identity;
mod manifest;
mod recovery;
mod self_edit_log;
mod step_checks;

pub use helpers::{
    RecoveryParse, load_digest_map, parse_porcelain_z, rel_under_tmp, resolve_tmpdir_path,
    sha256_file, tmpdir_rel_in_repo, write_bytes_atomic, write_digest_map,
};
pub use identity::{
    BGJOB_RC_KEY, CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION, CHECKS_INPUT_FP_SCHEMA_KEY,
    CHECKS_INPUT_FP_SCHEMA_V1, CHECKS_INPUT_HEAD_SHA_KEY, CHECKS_INPUT_TREE_FP_KEY,
    ChecksIdentityError, ChecksInputIdentity, Classification, WorktreeFacts,
    classify_completed_result, classify_completed_rows, classify_live_seed, compute_identity,
    first_kv_value, identities_match, identity_from_rows, integrity_failure_rows, read_env_rows,
    session_repo_root, validate_repo_root_path,
};
pub use self_edit_log::{
    SELF_EDIT_LOG_NAME, SelfEditRecord, file_sha256, normalize_path, read_self_edits,
    validate_session_tmpdir,
};
pub use manifest::{
    DispatchState, clear_external_scout_paths, manifest_legacy_fingerprint, path_under_submodule,
};
pub use recovery::{RecoveryPorcelainInputs, compute_recovery_paths};
pub use step_checks::{
    CHECKS_TERMINAL_ACTIONS, STEP6_CHECKS_STEP, StepChecksSite, checks_step_for_site,
    public_args_for_site, resolve_step_and_budget, resolve_step_name,
};
