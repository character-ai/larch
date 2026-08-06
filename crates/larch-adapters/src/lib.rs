//! Concrete adapters for filesystem, process, Git, time, and service boundaries.

pub mod clock;
pub mod codex_home;
pub mod cursor_config;
pub mod git;
pub mod github;
mod github_actions;
mod github_rest;
pub mod google_auth;
pub mod google_storage;
pub mod logging;
pub mod process;
mod process_identity;
pub mod retry;
pub mod run_lifecycle;
pub mod runtime;
pub mod s3_storage;
pub mod upgrade_larch;
pub mod vendor_auth;
pub mod vendor_diagnostics;
pub mod vendor_lifecycle;
pub mod vendor_reviewers;

use larch_core::BuildMetadata;

pub mod bgjob_registry;
mod file_io;
mod filesystem;
pub mod http_client;
pub mod phase_detail;
pub mod progress_state;
pub mod run_log_manifest;
mod session_env;
mod session_lifecycle;
pub mod stall_recovery;
pub mod statusline;

pub use codex_home::{CodexHomeContext, CodexHomeError, CodexHomePreparer};
pub use cursor_config::CursorConfigContext;
pub use file_io::{
    FileIoError, FileIoErrorKind, atomic_write_bytes, atomic_write_bytes_in, atomic_write_utf8,
    atomic_write_utf8_in, guarded_update_env, open_confined_read, read_first_raw_key, read_kv_raw,
    read_optional_utf8_lossy, read_session_kv_text, read_utf8, remove_optional_file,
    rename_same_directory,
};
pub use filesystem::{
    ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind, PluginRoot, RepositoryRoot,
    SecureTempDir, SecureTempFile, TemporaryRoot, ensure_directory_chain,
    is_allowed_session_tmpdir, normalize_path, path_strictly_under, path_under,
    resolve_allow_missing, safe_output_parent, writer_target_allowed,
};
pub use git::{
    AddRequest, ApplyRequest, BranchMutationRequest, CheckoutRequest, CleanRequest, CloneRequest,
    CommitMessage, CommitRequest, ConfigMutationRequest, ExactDiffRequest, FetchRequest,
    ForceWithLease, GitCli, GitCliError, GitCliInputError, GitCliInputErrorKind, GitCliPolicy,
    GitCliResult, GitConfigKey, GitFilePath, GitPath, GitRef, GitRefspec, GitRemote, GitToken,
    GitUrl, GixRepository, InitRequest, InterpretTrailersRequest, LsRemoteRequest, MergeRequest,
    PullRequest, PushRequest, RebaseRequest, RemoteMutationRequest, ResetMode, ResetRequest,
    RestoreRequest, RmRequest, SparseCheckoutRequest, StashRequest, SubmoduleRequest,
    TagMutationRequest, VersionRequest, WorktreeRequest, classify_process_error,
};
pub use process::{
    NoopProcessObserver, OpenFileHolderStatus, ProcessFileRouting, ProcessOutputRouting,
    ProcessStdinRouting, TokioProcessRunner, probe_open_file_holder, probe_process_command_name,
};
pub use process_identity::SystemProcessIdentityHost;
pub use session_env::{
    absolute_lexical, assert_no_symlink_ancestors, assert_no_symlink_path_or_ancestors,
    create_directories, is_directory, is_regular_file, parent_directory, publish_symlink,
    recover_prior_bool, recover_prior_design_value, remove_file_if_present,
    resolve_trusted_design_env_source, write_confined_file,
};
pub use session_lifecycle::{
    CLEANUP_AUDIT_LOG_NAME, ImplementTmpdirQuery, SessionIdOutcome, append_cleanup_audit,
    parent_process_id, remove_session_tmpdir, resolve_implement_tmpdir, validate_design_tmpdir,
    write_session_id,
};
pub use vendor_reviewers::{
    CheckReviewersContext, check_reviewers, prepare_codex_home, run_cursor_model_list,
};

/// Return metadata compiled into the adapter layer.
#[must_use]
pub const fn build_metadata() -> BuildMetadata {
    BuildMetadata::new(env!("CARGO_PKG_VERSION"), env!("LARCH_BUILD_TARGET"))
}

#[cfg(test)]
mod tests {
    use super::build_metadata;

    #[test]
    fn build_metadata_uses_the_workspace_version() {
        assert_eq!(build_metadata().version(), env!("CARGO_PKG_VERSION"));
        assert_eq!(build_metadata().target(), env!("LARCH_BUILD_TARGET"));
    }
}
