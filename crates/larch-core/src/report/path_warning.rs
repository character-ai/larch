//! One shared shape for a non-fatal, path-scoped reader warning.

use std::path::{Path, PathBuf};

/// A recoverable reader finding: a stable kind, the affected path, and a
/// diagnostic. Readers alias this with their own kind enum instead of
/// redeclaring the carrier.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PathWarning<K> {
    kind: K,
    path: PathBuf,
    message: String,
}

impl<K: Copy> PathWarning<K> {
    pub(crate) fn new(kind: K, path: PathBuf, message: impl Into<String>) -> Self {
        Self {
            kind,
            path,
            message: message.into(),
        }
    }

    /// Return the stable warning kind.
    #[must_use]
    pub const fn kind(&self) -> K {
        self.kind
    }

    /// Return the affected path.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Return the operator-facing diagnostic.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}
