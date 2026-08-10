//! `run-log` initialization, entry-write, append, probe, and verification
//! command boundaries.
//!
//! These eight commands own every write into a run directory that is not a
//! manifest field update: `init`, `write`, `write-round`, `append`,
//! `append-entry`, `append-failure`, `exists`, and `verify-completeness`.

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;
use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fs,
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::Duration,
};

use larch_adapters::{assert_no_symlink_path_or_ancestors, run_log_manifest::utc_now};
use larch_core::{
    BatchInfo, BatchMode, CompletenessOutcome, EXECUTION_ISSUE_CATEGORIES, FAILURE_CATEGORIES,
    FailureEntry, ManifestDocument, ManifestRecord, ManifestV2Seed, ReachabilityContext,
    RunLogLayout, RunLogSlug, Sanitizer, compose_execution_issue, compose_failure_entry,
    contains_recognized_session_tmpdir_pointer, emit_kv, execution_issue_body_keys,
    execution_issue_chunks, execution_issue_sections, existing_execution_issue_keys,
    is_round_sidecar_file, lookup_batch, normalize_run_log_text, normalized_body_sha256,
    redact_batch_payload, redact_run_log_payload, round_artifact_included,
    sanitize_diagram_capture, scan_required_files, stage_round_artifact, validate_batch_payload,
    validate_failure_counts,
};
use serde_json::Value;
use sha2::{Digest as _, Sha256};

use crate::argparse_compat::{ParsedCommandLine, parse_with_flags};
use crate::run_log_commands::{emit_log_envelope, resolve_log_root};

const REQUIRED_FILES_TSV: &str = "docs/run-logs-required-files.tsv";
const APPEND_LOCK_ATTEMPTS: usize = 100;
const APPEND_LOCK_SLEEP: Duration = Duration::from_millis(50);
const ARCHETYPE_DIGEST_LEN: usize = 12;
const DYNAMIC_ARCHETYPE_SUFFIX: &str = ".md";

/// Exit code for a refusal the Python owner raised as `ValueError`.
const RC_REFUSED: u8 = 1;
/// Exit code for a refusal the Python owner raised as `OSError`.
const RC_IO: u8 = 2;

/// Identity options every batch-scoped command declares.
const IDENTITY_OPTIONS: [&str; 3] = ["--log-root", "--skill", "--run-id"];

fn options(extra: &[&'static str]) -> Vec<&'static str> {
    IDENTITY_OPTIONS
        .iter()
        .copied()
        .chain(extra.iter().copied())
        .collect()
}

/// Return an option's value, or an empty string when it was not supplied.
fn text(parsed: &ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option)
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned())
}

/// Resolved identity for one run-log tree.
struct RunIdentity {
    layout: RunLogLayout,
}

impl RunIdentity {
    fn batch_path(&self, batch: &BatchInfo) -> PathBuf {
        self.layout
            .run_dir()
            .join(format!("{}{}", batch.name(), batch.extension()))
    }
}

/// Parse the shared identity options, emitting the Python refusal envelope.
fn parse_identity(parsed: &ParsedCommandLine, verb: &str) -> Result<RunIdentity, ExitCode> {
    let skill = text(parsed, "--skill");
    let run_id = text(parsed, "--run-id");
    if skill.is_empty() || run_id.is_empty() {
        eprintln!("cli.py run-log {verb}: error: the following arguments are required");
        return Err(argument_failure(verb));
    }
    let Ok(skill) = RunLogSlug::parse(&skill) else {
        eprintln!("invalid skill: {skill}");
        return Err(argument_failure(verb));
    };
    let Ok(run_id) = RunLogSlug::parse(&run_id) else {
        eprintln!("invalid run-id: {run_id}");
        return Err(argument_failure(verb));
    };
    let log_root = match resolve_log_root(&text(parsed, "--log-root")) {
        Ok(log_root) => log_root,
        Err(message) => {
            eprintln!("{message}");
            return Err(argument_failure(verb));
        }
    };
    Ok(RunIdentity {
        layout: RunLogLayout::new(log_root, skill, run_id),
    })
}

/// Parse `arguments`, reporting an `argparse`-shaped error before refusing.
fn parse_command(
    arguments: &[OsString],
    verb: &str,
    value_options: &[&'static str],
    flags: &[&'static str],
) -> Result<ParsedCommandLine, ExitCode> {
    let parsed = parse_with_flags(arguments, value_options, flags, 0);
    if let Some(message) = parsed.error() {
        eprintln!("cli.py run-log {verb}: error: {message}");
        return Err(argument_failure(verb));
    }
    Ok(parsed)
}

fn argument_failure(verb: &str) -> ExitCode {
    envelope_failure(RC_REFUSED, &format!("invalid {verb} arguments"))
}

fn envelope_failure(code: u8, message: &str) -> ExitCode {
    emit_log_envelope(None, false, false, message);
    ExitCode::from(code)
}

/// Rebase a relative caller path under `IMPLEMENT_TMPDIR`, leaving absolute
/// paths untouched.
fn rebase_under_tmpdir(raw: &str) -> PathBuf {
    let candidate = PathBuf::from(raw);
    if raw.is_empty() || candidate.is_absolute() {
        return candidate;
    }
    match env::var("IMPLEMENT_TMPDIR") {
        Ok(tmpdir) if !tmpdir.is_empty() => PathBuf::from(tmpdir).join(candidate),
        _ => candidate,
    }
}

/// Read a file the way Python reads run-log inputs: UTF-8 with replacement.
pub fn read_lossy(path: &Path) -> Result<String, String> {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| format!("{}: {error}", path.display()))
}

/// Read one validated regular file without following a swapped leaf symlink.
pub fn read_regular_bytes(path: &Path) -> Result<Vec<u8>, String> {
    assert_no_symlink_path_or_ancestors(path)?;
    let mut options = fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    options.custom_flags(nix::libc::O_NOFOLLOW);
    let mut file = options
        .open(path)
        .map_err(|error| format!("{}: {error}", path.display()))?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("{}: {error}", path.display()))?;
    if !metadata.is_file() {
        return Err(format!(
            "refusing to read non-regular file: {}",
            path.display()
        ));
    }
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|error| format!("{}: {error}", path.display()))?;
    Ok(bytes)
}

/// Read one validated regular file as UTF-8 with replacement.
pub fn read_regular_lossy(path: &Path) -> Result<String, String> {
    read_regular_bytes(path).map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

/// Run the Rust-owned `run-log init` command.
#[must_use]
pub fn init(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_command(
        arguments,
        "init",
        &options(&["--parent-skill", "--parent-run-id", "--issue"]),
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let identity = match parse_identity(&parsed, "init") {
        Ok(identity) => identity,
        Err(code) => return code,
    };
    let parent_skill = text(&parsed, "--parent-skill");
    let parent_run_id = text(&parsed, "--parent-run-id");
    if parent_skill.is_empty() != parent_run_id.is_empty() {
        return envelope_failure(
            RC_REFUSED,
            "parent-skill and parent-run-id must be provided together",
        );
    }
    if !parent_skill.is_empty() && RunLogSlug::parse(&parent_skill).is_err() {
        return envelope_failure(RC_REFUSED, &format!("invalid parent-skill: {parent_skill}"));
    }
    if !parent_run_id.is_empty() && RunLogSlug::parse(&parent_run_id).is_err() {
        return envelope_failure(
            RC_REFUSED,
            &format!("invalid parent-run-id: {parent_run_id}"),
        );
    }
    let issue = text(&parsed, "--issue");
    let issue_number = if issue.is_empty() {
        None
    } else if issue.bytes().all(|byte| byte.is_ascii_digit()) {
        match issue.parse::<u64>() {
            Ok(number) => Some(number),
            Err(_error) => return envelope_failure(RC_REFUSED, &format!("invalid issue: {issue}")),
        }
    } else {
        return envelope_failure(RC_REFUSED, &format!("invalid issue: {issue}"));
    };

    let path = identity.layout.manifest_path();
    if path.is_file() {
        emit_log_envelope(Some(&path), false, true, "");
        return ExitCode::SUCCESS;
    }
    let mut extra: BTreeMap<String, Value> = BTreeMap::new();
    extra.insert("parent_skill".to_owned(), optional_string(&parent_skill));
    extra.insert("parent_run_id".to_owned(), optional_string(&parent_run_id));
    extra.insert(
        "issue_number".to_owned(),
        issue_number.map_or(Value::Null, Value::from),
    );
    let seed = ManifestV2Seed {
        skill: identity.layout.skill().as_str().to_owned(),
        run_id: identity.layout.run_id().as_str().to_owned(),
        timestamp: utc_now(),
        larch_version: plugin_version(),
        main_model: main_model(),
        effort: effort_level(),
        steps_ran: BTreeMap::new(),
        extra,
    };
    let document = match ManifestDocument::synthesize_v2(seed) {
        Ok(document) => document,
        Err(error) => return envelope_failure(RC_REFUSED, &error.to_string()),
    };
    if let Err(message) = write_run_log_file(&path, &document.canonical_json()) {
        return envelope_failure(RC_IO, &message);
    }
    emit_log_envelope(Some(&path), true, false, "");
    ExitCode::SUCCESS
}

fn optional_string(value: &str) -> Value {
    if value.is_empty() {
        Value::Null
    } else {
        Value::String(value.to_owned())
    }
}

/// Resolve a batch registry row, refusing an unknown name or wrong mode.
fn resolve_batch(name: &str, expected: BatchMode) -> Result<&'static BatchInfo, ExitCode> {
    let Some(batch) = lookup_batch(name) else {
        return Err(envelope_failure(
            RC_REFUSED,
            &format!("unknown batch: {name}"),
        ));
    };
    if batch.mode() != expected {
        let message = match expected {
            BatchMode::Replace => format!("batch {} is append-only; use append", batch.name()),
            BatchMode::Append => format!("batch {} is replace-only; use write", batch.name()),
        };
        return Err(envelope_failure(RC_REFUSED, &message));
    }
    Ok(batch)
}

/// Run the Rust-owned `run-log write` command.
#[must_use]
pub fn write(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_command(
        arguments,
        "write",
        &options(&["--batch", "--input-file"]),
        &["--commit"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let batch_name = text(&parsed, "--batch");
    let input_file = text(&parsed, "--input-file");
    if batch_name.is_empty() || input_file.is_empty() {
        return argument_failure("write");
    }
    let identity = match parse_identity(&parsed, "write") {
        Ok(identity) => identity,
        Err(code) => return code,
    };
    let batch = match resolve_batch(&batch_name, BatchMode::Replace) {
        Ok(batch) => batch,
        Err(code) => return code,
    };
    let payload = match staged_payload(batch, &input_file) {
        Ok(payload) => payload,
        Err(failure) => return failure.into_envelope(),
    };
    let path = identity.batch_path(batch);
    if !path.is_symlink()
        && path.is_file()
        && fs::read(&path).is_ok_and(|bytes| String::from_utf8_lossy(&bytes) == payload)
    {
        emit_log_envelope(Some(&path), false, true, "");
        return ExitCode::SUCCESS;
    }
    if let Err(message) = write_run_log_file(&path, &payload) {
        return envelope_failure(RC_IO, &message);
    }
    emit_log_envelope(Some(&path), true, false, "");
    ExitCode::SUCCESS
}

/// Run the Rust-owned `run-log append` command.
#[must_use]
pub fn append(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_command(
        arguments,
        "append",
        &options(&["--batch", "--record-file"]),
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let batch_name = text(&parsed, "--batch");
    let record_file = text(&parsed, "--record-file");
    if batch_name.is_empty() || record_file.is_empty() {
        return argument_failure("append");
    }
    let identity = match parse_identity(&parsed, "append") {
        Ok(identity) => identity,
        Err(code) => return code,
    };
    let batch = match resolve_batch(&batch_name, BatchMode::Append) {
        Ok(batch) => batch,
        Err(code) => return code,
    };
    let payload = match staged_payload(batch, &record_file) {
        Ok(payload) => payload,
        Err(failure) => return failure.into_envelope(),
    };
    let path = identity.batch_path(batch);
    if let Err(message) = append_run_log_file(&path, &payload) {
        return envelope_failure(RC_IO, &message);
    }
    emit_log_envelope(Some(&path), true, false, "");
    ExitCode::SUCCESS
}

/// Run the Rust-owned `run-log exists` command.
#[must_use]
pub fn exists(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_command(arguments, "exists", &options(&["--batch"]), &[]) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let batch_name = text(&parsed, "--batch");
    if batch_name.is_empty() {
        return argument_failure("exists");
    }
    let identity = match parse_identity(&parsed, "exists") {
        Ok(identity) => identity,
        Err(code) => return code,
    };
    let Some(batch) = lookup_batch(&batch_name) else {
        return envelope_failure(RC_REFUSED, &format!("unknown batch: {batch_name}"));
    };
    let path = identity.batch_path(batch);
    let present = path.exists();
    emit_log_envelope(Some(&path), false, present, "");
    ExitCode::SUCCESS
}

/// A staged-payload refusal carrying the Python owner's exit code.
struct PayloadFailure {
    code: u8,
    message: String,
}

impl PayloadFailure {
    const fn refused(message: String) -> Self {
        Self {
            code: RC_REFUSED,
            message,
        }
    }

    const fn io(message: String) -> Self {
        Self {
            code: RC_IO,
            message,
        }
    }

    fn into_envelope(self) -> ExitCode {
        envelope_failure(self.code, &self.message)
    }
}

/// Read, refuse, redact, cap, and validate one batch payload.
fn staged_payload(batch: &BatchInfo, source: &str) -> Result<String, PayloadFailure> {
    let source = rebase_under_tmpdir(source);
    let raw = read_lossy(&source).map_err(PayloadFailure::io)?;
    if batch.rejects_session_tmpdir() && carries_session_tmpdir_pointer(batch, &raw) {
        return Err(PayloadFailure::refused(format!(
            "batch {} rejects recognized session-tmpdir pointers before persistence",
            batch.name()
        )));
    }
    let mut redacted = redact_run_log_payload(&raw);
    if let Some(cap) = batch.cap_bytes()
        && redacted.len() > cap
    {
        let original = redacted.len();
        let head = match std::str::from_utf8(&redacted.as_bytes()[..cap]) {
            Ok(head) => head.to_owned(),
            Err(error) => redacted[..error.valid_up_to()].to_owned(),
        };
        redacted = format!("{head}\n[TRUNCATED: original {original} bytes]\n");
    }
    validate_batch_payload(batch, &redacted)
        .map_err(|error| PayloadFailure::refused(error.message().to_owned()))?;
    Ok(normalize_run_log_text(&redacted))
}

/// True when raw text, or a JSON value decoded from it, names a session tmpdir.
fn carries_session_tmpdir_pointer(batch: &BatchInfo, raw: &str) -> bool {
    if contains_recognized_session_tmpdir_pointer(raw) {
        return true;
    }
    match batch.sanitizer() {
        // Malformed rows keep the existing post-redaction validation error.
        Sanitizer::JsonLines => raw
            .lines()
            .filter(|line| !line.trim().is_empty())
            .filter_map(|line| serde_json::from_str::<Value>(line).ok())
            .any(|value| json_carries_session_pointer(&value)),
        Sanitizer::JsonObject => serde_json::from_str::<Value>(raw)
            .is_ok_and(|value| json_carries_session_pointer(&value)),
        Sanitizer::Passthrough | Sanitizer::PlanGoals => false,
    }
}

fn json_carries_session_pointer(value: &Value) -> bool {
    match value {
        Value::String(text) => contains_recognized_session_tmpdir_pointer(text),
        Value::Array(items) => items.iter().any(json_carries_session_pointer),
        Value::Object(map) => map.iter().any(|(key, item)| {
            contains_recognized_session_tmpdir_pointer(key) || json_carries_session_pointer(item)
        }),
        Value::Null | Value::Bool(_) | Value::Number(_) => false,
    }
}

/// Publish `text` through a same-directory temp file, fsync, and rename.
pub fn write_run_log_file(path: &Path, text: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .ok_or_else(|| format!("refusing to write a rootless path: {}", path.display()))?;
    // Refuse an existing linked ancestor before `create_dir_all` can create
    // directories through it, then re-check after creation for a swap.
    assert_no_symlink_path_or_ancestors(path)?;
    fs::create_dir_all(parent).map_err(|error| format!("{}: {error}", parent.display()))?;
    assert_no_symlink_path_or_ancestors(path)?;
    let file_name = path
        .file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
    let publish = || -> std::io::Result<()> {
        let mut temporary = tempfile::Builder::new()
            .prefix(&format!(".manifest-{file_name}."))
            .suffix(".tmp")
            .tempfile_in(parent)?;
        temporary.write_all(text.as_bytes())?;
        temporary.as_file().sync_all()?;
        temporary.persist(path).map_err(|error| error.error)?;
        fs::File::open(parent).and_then(|directory| directory.sync_all())
    };
    publish().map_err(|error| format!("{}: {error}", path.display()))
}

fn append_run_log_file(path: &Path, text: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| format!("{}: {error}", parent.display()))?;
    }
    let mut options = fs::OpenOptions::new();
    options.create(true).append(true);
    #[cfg(unix)]
    options.mode(0o600);
    let mut handle = options
        .open(path)
        .map_err(|error| format!("{}: {error}", path.display()))?;
    handle
        .write_all(text.as_bytes())
        .map_err(|error| format!("{}: {error}", path.display()))
}

/// Run the Rust-owned `run-log write-round` command.
#[must_use]
pub fn write_round(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_command(
        arguments,
        "write-round",
        &options(&["--round", "--source-dir"]),
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let round_text = text(&parsed, "--round");
    let source_dir = text(&parsed, "--source-dir");
    if round_text.is_empty() || source_dir.is_empty() {
        return argument_failure("write-round");
    }
    let identity = match parse_identity(&parsed, "write-round") {
        Ok(identity) => identity,
        Err(code) => return code,
    };
    let round = round_text
        .bytes()
        .all(|byte| byte.is_ascii_digit())
        .then(|| round_text.parse::<u32>().ok())
        .flatten()
        .filter(|round| *round > 0);
    let Some(round) = round else {
        return envelope_failure(RC_REFUSED, "--round must be a positive integer");
    };
    let source = PathBuf::from(&source_dir);
    if !source.is_dir() || source.is_symlink() {
        return envelope_failure(
            RC_REFUSED,
            &format!("source directory not found: {}", source.display()),
        );
    }
    let dynamic_dir = source.join("dynamic-archetypes");
    if dynamic_dir.is_symlink() {
        return envelope_failure(
            RC_IO,
            &format!(
                "dynamic-archetypes must not be a symlink: {}",
                dynamic_dir.display()
            ),
        );
    }
    let dest = identity.layout.round_dir(round);
    let previous_round_dir = identity.layout.round_dir(round - 1);
    if let Err(error) = fs::create_dir_all(&dest) {
        return envelope_failure(RC_IO, &format!("{}: {error}", dest.display()));
    }
    match stage_round(&source, &dynamic_dir, &dest, &previous_round_dir) {
        Ok(written) => {
            emit_log_envelope(Some(&dest), written, !written, "");
            ExitCode::SUCCESS
        }
        Err(failure) => failure.into_envelope(),
    }
}

fn sorted_entries(directory: &Path) -> Vec<PathBuf> {
    let mut entries: Vec<PathBuf> = fs::read_dir(directory)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .collect();
    entries.sort();
    entries
}

fn base_name(path: &Path) -> String {
    path.file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned())
}

fn stage_round(
    source: &Path,
    dynamic_dir: &Path,
    dest: &Path,
    previous_round_dir: &Path,
) -> Result<bool, PayloadFailure> {
    let flush_debug = env::var("LARCH_FLUSH_DEBUG").is_ok_and(|value| value == "1");
    let mut written = false;
    let mut archetype_refs: BTreeMap<String, String> = BTreeMap::new();
    let mut seen: BTreeMap<String, PathBuf> = BTreeMap::new();
    let mut scan_dirs = vec![source.to_path_buf()];
    if dynamic_dir.is_dir() {
        scan_dirs.push(dynamic_dir.to_path_buf());
    }
    for scan_dir in scan_dirs {
        for item in sorted_entries(&scan_dir) {
            if !item.is_file() || item.is_symlink() {
                continue;
            }
            let name = base_name(&item);
            if is_round_sidecar_file(&name) {
                continue;
            }
            // Basename shape, not a file-type test: the pool key is the slot name.
            if name.starts_with("reviewer-dyn-") && name.ends_with(DYNAMIC_ARCHETYPE_SUFFIX) {
                stage_dynamic_archetype(&item, &name, dest, &mut archetype_refs)?;
                written = true;
                continue;
            }
            if !round_artifact_included(&name, flush_debug) {
                continue;
            }
            if name == "aggregator-output.txt" {
                let sibling = item.with_file_name("findings.md");
                if sibling.is_file() && fs::read(&sibling).ok() == fs::read(&item).ok() {
                    continue;
                }
            }
            if name.starts_with("scout-round") && name.ends_with("-manifest.json") {
                let previous = previous_round_dir.join(&name);
                if previous.is_file() && fs::read(&previous).ok() == fs::read(&item).ok() {
                    continue;
                }
            }
            if let Some(first) = seen.get(&name) {
                return Err(PayloadFailure::io(format!(
                    "duplicate round artifact basename '{name}' from {} and {}",
                    item.display(),
                    first.display()
                )));
            }
            seen.insert(name.clone(), item.clone());
            let body = read_lossy(&item).map_err(PayloadFailure::io)?;
            let content = stage_round_artifact(&name, &body)
                .map_err(|error| PayloadFailure::io(error.message()))?;
            let out = dest.join(&name);
            let unchanged = out.exists()
                && fs::read(&out).is_ok_and(|bytes| String::from_utf8_lossy(&bytes) == content);
            if !unchanged {
                write_run_log_file(&out, &content).map_err(PayloadFailure::io)?;
                written = true;
            }
        }
    }
    written |= annotate_panel_manifest(dest, &archetype_refs)?;
    Ok(written)
}

fn stage_dynamic_archetype(
    item: &Path,
    name: &str,
    dest: &Path,
    archetype_refs: &mut BTreeMap<String, String>,
) -> Result<(), PayloadFailure> {
    let body = read_lossy(item).map_err(PayloadFailure::io)?;
    let redacted = normalize_run_log_text(&redact_run_log_payload(&body));
    let digest = format!("{:x}", Sha256::digest(redacted.as_bytes()));
    let digest = &digest[..ARCHETYPE_DIGEST_LEN];
    let pool = dest.join("archetypes");
    fs::create_dir_all(&pool)
        .map_err(|error| PayloadFailure::io(format!("{}: {error}", pool.display())))?;
    let pool_path = pool.join(format!("{digest}.md"));
    if !pool_path.is_file() {
        write_run_log_file(&pool_path, &redacted).map_err(PayloadFailure::io)?;
    }
    let slot = format!(
        "dyn-{}",
        name.trim_start_matches("reviewer-dyn-")
            .trim_end_matches(".md")
    );
    archetype_refs.insert(slot, format!("archetypes/{digest}.md"));
    Ok(())
}

/// Append one string field to a JSON object row, preserving every other byte.
///
/// The retired Python owner re-serialized each row, which reordered nothing but
/// did rewrite separators. Rust's `serde_json` sorts object keys, so a decode
/// and re-encode would reorder the row instead. Splicing the field in before the
/// closing brace keeps the published row stable under either owner.
fn append_object_field(row: &str, key: &str, value: &str) -> Option<String> {
    let close = row.rfind('}')?;
    let head = row[..close].trim_end();
    let separator = if head.ends_with('{') { "" } else { ", " };
    let rendered = serde_json::to_string(&Value::String(value.to_owned())).ok()?;
    Some(format!(
        "{head}{separator}{}: {rendered}{}",
        serde_json::to_string(&Value::String(key.to_owned())).ok()?,
        &row[close..]
    ))
}

fn annotate_panel_manifest(
    dest: &Path,
    archetype_refs: &BTreeMap<String, String>,
) -> Result<bool, PayloadFailure> {
    let panel_manifest = dest.join("panel-manifest.ndjson");
    if archetype_refs.is_empty() || !panel_manifest.is_file() {
        return Ok(false);
    }
    let body = read_lossy(&panel_manifest).map_err(PayloadFailure::io)?;
    let mut lines: Vec<String> = Vec::new();
    let mut changed = false;
    for line in body.lines() {
        let stripped = line.trim();
        if stripped.is_empty() {
            lines.push(line.to_owned());
            continue;
        }
        let Ok(Value::Object(row)) = serde_json::from_str::<Value>(stripped) else {
            lines.push(line.to_owned());
            continue;
        };
        let slot = row
            .get("slot")
            .map_or_else(String::new, |value| match value {
                Value::String(text) => text.clone(),
                other => other.to_string(),
            });
        match archetype_refs.get(&slot) {
            Some(reference) if !row.contains_key("archetype_ref") => {
                match append_object_field(stripped, "archetype_ref", reference) {
                    Some(rewritten) => {
                        lines.push(rewritten);
                        changed = true;
                    }
                    None => lines.push(line.to_owned()),
                }
            }
            _ => lines.push(line.to_owned()),
        }
    }
    if !changed {
        return Ok(false);
    }
    let rendered = format!("{}\n", lines.join("\n"));
    write_run_log_file(&panel_manifest, &rendered).map_err(PayloadFailure::io)?;
    Ok(true)
}

/// Run the Rust-owned `run-log append-entry` command.
#[must_use]
pub fn append_entry(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--log", "--category", "--entry", "--entry-file"],
        &[],
        0,
    );
    if parsed.error().is_some() {
        return append_usage_failure();
    }
    let log = text(&parsed, "--log");
    let category = text(&parsed, "--category");
    let entry = text(&parsed, "--entry");
    let entry_file = text(&parsed, "--entry-file");
    // `--entry` and `--entry-file` form a required mutually exclusive group.
    if log.is_empty() || category.is_empty() || entry.is_empty() == entry_file.is_empty() {
        return append_usage_failure();
    }
    if !EXECUTION_ISSUE_CATEGORIES.contains(&category.as_str()) {
        return append_kv_failure(RC_REFUSED, &format!("unsupported category: {category}"));
    }
    let body = if entry_file.is_empty() {
        entry
    } else {
        match read_lossy(Path::new(&entry_file)) {
            Ok(body) => body,
            Err(message) => return append_kv_failure(RC_IO, &message),
        }
    };
    if let Err(message) = append_execution_issue(Path::new(&log), &category, &body) {
        return append_kv_failure(RC_IO, &message);
    }
    emit_kv("APPENDED", "true");
    emit_kv("LOG", &log);
    ExitCode::SUCCESS
}

fn append_usage_failure() -> ExitCode {
    emit_kv("FAILED", "true");
    emit_kv(
        "USAGE",
        "append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)",
    );
    ExitCode::from(RC_REFUSED)
}

fn append_kv_failure(code: u8, message: &str) -> ExitCode {
    emit_kv("FAILED", "true");
    // `emit_kv` refuses embedded newlines; collapse a multi-line IO message so a
    // diagnostic can never forge extra contract-stream rows.
    emit_kv("ERROR", &message.replace(['\n', '\r'], " "));
    ExitCode::from(code)
}

/// Run the Rust-owned `run-log append-failure` command.
#[must_use]
pub fn append_failure(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--log",
            "--site",
            "--tool",
            "--exit-code",
            "--category",
            "--output-file",
            "--verdict",
            "--retry-count",
            "--transient-retry-count",
            "--status-label",
        ],
        &["--redact"],
        0,
    );
    if parsed.error().is_some() {
        emit_kv("FAILED", "true");
        return ExitCode::from(RC_REFUSED);
    }
    let log = text(&parsed, "--log");
    let site = text(&parsed, "--site");
    let tool = text(&parsed, "--tool");
    let exit_code = text(&parsed, "--exit-code");
    let category = text(&parsed, "--category");
    let output_file = text(&parsed, "--output-file");
    if log.is_empty()
        || site.is_empty()
        || tool.is_empty()
        || exit_code.is_empty()
        || category.is_empty()
        || output_file.is_empty()
    {
        emit_kv("FAILED", "true");
        return ExitCode::from(RC_REFUSED);
    }
    let status_label = text(&parsed, "--status-label");
    match record_execution_failure(&FailureRecordRequest {
        log: Path::new(&log),
        site: &site,
        tool: &tool,
        exit_code: &exit_code,
        category: &category,
        output_file: &output_file,
        verdict: &text(&parsed, "--verdict"),
        retry_count: &text(&parsed, "--retry-count"),
        transient_retry_count: &text(&parsed, "--transient-retry-count"),
        status_label: &status_label,
        redact: parsed.flag("--redact"),
    }) {
        Ok(()) => {
            emit_kv("APPENDED", "true");
            emit_kv("LOG", &log);
            ExitCode::SUCCESS
        }
        Err(failure) => append_kv_failure(failure.code, &failure.message),
    }
}

/// One execution-issues failure record, already validated by its caller's parser.
pub struct FailureRecordRequest<'a> {
    /// Execution-issues log the record is appended to.
    pub log: &'a Path,
    /// Site label, for example `implement Step 2`.
    pub site: &'a str,
    /// Tool label, for example `codex-implement`.
    pub tool: &'a str,
    /// Launcher exit code as its decimal string.
    pub exit_code: &'a str,
    /// Execution-issues category.
    pub category: &'a str,
    /// Diagnostic carrier whose body the record quotes.
    pub output_file: &'a str,
    /// Failure verdict, empty when the caller has none.
    pub verdict: &'a str,
    /// Authentication retry count, empty when the caller has none.
    pub retry_count: &'a str,
    /// Transient retry count, empty when the caller has none.
    pub transient_retry_count: &'a str,
    /// Status word, empty for the default `failed`.
    pub status_label: &'a str,
    /// Whether the quoted body is scrubbed before it is written.
    pub redact: bool,
}

/// One rejected or failed record, carrying the caller's exit code.
pub struct FailureRecordError {
    /// Process exit code the CLI command reports.
    pub code: u8,
    /// Operator-facing reason.
    pub message: String,
}

/// Compose and append one launcher failure record without emitting KV rows.
///
/// This is the quiet owner the `run-log append-failure` command and the
/// in-process launchers share, so a launcher never re-derives the entry format,
/// the redaction routing, or the append lock.
///
/// # Errors
///
/// Returns the refusal or IO failure the CLI command would have reported.
pub fn record_execution_failure(
    request: &FailureRecordRequest<'_>,
) -> Result<(), FailureRecordError> {
    if !FAILURE_CATEGORIES.contains(&request.category) {
        return Err(FailureRecordError {
            code: RC_REFUSED,
            message: format!("unsupported category: {}", request.category),
        });
    }
    validate_failure_counts(
        request.exit_code,
        request.retry_count,
        request.transient_retry_count,
    )
    .map_err(|message| FailureRecordError {
        code: RC_REFUSED,
        message,
    })?;
    let body = failure_body(request.output_file, request.exit_code).map_err(|message| {
        FailureRecordError {
            code: RC_IO,
            message,
        }
    })?;
    let body = if request.redact {
        redact_run_log_payload(&body)
    } else {
        body
    };
    let body = if request.category == "Warnings"
        && format!("{} {}", request.site, request.output_file)
            .to_lowercase()
            .contains("diagram")
    {
        sanitize_diagram_capture(&body)
    } else {
        body
    };
    let entry = compose_failure_entry(&FailureEntry {
        site: request.site,
        tool: request.tool,
        exit_code: request.exit_code,
        verdict: request.verdict,
        retry_count: request.retry_count,
        transient_retry_count: request.transient_retry_count,
        status_label: if request.status_label.is_empty() {
            "failed"
        } else {
            request.status_label
        },
        body: &body,
    });
    append_execution_issue(request.log, request.category, &entry).map_err(|message| {
        FailureRecordError {
            code: RC_IO,
            message,
        }
    })
}

/// Read captured diagnostics, or synthesize the no-diagnostics placeholder.
fn failure_body(output_file: &str, exit_code: &str) -> Result<String, String> {
    let path = PathBuf::from(output_file);
    match fs::metadata(&path) {
        Ok(metadata) if metadata.is_file() && metadata.len() > 0 => read_lossy(&path),
        _ => Ok(format!("no diagnostics captured (exit {exit_code})\n")),
    }
}

/// Append one entry under `category`, serialized by a directory lock.
///
/// The lock is a `mkdir`-based mutex on `<log>.lock.d`. `mkdir` is atomic on
/// every supported filesystem, so two processes appending concurrently never
/// interleave a record.
pub fn append_execution_issue(log_file: &Path, category: &str, entry: &str) -> Result<(), String> {
    append_execution_issue_filtered(log_file, category, entry, None, false, true).map(|_outcome| ())
}

/// Result of one category-keyed execution-issue append.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionIssueAppendOutcome {
    /// At least one new Markdown chunk was durably appended.
    Appended,
    /// Every input chunk was already present in the live or durable ledger.
    Duplicate,
}

/// Append only execution-issue chunks not already present in either ledger.
///
/// The live Markdown read, category-keyed dedupe, and atomic replacement share
/// the same directory lock. This prevents two sibling callers from both
/// deciding that a chunk is new before either publishes it. A supplied batch
/// is read as append-only NDJSON; malformed rows are ignored while a symlink,
/// non-file, or unreadable batch is refused.
///
/// # Errors
///
/// Returns a message when a path is unsafe, a source cannot be read, redaction
/// refuses a chunk, the lock cannot be acquired, or the atomic write fails.
pub fn append_execution_issue_filtered(
    log_file: &Path,
    category: &str,
    entry: &str,
    existing_batch: Option<&Path>,
    redact_entry: bool,
    spaced_sections: bool,
) -> Result<ExecutionIssueAppendOutcome, String> {
    let local_log = log_file
        .parent()
        .is_some_and(|parent| parent.as_os_str().is_empty())
        .then(|| Path::new(".").join(log_file));
    let log_file = local_log.as_deref().unwrap_or(log_file);
    if fs::symlink_metadata(log_file).is_ok_and(|metadata| !metadata.is_file()) {
        return Err(format!(
            "refusing to append through non-regular log file: {}",
            log_file.display()
        ));
    }
    assert_no_symlink_path_or_ancestors(log_file)?;
    if let Some(parent) = log_file.parent()
        && !parent.as_os_str().is_empty()
    {
        fs::create_dir_all(parent).map_err(|error| format!("{}: {error}", parent.display()))?;
    }
    assert_no_symlink_path_or_ancestors(log_file)?;
    let batch_text = match existing_batch {
        None => String::new(),
        Some(path) => match fs::symlink_metadata(path) {
            Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
                return Err(format!(
                    "refusing to read non-regular execution-issues batch: {}",
                    path.display()
                ));
            }
            Ok(_metadata) => read_regular_lossy(path)?,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => String::new(),
            Err(error) => return Err(format!("{}: {error}", path.display())),
        },
    };
    let lock = log_file.with_file_name(format!("{}.lock.d", base_name(log_file)));
    acquire_append_lock(&lock)?;
    // Initialization belongs to the same critical section as read-modify-write.
    // Otherwise a writer that observed a missing file before a peer appended can
    // create an empty ledger after that append and discard the peer's entry.
    let result = (|| {
        if !log_file.exists() {
            write_run_log_file(log_file, "")?;
        }
        let existing = read_regular_lossy(log_file)?;
        let mut known = existing_execution_issue_keys(&batch_text);
        for (existing_category, section) in execution_issue_sections(&existing) {
            for chunk in execution_issue_chunks(&section) {
                known.extend(execution_issue_body_keys(&existing_category, &chunk));
            }
        }
        let dedupe_category = if EXECUTION_ISSUE_CATEGORIES.contains(&category) {
            category
        } else {
            "Warnings"
        };
        let durable_shas = existing_category_shas(&batch_text, dedupe_category);
        let mut kept = Vec::new();
        for chunk in execution_issue_chunks(entry) {
            let chunk = if redact_entry {
                redact_batch_payload(&chunk)
                    .map_err(|_refusal| "redaction failed for run-log batch payload".to_owned())?
            } else {
                chunk
            };
            let keys = execution_issue_body_keys(dedupe_category, &chunk);
            let digest = normalized_body_sha256(&chunk);
            if (!keys.is_empty() && keys.is_subset(&known)) || durable_shas.contains(&digest) {
                continue;
            }
            known.extend(keys);
            kept.push(chunk);
        }
        if kept.is_empty() {
            return Ok(ExecutionIssueAppendOutcome::Duplicate);
        }
        let entry = kept.join("\n");
        let composed = if spaced_sections {
            compose_execution_issue(&existing, category, &entry)
        } else {
            compose_compact_execution_issue(&existing, category, &entry)
        };
        write_run_log_file(log_file, &composed)?;
        Ok(ExecutionIssueAppendOutcome::Appended)
    })();
    let _ = fs::remove_dir(&lock);
    result
}

/// Compose the historical quiet `execution-issues append` Markdown spacing.
fn compose_compact_execution_issue(existing: &str, category: &str, entry: &str) -> String {
    let heading = format!("### {category}");
    let mut lines: Vec<String> = existing.lines().map(str::to_owned).collect();
    let Some(section) = lines.iter().position(|line| *line == heading) else {
        return format!(
            "{}{}{heading}\n{}\n",
            existing.trim_end(),
            if existing.trim().is_empty() {
                ""
            } else {
                "\n\n"
            },
            entry.trim_end()
        );
    };
    let mut insert = lines
        .iter()
        .enumerate()
        .skip(section + 1)
        .find(|(_index, line)| line.starts_with("### "))
        .map_or(lines.len(), |(index, _line)| index);
    while insert > section + 1 && lines[insert - 1].is_empty() {
        insert -= 1;
    }
    lines.insert(insert, entry.trim_end().to_owned());
    format!("{}\n", lines.join("\n").trim_end())
}

/// Return source hashes already published for one category.
fn existing_category_shas(batch_text: &str, category: &str) -> BTreeSet<String> {
    batch_text
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter_map(|value| match value {
            Value::Object(row)
                if row.get("category") == Some(&Value::String(category.to_owned())) =>
            {
                row.get("source_sha256")
                    .and_then(Value::as_str)
                    .map(str::to_owned)
            }
            _other => None,
        })
        .collect()
}

/// Stage one replace-mode batch without emitting a nested command envelope.
///
/// Flush orchestration is another Rust-owned `run-log` boundary. Reusing this
/// helper keeps payload redaction, validation, path confinement, and atomic
/// publication under the same owner as the public `write` command.
pub fn stage_replace_batch(
    log_root: &Path,
    skill: &str,
    run_id: &str,
    batch_name: &str,
    source: &Path,
) -> Result<PathBuf, String> {
    let skill = RunLogSlug::parse(skill).map_err(|error| error.to_string())?;
    let run_id = RunLogSlug::parse(run_id).map_err(|error| error.to_string())?;
    let batch = lookup_batch(batch_name).ok_or_else(|| format!("unknown batch: {batch_name}"))?;
    if batch.mode() != BatchMode::Replace {
        return Err(format!("batch {} is append-only; use append", batch.name()));
    }
    let source = source
        .to_str()
        .ok_or_else(|| format!("input path must be UTF-8: {}", source.display()))?;
    let payload = staged_payload(batch, source).map_err(|failure| failure.message)?;
    let layout = RunLogLayout::new(log_root, skill, run_id);
    let path = layout
        .run_dir()
        .join(format!("{}{}", batch.name(), batch.extension()));
    if !path.is_symlink()
        && path.is_file()
        && fs::read(&path).is_ok_and(|bytes| String::from_utf8_lossy(&bytes) == payload)
    {
        return Ok(path);
    }
    write_run_log_file(&path, &payload)?;
    Ok(path)
}

/// Stage one append-mode payload without emitting a nested command envelope.
pub fn stage_append_batch(
    log_root: &Path,
    skill: &str,
    run_id: &str,
    batch_name: &str,
    source: &Path,
) -> Result<PathBuf, String> {
    let skill = RunLogSlug::parse(skill).map_err(|error| error.to_string())?;
    let run_id = RunLogSlug::parse(run_id).map_err(|error| error.to_string())?;
    let batch = lookup_batch(batch_name).ok_or_else(|| format!("unknown batch: {batch_name}"))?;
    if batch.mode() != BatchMode::Append {
        return Err(format!("batch {} is replace-only; use write", batch.name()));
    }
    let source = source
        .to_str()
        .ok_or_else(|| format!("input path must be UTF-8: {}", source.display()))?;
    let payload = staged_payload(batch, source).map_err(|failure| failure.message)?;
    let layout = RunLogLayout::new(log_root, skill, run_id);
    let path = layout
        .run_dir()
        .join(format!("{}{}", batch.name(), batch.extension()));
    assert_no_symlink_path_or_ancestors(&path)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| format!("{}: {error}", parent.display()))?;
    }
    assert_no_symlink_path_or_ancestors(&path)?;
    let lock = path.with_file_name(format!("{}.lock.d", base_name(&path)));
    acquire_append_lock(&lock)?;
    let result = (|| {
        let mut combined = if path.is_file() {
            read_lossy(&path)?
        } else {
            String::new()
        };
        combined.push_str(&payload);
        write_run_log_file(&path, &combined)
    })();
    let _ = fs::remove_dir(&lock);
    result?;
    Ok(path)
}

/// Acquire the cross-platform directory mutex shared by atomic append writers.
pub fn acquire_append_lock(lock: &Path) -> Result<(), String> {
    for attempt in 0..APPEND_LOCK_ATTEMPTS {
        match fs::create_dir(lock) {
            Ok(()) => return Ok(()),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
                if attempt + 1 == APPEND_LOCK_ATTEMPTS {
                    return Err(format!("could not acquire lock: {}", lock.display()));
                }
                thread::sleep(APPEND_LOCK_SLEEP);
            }
            Err(error) => return Err(format!("{}: {error}", lock.display())),
        }
    }
    Err(format!("could not acquire lock: {}", lock.display()))
}

/// Run the Rust-owned `run-log verify-completeness` command.
#[must_use]
pub fn verify_completeness(arguments: &[OsString]) -> ExitCode {
    let Some(first) = arguments.first() else {
        eprintln!("MISSING=manifest");
        return ExitCode::from(RC_REFUSED);
    };
    let run_dir = PathBuf::from(first);
    if !run_dir.is_dir() {
        eprintln!(
            "verify-completeness: run dir not found: {}",
            run_dir.display()
        );
        return ExitCode::from(RC_REFUSED);
    }
    let manifest_tsv = match resolve_required_files_manifest() {
        Ok(path) => path,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(RC_REFUSED);
        }
    };
    let Ok(rows) = fs::read_to_string(&manifest_tsv) else {
        eprintln!(
            "verify-completeness: manifest not found: {}",
            manifest_tsv.display()
        );
        return ExitCode::from(RC_REFUSED);
    };
    let Some(manifest) = read_run_manifest(&run_dir) else {
        println!("MISSING=manifest");
        return ExitCode::from(RC_REFUSED);
    };
    let context = ReachabilityContext::new(&run_dir, &manifest);
    match scan_required_files(&context, &rows, |pattern| glob_hit(&run_dir, pattern)) {
        CompletenessOutcome::Complete => {
            println!("OK");
            ExitCode::SUCCESS
        }
        CompletenessOutcome::Missing(missing) => {
            println!("MISSING={}", missing.join(","));
            ExitCode::from(RC_REFUSED)
        }
        CompletenessOutcome::Invalid(message) => {
            eprintln!("{message}");
            ExitCode::from(RC_REFUSED)
        }
    }
}

/// Read a run manifest that the shared versioned reader accepts.
fn read_run_manifest(run_dir: &Path) -> Option<Value> {
    let path = run_dir.join("manifest.json");
    if !path.is_file() {
        return None;
    }
    let bytes = fs::read(&path).ok()?;
    ManifestRecord::parse_bytes(&bytes).ok()?;
    serde_json::from_slice::<Value>(&bytes).ok()
}

/// Resolve a single-`*` relative path against `run_dir`.
///
/// The required-files manifest allows at most one wildcard per row, and the
/// scan rejects any row with more, so a bounded prefix/suffix match is enough.
fn glob_hit(run_dir: &Path, pattern: &str) -> bool {
    let Some((head, tail)) = pattern.split_once('*') else {
        return run_dir.join(pattern).is_file();
    };
    let (prefix_dir, prefix_name) = head.rsplit_once('/').map_or_else(
        || (run_dir.to_path_buf(), head.to_owned()),
        |(directory, name)| (run_dir.join(directory), name.to_owned()),
    );
    let (suffix_name, suffix_rest) = tail.split_once('/').map_or_else(
        || (tail.to_owned(), None),
        |(name, rest)| (name.to_owned(), Some(rest.to_owned())),
    );
    sorted_entries(&prefix_dir).into_iter().any(|entry| {
        let name = base_name(&entry);
        if !name.starts_with(&prefix_name)
            || !name.ends_with(&suffix_name)
            || name.len() < prefix_name.len() + suffix_name.len()
        {
            return false;
        }
        suffix_rest
            .as_ref()
            .map_or_else(|| entry.clone(), |rest| entry.join(rest))
            .is_file()
    })
}

fn plugin_root() -> PathBuf {
    if let Some(root) = env::var_os(larch_core::env::CLAUDE_PLUGIN_ROOT)
        && !root.is_empty()
    {
        return PathBuf::from(root);
    }
    // Direct-binary execution outside the bootstrap: `<plugin_root>/bin/larch`.
    env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().and_then(Path::parent).map(Path::to_path_buf))
        .unwrap_or_else(|| PathBuf::from("."))
}

fn resolve_required_files_manifest() -> Result<PathBuf, String> {
    let root = plugin_root();
    let raw = env::var("LARCH_VERIFY_MANIFEST").unwrap_or_default();
    if raw.is_empty() {
        return Ok(root.join(REQUIRED_FILES_TSV));
    }
    let candidate = PathBuf::from(&raw);
    let candidate = if candidate.is_absolute() {
        candidate
    } else {
        root.join(raw.strip_prefix("./").unwrap_or(&raw))
    };
    let resolved = candidate.canonicalize().unwrap_or(candidate);
    let root = root.canonicalize().unwrap_or(root);
    if resolved.starts_with(&root) {
        Ok(resolved)
    } else {
        Err("LARCH_VERIFY_MANIFEST resolves outside repository root".to_owned())
    }
}

pub fn plugin_version() -> String {
    let path = plugin_root().join(".claude-plugin").join("plugin.json");
    let Ok(text) = fs::read_to_string(path) else {
        return "unknown".to_owned();
    };
    let Ok(Value::Object(data)) = serde_json::from_str::<Value>(&text) else {
        return "unknown".to_owned();
    };
    let version = match data.get("version") {
        Some(Value::String(version)) => version.trim().to_owned(),
        None | Some(Value::Null) => String::new(),
        Some(other) => other.to_string(),
    };
    if version.is_empty() || version == "null" {
        "unknown".to_owned()
    } else {
        version
    }
}

pub fn effort_level() -> String {
    // Python reads `CLAUDE_CODE_EFFORT_LEVEL or environ.get("CLAUDE_EFFORT", "unknown")`,
    // so a set-but-empty `CLAUDE_EFFORT` records an empty effort rather than `unknown`.
    non_empty_env("CLAUDE_CODE_EFFORT_LEVEL")
        .or_else(|| env::var("CLAUDE_EFFORT").ok())
        .unwrap_or_else(|| "unknown".to_owned())
}

pub fn main_model() -> String {
    main_model_for_source(None)
}

pub fn main_model_for_source(source_file: Option<&Path>) -> String {
    non_empty_env("CLAUDE_CODE_MODEL")
        .or_else(|| non_empty_env("CLAUDE_MODEL"))
        .or_else(|| {
            source_file.and_then(crate::agent_commands::resolve_claude_model_from_source_file)
        })
        // Reuse the established Claude-transcript model resolver rather than
        // standing up a second owner for session discovery (I-Owner-1).
        .unwrap_or_else(crate::agent_commands::resolve_claude_model_from_environment)
}

fn non_empty_env(key: &str) -> Option<String> {
    env::var(key).ok().filter(|value| !value.is_empty())
}

#[cfg(test)]
mod tests {
    use super::{
        ExecutionIssueAppendOutcome, append_execution_issue, append_execution_issue_filtered,
        append_object_field, glob_hit, rebase_under_tmpdir, stage_append_batch, write_run_log_file,
    };
    use std::{fs, path::PathBuf, thread};

    #[test]
    fn appended_field_preserves_the_rest_of_the_row() {
        assert_eq!(
            append_object_field("{\"slot\": \"dyn-x\", \"z\": 1}", "archetype_ref", "a/b.md"),
            Some("{\"slot\": \"dyn-x\", \"z\": 1, \"archetype_ref\": \"a/b.md\"}".to_owned())
        );
        assert_eq!(
            append_object_field("{}", "archetype_ref", "a/b.md"),
            Some("{\"archetype_ref\": \"a/b.md\"}".to_owned())
        );
        assert_eq!(append_object_field("not-json", "k", "v"), None);
    }

    #[test]
    fn absolute_sources_are_never_rebased() {
        assert_eq!(
            rebase_under_tmpdir("/abs/input.md"),
            PathBuf::from("/abs/input.md")
        );
        assert_eq!(rebase_under_tmpdir(""), PathBuf::new());
    }

    #[test]
    fn glob_hit_matches_one_wildcard_segments() {
        let dir = tempfile::tempdir().expect("temp dir");
        let round = dir.path().join("round-2");
        fs::create_dir_all(&round).expect("round dir");
        fs::write(round.join("aggregator-validate.stderr"), "x").expect("artifact");
        assert!(glob_hit(dir.path(), "round-*/aggregator-validate.stderr"));
        assert!(!glob_hit(dir.path(), "round-*/missing.stderr"));
        assert!(!glob_hit(dir.path(), "other-*/aggregator-validate.stderr"));
    }

    #[test]
    fn writer_creates_parents_and_refuses_symlink_targets() {
        let dir = tempfile::tempdir().expect("temp dir");
        // Real callers pass an already-resolved session tmpdir; canonicalize so
        // macOS's `/var` -> `/private/var` link is not itself a refused ancestor.
        let root = fs::canonicalize(dir.path()).expect("temp dir should canonicalize");
        let nested = root.join("a/b/c.md");
        write_run_log_file(&nested, "body\n").expect("nested write");
        assert_eq!(fs::read_to_string(&nested).expect("read back"), "body\n");

        let link = root.join("link.md");
        std::os::unix::fs::symlink(&nested, &link).expect("symlink");
        let error = write_run_log_file(&link, "other\n").expect_err("symlink refusal");
        assert!(
            error.contains("refusing symlinked path or ancestor"),
            "{error}"
        );

        // A symlinked ancestor is refused too, not just the destination itself.
        let linked_dir = root.join("linked-dir");
        std::os::unix::fs::symlink(root.join("a"), &linked_dir).expect("dir symlink");
        let through = linked_dir.join("b/c.md");
        let error = write_run_log_file(&through, "other\n").expect_err("ancestor refusal");
        assert!(
            error.contains("refusing symlinked path or ancestor"),
            "{error}"
        );

        let outside = root.join("outside");
        fs::create_dir(&outside).expect("outside dir");
        let linked_missing = root.join("linked-missing");
        std::os::unix::fs::symlink(&outside, &linked_missing).expect("missing-parent link");
        let escaped = linked_missing.join("new/entry.md");
        write_run_log_file(&escaped, "other\n").expect_err("pre-create ancestor refusal");
        assert!(!outside.join("new").exists());

        let record = root.join("record.ndjson");
        fs::write(&record, "{\"warning\":true}\n").expect("append record");
        stage_append_batch(
            &linked_missing,
            "implement",
            "run-abc",
            "execution-issues",
            &record,
        )
        .expect_err("append staging ancestor refusal");
        append_execution_issue(
            &linked_missing.join("new/execution-issues.md"),
            "Warnings",
            "- warning",
        )
        .expect_err("execution issue ancestor refusal");
        assert!(!outside.join("implement").exists());
        assert!(!outside.join("new").exists());
    }

    #[test]
    fn filtered_append_deduplicates_chunks_by_category_across_both_ledgers() {
        let dir = tempfile::tempdir().expect("temp dir");
        let root = fs::canonicalize(dir.path()).expect("canonical temp dir");
        let log = root.join("execution-issues.md");
        let batch = root.join("execution-issues.ndjson");
        fs::write(&log, "### Warnings\n\n- first\n").expect("live ledger");
        fs::write(
            &batch,
            concat!(
                "not-json\n",
                "{\"body\":\"- third\\n\",\"category\":\"Warnings\"}\n",
                "{\"body\":42,\"category\":\"Warnings\"}\n"
            ),
        )
        .expect("durable ledger");

        let outcome = append_execution_issue_filtered(
            &log,
            "Warnings",
            "- first\n- second\n- third\n",
            Some(&batch),
            false,
            true,
        )
        .expect("filtered append");
        assert_eq!(outcome, ExecutionIssueAppendOutcome::Appended);
        let text = fs::read_to_string(&log).expect("updated live ledger");
        assert_eq!(text.matches("- first").count(), 1);
        assert_eq!(text.matches("- second").count(), 1);
        assert_eq!(text.matches("- third").count(), 0);

        let other_category = append_execution_issue_filtered(
            &log,
            "Tool Failures",
            "- first\n",
            Some(&batch),
            false,
            true,
        )
        .expect("category-keyed append");
        assert_eq!(other_category, ExecutionIssueAppendOutcome::Appended);
        assert_eq!(
            fs::read_to_string(&log)
                .expect("category-keyed ledger")
                .matches("- first")
                .count(),
            2
        );
    }

    #[test]
    fn filtered_append_serializes_concurrent_writers_without_loss() {
        let dir = tempfile::tempdir().expect("temp dir");
        let root = fs::canonicalize(dir.path()).expect("canonical temp dir");
        let log = root.join("execution-issues.md");
        let writers: Vec<_> = (0..12)
            .map(|index| {
                let log = log.clone();
                thread::spawn(move || {
                    append_execution_issue(&log, "Warnings", &format!("- warning-{index}"))
                })
            })
            .collect();
        for writer in writers {
            writer.join().expect("writer thread").expect("append");
        }
        let text = fs::read_to_string(&log).expect("concurrent ledger");
        for index in 0..12 {
            assert_eq!(
                text.lines()
                    .filter(|line| *line == format!("- warning-{index}"))
                    .count(),
                1
            );
        }
    }

    #[test]
    fn filtered_append_refuses_hostile_batch_paths() {
        let dir = tempfile::tempdir().expect("temp dir");
        let root = fs::canonicalize(dir.path()).expect("canonical temp dir");
        let log = root.join("execution-issues.md");
        let target = root.join("batch.ndjson");
        let link = root.join("linked-batch.ndjson");
        fs::write(&target, "").expect("batch");
        std::os::unix::fs::symlink(&target, &link).expect("batch symlink");

        let error = append_execution_issue_filtered(
            &log,
            "Warnings",
            "- warning",
            Some(&link),
            false,
            true,
        )
        .expect_err("symlinked batch must be refused");
        assert!(error.contains("non-regular execution-issues batch"));
        assert!(!log.exists());

        let hostile_root = root.join("hostile-root");
        let linked_root = root.join("linked-root");
        fs::create_dir(&hostile_root).expect("hostile root");
        fs::write(hostile_root.join("batch.ndjson"), "").expect("nested batch");
        std::os::unix::fs::symlink(&hostile_root, &linked_root).expect("ancestor symlink");
        let error = append_execution_issue_filtered(
            &log,
            "Warnings",
            "- warning",
            Some(&linked_root.join("batch.ndjson")),
            false,
            true,
        )
        .expect_err("symlinked batch ancestor must be refused");
        assert!(error.contains("refusing symlinked path or ancestor"));
        assert!(!log.exists());
    }

    #[test]
    fn filtered_append_normalizes_unknown_categories_for_durable_dedupe() {
        let dir = tempfile::tempdir().expect("temp dir");
        let root = fs::canonicalize(dir.path()).expect("canonical temp dir");
        let log = root.join("execution-issues.md");
        let batch = root.join("execution-issues.ndjson");
        fs::write(
            &batch,
            "{\"body\":\"- custom warning\\n\",\"category\":\"Warnings\"}\n",
        )
        .expect("durable ledger");

        let durable = append_execution_issue_filtered(
            &log,
            "Custom Heading",
            "- custom warning",
            Some(&batch),
            false,
            true,
        )
        .expect("normalized durable dedupe");
        assert_eq!(durable, ExecutionIssueAppendOutcome::Duplicate);

        let first = append_execution_issue_filtered(
            &log,
            "Custom Heading",
            "- live warning",
            None,
            false,
            true,
        )
        .expect("first custom append");
        let repeated = append_execution_issue_filtered(
            &log,
            "Custom Heading",
            "- live warning",
            None,
            false,
            true,
        )
        .expect("repeated custom append");
        assert_eq!(first, ExecutionIssueAppendOutcome::Appended);
        assert_eq!(repeated, ExecutionIssueAppendOutcome::Duplicate);
    }
}
