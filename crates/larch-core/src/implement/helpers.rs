//! Shared porcelain, digest, and tmpdir path helpers for implement dispatch.

use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    io::Write as _,
    path::{Component, Path, PathBuf},
};

use sha2::{Digest as _, Sha256};

/// Parsed git porcelain `-z` stream used by recovery-path filtering.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RecoveryParse {
    /// `(status, path)` pairs including synthetic delete rows for rename sources.
    pub tuples: BTreeSet<(String, String)>,
    /// Every path mentioned in the porcelain stream.
    pub paths: BTreeSet<String>,
}

/// Parse a NUL-delimited `git status --porcelain=v1 -z` file.
#[must_use]
pub fn parse_porcelain_z(path: &Path) -> RecoveryParse {
    let raw = fs::read(path).unwrap_or_default();
    let items: Vec<&[u8]> = raw.split(|byte| *byte == 0).collect();
    let mut tuples = BTreeSet::new();
    let mut paths = BTreeSet::new();
    let mut idx = 0;
    while idx < items.len() {
        let rec = items[idx];
        idx += 1;
        if rec.is_empty() {
            continue;
        }
        let status = String::from_utf8_lossy(&rec[..rec.len().min(2)]).into_owned();
        let rel = decode_rel(if rec.len() > 3 { &rec[3..] } else { &[] });
        if (status.contains('R') || status.contains('C')) && idx < items.len() {
            let old_item = items[idx];
            idx += 1;
            if !old_item.is_empty() {
                let old_rel = decode_rel(old_item);
                tuples.insert(("D ".to_owned(), old_rel.clone()));
                paths.insert(old_rel);
            }
        }
        tuples.insert((status, rel.clone()));
        paths.insert(rel);
    }
    RecoveryParse { tuples, paths }
}

fn decode_rel(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

/// Resolve an optional artifact path beneath the active implement tmpdir.
///
/// Matches Python `resolve_tmpdir_path`: absolute paths outside the tmpdir are
/// rebased by stripping the first path component.
#[must_use]
pub fn resolve_tmpdir_path(tmpdir: &Path, raw: &str, default_relpath: &str) -> PathBuf {
    if raw.is_empty() {
        return tmpdir.join(default_relpath);
    }
    let candidate = PathBuf::from(raw);
    if candidate.is_absolute() {
        if candidate.starts_with(tmpdir) {
            return candidate;
        }
        let rest: PathBuf = candidate
            .components()
            .skip(1)
            .filter(|component| !matches!(component, Component::RootDir))
            .collect();
        return tmpdir.join(rest);
    }
    tmpdir.join(candidate)
}

/// Load `digest\\trel` lines into a map keyed by relative path.
#[must_use]
pub fn load_digest_map(path: &Path) -> BTreeMap<String, String> {
    let Ok(text) = fs::read_to_string(path) else {
        return BTreeMap::new();
    };
    let mut digests = BTreeMap::new();
    for line in text.lines() {
        if let Some((digest, rel)) = line.split_once('\t') {
            digests.insert(rel.to_owned(), digest.to_owned());
        }
    }
    digests
}

/// Write sorted digest map lines (`digest\\trel\\n`).
///
/// # Errors
/// Returns an I/O error when the parent cannot be created or the write fails.
pub fn write_digest_map(path: &Path, digests: &BTreeMap<String, String>) -> std::io::Result<()> {
    let mut lines = Vec::with_capacity(digests.len());
    for (rel, digest) in digests {
        lines.push(format!("{digest}\t{rel}"));
    }
    let mut text = lines.join("\n");
    if !text.is_empty() {
        text.push('\n');
    }
    write_bytes_atomic(path, text.as_bytes())
}

/// Return the tmpdir path relative to `repo_root`, when it is inside the repo.
#[must_use]
pub fn tmpdir_rel_in_repo(repo_root: &Path, tmpdir: &Path) -> Option<String> {
    let repo_real = fs::canonicalize(repo_root).ok()?;
    let tmp_real = fs::canonicalize(tmpdir).ok()?;
    if tmp_real == repo_real {
        return Some(".".to_owned());
    }
    let rel = tmp_real.strip_prefix(&repo_real).ok()?;
    Some(rel.to_string_lossy().replace('\\', "/"))
}

/// True when `rel` is the tmpdir relative path or a descendant.
#[must_use]
pub fn rel_under_tmp(rel: &str, tmp_rel: Option<&str>) -> bool {
    let Some(tmp_rel) = tmp_rel else {
        return false;
    };
    if rel == tmp_rel {
        return true;
    }
    let prefix = tmp_rel.trim_end_matches('/');
    rel.starts_with(&format!("{prefix}/"))
}

/// SHA-256 hex digest of a repo-relative file, or `"missing"` on I/O failure.
#[must_use]
pub fn sha256_file(repo_root: &Path, rel: &str) -> String {
    fs::read(repo_root.join(rel)).map_or_else(
        |_| "missing".to_owned(),
        |bytes| format!("{:x}", Sha256::digest(bytes)),
    )
}

/// Atomically replace `path` with `data` via a sibling `.tmp` file.
///
/// # Errors
/// Returns an I/O error when directory creation or the write/rename fails.
pub fn write_bytes_atomic(path: &Path, data: &[u8]) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let tmp = path.with_file_name(format!(
        "{}.tmp",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("artifact")
    ));
    {
        let mut file = fs::File::create(&tmp)?;
        file.write_all(data)?;
        file.sync_all()?;
    }
    fs::rename(tmp, path)
}
