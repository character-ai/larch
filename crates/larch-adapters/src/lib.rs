//! Concrete adapters for filesystem, process, Git, time, and service boundaries.

pub mod clock;
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
pub mod runtime;
pub mod upgrade_larch;

use larch_core::BuildMetadata;

mod file_io;
mod filesystem;
mod session_lifecycle;

pub use cursor_config::CursorConfigContext;
pub use file_io::{
    FileIoError, FileIoErrorKind, atomic_write_bytes, atomic_write_utf8, atomic_write_utf8_in,
    guarded_update_env, read_first_raw_key, read_kv_raw, read_optional_utf8_lossy,
    read_session_kv_text, read_utf8, rename_same_directory,
};
pub use filesystem::{
    ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind, PluginRoot, RepositoryRoot,
    SecureTempDir, SecureTempFile, TemporaryRoot, is_allowed_session_tmpdir, normalize_path,
    path_strictly_under, path_under, resolve_allow_missing, safe_output_parent,
    writer_target_allowed,
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
    NoopProcessObserver, OpenFileHolderStatus, TokioProcessRunner, probe_open_file_holder,
    probe_process_command_name,
};
pub use session_lifecycle::{
    CLEANUP_AUDIT_LOG_NAME, ImplementTmpdirQuery, SessionIdOutcome, append_cleanup_audit,
    parent_process_id, remove_session_tmpdir, resolve_implement_tmpdir, validate_design_tmpdir,
    write_session_id,
};
pub use process_identity::SystemProcessIdentityHost;

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
