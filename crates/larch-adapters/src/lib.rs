//! Concrete adapters for filesystem, process, Git, and service boundaries.

use larch_core::BuildMetadata;

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
