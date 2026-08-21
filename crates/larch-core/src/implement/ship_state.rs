//! Durable ship-state parsing, validation, and private publication.

use std::{
    ffi::OsStr,
    fmt, fs,
    path::{Component, Path, PathBuf},
};

use serde_json::Value;

use crate::{
    KeyPolicy, KvDocument, KvRow, ParseOptions, RenderOptions, ensure_under, private_atomic_write,
};

/// Every key the ship driver may retain in `ship-pr-state.sh`.
#[rustfmt::skip]
pub const SHIP_STATE_ALLOWED_KEYS: &[&str] = &[
    "PHASE", "BRANCH_NAME", "ISSUE_NUMBER", "RUN_ID",
    "REPO", "REPO_UNAVAILABLE", "FORKED_TARGET", "IMPLEMENT_TMPDIR",
    "MANIFEST_PATH", "MERGE", "DRAFT", "PR_CLOSED",
    "PR_NUMBER", "PR_URL", "PR_TITLE", "MERGE_RESULT",
    "CI_FIX_REBASE_PENDING", "CI_FIX_REBASE_PENDING_HEAD", "LAST_MONITORED_HEAD",
    "REBASE_COUNT", "FIX_ATTEMPTS", "ITERATION", "TRANSIENT_RETRIES",
    "RESUME_PHASE", "CALLER_KIND", "CONFLICT_FILES", "STALL_TRACKING", "STALL_STEP",
    "EXIT_CODE", "BAIL_REASON", "BAIL_NEEDS_USER_INPUT", "FAILED_RUN_ID", "BAIL_FAILURE_DETAIL_LOG",
    "EXPECTED_SESSION_ID", "EXPECTED_TMPDIR_BASENAME_PREFIX", "NO_LOGS_COMMIT", "NO_ADMIN_FALLBACK",
    "DESIGN_ONLY_DONE", "DEFERRED", "DONE_RENAME_APPLIED", "CI_PASSED", "TOOL_LABEL", "OOS_PENDING",
    "EMERGENCY_REPAIR_BRANCH", "ORIGINAL_BRANCH_FORBIDDEN", "MAIN_REPAIR_RUN_ID", "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER", "MAIN_HEALTH_REPAIR_COMMITTED", "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
    "MAIN_HEALTH_REPAIR_BASE_SHA", "MAIN_HEALTH_REPAIR_HEAD", "MAIN_HEALTH_HEAD_SHA",
];

/// Canonical ordered key set for a newly seeded ship state.
#[rustfmt::skip]
pub const INITIAL_SHIP_STATE_KEYS: &[&str] = &[
    "PHASE", "BRANCH_NAME", "ISSUE_NUMBER", "RUN_ID", "REPO",
    "REPO_UNAVAILABLE", "FORKED_TARGET", "MERGE", "DRAFT", "DEFERRED",
    "PR_CLOSED", "DONE_RENAME_APPLIED", "STALL_TRACKING", "STALL_STEP",
    "BAIL_NEEDS_USER_INPUT", "BAIL_REASON", "BAIL_FAILURE_DETAIL_LOG", "CI_PASSED",
    "PR_NUMBER", "PR_URL", "PR_TITLE", "RESUME_PHASE", "CALLER_KIND",
    "REBASE_COUNT", "FIX_ATTEMPTS", "ITERATION", "TRANSIENT_RETRIES", "FAILED_RUN_ID",
    "MANIFEST_PATH", "TOOL_LABEL", "DESIGN_ONLY_DONE", "EXPECTED_SESSION_ID",
    "EXPECTED_TMPDIR_BASENAME_PREFIX", "NO_ADMIN_FALLBACK", "NO_LOGS_COMMIT",
    "IMPLEMENT_TMPDIR", "CI_FIX_REBASE_PENDING", "OOS_PENDING", "EMERGENCY_REPAIR_BRANCH",
    "ORIGINAL_BRANCH_FORBIDDEN", "MAIN_REPAIR_RUN_ID", "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER", "MAIN_HEALTH_REPAIR_COMMITTED",
    "MAIN_HEALTH_REPAIR_FAILED_RUN_ID", "MAIN_HEALTH_REPAIR_BASE_SHA",
    "MAIN_HEALTH_REPAIR_HEAD", "MAIN_HEALTH_HEAD_SHA",
];

const MERGE_RESULTS: &[&str] = &[
    "merged",
    "admin_merged",
    "queued",
    "main_advanced",
    "ci_not_ready",
    "version_already_published",
    "policy_denied",
    "admin_failed",
    "review_required",
    "error",
    "already_merged",
];

/// Stable ship-state validation or persistence failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ShipStateError(String);

impl ShipStateError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for ShipStateError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for ShipStateError {}

/// Inputs whose validated projection creates the first ship-state document.
#[allow(clippy::struct_excessive_bools)] // one field per independent legacy CLI switch
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct InitialShipState {
    pub tmpdir: String,
    pub branch: String,
    pub issue: String,
    pub repo: String,
    pub run_id: String,
    pub manifest_path: String,
    pub tool_label: String,
    pub merge: bool,
    pub draft: bool,
    pub forked: bool,
    pub repo_unavailable: bool,
    pub deferred: bool,
    pub no_admin_fallback: bool,
    pub no_logs_commit: bool,
    pub expected_session_id: String,
    pub expected_tmpdir_basename_prefix: String,
    pub stall_tracking: bool,
    pub stall_step: String,
    pub bail_reason: String,
    pub bail_failure_detail_log: String,
}

/// One allowlisted ship-state document in stable insertion order.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ShipState {
    rows: Vec<(String, String)>,
}

impl ShipState {
    /// Read allowlisted rows with last-value duplicate semantics.
    ///
    /// # Errors
    /// Returns an error when the state cannot be read or parsed as the legacy KV grammar.
    pub fn read(path: &Path) -> Result<Self, ShipStateError> {
        let text = fs::read_to_string(path).map_err(|_error| {
            ShipStateError::new(format!(
                "cannot read existing ship state: {}",
                path.display()
            ))
        })?;
        let document = KvDocument::parse(&text, ParseOptions::legacy()).map_err(|_error| {
            ShipStateError::new(format!(
                "cannot read existing ship state: {}",
                path.display()
            ))
        })?;
        let mut rows: Vec<(String, String)> = Vec::new();
        for row in document.rows() {
            if !SHIP_STATE_ALLOWED_KEYS.contains(&row.key()) {
                continue;
            }
            if let Some((_key, value)) = rows.iter_mut().find(|(key, _value)| key == row.key()) {
                row.value().clone_into(value);
            } else {
                rows.push((row.key().to_owned(), row.value().to_owned()));
            }
        }
        Ok(Self { rows })
    }

    /// Build the canonical ordered first state after validating every field.
    ///
    /// # Errors
    /// Returns an error when an identity, manifest, or state value violates the wire contract.
    pub fn initial(input: &InitialShipState) -> Result<Self, ShipStateError> {
        validate_identity(input)?;
        validate_manifest(&input.manifest_path)?;
        let draft = input.draft && input.stall_step.is_empty();
        let boolean = |value: bool| if value { "true" } else { "false" }.to_owned();
        let values: [(&str, String); 48] = [
            ("PHASE", "checks".to_owned()),
            ("BRANCH_NAME", input.branch.clone()),
            ("ISSUE_NUMBER", input.issue.clone()),
            ("RUN_ID", input.run_id.clone()),
            ("REPO", input.repo.clone()),
            ("REPO_UNAVAILABLE", boolean(input.repo_unavailable)),
            ("FORKED_TARGET", boolean(input.forked)),
            ("MERGE", boolean(input.merge)),
            ("DRAFT", boolean(draft)),
            ("DEFERRED", boolean(input.deferred)),
            ("PR_CLOSED", "false".to_owned()),
            ("DONE_RENAME_APPLIED", "false".to_owned()),
            ("STALL_TRACKING", boolean(input.stall_tracking)),
            ("STALL_STEP", input.stall_step.clone()),
            ("BAIL_NEEDS_USER_INPUT", "false".to_owned()),
            ("BAIL_REASON", input.bail_reason.clone()),
            (
                "BAIL_FAILURE_DETAIL_LOG",
                input.bail_failure_detail_log.clone(),
            ),
            ("CI_PASSED", "false".to_owned()),
            ("PR_NUMBER", String::new()),
            ("PR_URL", String::new()),
            ("PR_TITLE", String::new()),
            ("RESUME_PHASE", String::new()),
            ("CALLER_KIND", String::new()),
            ("REBASE_COUNT", "0".to_owned()),
            ("FIX_ATTEMPTS", "0".to_owned()),
            ("ITERATION", "0".to_owned()),
            ("TRANSIENT_RETRIES", "0".to_owned()),
            ("FAILED_RUN_ID", String::new()),
            ("MANIFEST_PATH", input.manifest_path.clone()),
            ("TOOL_LABEL", input.tool_label.clone()),
            ("DESIGN_ONLY_DONE", "false".to_owned()),
            ("EXPECTED_SESSION_ID", input.expected_session_id.clone()),
            (
                "EXPECTED_TMPDIR_BASENAME_PREFIX",
                input.expected_tmpdir_basename_prefix.clone(),
            ),
            ("NO_ADMIN_FALLBACK", boolean(input.no_admin_fallback)),
            ("NO_LOGS_COMMIT", boolean(input.no_logs_commit)),
            ("IMPLEMENT_TMPDIR", input.tmpdir.clone()),
            ("CI_FIX_REBASE_PENDING", "false".to_owned()),
            ("OOS_PENDING", "false".to_owned()),
            ("EMERGENCY_REPAIR_BRANCH", String::new()),
            ("ORIGINAL_BRANCH_FORBIDDEN", "false".to_owned()),
            ("MAIN_REPAIR_RUN_ID", String::new()),
            ("MAIN_REPAIR_HEAD", String::new()),
            ("EMERGENCY_REPAIR_PR_NUMBER", String::new()),
            ("MAIN_HEALTH_REPAIR_COMMITTED", "false".to_owned()),
            ("MAIN_HEALTH_REPAIR_FAILED_RUN_ID", String::new()),
            ("MAIN_HEALTH_REPAIR_BASE_SHA", String::new()),
            ("MAIN_HEALTH_REPAIR_HEAD", String::new()),
            ("MAIN_HEALTH_HEAD_SHA", String::new()),
        ];
        debug_assert_eq!(values.len(), INITIAL_SHIP_STATE_KEYS.len());
        let mut state = Self::default();
        for (key, value) in values {
            state.set(key, value)?;
        }
        Ok(state)
    }

    /// Return one selected value.
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&str> {
        self.rows
            .iter()
            .find(|(candidate, _value)| candidate == key)
            .map(|(_key, value)| value.as_str())
    }

    /// Return whether this document has no retained ship-state rows.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    /// Set one allowlisted, line-safe value without moving its existing row.
    ///
    /// # Errors
    /// Returns an error when the key is not allowlisted or the value is unsafe.
    pub fn set(&mut self, key: &str, value: String) -> Result<(), ShipStateError> {
        if !SHIP_STATE_ALLOWED_KEYS.contains(&key) {
            return Err(ShipStateError::new(format!(
                "invalid ship state patch field: {key}"
            )));
        }
        validate_value(key, &value)?;
        if let Some((_key, existing)) = self
            .rows
            .iter_mut()
            .find(|(candidate, _value)| candidate == key)
        {
            *existing = value;
        } else {
            self.rows.push((key.to_owned(), value));
        }
        Ok(())
    }

    /// Remove one allowlisted field while retaining the order of every other row.
    ///
    /// # Errors
    /// Returns an error when the key is not part of the ship-state contract.
    pub fn remove(&mut self, key: &str) -> Result<(), ShipStateError> {
        if !SHIP_STATE_ALLOWED_KEYS.contains(&key) {
            return Err(ShipStateError::new(format!(
                "invalid ship state patch field: {key}"
            )));
        }
        self.rows.retain(|(candidate, _value)| candidate != key);
        Ok(())
    }

    /// Render exact ordered `KEY=value\n` bytes.
    ///
    /// # Errors
    /// Returns an error when a retained row violates the state or KV wire contract.
    pub fn render(&self) -> Result<String, ShipStateError> {
        for (key, value) in &self.rows {
            validate_value(key, value)?;
        }
        let rows = self
            .rows
            .iter()
            .map(|(key, value)| KvRow::new(key, value, KeyPolicy::Environment))
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| ShipStateError::new(error.to_string()))?;
        KvDocument::from_rows(rows)
            .render(RenderOptions::wire())
            .map_err(|error| ShipStateError::new(error.to_string()))
    }

    /// Publish this document under its owned implement tmpdir.
    ///
    /// # Errors
    /// Returns an error when the path is unsafe, a value is invalid, or publication fails.
    pub fn write(&self, path: &Path, tmpdir: &Path) -> Result<(), ShipStateError> {
        let _confined = confined_path(path, tmpdir, "ship state")?;
        ensure_state_parent(path, tmpdir)?;
        if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
            return Err(ShipStateError::new(format!(
                "refusing to write symlinked ship state path: {}",
                path.display()
            )));
        }
        private_atomic_write(path, &self.render()?, tmpdir)
            .map_err(|error| ShipStateError::new(error.to_string()))
    }
}

/// Return whether `path` carries at least one shell-shaped KV row.
#[must_use]
pub fn state_file_has_kv(path: &Path) -> bool {
    if !path.is_file() {
        return false;
    }
    let Ok(bytes) = fs::read(path) else {
        return true;
    };
    let Ok(text) = std::str::from_utf8(&bytes) else {
        return true;
    };
    KvDocument::parse(text, ParseOptions::legacy()).is_ok_and(|document| {
        document.rows().iter().any(|row| {
            let mut chars = row.key().chars();
            chars
                .next()
                .is_some_and(|character| character.is_ascii_alphabetic() || character == '_')
                && chars.all(|character| character.is_ascii_alphanumeric() || character == '_')
        })
    })
}

/// Confirm that an existing tmpdir resolves below one approved session root.
#[must_use]
pub fn tmpdir_under_allowed_root(tmpdir: &Path, roots: &[PathBuf]) -> bool {
    let safe_directory = fs::symlink_metadata(tmpdir)
        .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.is_dir());
    if tmpdir.as_os_str().is_empty()
        || tmpdir
            .components()
            .any(|component| matches!(component, Component::ParentDir))
        || !safe_directory
    {
        return false;
    }
    let Ok(resolved) = fs::canonicalize(tmpdir) else {
        return false;
    };
    roots.iter().any(|root| {
        fs::canonicalize(root)
            .is_ok_and(|allowed| resolved == allowed || resolved.starts_with(allowed))
    })
}

/// Confine and publish a create-if-absent initial state.
///
/// # Errors
/// Returns an error when the request is invalid or safe create-only publication fails.
pub fn write_initial_state(
    tmpdir: &Path,
    path: &Path,
    input: &InitialShipState,
) -> Result<(), ShipStateError> {
    let _confined = confined_path(path, tmpdir, "state file")?;
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(ShipStateError::new(format!(
            "refusing to write symlinked ship state path: {}",
            path.display()
        )));
    }
    if state_file_has_kv(path) {
        return Err(ShipStateError::new(
            "ship initial state is create-if-absent only; refusing to overwrite existing state",
        ));
    }
    ShipState::initial(input)?.write(path, tmpdir)
}

fn confined_path(path: &Path, tmpdir: &Path, label: &str) -> Result<PathBuf, ShipStateError> {
    ensure_under(path, tmpdir, label).map_err(|_error| {
        ShipStateError::new(format!(
            "--state-file must stay under --tmpdir: {}",
            path.display()
        ))
    })
}

fn ensure_state_parent(path: &Path, tmpdir: &Path) -> Result<(), ShipStateError> {
    let cwd = std::env::current_dir().map_err(|error| ShipStateError::new(error.to_string()))?;
    let root = if tmpdir.is_absolute() {
        tmpdir.to_path_buf()
    } else {
        cwd.join(tmpdir)
    };
    let root_metadata = fs::symlink_metadata(&root).map_err(|error| {
        ShipStateError::new(format!("cannot resolve ship-state tmpdir: {error}"))
    })?;
    if root_metadata.file_type().is_symlink() || !root_metadata.is_dir() {
        return Err(ShipStateError::new("ship-state tmpdir is unsafe"));
    }
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        cwd.join(path)
    };
    let parent = absolute
        .parent()
        .ok_or_else(|| ShipStateError::new("ship state has no parent"))?;
    let relative = parent
        .strip_prefix(&root)
        .map_err(|_error| ShipStateError::new("ship state parent escapes tmpdir"))?;
    let mut current = root;
    for component in relative.components() {
        let Component::Normal(name) = component else {
            return Err(ShipStateError::new("ship state parent is unsafe"));
        };
        current.push(name);
        match fs::symlink_metadata(&current) {
            Ok(metadata) if !metadata.file_type().is_symlink() && metadata.is_dir() => {}
            Ok(_) => {
                return Err(ShipStateError::new(format!(
                    "ship state parent is unsafe: {}",
                    current.display()
                )));
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                if let Err(create_error) = fs::create_dir(&current)
                    && create_error.kind() != std::io::ErrorKind::AlreadyExists
                {
                    return Err(ShipStateError::new(create_error.to_string()));
                }
                let metadata = fs::symlink_metadata(&current)
                    .map_err(|error| ShipStateError::new(error.to_string()))?;
                if metadata.file_type().is_symlink() || !metadata.is_dir() {
                    return Err(ShipStateError::new(format!(
                        "ship state parent is unsafe: {}",
                        current.display()
                    )));
                }
            }
            Err(error) => return Err(ShipStateError::new(error.to_string())),
        }
    }
    Ok(())
}

fn validate_identity(input: &InitialShipState) -> Result<(), ShipStateError> {
    if !valid_branch_name(input.branch.trim()) {
        return Err(ShipStateError::new(
            "--branch must be a non-empty valid branch name",
        ));
    }
    let issue = input.issue.trim();
    if issue.is_empty() || !issue.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(ShipStateError::new(
            "--issue must be a non-empty digit issue number",
        ));
    }
    if !valid_repo_slug(input.repo.trim()) {
        return Err(ShipStateError::new(
            "--repo must be a non-empty owner/repo slug",
        ));
    }
    if input.run_id.trim().is_empty() {
        return Err(ShipStateError::new("--run-id must be non-empty"));
    }
    Ok(())
}

#[allow(clippy::case_sensitive_file_extension_comparisons)] // preserves Python's exact `.env` check
fn validate_manifest(path: &str) -> Result<(), ShipStateError> {
    if path.is_empty() {
        return Ok(());
    }
    let path = Path::new(path);
    if path
        .file_name()
        .and_then(OsStr::to_str)
        .is_some_and(|name| name.ends_with(".env"))
    {
        return Err(ShipStateError::new(
            "MANIFEST_PATH must point at a readable JSON manifest, not a shell env file",
        ));
    }
    let value: Value = fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .ok_or_else(|| {
            ShipStateError::new("MANIFEST_PATH must point at a readable JSON manifest")
        })?;
    if !value.is_object() {
        return Err(ShipStateError::new(
            "MANIFEST_PATH JSON manifest must be an object",
        ));
    }
    Ok(())
}

fn validate_value(key: &str, value: &str) -> Result<(), ShipStateError> {
    if value.contains(['\n', '\r']) {
        return Err(ShipStateError::new(format!(
            "invalid newline in ship state value: {key}"
        )));
    }
    if key == "BRANCH_NAME" && !value.is_empty() && !valid_branch_name(value) {
        return Err(ShipStateError::new("invalid ship state BRANCH_NAME"));
    }
    if key == "PR_URL" && !valid_pr_url(value) {
        return Err(ShipStateError::new("invalid ship state PR_URL"));
    }
    if key == "MERGE_RESULT" && !value.is_empty() && !MERGE_RESULTS.contains(&value) {
        return Err(ShipStateError::new("invalid ship state MERGE_RESULT"));
    }
    if key == "CONFLICT_FILES" {
        validate_conflict_csv(value)?;
    }
    Ok(())
}

fn validate_conflict_csv(value: &str) -> Result<(), ShipStateError> {
    if value.is_empty() {
        return Err(ShipStateError::new("invalid empty CONFLICT_FILES"));
    }
    for item in value.split(',') {
        let path = Path::new(item);
        if item.is_empty()
            || item.trim() != item
            || path.is_absolute()
            || item.contains('\\')
            || path.components().any(|component| {
                matches!(
                    component,
                    Component::ParentDir | Component::CurDir | Component::RootDir
                )
            })
            || !item.bytes().all(|byte| {
                byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'/' | b'-')
            })
        {
            return Err(ShipStateError::new("invalid CONFLICT_FILES entry"));
        }
    }
    Ok(())
}

fn valid_branch_name(value: &str) -> bool {
    !value.is_empty()
        && !value.starts_with('-')
        && !value.ends_with('/')
        && !value.contains("..")
        && !value.contains("//")
        && !value.contains("@{")
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'/' | b'-'))
}

fn valid_repo_slug(value: &str) -> bool {
    if value.is_empty() || value.starts_with('-') {
        return false;
    }
    let mut parts = value.split('/');
    let valid = |part: &str| {
        !part.is_empty()
            && part
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    };
    matches!((parts.next(), parts.next(), parts.next()), (Some(owner), Some(repo), None) if valid(owner) && valid(repo))
}

fn valid_pr_url(value: &str) -> bool {
    value.is_empty()
        || (value
            .strip_prefix("http://")
            .or_else(|| value.strip_prefix("https://"))
            .is_some_and(|suffix| !suffix.is_empty())
            && value.bytes().all(|byte| {
                byte.is_ascii_alphanumeric() || b"._~:/?#[]@!$&'()*+,;=%-".contains(&byte)
            }))
}

#[cfg(test)]
mod tests {
    use super::{
        INITIAL_SHIP_STATE_KEYS, InitialShipState, KvDocument, KvRow, ParseOptions, ShipState,
        state_file_has_kv, write_initial_state,
    };
    use std::fs;
    use tempfile::TempDir;

    fn input(root: &TempDir) -> InitialShipState {
        InitialShipState {
            tmpdir: root.path().display().to_string(),
            branch: "feature/ship".to_owned(),
            issue: "8621".to_owned(),
            repo: "owner/repo".to_owned(),
            run_id: "run-1".to_owned(),
            merge: true,
            tool_label: "Codex".to_owned(),
            ..InitialShipState::default()
        }
    }

    #[test]
    fn initial_state_has_canonical_order_and_stall_draft_override() {
        let root = TempDir::new().expect("tmpdir");
        let mut request = input(&root);
        request.draft = true;
        request.stall_step = "5".to_owned();
        let state = ShipState::initial(&request).expect("state");
        let text = state.render().expect("render");
        let parsed = KvDocument::parse(&text, ParseOptions::legacy()).expect("state KV");
        let keys: Vec<_> = parsed.rows().iter().map(KvRow::key).collect();
        assert_eq!(keys, INITIAL_SHIP_STATE_KEYS);
        assert_eq!(state.get("DRAFT"), Some("false"));
        assert_eq!(state.get("OOS_PENDING"), Some("false"));
    }

    #[test]
    fn read_filters_unknown_rows_and_keeps_last_value_in_first_position() {
        let root = TempDir::new().expect("tmpdir");
        let path = root.path().join("ship.env");
        let data = "REPO=owner/first=mirror\nUNKNOWN=no\nPHASE=checks\nREPO=owner/final\n";
        fs::write(&path, data).expect("fixture");
        let state = ShipState::read(&path).expect("read");
        assert_eq!(
            state.render().expect("render"),
            "REPO=owner/final\nPHASE=checks\n"
        );
    }

    #[test]
    fn patch_mutations_validate_keys_and_preserve_remaining_order() {
        let mut state = ShipState {
            rows: vec![
                ("PHASE".to_owned(), "checks".to_owned()),
                ("REBASE_COUNT".to_owned(), "0".to_owned()),
            ],
        };
        state
            .set("REBASE_COUNT", "1".to_owned())
            .expect("set retained key");
        state.remove("PHASE").expect("remove retained key");
        assert_eq!(state.render().expect("render"), "REBASE_COUNT=1\n");
        assert!(state.remove("UNKNOWN").is_err());
    }

    #[test]
    fn initial_write_is_create_if_absent_and_refuses_symlink_leaf() {
        let root = TempDir::new().expect("tmpdir");
        let path = root.path().join("ship-pr-state.sh");
        write_initial_state(root.path(), &path, &input(&root)).expect("first write");
        assert!(state_file_has_kv(&path));
        assert!(write_initial_state(root.path(), &path, &input(&root)).is_err());

        let link = root.path().join("linked-state.sh");
        #[cfg(unix)]
        std::os::unix::fs::symlink(root.path().join("target"), &link).expect("symlink");
        #[cfg(unix)]
        assert!(write_initial_state(root.path(), &link, &input(&root)).is_err());
        #[cfg(unix)]
        assert!(
            ShipState::initial(&input(&root))
                .expect("state")
                .write(&link, root.path())
                .is_err()
        );
    }

    #[test]
    fn write_creates_only_real_contained_parent_directories() {
        let root = TempDir::new().expect("tmpdir");
        let path = root.path().join("nested/state/ship-pr-state.sh");
        write_initial_state(root.path(), &path, &input(&root)).expect("nested state");
        assert!(path.is_file());

        #[cfg(unix)]
        {
            let outside = TempDir::new().expect("outside");
            let linked = root.path().join("linked");
            std::os::unix::fs::symlink(outside.path(), &linked).expect("parent symlink");
            let escaped = linked.join("ship-pr-state.sh");
            assert!(write_initial_state(root.path(), &escaped, &input(&root)).is_err());
        }
    }

    #[test]
    fn validation_rejects_forged_values_and_non_object_manifest() {
        let root = TempDir::new().expect("tmpdir");
        let mut request = input(&root);
        request.branch = "bad\nbranch".to_owned();
        assert!(ShipState::initial(&request).is_err());
        let manifest = root.path().join("manifest.json");
        fs::write(&manifest, "[]\n").expect("manifest");
        request.branch = "feature/ship".to_owned();
        request.manifest_path = manifest.display().to_string();
        assert!(ShipState::initial(&request).is_err());
        let mut state = ShipState::default();
        assert!(
            state
                .set("CONFLICT_FILES", "src/main.rs,../escape".to_owned())
                .is_err()
        );

        let path = root.path().join("unsafe-state.sh");
        fs::write(&path, "PR_URL=javascript:alert(1)\n").expect("unsafe state");
        assert!(ShipState::read(&path).expect("read").render().is_err());
    }
}
