//! Filesystem, Git, and bgjob effects for Rust-owned stall-recovery commands.
use crate::{
    GixRepository, PathIntent, SystemProcessIdentityHost, TemporaryRoot, atomic_write_bytes_in,
    atomic_write_utf8_in, ensure_directory_chain,
};
use larch_core::{
    CommentPolicy, CrStrip, DuplicatePolicy, KvDocument, ParseOptions, RepositoryRead,
    artifact_prefix_valid, daemon_liveness, kv_text, public_text_is_sensitive, read_for,
    safe_phase, safe_step, select_kv_bytes, terminal_state_valid, unlink_entry,
    validate_process_identity,
};
use regex::Regex;
use sha2::{Digest as _, Sha256};
#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;
use std::{
    env,
    fs::{self, File, OpenOptions},
    io::{ErrorKind, Read as _},
    path::{Path, PathBuf},
    sync::LazyLock,
};
const STATE_LAYERS: &[&str] = &["ship-pr-state.sh", "finalize-state.sh", "session-env.sh"];
const CHECKS_BGJOB_STEPS: &[(&str, &str)] = &[
    ("implement-step3-checks", "3"),
    ("implement-checks-step5-self-review", "5"),
    ("implement-step5-self-review", "5"),
];
const CLEAR_UPDATES: &[(&str, &str)] = &[
    ("STALL_TRACKING", "false"),
    ("STALL_STEP", ""),
    ("BAIL_REASON", ""),
    ("IMPLEMENT_BAIL_REASON", ""),
    ("EXIT_CODE", "unknown"),
];
/// Fixed evidence artifacts that contribute sensitive tokens to a stall report.
pub const STALL_RECOVERY_EVIDENCE_NAMES: &[&str] = &[
    "ship-pr-state.sh",
    "finalize-state.sh",
    "session-env.sh",
    "source-env.sh",
    "execution-issues.md",
    "run-log-pointer.txt",
    "plan.txt",
    "feature-description.txt",
    "issue-body.txt",
    "composed-plan.md",
    "final-summary.md",
    "validate-plan-commands.log",
    "design-log-publish.failure.log",
    "design-plan-write.failure.log",
    "design-publish-tail.failure.log",
    "design-publish-tail.stdout.log",
    "design-publish-tail.stderr.log",
    "design-publish-rename.stderr.log",
    "design-publish-log.stderr.log",
];
const MAX_PUBLIC_FILE_BYTES: u64 = 256_000;
/// Maximum byte length accepted for an optional failure-detail artifact.
pub const MAX_DETAIL_FILE_BYTES: u64 = 65_536;
const MAX_DETAIL_FILE_BYTES_USIZE: usize = 65_536;
static URL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"https?://[^\s`)\]]+").expect("fixed regex"));
static GIT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+").expect("fixed regex")
});
static GITHUB_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+").expect("fixed regex")
});
static HOST_PATH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:^|[\s`(])/(?:Users|home|private|tmp|var|Volumes)/[^\s`)]+")
        .expect("fixed regex")
});
/// Stable command exit classes for state mutation failures.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StateMutationError {
    /// Existing state is malformed or unsafe and must not be replaced.
    Unsafe,
    /// A validated state mutation or readback failed.
    Failed,
}
/// Clear all stall fields and abandoned checks registry rows.
/// # Errors
/// Returns `Unsafe` for unsafe state and `Failed` when a validated mutation fails.
pub fn clear_stall(tmpdir: &Path) -> Result<(), StateMutationError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StateMutationError::Unsafe)?;
    if !tmpdir.exists() {
        clear_abandoned_checks_registry(&tmpdir);
        return Ok(());
    }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StateMutationError::Unsafe)?;
    let tmpdir = root.path().to_path_buf();
    for name in [
        "stall-recovery-classification.env",
        "stall-recovery-issue.env",
    ] {
        let _ = fs::remove_file(tmpdir.join(name));
    }
    let mut present = Vec::new();
    for name in STATE_LAYERS {
        let path = tmpdir.join(name);
        match inspect_state(&path) {
            Ok(Some(text)) if state_syntax_ok(&text) => present.push((path, text)),
            Ok(Some(_)) | Err(StateMutationError::Unsafe) => {
                return Err(StateMutationError::Unsafe);
            }
            Ok(None) => {}
            Err(StateMutationError::Failed) => return Err(StateMutationError::Failed),
        }
    }
    for (path, text) in present {
        rewrite_state(&root, &path, &text, CLEAR_UPDATES)?;
        let rewritten = read_lossy(&path).map_err(|()| StateMutationError::Failed)?;
        if read_last_value(&rewritten, "STALL_TRACKING") != "false"
            || !read_last_value(&rewritten, "STALL_STEP").is_empty()
        {
            return Err(StateMutationError::Failed);
        }
    }
    clear_abandoned_checks_registry(&tmpdir);
    Ok(())
}
/// Seed terminal state, returning the legacy `rewrite` or `seed` mode.
/// # Errors
/// Returns `Unsafe` for unsafe state and `Failed` when a validated mutation fails.
pub fn seed_terminal_state(
    tmpdir: &Path,
    stall_step: &str,
    phase: &str,
) -> Result<&'static str, StateMutationError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StateMutationError::Unsafe)?;
    let raw_state = tmpdir.join("ship-pr-state.sh");
    let existing = match inspect_state(&raw_state) {
        Ok(Some(text)) if state_syntax_ok(&text) => Some(text),
        Ok(Some(_)) | Err(StateMutationError::Unsafe) => return Err(StateMutationError::Unsafe),
        Ok(None) => None,
        Err(StateMutationError::Failed) => return Err(StateMutationError::Failed),
    };
    let prior = existing.as_deref().unwrap_or("");
    let step = safe_state_value(stall_step, prior, "STALL_STEP", "8", safe_step);
    let phase = safe_state_value(phase, prior, "PHASE", "ci-initial", safe_phase);
    ensure_directory_chain(&tmpdir).map_err(|_| StateMutationError::Failed)?;
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StateMutationError::Unsafe)?;
    let state = root.path().join("ship-pr-state.sh");
    let rewrite = existing
        .as_ref()
        .is_some_and(|text| !text.is_empty() && text.lines().any(|line| line.contains('=')));
    if rewrite {
        rewrite_state(
            &root,
            &state,
            existing.as_deref().unwrap_or(""),
            &[
                ("STALL_TRACKING", "true"),
                ("STALL_STEP", &step),
                ("PHASE", &phase),
            ],
        )?;
    } else {
        let text = format!(
            "PHASE={phase}\nSTALL_TRACKING=true\nSTALL_STEP={step}\nBAIL_REASON=\nBAIL_FAILURE_DETAIL_LOG=\nEXIT_CODE=4\n"
        );
        atomic_write_utf8_in(&root, &state, &text, false, 0o600)
            .map_err(|_| StateMutationError::Failed)?;
    }
    let written = read_lossy(&state).map_err(|()| StateMutationError::Failed)?;
    if read_last_value(&written, "STALL_TRACKING") != "true" {
        return Err(StateMutationError::Failed);
    }
    Ok(if rewrite { "rewrite" } else { "seed" })
}
/// Validate one terminal-state file below its owning temporary directory.
#[must_use]
pub fn terminal_state_is_valid(tmpdir: &Path, state: &Path, generic: bool) -> bool {
    if !state.is_absolute() || !tmpdir.is_dir() {
        return false;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(tmpdir)) else {
        return false;
    };
    let Some(state) = canonical_root_spelling(&root, tmpdir, state) else {
        return false;
    };
    let Ok(confined) = root.confine(&state, PathIntent::Read) else {
        return false;
    };
    let Ok(text) = read_lossy(confined.path()) else {
        return false;
    };
    let normalized = text
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .collect::<Vec<_>>()
        .join("\n");
    let Ok(document) = KvDocument::parse(&normalized, ParseOptions::environment()) else {
        return false;
    };
    let rows = document
        .rows()
        .iter()
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect::<Vec<_>>();
    terminal_state_valid(&rows, generic, |value| {
        canonical_root_spelling(&root, tmpdir, Path::new(value))
            .is_some_and(|path| safe_regular_file(&root, &path, None))
    })
}
/// Rebuild the effective sensitive corpus and validate a Tier B public file.
#[must_use]
pub fn tier_b_public_file_is_valid(
    tmpdir: &Path,
    public_file: &Path,
    sensitive_corpus: &Path,
    artifact_prefix: &str,
) -> bool {
    if !tmpdir.is_absolute()
        || !public_file.is_absolute()
        || !sensitive_corpus.is_absolute()
        || !artifact_prefix_valid(artifact_prefix)
        || !regular_nonsymlink(public_file, Some(MAX_PUBLIC_FILE_BYTES))
    {
        return false;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(tmpdir)) else {
        return false;
    };
    let Some(sensitive_corpus) = canonical_root_spelling(&root, tmpdir, sensitive_corpus) else {
        return false;
    };
    if !safe_regular_file(&root, &sensitive_corpus, None) {
        return false;
    }
    let effective = root.path().join(format!(
        "{}-sensitive-corpus.public.effective",
        if artifact_prefix.is_empty() {
            "stall-recovery"
        } else {
            artifact_prefix
        }
    ));
    let corpus = build_sensitive_corpus(&root, &sensitive_corpus, artifact_prefix);
    if atomic_write_utf8_in(&root, &effective, &corpus, false, 0o600).is_err() {
        return false;
    }
    let sensitive = read_lossy(public_file)
        .ok()
        .is_none_or(|candidate| public_text_is_sensitive(&corpus, &candidate));
    if sensitive {
        return false;
    }
    let _ = fs::remove_file(effective);
    true
}

/// Detect whether the active repository is a non-forked larch development clone.
#[must_use]
pub fn is_larch_dev_clone(tmpdir: &Path, working_tree_root: Option<&Path>) -> bool {
    let forked = ["ship-pr-state.sh", "session-env.sh"]
        .iter()
        .find_map(|name| {
            let path = tmpdir.join(name);
            regular_nonsymlink(&path, None)
                .then(|| read_lossy(&path).ok())
                .flatten()
                .and_then(|text| {
                    let value = read_last_value(&text, "FORKED_TARGET");
                    (!value.is_empty()).then_some(value)
                })
        })
        .unwrap_or_default();
    if matches!(
        forked.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    ) {
        return false;
    }
    let root = working_tree_root.map(Path::to_path_buf).or_else(|| {
        GixRepository::discover(env::current_dir().ok()?)
            .ok()?
            .location()
            .work_dir
            .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))
    });
    root.is_some_and(|root| regular_nonsymlink(&root.join("skills/implement/SKILL.md"), None))
}

/// Stable validation failures for an optional failure-detail log.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FailureDetailLogError {
    /// The caller supplied a relative path.
    NonAbsolute,
    /// The path or a confined component is a symlink.
    Symlink,
    /// The path is not below the validated temporary root.
    OutsideTmpdir,
    /// The file disappeared before it could be opened.
    Missing,
    /// The path is not a regular file.
    NotRegularFile,
    /// The file exceeds the 64 KiB optional-evidence limit.
    Oversize,
    /// The operating system refused a safe read.
    Unreadable,
}

impl FailureDetailLogError {
    /// Return the legacy stable suffix used in ledger diagnostics.
    #[must_use]
    pub const fn suffix(self) -> &'static str {
        match self {
            Self::NonAbsolute => "non-absolute",
            Self::Symlink => "symlink",
            Self::OutsideTmpdir => "outside-tmpdir",
            Self::Missing => "missing",
            Self::NotRegularFile => "not-regular-file",
            Self::Oversize => "oversize",
            Self::Unreadable => "unreadable",
        }
    }

    /// Render the legacy user-facing validation diagnostic for `flag`.
    #[must_use]
    pub fn message(self, flag: &str) -> String {
        match self {
            Self::NonAbsolute => format!("stall-recovery: {flag} must be absolute"),
            Self::Symlink => format!("stall-recovery: {flag} must not be a symlink"),
            Self::OutsideTmpdir | Self::Missing | Self::NotRegularFile => {
                format!("stall-recovery: {flag} outside implement tmpdir")
            }
            Self::Oversize => format!("stall-recovery: {flag} exceeds 64KiB"),
            Self::Unreadable => format!("stall-recovery: {flag} unreadable"),
        }
    }
}

/// Classify a failure-detail path without reading its content.
///
/// The path must be absolute, regular, non-symlinked, below `root`, and at
/// most [`MAX_DETAIL_FILE_BYTES`] long.
///
/// # Errors
///
/// Returns the stable validation reason when the file is unsafe, too large, or
/// unreadable.
pub fn classify_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
) -> Result<(), FailureDetailLogError> {
    open_failure_detail_log(root, path, Some(MAX_DETAIL_FILE_BYTES)).map(|_| ())
}

/// Read a validated failure-detail log as lossy UTF-8.
///
/// # Errors
///
/// Returns the stable validation reason when the file is unsafe, too large, or
/// unreadable.
pub fn read_validated_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
) -> Result<String, FailureDetailLogError> {
    let (mut file, _size) = open_failure_detail_log(root, path, Some(MAX_DETAIL_FILE_BYTES))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|_| FailureDetailLogError::Unreadable)?;
    if bytes.len() > MAX_DETAIL_FILE_BYTES_USIZE {
        return Err(FailureDetailLogError::Oversize);
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

/// Read optional failure evidence, returning an empty string for unsafe input.
#[must_use]
pub fn read_optional_failure_detail_evidence(root: &TemporaryRoot, path: &Path) -> String {
    read_validated_failure_detail_log(root, path).unwrap_or_default()
}

/// Materialize a bounded, private sidecar from an oversized detail log.
///
/// The returned path is absolute and confined below `root`. The sidecar name
/// uses the legacy SHA-256 seed so ledger references remain stable.
#[must_use]
pub fn materialize_truncated_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
) -> Option<PathBuf> {
    let (mut source, size) = open_failure_detail_log(root, path, None).ok()?;
    let mut prefix = Vec::with_capacity(MAX_DETAIL_FILE_BYTES_USIZE);
    source
        .by_ref()
        .take(MAX_DETAIL_FILE_BYTES)
        .read_to_end(&mut prefix)
        .ok()?;
    let canonical = fs::canonicalize(path).ok()?;
    if !canonical.starts_with(root.path()) {
        return None;
    }
    let mut digest = Sha256::new();
    digest.update(canonical.to_string_lossy().as_bytes());
    digest.update([0]);
    digest.update(size.to_string().as_bytes());
    digest.update([0]);
    digest.update(&prefix);
    let fingerprint = format!("{:x}", digest.finalize());
    let name = format!(
        "stall-recovery-failure-detail-log-{}.truncated.log",
        &fingerprint[..16]
    );
    let sidecar = root.path().join(&name);
    atomic_write_bytes_in(root, &sidecar, &prefix, false, 0o600).ok()?;
    classify_failure_detail_log(root, &sidecar)
        .is_ok()
        .then_some(sidecar)
}

/// Find the newest valid failure-detail sidecar named by escalation evidence.
#[must_use]
pub fn latest_failure_detail_log_sidecar(
    root: &TemporaryRoot,
    ledger: &Path,
    fallback: &Path,
) -> Option<PathBuf> {
    detail_log_ledger_fields(root, ledger, fallback)
        .into_iter()
        .filter_map(|(utc, sequence, value)| {
            if value.contains('\0') || Path::new(&value).is_absolute() {
                None
            } else {
                let path = root.path().join(value);
                classify_failure_detail_log(root, &path)
                    .is_ok()
                    .then_some((utc, sequence, path))
            }
        })
        .max_by(|left, right| left.0.cmp(&right.0).then(left.1.cmp(&right.1)))
        .map(|(_, _, path)| path)
}

/// Read the primary detail log, or the newest valid ledger sidecar when allowed.
///
/// The returned path is the validated source used for the content. Invalid
/// primary input is intentionally ignored before considering a sidecar, which
/// preserves the former reporting fallback contract.
#[must_use]
pub fn read_failure_detail_log_with_sidecar_fallback(
    root: &TemporaryRoot,
    primary: &str,
    ledger: &Path,
    fallback: &Path,
    allow_without_primary: bool,
) -> Option<(String, PathBuf)> {
    if !primary.is_empty() {
        let path = PathBuf::from(primary);
        if let Ok(detail) = read_validated_failure_detail_log(root, &path) {
            return Some((detail, path));
        }
    } else if !allow_without_primary {
        return None;
    }
    let sidecar = latest_failure_detail_log_sidecar(root, ledger, fallback)?;
    read_validated_failure_detail_log(root, &sidecar)
        .ok()
        .map(|detail| (detail, sidecar))
}

fn detail_log_ledger_fields(
    root: &TemporaryRoot,
    ledger: &Path,
    fallback: &Path,
) -> Vec<(String, usize, String)> {
    let mut found = Vec::new();
    let mut sequence = 0;
    for path in [ledger, fallback] {
        if !safe_regular_file(root, path, None) {
            continue;
        }
        let Ok(text) = read_lossy(path) else {
            continue;
        };
        for row in text.lines() {
            sequence += 1;
            let mut utc = "";
            let mut detail = "";
            for field in row.split('\t') {
                let Some((key, value)) = field.split_once('=') else {
                    continue;
                };
                if key == "utc" {
                    utc = value;
                } else if key == "failure_detail_log" {
                    detail = value;
                }
            }
            if !detail.is_empty() {
                found.push((utc.to_owned(), sequence, detail.to_owned()));
            }
        }
    }
    found
}

fn open_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
    max_size: Option<u64>,
) -> Result<(File, u64), FailureDetailLogError> {
    if !path.is_absolute() {
        return Err(FailureDetailLogError::NonAbsolute);
    }
    if !path.starts_with(root.path()) {
        return Err(FailureDetailLogError::OutsideTmpdir);
    }
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(FailureDetailLogError::Symlink);
        }
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => {
            return Err(FailureDetailLogError::Missing);
        }
        Err(_) => return Err(FailureDetailLogError::Unreadable),
    };
    if !metadata.is_file() {
        return Err(FailureDetailLogError::NotRegularFile);
    }
    if max_size.is_some_and(|limit| metadata.len() > limit) {
        return Err(FailureDetailLogError::Oversize);
    }
    root.confine(path, PathIntent::Read)
        .map_err(|_| FailureDetailLogError::OutsideTmpdir)?;
    let file = open_failure_detail_file(path)?;
    let opened = file
        .metadata()
        .map_err(|_| FailureDetailLogError::Unreadable)?;
    if !opened.is_file() {
        return Err(FailureDetailLogError::NotRegularFile);
    }
    if max_size.is_some_and(|limit| opened.len() > limit) {
        return Err(FailureDetailLogError::Oversize);
    }
    Ok((file, opened.len()))
}

fn open_failure_detail_file(path: &Path) -> Result<File, FailureDetailLogError> {
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    options.custom_flags(nix::libc::O_NOFOLLOW);
    options.open(path).map_err(|error| {
        #[cfg(unix)]
        if error.raw_os_error() == Some(nix::libc::ELOOP) {
            return FailureDetailLogError::Symlink;
        }
        let _ = error;
        FailureDetailLogError::Unreadable
    })
}

fn inspect_state(path: &Path) -> Result<Option<String>, StateMutationError> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(StateMutationError::Failed),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(StateMutationError::Unsafe);
    }
    if OpenOptions::new()
        .read(true)
        .write(true)
        .open(path)
        .is_err()
    {
        return Err(StateMutationError::Unsafe);
    }
    read_lossy(path)
        .map(Some)
        .map_err(|()| StateMutationError::Failed)
}

fn state_syntax_ok(text: &str) -> bool {
    text.lines()
        .all(|line| line.is_empty() || line.starts_with('#') || line.contains('='))
        && render_state(text, &[]).is_ok()
}

fn rewrite_state(
    root: &TemporaryRoot,
    path: &Path,
    text: &str,
    updates: &[(&str, &str)],
) -> Result<(), StateMutationError> {
    let rendered = render_state(text, updates)?;
    atomic_write_utf8_in(root, path, &rendered, false, 0o600)
        .map_err(|_| StateMutationError::Failed)
}

fn render_state(text: &str, updates: &[(&str, &str)]) -> Result<String, StateMutationError> {
    let mut options = ParseOptions::legacy();
    options.comments = CommentPolicy::Skip;
    options.cr_strip = CrStrip::Suffix;
    let document = KvDocument::parse(text, options).map_err(|_| StateMutationError::Failed)?;
    let mut rows: Vec<(String, String)> = Vec::new();
    for row in document.rows() {
        if let Some((_, current)) = rows.iter_mut().find(|(current, _)| current == row.key()) {
            row.value().clone_into(current);
        } else {
            rows.push((row.key().to_owned(), row.value().to_owned()));
        }
    }
    for (key, value) in updates {
        if let Some((_, current)) = rows.iter_mut().find(|(current, _)| current == key) {
            (*value).clone_into(current);
        } else {
            rows.push(((*key).to_owned(), (*value).to_owned()));
        }
    }
    let refs = rows
        .iter()
        .map(|(key, value)| (key.as_str(), value.as_str()))
        .collect::<Vec<_>>();
    kv_text(&refs).map_err(|_| StateMutationError::Failed)
}

fn read_last_value(text: &str, key: &str) -> String {
    String::from_utf8_lossy(&select_kv_bytes(
        text.as_bytes(),
        key.as_bytes(),
        b"",
        DuplicatePolicy::Last,
        CrStrip::Both,
    ))
    .into_owned()
}

fn safe_state_value(
    argument: &str,
    prior: &str,
    key: &str,
    fallback: &str,
    validator: fn(&str, bool) -> bool,
) -> String {
    let prior = read_last_value(prior, key);
    let value = if !argument.is_empty() {
        argument.to_owned()
    } else if prior.is_empty() {
        fallback.to_owned()
    } else {
        prior
    };
    if validator(&value, true) || value == "unknown" {
        value
    } else {
        "unknown".to_owned()
    }
}

fn clear_abandoned_checks_registry(tmpdir: &Path) {
    let host = SystemProcessIdentityHost::new();
    for (path, _) in abandoned_checks_registry_rows(tmpdir, &host) {
        unlink_entry(&path);
    }
}

/// Return the first abandoned checks step using the shared Rust bgjob registry.
#[must_use]
pub fn abandoned_checks_stall_step(tmpdir: &Path) -> Option<&'static str> {
    let host = SystemProcessIdentityHost::new();
    abandoned_checks_registry_rows(tmpdir, &host)
        .into_iter()
        .next()
        .map(|(_, step)| step)
}

fn abandoned_checks_registry_rows(
    tmpdir: &Path,
    host: &SystemProcessIdentityHost,
) -> Vec<(PathBuf, &'static str)> {
    let mut abandoned = Vec::new();
    for &(step, stall_step) in CHECKS_BGJOB_STEPS {
        let Ok((path, Some(entry))) = read_for(tmpdir, step, None) else {
            continue;
        };
        if regular_nonsymlink(&entry.result_env, None) {
            continue;
        }
        let owner_dead = entry
            .owner
            .as_ref()
            .is_some_and(|owner| !validate_process_identity(host, owner).ok);
        if !daemon_liveness(host, &entry).live || owner_dead {
            abandoned.push((path, stall_step));
        }
    }
    abandoned
}

fn build_sensitive_corpus(root: &TemporaryRoot, sensitive: &Path, prefix: &str) -> String {
    let mut sources = vec![
        sensitive.to_path_buf(),
        artifact_path(root.path(), "stall-recovery-classification.env", prefix),
        artifact_path(root.path(), "stall-recovery-attempts.env", prefix),
        artifact_path(root.path(), "stall-recovery-escalation-ledger.tsv", prefix),
        artifact_path(
            root.path(),
            "stall-recovery-escalation-fallback.tsv",
            prefix,
        ),
        artifact_path(
            root.path(),
            "stall-recovery-escalation-record-failure.env",
            prefix,
        ),
    ];
    sources.extend(
        STALL_RECOVERY_EVIDENCE_NAMES
            .iter()
            .map(|name| root.path().join(name)),
    );
    let class_file = artifact_path(root.path(), "stall-recovery-classification.env", prefix);
    if let Ok(text) = read_lossy(&class_file) {
        let detail = read_last_value(&text, "FAILURE_DETAIL_LOG");
        let detail_path = Path::new(&detail);
        if !detail.is_empty()
            && let Some(detail_path) = canonical_root_spelling(root, root.path(), detail_path)
            && safe_regular_file(root, &detail_path, Some(MAX_DETAIL_FILE_BYTES))
        {
            sources.push(detail_path);
        }
    }
    build_sensitive_corpus_from_evidence(root, sources)
}

/// Build the effective sensitive-token corpus from confined report evidence.
///
/// Every input path is revalidated below `root`; missing, symlinked, and
/// non-regular files contribute no data. Callers can therefore pass optional
/// report artifacts without widening the trusted filesystem boundary.
#[must_use]
pub fn build_sensitive_corpus_from_evidence(
    root: &TemporaryRoot,
    sources: impl IntoIterator<Item = PathBuf>,
) -> String {
    let mut lines = Vec::new();
    for source in sources {
        if !safe_regular_file(root, &source, None) {
            continue;
        }
        let Ok(text) = read_lossy(&source) else {
            continue;
        };
        lines.extend(text.lines().map(str::to_owned));
        for regex in [&*URL_RE, &*GIT_RE, &*GITHUB_RE, &*HOST_PATH_RE] {
            lines.extend(
                regex
                    .find_iter(&text)
                    .map(|found| found.as_str().trim().to_owned()),
            );
        }
    }
    lines
        .into_iter()
        .map(|line| line.trim().to_owned())
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>()
        .join("\n")
        + "\n"
}

fn artifact_path(tmpdir: &Path, default_name: &str, prefix: &str) -> PathBuf {
    if prefix.is_empty() || prefix == "stall-recovery" {
        tmpdir.join(default_name)
    } else {
        tmpdir.join(format!(
            "{prefix}{}",
            default_name
                .strip_prefix("stall-recovery")
                .unwrap_or(default_name)
        ))
    }
}

fn safe_regular_file(root: &TemporaryRoot, path: &Path, max_size: Option<u64>) -> bool {
    path.is_absolute()
        && root.confine(path, PathIntent::Read).is_ok()
        && regular_nonsymlink(path, max_size)
}

fn canonical_root_spelling(
    root: &TemporaryRoot,
    input_root: &Path,
    path: &Path,
) -> Option<PathBuf> {
    if !path.is_absolute()
        || fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink())
    {
        return None;
    }
    if let Ok(relative) = path.strip_prefix(input_root) {
        return Some(root.path().join(relative));
    }
    let canonical = fs::canonicalize(path).ok()?;
    canonical.starts_with(root.path()).then_some(canonical)
}

fn regular_nonsymlink(path: &Path, max_size: Option<u64>) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| {
        metadata.is_file()
            && !metadata.file_type().is_symlink()
            && max_size.is_none_or(|limit| metadata.len() <= limit)
    })
}

fn absolute_path(path: &Path) -> Result<PathBuf, ()> {
    if path.is_absolute() {
        Ok(path.to_path_buf())
    } else {
        env::current_dir().map(|cwd| cwd.join(path)).map_err(|_| ())
    }
}

fn read_lossy(path: &Path) -> Result<String, ()> {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|_| ())
}

#[cfg(test)]
mod tests {
    use super::{
        FailureDetailLogError, MAX_DETAIL_FILE_BYTES, MAX_DETAIL_FILE_BYTES_USIZE,
        StateMutationError, classify_failure_detail_log, clear_stall,
        latest_failure_detail_log_sidecar, materialize_truncated_failure_detail_log,
        read_failure_detail_log_with_sidecar_fallback, read_validated_failure_detail_log,
        seed_terminal_state, terminal_state_is_valid,
    };
    use crate::TemporaryRoot;
    use std::fs;

    #[test]
    fn seed_and_clear_preserve_unrelated_state() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state = temp.path().join("ship-pr-state.sh");
        fs::write(&state, "KEEP=yes\nSTALL_STEP=9\nPHASE=merge\n").expect("seed fixture");
        assert_eq!(
            seed_terminal_state(temp.path(), "8a", "ci-initial"),
            Ok("rewrite")
        );
        let seeded = fs::read_to_string(&state).expect("seeded state");
        assert!(seeded.contains("KEEP=yes\n"));
        assert!(seeded.contains("STALL_TRACKING=true\n"));
        clear_stall(temp.path()).expect("clear state");
        let cleared = fs::read_to_string(&state).expect("cleared state");
        assert!(cleared.contains("KEEP=yes\n"));
        assert!(cleared.contains("STALL_TRACKING=false\n"));
    }

    #[test]
    fn malformed_state_fails_before_mutation() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state = temp.path().join("ship-pr-state.sh");
        fs::write(&state, "STALL_TRACKING=true\npartial\n").expect("fixture");
        assert_eq!(clear_stall(temp.path()), Err(StateMutationError::Unsafe));
        assert_eq!(
            fs::read_to_string(state).expect("unchanged"),
            "STALL_TRACKING=true\npartial\n"
        );
    }

    #[test]
    fn terminal_validation_rejects_partial_files() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state = temp.path().join("terminal.env");
        fs::write(
            &state,
            "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\n",
        )
        .expect("fixture");
        assert!(!terminal_state_is_valid(temp.path(), &state, true));
    }

    #[test]
    fn failure_detail_log_reads_only_small_confined_regular_files() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let detail = root.path().join("detail.log");
        fs::write(&detail, "bounded detail\n").expect("detail fixture");

        assert_eq!(classify_failure_detail_log(&root, &detail), Ok(()));
        assert_eq!(
            read_validated_failure_detail_log(&root, &detail),
            Ok("bounded detail\n".to_owned())
        );
        assert_eq!(
            classify_failure_detail_log(&root, &root.path().join("missing.log")),
            Err(FailureDetailLogError::Missing)
        );
        assert_eq!(
            FailureDetailLogError::Oversize.message("--failure-detail-log"),
            "stall-recovery: --failure-detail-log exceeds 64KiB"
        );
    }

    #[test]
    fn failure_detail_log_materializes_and_reads_the_newest_ledger_sidecar() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let detail = root.path().join("large-detail.log");
        fs::write(&detail, vec![b'x'; MAX_DETAIL_FILE_BYTES_USIZE + 1])
            .expect("oversized detail fixture");
        assert_eq!(
            classify_failure_detail_log(&root, &detail),
            Err(FailureDetailLogError::Oversize)
        );

        let sidecar = materialize_truncated_failure_detail_log(&root, &detail)
            .expect("materialized detail sidecar");
        let fingerprint = sidecar
            .file_name()
            .and_then(|name| name.to_str())
            .and_then(|name| name.strip_prefix("stall-recovery-failure-detail-log-"))
            .and_then(|name| name.strip_suffix(".truncated.log"))
            .expect("legacy sidecar name");
        assert_eq!(fingerprint.len(), 16);
        assert!(fingerprint.bytes().all(|byte| byte.is_ascii_hexdigit()));
        assert_eq!(
            fs::metadata(&sidecar).expect("sidecar metadata").len(),
            MAX_DETAIL_FILE_BYTES
        );
        let relative = sidecar
            .strip_prefix(root.path())
            .expect("confined sidecar")
            .display()
            .to_string();
        let ledger = root.path().join("ledger.tsv");
        fs::write(
            &ledger,
            format!("utc=2026-01-01T00:00:00Z\tfailure_detail_log={relative}\n"),
        )
        .expect("ledger fixture");
        let fallback = root.path().join("fallback.tsv");

        assert_eq!(
            latest_failure_detail_log_sidecar(&root, &ledger, &fallback),
            Some(sidecar.clone())
        );
        let (detail, selected) =
            read_failure_detail_log_with_sidecar_fallback(&root, "", &ledger, &fallback, true)
                .expect("sidecar fallback");
        assert_eq!(selected, sidecar);
        assert_eq!(detail.len(), MAX_DETAIL_FILE_BYTES_USIZE);
    }

    #[cfg(unix)]
    #[test]
    fn failure_detail_log_rejects_a_symlink() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let target = root.path().join("target.log");
        let link = root.path().join("detail.log");
        fs::write(&target, "bounded detail\n").expect("detail fixture");
        std::os::unix::fs::symlink(&target, &link).expect("detail symlink");

        assert_eq!(
            classify_failure_detail_log(&root, &link),
            Err(FailureDetailLogError::Symlink)
        );
    }
}
