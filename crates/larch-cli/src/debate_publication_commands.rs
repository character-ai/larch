//! Rust owner for the four `debate` publication verbs (#8604, which retires
//! `python/larch/debate/publication.py`): `issue-prepare`, `title-transition`,
//! `proposal-link`, and `comment-verify`.
//!
//! GitHub reads and writes route through the shared #7672 typed owner
//! (`IssueMutationOwner` over `GitHubService`); this module introduces no
//! debate-local GitHub client. The publication envelope is a distinct, simpler
//! contract from the debate-protocol `envelope()` in [`crate::debate_commands`]:
//! it carries no `schema_version`, `fingerprint`, or `phase`. Each verb prints one
//! compact, sorted-key JSON line and returns a fixed exit code, byte-identical
//! to the retired Python `publication` module.

#![allow(clippy::too_many_lines, clippy::module_name_repetitions)]

use std::collections::{BTreeMap, BTreeSet};
use std::ffi::OsString;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use larch_adapters::github::IssueMutationOwner;
use larch_adapters::{
    ConfinedPath, PathIntent, TemporaryRoot, absolute_lexical, atomic_write_utf8,
    ensure_directory_chain, read_utf8,
};
use larch_core::debate::DEBATE_SUBJECT_MAX_BYTES;
use larch_core::{
    GitHubComment, GitHubIssueState, GitHubService, IssueMutationField, IssueMutationRequest,
    IssueMutationSnapshot, VerifiedIssueMutation, redact_outbound, redact_secrets_only,
    redact_sensitive_paths, title_lifecycle_reject_marker,
};
use serde_json::{Map, Value};

use crate::github_repository_resolution::repository_ref;
use crate::github_service::with_github_service;
use crate::issue_mutation_support::authorization_request;

/// Canonical preparation metadata filename (mirrors `_METADATA_FILENAME`).
const METADATA_FILENAME: &str = "debate-source.json";
/// Bounded redacted subject filename (`config.DEBATE_SUBJECT_FILENAME`).
const SUBJECT_FILENAME: &str = "debate-subject.md";
/// Canonical synthesized proposal body (`config.DEBATE_PROPOSAL_BODY_FILENAME`).
const PROPOSAL_BODY_FILENAME: &str = "proposal-body.md";
/// Backlinked proposal body (`config.DEBATE_LINKED_PROPOSAL_BODY_FILENAME`).
const LINKED_PROPOSAL_BODY_FILENAME: &str = "proposal-linked-body.md";
/// Lifecycle prefix for a debate in progress (`config.DEBATE_TITLE_PREFIX_BY_STATE`).
pub const DEBATING_PREFIX: &str = "[DEBATING] ";
/// Lifecycle prefix for a concluded debate (`config.DEBATE_TITLE_PREFIX_BY_STATE`).
pub const DEBATED_PREFIX: &str = "[DEBATED] ";
/// Maximum lifecycle title length in characters (`config.TRACKING_TITLE_MAX_LEN`).
const TRACKING_TITLE_MAX_LEN: usize = 256;
/// Required opening of a debate comment marker.
const COMMENT_MARKER_PREFIX: &str = "<!-- larch:debate-";
/// Required closing of a debate comment marker.
const COMMENT_MARKER_SUFFIX: &str = " -->";
/// Suffix appended to a truncated bounded subject.
const SUBJECT_TRUNCATION_SUFFIX: &str = "\n\n[subject truncated]\n";
/// Exit code for a validation failure (`config.DEBATE_EXIT_VALIDATION`).
const EXIT_VALIDATION: u8 = 2;
/// Exit code for a publication failure (`config.DEBATE_EXIT_PUBLICATION_FAILURE`).
const EXIT_PUBLICATION: u8 = 10;

/// The seven-field preparation record persisted as `debate-source.json`
/// (mirrors Python `SourceMetadata`).
struct SourceMetadata {
    repository: String,
    issue: String,
    original_title: String,
    debating_title: String,
    debated_title: String,
    prepared_updated_at: String,
    issue_url: String,
}

/// The verified outcome of `prepare_issue`, plus the emitted artifact paths.
struct Prepared {
    metadata: SourceMetadata,
    subject_path: PathBuf,
    metadata_path: PathBuf,
}

// ---------------------------------------------------------------------------
// Command entry points
// ---------------------------------------------------------------------------

/// `debate issue-prepare`
#[must_use]
pub fn issue_prepare(arguments: &[OsString]) -> ExitCode {
    let (line, code) = match run_issue_prepare(arguments) {
        Ok(prepared) => (
            success_envelope(
                "issue-prepare",
                vec![
                    (
                        "metadata_path",
                        Value::String(path_string(&prepared.metadata_path)),
                    ),
                    (
                        "subject_path",
                        Value::String(path_string(&prepared.subject_path)),
                    ),
                    ("source_issue", Value::String(prepared.metadata.issue)),
                    ("source_url", Value::String(prepared.metadata.issue_url)),
                ],
            ),
            ExitCode::SUCCESS,
        ),
        Err(()) => (
            error_envelope("issue-prepare", "validation"),
            ExitCode::from(EXIT_VALIDATION),
        ),
    };
    println!("{line}");
    code
}

/// `debate title-transition`
#[must_use]
pub fn title_transition(arguments: &[OsString]) -> ExitCode {
    let (line, code) = match run_title_transition(arguments) {
        Ok((changed, owned, updated_at)) => (
            success_envelope(
                "title-transition",
                vec![
                    ("changed", Value::Bool(changed)),
                    ("owned", Value::Bool(owned)),
                    ("updated_at", Value::String(updated_at)),
                ],
            ),
            ExitCode::SUCCESS,
        ),
        Err(()) => (
            error_envelope("title-transition", "mutation"),
            ExitCode::from(EXIT_PUBLICATION),
        ),
    };
    println!("{line}");
    code
}

/// `debate proposal-link`
#[must_use]
pub fn proposal_link(arguments: &[OsString]) -> ExitCode {
    let (line, code) = match run_proposal_link(arguments) {
        Ok(artifact) => (
            success_envelope(
                "proposal-link",
                vec![("artifact_path", Value::String(path_string(&artifact)))],
            ),
            ExitCode::SUCCESS,
        ),
        Err(()) => (
            error_envelope("proposal-link", "validation"),
            ExitCode::from(EXIT_PUBLICATION),
        ),
    };
    println!("{line}");
    code
}

/// `debate comment-verify`
#[must_use]
pub fn comment_verify(arguments: &[OsString]) -> ExitCode {
    let (line, code) = match run_comment_verify(arguments) {
        Ok(comment_id) => (
            success_envelope(
                "comment-verify",
                vec![("comment_id", Value::String(comment_id))],
            ),
            ExitCode::SUCCESS,
        ),
        Err(()) => (
            error_envelope("comment-verify", "postcondition"),
            ExitCode::from(EXIT_PUBLICATION),
        ),
    };
    println!("{line}");
    code
}

// ---------------------------------------------------------------------------
// Envelope emitters (compact, sorted-key JSON via serde_json's BTreeMap)
// ---------------------------------------------------------------------------

/// Build the `ok:true` envelope with the verb's payload fields.
fn success_envelope(operation: &str, extra: Vec<(&str, Value)>) -> String {
    let mut object = Map::new();
    let _ = object.insert("ok".to_owned(), Value::Bool(true));
    let _ = object.insert("operation".to_owned(), Value::String(operation.to_owned()));
    let _ = object.insert("error_class".to_owned(), Value::Null);
    for (key, value) in extra {
        let _ = object.insert(key.to_owned(), value);
    }
    serde_json::to_string(&Value::Object(object)).unwrap_or_default()
}

/// Build the three-key `ok:false` envelope for a verb's fixed error class.
fn error_envelope(operation: &str, error_class: &str) -> String {
    let mut object = Map::new();
    let _ = object.insert("ok".to_owned(), Value::Bool(false));
    let _ = object.insert("operation".to_owned(), Value::String(operation.to_owned()));
    let _ = object.insert(
        "error_class".to_owned(),
        Value::String(error_class.to_owned()),
    );
    serde_json::to_string(&Value::Object(object)).unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Verb logic
// ---------------------------------------------------------------------------

fn run_issue_prepare(arguments: &[OsString]) -> Result<Prepared, ()> {
    let parsed = parse_args(arguments, &["--debate-tmpdir", "--repo", "--issue"])?;
    prepare_issue(
        value(&parsed, "--debate-tmpdir")?,
        value(&parsed, "--repo")?,
        value(&parsed, "--issue")?,
    )
}

fn run_title_transition(arguments: &[OsString]) -> Result<(bool, bool, String), ()> {
    let parsed = parse_args(arguments, &["--debate-tmpdir", "--mode"])?;
    transition_title(
        value(&parsed, "--debate-tmpdir")?,
        value(&parsed, "--mode")?,
    )
}

fn run_proposal_link(arguments: &[OsString]) -> Result<PathBuf, ()> {
    let parsed = parse_args(arguments, &["--debate-tmpdir", "--body-file"])?;
    link_proposal_body(
        value(&parsed, "--debate-tmpdir")?,
        value(&parsed, "--body-file")?,
    )
}

fn run_comment_verify(arguments: &[OsString]) -> Result<String, ()> {
    let parsed = parse_args(
        arguments,
        &["--debate-tmpdir", "--marker", "--content-file"],
    )?;
    verify_comment(
        value(&parsed, "--debate-tmpdir")?,
        value(&parsed, "--marker")?,
        value(&parsed, "--content-file")?,
    )
}

/// Borrow one required parsed flag value.
fn value<'a>(parsed: &'a BTreeMap<String, String>, flag: &str) -> Result<&'a str, ()> {
    parsed.get(flag).map(String::as_str).ok_or(())
}

/// Snapshot one open, unowned source and persist the subject and metadata.
fn prepare_issue(debate_tmpdir: &str, repository: &str, issue: &str) -> Result<Prepared, ()> {
    let root_abs = lexical_absolute(debate_tmpdir);
    ensure_directory_chain(&root_abs).map_err(|_error| ())?;
    let debate_root = TemporaryRoot::resolve(Some(&root_abs)).map_err(|_error| ())?;
    let snapshot = read_snapshot(repository, issue)?;
    if snapshot.state != GitHubIssueState::Open {
        return Err(());
    }
    if title_lifecycle_reject_marker(&snapshot.title).is_some() {
        return Err(());
    }
    let metadata = SourceMetadata {
        repository: repository.to_owned(),
        issue: issue.to_owned(),
        original_title: snapshot.title.clone(),
        debating_title: lifecycle_title(DEBATING_PREFIX, &snapshot.title)?,
        debated_title: lifecycle_title(DEBATED_PREFIX, &snapshot.title)?,
        prepared_updated_at: snapshot.updated_at.clone(),
        issue_url: format!("https://github.com/{repository}/issues/{issue}"),
    };
    let subject = bounded_subject(issue, &snapshot.title, &snapshot.body)?;
    write_confined(&debate_root, SUBJECT_FILENAME, &subject)?;
    write_metadata(&debate_root, &metadata)?;
    Ok(Prepared {
        metadata,
        subject_path: root_abs.join(SUBJECT_FILENAME),
        metadata_path: root_abs.join(METADATA_FILENAME),
    })
}

/// Apply a TITLE-only compare-and-swap lifecycle transition, or a no-op.
fn transition_title(debate_tmpdir: &str, mode: &str) -> Result<(bool, bool, String), ()> {
    let root_abs = lexical_absolute(debate_tmpdir);
    let debate_root = TemporaryRoot::resolve(Some(&root_abs)).map_err(|_error| ())?;
    let metadata = read_metadata(&debate_root)?;
    let snapshot = read_snapshot(&metadata.repository, &metadata.issue)?;
    if mode != "restore" && snapshot.state != GitHubIssueState::Open {
        return Err(());
    }
    let (target, owned) = transition_target(&metadata, &snapshot, mode)?;
    let Some(target) = target else {
        return Ok((false, owned, snapshot.updated_at));
    };
    let result = apply_title(&snapshot, &target)?;
    Ok((
        result.after.title != result.before.title,
        true,
        result.after.updated_at,
    ))
}

/// The start/finish/restore state machine (mirrors `_transition_target`).
fn transition_target(
    metadata: &SourceMetadata,
    snapshot: &IssueMutationSnapshot,
    mode: &str,
) -> Result<(Option<String>, bool), ()> {
    match mode {
        "start" => {
            if snapshot.title == metadata.debating_title {
                Ok((None, true))
            } else if snapshot.title != metadata.original_title
                || snapshot.updated_at != metadata.prepared_updated_at
            {
                Err(())
            } else {
                Ok((Some(metadata.debating_title.clone()), true))
            }
        }
        "finish" => {
            if snapshot.title == metadata.debated_title {
                Ok((None, true))
            } else if snapshot.title != metadata.debating_title {
                Err(())
            } else {
                Ok((Some(metadata.debated_title.clone()), true))
            }
        }
        "restore" => {
            if snapshot.title == metadata.debating_title {
                Ok((Some(metadata.original_title.clone()), true))
            } else {
                Ok((None, false))
            }
        }
        _ => Err(()),
    }
}

/// Append the canonical source backlink to a synthesized proposal body.
fn link_proposal_body(debate_tmpdir: &str, body_file: &str) -> Result<PathBuf, ()> {
    let root_abs = lexical_absolute(debate_tmpdir);
    let debate_root = TemporaryRoot::resolve(Some(&root_abs)).map_err(|_error| ())?;
    let metadata = read_metadata(&debate_root)?;
    if lexical_absolute(body_file) != root_abs.join(PROPOSAL_BODY_FILENAME) {
        return Err(());
    }
    let raw = read_confined(&debate_root, PROPOSAL_BODY_FILENAME, true)?;
    let body = redact_outbound(&raw);
    let body = body.trim();
    if body.is_empty() || body.contains('\u{0}') {
        return Err(());
    }
    let linked = format!(
        "{body}\n\n## Debate source\n\nSource: [#{}]({})\n",
        metadata.issue, metadata.issue_url
    );
    write_confined(&debate_root, LINKED_PROPOSAL_BODY_FILENAME, &linked)?;
    Ok(root_abs.join(LINKED_PROPOSAL_BODY_FILENAME))
}

/// Re-read one source comment and verify its exact redacted postcondition.
fn verify_comment(debate_tmpdir: &str, marker: &str, content_file: &str) -> Result<String, ()> {
    let root_abs = lexical_absolute(debate_tmpdir);
    let debate_root = TemporaryRoot::resolve(Some(&root_abs)).map_err(|_error| ())?;
    let metadata = read_metadata(&debate_root)?;
    let content = read_under_root(&root_abs, &debate_root, content_file, true)?;
    let expected = expected_comment_body(marker, &content)?;
    let comments = list_comments(&metadata.repository, &metadata.issue)?;
    let mut matches: Vec<(String, String)> = Vec::new();
    for comment in comments {
        let head = comment.body.split('\n').next().unwrap_or("");
        let head = head.strip_prefix('\u{feff}').unwrap_or(head);
        let head = head.strip_suffix('\r').unwrap_or(head);
        if head == marker {
            let id = if comment.id == 0 {
                String::new()
            } else {
                comment.id.to_string()
            };
            matches.push((id, comment.body.trim_end_matches('\n').to_owned()));
        }
    }
    if matches.len() != 1
        || matches[0].1 != expected
        || matches[0].0.is_empty()
        || !matches[0]
            .0
            .chars()
            .all(|character| character.is_ascii_digit())
    {
        return Err(());
    }
    Ok(matches[0].0.clone())
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/// Redact, normalize, and byte-bound the subject (mirrors `_bounded_subject`).
fn bounded_subject(issue: &str, title: &str, body: &str) -> Result<String, ()> {
    let raw = format!("# Debate subject\n\nSource issue #{issue}: {title}\n\n{body}");
    let mut clean = redact_outbound(&raw)
        .replace('\r', "\n")
        .replace('\u{0}', "");
    if clean.len() > DEBATE_SUBJECT_MAX_BYTES {
        let mut cut = DEBATE_SUBJECT_MAX_BYTES - SUBJECT_TRUNCATION_SUFFIX.len();
        while !clean.is_char_boundary(cut) {
            cut -= 1;
        }
        clean = format!("{}{SUBJECT_TRUNCATION_SUFFIX}", &clean[..cut]);
    }
    if clean.trim().is_empty() {
        return Err(());
    }
    Ok(clean)
}

/// Prepend a lifecycle prefix to a source title (mirrors `_lifecycle_title`).
/// The tail bound counts characters, not bytes, matching Python `str` slicing.
fn lifecycle_title(prefix: &str, original: &str) -> Result<String, ()> {
    let prefix_len = prefix.chars().count();
    if prefix_len >= TRACKING_TITLE_MAX_LEN || original.is_empty() {
        return Err(());
    }
    let tail = TRACKING_TITLE_MAX_LEN - prefix_len;
    let truncated: String = original.chars().take(tail).collect();
    Ok(format!("{prefix}{truncated}"))
}

/// Build the exact expected redacted comment body (mirrors `_expected_comment_body`).
fn expected_comment_body(marker: &str, content: &str) -> Result<String, ()> {
    if !marker.starts_with(COMMENT_MARKER_PREFIX)
        || !marker.ends_with(COMMENT_MARKER_SUFFIX)
        || marker.contains('\n')
        || marker.contains('\r')
    {
        return Err(());
    }
    let body = redact_sensitive_paths(&format!("{marker}\n\n{content}"));
    let body = redact_secrets_only(&body);
    if body.contains("[content truncated") {
        return Err(());
    }
    Ok(body.trim_end_matches('\n').to_owned())
}

// ---------------------------------------------------------------------------
// Metadata persistence
// ---------------------------------------------------------------------------

/// Write `debate-source.json` as sorted-key compact JSON plus a trailing newline.
fn write_metadata(root: &TemporaryRoot, metadata: &SourceMetadata) -> Result<(), ()> {
    let mut object = Map::new();
    let _ = object.insert(
        "repository".to_owned(),
        Value::String(metadata.repository.clone()),
    );
    let _ = object.insert("issue".to_owned(), Value::String(metadata.issue.clone()));
    let _ = object.insert(
        "original_title".to_owned(),
        Value::String(metadata.original_title.clone()),
    );
    let _ = object.insert(
        "debating_title".to_owned(),
        Value::String(metadata.debating_title.clone()),
    );
    let _ = object.insert(
        "debated_title".to_owned(),
        Value::String(metadata.debated_title.clone()),
    );
    let _ = object.insert(
        "prepared_updated_at".to_owned(),
        Value::String(metadata.prepared_updated_at.clone()),
    );
    let _ = object.insert(
        "issue_url".to_owned(),
        Value::String(metadata.issue_url.clone()),
    );
    let text = format!(
        "{}\n",
        serde_json::to_string(&Value::Object(object)).map_err(|_error| ())?
    );
    write_confined(root, METADATA_FILENAME, &text)
}

/// Read and strictly validate `debate-source.json` (mirrors `_read_metadata`).
fn read_metadata(root: &TemporaryRoot) -> Result<SourceMetadata, ()> {
    let text = read_confined(root, METADATA_FILENAME, true)?;
    let value: Value = serde_json::from_str(&text).map_err(|_error| ())?;
    let Value::Object(map) = value else {
        return Err(());
    };
    let field = |key: &str| -> Result<String, ()> {
        match map.get(key) {
            Some(Value::String(text)) if !text.is_empty() => Ok(text.clone()),
            _ => Err(()),
        }
    };
    let metadata = SourceMetadata {
        repository: field("repository")?,
        issue: field("issue")?,
        original_title: field("original_title")?,
        debating_title: field("debating_title")?,
        debated_title: field("debated_title")?,
        prepared_updated_at: field("prepared_updated_at")?,
        issue_url: field("issue_url")?,
    };
    if map.len() != 7 {
        return Err(());
    }
    Ok(metadata)
}

// ---------------------------------------------------------------------------
// Confined filesystem helpers
// ---------------------------------------------------------------------------

/// Resolve a caller path to an absolute lexical path (relative → cwd-joined).
fn lexical_absolute(path: &str) -> PathBuf {
    absolute_lexical(Path::new(path))
}

/// Atomically write one file confined to `root` by its known relative name.
fn write_confined(root: &TemporaryRoot, filename: &str, text: &str) -> Result<(), ()> {
    let confined: ConfinedPath = root
        .confine(filename, PathIntent::Write)
        .map_err(|_error| ())?;
    atomic_write_utf8(&confined, text, 0o600).map_err(|_error| ())
}

/// Read one file confined to `root` by its known relative name, strictly UTF-8.
fn read_confined(root: &TemporaryRoot, filename: &str, reject_cr: bool) -> Result<String, ()> {
    let confined = root
        .confine(filename, PathIntent::Read)
        .map_err(|_error| ())?;
    let text = read_utf8(&confined).map_err(|_error| ())?;
    if reject_cr && text.contains('\r') {
        return Err(());
    }
    Ok(text)
}

/// Read a caller-supplied path re-anchored under the canonical debate root.
///
/// The caller path is compared lexically against the lexical root (mirroring
/// Python `_assert_contained`), then the resolved relative name is confined to
/// the canonicalized root so symlinked temporary directories still read safely.
fn read_under_root(
    root_abs: &Path,
    root: &TemporaryRoot,
    supplied: &str,
    reject_cr: bool,
) -> Result<String, ()> {
    let absolute = lexical_absolute(supplied);
    let relative = absolute.strip_prefix(root_abs).map_err(|_error| ())?;
    let confined = root
        .confine(relative, PathIntent::Read)
        .map_err(|_error| ())?;
    let text = read_utf8(&confined).map_err(|_error| ())?;
    if reject_cr && text.contains('\r') {
        return Err(());
    }
    Ok(text)
}

/// Render a filesystem path as the string an envelope carries.
fn path_string(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

// ---------------------------------------------------------------------------
// GitHub boundary (the #7672 typed owner over `GitHubService`)
// ---------------------------------------------------------------------------

/// Read one issue snapshot through the shared issue-mutation owner.
fn read_snapshot(repository: &str, issue: &str) -> Result<IssueMutationSnapshot, ()> {
    let reference = repository_ref(repository)?;
    let number: u64 = issue.parse().map_err(|_error| ())?;
    with_github_service(async |service, cancellation| {
        IssueMutationOwner::new(service)
            .read_snapshot(&reference, number, cancellation)
            .await
            .map_err(|error| error.reason().to_owned())
    })
    .map_err(|_error| ())
}

/// Apply a freshness-checked TITLE-only mutation through the shared owner.
fn apply_title(
    snapshot: &IssueMutationSnapshot,
    target: &str,
) -> Result<VerifiedIssueMutation, ()> {
    let request = IssueMutationRequest {
        repository: snapshot.repository.clone(),
        issue: snapshot.issue,
        expected_updated_at: snapshot.updated_at.clone(),
        expected_state: snapshot.state,
        fields: BTreeSet::from([IssueMutationField::Title]),
        title: Some(target.to_owned()),
        body: None,
        labels: None,
        marker: None,
        lease: None,
    };
    with_github_service(async |service, cancellation| {
        IssueMutationOwner::new(service)
            .apply(
                cancellation,
                &authorization_request("", "", "", true),
                &request,
            )
            .await
            .map_err(|error| error.reason().to_owned())
    })
    .map_err(|_error| ())
}

/// List the source issue's comments through the shared GitHub service.
fn list_comments(repository: &str, issue: &str) -> Result<Vec<GitHubComment>, ()> {
    let reference = repository_ref(repository)?;
    let number: u64 = issue.parse().map_err(|_error| ())?;
    with_github_service(async |service, cancellation| {
        service
            .list_comments(&reference, number, cancellation)
            .await
            .map_err(|error| error.to_string())
    })
    .map_err(|_error| ())
}

// ---------------------------------------------------------------------------
// Argument parsing (argparse-compatible for the value flags used here)
// ---------------------------------------------------------------------------

/// Parse `--flag value` / `--flag=value` pairs; any deviation, unknown flag, or
/// missing required flag is a failure, mirroring Python `argparse`'s exit path.
fn parse_args(arguments: &[OsString], known: &[&str]) -> Result<BTreeMap<String, String>, ()> {
    let parsed = crate::debate_commands::parse_known_flags(arguments, known)?;
    for name in known {
        if !parsed.contains_key(*name) {
            return Err(());
        }
    }
    Ok(parsed)
}

#[cfg(test)]
mod tests;
