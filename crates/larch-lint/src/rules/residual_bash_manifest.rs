//! Shared strict reader for the residual Bash inventory.

use std::collections::BTreeSet;

use crate::{LintError, RepoPath, Repository};

pub(super) const MANIFEST_PATH: &str = "scripts/residual-bash-paths.txt";
const EXCLUDED_PREFIXES: [&str; 2] = ["larch-logs/", "node_modules/"];

pub(super) fn required_paths(
    repository: &Repository,
) -> Result<BTreeSet<RepoPath>, LintError> {
    let manifest = RepoPath::from_trusted(MANIFEST_PATH);
    let source = repository.read_required_utf8(
        &manifest,
        format!("could not read residual bash manifest: {MANIFEST_PATH}"),
    )?;
    let mut paths = BTreeSet::new();
    for (index, line) in source.lines().enumerate() {
        let raw = line.trim();
        if raw.is_empty() || raw.starts_with('#') {
            continue;
        }
        validate_residual_path(raw, index + 1)?;
        let path = RepoPath::from_trusted(raw);
        if !paths.insert(path.clone()) {
            return Err(LintError::new(format!(
                "duplicate residual bash path at {MANIFEST_PATH}:{}: {raw}",
                index + 1
            )));
        }
        if repository.paths().binary_search(&path).is_err() {
            return Err(LintError::new(format!(
                "missing residual bash path: {raw}"
            )));
        }
    }
    Ok(paths)
}

fn validate_residual_path(raw: &str, line: usize) -> Result<(), LintError> {
    if raw.starts_with('/') || raw.contains('\0') || raw.split('/').any(|part| part == "..") {
        return Err(LintError::new(format!(
            "invalid residual bash path: {raw:?}"
        )));
    }
    if EXCLUDED_PREFIXES
        .iter()
        .any(|prefix| raw.starts_with(prefix))
    {
        return Err(LintError::new(format!(
            "excluded residual bash path: {raw:?}"
        )));
    }
    if raw.strip_suffix(".sh").is_none() && raw.strip_suffix(".inc.bash").is_none() {
        return Err(LintError::new(format!(
            "{MANIFEST_PATH}:{line}: residual bash path must end with .sh or .inc.bash: {raw:?}",
        )));
    }
    Ok(())
}
