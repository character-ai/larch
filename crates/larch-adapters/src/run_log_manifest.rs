//! Durable run-log manifest publication.
//!
//! [`ManifestStore`] is the sole filesystem writer for the Rust-owned
//! `run-log manifest` selector. It delegates publication to
//! [`crate::atomic_write_utf8_in`], whose same-directory write, sync, rename,
//! and parent-directory sync protocol is the manifest durability contract.

use chrono::{SecondsFormat, Utc};
use larch_core::{ManifestDocument, ManifestUpdate, ManifestWriteError, RunLogLayout};
use std::{
    error::Error,
    fmt,
    path::{Path, PathBuf},
};

use crate::{
    FileIoError, PathIntent, PathSafetyError, PathSafetyErrorKind, TemporaryRoot,
    atomic_write_utf8_in, read_utf8,
};

const MANIFEST_FILE_MODE: u32 = 0o600;

/// A securely rooted store for one run-log tree.
#[derive(Clone, Debug)]
pub struct ManifestStore {
    root: TemporaryRoot,
}

/// Why a durable manifest update could not complete.
#[derive(Debug)]
pub enum ManifestStoreError {
    /// The requested log root or manifest path was unsafe.
    PathSafety(PathSafetyError),
    /// The target manifest did not exist as a regular file.
    MissingManifest(PathBuf),
    /// The layout belongs to a different trusted log-root tree.
    RootMismatch {
        /// Canonical root held by this store.
        store_root: PathBuf,
        /// Canonical root selected by the caller's layout.
        layout_root: PathBuf,
    },
    /// Reading or publishing the manifest failed.
    FileIo(FileIoError),
    /// Version-aware construction or mutation refused the source data.
    Manifest(ManifestWriteError),
}

impl fmt::Display for ManifestStoreError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PathSafety(error) => error.fmt(formatter),
            Self::MissingManifest(path) => {
                write!(formatter, "manifest not found: {}", path.display())
            }
            Self::RootMismatch {
                store_root,
                layout_root,
            } => write!(
                formatter,
                "manifest layout root differs from store root: {} != {}",
                layout_root.display(),
                store_root.display()
            ),
            Self::FileIo(error) => error.fmt(formatter),
            Self::Manifest(error) => error.fmt(formatter),
        }
    }
}

impl Error for ManifestStoreError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::PathSafety(error) => Some(error),
            Self::MissingManifest(_) | Self::RootMismatch { .. } => None,
            Self::FileIo(error) => Some(error),
            Self::Manifest(error) => Some(error),
        }
    }
}

impl ManifestStore {
    /// Open an existing absolute, non-symlinked run-log root.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestStoreError::PathSafety`] if the root is absent,
    /// relative, symlinked, or not a directory.
    pub fn open(log_root: &Path) -> Result<Self, ManifestStoreError> {
        TemporaryRoot::resolve(Some(log_root))
            .map(|root| Self { root })
            .map_err(ManifestStoreError::PathSafety)
    }

    /// Apply updates to one existing v2 manifest and atomically publish it.
    ///
    /// # Errors
    ///
    /// Returns a typed failure without writing when the source is missing,
    /// malformed, historical, unknown-versioned, or has immutable updates.
    /// Successful publication exclusively uses [`atomic_write_utf8_in`].
    pub fn update(
        &self,
        layout: &RunLogLayout,
        updates: &[ManifestUpdate],
        updated_at: &str,
    ) -> Result<PathBuf, ManifestStoreError> {
        self.update_with(layout, updates, updated_at, |root, path, rendered| {
            atomic_write_utf8_in(root, path, rendered, true, MANIFEST_FILE_MODE)
                .map_err(ManifestStoreError::FileIo)
        })
    }

    fn update_with(
        &self,
        layout: &RunLogLayout,
        updates: &[ManifestUpdate],
        updated_at: &str,
        publish: impl FnOnce(&TemporaryRoot, &Path, &str) -> Result<(), ManifestStoreError>,
    ) -> Result<PathBuf, ManifestStoreError> {
        let layout_root = TemporaryRoot::resolve(Some(layout.log_root()))
            .map_err(ManifestStoreError::PathSafety)?;
        if layout_root != self.root {
            return Err(ManifestStoreError::RootMismatch {
                store_root: self.root.path().to_path_buf(),
                layout_root: layout_root.path().to_path_buf(),
            });
        }
        let requested_path = layout.manifest_path();
        let path = self.root.path().join(layout.manifest_relative_path());
        let source = self.confined_manifest(&path, &requested_path)?;
        let text = read_utf8(&source).map_err(ManifestStoreError::FileIo)?;
        let mut manifest =
            ManifestDocument::from_bytes(text.as_bytes()).map_err(ManifestStoreError::Manifest)?;
        manifest
            .apply_updates(updates, updated_at)
            .map_err(ManifestStoreError::Manifest)?;
        let rendered = manifest.canonical_json();
        publish(&self.root, &path, &rendered)?;
        Ok(requested_path)
    }

    fn confined_manifest(
        &self,
        path: &Path,
        requested_path: &Path,
    ) -> Result<crate::ConfinedPath, ManifestStoreError> {
        self.root.confine(path, PathIntent::Read).map_err(|error| {
            if error.kind() == PathSafetyErrorKind::Missing {
                ManifestStoreError::MissingManifest(requested_path.to_path_buf())
            } else {
                ManifestStoreError::PathSafety(error)
            }
        })
    }
}

/// Return the UTC timestamp shape written by the retired Python selector.
#[must_use]
pub fn utc_now() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true)
}

#[cfg(test)]
mod tests {
    use super::{MANIFEST_FILE_MODE, ManifestStore, ManifestStoreError};
    use larch_core::{ManifestUpdate, RunLogLayout, RunLogSlug};
    use serde_json::{Value, json};
    use std::{fs, io, io::Write as _, path::Path};

    fn layout(root: &Path) -> RunLogLayout {
        RunLogLayout::new(
            root,
            RunLogSlug::parse("implement").expect("skill should parse"),
            RunLogSlug::parse("run-1").expect("run id should parse"),
        )
    }

    fn v2_manifest() -> &'static str {
        "{\n  \"schema_version\": 2,\n  \"skill\": \"implement\",\n  \"run_id\": \"run-1\",\n  \"started_at\": \"t0\",\n  \"status\": \"partial\",\n  \"steps_ran\": {}\n}\n"
    }

    #[test]
    fn updates_a_full_run_log_tree_through_the_atomic_writer() {
        let directory = tempfile::tempdir().expect("temporary root should create");
        let layout = layout(directory.path());
        let path = layout.manifest_path();
        fs::create_dir_all(path.parent().expect("manifest parent"))
            .expect("manifest parent should create");
        fs::write(&path, v2_manifest()).expect("manifest should seed");
        let store = ManifestStore::open(directory.path()).expect("root should open");
        let updates: Vec<ManifestUpdate> = vec![
            ("steps_ran.step8".to_owned(), Value::Bool(true)),
            ("pr_number".to_owned(), json!(17)),
        ];

        let written = store
            .update(&layout, &updates, "2026-08-05T00:00:00Z")
            .expect("update should write");

        assert_eq!(written, path);
        assert_eq!(
            fs::read_to_string(&path).expect("manifest should read"),
            concat!(
                "{\n",
                "  \"pr_number\": 17,\n",
                "  \"run_id\": \"run-1\",\n",
                "  \"schema_version\": 2,\n",
                "  \"skill\": \"implement\",\n",
                "  \"started_at\": \"t0\",\n",
                "  \"status\": \"partial\",\n",
                "  \"steps_ran\": {\n",
                "    \"step8\": true\n",
                "  },\n",
                "  \"updated_at\": \"2026-08-05T00:00:00Z\"\n",
                "}\n"
            )
        );
    }

    #[test]
    fn rejected_manifest_keeps_the_complete_old_destination() {
        let directory = tempfile::tempdir().expect("temporary root should create");
        let layout = layout(directory.path());
        let path = layout.manifest_path();
        fs::create_dir_all(path.parent().expect("manifest parent"))
            .expect("manifest parent should create");
        let original = "{\"schema_version\":99,\"status\":\"partial\"}\n";
        fs::write(&path, original).expect("manifest should seed");
        let store = ManifestStore::open(directory.path()).expect("root should open");

        let error = store
            .update(&layout, &[], "2026-08-05T00:00:00Z")
            .expect_err("unknown version should fail before publication");

        assert!(matches!(error, ManifestStoreError::Manifest(_)));
        assert_eq!(
            fs::read_to_string(path).expect("manifest should read"),
            original
        );
    }

    #[test]
    fn injected_pre_rename_failure_keeps_the_complete_old_manifest() {
        let directory = tempfile::tempdir().expect("temporary root should create");
        let layout = layout(directory.path());
        let path = layout.manifest_path();
        fs::create_dir_all(path.parent().expect("manifest parent"))
            .expect("manifest parent should create");
        let original = v2_manifest();
        fs::write(&path, original).expect("manifest should seed");
        let store = ManifestStore::open(directory.path()).expect("root should open");

        let error = store
            .update_with(
                &layout,
                &[],
                "2026-08-05T00:00:00Z",
                |root, target, rendered| {
                    crate::file_io::atomic_write_in_with(
                        root,
                        target,
                        true,
                        MANIFEST_FILE_MODE,
                        |file| {
                            file.write_all(rendered.as_bytes())?;
                            Err(io::Error::other("injected pre-rename failure"))
                        },
                    )
                    .map_err(ManifestStoreError::FileIo)
                },
            )
            .expect_err("injected publication should fail");

        assert!(matches!(error, ManifestStoreError::FileIo(_)));
        assert_eq!(
            fs::read_to_string(path).expect("manifest should read"),
            original
        );
    }

    #[test]
    fn refuses_a_layout_from_a_different_root_before_writing() {
        let first = tempfile::tempdir().expect("first temporary root should create");
        let second = tempfile::tempdir().expect("second temporary root should create");
        let store = ManifestStore::open(first.path()).expect("root should open");

        assert!(matches!(
            store.update(&layout(second.path()), &[], "2026-08-05T00:00:00Z"),
            Err(ManifestStoreError::RootMismatch { .. })
        ));
    }
}
