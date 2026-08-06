//! Filesystem, Git, and bgjob effects for Rust-owned stall-recovery commands.
use crate::{
    GixRepository, PathIntent, SystemProcessIdentityHost, TemporaryRoot, atomic_write_utf8_in,
    ensure_directory_chain,
};
use larch_core::{
    CommentPolicy, CrStrip, DuplicatePolicy, KvDocument, ParseOptions, RepositoryRead,
    artifact_prefix_valid, daemon_liveness, kv_text, public_text_is_sensitive, read_for,
    safe_phase, safe_step, select_kv_bytes, terminal_state_valid, unlink_entry,
    validate_process_identity,
};
use regex::Regex;
use std::{
    env, fs,
    fs::OpenOptions,
    io::ErrorKind,
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
const EVIDENCE_NAMES: &[&str] = &[
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
const MAX_DETAIL_FILE_BYTES: u64 = 65_536;
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
    sources.extend(EVIDENCE_NAMES.iter().map(|name| root.path().join(name)));
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
    use super::{StateMutationError, clear_stall, seed_terminal_state, terminal_state_is_valid};
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
}
