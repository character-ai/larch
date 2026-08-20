//! Self-edit attribution log reader for `/implement` (issue #6876).
//!
//! File-mutating subprocesses spawned by `/implement` record the repo-relative
//! paths they changed. The orchestrator consults this log before concluding
//! that a between-action working-tree change came from another runner.

use std::{
    collections::HashMap,
    env, fs,
    io::Write as _,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

use sha2::{Digest as _, Sha256};

/// File name of the attribution log inside an implement tmpdir.
pub const SELF_EDIT_LOG_NAME: &str = "self-edit-log.tsv";

const HEADER: &str = "recorded_epoch_s\tsource\tpath\tpost_sha256";
const HEADER_LINE: &str = "recorded_epoch_s\tsource\tpath\tpost_sha256\n";
const SESSION_PREFIXES: [&str; 2] = ["claude-implement-", "claude-review-"];
const SOURCE_MAX_LEN: usize = 64;

/// One recorded self-edit attribution row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SelfEditRecord {
    /// Epoch seconds the row was recorded.
    pub recorded_epoch_s: i64,
    /// Sanitized source token of the mutating subprocess.
    pub source: String,
    /// Repository-relative path that was changed.
    pub path: String,
    /// SHA-256 of the file right after the edit.
    pub post_sha256: String,
}

/// Strip TSV-hostile control characters so a path round-trips exactly.
#[must_use]
pub fn normalize_path(value: &str) -> String {
    value.replace(['\t', '\r', '\n'], " ").trim().to_owned()
}

/// Parse recorded attribution rows; tolerant of a missing or partial log.
#[must_use]
pub fn read_self_edits(tmpdir: &Path) -> Vec<SelfEditRecord> {
    let path = tmpdir.join(SELF_EDIT_LOG_NAME);
    let Ok(metadata) = fs::symlink_metadata(&path) else {
        return Vec::new();
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Vec::new();
    }
    let Ok(bytes) = fs::read(&path) else {
        return Vec::new();
    };
    let text = String::from_utf8_lossy(&bytes);
    let mut records = Vec::new();
    for line in text.lines() {
        if line.is_empty() || line == HEADER {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        let [epoch_raw, source, rel_path, sha] = fields.as_slice() else {
            continue;
        };
        let Ok(recorded_epoch_s) = epoch_raw.trim().parse::<i64>() else {
            continue;
        };
        records.push(SelfEditRecord {
            recorded_epoch_s,
            source: (*source).to_owned(),
            path: (*rel_path).to_owned(),
            post_sha256: (*sha).to_owned(),
        });
    }
    records
}

/// SHA-256 of a repo-relative file, or a bounded sentinel when unreadable.
#[must_use]
pub fn file_sha256(repo_root: &Path, rel: &str) -> String {
    let target = repo_root.join(rel);
    match fs::symlink_metadata(&target) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {
            fs::read(&target).map_or_else(
                |_| "unreadable".to_owned(),
                |bytes| format!("{:x}", Sha256::digest(bytes)),
            )
        }
        Ok(_) | Err(_) => "missing".to_owned(),
    }
}

/// Map each repo-relative path to its current sha256 (see [`file_sha256`]).
#[must_use]
pub fn digest_paths(repo_root: &Path, paths: &[String]) -> HashMap<String, String> {
    paths
        .iter()
        .map(|path| (path.clone(), file_sha256(repo_root, path)))
        .collect()
}

/// Sanitize a source token to the `[A-Za-z0-9_.:@/-]` grammar, bounded length.
fn sanitize_source(source: &str) -> String {
    let cleaned: String = source
        .trim()
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '_' | '.' | ':' | '@' | '/' | '-') {
                ch
            } else {
                '-'
            }
        })
        .take(SOURCE_MAX_LEN)
        .collect();
    if cleaned.is_empty() {
        "unknown".to_owned()
    } else {
        cleaned
    }
}

fn append_rows(path: &Path, rows: &[(i64, String, String, String)]) {
    if let Some(parent) = path.parent() {
        let _ignored = fs::create_dir_all(parent);
    }
    if fs::symlink_metadata(path).is_ok_and(|meta| meta.file_type().is_symlink()) {
        return;
    }
    let needs_header = fs::metadata(path).map_or(true, |meta| meta.len() == 0);
    let Ok(mut handle) = fs::OpenOptions::new().create(true).append(true).open(path) else {
        return;
    };
    if needs_header {
        let _ignored = handle.write_all(HEADER_LINE.as_bytes());
    }
    for (epoch_s, source, rel_path, sha) in rows {
        let _ignored =
            handle.write_all(format!("{epoch_s}\t{source}\t{rel_path}\t{sha}\n").as_bytes());
    }
    drop(handle);
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        let _ignored = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
    }
}

/// Append one attribution row per changed path; returns the row count.
///
/// Best-effort: never panics, so a checks or repair-loop caller is never
/// disrupted by logging. Returns 0 when the tmpdir is unusable, no paths are
/// supplied, or any write fails. `now_epoch_s` overrides the clock for tests.
#[must_use]
pub fn record_self_edits(
    tmpdir: &Path,
    source: &str,
    paths: &[String],
    repo_root: &Path,
    now_epoch_s: Option<i64>,
) -> usize {
    let Ok(metadata) = fs::symlink_metadata(tmpdir) else {
        return 0;
    };
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        return 0;
    }
    let epoch_s = now_epoch_s.unwrap_or_else(|| {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |elapsed| {
                i64::try_from(elapsed.as_secs()).unwrap_or(i64::MAX)
            })
    });
    let source_token = sanitize_source(source);
    let mut rows: Vec<(i64, String, String, String)> = Vec::new();
    let mut seen: Vec<String> = Vec::new();
    for raw in paths {
        let rel = normalize_path(raw);
        if rel.is_empty() || seen.contains(&rel) {
            continue;
        }
        seen.push(rel.clone());
        let sha = file_sha256(repo_root, &rel);
        rows.push((epoch_s, source_token.clone(), rel, sha));
    }
    if rows.is_empty() {
        return 0;
    }
    append_rows(&tmpdir.join(SELF_EDIT_LOG_NAME), &rows);
    rows.len()
}

fn canonical_dir(path: &Path) -> Option<PathBuf> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        return None;
    }
    fs::canonicalize(path).ok()
}

/// Validate an implement or review session tmpdir under its accepted roots.
///
/// Mirrors the shared `checks` tmpdir contract: an absolute, non-symlink
/// session directory whose canonical name carries a session prefix and that
/// lives under the larch session cache or directly under the system tmpdir.
#[must_use]
pub fn validate_session_tmpdir(tmpdir: &str) -> Option<PathBuf> {
    if !tmpdir.starts_with('/') {
        return None;
    }
    let canonical = canonical_dir(Path::new(tmpdir))?;
    let name = canonical.file_name()?.to_string_lossy().into_owned();
    if !SESSION_PREFIXES
        .iter()
        .any(|prefix| name.starts_with(prefix))
    {
        return None;
    }
    let xdg_cache = env::var("XDG_CACHE_HOME").unwrap_or_default();
    let xdg_cache = xdg_cache.trim();
    let cache_root = if xdg_cache.is_empty() {
        PathBuf::from(env::var("HOME").unwrap_or_default()).join(".cache")
    } else {
        PathBuf::from(xdg_cache)
    };
    if let Some(sessions) = canonical_dir(&cache_root.join("larch").join("sessions"))
        && canonical.starts_with(&sessions)
    {
        return Some(canonical);
    }
    let parent = canonical.parent()?.to_path_buf();
    for candidate in ["/tmp", "/private/tmp"] {
        if canonical_dir(Path::new(candidate)).is_some_and(|resolved| parent == resolved) {
            return Some(canonical);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn normalize_path_strips_control_characters() {
        assert_eq!(normalize_path("  a\tb\rc\nd  "), "a b c d");
        assert_eq!(normalize_path(""), "");
    }

    #[test]
    fn read_self_edits_skips_header_and_malformed_rows() {
        let root = TempDir::new().expect("temp");
        fs::write(
            root.path().join(SELF_EDIT_LOG_NAME),
            format!("{HEADER}\n1\tlint-fix\ta.py\tdeadbeef\nshort\trow\n2\tsrc\tb.py\n3x\ts\tc.py\th\n7\ts2\td.py\th2\n"),
        )
        .expect("write");
        let records = read_self_edits(root.path());
        assert_eq!(records.len(), 2);
        assert_eq!(records[0].path, "a.py");
        assert_eq!(records[0].recorded_epoch_s, 1);
        assert_eq!(records[1].source, "s2");
        assert!(read_self_edits(&root.path().join("absent")).is_empty());
    }

    #[test]
    fn file_sha256_reports_sentinels() {
        let root = TempDir::new().expect("temp");
        fs::write(root.path().join("a.txt"), "x").expect("write");
        assert_eq!(
            file_sha256(root.path(), "a.txt"),
            "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
        );
        assert_eq!(file_sha256(root.path(), "missing.txt"), "missing");
    }

    #[test]
    fn validate_session_tmpdir_requires_prefix_and_root() {
        assert!(validate_session_tmpdir("relative").is_none());
        assert!(validate_session_tmpdir("/larch-self-edit-missing").is_none());
        let root = TempDir::new().expect("temp");
        let session = root.path().join("claude-implement-parity");
        fs::create_dir_all(&session).expect("session");
        assert!(
            validate_session_tmpdir(&session.to_string_lossy()).is_none(),
            "a session outside the accepted roots is refused"
        );
    }
}
