//! Run-log directory and file layout helpers.

use std::path::{Path, PathBuf};

use super::slug::RunLogSlug;

/// Relative batch basename without directory separators.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct BatchName(Box<str>);

impl BatchName {
    /// Create a batch name without validating path safety of the full relative path.
    ///
    /// Callers supply known batch registry names. Empty names are rejected.
    ///
    /// # Errors
    ///
    /// Returns an error string when the name is empty or contains a path separator.
    pub fn new(value: impl Into<String>) -> Result<Self, String> {
        let value = value.into();
        if value.is_empty() {
            return Err("batch name must be non-empty".to_owned());
        }
        if value.contains('/') || value.contains('\\') || value.contains("..") {
            return Err("batch name must not contain path separators or '..'".to_owned());
        }
        Ok(Self(value.into_boxed_str()))
    }

    /// Return the batch basename.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Path helpers rooted at a staging or repository log root.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunLogLayout {
    log_root: PathBuf,
    skill: RunLogSlug,
    run_id: RunLogSlug,
}

impl RunLogLayout {
    /// Create a layout for one skill/run under `log_root`.
    #[must_use]
    pub fn new(log_root: impl Into<PathBuf>, skill: RunLogSlug, run_id: RunLogSlug) -> Self {
        Self {
            log_root: log_root.into(),
            skill,
            run_id,
        }
    }

    /// Create a layout under `<repo_root>/larch-logs`.
    #[must_use]
    pub fn under_repo(repo_root: impl AsRef<Path>, skill: RunLogSlug, run_id: RunLogSlug) -> Self {
        Self::new(repo_root.as_ref().join("larch-logs"), skill, run_id)
    }

    /// Return the staging or repository log root.
    #[must_use]
    pub fn log_root(&self) -> &Path {
        &self.log_root
    }

    /// Return the skill slug.
    #[must_use]
    pub const fn skill(&self) -> &RunLogSlug {
        &self.skill
    }

    /// Return the run-id slug.
    #[must_use]
    pub const fn run_id(&self) -> &RunLogSlug {
        &self.run_id
    }

    /// Return `<log_root>/<skill>/<run_id>`.
    #[must_use]
    pub fn run_dir(&self) -> PathBuf {
        self.log_root
            .join(self.skill.as_str())
            .join(self.run_id.as_str())
    }

    /// Return the run manifest path.
    #[must_use]
    pub fn manifest_path(&self) -> PathBuf {
        self.run_dir().join("manifest.json")
    }

    /// Return the round directory for a 1-based round number.
    #[must_use]
    pub fn round_dir(&self, round: u32) -> PathBuf {
        self.run_dir().join(format!("round-{round}"))
    }

    /// Return a batch artifact path with the given extension (including the leading dot).
    #[must_use]
    pub fn batch_path(&self, batch: &BatchName, extension: &str) -> PathBuf {
        self.run_dir()
            .join(format!("{}{extension}", batch.as_str()))
    }
}

#[cfg(test)]
mod tests {
    use super::{BatchName, RunLogLayout};
    use crate::run_log::RunLogSlug;
    use std::path::PathBuf;

    #[test]
    fn builds_python_compatible_paths() {
        let layout = RunLogLayout::new(
            "/tmp/logs",
            RunLogSlug::parse("implement").unwrap(),
            RunLogSlug::parse("run-abc").unwrap(),
        );
        assert_eq!(
            layout.run_dir(),
            PathBuf::from("/tmp/logs/implement/run-abc")
        );
        assert_eq!(
            layout.manifest_path(),
            PathBuf::from("/tmp/logs/implement/run-abc/manifest.json")
        );
        assert_eq!(
            layout.round_dir(2),
            PathBuf::from("/tmp/logs/implement/run-abc/round-2")
        );
        let batch = BatchName::new("code-review-tally").unwrap();
        assert_eq!(
            layout.batch_path(&batch, ".json"),
            PathBuf::from("/tmp/logs/implement/run-abc/code-review-tally.json")
        );
    }

    #[test]
    fn under_repo_uses_larch_logs() {
        let layout = RunLogLayout::under_repo(
            "/repo",
            RunLogSlug::parse("design").unwrap(),
            RunLogSlug::parse("-abc123").unwrap(),
        );
        assert_eq!(layout.log_root(), PathBuf::from("/repo/larch-logs"));
    }
}
