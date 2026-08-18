//! Rust owner for `debate init` and `debate round-prep` (#8600).
//!
//! Atomically replaces the Python registrations for the two commands. Seating,
//! prompt rendering, and the state store are reused from `larch-core`
//! (`debate::prompt`, `debate::state`, `external_defaults`) and the effectful
//! state layer in [`crate::debate_state`]; this module owns only argument
//! parsing, the effectful `initialize`/`round_prep` orchestration, the
//! subprocess-slot vendor bootstrap, the JSON envelope, and exit-code mapping.
//!
//! Byte-identity: stdout envelopes, `debate-state.json`, and the per-slot
//! turn-prompt files match the pre-cutover Python `orchestrator` exactly.

#![allow(clippy::too_many_lines, clippy::module_name_repetitions)]

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::Duration;

use larch_adapters::{
    PathIntent, TemporaryRoot, atomic_write_utf8_in, ensure_directory_chain, read_utf8,
};
use larch_core::debate::{
    ABSENT_FINGERPRINT, ActiveRound, DEBATE_SUBJECT_MAX_BYTES, DEBATE_SUBJECT_VALUE_KEY,
    InitializationContext, LIVE_PANEL_MINIMUM, MailboxEntry, ParticipantSlot, PointId,
    RestoreMetadata, RoundState, STATE_FILENAME, StateError, StoredState, base64_encode,
    bootstrap_prompt, is_safe_line, mailbox_entry, model_args, new_proposal, require_fingerprint,
    turn_prompt,
};
use larch_core::{
    DebateSeat, VendorLaunchRequest, VendorProgram, VendorSessionHandle, build_codex_session_argv,
    build_cursor_create_chat_argv, debate_panel_seating, parse_codex_session_id,
    parse_cursor_create_chat_id,
};
use serde_json::{Map, Value};

use crate::external_agent::{
    ExternalAgentLaunch, ExternalAgentRouting, run_external_agent_launch,
};

/// Debate envelope schema version (mirrors `config.DEBATE_ENVELOPE_SCHEMA_VERSION`).
const ENVELOPE_SCHEMA_VERSION: i64 = 2;
/// Two or more unavailable vendors hard-fails init.
const UNAVAILABLE_VENDOR_LIMIT: usize = 2;
/// Vendor bootstrap deadline in seconds.
const VENDOR_TIMEOUT_SECONDS: u64 = 900;
/// Sampling interval while a bootstrap vendor runs.
const POLL_INTERVAL: Duration = Duration::from_millis(250);

/// Exit code for a validation failure.
const EXIT_VALIDATION: i32 = 2;
/// Exit code for a persistence failure.
const EXIT_PERSISTENCE_FAILURE: i32 = 5;
/// Exit code for a vendor bootstrap runner failure.
const EXIT_RUNNER_FAILURE: i32 = 6;
/// Exit code for an unsupported subprocess transport.
const EXIT_UNSUPPORTED_TRANSPORT: i32 = 7;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

/// A stable, externally visible debate command failure carrying its exit code.
#[derive(Clone, Debug)]
struct DebateError {
    error_class: &'static str,
    exit_code: i32,
}

impl DebateError {
    const fn validation() -> Self {
        Self {
            error_class: "validation",
            exit_code: EXIT_VALIDATION,
        }
    }

    const fn persistence() -> Self {
        Self {
            error_class: "persistence_failure",
            exit_code: EXIT_PERSISTENCE_FAILURE,
        }
    }

    const fn runner_failure() -> Self {
        Self {
            error_class: "runner_failure",
            exit_code: EXIT_RUNNER_FAILURE,
        }
    }

    const fn unsupported_transport() -> Self {
        Self {
            error_class: "unsupported_transport",
            exit_code: EXIT_UNSUPPORTED_TRANSPORT,
        }
    }
}

impl From<StateError> for DebateError {
    fn from(error: StateError) -> Self {
        Self {
            error_class: error.class().as_str(),
            exit_code: error.exit_code(),
        }
    }
}

/// A subprocess-slot session bootstrapper, injected for tests.
type Bootstrapper<'a> =
    &'a dyn Fn(&ParticipantSlot, &InitializationContext) -> Result<VendorSessionHandle, DebateError>;

// ---------------------------------------------------------------------------
// Public command entry points
// ---------------------------------------------------------------------------

/// `debate init`
#[must_use]
pub fn init(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_args(
        arguments,
        &[
            "--debate-tmpdir",
            "--expected-fingerprint",
            "--repo-workdir",
            "--log-root",
            "--run-id",
            "--point-universe-json",
            "--cursor-present",
            "--codex-present",
            "--claude-present",
            "--subject-file",
            "--source-metadata-file",
            "--restore-issue-number",
            "--restore-original-title",
            "--restore-title",
            "--run-local-values-json",
        ],
        &[
            "--debate-tmpdir",
            "--expected-fingerprint",
            "--repo-workdir",
            "--log-root",
            "--run-id",
            "--point-universe-json",
            "--cursor-present",
            "--codex-present",
            "--claude-present",
            "--subject-file",
        ],
    ) {
        Ok(parsed) => parsed,
        Err(error) => return finish("init", Err(error)),
    };
    finish("init", run_init(&parsed, &default_bootstrapper))
}

/// `debate round-prep`
#[must_use]
pub fn round_prep(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_args(
        arguments,
        &["--debate-tmpdir", "--expected-fingerprint", "--round"],
        &["--debate-tmpdir", "--expected-fingerprint", "--round"],
    ) {
        Ok(parsed) => parsed,
        Err(error) => return finish("round-prep", Err(error)),
    };
    finish("round-prep", run_round_prep(&parsed))
}

/// Emit the operation envelope and map the outcome to an exit code.
fn finish(operation: &str, outcome: Result<StoredState, DebateError>) -> ExitCode {
    match outcome {
        Ok(state) => {
            println!("{}", envelope(true, operation, Some(&state), None));
            ExitCode::SUCCESS
        }
        Err(error) => {
            println!(
                "{}",
                envelope(false, operation, None, Some(error.error_class))
            );
            ExitCode::from(u8::try_from(error.exit_code).unwrap_or(2))
        }
    }
}

/// Build the `_envelope` JSON, byte-identical to the Python emitter.
fn envelope(
    ok: bool,
    operation: &str,
    state: Option<&StoredState>,
    error_class: Option<&str>,
) -> String {
    let phase = state
        .and_then(|state| state.proposal.phase())
        .map_or(Value::Null, |phase| {
            Value::String(phase.as_str().to_owned())
        });
    let terminal = state
        .and_then(|state| state.proposal.terminal_outcome())
        .map_or(Value::Null, |outcome| {
            Value::String(outcome.as_str().to_owned())
        });
    let warning = state.map_or(String::new(), |state| state.initialization.warning.clone());
    let mut object = Map::new();
    let _ = object.insert(
        "schema_version".to_owned(),
        Value::Number(ENVELOPE_SCHEMA_VERSION.into()),
    );
    let _ = object.insert("ok".to_owned(), Value::Bool(ok));
    let _ = object.insert("operation".to_owned(), Value::String(operation.to_owned()));
    let _ = object.insert(
        "fingerprint".to_owned(),
        state.map_or(Value::Null, |state| {
            Value::String(state.fingerprint.clone())
        }),
    );
    let _ = object.insert("phase".to_owned(), phase);
    let _ = object.insert("terminal_outcome".to_owned(), terminal);
    let _ = object.insert("warning".to_owned(), Value::String(warning));
    let _ = object.insert("slot_result".to_owned(), Value::Null);
    let _ = object.insert(
        "error_class".to_owned(),
        error_class.map_or(Value::Null, |class| Value::String(class.to_owned())),
    );
    let _ = object.insert("artifact_path".to_owned(), Value::Null);
    serde_json::to_string(&Value::Object(object)).unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Argument parsing (argparse-compatible for the value flags used here)
// ---------------------------------------------------------------------------

/// Parse `--flag value` / `--flag=value` pairs; any deviation is a validation
/// failure, mirroring Python `argparse`'s `SystemExit` envelope path.
fn parse_args(
    arguments: &[OsString],
    known: &[&str],
    required: &[&str],
) -> Result<BTreeMap<String, String>, DebateError> {
    let mut parsed: BTreeMap<String, String> = BTreeMap::new();
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index]
            .to_str()
            .ok_or_else(DebateError::validation)?;
        if !token.starts_with("--") {
            return Err(DebateError::validation());
        }
        let (flag, inline_value) = match token.split_once('=') {
            Some((flag, value)) => (flag, Some(value.to_owned())),
            None => (token, None),
        };
        if !known.contains(&flag) {
            return Err(DebateError::validation());
        }
        let value = if let Some(value) = inline_value {
            value
        } else {
            index += 1;
            let next = arguments.get(index).ok_or_else(DebateError::validation)?;
            next.to_str().ok_or_else(DebateError::validation)?.to_owned()
        };
        let _ = parsed.insert(flag.to_owned(), value);
        index += 1;
    }
    for name in required {
        if !parsed.contains_key(*name) {
            return Err(DebateError::validation());
        }
    }
    Ok(parsed)
}

// ---------------------------------------------------------------------------
// Input-value helpers (mirror `_point_values`, `_run_local_values`, `_strict_bool`)
// ---------------------------------------------------------------------------

fn point_values(raw: &str) -> Result<Vec<PointId>, DebateError> {
    let decoded: Value = serde_json::from_str(raw).map_err(|_error| DebateError::validation())?;
    let Value::Array(items) = decoded else {
        return Err(DebateError::validation());
    };
    if items.is_empty() {
        return Err(DebateError::validation());
    }
    let mut seen: Vec<i64> = Vec::new();
    let mut points: Vec<PointId> = Vec::new();
    for value in &items {
        let number = json_exact_int(value).ok_or_else(DebateError::validation)?;
        if seen.contains(&number) {
            return Err(DebateError::validation());
        }
        seen.push(number);
        let narrowed = u16::try_from(number).map_err(|_error| DebateError::validation())?;
        points.push(PointId::new(narrowed).map_err(|_error| DebateError::validation())?);
    }
    Ok(points)
}

fn run_local_values(raw: Option<&str>) -> Result<BTreeMap<String, String>, DebateError> {
    let Some(raw) = raw else {
        return Ok(BTreeMap::new());
    };
    let decoded: Value = serde_json::from_str(raw).map_err(|_error| DebateError::validation())?;
    let Value::Object(object) = decoded else {
        return Err(DebateError::validation());
    };
    let mut result: BTreeMap<String, String> = BTreeMap::new();
    for (key, value) in object {
        let value = value.as_str().ok_or_else(DebateError::validation)?;
        if !is_safe_line(&key) || !is_safe_line(value) {
            return Err(DebateError::validation());
        }
        let _ = result.insert(key, value.to_owned());
    }
    Ok(result)
}

fn strict_bool(value: &str) -> Result<bool, DebateError> {
    match value {
        "true" => Ok(true),
        "false" => Ok(false),
        _ => Err(DebateError::validation()),
    }
}

/// Accept only an exact JSON integer, rejecting booleans and floats.
fn json_exact_int(value: &Value) -> Option<i64> {
    match value {
        Value::Number(number) => number.as_i64(),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// init
// ---------------------------------------------------------------------------

struct InitInputs {
    debate_tmpdir: String,
    expected_fingerprint: String,
    repo_workdir: String,
    log_root: String,
    run_id: String,
    point_universe: Vec<PointId>,
    run_local_values: BTreeMap<String, String>,
    cursor: bool,
    codex: bool,
    claude: bool,
    restore_issue_number: String,
    restore_original_title: String,
    restore_title: String,
    subject: String,
}

fn run_init(
    parsed: &BTreeMap<String, String>,
    bootstrapper: Bootstrapper<'_>,
) -> Result<StoredState, DebateError> {
    let debate_tmpdir = parsed["--debate-tmpdir"].clone();
    let subject = read_subject(&debate_tmpdir, &parsed["--subject-file"])?;
    let (restore_issue_number, restore_original_title, restore_title) =
        resolve_restore(parsed, &debate_tmpdir)?;
    let inputs = InitInputs {
        debate_tmpdir,
        expected_fingerprint: parsed["--expected-fingerprint"].clone(),
        repo_workdir: parsed["--repo-workdir"].clone(),
        log_root: parsed["--log-root"].clone(),
        run_id: parsed["--run-id"].clone(),
        point_universe: point_values(&parsed["--point-universe-json"])?,
        run_local_values: run_local_values(
            parsed.get("--run-local-values-json").map(String::as_str),
        )?,
        cursor: strict_bool(&parsed["--cursor-present"])?,
        codex: strict_bool(&parsed["--codex-present"])?,
        claude: strict_bool(&parsed["--claude-present"])?,
        restore_issue_number,
        restore_original_title,
        restore_title,
        subject,
    };
    initialize(&inputs, bootstrapper)
}

/// Read the subject file confined to the debate root, rejecting CR.
fn read_subject(debate_tmpdir: &str, subject_file: &str) -> Result<String, DebateError> {
    let debate_root = ensure_trusted_root(debate_tmpdir).map_err(|_error| DebateError::validation())?;
    let confined = debate_root
        .confine(subject_file, PathIntent::Read)
        .map_err(|_error| DebateError::validation())?;
    let text = read_utf8(&confined).map_err(|_error| DebateError::validation())?;
    if text.contains('\r') {
        return Err(DebateError::validation());
    }
    Ok(text)
}

/// Resolve restore metadata from `--source-metadata-file` or the restore triplet.
fn resolve_restore(
    parsed: &BTreeMap<String, String>,
    debate_tmpdir: &str,
) -> Result<(String, String, String), DebateError> {
    if let Some(metadata_file) = parsed.get("--source-metadata-file") {
        if parsed.contains_key("--restore-issue-number")
            || parsed.contains_key("--restore-original-title")
            || parsed.contains_key("--restore-title")
        {
            return Err(DebateError::validation());
        }
        let metadata = load_source_metadata(debate_tmpdir, metadata_file)?;
        return Ok((
            metadata.issue,
            metadata.original_title,
            metadata.debating_title,
        ));
    }
    let issue = parsed
        .get("--restore-issue-number")
        .ok_or_else(DebateError::validation)?;
    let original = parsed
        .get("--restore-original-title")
        .ok_or_else(DebateError::validation)?;
    let title = parsed
        .get("--restore-title")
        .ok_or_else(DebateError::validation)?;
    Ok((issue.clone(), original.clone(), title.clone()))
}

fn initialize(
    inputs: &InitInputs,
    bootstrapper: Bootstrapper<'_>,
) -> Result<StoredState, DebateError> {
    if inputs.expected_fingerprint != ABSENT_FINGERPRINT {
        return Err(DebateError::validation());
    }
    for value in [
        &inputs.repo_workdir,
        &inputs.log_root,
        &inputs.run_id,
        &inputs.restore_issue_number,
        &inputs.restore_original_title,
        &inputs.restore_title,
    ] {
        if !is_safe_line(value) {
            return Err(DebateError::validation());
        }
    }
    let debate_root_path = lexical_absolute(&inputs.debate_tmpdir);
    let _debate_root =
        ensure_trusted_root(&inputs.debate_tmpdir).map_err(|_error| DebateError::persistence())?;
    let workdir = lexical_absolute(&inputs.repo_workdir);
    TemporaryRoot::resolve(Some(&workdir)).map_err(|_error| DebateError::validation())?;
    let log_root = lexical_absolute(&inputs.log_root);
    ensure_trusted_root(&inputs.log_root).map_err(|_error| DebateError::validation())?;

    let _lock = larch_cli::debate_state::lock_state(&debate_root_path)?;
    if debate_root_path.join(STATE_FILENAME).exists() {
        return Err(DebateError::validation());
    }

    let slots = debate_slots(inputs.cursor, inputs.codex, inputs.claude)?;
    let missing: Vec<&ParticipantSlot> = slots.iter().filter(|slot| !slot.available).collect();
    if missing.len() >= UNAVAILABLE_VENDOR_LIMIT {
        return Err(DebateError::validation());
    }
    let warning = missing
        .first()
        .map_or(String::new(), |slot| format!("unavailable vendor: {}", slot.slot));

    let mut values = inputs.run_local_values.clone();
    if values.contains_key(DEBATE_SUBJECT_VALUE_KEY) {
        return Err(DebateError::validation());
    }
    let subject_bytes = inputs.subject.as_bytes();
    if inputs.subject.is_empty()
        || inputs.subject.contains(['\r', '\u{0}'])
        || subject_bytes.len() > DEBATE_SUBJECT_MAX_BYTES
    {
        return Err(DebateError::validation());
    }
    let _ = values.insert(
        DEBATE_SUBJECT_VALUE_KEY.to_owned(),
        base64_encode(subject_bytes),
    );

    let restore = RestoreMetadata {
        issue_number: inputs.restore_issue_number.clone(),
        original_title: inputs.restore_original_title.clone(),
        restore_title: inputs.restore_title.clone(),
    };
    let point_universe: Vec<i64> = inputs
        .point_universe
        .iter()
        .map(|point| i64::from(point.number()))
        .collect();
    let mut context = InitializationContext {
        point_universe,
        run_local_values: values.clone(),
        repo_workdir: path_to_string(&workdir),
        log_root: path_to_string(&log_root),
        run_id: inputs.run_id.clone(),
        slots,
        restore,
        session_handles: BTreeMap::new(),
        warning,
    };

    let subprocess_slots: Vec<ParticipantSlot> = context
        .slots
        .iter()
        .filter(|slot| slot.available && slot.transport == "subprocess")
        .cloned()
        .collect();
    let mut handles: BTreeMap<String, VendorSessionHandle> = BTreeMap::new();
    for slot in &subprocess_slots {
        let handle = bootstrapper(slot, &context)?;
        let _ = handles.insert(slot.slot.clone(), handle);
    }
    context.session_handles = handles;

    let needles: Vec<&str> = values.values().map(String::as_str).collect();
    let proposal =
        new_proposal(&inputs.point_universe, &needles).map_err(|_error| DebateError::validation())?;
    let stored = StoredState {
        initialization: context,
        proposal,
        proposal_run_local_values: values,
        active_round: None,
        drops: Vec::new(),
        fingerprint: String::new(),
    };
    Ok(larch_cli::debate_state::write_state(&debate_root_path, &stored)?)
}

/// Fixed debate seating with availability applied, asserting protocol order.
fn debate_slots(
    cursor: bool,
    codex: bool,
    claude: bool,
) -> Result<Vec<ParticipantSlot>, DebateError> {
    let availability = |tool: &str| -> bool {
        match tool {
            "cursor" => cursor,
            "codex" => codex,
            _ => claude,
        }
    };
    let seating = debate_panel_seating();
    let slots: Vec<ParticipantSlot> = seating
        .iter()
        .map(|seat: &DebateSeat| ParticipantSlot {
            slot: seat.slot.to_owned(),
            tool: seat.tool.to_owned(),
            transport: seat.transport.to_owned(),
            available: availability(seat.tool),
            model: seat.model.to_owned(),
        })
        .collect();
    let order: Vec<&str> = slots.iter().map(|slot| slot.slot.as_str()).collect();
    if order != larch_core::debate::SLOT_ORDER {
        return Err(DebateError::validation());
    }
    Ok(slots)
}

// ---------------------------------------------------------------------------
// round-prep
// ---------------------------------------------------------------------------

fn run_round_prep(parsed: &BTreeMap<String, String>) -> Result<StoredState, DebateError> {
    let round_number: i64 = parsed["--round"]
        .trim()
        .parse()
        .map_err(|_error| DebateError::validation())?;
    let debate_tmpdir = &parsed["--debate-tmpdir"];
    let expected_fingerprint = &parsed["--expected-fingerprint"];
    let debate_root_path = lexical_absolute(debate_tmpdir);
    // Validate the existing (non-created) debate root.
    TemporaryRoot::resolve(Some(&debate_root_path)).map_err(|_error| DebateError::persistence())?;
    let _lock = larch_cli::debate_state::lock_state(&debate_root_path)?;
    let state = larch_cli::debate_state::load_state(&debate_root_path)?;
    require_fingerprint(&state, expected_fingerprint)?;
    if state.active_round.is_some() {
        return Err(DebateError::validation());
    }
    let admitted_round = i64::try_from(state.proposal.rounds().len()).unwrap_or(i64::MAX) + 1;
    if state.proposal.phase().is_none() || round_number != admitted_round {
        return Err(DebateError::validation());
    }
    let live: Vec<String> = state
        .initialization
        .slots
        .iter()
        .filter(|slot| slot.available)
        .map(|slot| slot.slot.clone())
        .collect();
    if live.len() < LIVE_PANEL_MINIMUM {
        return Err(DebateError::validation());
    }
    let previous: Option<&RoundState> = state.proposal.rounds().last();
    let mut mailboxes: BTreeMap<String, Vec<MailboxEntry>> = BTreeMap::new();
    for slot in &live {
        let entries: Vec<MailboxEntry> = previous.map_or_else(Vec::new, |round| {
            round
                .bindings()
                .iter()
                .filter(|binding| binding.slot().as_str() != slot)
                .map(mailbox_entry)
                .collect()
        });
        let _ = mailboxes.insert(slot.clone(), entries);
    }
    let subject_encoded = state
        .initialization
        .run_local_values
        .get(DEBATE_SUBJECT_VALUE_KEY)
        .cloned()
        .unwrap_or_default();
    let debate_root =
        ensure_trusted_root(debate_tmpdir).map_err(|_error| DebateError::persistence())?;
    for slot in &live {
        let prompt = turn_prompt(
            slot,
            round_number,
            &state.initialization.point_universe,
            &mailboxes[slot],
            &subject_encoded,
        )?;
        let filename = format!("{slot}-round-{round_number}-prompt.md");
        let confined = debate_root
            .confine(debate_root.path().join(&filename), PathIntent::Write)
            .map_err(|_error| DebateError::persistence())?;
        atomic_write_utf8_in(&debate_root, confined.path(), &prompt, false, 0o600)
            .map_err(|_error| DebateError::persistence())?;
    }
    let active = ActiveRound {
        round_number,
        prepared: true,
        mailboxes,
        live_slots: live.clone(),
        pending_slots: live,
        reserved_slot: None,
        bindings: BTreeMap::new(),
    };
    let stored = StoredState {
        active_round: Some(active),
        fingerprint: String::new(),
        ..state
    };
    Ok(larch_cli::debate_state::write_state(&debate_root_path, &stored)?)
}

// ---------------------------------------------------------------------------
// Source metadata (READ half of publication.load_source_metadata)
// ---------------------------------------------------------------------------

const SOURCE_METADATA_FILENAME: &str = "debate-source.json";
const SOURCE_METADATA_KEYS: [&str; 7] = [
    "repository",
    "issue",
    "original_title",
    "debating_title",
    "debated_title",
    "prepared_updated_at",
    "issue_url",
];

struct SourceMetadata {
    issue: String,
    original_title: String,
    debating_title: String,
}

fn load_source_metadata(
    debate_tmpdir: &str,
    metadata_file: &str,
) -> Result<SourceMetadata, DebateError> {
    let root = ensure_trusted_root(debate_tmpdir).map_err(|_error| DebateError::validation())?;
    // Canonical-path check: the supplied file must be exactly root/debate-source.json.
    let supplied = lexical_absolute(metadata_file);
    let expected = root.path().join(SOURCE_METADATA_FILENAME);
    if supplied != expected && supplied != lexical_absolute(debate_tmpdir).join(SOURCE_METADATA_FILENAME)
    {
        return Err(DebateError::validation());
    }
    let confined = root
        .confine(root.path().join(SOURCE_METADATA_FILENAME), PathIntent::Read)
        .map_err(|_error| DebateError::validation())?;
    let text = read_utf8(&confined).map_err(|_error| DebateError::validation())?;
    if text.contains('\r') {
        return Err(DebateError::validation());
    }
    let decoded: Value = serde_json::from_str(&text).map_err(|_error| DebateError::validation())?;
    let Value::Object(object) = decoded else {
        return Err(DebateError::validation());
    };
    let keys: Vec<&str> = object.keys().map(String::as_str).collect();
    let mut expected_keys: Vec<&str> = SOURCE_METADATA_KEYS.to_vec();
    let mut present_keys = keys.clone();
    expected_keys.sort_unstable();
    present_keys.sort_unstable();
    if present_keys != expected_keys {
        return Err(DebateError::validation());
    }
    let field = |name: &str| -> Result<String, DebateError> {
        let value = object.get(name).and_then(Value::as_str).unwrap_or_default();
        if value.is_empty() {
            return Err(DebateError::validation());
        }
        Ok(value.to_owned())
    };
    // Every value must be a non-empty string.
    for name in SOURCE_METADATA_KEYS {
        let _ = field(name)?;
    }
    Ok(SourceMetadata {
        issue: field("issue")?,
        original_title: field("original_title")?,
        debating_title: field("debating_title")?,
    })
}

// ---------------------------------------------------------------------------
// Vendor bootstrap
// ---------------------------------------------------------------------------

/// Bootstrap one subprocess vendor session and return its validated handle.
///
/// Mirrors Python `orchestrator.default_bootstrapper`: launch the vendor's
/// session-create command, capture its stdout, and parse exactly one explicit
/// session handle. Only `cursor` and `codex` are supported; every other tool is
/// an unsupported transport.
fn default_bootstrapper(
    slot: &ParticipantSlot,
    context: &InitializationContext,
) -> Result<VendorSessionHandle, DebateError> {
    let log_root = Path::new(&context.log_root);
    let capture = log_root.join(format!("{}-bootstrap-capture.txt", slot.slot));
    let output = log_root.join(format!("{}-bootstrap.out", slot.slot));
    let (program, argv) = match slot.tool.as_str() {
        "cursor" => (
            VendorProgram::Cursor,
            build_cursor_create_chat_argv().full_argv(),
        ),
        "codex" => {
            let mut request = VendorLaunchRequest::new(
                context.repo_workdir.clone(),
                output.display().to_string(),
                bootstrap_prompt(slot, &context.point_universe),
            );
            request.model_args =
                model_args(&slot.tool, &slot.model).map_err(DebateError::from)?;
            let built =
                build_codex_session_argv(&request).map_err(|_error| DebateError::runner_failure())?;
            (VendorProgram::Codex, built.full_argv())
        }
        _ => return Err(DebateError::unsupported_transport()),
    };
    let launch = ExternalAgentLaunch {
        tool: slot.tool.clone(),
        output: capture.display().to_string(),
        timeout_seconds: VENDOR_TIMEOUT_SECONDS,
        command: argv,
        program,
        routing: ExternalAgentRouting::CaptureStdoutOnly,
        stderr_sink: None,
        working_directory: Some(PathBuf::from(&context.repo_workdir)),
        environment: Vec::new(),
        sentinel_suffix: ".done",
        poll_interval: POLL_INTERVAL,
        stdin: None,
        stall_watch: None,
    };
    let outcome =
        run_external_agent_launch(&launch).map_err(|_error| DebateError::runner_failure())?;
    if outcome.exit_code != 0 {
        return Err(DebateError::runner_failure());
    }
    let text = fs::read_to_string(&capture).map_err(|_error| DebateError::runner_failure())?;
    if slot.tool == "codex" {
        return parse_codex_session_id(&text).map_err(|_error| DebateError::runner_failure());
    }
    let session_id =
        parse_cursor_create_chat_id(&text).map_err(|_error| DebateError::runner_failure())?;
    VendorSessionHandle::create("cursor", &session_id)
        .map_err(|_error| DebateError::runner_failure())
}

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------

/// Lexically absolute path (no symlink resolution), matching Python's
/// `_absolute_lexical`: an absolute path is returned verbatim; a relative path
/// is joined onto the current directory.
fn lexical_absolute(path: &str) -> PathBuf {
    let candidate = PathBuf::from(path);
    if candidate.is_absolute() {
        candidate
    } else {
        std::env::current_dir()
            .unwrap_or_else(|_error| PathBuf::from("."))
            .join(candidate)
    }
}

fn path_to_string(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

/// Ensure the trusted debate root exists and resolve it for confinement.
fn ensure_trusted_root(path: &str) -> Result<TemporaryRoot, StateError> {
    let lexical = lexical_absolute(path);
    ensure_directory_chain(&lexical)
        .map_err(|_error| StateError::persistence("unsafe debate directory"))?;
    TemporaryRoot::resolve(Some(&lexical))
        .map_err(|_error| StateError::persistence("unsafe debate directory"))
}

#[cfg(test)]
mod tests;
