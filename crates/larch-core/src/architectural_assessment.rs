//! Step 8 architectural assessment substrate (#8615).
//!
//! Library owner for evidence materialization, durable-note persistence, ship
//! outcome sidecars, detail sanitization, and final-report sections. Ported
//! from `larch.implement.architectural_assessment` plus the used surface of
//! `larch.core.architectural_guidelines` and ship outcome writers in
//! `larch.implement.ship_guidelines`.
//!
//! Git identity and diff materialization are injected through [`AssessmentGit`]
//! so this crate stays outside the closed Git CLI ownership boundary; the
//! future CLI command layer supplies the live adapter.

use std::{
    collections::{BTreeMap, BTreeSet, HashSet},
    fs,
    path::{Component, Path, PathBuf},
    sync::LazyLock,
};

use chrono::{SecondsFormat, Utc};
use regex::Regex;
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};

use crate::{
    AssessmentKind, DuplicateInputPolicy, DuplicatePolicy, KvDocument, MalformedLinePolicy,
    ParseOptions, bgjob_daemon::redact_outbound, compose_execution_issue,
    execution_issue_body_keys, execution_issue_chunks, execution_issue_sections,
    existing_execution_issue_keys, implement::write_bytes_atomic,
    logging_util::sanitize_diagnostic_line, redact_batch_payload, redaction::redact,
    validate_ship_outcome_record,
};

/// Kind order preserved by [`normalize_kinds`].
pub const KIND_ORDER: [AssessmentKind; 2] =
    [AssessmentKind::Invariants, AssessmentKind::Guidelines];
/// `submit` exit code when HEAD moved between materialize and submit.
pub const EXIT_HEAD_DRIFT: i32 = 10;
/// Inclusive assessment-note character cap.
pub const MAX_ASSESSMENT_CHARS: usize = 12_000;
/// Stdin byte cap for `sanitize-detail`.
pub const MAX_SANITIZE_DETAIL_BYTES: usize = 8 * 1024;

pub const NOTE_STATE_AUTHORED: &str = "authored";
pub const NOTE_STATE_DETERMINISTIC_CLEAN: &str = "deterministic-clean";
pub const NOTE_STATE_UNAVAILABLE: &str = "unavailable";
pub const ASSESSMENT_OUTCOME_CLEAN: &str = "clean";
pub const ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME: &str = "invalid-explicit-outcome";
pub const ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH: &str =
    "clean-outcome-prose-mismatch: identifier citation found in clean note";
pub const ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA: &str = "missing-or-invalid-outcome-metadata";
pub const ASSESSMENT_RESULT_REAUTHOR_REQUIRED: &str = "reauthor-required";
pub const REASON_DETERMINISTIC_CLEAN: &str = "deterministic-clean";
pub const REASON_UNAVAILABLE: &str = "unavailable";

const NOTE_STATE_TOKENS: &[&str] = &[
    NOTE_STATE_AUTHORED,
    NOTE_STATE_DETERMINISTIC_CLEAN,
    NOTE_STATE_UNAVAILABLE,
];
const REAUTHOR_REASONS: &[&str] = &[
    ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME,
    ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH,
    ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA,
];
const LEGACY_WARNING: &str = "architectural-guideline-warnings.md";
const LEGACY_WARNING_ENV: &str = "architectural-guideline-warnings.meta.env";
const EXECUTION_WARNINGS_CATEGORY: &str = "Warnings";

static DIFF_HEADER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^diff --git a/(\S+) b/(\S+)$").expect("diff header"));
static IDENTIFIER_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^#{1,6}\s+((?:I|G)-[A-Za-z0-9-]+-\d+):").expect("identifier heading")
});
static COMMIT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[0-9a-f]{40}$").expect("commit sha"));
static BASE_REF_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$").expect("base ref"));
static EXCEPTION_LINE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^\s*Exception:").expect("exception line"));
static CLEAN_ASSESSMENT_LEAD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^\W*no\b[^.;\n]*\b(?:violation|deviation)s?\b").expect("clean lead")
});
static GUIDELINE_ID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"G-[A-Za-z0-9-]+-\d+").expect("guideline id"));
static INVARIANT_ID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"I-[A-Za-z0-9-]+-\d+").expect("invariant id"));
static RUN_ID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9._-]+$").expect("run id"));

/// Validated evidence identity for one requested kind.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MaterializedEvidence {
    /// Assessment kind token.
    pub kind: AssessmentKind,
    /// Covered HEAD SHA.
    pub head_sha: String,
    /// Covered base ref (`origin/main` or `upstream/main`).
    pub base_ref: String,
    /// Frozen diff snapshot path.
    pub diff_path: PathBuf,
    /// Frozen diff text.
    pub diff_text: String,
    /// SHA-256 of the frozen diff.
    pub diff_fingerprint: String,
    /// Knowledge file path under the repo root.
    pub knowledge_path: PathBuf,
    /// SHA-256 of the knowledge file bytes.
    pub knowledge_sha256: String,
    /// Heading identifiers present in the knowledge file.
    pub identifiers: BTreeSet<String>,
}

/// Validated result for one kind after submit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AssessmentResult {
    /// Assessment kind.
    pub kind: AssessmentKind,
    /// Authored outcome state (`clean` / `deviation` / `violation`).
    pub state: String,
    /// Redacted assessment note body.
    pub assessment: String,
    /// Covered HEAD SHA.
    pub head_sha: String,
    /// Covered base ref.
    pub base_ref: String,
    /// Frozen diff fingerprint.
    pub diff_fingerprint: String,
    /// Knowledge SHA-256.
    pub knowledge_sha256: String,
}

/// HEAD moved; orchestrator must rematerialize.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HeadDrift(pub String);

impl std::fmt::Display for HeadDrift {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for HeadDrift {}

/// Durable deviation awaits a retryable warning-log append.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DeviationLogPending(pub String);

impl std::fmt::Display for DeviationLogPending {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for DeviationLogPending {}

/// Assessment must be revised before durable persistence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReauthorRequired(pub String);

impl std::fmt::Display for ReauthorRequired {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for ReauthorRequired {}

/// Git operations the assessment substrate needs from the CLI adapter layer.
pub trait AssessmentGit {
    /// `git rev-parse` / verify helper returning trimmed stdout.
    ///
    /// # Errors
    /// Returns a sanitized diagnostic when git fails.
    fn git_read(&self, repo_root: &Path, argv: &[&str]) -> Result<String, String>;

    /// Historical merge-base..HEAD diff excluding `larch-logs/**`.
    ///
    /// # Errors
    /// Returns a diagnostic when merge-base or diff fails.
    fn implementation_diff_for_head(
        &self,
        repo_root: &Path,
        head_sha: &str,
        base_remote: &str,
        base_ref: &str,
    ) -> Result<String, String>;

    /// NUL-delimited changed paths between two commits (`--no-renames --name-only -z`).
    ///
    /// # Errors
    /// Returns a diagnostic when the path listing is incomplete or fails.
    fn incremental_paths(
        &self,
        repo_root: &Path,
        old_head: &str,
        new_head: &str,
    ) -> Result<Vec<String>, String>;
}

/// Validate, deduplicate, and order requested assessment kinds.
///
/// # Errors
/// Returns when no kinds are requested or an unknown kind appears.
pub fn normalize_kinds(raw_kinds: &[impl AsRef<str>]) -> Result<Vec<AssessmentKind>, String> {
    let mut requested = HashSet::new();
    for raw in raw_kinds {
        let kind = parse_kind(raw.as_ref())?;
        requested.insert(kind);
    }
    if requested.is_empty() {
        return Err("at least one --kind is required".to_owned());
    }
    Ok(KIND_ORDER
        .into_iter()
        .filter(|kind| requested.contains(kind))
        .collect())
}

fn parse_kind(raw: &str) -> Result<AssessmentKind, String> {
    match raw {
        "invariants" => Ok(AssessmentKind::Invariants),
        "guidelines" => Ok(AssessmentKind::Guidelines),
        other => Err(format!("unsupported assessment kind: {other}")),
    }
}

/// SHA-256 hex of UTF-8 diff text (Python `surrogateescape` is a no-op for valid UTF-8).
#[must_use]
pub fn diff_fingerprint(diff_text: &str) -> String {
    hex_sha256(diff_text.as_bytes())
}

fn hex_sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

/// Return true only when every changed path is proven outside architectural scope.
#[must_use]
pub fn deterministic_out_of_scope(diff_text: &str) -> bool {
    let Some(paths) = diff_paths(diff_text) else {
        return false;
    };
    if paths.is_empty() {
        return false;
    }
    paths.iter().all(|path| {
        (path.starts_with("docs/") && Path::new(path).extension().is_some_and(|ext| ext == "md"))
            || path.starts_with("larch-logs/")
    })
}

fn diff_paths(diff_text: &str) -> Option<Vec<String>> {
    if diff_text.trim().is_empty() {
        return Some(Vec::new());
    }
    let mut paths = Vec::new();
    for line in diff_text.lines() {
        if line.starts_with("Binary files ")
            || line.starts_with("GIT binary patch")
            || line.starts_with("rename from ")
            || line.starts_with("rename to ")
        {
            return None;
        }
        if !line.starts_with("diff --git ") {
            continue;
        }
        let captures = DIFF_HEADER_RE.captures(line)?;
        let left = captures.get(1)?.as_str();
        let right = captures.get(2)?.as_str();
        if left != right {
            return None;
        }
        if !is_safe_rel_path(left) {
            return None;
        }
        paths.push(left.to_owned());
    }
    if paths.is_empty() { None } else { Some(paths) }
}

fn is_safe_rel_path(path: &str) -> bool {
    if path.starts_with('/') || path.contains('\\') || path.contains("//") {
        return false;
    }
    let candidate = Path::new(path);
    if candidate.is_absolute() {
        return false;
    }
    if candidate.to_string_lossy() != path {
        return false;
    }
    candidate.components().all(|part| match part {
        Component::Normal(os) => !os.is_empty() && os != "." && os != "..",
        _ => false,
    })
}

/// Sanitize one diagnostic for a line-oriented handoff.
#[must_use]
pub fn sanitize_detail(text: &str, implement_tmpdir: &Path) -> String {
    let redacted = redact_outbound(text).replace(
        &implement_tmpdir.display().to_string(),
        "<implement-tmpdir>",
    );
    let flattened: String = redacted
        .chars()
        .map(|character| {
            if character >= ' ' && character != '\u{7f}' {
                character
            } else {
                ' '
            }
        })
        .collect();
    sanitize_diagnostic_line(&flattened)
        .trim()
        .chars()
        .take(500)
        .collect()
}

/// Render final-report architectural sections (fail-soft per section).
#[must_use]
pub fn final_report_sections(implement_tmpdir: &Path, head_sha: &str) -> String {
    let mut sections = Vec::new();
    for (kind, heading) in [
        (AssessmentKind::Invariants, "Architectural invariants"),
        (AssessmentKind::Guidelines, "Architectural guidelines"),
    ] {
        if let Ok(Some(section)) =
            consumable_note_section(implement_tmpdir, kind, heading, head_sha)
        {
            sections.push(section.trim_end_matches('\n').to_owned());
        }
    }
    if sections.is_empty() {
        String::new()
    } else {
        format!("{}\n", sections.join("\n\n"))
    }
}

fn consumable_note_section(
    implement_tmpdir: &Path,
    kind: AssessmentKind,
    heading: &str,
    head_sha: &str,
) -> Result<Option<String>, ()> {
    if head_sha.is_empty() || !note_consumable(implement_tmpdir, head_sha, kind, "", None, None) {
        return Ok(None);
    }
    let note = fs::read_to_string(durable_note_path(implement_tmpdir, kind)).map_err(|_| ())?;
    let stripped = redact_note_fail_soft(&note).trim().to_owned();
    if stripped.is_empty() {
        return Ok(None);
    }
    Ok(Some(format!("## {heading}\n\n{stripped}\n")))
}

fn redact_note_fail_soft(note: &str) -> String {
    let redacted = redact(note).text().to_owned();
    if redacted.contains("[content truncated") {
        return String::new();
    }
    redacted
}

fn reauthor_status(reason: &str) -> String {
    let bounded = if REAUTHOR_REASONS.contains(&reason) {
        reason
    } else {
        ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA
    };
    format!("{ASSESSMENT_RESULT_REAUTHOR_REQUIRED}:{bounded}")
}

fn kind_paths(
    kind: AssessmentKind,
    implement_tmpdir: &Path,
    repo_root: &Path,
) -> (PathBuf, PathBuf, PathBuf) {
    (
        implement_tmpdir.join(kind.materialize_env_filename()),
        implement_tmpdir.join(kind.materialized_diff_filename()),
        repo_root.join(kind.knowledge_filename()),
    )
}

/// Durable note path for one kind.
#[must_use]
pub fn durable_note_path(implement_tmpdir: &Path, kind: AssessmentKind) -> PathBuf {
    implement_tmpdir.join(kind.durable_note_filename())
}

fn durable_note_env_path(implement_tmpdir: &Path, kind: AssessmentKind) -> PathBuf {
    implement_tmpdir.join(kind.durable_note_env_filename())
}

fn ship_outcome_path(implement_tmpdir: &Path, kind: AssessmentKind) -> PathBuf {
    implement_tmpdir.join(kind.ship_outcome_sidecar_filename())
}

/// Validate a recorded materialization against the covered snapshot identity.
///
/// # Errors
/// Returns when metadata, paths, fingerprints, or historical diffs mismatch.
pub fn validate_materialization(
    kind: AssessmentKind,
    repo_root: &Path,
    implement_tmpdir: &Path,
    git: &dyn AssessmentGit,
) -> Result<MaterializedEvidence, String> {
    let (metadata_path, expected_diff_path, expected_knowledge_path) =
        kind_paths(kind, implement_tmpdir, repo_root);
    let metadata = read_env_strict(&metadata_path, implement_tmpdir)?;
    let status_key = kind.status_env_key();
    let knowledge_key = kind.path_env_key();
    let required = [
        "STATUS",
        "HEAD_SHA",
        "BASE_REF",
        "DIFF_FINGERPRINT",
        "DIFF_SNAPSHOT",
        status_key,
        knowledge_key,
    ];
    if required
        .iter()
        .any(|key| metadata.get(*key).is_none_or(String::is_empty))
        || metadata.get("STATUS").map(String::as_str) != Some("present")
        || metadata.get(status_key).map(String::as_str) != Some("present")
    {
        return Err(format!(
            "incomplete {} materialization metadata",
            kind.key()
        ));
    }
    let head_sha = metadata["HEAD_SHA"].clone();
    let base_ref = metadata["BASE_REF"].clone();
    validate_recorded_identity(&head_sha, &base_ref)?;
    let resolved_head = git.git_read(
        repo_root,
        &["rev-parse", "--verify", &format!("{head_sha}^{{commit}}")],
    )?;
    if resolved_head != head_sha {
        return Err(format!("{} covered HEAD is not canonical", kind.key()));
    }
    let _ = git.git_read(
        repo_root,
        &["rev-parse", "--verify", &format!("{base_ref}^{{commit}}")],
    )?;
    let diff_path = PathBuf::from(&metadata["DIFF_SNAPSHOT"]);
    if !same_resolved_path(&diff_path, &expected_diff_path) {
        return Err(format!("{} diff snapshot path mismatch", kind.key()));
    }
    let knowledge_path = PathBuf::from(&metadata[knowledge_key]);
    if !same_resolved_path(&knowledge_path, &expected_knowledge_path) {
        return Err(format!("{} knowledge path mismatch", kind.key()));
    }
    let diff_text = read_regular(&diff_path, implement_tmpdir)?;
    if diff_fingerprint(&diff_text) != metadata["DIFF_FINGERPRINT"] {
        return Err(format!("{} frozen diff fingerprint mismatch", kind.key()));
    }
    let recorded = recorded_diff(repo_root, &head_sha, &base_ref, git)?;
    if recorded != diff_text {
        return Err(format!(
            "{} frozen diff does not match covered snapshot",
            kind.key()
        ));
    }
    let knowledge_text = read_regular(&knowledge_path, repo_root)?;
    let identifiers = IDENTIFIER_HEADING_RE
        .captures_iter(&knowledge_text)
        .filter_map(|captures| captures.get(1).map(|matched| matched.as_str().to_owned()))
        .collect();
    Ok(MaterializedEvidence {
        kind,
        head_sha,
        base_ref,
        diff_path,
        diff_text,
        diff_fingerprint: metadata["DIFF_FINGERPRINT"].clone(),
        knowledge_path,
        knowledge_sha256: hex_sha256(knowledge_text.as_bytes()),
        identifiers,
    })
}

fn validate_recorded_identity(head_sha: &str, base_ref: &str) -> Result<(), String> {
    if COMMIT_RE.captures(head_sha).is_none() {
        return Err("materialization HEAD_SHA is invalid".to_owned());
    }
    if BASE_REF_RE.captures(base_ref).is_none()
        || base_ref.starts_with('-')
        || !base_ref.contains('/')
    {
        return Err("materialization BASE_REF is invalid".to_owned());
    }
    Ok(())
}

fn recorded_diff(
    repo_root: &Path,
    head_sha: &str,
    base_ref: &str,
    git: &dyn AssessmentGit,
) -> Result<String, String> {
    validate_recorded_identity(head_sha, base_ref)?;
    let (remote, ref_name) = base_ref
        .split_once('/')
        .ok_or_else(|| "materialization BASE_REF is invalid".to_owned())?;
    git.implementation_diff_for_head(repo_root, head_sha, remote, ref_name)
}

/// Materialize evidence for requested kinds; return statuses and pending evidence.
///
/// # Errors
/// Returns on invalid roots, repeated HEAD drift, or materialization failure.
pub fn materialize(
    kinds: &[impl AsRef<str>],
    repo_root: &Path,
    implement_tmpdir: &Path,
    git: &dyn AssessmentGit,
) -> Result<(BTreeMap<String, String>, Vec<MaterializedEvidence>), String> {
    let normalized = normalize_kinds(kinds)?;
    let root = resolve_dir(repo_root)?;
    let tmpdir = resolve_dir(implement_tmpdir)?;
    prepare_pending(&normalized, &root, &tmpdir, git)
}

/// Revalidate identity fail-closed and persist one authored assessment note.
///
/// # Errors
/// Returns usage/validation errors, [`HeadDrift`], [`ReauthorRequired`], or
/// [`DeviationLogPending`].
pub fn submit(
    kind: &str,
    state: &str,
    note: &str,
    repo_root: &Path,
    implement_tmpdir: &Path,
    allow_exception: bool,
    git: &dyn AssessmentGit,
) -> Result<AssessmentResult, SubmitError> {
    let normalized = normalize_kinds(&[kind]).map_err(SubmitError::Value)?;
    let single = normalized[0];
    let allowed = if single.is_invariant() {
        ["clean", "violation"].as_slice()
    } else {
        ["clean", "deviation"].as_slice()
    };
    if !allowed.contains(&state) {
        return Err(SubmitError::Value(format!(
            "unsupported {} assessment state: {state}",
            single.key()
        )));
    }
    if note.trim().is_empty() || note.len() > MAX_ASSESSMENT_CHARS {
        return Err(SubmitError::Value(
            "assessment note is empty or oversized".to_owned(),
        ));
    }
    if single == AssessmentKind::Guidelines
        && state == "deviation"
        && !allow_exception
        && EXCEPTION_LINE_RE.is_match(note)
    {
        return Err(SubmitError::Value(
            "guideline deviation note carries a documented-exception block; \
             only the fix-ladder decline re-submission (--allow-exception) may persist it"
                .to_owned(),
        ));
    }
    let root = resolve_dir(repo_root).map_err(SubmitError::Value)?;
    let tmpdir = resolve_dir(implement_tmpdir).map_err(SubmitError::Value)?;
    let evidence =
        validate_materialization(single, &root, &tmpdir, git).map_err(SubmitError::Value)?;
    let current_head = git
        .git_read(&root, &["rev-parse", "HEAD"])
        .map_err(SubmitError::Value)?;
    if current_head != evidence.head_sha {
        return Err(SubmitError::HeadDrift(HeadDrift(
            "HEAD changed between architectural assessment materialize and submit".to_owned(),
        )));
    }
    let redacted_note = redact_outbound(note);
    if redacted_note.len() > MAX_ASSESSMENT_CHARS {
        return Err(SubmitError::Value(
            "assessment note exceeds size cap after redaction".to_owned(),
        ));
    }
    let result = AssessmentResult {
        kind: single,
        state: state.to_owned(),
        assessment: redacted_note,
        head_sha: evidence.head_sha,
        base_ref: evidence.base_ref,
        diff_fingerprint: evidence.diff_fingerprint,
        knowledge_sha256: evidence.knowledge_sha256,
    };
    persist_result(&result, &root, &tmpdir, git)?;
    Ok(result)
}

/// Errors from [`submit`].
#[derive(Debug)]
pub enum SubmitError {
    /// Usage or validation failure.
    Value(String),
    /// HEAD drift between materialize and submit.
    HeadDrift(HeadDrift),
    /// Note must be reauthored.
    Reauthor(ReauthorRequired),
    /// Deviation log append pending.
    LogPending(DeviationLogPending),
    /// I/O or unexpected failure.
    Io(String),
}

impl std::fmt::Display for SubmitError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Value(text) | Self::Io(text) => formatter.write_str(text),
            Self::HeadDrift(error) => formatter.write_str(&error.0),
            Self::Reauthor(error) => formatter.write_str(&error.0),
            Self::LogPending(error) => formatter.write_str(&error.0),
        }
    }
}

impl std::error::Error for SubmitError {}

fn prepare_pending(
    normalized: &[AssessmentKind],
    repo_root: &Path,
    implement_tmpdir: &Path,
    git: &dyn AssessmentGit,
) -> Result<(BTreeMap<String, String>, Vec<MaterializedEvidence>), String> {
    for _ in 0..3 {
        let head_sha = git.git_read(repo_root, &["rev-parse", "HEAD"])?;
        match prepare_kinds(normalized, repo_root, implement_tmpdir, &head_sha, git) {
            Ok((kind_statuses, kind_pending)) => {
                return Ok((kind_statuses, kind_pending));
            }
            Err(PrepareErr::HeadDrift) => {}
            Err(PrepareErr::Other(message)) => return Err(message),
        }
    }
    Err("HEAD changed repeatedly during architectural assessment setup".to_owned())
}

enum PrepareErr {
    HeadDrift,
    Other(String),
}

fn prepare_kinds(
    normalized: &[AssessmentKind],
    repo_root: &Path,
    implement_tmpdir: &Path,
    head_sha: &str,
    git: &dyn AssessmentGit,
) -> Result<(BTreeMap<String, String>, Vec<MaterializedEvidence>), PrepareErr> {
    let mut statuses = BTreeMap::new();
    let mut pending = Vec::new();
    for &kind in normalized {
        match prepare_kind(kind, repo_root, implement_tmpdir, head_sha, git) {
            Ok((Some(status), None)) => {
                statuses.insert(kind.key().to_owned(), status);
            }
            Ok((None, Some(evidence))) => pending.push(evidence),
            Ok((None, None)) => {}
            Ok((Some(_), Some(_))) => unreachable!("status and evidence are mutually exclusive"),
            Err(PrepareErr::HeadDrift) => return Err(PrepareErr::HeadDrift),
            Err(PrepareErr::Other(message)) => return Err(PrepareErr::Other(message)),
        }
    }
    Ok((statuses, pending))
}

fn prepare_kind(
    kind: AssessmentKind,
    repo_root: &Path,
    implement_tmpdir: &Path,
    head_sha: &str,
    git: &dyn AssessmentGit,
) -> Result<(Option<String>, Option<MaterializedEvidence>), PrepareErr> {
    if already_handled(kind, repo_root, implement_tmpdir, head_sha, git)
        .map_err(PrepareErr::Other)?
    {
        return Ok((Some("handled".to_owned()), None));
    }
    let evidence = match materialize_current(kind, repo_root, implement_tmpdir, head_sha, git) {
        Ok(Some(evidence)) => evidence,
        Ok(None) => {
            let repair = repair_current_outcome(kind, repo_root, implement_tmpdir, head_sha, git)?;
            if repair == "handled" || repair == "log-pending" {
                return Ok((Some(repair), None));
            }
            validate_materialization(kind, repo_root, implement_tmpdir, git)
                .map_err(PrepareErr::Other)?
        }
        Err(PrepareErr::HeadDrift) => return Err(PrepareErr::HeadDrift),
        Err(PrepareErr::Other(message)) => return Err(PrepareErr::Other(message)),
    };
    if deterministic_out_of_scope(&evidence.diff_text) {
        persist_clean(&evidence, repo_root, implement_tmpdir, git)?;
        return Ok((Some("deterministic-clean".to_owned()), None));
    }
    Ok((None, Some(evidence)))
}

fn materialize_current(
    kind: AssessmentKind,
    repo_root: &Path,
    implement_tmpdir: &Path,
    head_sha: &str,
    git: &dyn AssessmentGit,
) -> Result<Option<MaterializedEvidence>, PrepareErr> {
    let result = prepare_compose_assessment(kind, implement_tmpdir, repo_root, head_sha, git)
        .map_err(|error| match error.as_str() {
            msg if msg.contains("HEAD changed") => PrepareErr::HeadDrift,
            other => PrepareErr::Other(other.to_owned()),
        })?;
    match result.status.as_str() {
        "current" => Ok(None),
        "assessment-required" => validate_materialization(kind, repo_root, implement_tmpdir, git)
            .map(Some)
            .map_err(PrepareErr::Other),
        _ => Err(PrepareErr::Other(if result.warning.is_empty() {
            format!("{} materialization was not produced", kind.key())
        } else {
            result.warning
        })),
    }
}

struct ComposeResult {
    status: String,
    warning: String,
}

fn prepare_compose_assessment(
    kind: AssessmentKind,
    implement_tmpdir: &Path,
    repo_root: &Path,
    expected_head_sha: &str,
    git: &dyn AssessmentGit,
) -> Result<ComposeResult, String> {
    fs::create_dir_all(implement_tmpdir).map_err(|error| error.to_string())?;
    clear_staged_and_dropped(implement_tmpdir, kind);
    let current_head = git.git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])?;
    if !expected_head_sha.is_empty() && expected_head_sha != current_head {
        return Err(format!(
            "HEAD changed before architectural-{} compose materialization",
            kind.key()
        ));
    }
    let metadata = read_env_lenient(&durable_note_env_path(implement_tmpdir, kind));
    let base_ref = metadata.get("BASE_REF").cloned().unwrap_or_default();
    if !current_head.is_empty()
        && note_consumable(
            implement_tmpdir,
            &current_head,
            kind,
            &base_ref,
            Some(repo_root),
            Some(git as &dyn AssessmentGit),
        )
        && !base_ref.is_empty()
        && !note_fingerprint_stale(implement_tmpdir, &base_ref, kind, repo_root, git)
    {
        return Ok(ComposeResult {
            status: "current".to_owned(),
            warning: String::new(),
        });
    }
    let knowledge_path = repo_root.join(kind.knowledge_filename());
    let (status, content, warning) = read_knowledge(kind, repo_root, &knowledge_path)?;
    if status == "absent" || status == "invalid" {
        return Ok(ComposeResult {
            status: status.to_owned(),
            warning,
        });
    }
    if kind == AssessmentKind::Invariants && content.trim().is_empty() {
        return Ok(ComposeResult {
            status: "present-empty".to_owned(),
            warning: String::new(),
        });
    }
    let base_remote = "origin";
    let base_name = "main";
    let base_label = format!("{base_remote}/{base_name}");
    let diff_text =
        git.implementation_diff_for_head(repo_root, &current_head, base_remote, base_name)?;
    if git.git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])? != current_head {
        return Err(format!(
            "HEAD changed before architectural-{} compose materialization",
            kind.key()
        ));
    }
    let fingerprint = diff_fingerprint(&diff_text);
    let diff_path = implement_tmpdir.join(kind.materialized_diff_filename());
    write_text_atomic(&diff_path, &diff_text)?;
    write_compose_materialization_metadata(
        implement_tmpdir,
        kind,
        &current_head,
        &base_label,
        &fingerprint,
        &diff_path,
        status,
        &knowledge_path,
    )?;
    Ok(ComposeResult {
        status: "assessment-required".to_owned(),
        warning: String::new(),
    })
}

fn read_knowledge(
    kind: AssessmentKind,
    repo_root: &Path,
    path: &Path,
) -> Result<(&'static str, String, String), String> {
    match path.symlink_metadata() {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(("absent", String::new(), String::new()));
        }
        Err(error) => return Err(error.to_string()),
        Ok(meta) if meta.file_type().is_symlink() => {
            return Ok((
                "invalid",
                String::new(),
                format!(
                    "{} is invalid: symlinks are not read",
                    kind.knowledge_filename()
                ),
            ));
        }
        Ok(meta) if meta.is_dir() => {
            return Ok((
                "invalid",
                String::new(),
                format!(
                    "{} is invalid: expected a regular file, found a directory",
                    kind.knowledge_filename()
                ),
            ));
        }
        Ok(meta) if !meta.is_file() => {
            return Ok((
                "invalid",
                String::new(),
                format!(
                    "{} is invalid: expected a regular file",
                    kind.knowledge_filename()
                ),
            ));
        }
        Ok(_) => {}
    }
    if !under(path, repo_root) {
        return Ok((
            "invalid",
            String::new(),
            format!(
                "{} is invalid: path escapes repo root",
                kind.knowledge_filename()
            ),
        ));
    }
    match fs::read_to_string(path) {
        Ok(text) => Ok(("present", text, String::new())),
        Err(error) => Ok((
            "invalid",
            String::new(),
            format!(
                "{} is invalid: unreadable file ({error})",
                kind.knowledge_filename()
            ),
        )),
    }
}

#[allow(clippy::too_many_arguments)]
fn write_compose_materialization_metadata(
    implement_tmpdir: &Path,
    kind: AssessmentKind,
    head_sha: &str,
    base_ref: &str,
    fingerprint: &str,
    diff_path: &Path,
    knowledge_status: &str,
    knowledge_path: &Path,
) -> Result<(), String> {
    let written_at = Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let text = format!(
        "STATUS=present\n\
         HEAD_SHA={}\n\
         ASSESSED_HEAD_SHA={}\n\
         BASE_REF={}\n\
         NOTE_STATE={NOTE_STATE_AUTHORED}\n\
         DIFF_FINGERPRINT={}\n\
         AUTHORED_DIFF_FINGERPRINT={}\n\
         COVERED_DIFF_FINGERPRINT={}\n\
         DIFF_SNAPSHOT={}\n\
         {}={}\n\
         {}={}\n\
         ASSESSMENT_KIND=\n\
         WRITTEN_AT={written_at}\n",
        env_escape(head_sha),
        env_escape(head_sha),
        env_escape(base_ref),
        env_escape(fingerprint),
        env_escape(fingerprint),
        env_escape(fingerprint),
        env_escape(&diff_path.display().to_string()),
        kind.status_env_key(),
        env_escape(knowledge_status),
        kind.path_env_key(),
        env_escape(&knowledge_path.display().to_string()),
    );
    write_text_atomic(
        &implement_tmpdir.join(kind.materialize_env_filename()),
        &text,
    )
}

fn already_handled(
    kind: AssessmentKind,
    repo_root: &Path,
    implement_tmpdir: &Path,
    head_sha: &str,
    git: &dyn AssessmentGit,
) -> Result<bool, String> {
    let metadata = read_env_lenient(&durable_note_env_path(implement_tmpdir, kind));
    let base_ref = metadata.get("BASE_REF").cloned().unwrap_or_default();
    let note_state = metadata
        .get("NOTE_STATE")
        .cloned()
        .unwrap_or_else(|| NOTE_STATE_AUTHORED.to_owned());
    let allowed = if kind.is_invariant() {
        [ASSESSMENT_OUTCOME_CLEAN, "violation"]
    } else {
        [ASSESSMENT_OUTCOME_CLEAN, "deviation"]
    };
    if note_state == NOTE_STATE_AUTHORED {
        let outcome = metadata.get("ASSESSMENT_KIND").map_or("", String::as_str);
        if !allowed.contains(&outcome) || !authored_note_valid(kind, implement_tmpdir, outcome) {
            return Ok(false);
        }
    }
    if base_ref.is_empty()
        || !note_consumable(
            implement_tmpdir,
            head_sha,
            kind,
            &base_ref,
            Some(repo_root),
            Some(git as &dyn AssessmentGit),
        )
        || !outcome_valid(kind, implement_tmpdir, &metadata)
    {
        return Ok(false);
    }
    if metadata.get("NOTE_STATE").map(String::as_str) == Some(NOTE_STATE_UNAVAILABLE) {
        return Ok(false);
    }
    if kind == AssessmentKind::Guidelines
        && metadata.get("ASSESSMENT_KIND").map(String::as_str) == Some("deviation")
    {
        let note = read_regular(&durable_note_path(implement_tmpdir, kind), implement_tmpdir)?;
        let status = append_deviation_note(implement_tmpdir, &note);
        return Ok(status == "ok" || status == "duplicate");
    }
    Ok(true)
}

fn authored_note_valid(kind: AssessmentKind, implement_tmpdir: &Path, outcome: &str) -> bool {
    let Ok(note) = read_regular(&durable_note_path(implement_tmpdir, kind), implement_tmpdir)
    else {
        return false;
    };
    authored_outcome_valid(&note, outcome, kind.is_invariant())
}

/// Whether authored outcome metadata is consistent with its note.
#[must_use]
pub fn authored_outcome_valid(note: &str, outcome: &str, invariant: bool) -> bool {
    validate_authored_outcome(
        note,
        outcome,
        if invariant {
            AssessmentKind::Invariants
        } else {
            AssessmentKind::Guidelines
        },
    )
    .is_ok()
}

fn validate_authored_outcome(
    note: &str,
    outcome: &str,
    kind: AssessmentKind,
) -> Result<String, ReauthorRequired> {
    let allowed = if kind.is_invariant() {
        [ASSESSMENT_OUTCOME_CLEAN, "violation"]
    } else {
        [ASSESSMENT_OUTCOME_CLEAN, "deviation"]
    };
    if !allowed.contains(&outcome) {
        return Err(ReauthorRequired(
            ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME.to_owned(),
        ));
    }
    let classified = classify_assessment_prose(
        note,
        kind.clean_presentation_note(),
        if kind.is_invariant() {
            &INVARIANT_ID_RE
        } else {
            &GUIDELINE_ID_RE
        },
        kind.non_clean_authored_outcome(),
    );
    if outcome == ASSESSMENT_OUTCOME_CLEAN && classified != ASSESSMENT_OUTCOME_CLEAN {
        return Err(ReauthorRequired(
            ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH.to_owned(),
        ));
    }
    Ok(outcome.to_owned())
}

fn classify_assessment_prose(
    note: &str,
    clean_lead: &str,
    identifier_pattern: &Regex,
    non_clean_outcome: &str,
) -> String {
    if note.trim().is_empty() {
        return String::new();
    }
    let first_line = note.split_once('\n').map_or(note, |(line, _)| line).trim();
    if first_line == clean_lead || CLEAN_ASSESSMENT_LEAD_RE.is_match(first_line) {
        return ASSESSMENT_OUTCOME_CLEAN.to_owned();
    }
    if identifier_pattern.is_match(note) {
        non_clean_outcome.to_owned()
    } else {
        ASSESSMENT_OUTCOME_CLEAN.to_owned()
    }
}

fn outcome_valid(
    kind: AssessmentKind,
    implement_tmpdir: &Path,
    metadata: &BTreeMap<String, String>,
) -> bool {
    let path = ship_outcome_path(implement_tmpdir, kind);
    let Ok(text) = read_regular(&path, implement_tmpdir) else {
        return false;
    };
    let Ok(data) = serde_json::from_str::<Value>(&text) else {
        return false;
    };
    if validate_ship_outcome_record(&data, kind).is_some() {
        return false;
    }
    let Some(record) = data.as_object() else {
        return false;
    };
    let base = record
        .get("base_ref")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let head = record
        .get("head_sha")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let expected_head = metadata
        .get("ASSESSED_HEAD_SHA")
        .filter(|value| !value.is_empty())
        .or_else(|| metadata.get("HEAD_SHA"))
        .map(String::as_str)
        .unwrap_or_default();
    base == metadata
        .get("BASE_REF")
        .map(String::as_str)
        .unwrap_or_default()
        && head == expected_head
}

/// Whether a durable note is consumable for the covered HEAD.
#[must_use]
pub fn note_consumable(
    implement_tmpdir: &Path,
    head_sha: &str,
    kind: AssessmentKind,
    base_ref: &str,
    repo_root: Option<&Path>,
    git: Option<&dyn AssessmentGit>,
) -> bool {
    let note_path = durable_note_path(implement_tmpdir, kind);
    let meta_path = durable_note_env_path(implement_tmpdir, kind);
    let snapshot_path = implement_tmpdir.join(kind.materialized_diff_filename());
    if !regular_file(&note_path) || !regular_file(&meta_path) {
        return false;
    }
    let metadata = read_env_lenient(&meta_path);
    let Some((note_state, _authored, mut covered, stored_base)) =
        validated_note_metadata(&metadata, &snapshot_path)
    else {
        return false;
    };
    let resolved_base = if base_ref.is_empty() {
        stored_base.clone()
    } else {
        base_ref.to_owned()
    };
    if resolved_base.is_empty() || (!base_ref.is_empty() && resolved_base != stored_base) {
        return false;
    }
    if note_state == NOTE_STATE_UNAVAILABLE {
        return metadata.get("HEAD_SHA").map(String::as_str) == Some(head_sha);
    }
    let Some(repo_root) = repo_root else {
        return metadata.get("HEAD_SHA").map(String::as_str) == Some(head_sha);
    };
    let Some(git) = git else {
        return metadata.get("HEAD_SHA").map(String::as_str) == Some(head_sha);
    };
    let mut metadata = metadata;
    if metadata.get("HEAD_SHA").map(String::as_str) != Some(head_sha) {
        if !advance_note_coverage(
            implement_tmpdir,
            &metadata,
            head_sha,
            &resolved_base,
            repo_root,
            kind,
            git,
        ) {
            return false;
        }
        metadata = read_env_lenient(&meta_path);
        let Some(validated) = validated_note_metadata(&metadata, &snapshot_path) else {
            return false;
        };
        covered = validated.2;
    }
    if git
        .git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])
        .ok()
        .as_deref()
        != Some(head_sha)
    {
        return false;
    }
    live_fingerprint(repo_root, &resolved_base, git).is_some_and(|live| live == covered)
}

fn note_fingerprint_stale(
    implement_tmpdir: &Path,
    base_ref: &str,
    kind: AssessmentKind,
    repo_root: &Path,
    git: &dyn AssessmentGit,
) -> bool {
    let metadata = read_env_lenient(&durable_note_env_path(implement_tmpdir, kind));
    let Some(identity) = note_identity(&metadata) else {
        return true;
    };
    if identity.0 == NOTE_STATE_UNAVAILABLE {
        return false;
    }
    live_fingerprint(repo_root, base_ref, git).is_none_or(|live| live != identity.2)
}

fn note_identity(metadata: &BTreeMap<String, String>) -> Option<(String, String, String)> {
    let legacy = metadata
        .get("DIFF_FINGERPRINT")
        .map_or("", String::as_str)
        .trim()
        .to_owned();
    let new_format = [
        "NOTE_STATE",
        "AUTHORED_DIFF_FINGERPRINT",
        "COVERED_DIFF_FINGERPRINT",
    ]
    .iter()
    .any(|key| metadata.contains_key(*key));
    let note_state = {
        let raw = metadata.get("NOTE_STATE").map_or("", String::as_str).trim();
        if raw.is_empty() {
            if new_format {
                String::new()
            } else {
                NOTE_STATE_AUTHORED.to_owned()
            }
        } else {
            raw.to_owned()
        }
    };
    if !NOTE_STATE_TOKENS.contains(&note_state.as_str()) {
        return None;
    }
    let (authored, covered) = if new_format {
        (
            metadata
                .get("AUTHORED_DIFF_FINGERPRINT")
                .map_or("", String::as_str)
                .trim()
                .to_owned(),
            metadata
                .get("COVERED_DIFF_FINGERPRINT")
                .map_or("", String::as_str)
                .trim()
                .to_owned(),
        )
    } else {
        (legacy.clone(), legacy)
    };
    if note_state == NOTE_STATE_UNAVAILABLE {
        return Some((note_state, authored, covered));
    }
    if authored.is_empty() || covered.is_empty() {
        return None;
    }
    Some((note_state, authored, covered))
}

fn validated_note_metadata(
    metadata: &BTreeMap<String, String>,
    expected_snapshot: &Path,
) -> Option<(String, String, String, String)> {
    if metadata.get("STATUS").map(String::as_str) != Some("present") {
        return None;
    }
    let (note_state, authored, covered) = note_identity(metadata)?;
    let base_ref = metadata
        .get("BASE_REF")
        .map_or("", String::as_str)
        .trim()
        .to_owned();
    if note_state == NOTE_STATE_UNAVAILABLE {
        return Some((note_state, authored, covered, base_ref));
    }
    let prior_format = metadata.get("NOTE_STATE").is_none_or(String::is_empty)
        && metadata
            .get("AUTHORED_DIFF_FINGERPRINT")
            .is_none_or(String::is_empty)
        && metadata
            .get("COVERED_DIFF_FINGERPRINT")
            .is_none_or(String::is_empty);
    if prior_format {
        return Some((note_state, authored, covered, base_ref));
    }
    let declared = metadata.get("DIFF_SNAPSHOT")?;
    if declared.is_empty() {
        return None;
    }
    if !same_resolved_path(Path::new(declared), expected_snapshot) {
        return None;
    }
    if !snapshot_matches(expected_snapshot, &covered) {
        return None;
    }
    Some((note_state, authored, covered, base_ref))
}

fn snapshot_matches(snapshot_path: &Path, covered_fingerprint: &str) -> bool {
    if covered_fingerprint.is_empty() || !regular_file(snapshot_path) {
        return false;
    }
    let Ok(text) = fs::read_to_string(snapshot_path) else {
        return false;
    };
    diff_fingerprint(&text) == covered_fingerprint
}

fn advance_note_coverage(
    implement_tmpdir: &Path,
    metadata: &BTreeMap<String, String>,
    head_sha: &str,
    base_ref: &str,
    repo_root: &Path,
    kind: AssessmentKind,
    git: &dyn AssessmentGit,
) -> bool {
    let stored_head = metadata
        .get("HEAD_SHA")
        .map_or("", String::as_str)
        .trim()
        .to_owned();
    let Some((note_state, authored, covered)) = note_identity(metadata) else {
        return false;
    };
    if note_state == NOTE_STATE_UNAVAILABLE {
        return false;
    }
    let snapshot_path = implement_tmpdir.join(kind.materialized_diff_filename());
    if git
        .git_read(
            repo_root,
            &[
                "rev-parse",
                "--verify",
                &format!("{stored_head}^{{commit}}"),
            ],
        )
        .is_err()
    {
        return false;
    }
    let (remote, ref_name) = base_ref.split_once('/').unwrap_or(("origin", base_ref));
    let Ok(stored_diff) =
        git.implementation_diff_for_head(repo_root, &stored_head, remote, ref_name)
    else {
        return false;
    };
    if diff_fingerprint(&stored_diff) != covered || !snapshot_matches(&snapshot_path, &covered) {
        return false;
    }
    let Ok(paths) = git.incremental_paths(repo_root, &stored_head, head_sha) else {
        return false;
    };
    if paths.is_empty() || !paths.iter().all(|path| path_out_of_scope(path)) {
        return false;
    }
    if git
        .git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])
        .ok()
        .as_deref()
        != Some(head_sha)
    {
        return false;
    }
    let Some((diff_text, covered_fingerprint)) = live_diff(repo_root, base_ref, git) else {
        return false;
    };
    if git
        .git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])
        .ok()
        .as_deref()
        != Some(head_sha)
    {
        return false;
    }
    let mut refreshed = metadata.clone();
    refreshed.insert("NOTE_STATE".to_owned(), note_state);
    refreshed.insert("AUTHORED_DIFF_FINGERPRINT".to_owned(), authored);
    refreshed.insert(
        "COVERED_DIFF_FINGERPRINT".to_owned(),
        covered_fingerprint.clone(),
    );
    refreshed.insert("DIFF_FINGERPRINT".to_owned(), covered_fingerprint);
    refreshed.insert(
        "DIFF_SNAPSHOT".to_owned(),
        snapshot_path.display().to_string(),
    );
    let meta_path = durable_note_env_path(implement_tmpdir, kind);
    if write_text_atomic(&snapshot_path, &diff_text).is_err() {
        return false;
    }
    let meta_text = durable_metadata_text(head_sha, &refreshed, base_ref, kind.status_env_key());
    write_text_atomic(&meta_path, &meta_text).is_ok()
}

fn path_out_of_scope(path: &str) -> bool {
    if path.is_empty() || path.starts_with('/') || path.contains('\\') || path.contains("//") {
        return false;
    }
    if !is_safe_rel_path(path) {
        return false;
    }
    let candidate = Path::new(path);
    let parts: Vec<_> = candidate.components().collect();
    if parts.len() < 2 {
        return false;
    }
    match parts[0] {
        Component::Normal(first) if first == "larch-logs" => true,
        Component::Normal(first)
            if first == "docs" && candidate.extension().is_some_and(|ext| ext == "md") =>
        {
            true
        }
        _ => false,
    }
}

fn live_diff(
    repo_root: &Path,
    resolved_base: &str,
    git: &dyn AssessmentGit,
) -> Option<(String, String)> {
    let (remote, ref_name) = resolved_base
        .split_once('/')
        .unwrap_or(("origin", resolved_base));
    let head = git
        .git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])
        .ok()?;
    let diff = git
        .implementation_diff_for_head(repo_root, &head, remote, ref_name)
        .ok()?;
    let fingerprint = diff_fingerprint(&diff);
    Some((diff, fingerprint))
}

fn live_fingerprint(
    repo_root: &Path,
    resolved_base: &str,
    git: &dyn AssessmentGit,
) -> Option<String> {
    live_diff(repo_root, resolved_base, git).map(|(_, fingerprint)| fingerprint)
}

fn repair_current_outcome(
    kind: AssessmentKind,
    repo_root: &Path,
    implement_tmpdir: &Path,
    head_sha: &str,
    git: &dyn AssessmentGit,
) -> Result<String, PrepareErr> {
    if git
        .git_read(repo_root, &["rev-parse", "HEAD"])
        .map_err(PrepareErr::Other)?
        != head_sha
    {
        return Err(PrepareErr::HeadDrift);
    }
    let metadata = read_env_lenient(&durable_note_env_path(implement_tmpdir, kind));
    let state = metadata.get("ASSESSMENT_KIND").cloned().unwrap_or_default();
    let allowed = [ASSESSMENT_OUTCOME_CLEAN, kind.non_clean_authored_outcome()];
    if !allowed.contains(&state.as_str()) {
        let _ = invalidate_implement_note(implement_tmpdir, kind);
        return Ok(reauthor_status(ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME));
    }
    let Ok(note) = read_regular(&durable_note_path(implement_tmpdir, kind), implement_tmpdir)
    else {
        let _ = invalidate_implement_note(implement_tmpdir, kind);
        return Ok(reauthor_status(ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA));
    };
    if !authored_outcome_valid(&note, &state, kind.is_invariant()) {
        let _ = invalidate_implement_note(implement_tmpdir, kind);
        return Ok(reauthor_status(if state == ASSESSMENT_OUTCOME_CLEAN {
            ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH
        } else {
            ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME
        }));
    }
    if !outcome_valid(kind, implement_tmpdir, &metadata) {
        let result = AssessmentResult {
            kind,
            state: state.clone(),
            assessment: note.clone(),
            head_sha: head_sha.to_owned(),
            base_ref: metadata.get("BASE_REF").cloned().unwrap_or_default(),
            diff_fingerprint: String::new(),
            knowledge_sha256: String::new(),
        };
        write_outcome(kind, implement_tmpdir, &result, NOTE_STATE_AUTHORED, "")
            .map_err(PrepareErr::Other)?;
        if !outcome_valid(kind, implement_tmpdir, &metadata) {
            return Err(PrepareErr::Other(
                "architectural outcome repair postcondition failed".to_owned(),
            ));
        }
    }
    if kind == AssessmentKind::Guidelines && state == "deviation" {
        let status = append_deviation_note(implement_tmpdir, &note);
        return Ok(if status == "ok" || status == "duplicate" {
            "handled".to_owned()
        } else {
            "log-pending".to_owned()
        });
    }
    Ok("handled".to_owned())
}

fn persist_clean(
    evidence: &MaterializedEvidence,
    repo_root: &Path,
    implement_tmpdir: &Path,
    git: &dyn AssessmentGit,
) -> Result<(), PrepareErr> {
    if git
        .git_read(repo_root, &["rev-parse", "HEAD"])
        .map_err(PrepareErr::Other)?
        != evidence.head_sha
    {
        return Err(PrepareErr::HeadDrift);
    }
    write_deterministic_clean_note(
        implement_tmpdir,
        &evidence.head_sha,
        &evidence.base_ref,
        &evidence.diff_text,
        evidence.kind,
    )
    .map_err(PrepareErr::Other)?;
    let result = AssessmentResult {
        kind: evidence.kind,
        state: ASSESSMENT_OUTCOME_CLEAN.to_owned(),
        assessment: evidence.kind.clean_presentation_note().to_owned(),
        head_sha: evidence.head_sha.clone(),
        base_ref: evidence.base_ref.clone(),
        diff_fingerprint: evidence.diff_fingerprint.clone(),
        knowledge_sha256: evidence.knowledge_sha256.clone(),
    };
    write_outcome(
        evidence.kind,
        implement_tmpdir,
        &result,
        NOTE_STATE_DETERMINISTIC_CLEAN,
        "",
    )
    .map_err(PrepareErr::Other)
}

/// Persist a deterministic clean note backed by validated diff evidence.
///
/// # Errors
/// Returns when artifact writes fail.
pub fn write_deterministic_clean_note(
    implement_tmpdir: &Path,
    head_sha: &str,
    base_ref: &str,
    diff_text: &str,
    kind: AssessmentKind,
) -> Result<(), String> {
    let fingerprint = diff_fingerprint(diff_text);
    let diff_path = implement_tmpdir.join(kind.materialized_diff_filename());
    write_text_atomic(&diff_path, diff_text)?;
    let mut metadata = BTreeMap::new();
    metadata.insert(
        "NOTE_STATE".to_owned(),
        NOTE_STATE_DETERMINISTIC_CLEAN.to_owned(),
    );
    metadata.insert("ASSESSED_HEAD_SHA".to_owned(), head_sha.to_owned());
    metadata.insert("DIFF_FINGERPRINT".to_owned(), fingerprint.clone());
    metadata.insert("AUTHORED_DIFF_FINGERPRINT".to_owned(), fingerprint.clone());
    metadata.insert("COVERED_DIFF_FINGERPRINT".to_owned(), fingerprint);
    metadata.insert("DIFF_SNAPSHOT".to_owned(), diff_path.display().to_string());
    metadata.insert(
        "ASSESSMENT_KIND".to_owned(),
        ASSESSMENT_OUTCOME_CLEAN.to_owned(),
    );
    write_implement_note(
        implement_tmpdir,
        kind.clean_presentation_note(),
        head_sha,
        &metadata,
        base_ref,
        kind,
    )
}

fn persist_result(
    result: &AssessmentResult,
    repo_root: &Path,
    implement_tmpdir: &Path,
    git: &dyn AssessmentGit,
) -> Result<(), SubmitError> {
    let current_head = git
        .git_read(repo_root, &["rev-parse", "HEAD"])
        .map_err(SubmitError::Value)?;
    if current_head != result.head_sha {
        return Err(SubmitError::HeadDrift(HeadDrift(
            "HEAD changed after architectural assessment launch".to_owned(),
        )));
    }
    write_compose_assessment(
        implement_tmpdir,
        &result.assessment,
        &result.state,
        result.kind,
        repo_root,
        git,
    )
    .map_err(|error| match error {
        ComposeWriteError::Reauthor(reason) => SubmitError::Reauthor(ReauthorRequired(reason)),
        ComposeWriteError::Other(message) => SubmitError::Value(message),
    })?;
    write_outcome(
        result.kind,
        implement_tmpdir,
        result,
        NOTE_STATE_AUTHORED,
        "",
    )
    .map_err(SubmitError::Io)?;
    let metadata = read_env_lenient(&durable_note_env_path(implement_tmpdir, result.kind));
    if !outcome_valid(result.kind, implement_tmpdir, &metadata) {
        return Err(SubmitError::Reauthor(ReauthorRequired(
            ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA.to_owned(),
        )));
    }
    if result.kind == AssessmentKind::Guidelines && result.state == "deviation" {
        let status = append_deviation_note(implement_tmpdir, &result.assessment);
        if status != "ok" && status != "duplicate" {
            return Err(SubmitError::LogPending(DeviationLogPending(
                "guideline deviation log append failed".to_owned(),
            )));
        }
    }
    Ok(())
}

enum ComposeWriteError {
    Reauthor(String),
    Other(String),
}

fn write_compose_assessment(
    implement_tmpdir: &Path,
    assessment_text: &str,
    outcome: &str,
    kind: AssessmentKind,
    repo_root: &Path,
    git: &dyn AssessmentGit,
) -> Result<(), ComposeWriteError> {
    let mut normalized = assessment_text.trim_end_matches('\n').to_owned();
    normalized.push('\n');
    if normalized.trim().is_empty() {
        return Err(ComposeWriteError::Other(
            "assessment-file: content must not be empty".to_owned(),
        ));
    }
    let validated = validate_authored_outcome(&normalized, outcome, kind)
        .map_err(|error| ComposeWriteError::Reauthor(error.0))?;
    let metadata = read_env_lenient(&implement_tmpdir.join(kind.materialize_env_filename()));
    let materialized_head = metadata.get("HEAD_SHA").cloned().unwrap_or_default();
    if materialized_head.is_empty() {
        return Err(ComposeWriteError::Other(
            "compose materialization metadata is missing HEAD_SHA".to_owned(),
        ));
    }
    let current_head = git
        .git_read(repo_root, &["rev-parse", "--verify", "HEAD^{commit}"])
        .map_err(ComposeWriteError::Other)?;
    if current_head != materialized_head {
        return Err(ComposeWriteError::Other(
            "HEAD changed after compose materialization; rerun Step 8".to_owned(),
        ));
    }
    if metadata.get("STATUS").map(String::as_str) != Some("present") {
        return Err(ComposeWriteError::Other(
            "compose materialization metadata is not present".to_owned(),
        ));
    }
    let mut metadata = metadata;
    metadata.insert("ASSESSMENT_KIND".to_owned(), validated);
    write_implement_note(
        implement_tmpdir,
        &normalized,
        &materialized_head,
        &metadata,
        metadata.get("BASE_REF").map_or("", String::as_str),
        kind,
    )
    .map_err(ComposeWriteError::Other)
}

fn write_implement_note(
    implement_tmpdir: &Path,
    note_text: &str,
    head_sha: &str,
    metadata: &BTreeMap<String, String>,
    base_ref: &str,
    kind: AssessmentKind,
) -> Result<(), String> {
    write_text_atomic(&durable_note_path(implement_tmpdir, kind), note_text)?;
    write_text_atomic(
        &durable_note_env_path(implement_tmpdir, kind),
        &durable_metadata_text(head_sha, metadata, base_ref, kind.status_env_key()),
    )?;
    clear_staged_and_dropped(implement_tmpdir, kind);
    Ok(())
}

fn durable_metadata_text(
    head_sha: &str,
    metadata: &BTreeMap<String, String>,
    base_ref: &str,
    status_key: &str,
) -> String {
    let new_format = [
        "NOTE_STATE",
        "AUTHORED_DIFF_FINGERPRINT",
        "COVERED_DIFF_FINGERPRINT",
    ]
    .iter()
    .any(|key| metadata.get(*key).is_some_and(|value| !value.is_empty()));
    let identity = note_identity(metadata);
    let note_state = identity.as_ref().map_or_else(
        || {
            metadata
                .get("NOTE_STATE")
                .cloned()
                .unwrap_or_else(|| NOTE_STATE_AUTHORED.to_owned())
        },
        |identity| identity.0.clone(),
    );
    let authored = identity.as_ref().map_or_else(
        || {
            metadata
                .get("AUTHORED_DIFF_FINGERPRINT")
                .cloned()
                .unwrap_or_default()
        },
        |identity| identity.1.clone(),
    );
    let covered = identity.as_ref().map_or_else(
        || {
            metadata
                .get("COVERED_DIFF_FINGERPRINT")
                .cloned()
                .unwrap_or_default()
        },
        |identity| identity.2.clone(),
    );
    let compatibility = if covered.is_empty() {
        metadata
            .get("DIFF_FINGERPRINT")
            .cloned()
            .unwrap_or_default()
    } else {
        covered.clone()
    };
    let written_at = Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let mut lines = vec!["STATUS=present".to_owned()];
    if new_format {
        lines.push(format!("NOTE_STATE={}", env_escape(&note_state)));
        lines.push(format!(
            "AUTHORED_DIFF_FINGERPRINT={}",
            env_escape(&authored)
        ));
        lines.push(format!("COVERED_DIFF_FINGERPRINT={}", env_escape(&covered)));
    }
    lines.extend([
        format!("HEAD_SHA={}", env_escape(head_sha)),
        format!(
            "ASSESSED_HEAD_SHA={}",
            env_escape(metadata.get("ASSESSED_HEAD_SHA").map_or("", String::as_str))
        ),
        format!("DIFF_FINGERPRINT={}", env_escape(&compatibility)),
        format!(
            "BASE_REF={}",
            env_escape(if base_ref.is_empty() {
                metadata.get("BASE_REF").map_or("", String::as_str)
            } else {
                base_ref
            })
        ),
        format!(
            "DIFF_SNAPSHOT={}",
            env_escape(metadata.get("DIFF_SNAPSHOT").map_or("", String::as_str))
        ),
        format!(
            "{status_key}={}",
            env_escape(metadata.get(status_key).map_or("present", String::as_str))
        ),
        format!(
            "ASSESSMENT_KIND={}",
            env_escape(metadata.get("ASSESSMENT_KIND").map_or("", String::as_str))
        ),
        format!("WRITTEN_AT={written_at}"),
        String::new(),
    ]);
    lines.join("\n")
}

fn write_outcome(
    kind: AssessmentKind,
    implement_tmpdir: &Path,
    result: &AssessmentResult,
    note_state: &str,
    detail: &str,
) -> Result<(), String> {
    if result.head_sha.trim().is_empty() {
        return Err(format!(
            "architectural-{} outcome head_sha is empty",
            kind.key()
        ));
    }
    let (outcome, reason, assessment_kind) = classify_ship_outcome(kind, &result.state, note_state);
    let status_field = kind.status_field();
    let mut record = Map::new();
    record.insert("schema_version".to_owned(), json!("1"));
    record.insert("phase".to_owned(), json!("implement"));
    record.insert("step".to_owned(), json!("8"));
    record.insert("outcome".to_owned(), json!(outcome));
    record.insert("reason".to_owned(), json!(reason));
    record.insert("detail".to_owned(), json!(bounded_detail(detail)));
    record.insert(status_field.to_owned(), json!("present"));
    record.insert(
        "head_sha".to_owned(),
        json!(bounded_detail(&result.head_sha)),
    );
    record.insert(
        "base_ref".to_owned(),
        json!(bounded_detail(&result.base_ref)),
    );
    record.insert("assessment_kind".to_owned(), json!(assessment_kind));
    record.insert("operator_waived".to_owned(), json!(false));
    let mut keys: Vec<_> = record.keys().cloned().collect();
    keys.sort();
    let mut ordered = Map::new();
    for key in keys {
        if let Some(value) = record.remove(&key) {
            ordered.insert(key, value);
        }
    }
    let text = format!(
        "{}\n",
        serde_json::to_string(&Value::Object(ordered)).map_err(|error| error.to_string())?
    );
    write_text_atomic(&ship_outcome_path(implement_tmpdir, kind), &text)
}

fn classify_ship_outcome(
    kind: AssessmentKind,
    assessment_kind: &str,
    note_state: &str,
) -> (&'static str, &'static str, &'static str) {
    if note_state == NOTE_STATE_DETERMINISTIC_CLEAN {
        return (
            "clean",
            REASON_DETERMINISTIC_CLEAN,
            ASSESSMENT_OUTCOME_CLEAN,
        );
    }
    if note_state == NOTE_STATE_UNAVAILABLE {
        return ("dropped", REASON_UNAVAILABLE, "");
    }
    if assessment_kind == ASSESSMENT_OUTCOME_CLEAN {
        return ("clean", "clean-note", ASSESSMENT_OUTCOME_CLEAN);
    }
    (
        if kind.is_invariant() {
            "violation"
        } else {
            "pinned"
        },
        if kind.is_invariant() {
            "violation-note"
        } else {
            "note-pinned"
        },
        kind.non_clean_authored_outcome(),
    )
}

fn bounded_detail(text: &str) -> String {
    sanitize_diagnostic_line(&redact_outbound(text))
        .chars()
        .take(500)
        .collect()
}

/// Append a guideline deviation warning unless the run already has the same warning.
#[must_use]
pub fn append_deviation_note(implement_tmpdir: &Path, note: &str) -> &'static str {
    // Mirrors Python `append_deviation_note`: format the warning, redact each
    // chunk, then category-key-dedupe against the live ledger and optional
    // durable NDJSON batch before composing. Step 8 is single-threaded per
    // run, so the directory lock the CLI append holds is omitted here.
    let Ok(entry) = format_deviation_warning_entry(note) else {
        return "failed";
    };
    let issue_log = implement_tmpdir.join("execution-issues.md");
    if issue_log
        .symlink_metadata()
        .is_ok_and(|metadata| !metadata.is_file())
    {
        return "failed";
    }
    let batch_text = execution_issue_batch_path(implement_tmpdir)
        .and_then(|path| fs::read_to_string(path).ok())
        .unwrap_or_default();
    let existing = fs::read_to_string(&issue_log).unwrap_or_default();
    let mut known = existing_execution_issue_keys(&batch_text);
    for (category, section) in execution_issue_sections(&existing) {
        for chunk in execution_issue_chunks(&section) {
            known.extend(execution_issue_body_keys(&category, &chunk));
        }
    }
    let mut kept = Vec::new();
    for chunk in execution_issue_chunks(&entry) {
        let Ok(redacted) = redact_batch_payload(&chunk) else {
            return "failed";
        };
        let keys = execution_issue_body_keys(EXECUTION_WARNINGS_CATEGORY, &redacted);
        if !keys.is_empty() && keys.is_subset(&known) {
            continue;
        }
        known.extend(keys);
        kept.push(redacted);
    }
    if kept.is_empty() {
        return "duplicate";
    }
    let composed =
        compose_execution_issue(&existing, EXECUTION_WARNINGS_CATEGORY, &kept.join("\n"));
    if write_text_atomic(&issue_log, &composed).is_err() {
        return "failed";
    }
    "ok"
}

fn execution_issue_batch_path(implement_tmpdir: &Path) -> Option<PathBuf> {
    let run_id = read_session_run_id(implement_tmpdir);
    if run_id.is_empty() {
        return None;
    }
    Some(
        implement_tmpdir
            .join("larch-logs")
            .join("implement")
            .join(run_id)
            .join("execution-issues.ndjson"),
    )
}

fn read_session_run_id(implement_tmpdir: &Path) -> String {
    let parent = implement_tmpdir.join("parent-issue.md");
    if let Ok(text) = fs::read_to_string(&parent) {
        for line in text.lines() {
            if let Some(value) = line.strip_prefix("RUN_ID=") {
                let run_id = value.trim();
                if valid_run_id(run_id) {
                    return run_id.to_owned();
                }
            }
        }
    }
    let session_id = implement_tmpdir.join("session-id");
    if !regular_file(&session_id) {
        return String::new();
    }
    let Ok(run_id) = fs::read_to_string(&session_id) else {
        return String::new();
    };
    let run_id = run_id.trim();
    if valid_run_id(run_id) {
        run_id.to_owned()
    } else {
        String::new()
    }
}

fn valid_run_id(run_id: &str) -> bool {
    !run_id.is_empty()
        && !run_id.contains("..")
        && !run_id.contains('/')
        && !run_id.contains('\\')
        && RUN_ID_RE.is_match(run_id)
}

fn format_deviation_warning_entry(note: &str) -> Result<String, String> {
    let mut lines = Vec::new();
    for raw in note.lines() {
        let stripped = raw.trim();
        if stripped.is_empty() {
            continue;
        }
        if stripped.starts_with("- ") {
            lines.push(stripped.to_owned());
        } else {
            lines.push(format!("- {stripped}"));
        }
    }
    if lines.is_empty() {
        return Err("note-file: content must not be empty".to_owned());
    }
    Ok(lines.join("\n"))
}

fn invalidate_implement_note(implement_tmpdir: &Path, kind: AssessmentKind) -> Result<(), String> {
    let mut names = vec![
        kind.staged_assessment_filename(),
        kind.staged_assessment_env_filename(),
        kind.durable_note_filename(),
        kind.durable_note_env_filename(),
        kind.dropped_note_filename(),
        kind.ship_outcome_sidecar_filename(),
    ];
    if kind == AssessmentKind::Guidelines {
        names.insert(0, LEGACY_WARNING);
        names.insert(1, LEGACY_WARNING_ENV);
    }
    for name in &names {
        let path = implement_tmpdir.join(name);
        let _ = remove_artifact(&path);
    }
    let surviving: Vec<_> = names
        .iter()
        .filter(|name| implement_tmpdir.join(name).symlink_metadata().is_ok())
        .copied()
        .collect();
    if surviving.is_empty() {
        Ok(())
    } else {
        Err(format!(
            "artifact(s) survived invalidation: {}",
            surviving.join(", ")
        ))
    }
}

fn clear_staged_and_dropped(implement_tmpdir: &Path, kind: AssessmentKind) {
    let mut names = vec![
        kind.staged_assessment_filename(),
        kind.staged_assessment_env_filename(),
        kind.dropped_note_filename(),
        kind.ship_outcome_sidecar_filename(),
    ];
    if kind == AssessmentKind::Guidelines {
        names.insert(0, LEGACY_WARNING);
        names.insert(1, LEGACY_WARNING_ENV);
    }
    for name in names {
        let _ = remove_artifact(&implement_tmpdir.join(name));
    }
}

fn remove_artifact(path: &Path) -> Result<(), String> {
    match path.symlink_metadata() {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.to_string()),
        Ok(meta) if meta.is_dir() && !meta.file_type().is_symlink() => {
            fs::remove_dir_all(path).map_err(|error| error.to_string())
        }
        Ok(_) => fs::remove_file(path).map_err(|error| error.to_string()),
    }
}

fn resolve_dir(path: &Path) -> Result<PathBuf, String> {
    let meta = path.symlink_metadata().map_err(|error| error.to_string())?;
    if meta.file_type().is_symlink() || !meta.is_dir() {
        return Err("repo root and implement tmpdir must be non-symlink directories".to_owned());
    }
    path.canonicalize().map_err(|error| error.to_string())
}

fn under(path: &Path, root: &Path) -> bool {
    match (path.canonicalize(), root.canonicalize()) {
        (Ok(resolved), Ok(root_resolved)) => resolved.starts_with(root_resolved),
        _ => false,
    }
}

fn same_resolved_path(left: &Path, right: &Path) -> bool {
    match (left.canonicalize(), right.canonicalize()) {
        (Ok(left), Ok(right)) => left == right,
        _ => false,
    }
}

fn regular_file(path: &Path) -> bool {
    path.symlink_metadata()
        .is_ok_and(|meta| meta.is_file() && !meta.file_type().is_symlink())
}

/// Read a non-symlink regular file confined under `root`.
///
/// # Errors
/// Returns when `path` escapes `root`, is not a regular file, or cannot be read.
pub fn read_regular(path: &Path, root: &Path) -> Result<String, String> {
    if !under(path, root) || !regular_file(path) {
        return Err(format!(
            "invalid evidence file: {}",
            path.file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("<unknown>")
        ));
    }
    fs::read_to_string(path).map_err(|error| error.to_string())
}

fn read_env_strict(path: &Path, root: &Path) -> Result<BTreeMap<String, String>, String> {
    let text = read_regular(path, root)?;
    let mut options = ParseOptions::legacy();
    options.malformed_lines = MalformedLinePolicy::Reject;
    options.duplicates = DuplicateInputPolicy::Reject;
    let document = KvDocument::parse(&text, options)
        .map_err(|_error| "malformed or duplicate materialization field".to_owned())?;
    let mut values = BTreeMap::new();
    for row in document.rows() {
        if row.key().is_empty() {
            return Err("malformed or duplicate materialization field: <empty>".to_owned());
        }
        values.insert(row.key().to_owned(), row.value().to_owned());
    }
    Ok(values)
}

fn read_env_lenient(path: &Path) -> BTreeMap<String, String> {
    if !regular_file(path) {
        return BTreeMap::new();
    }
    let Ok(text) = fs::read_to_string(path) else {
        return BTreeMap::new();
    };
    let Ok(document) = KvDocument::parse(&text, ParseOptions::legacy()) else {
        return BTreeMap::new();
    };
    document.select(DuplicatePolicy::Last)
}

fn env_escape(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}

fn write_text_atomic(path: &Path, text: &str) -> Result<(), String> {
    write_bytes_atomic(path, text.as_bytes()).map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{
        ASSESSMENT_OUTCOME_CLEAN, AssessmentGit, AssessmentKind, AssessmentResult,
        MAX_ASSESSMENT_CHARS, NOTE_STATE_AUTHORED, NOTE_STATE_DETERMINISTIC_CLEAN, SubmitError,
        already_handled, append_deviation_note, authored_outcome_valid, deterministic_out_of_scope,
        diff_fingerprint, durable_note_path, final_report_sections, materialize, normalize_kinds,
        note_consumable, sanitize_detail, submit, validate_materialization,
        write_deterministic_clean_note, write_outcome,
    };
    use std::{
        fs,
        path::{Path, PathBuf},
        sync::Mutex,
    };

    const HEAD_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const HEAD_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    const DOCS_DIFF: &str = "diff --git a/docs/a.md b/docs/a.md\n";
    const CODE_DIFF: &str = "diff --git a/python/a.py b/python/a.py\n";

    /// Fixed-HEAD / fixed-diff git stub for offline assessment coverage.
    struct FakeGit {
        head: String,
        /// When set, `rev-parse HEAD` returns this instead of `head` (submit drift).
        drift_head: Mutex<Option<String>>,
        diff: String,
        incremental: Vec<String>,
        fail_read: Mutex<bool>,
    }

    impl FakeGit {
        fn new(head: &str, diff: &str) -> Self {
            Self {
                head: head.to_owned(),
                drift_head: Mutex::new(None),
                diff: diff.to_owned(),
                incremental: Vec::new(),
                fail_read: Mutex::new(false),
            }
        }

        fn with_drift(self, drift: &str) -> Self {
            *self.drift_head.lock().expect("lock") = Some(drift.to_owned());
            self
        }
    }

    impl AssessmentGit for FakeGit {
        fn git_read(&self, _repo_root: &Path, argv: &[&str]) -> Result<String, String> {
            if *self.fail_read.lock().expect("lock") {
                return Err("fake git read failed".to_owned());
            }
            let joined = argv.join(" ");
            if joined == "rev-parse HEAD" || joined == "rev-parse --verify HEAD^{commit}" {
                if let Some(drift) = self.drift_head.lock().expect("lock").as_ref() {
                    return Ok(drift.clone());
                }
                return Ok(self.head.clone());
            }
            if argv.len() >= 3 && argv[0] == "rev-parse" && argv[1] == "--verify" {
                let target = argv[2];
                if let Some(token) = target.strip_suffix("^{commit}") {
                    if token == "HEAD" {
                        if let Some(drift) = self.drift_head.lock().expect("lock").as_ref() {
                            return Ok(drift.clone());
                        }
                        return Ok(self.head.clone());
                    }
                    if token.contains('/') {
                        return Ok(self.head.clone());
                    }
                    return Ok(token.to_owned());
                }
            }
            Err(format!("unexpected fake git_read argv: {argv:?}"))
        }

        fn implementation_diff_for_head(
            &self,
            _repo_root: &Path,
            _head_sha: &str,
            _base_remote: &str,
            _base_ref: &str,
        ) -> Result<String, String> {
            Ok(self.diff.clone())
        }

        fn incremental_paths(
            &self,
            _repo_root: &Path,
            _old_head: &str,
            _new_head: &str,
        ) -> Result<Vec<String>, String> {
            Ok(self.incremental.clone())
        }
    }

    fn write_guidelines_knowledge(repo: &Path) {
        fs::write(
            repo.join("ARCHITECTURAL_GUIDELINES.md"),
            "### G-Py-4: Fail loudly\n\nBody.\n",
        )
        .expect("guidelines knowledge");
    }

    fn write_invariants_knowledge(repo: &Path) {
        fs::write(
            repo.join("ARCHITECTURAL_INVARIANTS.md"),
            "### I-Core-1: Keep boundaries\n\nBody.\n",
        )
        .expect("invariants knowledge");
    }

    fn write_materialize_env(
        tmpdir: &Path,
        kind: AssessmentKind,
        head: &str,
        base_ref: &str,
        diff_text: &str,
        knowledge_path: &Path,
        fingerprint_override: Option<&str>,
    ) {
        let diff_path = tmpdir.join(kind.materialized_diff_filename());
        fs::write(&diff_path, diff_text).expect("diff snapshot");
        let fingerprint =
            fingerprint_override.unwrap_or(&diff_fingerprint(diff_text)).to_owned();
        let text = format!(
            "STATUS=present\n\
             HEAD_SHA={head}\n\
             ASSESSED_HEAD_SHA={head}\n\
             BASE_REF={base_ref}\n\
             NOTE_STATE={NOTE_STATE_AUTHORED}\n\
             DIFF_FINGERPRINT={fingerprint}\n\
             AUTHORED_DIFF_FINGERPRINT={fingerprint}\n\
             COVERED_DIFF_FINGERPRINT={fingerprint}\n\
             DIFF_SNAPSHOT={}\n\
             {}=present\n\
             {}={}\n\
             ASSESSMENT_KIND=\n\
             WRITTEN_AT=2026-01-01T00:00:00Z\n",
            diff_path.display(),
            kind.status_env_key(),
            kind.path_env_key(),
            knowledge_path.display(),
        );
        fs::write(tmpdir.join(kind.materialize_env_filename()), text).expect("materialize env");
    }

    fn setup_repo_tmpdir() -> (tempfile::TempDir, PathBuf, PathBuf) {
        let root = tempfile::tempdir().expect("root");
        let repo = root.path().join("repo");
        let tmpdir = root.path().join("implement");
        fs::create_dir_all(&repo).expect("repo");
        fs::create_dir_all(&tmpdir).expect("tmpdir");
        (root, repo, tmpdir)
    }

    #[test]
    fn normalize_kinds_deduplicates_and_orders() {
        let kinds = normalize_kinds(&["guidelines", "invariants", "guidelines"]).expect("kinds");
        assert_eq!(
            kinds,
            vec![AssessmentKind::Invariants, AssessmentKind::Guidelines]
        );
    }

    #[test]
    fn normalize_kinds_rejects_empty_and_unknown() {
        assert!(normalize_kinds(&[] as &[&str]).is_err());
        assert!(normalize_kinds(&["other"]).is_err());
    }

    #[test]
    fn fingerprint_is_stable_sha256_hex() {
        let text = "diff --git a/docs/a.md b/docs/a.md\n";
        assert_eq!(diff_fingerprint(text).len(), 64);
        assert_eq!(diff_fingerprint(text), diff_fingerprint(text));
        assert_ne!(diff_fingerprint(text), diff_fingerprint("other"));
    }

    #[test]
    fn deterministic_filter_is_conservative() {
        assert!(deterministic_out_of_scope(
            "diff --git a/docs/a.md b/docs/a.md\n"
        ));
        assert!(deterministic_out_of_scope(
            "diff --git a/larch-logs/run/a.txt b/larch-logs/run/a.txt\n"
        ));
        assert!(!deterministic_out_of_scope(
            "diff --git a/python/a.py b/python/a.py\n"
        ));
        assert!(!deterministic_out_of_scope(
            "diff --git a/docs/a.md b/docs/b.md\n"
        ));
        assert!(!deterministic_out_of_scope(
            "Binary files a/x and b/x differ\n"
        ));
        assert!(!deterministic_out_of_scope("diff --git a/../x b/../x\n"));
        assert!(!deterministic_out_of_scope(""));
        assert!(!deterministic_out_of_scope(
            "diff --git a/docs/noext b/docs/noext\n"
        ));
        assert!(!deterministic_out_of_scope(
            "rename from docs/a.md\nrename to docs/b.md\n"
        ));
        assert!(!deterministic_out_of_scope(
            "GIT binary patch\nliteral 1\n"
        ));
    }

    #[test]
    fn sanitize_detail_redacts_path_flattens_and_truncates() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let token = format!("ghp_{}", "x".repeat(30));
        let input = format!(
            "lead\n{}{}\t{token}{}",
            tmp.path().display(),
            "\u{0001}",
            "Z".repeat(600)
        );
        let out = sanitize_detail(&input, tmp.path());
        assert!(!out.contains('\n'), "{out:?}");
        assert!(!out.contains(tmp.path().to_str().expect("utf8")), "{out}");
        assert!(out.contains("<implement-tmpdir>"), "{out}");
        assert!(!out.contains(&token), "{out}");
        assert!(out.contains("<REDACTED-TOKEN>") || !out.contains("ghp_"), "{out}");
        assert!(out.len() <= 500, "len={}", out.len());
        assert!(out.starts_with("lead <implement-tmpdir>"), "{out}");
    }

    #[test]
    fn final_report_sections_empty_when_notes_missing_or_head_wrong() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        assert_eq!(final_report_sections(tmp.path(), HEAD_A), "");
        write_deterministic_clean_note(
            tmp.path(),
            HEAD_A,
            "origin/main",
            DOCS_DIFF,
            AssessmentKind::Guidelines,
        )
        .expect("write");
        assert_eq!(final_report_sections(tmp.path(), HEAD_B), "");
    }

    #[test]
    fn final_report_sections_renders_consumable_guidelines_note() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        write_deterministic_clean_note(
            tmp.path(),
            HEAD_A,
            "origin/main",
            DOCS_DIFF,
            AssessmentKind::Guidelines,
        )
        .expect("write");
        let report = final_report_sections(tmp.path(), HEAD_A);
        assert!(report.contains("## Architectural guidelines"), "{report}");
        assert!(report.contains("no deviations identified"), "{report}");
        assert!(!report.contains("## Architectural invariants"), "{report}");
    }

    #[test]
    fn clean_note_persists_deterministic_identity() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let head = "a".repeat(40);
        let diff = "diff --git a/docs/a.md b/docs/a.md\n";
        write_deterministic_clean_note(
            tmp.path(),
            &head,
            "origin/main",
            diff,
            AssessmentKind::Guidelines,
        )
        .expect("write clean");
        let note = fs::read_to_string(durable_note_path(tmp.path(), AssessmentKind::Guidelines))
            .expect("note");
        assert!(note.contains("no deviations identified"));
        let meta = fs::read_to_string(
            tmp.path()
                .join(AssessmentKind::Guidelines.durable_note_env_filename()),
        )
        .expect("meta");
        assert!(meta.contains(&format!("NOTE_STATE={NOTE_STATE_DETERMINISTIC_CLEAN}")));
        assert!(meta.contains(&format!("DIFF_FINGERPRINT={}", diff_fingerprint(diff))));
        assert!(meta.contains("ASSESSMENT_KIND=clean"));
        assert!(note_consumable(
            tmp.path(),
            &head,
            AssessmentKind::Guidelines,
            "origin/main",
            None,
            None,
        ));
    }

    #[test]
    fn write_outcome_writes_valid_ship_sidecar() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let result = AssessmentResult {
            kind: AssessmentKind::Guidelines,
            state: ASSESSMENT_OUTCOME_CLEAN.to_owned(),
            assessment: AssessmentKind::Guidelines
                .clean_presentation_note()
                .to_owned(),
            head_sha: HEAD_A.to_owned(),
            base_ref: "origin/main".to_owned(),
            diff_fingerprint: diff_fingerprint(DOCS_DIFF),
            knowledge_sha256: "d".repeat(64),
        };
        write_outcome(
            AssessmentKind::Guidelines,
            tmp.path(),
            &result,
            NOTE_STATE_DETERMINISTIC_CLEAN,
            "",
        )
        .expect("write outcome");
        let text = fs::read_to_string(
            tmp.path()
                .join(AssessmentKind::Guidelines.ship_outcome_sidecar_filename()),
        )
        .expect("sidecar");
        assert!(text.contains(r#""outcome":"clean""#), "{text}");
        assert!(
            text.contains(r#""reason":"deterministic-clean""#),
            "{text}"
        );
        assert!(text.contains(r#""assessment_kind":"clean""#), "{text}");
        assert!(text.contains(HEAD_A), "{text}");
    }

    #[test]
    fn write_outcome_rejects_empty_head() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let result = AssessmentResult {
            kind: AssessmentKind::Invariants,
            state: "violation".to_owned(),
            assessment: "I-Core-1 broken\n".to_owned(),
            head_sha: String::new(),
            base_ref: "origin/main".to_owned(),
            diff_fingerprint: "f".repeat(64),
            knowledge_sha256: "d".repeat(64),
        };
        let err = write_outcome(
            AssessmentKind::Invariants,
            tmp.path(),
            &result,
            NOTE_STATE_AUTHORED,
            "detail",
        )
        .expect_err("empty head");
        assert!(err.contains("head_sha is empty"), "{err}");
    }

    #[test]
    fn note_consumable_rejects_head_mismatch_without_repo() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        let head = "b".repeat(40);
        write_deterministic_clean_note(
            tmp.path(),
            &head,
            "origin/main",
            "diff --git a/docs/a.md b/docs/a.md\n",
            AssessmentKind::Invariants,
        )
        .expect("write");
        assert!(!note_consumable(
            tmp.path(),
            &"c".repeat(40),
            AssessmentKind::Invariants,
            "origin/main",
            None,
            None,
        ));
    }

    #[test]
    fn note_consumable_with_fake_git_when_live_fingerprint_matches() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_deterministic_clean_note(
            &tmpdir,
            HEAD_A,
            "origin/main",
            DOCS_DIFF,
            AssessmentKind::Guidelines,
        )
        .expect("write");
        let git = FakeGit::new(HEAD_A, DOCS_DIFF);
        assert!(note_consumable(
            &tmpdir,
            HEAD_A,
            AssessmentKind::Guidelines,
            "origin/main",
            Some(repo.as_path()),
            Some(&git as &dyn AssessmentGit),
        ));
    }

    #[test]
    fn authored_outcome_valid_clean_violation_and_deviation_cases() {
        assert!(authored_outcome_valid(
            "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n",
            "clean",
            false
        ));
        assert!(!authored_outcome_valid(
            "clean lead but cites G-Py-4 elsewhere\n",
            "clean",
            false
        ));
        assert!(authored_outcome_valid(
            "Consulted ARCHITECTURAL_INVARIANTS.md; no violations identified.\n",
            "clean",
            true
        ));
        assert!(authored_outcome_valid(
            "I-Core-1 is violated by the new helper.\n",
            "violation",
            true
        ));
        assert!(authored_outcome_valid(
            "G-Py-4 is bent for this ship ladder step.\n",
            "deviation",
            false
        ));
        assert!(!authored_outcome_valid(
            "I-Core-1 is violated by the new helper.\n",
            "deviation",
            true
        ));
        assert!(!authored_outcome_valid(
            "G-Py-4 is bent for this ship ladder step.\n",
            "violation",
            false
        ));
        assert!(!authored_outcome_valid("anything", "bogus", false));
        assert!(!authored_outcome_valid("", "clean", false));
    }

    #[test]
    fn append_deviation_note_ok_duplicate_and_failed() {
        let tmp = tempfile::tempdir().expect("tmpdir");
        assert_eq!(append_deviation_note(tmp.path(), "   \n"), "failed");
        assert_eq!(
            append_deviation_note(tmp.path(), "G-Py-4 bent for tests."),
            "ok"
        );
        let log = fs::read_to_string(tmp.path().join("execution-issues.md")).expect("log");
        assert!(log.contains("G-Py-4 bent for tests."), "{log}");
        assert_eq!(
            append_deviation_note(tmp.path(), "G-Py-4 bent for tests."),
            "duplicate"
        );
        let blocked = tempfile::tempdir().expect("blocked");
        fs::create_dir_all(blocked.path().join("execution-issues.md")).expect("dir collision");
        assert_eq!(
            append_deviation_note(blocked.path(), "G-Py-4 again."),
            "failed"
        );
    }

    #[test]
    fn validate_materialization_rejects_incomplete_and_fingerprint_mismatch() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
        let git = FakeGit::new(HEAD_A, CODE_DIFF);

        fs::write(
            tmpdir.join(AssessmentKind::Guidelines.materialize_env_filename()),
            "STATUS=present\nHEAD_SHA=\n",
        )
        .expect("bad meta");
        let err = validate_materialization(
            AssessmentKind::Guidelines,
            &repo,
            &tmpdir,
            &git,
        )
        .expect_err("incomplete");
        assert!(err.contains("incomplete"), "{err}");

        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            "not-a-sha",
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let err = validate_materialization(
            AssessmentKind::Guidelines,
            &repo,
            &tmpdir,
            &git,
        )
        .expect_err("bad head");
        assert!(err.contains("HEAD_SHA is invalid"), "{err}");

        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            Some(&"0".repeat(64)),
        );
        let err = validate_materialization(
            AssessmentKind::Guidelines,
            &repo,
            &tmpdir,
            &git,
        )
        .expect_err("fp mismatch");
        assert!(err.contains("fingerprint mismatch"), "{err}");
    }

    #[test]
    fn validate_materialization_accepts_matching_stubbed_identity() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let git = FakeGit::new(HEAD_A, CODE_DIFF);
        let evidence = validate_materialization(
            AssessmentKind::Guidelines,
            &repo,
            &tmpdir,
            &git,
        )
        .expect("valid");
        assert_eq!(evidence.head_sha, HEAD_A);
        assert_eq!(evidence.base_ref, "origin/main");
        assert_eq!(evidence.diff_text, CODE_DIFF);
        assert!(evidence.identifiers.contains("G-Py-4"));
    }

    #[test]
    fn submit_rejects_bad_state_empty_note_and_exception_gate() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let git = FakeGit::new(HEAD_A, CODE_DIFF);

        let err = submit(
            "guidelines",
            "violation",
            "G-Py-4 note\n",
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect_err("bad state");
        assert!(matches!(err, SubmitError::Value(_)), "{err}");
        assert!(err.to_string().contains("unsupported"), "{err}");

        let err = submit(
            "guidelines",
            "deviation",
            "   \n",
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect_err("empty");
        assert!(err.to_string().contains("empty or oversized"), "{err}");

        let oversized = "x".repeat(MAX_ASSESSMENT_CHARS + 1);
        let err = submit(
            "guidelines",
            "deviation",
            &oversized,
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect_err("oversized");
        assert!(err.to_string().contains("empty or oversized"), "{err}");

        let err = submit(
            "guidelines",
            "deviation",
            "G-Py-4 applies.\nException: pragmatic (author: main-agent, date: 2026-07-13)\n",
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect_err("exception gate");
        assert!(
            err.to_string().contains("documented-exception")
                || err.to_string().contains("allow-exception"),
            "{err}"
        );
    }

    #[test]
    fn submit_rejects_head_drift_after_materialize() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let git = FakeGit::new(HEAD_A, CODE_DIFF).with_drift(HEAD_B);
        let err = submit(
            "guidelines",
            "clean",
            &format!(
                "{}\n",
                AssessmentKind::Guidelines.clean_presentation_note()
            ),
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect_err("drift");
        assert!(matches!(err, SubmitError::HeadDrift(_)), "{err}");
        assert!(err.to_string().contains("HEAD changed"), "{err}");
    }

    #[test]
    fn submit_persists_clean_guidelines_assessment() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let git = FakeGit::new(HEAD_A, CODE_DIFF);
        let note = format!(
            "{}\n",
            AssessmentKind::Guidelines.clean_presentation_note()
        );
        let result = submit(
            "guidelines",
            "clean",
            &note,
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect("submit clean");
        assert_eq!(result.state, "clean");
        assert_eq!(result.head_sha, HEAD_A);
        let durable = fs::read_to_string(durable_note_path(&tmpdir, AssessmentKind::Guidelines))
            .expect("note");
        assert!(durable.contains("no deviations identified"), "{durable}");
        let sidecar = fs::read_to_string(
            tmpdir.join(AssessmentKind::Guidelines.ship_outcome_sidecar_filename()),
        )
        .expect("sidecar");
        assert!(sidecar.contains(r#""outcome":"clean""#), "{sidecar}");
    }

    #[test]
    fn submit_persists_deviation_and_appends_warning() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
        write_materialize_env(
            &tmpdir,
            AssessmentKind::Guidelines,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let git = FakeGit::new(HEAD_A, CODE_DIFF);
        let result = submit(
            "guidelines",
            "deviation",
            "G-Py-4 is bent for the coverage ladder.\n",
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect("submit deviation");
        assert_eq!(result.state, "deviation");
        let log = fs::read_to_string(tmpdir.join("execution-issues.md")).expect("log");
        assert!(log.contains("G-Py-4"), "{log}");
        let sidecar = fs::read_to_string(
            tmpdir.join(AssessmentKind::Guidelines.ship_outcome_sidecar_filename()),
        )
        .expect("sidecar");
        assert!(sidecar.contains(r#""outcome":"pinned""#), "{sidecar}");
    }

    #[test]
    fn materialize_docs_only_diff_is_deterministic_clean() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let git = FakeGit::new(HEAD_A, DOCS_DIFF);
        let (statuses, pending) =
            materialize(&["guidelines"], &repo, &tmpdir, &git).expect("materialize");
        assert!(pending.is_empty(), "{pending:?}");
        assert_eq!(
            statuses.get("guidelines").map(String::as_str),
            Some("deterministic-clean")
        );
        assert!(note_consumable(
            &tmpdir,
            HEAD_A,
            AssessmentKind::Guidelines,
            "origin/main",
            None,
            None,
        ));
    }

    #[test]
    fn materialize_code_diff_returns_pending_evidence() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let git = FakeGit::new(HEAD_A, CODE_DIFF);
        let (statuses, pending) =
            materialize(&["guidelines"], &repo, &tmpdir, &git).expect("materialize");
        assert!(statuses.is_empty(), "{statuses:?}");
        assert_eq!(pending.len(), 1);
        assert_eq!(pending[0].kind, AssessmentKind::Guidelines);
        assert_eq!(pending[0].diff_text, CODE_DIFF);
        assert!(pending[0].identifiers.contains("G-Py-4"));
    }

    #[test]
    fn materialize_reports_handled_when_note_already_consumable() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_guidelines_knowledge(&repo);
        let git = FakeGit::new(HEAD_A, DOCS_DIFF);
        let (statuses, _) =
            materialize(&["guidelines"], &repo, &tmpdir, &git).expect("first");
        assert_eq!(
            statuses.get("guidelines").map(String::as_str),
            Some("deterministic-clean")
        );
        let (statuses, pending) =
            materialize(&["guidelines"], &repo, &tmpdir, &git).expect("second");
        assert!(pending.is_empty(), "{pending:?}");
        assert_eq!(
            statuses.get("guidelines").map(String::as_str),
            Some("handled")
        );
        assert!(
            already_handled(
                AssessmentKind::Guidelines,
                &repo,
                &tmpdir,
                HEAD_A,
                &git,
            )
            .expect("already")
        );
    }

    #[test]
    fn materialize_invariants_with_code_diff_is_pending() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_invariants_knowledge(&repo);
        let git = FakeGit::new(HEAD_A, CODE_DIFF);
        let (statuses, pending) =
            materialize(&["invariants"], &repo, &tmpdir, &git).expect("materialize");
        assert!(statuses.is_empty(), "{statuses:?}");
        assert_eq!(pending.len(), 1);
        assert!(pending[0].identifiers.contains("I-Core-1"));
    }

    #[test]
    fn submit_invariant_violation_persists_outcome() {
        let (_root, repo, tmpdir) = setup_repo_tmpdir();
        write_invariants_knowledge(&repo);
        let knowledge = repo.join("ARCHITECTURAL_INVARIANTS.md");
        write_materialize_env(
            &tmpdir,
            AssessmentKind::Invariants,
            HEAD_A,
            "origin/main",
            CODE_DIFF,
            &knowledge,
            None,
        );
        let git = FakeGit::new(HEAD_A, CODE_DIFF);
        let result = submit(
            "invariants",
            "violation",
            "I-Core-1 is violated by the coverage helper.\n",
            &repo,
            &tmpdir,
            false,
            &git,
        )
        .expect("submit violation");
        assert_eq!(result.state, "violation");
        let sidecar = fs::read_to_string(
            tmpdir.join(AssessmentKind::Invariants.ship_outcome_sidecar_filename()),
        )
        .expect("sidecar");
        assert!(sidecar.contains(r#""outcome":"violation""#), "{sidecar}");
    }
}
