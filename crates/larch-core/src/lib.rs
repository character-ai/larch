//! Domain types, use cases, and effect-free service ports for larch.

/// Immutable metadata about the running larch build.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BuildMetadata {
    version: &'static str,
}

impl BuildMetadata {
    /// Create metadata for a compile-time version.
    #[must_use]
    pub const fn new(version: &'static str) -> Self {
        Self { version }
    }

    /// Return the build version.
    #[must_use]
    pub const fn version(self) -> &'static str {
        self.version
    }
}

#[cfg(test)]
mod tests {
    use super::BuildMetadata;

    #[test]
    fn build_metadata_preserves_the_version() {
        let metadata = BuildMetadata::new("1.2.3");

        assert_eq!(metadata.version(), "1.2.3");
    }
}
