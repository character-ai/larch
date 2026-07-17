//! Shared Rust source selection for ownership rules.

use std::collections::BTreeSet;
use std::path::Path;

use cargo_metadata::MetadataCommand;

use crate::{LintError, PathSelector, RepoPath, Repository};

/// Return whether a repository-relative path is a Rust test source.
#[must_use]
pub(super) fn is_test_path(path: &str) -> bool {
    path.split('/').any(|part| part == "tests")
        || path.rsplit('/').next().is_some_and(|name| {
            name.starts_with("test_") || name.ends_with("_test.rs") || name == "tests.rs"
        })
}

/// Select tracked Rust sources, preferring workspace package roots when present.
///
/// # Errors
///
/// Returns an error when path globs are invalid or Cargo metadata cannot be read
/// from a present workspace manifest.
pub(super) fn selected_rust_sources(
    repository: &Repository,
) -> Result<Vec<&RepoPath>, LintError> {
    let selector = PathSelector::new(&["**/*.rs"], &["**/target/**"])?;
    let paths = selector.select(repository);
    let Some(package_prefixes) = workspace_package_prefixes(repository.root())? else {
        return Ok(paths);
    };
    Ok(paths
        .into_iter()
        .filter(|path| {
            package_prefixes
                .iter()
                .any(|prefix| path_under_prefix(path.as_str(), prefix))
        })
        .collect())
}

fn workspace_package_prefixes(root: &Path) -> Result<Option<BTreeSet<String>>, LintError> {
    let manifest = root.join("Cargo.toml");
    if !manifest.is_file() {
        return Ok(None);
    }
    let metadata = MetadataCommand::new()
        .manifest_path(&manifest)
        .current_dir(root)
        .no_deps()
        .exec()
        .map_err(|error| LintError::new(format!("cannot read Cargo metadata: {error}")))?;
    let mut prefixes = BTreeSet::new();
    for package in metadata.packages {
        let package_root = package
            .manifest_path
            .parent()
            .ok_or_else(|| {
                LintError::new(format!(
                    "package {} manifest has no parent directory",
                    package.name
                ))
            })?;
        let relative = package_root.strip_prefix(root).map_err(|_| {
            LintError::new(format!(
                "package {} is outside the repository root",
                package.name
            ))
        })?;
        let prefix = relative
            .components()
            .map(|component| component.as_str())
            .collect::<Vec<_>>()
            .join("/");
        if prefix.is_empty() {
            prefixes.insert(String::new());
        } else {
            prefixes.insert(prefix);
        }
    }
    Ok(Some(prefixes))
}

fn path_under_prefix(path: &str, prefix: &str) -> bool {
    if prefix.is_empty() {
        return true;
    }
    path == prefix || path.starts_with(&format!("{prefix}/"))
}
