//! Pure helpers for the `/implement` commit-routing verbs (#8611).
//!
//! `implement commit`, `implement commit-route`, and `implement
//! checks-commit-route` share the site tables, failure-log format, stall-seed
//! ship-state patch, checks relay grammar, and Step 4 seed resolution ported
//! from `python/larch/implement/dispatch_commit_route.py`. The CLI owner
//! (`implement_commit_route_commands`) sequences the already-Rust sub-verbs and
//! git probes around these pure helpers.

use std::{
    collections::BTreeMap,
    fmt::Write,
    path::{Path, PathBuf},
};

use crate::{
    env_file::{KvDocument, ParseOptions},
    implement::self_edit_log::{file_sha256, read_self_edits},
    redaction::redact_secrets_only,
};

/// Outer deadline (ms) for the commit-route leg inside checks-commit-route.
pub const COMMIT_ROUTE_DEADLINE_MS: u64 = 3_600_000;
/// Default deadline (ms) for the checks front-half leg.
pub const CHECKS_DEADLINE_MS: u64 = 10_800_000;
/// Byte cap for a written commit-route failure log.
pub const COMMIT_ROUTE_FAILURE_LOG_MAX: usize = 12_000;
/// `ERROR=` value length cap the commit envelope enforces.
pub const COMMIT_ERROR_MAX: usize = 500;

/// `review-and-fix commit-fixes` outcomes that count as a successful commit.
pub const COMMIT_ROUTE_SUCCESS_OUTCOMES: [&str; 2] = ["ok", "noop"];
/// Commit KVs the commit-route relay is allowed to echo.
pub const STEP5_RESUME_COMMIT_RELAY_KEYS: [&str; 5] =
    ["COMMITTED", "ERROR", "SHA", "COMMIT_OUTCOME", "NEXT_ACTION"];

/// One commit-route stall site: where a failed commit stalls and how it logs.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CommitRouteSite {
    /// Ship-state `STALL_STEP` recorded on a stall.
    pub stall_step: &'static str,
    /// Ship-state `BAIL_REASON` recorded on a stall.
    pub bail_reason: &'static str,
    /// Human label printed at the head of the failure log.
    pub failure_log_label: &'static str,
    /// Whether a clean `git status --porcelain` gate follows a successful commit.
    pub porcelain_probe: bool,
}

/// The Step 4 implementation-commit site (`checks-commit-route --commit-site step4`).
pub const STEP4_COMMIT_SITE: CommitRouteSite = CommitRouteSite {
    stall_step: "4",
    bail_reason: "implementation-commit-failed",
    failure_log_label: "Step 4: implementation commit failed",
    porcelain_probe: false,
};

/// Resolve one `commit-route --site` value to its stall/log contract.
#[must_use]
pub fn commit_route_site(name: &str) -> Option<CommitRouteSite> {
    match name {
        "step5-self-review" => Some(CommitRouteSite {
            stall_step: "5",
            bail_reason: "review-fix-commit-failed",
            failure_log_label: "Step 5: self-review commit failed",
            porcelain_probe: false,
        }),
        "step5-resume-handoff" => Some(CommitRouteSite {
            stall_step: "5",
            bail_reason: "resume-handoff-commit-failed",
            failure_log_label: "Step 5: resume handoff commit failed",
            porcelain_probe: true,
        }),
        "step7" => Some(CommitRouteSite {
            stall_step: "7",
            bail_reason: "review-fix-commit-failed",
            failure_log_label: "Step 7: review-fix commit failed",
            porcelain_probe: false,
        }),
        _ => None,
    }
}

/// The three `commit-route` site names, sorted for the choice validator.
#[must_use]
pub const fn commit_route_site_names() -> [&'static str; 3] {
    ["step5-resume-handoff", "step5-self-review", "step7"]
}

/// A captured commit-route failure the stall path logs and seeds from.
pub struct CommitRouteFailure {
    /// Machine site key (e.g. `step7`, `step4`).
    pub site_name: String,
    /// Resolved stall/log contract for `site_name`.
    pub site: CommitRouteSite,
    /// Exit code recorded in the log and forwarded to `run-log append-failure`.
    pub exit_code: i32,
    /// Short machine reason recorded in the log.
    pub reason: String,
    /// Captured child stdout.
    pub stdout: String,
    /// Captured child stderr.
    pub stderr: String,
}

/// Every line whose text equals `KEY=<value>`, returning the values in order.
#[must_use]
pub fn parse_line_anchored(stdout: &str, key: &str) -> Vec<String> {
    let prefix = format!("{key}=");
    stdout
        .lines()
        .filter_map(|line| line.strip_prefix(&prefix).map(str::to_owned))
        .collect()
}

/// Parse one whitespace-delimited `KEY=value` checks line (first value wins).
#[must_use]
pub fn parse_whitespace_kv_line(line: &str) -> BTreeMap<String, String> {
    let mut map = BTreeMap::new();
    for token in line.split_whitespace() {
        let Some((key, value)) = token.split_once('=') else {
            continue;
        };
        if key.is_empty()
            || !key
                .bytes()
                .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
        {
            continue;
        }
        map.entry(key.to_owned())
            .or_insert_with(|| value.to_owned());
    }
    map
}

/// Build the single relay line a checks capture projects to its consumer.
#[must_use]
pub fn checks_relay_line(captured: &BTreeMap<String, String>) -> String {
    let get = |key: &str| captured.get(key).map_or("", String::as_str);
    if get("RELEVANT_CHECKS_SKIPPED") == "true" {
        return format!("RELEVANT_CHECKS_SKIPPED=true SITE={}", get("SITE"));
    }
    if get("RELEVANT_CHECKS_OK") == "true" {
        let mut line = format!(
            "RELEVANT_CHECKS_OK=true SITE={} COVERAGE={} PHASE={}",
            get("SITE"),
            get("COVERAGE"),
            get("PHASE"),
        );
        if !get("WARN").is_empty() {
            let _ = write!(line, " WARN={}", get("WARN"));
        }
        return line;
    }
    let reason = if get("FAILURE_REASON").is_empty() {
        "checks-failed"
    } else {
        get("FAILURE_REASON")
    };
    let mut parts = vec!["STATUS=fail".to_owned(), format!("FAILURE_REASON={reason}")];
    for key in ["EXIT_CODE", "PHASE", "DIGEST_FILE", "REDACTED_LOG_FILE"] {
        if !get(key).is_empty() {
            parts.push(format!("{key}={}", get(key)));
        }
    }
    parts.join(" ")
}

/// Whether a checks capture is a pass (skipped or ok) rather than a failure.
#[must_use]
pub fn checks_pass(captured: &BTreeMap<String, String>) -> bool {
    if captured.get("STATUS").map(String::as_str) == Some("fail") {
        return false;
    }
    captured.get("RELEVANT_CHECKS_OK").map(String::as_str) == Some("true")
        || captured.get("RELEVANT_CHECKS_SKIPPED").map(String::as_str) == Some("true")
}

/// Slug for the failure-log basename derived from an arbitrary site name.
#[must_use]
pub fn commit_route_failure_log_name(site: &str) -> String {
    let mut slug = String::with_capacity(site.len());
    let mut last_dash = false;
    for ch in site.chars() {
        if ch.is_ascii_alphanumeric() || matches!(ch, '_' | '.' | '-') {
            slug.push(ch);
            last_dash = false;
        } else if !last_dash {
            slug.push('-');
            last_dash = true;
        }
    }
    let slug = slug.trim_matches('-');
    let slug = if slug.is_empty() { "unknown" } else { slug };
    format!("commit-route-{slug}.failure.log")
}

/// Full path of the failure log for one commit-route site.
#[must_use]
pub fn commit_route_failure_log_path(implement_tmpdir: &Path, site: &str) -> PathBuf {
    implement_tmpdir.join(commit_route_failure_log_name(site))
}

/// Render the failure-log body, truncated to the shared cap.
#[must_use]
pub fn commit_route_failure_log_text(failure: &CommitRouteFailure) -> String {
    let text = format!(
        "{label}\nsite={site}\nexit_code={exit}\nreason={reason}\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}\n",
        label = failure.site.failure_log_label,
        site = failure.site_name,
        exit = failure.exit_code,
        reason = failure.reason,
        stdout = failure.stdout,
        stderr = failure.stderr,
    );
    if text.len() > COMMIT_ROUTE_FAILURE_LOG_MAX {
        let mut truncated: String = text.chars().take(COMMIT_ROUTE_FAILURE_LOG_MAX).collect();
        truncated.push_str("\n[truncated]\n");
        truncated
    } else {
        text
    }
}

/// Fold a git error stream to one line, capped at [`COMMIT_ERROR_MAX`].
#[must_use]
pub fn fold_commit_error(stderr: &str, stdout: &str) -> String {
    let source = if stderr.is_empty() { stdout } else { stderr };
    let folded: String = source.replace('\n', " ");
    folded.chars().take(COMMIT_ERROR_MAX).collect()
}

fn is_allowed_ship_key(key: &str) -> bool {
    !key.is_empty() && super::ship_state::SHIP_STATE_ALLOWED_KEYS.contains(&key)
}

/// Outcome of a durable stall-seed ship-state patch attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ShipStatePatch {
    /// The existing ship state carried KV and was patched in place.
    Patched,
    /// The existing ship state is malformed or symlinked; refuse to patch.
    Refused,
    /// No usable ship state exists; the caller should seed a fresh one.
    Absent,
}

/// True when any physical line looks like `IDENT=` — the has-KV probe.
#[must_use]
pub fn ship_state_has_kv(text: &str) -> bool {
    KvDocument::parse(text, ParseOptions::legacy()).is_ok_and(|document| {
        document.select_all().keys().any(|key| {
            !key.is_empty()
                && key
                    .bytes()
                    .next()
                    .is_some_and(|b| b.is_ascii_alphabetic() || b == b'_')
                && key.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
        })
    })
}

/// Patch the stall keys into an existing ship-state file, preserving allowed
/// keys and last-value semantics; mirrors Python `_patch_ship_state_keys`.
///
/// Returns [`ShipStatePatch::Absent`] when no file exists (seed a fresh state),
/// [`ShipStatePatch::Refused`] for a symlinked or malformed-but-nonempty state,
/// and [`ShipStatePatch::Patched`] after a successful atomic rewrite.
#[must_use]
pub fn patch_ship_state_stall(
    state_file: &Path,
    stall_step: &str,
    bail_reason: &str,
) -> ShipStatePatch {
    if state_file.is_symlink() {
        return ShipStatePatch::Refused;
    }
    let Ok(metadata) = std::fs::symlink_metadata(state_file) else {
        return ShipStatePatch::Absent;
    };
    if !metadata.is_file() {
        return ShipStatePatch::Absent;
    }
    let Ok(text) = std::fs::read_to_string(state_file) else {
        return ShipStatePatch::Refused;
    };
    if !ship_state_has_kv(&text) {
        return if text.trim().is_empty() {
            ShipStatePatch::Absent
        } else {
            ShipStatePatch::Refused
        };
    }
    let document = KvDocument::parse(&text, ParseOptions::legacy()).unwrap_or_default();
    // Last value wins across allowed keys, preserving first-seen order.
    let mut order: Vec<String> = Vec::new();
    let mut fields: BTreeMap<String, String> = BTreeMap::new();
    for row in document.rows() {
        let key = row.key();
        if !is_allowed_ship_key(key) {
            continue;
        }
        if !fields.contains_key(key) {
            order.push(key.to_owned());
        }
        fields.insert(key.to_owned(), row.value().to_owned());
    }
    for (key, value) in [
        ("STALL_TRACKING", "true"),
        ("STALL_STEP", stall_step),
        ("BAIL_REASON", bail_reason),
    ] {
        if !fields.contains_key(key) {
            order.push(key.to_owned());
        }
        fields.insert(key.to_owned(), value.to_owned());
    }
    // A stall value must never carry a newline into the KV stream.
    if fields.values().any(|value| value.contains(['\n', '\r'])) {
        return ShipStatePatch::Refused;
    }
    let mut rendered = String::new();
    for key in &order {
        if let Some(value) = fields.get(key) {
            rendered.push_str(key);
            rendered.push('=');
            rendered.push_str(value);
            rendered.push('\n');
        }
    }
    match crate::write_bytes_atomic(state_file, rendered.as_bytes()) {
        Ok(()) => ShipStatePatch::Patched,
        Err(_) => ShipStatePatch::Refused,
    }
}

/// A resolved Step 4 commit seed: message plus a frozen NUL pathspec, or a noop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Step4CommitSeed {
    /// Redacted commit message.
    pub message: String,
    /// Frozen NUL-delimited pathspec, or `None` for a noop seed.
    pub pathspec: Option<PathBuf>,
    /// Reason recorded when `pathspec` is `None`.
    pub noop_reason: String,
    /// Whether the Step 3 self-edit union must refresh the pathspec.
    pub refresh_step3_self_edits: bool,
}

/// A file exists, is not a symlink, and has non-zero size.
#[must_use]
pub fn path_readable_nonempty(path: &Path) -> bool {
    std::fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

/// Read a redacted, trimmed commit message from a file (empty on failure).
#[must_use]
pub fn read_redacted_message(path: &Path) -> String {
    std::fs::read_to_string(path).map_or_else(
        |_| String::new(),
        |text| redact_secrets_only(&text).trim().to_owned(),
    )
}

/// Split a NUL-delimited pathspec file into its non-empty entries.
#[must_use]
pub fn read_nul_pathspec(path: &Path) -> Vec<String> {
    let Ok(raw) = std::fs::read(path) else {
        return Vec::new();
    };
    raw.split(|byte| *byte == 0)
        .filter(|segment| !segment.is_empty())
        .map(|segment| String::from_utf8_lossy(segment).into_owned())
        .collect()
}

/// Serialize a pathspec back to its NUL-delimited byte form.
#[must_use]
pub fn nul_pathspec_bytes(paths: &[String]) -> Vec<u8> {
    let mut data = Vec::new();
    for path in paths {
        data.extend_from_slice(path.as_bytes());
        data.push(0);
    }
    data
}

/// Union still-attributed Step 3 self-edits into a frozen pathspec.
///
/// Given the current dirty paths, returns the extra rel paths whose recorded
/// `lint-fix:step3`/`pre-commit-autofix` post-sha still matches the working
/// tree. Unrelated concurrent edits stay outside the commit route.
#[must_use]
pub fn step3_self_edit_additions(
    implement_tmpdir: &Path,
    repo_root: &Path,
    dirty_paths: &[String],
) -> Vec<String> {
    let dirty: std::collections::BTreeSet<&str> = dirty_paths.iter().map(String::as_str).collect();
    let mut additions = Vec::new();
    for record in read_self_edits(implement_tmpdir) {
        if record.source != "lint-fix:step3" && record.source != "pre-commit-autofix" {
            continue;
        }
        if !dirty.contains(record.path.as_str()) {
            continue;
        }
        let path = Path::new(&record.path);
        if path.is_absolute() || path.components().any(|c| c.as_os_str() == "..") {
            continue;
        }
        if file_sha256(repo_root, &record.path) == record.post_sha256 {
            additions.push(record.path.clone());
        }
    }
    additions
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn site_lookup_and_step4_contract() {
        assert!(commit_route_site("bogus").is_none());
        let step7 = commit_route_site("step7").expect("step7");
        assert_eq!(step7.stall_step, "7");
        assert_eq!(step7.bail_reason, "review-fix-commit-failed");
        assert!(!step7.porcelain_probe);
        assert!(
            commit_route_site("step5-resume-handoff")
                .expect("resume")
                .porcelain_probe
        );
        assert_eq!(
            STEP4_COMMIT_SITE.bail_reason,
            "implementation-commit-failed"
        );
    }

    #[test]
    fn line_anchored_only_matches_full_prefix_lines() {
        let stdout = "COMMIT_OUTCOME=ok\nX COMMIT_OUTCOME=no\nCOMMIT_OUTCOME=noop\n";
        assert_eq!(
            parse_line_anchored(stdout, "COMMIT_OUTCOME"),
            ["ok", "noop"]
        );
    }

    #[test]
    fn whitespace_kv_first_value_wins_and_skips_bad_keys() {
        let map =
            parse_whitespace_kv_line("RELEVANT_CHECKS_OK=true SITE=step5 site=lower SITE=dup");
        assert_eq!(map.get("RELEVANT_CHECKS_OK").unwrap(), "true");
        assert_eq!(map.get("SITE").unwrap(), "step5");
        assert!(!map.contains_key("site"));
    }

    #[test]
    fn checks_relay_line_shapes() {
        let mut skip = BTreeMap::new();
        skip.insert("RELEVANT_CHECKS_SKIPPED".to_owned(), "true".to_owned());
        skip.insert("SITE".to_owned(), "step3".to_owned());
        assert_eq!(
            checks_relay_line(&skip),
            "RELEVANT_CHECKS_SKIPPED=true SITE=step3"
        );

        let mut ok = BTreeMap::new();
        ok.insert("RELEVANT_CHECKS_OK".to_owned(), "true".to_owned());
        ok.insert("SITE".to_owned(), "step5".to_owned());
        ok.insert("COVERAGE".to_owned(), "rust".to_owned());
        ok.insert("PHASE".to_owned(), "front".to_owned());
        ok.insert("WARN".to_owned(), "slow".to_owned());
        assert_eq!(
            checks_relay_line(&ok),
            "RELEVANT_CHECKS_OK=true SITE=step5 COVERAGE=rust PHASE=front WARN=slow"
        );
        assert!(checks_pass(&ok));

        let mut fail = BTreeMap::new();
        fail.insert("STATUS".to_owned(), "fail".to_owned());
        fail.insert("EXIT_CODE".to_owned(), "2".to_owned());
        assert_eq!(
            checks_relay_line(&fail),
            "STATUS=fail FAILURE_REASON=checks-failed EXIT_CODE=2"
        );
        assert!(!checks_pass(&fail));
    }

    #[test]
    fn failure_log_name_slug_and_truncation() {
        assert_eq!(
            commit_route_failure_log_name("step7"),
            "commit-route-step7.failure.log"
        );
        assert_eq!(
            commit_route_failure_log_name("step5/self review"),
            "commit-route-step5-self-review.failure.log"
        );
        assert_eq!(
            commit_route_failure_log_name("///"),
            "commit-route-unknown.failure.log"
        );
        let failure = CommitRouteFailure {
            site_name: "step7".to_owned(),
            site: commit_route_site("step7").unwrap(),
            exit_code: 1,
            reason: "boom".to_owned(),
            stdout: "x".repeat(COMMIT_ROUTE_FAILURE_LOG_MAX + 50),
            stderr: String::new(),
        };
        let text = commit_route_failure_log_text(&failure);
        assert!(text.ends_with("[truncated]\n"));
        assert!(text.len() <= COMMIT_ROUTE_FAILURE_LOG_MAX + "\n[truncated]\n".len());
    }

    #[test]
    fn fold_commit_error_prefers_stderr_and_caps() {
        assert_eq!(fold_commit_error("a\nb", "ignored"), "a b");
        assert_eq!(
            fold_commit_error("", "only stdout\nhere"),
            "only stdout here"
        );
        assert_eq!(
            fold_commit_error(&"z".repeat(600), "").len(),
            COMMIT_ERROR_MAX
        );
    }

    #[test]
    fn ship_state_patch_variants() {
        let dir = tempfile::tempdir().expect("tmp");
        let state = dir.path().join("ship-pr-state.sh");
        assert_eq!(
            patch_ship_state_stall(&state, "5", "boom"),
            ShipStatePatch::Absent
        );
        std::fs::write(&state, "   \n").expect("write empty");
        assert_eq!(
            patch_ship_state_stall(&state, "5", "boom"),
            ShipStatePatch::Absent
        );
        std::fs::write(&state, "no kv here\n").expect("write junk");
        assert_eq!(
            patch_ship_state_stall(&state, "5", "boom"),
            ShipStatePatch::Refused
        );
        std::fs::write(&state, "PHASE=ship\nUNKNOWN_KEY=drop\nSTALL_STEP=1\n").expect("write kv");
        assert_eq!(
            patch_ship_state_stall(&state, "5", "resume-handoff-commit-failed"),
            ShipStatePatch::Patched
        );
        let patched = std::fs::read_to_string(&state).expect("read");
        assert!(patched.contains("PHASE=ship\n"));
        assert!(!patched.contains("UNKNOWN_KEY"));
        assert!(patched.contains("STALL_STEP=5\n"));
        assert!(patched.contains("STALL_TRACKING=true\n"));
        assert!(patched.contains("BAIL_REASON=resume-handoff-commit-failed\n"));
    }

    #[test]
    fn nul_pathspec_round_trips() {
        let dir = tempfile::tempdir().expect("tmp");
        let file = dir.path().join("paths.nul");
        let paths = vec!["a b.rs".to_owned(), "c/d.rs".to_owned()];
        std::fs::write(&file, nul_pathspec_bytes(&paths)).expect("write");
        assert_eq!(read_nul_pathspec(&file), paths);
    }
}
