//! Concrete adapters for filesystem, process, Git, and service boundaries.

pub mod runtime;

use larch_core::BuildMetadata;

mod filesystem;

pub use filesystem::{
    ConfinedPath, PathIntent, PathSafetyError, PathSafetyErrorKind, PluginRoot, RepositoryRoot,
    SecureTempDir, SecureTempFile, TemporaryRoot, normalize_path,
};

/// Return metadata compiled into the adapter layer.
#[must_use]
pub const fn build_metadata() -> BuildMetadata {
    BuildMetadata::new(env!("CARGO_PKG_VERSION"))
}

#[cfg(test)]
mod tests {
    use super::build_metadata;

    #[test]
    fn build_metadata_uses_the_workspace_version() {
        assert_eq!(build_metadata().version(), env!("CARGO_PKG_VERSION"));
    }
}
