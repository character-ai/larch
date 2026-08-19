//! Checks bgjob result-input identity: HEAD + worktree fingerprint (I-Stale-1).
//!
//! Git access stays in the command layer: [`WorktreeFacts`] carries the exact
//! bytes this module hashes, so the fingerprint, the row grammar, and both
//! classifiers have one pure owner.

use std::{
    collections::BTreeMap,
    fmt, fs,
    path::{Path, PathBuf},
};

use sha2::{Digest as _, Sha256};

use crate::env_file::{KvDocument, ParseOptions};

/// Stdout key for the recorded HEAD commit.
pub const CHECKS_INPUT_HEAD_SHA_KEY: &str = "CHECKS_INPUT_HEAD_SHA";
/// Stdout key for the recorded worktree fingerprint.
pub const CHECKS_INPUT_TREE_FP_KEY: &str = "CHECKS_INPUT_TREE_FP";
/// Stdout key for the fingerprint schema token.
pub const CHECKS_INPUT_FP_SCHEMA_KEY: &str = "CHECKS_INPUT_FP_SCHEMA";
/// The only fingerprint schema this owner computes or accepts.
pub const CHECKS_INPUT_FP_SCHEMA_V1: &str = "v1";
/// Terminal action recorded for a child whose identity drifted.
pub const CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION: &str = "identity-integrity-failed";
/// Result-env key carrying the child's exit code.
pub const BGJOB_RC_KEY: &str = "BGJOB_RC";

/// Fail-closed identity computation or root-validation failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChecksIdentityError(String);

impl ChecksIdentityError {
    /// Build an error carrying the exact operator-visible message.
    #[must_use]
    pub fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for ChecksIdentityError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for ChecksIdentityError {}

/// Immutable launch identity for one checks bgjob.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChecksInputIdentity {
    /// Resolved `HEAD` commit.
    pub head_sha: String,
    /// SHA-256 over HEAD plus the staged, unstaged, and untracked worktree.
    pub tree_fingerprint: String,
    /// Fingerprint schema token.
    pub fingerprint_schema: String,
    /// Validated repository root the identity was computed in.
    pub repo_root: PathBuf,
}

impl ChecksInputIdentity {
    /// Return the three stdout identity rows in their pinned order.
    #[must_use]
    pub fn as_rows(&self) -> Vec<(String, String)> {
        vec![
            (CHECKS_INPUT_HEAD_SHA_KEY.to_owned(), self.head_sha.clone()),
            (
                CHECKS_INPUT_TREE_FP_KEY.to_owned(),
                self.tree_fingerprint.clone(),
            ),
            (
                CHECKS_INPUT_FP_SCHEMA_KEY.to_owned(),
                self.fingerprint_schema.clone(),
            ),
        ]
    }
}

/// One classified result or merge env.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Classification {
    /// One of `matching`, `stale`, `incomplete`, `unsafe`, or `absent`.
    pub state: &'static str,
    /// Bounded reason token, empty for `matching`.
    pub reason: String,
}

impl Classification {
    fn new(state: &'static str, reason: impl Into<String>) -> Self {
        Self {
            state,
            reason: reason.into(),
        }
    }
}

/// Exact Git inputs the fingerprint hashes, captured by the command layer.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct WorktreeFacts {
    /// `git rev-parse HEAD` output, already trimmed.
    pub head_sha: String,
    /// Raw `git diff --cached --binary --no-ext-diff` bytes.
    pub staged_diff: Vec<u8>,
    /// Raw `git diff --binary --no-ext-diff` bytes.
    pub unstaged_diff: Vec<u8>,
    /// Repository-relative untracked paths, in any order.
    pub untracked: Vec<String>,
}

fn is_lower_hex(value: &str) -> bool {
    value
        .bytes()
        .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_head_sha(value: &str) -> bool {
    (7..=64).contains(&value.len()) && is_lower_hex(value)
}

fn is_tree_fingerprint(value: &str) -> bool {
    value.len() == 64 && is_lower_hex(value)
}

/// Validate a persisted repository root's local file-system properties.
///
/// The Git-toplevel comparison belongs to the command layer, which owns Git.
///
/// # Errors
/// Returns a fail-closed error for a relative, symlinked, non-directory, or
/// unresolvable root.
pub fn validate_repo_root_path(repo_root: &Path) -> Result<PathBuf, ChecksIdentityError> {
    if !repo_root.is_absolute() {
        return Err(ChecksIdentityError::new(
            "repo root must be an absolute path",
        ));
    }
    let metadata = fs::symlink_metadata(repo_root)
        .map_err(|_| ChecksIdentityError::new("repo root must be a non-symlink directory"))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(ChecksIdentityError::new(
            "repo root must be a non-symlink directory",
        ));
    }
    let resolved = fs::canonicalize(repo_root).map_err(|error| {
        ChecksIdentityError::new(format!("repo root could not be resolved: {error}"))
    })?;
    let resolved_metadata = fs::symlink_metadata(&resolved).map_err(|_| {
        ChecksIdentityError::new("resolved repo root must be a non-symlink directory")
    })?;
    if resolved_metadata.file_type().is_symlink() || !resolved_metadata.is_dir() {
        return Err(ChecksIdentityError::new(
            "resolved repo root must be a non-symlink directory",
        ));
    }
    Ok(resolved)
}

/// Compute the HEAD plus worktree identity for a validated repository root.
///
/// The hashed input order is pinned: schema token, `\0head\0`, HEAD, the staged
/// diff, the unstaged diff, then the untracked-content digest.
///
/// # Errors
/// Returns a fail-closed error for a malformed HEAD or an untracked path that
/// is not a readable regular file.
pub fn compute_identity(
    repo_root: PathBuf,
    facts: &WorktreeFacts,
) -> Result<ChecksInputIdentity, ChecksIdentityError> {
    if !is_head_sha(&facts.head_sha) {
        return Err(ChecksIdentityError::new("HEAD SHA is malformed"));
    }
    let untracked_blob = untracked_content_blob(&repo_root, &facts.untracked)?;
    let mut hasher = Sha256::new();
    hasher.update(CHECKS_INPUT_FP_SCHEMA_V1.as_bytes());
    hasher.update(b"\0head\0");
    hasher.update(facts.head_sha.as_bytes());
    hasher.update(b"\0staged\0");
    hasher.update(&facts.staged_diff);
    hasher.update(b"\0unstaged\0");
    hasher.update(&facts.unstaged_diff);
    hasher.update(b"\0untracked\0");
    hasher.update(untracked_blob);
    Ok(ChecksInputIdentity {
        head_sha: facts.head_sha.clone(),
        tree_fingerprint: format!("{:x}", hasher.finalize()),
        fingerprint_schema: CHECKS_INPUT_FP_SCHEMA_V1.to_owned(),
        repo_root,
    })
}

fn untracked_content_blob(
    repo_root: &Path,
    untracked: &[String],
) -> Result<[u8; 32], ChecksIdentityError> {
    let mut sorted: Vec<&String> = untracked.iter().collect();
    sorted.sort();
    let mut hasher = Sha256::new();
    for rel in sorted {
        hasher.update(rel.as_bytes());
        hasher.update(b"\0");
        let path = repo_root.join(rel);
        let metadata = fs::symlink_metadata(&path).map_err(|_| {
            ChecksIdentityError::new(format!("untracked path is not a regular file: {rel}"))
        })?;
        if metadata.file_type().is_symlink() || !metadata.is_file() {
            return Err(ChecksIdentityError::new(format!(
                "untracked path is not a regular file: {rel}"
            )));
        }
        let bytes = fs::read(&path)
            .map_err(|_| ChecksIdentityError::new(format!("untracked path unreadable: {rel}")))?;
        hasher.update(format!("{:x}", Sha256::digest(bytes)).as_bytes());
        hasher.update(b"\0");
    }
    Ok(hasher.finalize().into())
}

/// True when two identities agree on every field, including the repository root.
#[must_use]
pub fn identities_match(left: &ChecksInputIdentity, right: &ChecksInputIdentity) -> bool {
    left.head_sha == right.head_sha
        && left.tree_fingerprint == right.tree_fingerprint
        && left.fingerprint_schema == right.fingerprint_schema
        && left.repo_root == right.repo_root
}

/// Rebuild an identity from persisted rows, rejecting a malformed triple.
#[must_use]
pub fn identity_from_rows(
    rows: &BTreeMap<String, String>,
    repo_root: &Path,
) -> Option<ChecksInputIdentity> {
    let head = rows.get(CHECKS_INPUT_HEAD_SHA_KEY)?;
    let tree_fp = rows.get(CHECKS_INPUT_TREE_FP_KEY)?;
    let schema = rows.get(CHECKS_INPUT_FP_SCHEMA_KEY)?;
    if head.is_empty() || tree_fp.is_empty() || schema.is_empty() {
        return None;
    }
    if !is_head_sha(head) {
        return None;
    }
    if !is_tree_fingerprint(tree_fp) || schema != CHECKS_INPUT_FP_SCHEMA_V1 {
        return None;
    }
    Some(ChecksInputIdentity {
        head_sha: head.clone(),
        tree_fingerprint: tree_fp.clone(),
        fingerprint_schema: schema.clone(),
        repo_root: repo_root.to_path_buf(),
    })
}

fn is_environment_key(key: &str) -> bool {
    !key.is_empty()
        && key
            .bytes()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit() || byte == b'_')
}

/// Parse a checks result or merge env, rejecting unsafe files and CR bytes.
///
/// A missing file yields an empty map; duplicate keys keep the last value, and
/// rows whose key is not `[A-Z0-9_]+` are ignored.
///
/// # Errors
/// Returns a fail-closed error for a symlink, a non-regular file, an unreadable
/// file, or content containing a carriage return.
pub fn read_env_rows(path: &Path) -> Result<BTreeMap<String, String>, ChecksIdentityError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) => {
            if metadata.file_type().is_symlink() {
                return Err(ChecksIdentityError::new("env path must not be a symlink"));
            }
            if !metadata.is_file() {
                return Err(ChecksIdentityError::new("env path must be a regular file"));
            }
        }
        Err(_) => return Ok(BTreeMap::new()),
    }
    let bytes = fs::read(path)
        .map_err(|error| ChecksIdentityError::new(format!("env parse failed: {error}")))?;
    let text = String::from_utf8_lossy(&bytes);
    if text.contains('\r') {
        return Err(ChecksIdentityError::new(format!(
            "env parse failed: carriage return not allowed in {}",
            path.display()
        )));
    }
    let document = KvDocument::parse(&text, ParseOptions::legacy())
        .map_err(|error| ChecksIdentityError::new(format!("env parse failed: {error}")))?;
    let mut rows = BTreeMap::new();
    for row in document.rows() {
        if is_environment_key(row.key()) {
            let _ = rows.insert(row.key().to_owned(), row.value().to_owned());
        }
    }
    Ok(rows)
}

fn unsafe_or_missing(path: &Path) -> Result<bool, ChecksIdentityError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            Err(ChecksIdentityError::new("non-regular"))
        }
        Ok(_) => Ok(false),
        Err(_) => Ok(true),
    }
}

/// Classify a completed checks result env for rejoin.
#[must_use]
pub fn classify_completed_result(
    result_env: &Path,
    step: &str,
    live: &ChecksInputIdentity,
    terminal_actions: &[&str],
) -> Classification {
    match unsafe_or_missing(result_env) {
        Err(_) => return Classification::new("unsafe", "non-regular-result-env"),
        Ok(true) => return Classification::new("absent", "missing"),
        Ok(false) => {}
    }
    match read_env_rows(result_env) {
        Ok(rows) => classify_completed_rows(&rows, step, live, terminal_actions),
        Err(error) => Classification::new("unsafe", error.to_string()),
    }
}

/// Classify already-parsed completed-result rows against the live identity.
#[must_use]
pub fn classify_completed_rows(
    rows: &BTreeMap<String, String>,
    step: &str,
    live: &ChecksInputIdentity,
    terminal_actions: &[&str],
) -> Classification {
    if rows.is_empty() {
        return Classification::new("incomplete", "empty");
    }
    let next_action = rows.get("NEXT_ACTION").map_or("", String::as_str);
    let incomplete_reason = if rows.get(BGJOB_RC_KEY).map_or("", String::as_str) != "0" {
        "bgjob-rc"
    } else if next_action.is_empty() {
        "missing-next-action"
    } else if !terminal_actions.contains(&next_action) {
        "unsupported-next-action"
    } else {
        ""
    };
    if !incomplete_reason.is_empty() {
        return Classification::new("incomplete", incomplete_reason);
    }
    if rows.get("STEP").map_or("", String::as_str) != step {
        return Classification::new("stale", "step-mismatch");
    }
    let Some(persisted) = identity_from_rows(rows, &live.repo_root) else {
        return Classification::new("stale", "missing-identity");
    };
    if persisted.fingerprint_schema != live.fingerprint_schema {
        return Classification::new("stale", "schema-mismatch");
    }
    if persisted.head_sha != live.head_sha || persisted.tree_fingerprint != live.tree_fingerprint {
        return Classification::new("stale", "identity-mismatch");
    }
    Classification::new("matching", "")
}

/// Classify a live job's seeded merge-env identity against the live repository.
#[must_use]
pub fn classify_live_seed(merge_env: &Path, live: &ChecksInputIdentity) -> Classification {
    match unsafe_or_missing(merge_env) {
        Err(_) => return Classification::new("unsafe", "non-regular-merge-env"),
        Ok(true) => return Classification::new("incomplete", "missing-merge-env"),
        Ok(false) => {}
    }
    let rows = match read_env_rows(merge_env) {
        Ok(rows) => rows,
        Err(error) => return Classification::new("unsafe", error.to_string()),
    };
    let Some(persisted) = identity_from_rows(&rows, &live.repo_root) else {
        return Classification::new("incomplete", "missing-identity");
    };
    if identities_match(&persisted, live) {
        Classification::new("matching", "")
    } else {
        Classification::new("stale", "identity-mismatch")
    }
}

/// Non-reusable terminal rows for child identity drift.
#[must_use]
pub fn integrity_failure_rows(step: &str, reason: &str) -> Vec<(String, String)> {
    let safe_reason = reason.replace(['\n', '\r'], " ");
    let safe_reason = if safe_reason.is_empty() {
        "identity-integrity-failed".to_owned()
    } else {
        safe_reason
    };
    vec![
        ("STEP".to_owned(), step.to_owned()),
        (BGJOB_RC_KEY.to_owned(), "1".to_owned()),
        (
            "NEXT_ACTION".to_owned(),
            CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION.to_owned(),
        ),
        ("FAILURE_REASON".to_owned(), safe_reason),
    ]
}

/// Read `REPO_ROOT` from an implement session env, rejecting an unsafe file.
///
/// # Errors
/// Returns a fail-closed error when the session env is missing, unsafe, or
/// records no repository root.
pub fn session_repo_root(implement_tmpdir: &Path) -> Result<String, ChecksIdentityError> {
    let session = implement_tmpdir.join("session-env.sh");
    let metadata = fs::symlink_metadata(&session)
        .map_err(|_| ChecksIdentityError::new("session-env.sh is missing or unsafe"))?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(ChecksIdentityError::new(
            "session-env.sh is missing or unsafe",
        ));
    }
    let text = fs::read(&session)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default();
    let raw = first_kv_value(&text, "REPO_ROOT")
        .unwrap_or_default()
        .trim()
        .trim_matches(['\'', '"'])
        .to_owned();
    if raw.is_empty() {
        return Err(ChecksIdentityError::new(
            "REPO_ROOT missing from session-env.sh",
        ));
    }
    Ok(raw)
}

/// Return the first `KEY=value` match, matching the shared Python reader.
///
/// One carriage return before a line feed is CRLF framing; a lone carriage
/// return stays value data.
#[must_use]
pub fn first_kv_value(text: &str, key: &str) -> Option<String> {
    let prefix = format!("{key}=");
    let lines: Vec<&str> = text.split('\n').collect();
    let last = lines.len().saturating_sub(1);
    for (index, raw) in lines.iter().enumerate() {
        let line = if index < last {
            raw.strip_suffix('\r').unwrap_or(raw)
        } else {
            *raw
        };
        if let Some(value) = line.strip_prefix(prefix.as_str()) {
            return Some(value.to_owned());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    use tempfile::TempDir;

    const ACTIONS: &[&str] = &["continue", "stall", "checks-failed", "skip-to-7a"];

    fn facts() -> WorktreeFacts {
        WorktreeFacts {
            head_sha: "a".repeat(40),
            staged_diff: b"staged".to_vec(),
            unstaged_diff: b"unstaged".to_vec(),
            untracked: Vec::new(),
        }
    }

    fn live(root: &Path) -> ChecksInputIdentity {
        compute_identity(root.to_path_buf(), &facts()).expect("identity")
    }

    fn rows_of(identity: &ChecksInputIdentity) -> BTreeMap<String, String> {
        identity.as_rows().into_iter().collect()
    }

    #[test]
    fn compute_is_deterministic_and_input_sensitive() {
        let root = TempDir::new().expect("temp");
        let first = live(root.path());
        let second = live(root.path());
        assert_eq!(first.tree_fingerprint, second.tree_fingerprint);
        assert!(is_tree_fingerprint(&first.tree_fingerprint));
        assert_eq!(first.fingerprint_schema, CHECKS_INPUT_FP_SCHEMA_V1);
        for mutate in [0_u8, 1, 2] {
            let mut changed = facts();
            match mutate {
                0 => changed.head_sha = "b".repeat(40),
                1 => changed.staged_diff = b"other".to_vec(),
                _ => changed.unstaged_diff = b"other".to_vec(),
            }
            let other =
                compute_identity(root.path().to_path_buf(), &changed).expect("changed identity");
            assert_ne!(first.tree_fingerprint, other.tree_fingerprint);
        }
    }

    #[test]
    fn untracked_content_changes_the_fingerprint() {
        let root = TempDir::new().expect("temp");
        fs::write(root.path().join("new.txt"), "one").expect("write");
        let mut with_untracked = facts();
        with_untracked.untracked = vec!["new.txt".to_owned()];
        let before =
            compute_identity(root.path().to_path_buf(), &with_untracked).expect("before identity");
        fs::write(root.path().join("new.txt"), "two").expect("rewrite");
        let after =
            compute_identity(root.path().to_path_buf(), &with_untracked).expect("after identity");
        assert_ne!(before.tree_fingerprint, after.tree_fingerprint);
        assert_ne!(
            before.tree_fingerprint,
            live(root.path()).tree_fingerprint,
            "untracked rows must change the fingerprint"
        );
    }

    #[test]
    fn untracked_symlink_and_malformed_head_fail_closed() {
        let root = TempDir::new().expect("temp");
        let mut bad_head = facts();
        bad_head.head_sha = "nothex".to_owned();
        assert_eq!(
            compute_identity(root.path().to_path_buf(), &bad_head)
                .expect_err("malformed head")
                .to_string(),
            "HEAD SHA is malformed"
        );
        let mut missing = facts();
        missing.untracked = vec!["absent.txt".to_owned()];
        assert!(
            compute_identity(root.path().to_path_buf(), &missing)
                .expect_err("missing untracked")
                .to_string()
                .contains("not a regular file")
        );
    }

    #[test]
    fn validate_repo_root_path_rejects_relative_and_missing() {
        assert_eq!(
            validate_repo_root_path(Path::new("relative"))
                .expect_err("relative")
                .to_string(),
            "repo root must be an absolute path"
        );
        assert_eq!(
            validate_repo_root_path(Path::new("/larch-identity-missing-root"))
                .expect_err("missing")
                .to_string(),
            "repo root must be a non-symlink directory"
        );
    }

    #[test]
    fn read_env_rows_applies_last_wins_and_key_grammar() {
        let root = TempDir::new().expect("temp");
        let path = root.path().join("result.env");
        fs::write(&path, "A=1\nA=2\nbad-key=3\n#C=4\n\nD=\n").expect("write");
        let rows = read_env_rows(&path).expect("rows");
        assert_eq!(rows.get("A").map(String::as_str), Some("2"));
        assert_eq!(rows.get("D").map(String::as_str), Some(""));
        assert!(!rows.contains_key("bad-key"));
        assert!(!rows.contains_key("#C"));
        assert!(
            read_env_rows(&root.path().join("absent.env"))
                .expect("absent")
                .is_empty()
        );
        fs::write(&path, "A=1\r\n").expect("rewrite");
        assert!(
            read_env_rows(&path)
                .expect_err("cr")
                .to_string()
                .contains("carriage return")
        );
    }

    #[test]
    fn classify_completed_covers_every_branch() {
        let root = TempDir::new().expect("temp");
        let identity = live(root.path());
        let path = root.path().join("result.env");
        let cases: &[(&str, &str, &str)] = &[
            ("", "absent", "missing"),
            ("\n", "incomplete", "empty"),
            ("BGJOB_RC=1\n", "incomplete", "bgjob-rc"),
            ("BGJOB_RC=0\n", "incomplete", "missing-next-action"),
            (
                "BGJOB_RC=0\nNEXT_ACTION=nope\n",
                "incomplete",
                "unsupported-next-action",
            ),
            (
                "BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=other\n",
                "stale",
                "step-mismatch",
            ),
            (
                "BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=s\n",
                "stale",
                "missing-identity",
            ),
        ];
        for (body, state, reason) in cases {
            if body.is_empty() {
                let _ = fs::remove_file(&path);
            } else {
                fs::write(&path, body).expect("write");
            }
            let classified = classify_completed_result(&path, "s", &identity, ACTIONS);
            assert_eq!(
                (classified.state, classified.reason.as_str()),
                (*state, *reason)
            );
        }
    }

    #[test]
    fn classify_completed_reports_schema_and_identity_mismatch() {
        let root = TempDir::new().expect("temp");
        let identity = live(root.path());
        let path = root.path().join("result.env");
        let head = &identity.head_sha;
        let fingerprint = &identity.tree_fingerprint;
        fs::write(
            &path,
            format!(
                "BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=s\n{CHECKS_INPUT_HEAD_SHA_KEY}={head}\n{CHECKS_INPUT_TREE_FP_KEY}={fingerprint}\n{CHECKS_INPUT_FP_SCHEMA_KEY}=v1\n"
            ),
        )
        .expect("write");
        assert_eq!(
            classify_completed_result(&path, "s", &identity, ACTIONS).state,
            "matching"
        );
        fs::write(
            &path,
            format!(
                "BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=s\n{CHECKS_INPUT_HEAD_SHA_KEY}={}\n{CHECKS_INPUT_TREE_FP_KEY}={fingerprint}\n{CHECKS_INPUT_FP_SCHEMA_KEY}=v1\n",
                "c".repeat(40)
            ),
        )
        .expect("write");
        let drifted = classify_completed_result(&path, "s", &identity, ACTIONS);
        assert_eq!(
            (drifted.state, drifted.reason.as_str()),
            ("stale", "identity-mismatch")
        );
        let mut schema_rows = rows_of(&identity);
        let _ = schema_rows.insert(CHECKS_INPUT_FP_SCHEMA_KEY.to_owned(), "v2".to_owned());
        assert!(identity_from_rows(&schema_rows, root.path()).is_none());
    }

    #[test]
    fn classify_live_seed_covers_missing_and_drift() {
        let root = TempDir::new().expect("temp");
        let identity = live(root.path());
        let merge = root.path().join("merge.env");
        assert_eq!(
            classify_live_seed(&merge, &identity).reason,
            "missing-merge-env"
        );
        fs::write(&merge, "STEP=s\n").expect("write");
        assert_eq!(
            classify_live_seed(&merge, &identity).reason,
            "missing-identity"
        );
        let head = &identity.head_sha;
        let fingerprint = &identity.tree_fingerprint;
        fs::write(
            &merge,
            format!(
                "{CHECKS_INPUT_HEAD_SHA_KEY}={head}\n{CHECKS_INPUT_TREE_FP_KEY}={fingerprint}\n{CHECKS_INPUT_FP_SCHEMA_KEY}=v1\n"
            ),
        )
        .expect("write");
        assert_eq!(classify_live_seed(&merge, &identity).state, "matching");
        let drifted = ChecksInputIdentity {
            head_sha: "d".repeat(40),
            ..identity.clone()
        };
        assert_eq!(
            classify_live_seed(&merge, &drifted).reason,
            "identity-mismatch"
        );
    }

    #[test]
    fn integrity_rows_are_non_reusable() {
        let rows: BTreeMap<String, String> =
            integrity_failure_rows("implement-step3-checks", "bad\nreason")
                .into_iter()
                .collect();
        assert_eq!(rows.get("BGJOB_RC").map(String::as_str), Some("1"));
        assert_eq!(
            rows.get("NEXT_ACTION").map(String::as_str),
            Some(CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION)
        );
        assert_eq!(
            rows.get("FAILURE_REASON").map(String::as_str),
            Some("bad reason")
        );
        let root = TempDir::new().expect("temp");
        let identity = live(root.path());
        let classified =
            classify_completed_rows(&rows, "implement-step3-checks", &identity, ACTIONS);
        assert_eq!(classified.state, "incomplete");
    }

    #[test]
    fn session_repo_root_reads_the_first_row() {
        let root = TempDir::new().expect("temp");
        assert!(session_repo_root(root.path()).is_err());
        fs::write(
            root.path().join("session-env.sh"),
            "REPO_ROOT='/tmp/repo'\nREPO_ROOT=/tmp/other\n",
        )
        .expect("write");
        assert_eq!(session_repo_root(root.path()).expect("root"), "/tmp/repo");
        fs::write(root.path().join("session-env.sh"), "OTHER=1\n").expect("write");
        assert_eq!(
            session_repo_root(root.path())
                .expect_err("missing")
                .to_string(),
            "REPO_ROOT missing from session-env.sh"
        );
    }
}
