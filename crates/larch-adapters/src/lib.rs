//! Concrete adapters for filesystem, process, Git, time, and service boundaries.

pub mod clock;
pub mod google_auth;
pub mod logging;
pub mod process;
pub mod retry;
pub mod runtime;

use larch_core::BuildMetadata;

mod file_io;
mod filesystem;

pub use file_io::{
    FileIoError, FileIoErrorKind, atomic_write_utf8, guarded_update_env, read_utf8,
    rename_same_directory,
};
pub use filesystem::{
    ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind, PluginRoot, RepositoryRoot,
    SecureTempDir, SecureTempFile, TemporaryRoot, normalize_path,
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
