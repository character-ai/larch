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
    DropRecord, InitializationContext, LIVE_PANEL_MINIMUM, MailboxEntry, ParticipantSlot, PointId,
    ReasonFingerprint, RestoreMetadata, RoundNumber, RoundState, SLOT_ORDER, STATE_FILENAME,
    SlotLedgerBinding, StateError, StoredState, TransitionAction, base64_encode, bootstrap_prompt,
    fingerprint_reason, is_safe_line, mailbox_entry, model_args, new_proposal, parse_slot,
    parse_slot_ledger, require_fingerprint, transition, turn_prompt,
};
use larch_core::{
    DebateSeat, VendorLaunchRequest, VendorProgram, VendorSessionHandle, build_codex_resume_argv,
    build_codex_session_argv, build_cursor_create_chat_argv, build_cursor_resume_argv,
    debate_panel_seating, parse_codex_session_id, parse_cursor_create_chat_id,
};
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};

use crate::external_agent::{ExternalAgentLaunch, ExternalAgentRouting, run_external_agent_launch};

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

/// Maximum recorded turn-output size in bytes (mirrors `DEBATE_TURN_OUTPUT_MAX_BYTES`).
const DEBATE_TURN_OUTPUT_MAX_BYTES: usize = 4 * 1024;
/// Drop reason: the turn runner failed.
const DROP_RUNNER_FAILURE: &str = "runner_failure";
/// Drop reason: the slot transport is unsupported.
const DROP_UNSUPPORTED_TRANSPORT: &str = "unsupported_transport";
/// Drop reason: the turn output was rejected by the protocol.
const DROP_PROTOCOL_REJECTION: &str = "protocol_rejection";
/// Filename of the abort restore handoff.
const ABORT_RESTORE_FILENAME: &str = "abort-restore.env";
/// Restore handoff key: tracking issue number.
const RESTORE_ISSUE_NUMBER_KEY: &str = "RESTORE_ISSUE_NUMBER";
/// Restore handoff key: original tracking-issue title.
const RESTORE_ORIGINAL_TITLE_KEY: &str = "RESTORE_ORIGINAL_TITLE";
/// Restore handoff key: restore tracking-issue title.
const RESTORE_TITLE_KEY: &str = "RESTORE_TITLE";
/// Restore handoff key: new source fingerprint.
const SOURCE_FINGERPRINT_KEY: &str = "SOURCE_FINGERPRINT";

/// The drop exit code for a drop reason token (mirrors `DEBATE_DROP_EXIT_CODES`).
fn drop_exit_code(reason: &str) -> i32 {
    match reason {
        DROP_RUNNER_FAILURE => EXIT_RUNNER_FAILURE,
        DROP_UNSUPPORTED_TRANSPORT => EXIT_UNSUPPORTED_TRANSPORT,
        _ => EXIT_VALIDATION,
    }
}

/// Whether `reason` is a recognized drop token carried by a runner failure.
fn is_drop_reason(reason: &str) -> bool {
    matches!(
        reason,
        DROP_RUNNER_FAILURE | DROP_UNSUPPORTED_TRANSPORT | DROP_PROTOCOL_REJECTION
    )
}

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
type Bootstrapper<'a> = &'a dyn Fn(
    &ParticipantSlot,
    &InitializationContext,
) -> Result<VendorSessionHandle, DebateError>;

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

/// `debate record-turn`
#[must_use]
pub fn record_turn(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_args(
        arguments,
        &[
            "--debate-tmpdir",
            "--expected-fingerprint",
            "--round",
            "--slot",
            "--input-file",
        ],
        &["--debate-tmpdir", "--expected-fingerprint", "--round", "--slot"],
    ) {
        Ok(parsed) => parsed,
        Err(error) => return finish("record-turn", Err(error)),
    };
    // `--input-file` selects the claude input runner; every other slot uses the
    // default cursor/codex runner. The trusted-root resolution and slot check
    // mirror Python `_record_turn_operation`.
    if let Some(input_file) = parsed.get("--input-file") {
        if parsed["--slot"] != "claude" {
            return finish("record-turn", Err(DebateError::validation()));
        }
        let debate_root_path = lexical_absolute(&parsed["--debate-tmpdir"]);
        let root = match TemporaryRoot::resolve(Some(&debate_root_path)) {
            Ok(root) => root,
            Err(_error) => return finish("record-turn", Err(DebateError::persistence())),
        };
        let input_file = input_file.clone();
        let runner = move |request: &TurnRequest| input_file_runner(&root, &input_file, request);
        return finish_turn(run_record_turn(&parsed, &runner));
    }
    finish_turn(run_record_turn(&parsed, &default_runner))
}

/// `debate abort`
#[must_use]
pub fn abort(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_args(
        arguments,
        &["--debate-tmpdir", "--expected-fingerprint"],
        &["--debate-tmpdir", "--expected-fingerprint"],
    ) {
        Ok(parsed) => parsed,
        Err(error) => return finish("abort", Err(error)),
    };
    finish("abort", run_abort(&parsed))
}

/// Emit the record-turn envelope, carrying a drop reason and exit code.
fn finish_turn(outcome: Result<TurnEnvelope, DebateError>) -> ExitCode {
    match outcome {
        Ok(turn) => {
            println!(
                "{}",
                envelope(
                    turn.slot_result.is_none(),
                    "record-turn",
                    Some(&turn.state),
                    turn.slot_result,
                    turn.slot_result,
                )
            );
            ExitCode::from(u8::try_from(turn.exit_code).unwrap_or(2))
        }
        Err(error) => finish("record-turn", Err(error)),
    }
}

/// Emit the operation envelope and map the outcome to an exit code.
fn finish(operation: &str, outcome: Result<StoredState, DebateError>) -> ExitCode {
    match outcome {
        Ok(state) => {
            println!("{}", envelope(true, operation, Some(&state), None, None));
            ExitCode::SUCCESS
        }
        Err(error) => {
            println!(
                "{}",
                envelope(false, operation, None, Some(error.error_class), None)
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
    slot_result: Option<&str>,
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
    let _ = object.insert(
        "slot_result".to_owned(),
        slot_result.map_or(Value::Null, |result| Value::String(result.to_owned())),
    );
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
            next.to_str()
                .ok_or_else(DebateError::validation)?
                .to_owned()
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
    let debate_root =
        ensure_trusted_root(debate_tmpdir).map_err(|_error| DebateError::validation())?;
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
    let warning = missing.first().map_or(String::new(), |slot| {
        format!("unavailable vendor: {}", slot.slot)
    });

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
    let proposal = new_proposal(&inputs.point_universe, &needles)
        .map_err(|_error| DebateError::validation())?;
    let stored = StoredState {
        initialization: context,
        proposal,
        proposal_run_local_values: values,
        active_round: None,
        drops: Vec::new(),
        fingerprint: String::new(),
    };
    Ok(larch_cli::debate_state::write_state(
        &debate_root_path,
        &stored,
    )?)
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
    Ok(larch_cli::debate_state::write_state(
        &debate_root_path,
        &stored,
    )?)
}

// ---------------------------------------------------------------------------
// record-turn and abort
// ---------------------------------------------------------------------------

/// One recorded turn's request passed to the runner (mirrors `TurnRequest`).
struct TurnRequest {
    prompt: String,
    workdir: PathBuf,
    output: PathBuf,
    session_handle: Option<VendorSessionHandle>,
    model: String,
}

/// One runner outcome (mirrors Python `TurnResult`).
struct TurnOutcome {
    ok: bool,
    output: Option<PathBuf>,
    error_class: Option<&'static str>,
}

impl TurnOutcome {
    const fn success(output: PathBuf) -> Self {
        Self {
            ok: true,
            output: Some(output),
            error_class: None,
        }
    }

    const fn drop(reason: &'static str) -> Self {
        Self {
            ok: false,
            output: None,
            error_class: Some(reason),
        }
    }
}

/// A recorded turn's persisted state plus its optional drop reason.
#[derive(Debug)]
struct TurnEnvelope {
    state: StoredState,
    slot_result: Option<&'static str>,
    exit_code: i32,
}

/// A record-turn runner, injected for tests (mirrors the [`Bootstrapper`] seam).
type Runner<'a> = &'a dyn Fn(&TurnRequest) -> TurnOutcome;

fn run_record_turn(
    parsed: &BTreeMap<String, String>,
    runner: Runner<'_>,
) -> Result<TurnEnvelope, DebateError> {
    let round_number: i64 = parsed["--round"]
        .trim()
        .parse()
        .map_err(|_error| DebateError::validation())?;
    let slot = parsed["--slot"].clone();
    let expected_fingerprint = &parsed["--expected-fingerprint"];
    let debate_root_path = lexical_absolute(&parsed["--debate-tmpdir"]);
    let debate_root =
        TemporaryRoot::resolve(Some(&debate_root_path)).map_err(|_error| DebateError::persistence())?;
    let _lock = larch_cli::debate_state::lock_state(&debate_root_path)?;
    let state = larch_cli::debate_state::load_state(&debate_root_path)?;
    require_fingerprint(&state, expected_fingerprint)?;

    let Some(active) = state.active_round.as_ref() else {
        return Err(DebateError::validation());
    };
    if !active.prepared
        || active.round_number != round_number
        || state.proposal.phase().is_none()
    {
        return Err(DebateError::validation());
    }
    if active.reserved_slot.is_some()
        || active.pending_slots.is_empty()
        || active.pending_slots[0] != slot
    {
        return Err(DebateError::validation());
    }
    if !active.live_slots.iter().any(|live| live == &slot) {
        return Err(DebateError::validation());
    }

    let handle = state.initialization.session_handles.get(&slot).cloned();
    let model = state
        .initialization
        .slots
        .iter()
        .find(|item| item.slot == slot)
        .map_or_else(String::new, |item| item.model.clone());
    let subject_encoded = state
        .initialization
        .run_local_values
        .get(DEBATE_SUBJECT_VALUE_KEY)
        .cloned()
        .unwrap_or_default();
    let mailbox = active.mailboxes.get(&slot).cloned().unwrap_or_default();
    let prompt = turn_prompt(
        &slot,
        round_number,
        &state.initialization.point_universe,
        &mailbox,
        &subject_encoded,
    )?;
    let output = debate_root.path().join(format!("{slot}-round-{round_number}.out"));
    let request = TurnRequest {
        prompt,
        workdir: PathBuf::from(&state.initialization.repo_workdir),
        output: output.clone(),
        session_handle: handle,
        model,
    };

    // Reserve the slot on disk before running the runner, so a crash mid-turn
    // cannot double-run the reserved slot.
    let reserved = ActiveRound {
        reserved_slot: Some(slot.clone()),
        ..active.clone()
    };
    let reserved_stored = StoredState {
        active_round: Some(reserved),
        fingerprint: String::new(),
        ..state.clone()
    };
    let reserved_state = larch_cli::debate_state::write_state(&debate_root_path, &reserved_stored)?;

    let outcome = runner(&request);
    if !outcome.ok || outcome.output.is_none() {
        let reason = outcome
            .error_class
            .filter(|reason| is_drop_reason(reason))
            .unwrap_or(DROP_RUNNER_FAILURE);
        return record_drop(&debate_root_path, &reserved_state, &slot, round_number, reason);
    }

    // Confine and parse the runner's output into a validated slot binding.
    let needles: Vec<&str> = reserved_state
        .proposal
        .run_local_values()
        .iter()
        .map(String::as_str)
        .collect();
    let Some(binding) = build_binding(&debate_root, &output, &slot, &needles) else {
        return record_drop(
            &debate_root_path,
            &reserved_state,
            &slot,
            round_number,
            DROP_PROTOCOL_REJECTION,
        );
    };

    let active_ref = reserved_state
        .active_round
        .as_ref()
        .ok_or_else(DebateError::validation)?;
    let mut completed = active_ref.bindings.clone();
    let _ = completed.insert(slot.clone(), binding);
    let pending: Vec<String> = active_ref
        .pending_slots
        .iter()
        .filter(|item| item.as_str() != slot)
        .cloned()
        .collect();

    let next_state = if pending.is_empty() {
        let bindings: Vec<SlotLedgerBinding> = SLOT_ORDER
            .iter()
            .filter_map(|item| completed.get(*item).cloned())
            .collect();
        let Some(round) = make_round(round_number, bindings) else {
            return record_drop(
                &debate_root_path,
                &reserved_state,
                &slot,
                round_number,
                DROP_PROTOCOL_REJECTION,
            );
        };
        let Ok(proposal) = transition(
            &reserved_state.proposal,
            TransitionAction::SubmitRound,
            Some(&round),
            None,
        ) else {
            return record_drop(
                &debate_root_path,
                &reserved_state,
                &slot,
                round_number,
                DROP_PROTOCOL_REJECTION,
            );
        };
        StoredState {
            proposal,
            active_round: None,
            fingerprint: String::new(),
            ..reserved_state.clone()
        }
    } else {
        let next_active = ActiveRound {
            round_number,
            prepared: true,
            mailboxes: active_ref.mailboxes.clone(),
            live_slots: active_ref.live_slots.clone(),
            pending_slots: pending,
            reserved_slot: None,
            bindings: completed,
        };
        StoredState {
            active_round: Some(next_active),
            fingerprint: String::new(),
            ..reserved_state.clone()
        }
    };
    let written = larch_cli::debate_state::write_state(&debate_root_path, &next_state)?;
    Ok(TurnEnvelope {
        state: written,
        slot_result: None,
        exit_code: 0,
    })
}

/// Drop `slot` from the reserved state, persist, and build the drop envelope.
fn record_drop(
    root: &Path,
    state: &StoredState,
    slot: &str,
    round_number: i64,
    reason: &'static str,
) -> Result<TurnEnvelope, DebateError> {
    let dropped = drop_slot(state, slot, round_number, reason);
    let written = larch_cli::debate_state::write_state(root, &dropped)?;
    Ok(TurnEnvelope {
        state: written,
        slot_result: Some(reason),
        exit_code: drop_exit_code(reason),
    })
}

/// Remove `slot` from the active round and sub-floor-abort (mirrors `_drop`).
fn drop_slot(state: &StoredState, slot: &str, round_number: i64, reason: &str) -> StoredState {
    let event_id = format!(
        "{:x}",
        Sha256::digest(
            format!("{}\0{slot}\0{round_number}\0{reason}", state.fingerprint).as_bytes()
        )
    );
    let Some(active) = state.active_round.as_ref() else {
        return state.clone();
    };
    let live: Vec<String> = active
        .live_slots
        .iter()
        .filter(|item| item.as_str() != slot)
        .cloned()
        .collect();
    let pending: Vec<String> = active
        .pending_slots
        .iter()
        .filter(|item| item.as_str() != slot)
        .cloned()
        .collect();
    let updated_active = ActiveRound {
        live_slots: live.clone(),
        pending_slots: pending,
        reserved_slot: None,
        ..active.clone()
    };
    let mut drops = state.drops.clone();
    drops.push(DropRecord {
        slot: slot.to_owned(),
        round_number,
        reason: reason.to_owned(),
        event_id,
    });
    let mut proposal = state.proposal.clone();
    if live.len() < LIVE_PANEL_MINIMUM
        && proposal.phase().is_some()
        && let Ok(aborted) = transition(&proposal, TransitionAction::Abort, None, None)
    {
        proposal = aborted;
    }
    StoredState {
        initialization: state.initialization.clone(),
        proposal,
        proposal_run_local_values: state.proposal_run_local_values.clone(),
        active_round: Some(updated_active),
        drops,
        fingerprint: String::new(),
    }
}

/// Read the confined turn output, cap its size, and bind it (mirrors the
/// record-turn output ladder). Any rejection yields `None` (protocol rejection).
fn build_binding(
    root: &TemporaryRoot,
    output: &Path,
    slot: &str,
    needles: &[&str],
) -> Option<SlotLedgerBinding> {
    let text = read_confined(root, output, false)?;
    if text.len() > DEBATE_TURN_OUTPUT_MAX_BYTES {
        return None;
    }
    let ledger = parse_slot_ledger(&text).ok()?;
    let fingerprints: Vec<ReasonFingerprint> = ledger
        .rows
        .iter()
        .map(|row| fingerprint_reason(&row.reason, needles))
        .collect::<Result<_, _>>()
        .ok()?;
    let participant = parse_slot(slot).ok()?;
    SlotLedgerBinding::new(participant, ledger, fingerprints, needles).ok()
}

/// Convert an integer round number to the protocol round enum.
fn make_round(round_number: i64, bindings: Vec<SlotLedgerBinding>) -> Option<RoundState> {
    let number = match round_number {
        1 => RoundNumber::Round1,
        2 => RoundNumber::Round2,
        _ => return None,
    };
    RoundState::new(number, bindings).ok()
}

/// Read one confined UTF-8 file below `root`, optionally rejecting CR.
fn read_confined(root: &TemporaryRoot, path: &Path, reject_cr: bool) -> Option<String> {
    let confined = root.confine(path, PathIntent::Read).ok()?;
    let text = read_utf8(&confined).ok()?;
    if reject_cr && text.contains('\r') {
        return None;
    }
    Some(text)
}

/// Extract Cursor's declared final-result field, strictly (mirrors
/// `_cursor_final_result`): the payload must be an object with a nonempty
/// string `result`.
fn cursor_final_result(raw: &str) -> Option<String> {
    let payload: Value = serde_json::from_str(raw).ok()?;
    let Value::Object(map) = payload else {
        return None;
    };
    match map.get("result") {
        Some(Value::String(result)) if !result.is_empty() => Some(result.clone()),
        _ => None,
    }
}

/// Drive one Cursor or Codex turn; every other transport is unsupported
/// (mirrors `_default_runner`).
fn default_runner(request: &TurnRequest) -> TurnOutcome {
    let Some(handle) = request.session_handle.as_ref() else {
        return TurnOutcome::drop(DROP_UNSUPPORTED_TRANSPORT);
    };
    let vendor = handle.vendor().as_str();
    if vendor != "cursor" && vendor != "codex" {
        return TurnOutcome::drop(DROP_UNSUPPORTED_TRANSPORT);
    }
    let Ok(model_arguments) = model_args(vendor, &request.model) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    let mut launch_request = VendorLaunchRequest::new(
        request.workdir.display().to_string(),
        request.output.display().to_string(),
        request.prompt.clone(),
    );
    launch_request.model_args = model_arguments;
    if vendor == "cursor" {
        run_cursor_turn(handle, &launch_request, request)
    } else {
        run_codex_turn(handle, &launch_request, request)
    }
}

/// Run a Cursor resume turn, extracting the final result to the output file.
fn run_cursor_turn(
    handle: &VendorSessionHandle,
    launch_request: &VendorLaunchRequest,
    request: &TurnRequest,
) -> TurnOutcome {
    let capture = request.output.with_extension("stdout");
    let Ok(argv) = build_cursor_resume_argv(handle, launch_request) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    let launch = ExternalAgentLaunch {
        tool: "cursor".to_owned(),
        output: capture.display().to_string(),
        timeout_seconds: VENDOR_TIMEOUT_SECONDS,
        command: argv.full_argv(),
        program: VendorProgram::Cursor,
        routing: ExternalAgentRouting::CaptureStdoutOnly,
        stderr_sink: None,
        working_directory: Some(request.workdir.clone()),
        environment: Vec::new(),
        sentinel_suffix: ".done",
        poll_interval: POLL_INTERVAL,
        stdin: None,
        stall_watch: None,
    };
    let Ok(outcome) = run_external_agent_launch(&launch) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    if outcome.exit_code != 0 {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    }
    let Some(root) = request
        .output
        .parent()
        .and_then(|parent| TemporaryRoot::resolve(Some(parent)).ok())
    else {
        return TurnOutcome::drop(DROP_PROTOCOL_REJECTION);
    };
    let Some(final_result) =
        read_confined(&root, &capture, false).and_then(|text| cursor_final_result(&text))
    else {
        return TurnOutcome::drop(DROP_PROTOCOL_REJECTION);
    };
    let Ok(confined) = root.confine(&request.output, PathIntent::Write) else {
        return TurnOutcome::drop(DROP_PROTOCOL_REJECTION);
    };
    if atomic_write_utf8_in(&root, confined.path(), &final_result, false, 0o600).is_err() {
        return TurnOutcome::drop(DROP_PROTOCOL_REJECTION);
    }
    TurnOutcome::success(request.output.clone())
}

/// Run a Codex resume turn; Codex writes its final message to the output file.
fn run_codex_turn(
    handle: &VendorSessionHandle,
    launch_request: &VendorLaunchRequest,
    request: &TurnRequest,
) -> TurnOutcome {
    let Ok(argv) = build_codex_resume_argv(handle, launch_request) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    let launch = ExternalAgentLaunch {
        tool: "codex".to_owned(),
        output: request.output.display().to_string(),
        timeout_seconds: VENDOR_TIMEOUT_SECONDS,
        command: argv.full_argv(),
        program: VendorProgram::Codex,
        routing: ExternalAgentRouting::CaptureCombined,
        stderr_sink: None,
        working_directory: Some(request.workdir.clone()),
        environment: Vec::new(),
        sentinel_suffix: ".done",
        poll_interval: POLL_INTERVAL,
        stdin: None,
        stall_watch: None,
    };
    let Ok(outcome) = run_external_agent_launch(&launch) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    if outcome.exit_code != 0 {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    }
    TurnOutcome::success(request.output.clone())
}

/// The claude `--input-file` runner (mirrors `_record_turn_operation`'s
/// `input_runner`): copy a confined input file to the turn output.
fn input_file_runner(root: &TemporaryRoot, input_file: &str, request: &TurnRequest) -> TurnOutcome {
    let Some(text) = read_confined(root, Path::new(input_file), true) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    if text.is_empty() || text.contains('\u{0}') || text.len() > DEBATE_TURN_OUTPUT_MAX_BYTES {
        return TurnOutcome::drop(DROP_PROTOCOL_REJECTION);
    }
    let Ok(confined) = root.confine(&request.output, PathIntent::Write) else {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    };
    if atomic_write_utf8_in(root, confined.path(), &text, false, 0o600).is_err() {
        return TurnOutcome::drop(DROP_RUNNER_FAILURE);
    }
    TurnOutcome::success(request.output.clone())
}

/// `debate abort`: terminal-abort when nonterminal, then write/verify the
/// restore handoff (mirrors Python `abort`).
fn run_abort(parsed: &BTreeMap<String, String>) -> Result<StoredState, DebateError> {
    let expected_fingerprint = &parsed["--expected-fingerprint"];
    let debate_root_path = lexical_absolute(&parsed["--debate-tmpdir"]);
    TemporaryRoot::resolve(Some(&debate_root_path)).map_err(|_error| DebateError::persistence())?;
    let _lock = larch_cli::debate_state::lock_state(&debate_root_path)?;
    let state = larch_cli::debate_state::load_state(&debate_root_path)?;
    require_fingerprint(&state, expected_fingerprint)?;

    let proposal = if state.proposal.phase().is_some() {
        transition(&state.proposal, TransitionAction::Abort, None, None)
            .map_err(|_error| DebateError::validation())?
    } else {
        state.proposal.clone()
    };
    let updated_stored = StoredState {
        proposal,
        fingerprint: String::new(),
        ..state
    };
    let updated = larch_cli::debate_state::write_state(&debate_root_path, &updated_stored)?;

    let restore = &updated.initialization.restore;
    let payload = format!(
        "{RESTORE_ISSUE_NUMBER_KEY}={}\n{RESTORE_ORIGINAL_TITLE_KEY}={}\n{RESTORE_TITLE_KEY}={}\n{SOURCE_FINGERPRINT_KEY}={}\n",
        restore.issue_number, restore.original_title, restore.restore_title, updated.fingerprint
    );
    let root = TemporaryRoot::resolve(Some(&debate_root_path))
        .map_err(|_error| DebateError::persistence())?;
    let handoff = root.path().join(ABORT_RESTORE_FILENAME);
    if handoff.exists() {
        let existing = read_confined(&root, &handoff, false).ok_or_else(DebateError::persistence)?;
        if existing != payload {
            return Err(DebateError::persistence());
        }
    } else {
        let confined = root
            .confine(&handoff, PathIntent::Write)
            .map_err(|_error| DebateError::persistence())?;
        atomic_write_utf8_in(&root, confined.path(), &payload, false, 0o600)
            .map_err(|_error| DebateError::persistence())?;
    }
    Ok(updated)
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
    if supplied != expected
        && supplied != lexical_absolute(debate_tmpdir).join(SOURCE_METADATA_FILENAME)
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
            request.model_args = model_args(&slot.tool, &slot.model).map_err(DebateError::from)?;
            let built = build_codex_session_argv(&request)
                .map_err(|_error| DebateError::runner_failure())?;
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
