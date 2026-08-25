//! The three-phase waterfall dispatcher that owns every external review slot.
//!
//! One slot manifest drives three ordered phases: the slot's primary vendor,
//! the opposite vendor, then Claude. Each phase launches every one of its slots
//! before a single collector pass reads them, so a slow slot never serializes
//! its siblings. Slots that no phase satisfies leave a per-slot drop record,
//! which the coverage gates downstream read instead of inferring loss from a
//! shortened path list.
//!
//! Child work runs through the verified bootstrap entrypoint, never through a
//! binary path and never through a launcher-local spawn: `ExternalProgram::Larch`
//! selects `scripts/larch.sh` from the validated plugin root, and the shared
//! process runner owns the process group, the deadline, and the teardown.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::{Arc, Mutex, PoisonError},
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

use larch_adapters::{
    NoopProcessObserver, PathIntent, ProcessFileRouting, TemporaryRoot, TokioProcessRunner,
    atomic_write_utf8_in,
    runtime::{Cancellation, LarchRuntime, cancel_on_shutdown_signal},
    vendor_diagnostics::write_failure_diag,
};
use larch_core::{
    ChildEnvironment, DuplicatePolicy, ExternalProgram, KvDocument, LarchProgram,
    LauncherArtifactKind, ParseOptions, ProcessRequest, SafeText, emit_kv,
};
use regex::Regex;
use serde_json::{Map, Value};

use crate::agent_commands::AgentRawArguments;
use crate::claude_commands::parse_uint;
use crate::collector_commands::{
    CollectorOptions, CollectorRecord, Publication, StructuredValidation, SubstantiveValidation,
    collect,
};
use crate::launcher_support::{
    LauncherArtifacts, confined_target, is_control_character, is_positive_int, parse_presence,
    validate_site, write_confined,
};
use crate::runtime_entrypoint::plugin_root_directory;

/// Decode a legacy `KEY=value` dispatch envelope with last-key-wins semantics.
///
/// Review command boundaries consume waterfall stdout directly, so they share
/// this codec instead of reimplementing the wire grammar.
pub fn parse_dispatch_kv(text: &str) -> BTreeMap<String, String> {
    let document = KvDocument::parse(text, ParseOptions::legacy())
        .expect("legacy dispatch envelope parser accepts every text input");
    document.select(DuplicatePolicy::Last)
}

/// Append the routing policy shared by reviewer-panel waterfall callers.
pub fn append_review_routing_arguments(
    arguments: &mut Vec<OsString>,
    site: &str,
    difficulty: &str,
    default_model: Option<&str>,
) {
    arguments.extend([
        "--site".into(),
        site.into(),
        "--model-role".into(),
        "review".into(),
        "--difficulty".into(),
        difficulty.into(),
        "--no-fallback".into(),
    ]);
    if let Some(model) = default_model {
        arguments.extend(["--default-model".into(), model.into()]);
    }
}

/// Program name every diagnostic and drop record still carries.
const PROG: &str = "dispatch-with-waterfall.sh";
/// Longest timing-ledger task kind one slot launch may record.
const TIMING_KIND_MAX: usize = 64;
/// Fewest slots in a phase before the adaptive straggler deadline may arm.
const MIN_STRAGGLER_PHASE_SLOTS: usize = 2;
/// Interval between slot-completion samples inside one phase.
const REAP_POLL_INTERVAL: Duration = Duration::from_millis(50);
/// Sentinel wait the collector uses when `--timeout` is unparseable.
const DEFAULT_COLLECTOR_TIMEOUT: u64 = 1800;
/// Grace a cancelled slot child gets before its process group is killed.
const LAUNCH_SHUTDOWN_GRACE: Duration = Duration::from_secs(1);
/// Backstop above `--timeout` before the runner terminates a slot child itself.
///
/// The launcher enforces the real deadline; this only bounds a wedged child so
/// one slot cannot hold the dispatcher open forever.
const LAUNCH_TIMEOUT_MARGIN: Duration = Duration::from_secs(600);
/// Longest wait for slot teardown after an operating-system shutdown signal.
const SHUTDOWN_DRAIN: Duration = Duration::from_secs(5);
/// Exit code a terminated dispatch reports, matching the retired signal handler.
const SHUTDOWN_EXIT_CODE: u8 = 143;
/// Exit code recorded for a slot child the dispatcher terminated.
const TERMINATED_EXIT_CODE: i32 = -15;
/// Bounded capture for one collector invocation's standard streams.
const COLLECTOR_OUTPUT_LIMIT: usize = 256 * 1024;
/// Longest drop snippet preserved from a rejected row or an unusable result.
const SNIPPET_CHARS: usize = 200;
/// Bytes read from a result file before a drop snippet is composed.
const SNIPPET_SOURCE_BYTES: usize = 2000;
/// Default straggler deadline multiple applied to the half-mark anchor.
const STRAGGLER_MULTIPLE_DEFAULT: f64 = 2.5;
/// Shortest straggler deadline, in seconds.
const STRAGGLER_FLOOR_SECONDS_DEFAULT: u64 = 300;
/// Longest straggler deadline, in seconds.
const STRAGGLER_MAX_SECONDS_DEFAULT: u64 = 900;
/// Claude fallback count above which the dispatch warns about cost.
const FALLBACK_WARN_THRESHOLD_DEFAULT: u64 = 3;

const USAGE: &str = concat!(
    "Usage: dispatch-with-waterfall.sh --slots-file FILE --codex-present true|false ",
    "--cursor-present true|false --mode diff|description [--paths-file FILE] [--skip-invalid-slots] [--site SITE] [context flags]. ",
    "Default paths-file is SLOTS_FILE.output-files; its parent directory must already exist. ",
    "--straggler-cutoff enables the adaptive reviewer straggler deadline for this dispatch. ",
    "--model-role default|review|vote|fix forwards an explicit Codex model role to Codex launches. ",
    "--default-model forwards a non-empty Codex model default after env overrides and before role defaults. ",
    "--difficulty forwards the applied difficulty tier to prompt renderers. ",
    "Stdout KVs include ALL_OUTPUT_FILES_PATH, ALL_OUTPUT_FILES, ALL_OUTPUT_TOOLS, DISPATCH_OK, WARN, …",
);

/// The vendor one slot launch drives.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LaunchTool {
    /// Codex, the primary vendor for most reviewer archetypes.
    Codex,
    /// Cursor, the opposite vendor in the cross-vendor phase.
    Cursor,
    /// Claude, the terminal fallback that never runs in phase one.
    Claude,
}

impl LaunchTool {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Codex => "codex",
            Self::Cursor => "cursor",
            Self::Claude => "claude",
        }
    }

    const fn opposite(self) -> Self {
        match self {
            Self::Codex => Self::Cursor,
            Self::Cursor | Self::Claude => Self::Codex,
        }
    }
}

/// One of the three ordered dispatch phases.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    /// The slot's declared primary vendor.
    One,
    /// The opposite vendor.
    Two,
    /// The terminal Claude fallback.
    Three,
}

impl Phase {
    const fn as_str(self) -> &'static str {
        match self {
            Self::One => "phase1",
            Self::Two => "phase2",
            Self::Three => "phase3",
        }
    }
}

/// One manifest row, already validated against the slot-row grammar.
#[derive(Clone, Debug)]
struct Slot {
    name: String,
    tool: LaunchTool,
    output: String,
    agent: String,
    prompt_file: String,
    model_role: String,
    cursor_model: String,
    prompt_files: Option<BTreeMap<String, String>>,
    payload_bytes: i64,
    payload_files: Option<BTreeMap<String, i64>>,
}

/// One manifest row rejected under `--skip-invalid-slots`.
#[derive(Clone, Debug)]
struct InvalidSlotDrop {
    line: usize,
    slot: String,
    snippet: String,
    message: String,
}

/// Why one slot left the dispatch without a usable result.
#[derive(Clone, Debug, Default)]
struct DropState {
    reason: String,
    detail: String,
}

impl DropState {
    fn new(reason: &str, detail: impl Into<String>) -> Self {
        Self {
            reason: reason.to_owned(),
            detail: detail.into(),
        }
    }
}

/// Every option the dispatch grammar accepts.
#[derive(Clone, Debug, Default)]
#[allow(clippy::struct_excessive_bools)] // one field per flag in the retired grammar
struct Options {
    slots_file: String,
    codex_present: bool,
    cursor_present: bool,
    mode: String,
    diff_file: String,
    commit_count: String,
    plan_file: String,
    feature_file: String,
    scope_files: String,
    description_text: String,
    timeout: String,
    fallback_counter_file: String,
    competition_notice: bool,
    competition_notice_file: String,
    paths_file: String,
    require_result_pattern: String,
    require_first_line_pattern: String,
    no_fallback: bool,
    straggler_cutoff: bool,
    skip_invalid_slots: bool,
    site: String,
    session_env_path: String,
    model_role: String,
    default_model: String,
    difficulty: String,
    claude_read_tools_add_dir: String,
    panel_artifact_dir: String,
    panel_round_num: String,
    panel_source_agent_file: String,
}

/// The result-acceptance gates one dispatch applies to every collected slot.
struct ResultGates {
    result: Option<Regex>,
    first_line: Option<Regex>,
}

/// Run `agent dispatch-waterfall`.
pub fn dispatch_waterfall(arguments: &AgentRawArguments) -> ExitCode {
    match parse_arguments(&arguments.arguments) {
        Ok(ParsedArguments::Help) => {
            eprintln!("{USAGE}");
            ExitCode::SUCCESS
        }
        Ok(ParsedArguments::Unknown(option)) => {
            refuse(&format!("{PROG}: unknown option: {option}"));
            eprintln!("{USAGE}");
            ExitCode::from(2)
        }
        Ok(ParsedArguments::Options(options)) => run_dispatch(&options),
        Err(message) => {
            refuse(&message);
            ExitCode::from(2)
        }
    }
}

/// The result of one in-process waterfall dispatch.
///
/// Review and plan-review dispatch commands invoke this layer directly.
/// Keeping the result structured lets those commands retain their legacy
/// envelopes without spawning another larch process or recapturing stdout.
#[derive(Clone, Debug, Default)]
#[allow(clippy::struct_excessive_bools)] // Legacy stdout exposes these independent per-panel outcomes.
pub struct WaterfallDispatchOutcome {
    phase1_slots: Vec<String>,
    phase2_slots: Vec<String>,
    phase3_slots: Vec<String>,
    pub(crate) all_output_files: Vec<String>,
    pub(crate) all_output_tools: Vec<String>,
    pub(crate) paths_file: String,
    pub(crate) dropped_slots_file: String,
    fallback_count: u64,
    pub(crate) straggler_dropped_count: usize,
    pub(crate) invalid_slot_drop_count: usize,
    pub(crate) invalid_slots_file: String,
    pub(crate) warning: String,
    pub(crate) dispatch_ok: bool,
    pub(crate) static_dispatch_ok: bool,
    pub(crate) dynamic_dispatch_ok: bool,
    all_slots_dropped: bool,
}

/// Dispatch a review panel through the sole waterfall launch owner.
///
/// This deliberately accepts the same raw grammar as `agent
/// dispatch-waterfall`, but returns the report instead of emitting its own
/// stdout envelope. Vendor processes still start only in this module.
pub fn dispatch_for_review(arguments: &[OsString]) -> Result<WaterfallDispatchOutcome, String> {
    let options = match parse_arguments(arguments)? {
        ParsedArguments::Options(options) => options,
        ParsedArguments::Help => {
            return Err("dispatch-waterfall help is not a dispatch request".to_owned());
        }
        ParsedArguments::Unknown(option) => {
            return Err(format!("{PROG}: unknown option: {option}"));
        }
    };
    let registry = LaunchRegistry::create();
    let outcome = dispatch(&options, &registry);
    registry.terminate_all();
    if registry.is_cancelled() {
        return Err("dispatch-with-waterfall.sh: dispatch cancelled".to_owned());
    }
    outcome
}

fn run_dispatch(options: &Options) -> ExitCode {
    let registry = LaunchRegistry::create();
    let outcome = dispatch(options, &registry);
    registry.terminate_all();
    if registry.is_cancelled() {
        // A shutdown signal reached this dispatch. Report the terminated exit
        // here rather than racing the watchdog's own drain-then-exit.
        return ExitCode::from(SHUTDOWN_EXIT_CODE);
    }
    match outcome {
        Ok(outcome) => {
            emit_report(&outcome);
            ExitCode::SUCCESS
        }
        Err(message) => {
            refuse(&message);
            ExitCode::from(2)
        }
    }
}

/// Report one operator-facing refusal, redacted like the retired diagnostic.
fn refuse(message: &str) {
    eprintln!("{}", SafeText::diagnostic(message));
}

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

/// What the dispatch grammar resolved one argument vector to.
enum ParsedArguments {
    /// A complete, validated option set.
    Options(Box<Options>),
    /// `--help`, which prints the usage line and succeeds.
    Help,
    /// An option outside the grammar, reported with the usage line.
    Unknown(String),
}

/// Resolve the string field one value-taking flag writes, if the flag exists.
fn value_field<'a>(raw: &'a mut RawOptions, flag: &str) -> Option<&'a mut String> {
    let options = &mut raw.options;
    let field = match flag {
        "--slots-file" => &mut options.slots_file,
        "--mode" => &mut options.mode,
        "--diff-file" => &mut options.diff_file,
        "--commit-count" => &mut options.commit_count,
        "--plan-file" => &mut options.plan_file,
        "--feature-file" => &mut options.feature_file,
        "--scope-files" => &mut options.scope_files,
        "--description-text" => &mut options.description_text,
        "--timeout" => &mut options.timeout,
        "--fallback-counter-file" => &mut options.fallback_counter_file,
        "--competition-notice-file" => &mut options.competition_notice_file,
        "--paths-file" => &mut options.paths_file,
        "--require-result-pattern" => &mut options.require_result_pattern,
        "--require-first-line-pattern" => &mut options.require_first_line_pattern,
        "--site" => &mut options.site,
        "--session-env-path" => &mut options.session_env_path,
        "--model-role" => &mut options.model_role,
        "--default-model" => &mut options.default_model,
        "--difficulty" => &mut options.difficulty,
        "--claude-read-tools-add-dir" => &mut options.claude_read_tools_add_dir,
        "--panel-artifact-dir" => &mut options.panel_artifact_dir,
        "--panel-round-num" => &mut options.panel_round_num,
        "--panel-source-agent-file" => &mut options.panel_source_agent_file,
        "--codex-present" | "--codex-available" => &mut raw.codex_present,
        "--cursor-present" | "--cursor-available" => &mut raw.cursor_present,
        _ => return None,
    };
    Some(field)
}

/// The option set before the two tristate presence flags are decoded.
struct RawOptions {
    options: Options,
    codex_present: String,
    cursor_present: String,
}

fn parse_arguments(arguments: &[OsString]) -> Result<ParsedArguments, String> {
    let mut raw = RawOptions {
        options: Options {
            timeout: "1800".to_owned(),
            site: "review Step 2".to_owned(),
            ..Options::default()
        },
        codex_present: String::new(),
        cursor_present: String::new(),
    };
    let mut index = 0;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy().into_owned();
        match argument.as_str() {
            "--competition-notice" => raw.options.competition_notice = true,
            "--no-fallback" => raw.options.no_fallback = true,
            "--straggler-cutoff" => raw.options.straggler_cutoff = true,
            "--skip-invalid-slots" => raw.options.skip_invalid_slots = true,
            "--help" => return Ok(ParsedArguments::Help),
            _ => {
                if value_field(&mut raw, &argument).is_none() {
                    return Ok(ParsedArguments::Unknown(argument));
                }
                let Some(value) = arguments.get(index + 1) else {
                    return Err(missing_value_message(&argument));
                };
                let owned = value.to_string_lossy().into_owned();
                if let Some(field) = value_field(&mut raw, &argument) {
                    *field = owned;
                }
                index += 1;
            }
        }
        index += 1;
    }
    validate_options(raw).map(|options| ParsedArguments::Options(Box::new(options)))
}

fn missing_value_message(flag: &str) -> String {
    let reported = match flag {
        "--codex-present" | "--codex-available" => "--codex-present",
        "--cursor-present" | "--cursor-available" => "--cursor-present",
        other => other,
    };
    format!("{PROG}: {reported} requires a value")
}

fn validate_options(raw: RawOptions) -> Result<Options, String> {
    let mut options = raw.options;
    if options.slots_file.is_empty() || !Path::new(&options.slots_file).is_file() {
        return Err(format!("{PROG}: --slots-file must name a file"));
    }
    options.codex_present = parse_presence(PROG, "--codex-present", &raw.codex_present)?;
    options.cursor_present = parse_presence(PROG, "--cursor-present", &raw.cursor_present)?;
    if options.mode != "diff" && options.mode != "description" {
        return Err(format!("{PROG}: --mode must be diff or description"));
    }
    if !is_positive_int(&options.timeout) {
        return Err(format!("{PROG}: --timeout must be a positive integer"));
    }
    validate_site(PROG, &options.site)?;
    if !options.model_role.is_empty() && !is_model_role(&options.model_role) {
        return Err(format!(
            "{PROG}: --model-role must be default, review, vote, or fix"
        ));
    }
    Ok(options)
}

fn is_model_role(value: &str) -> bool {
    matches!(value, "default" | "review" | "vote" | "fix")
}

/// Compile one caller-supplied POSIX extended regular expression.
///
/// The retired dispatcher rewrote POSIX classes into Python escapes; the Rust
/// engine accepts `[[:class:]]` directly, so the raw pattern compiles as given
/// with the multi-line anchoring the callers already relied on.
fn compile_pattern(raw: &str, flag: &str) -> Result<Option<Regex>, String> {
    if raw.is_empty() {
        return Ok(None);
    }
    Regex::new(&format!("(?m){raw}"))
        .map(Some)
        .map_err(|_error| format!("{PROG}: {flag} is not a valid ERE: {raw}"))
}

// ---------------------------------------------------------------------------
// Slot-row parsing
// ---------------------------------------------------------------------------

fn invalid_row_message(row: &str) -> String {
    format!("{PROG}: invalid slot row: {row}")
}

fn slot_message(slot: &str, detail: &str) -> String {
    format!("{PROG}: slot '{slot}' {detail}")
}

fn parse_prompt_files(
    raw: Option<&Value>,
    slot: &str,
) -> Result<Option<BTreeMap<String, String>>, String> {
    let Some(value) = raw.filter(|value| !value.is_null()) else {
        return Ok(None);
    };
    let Some(object) = value.as_object() else {
        return Err(slot_message(slot, "prompt_files must be an object"));
    };
    let mut parsed = BTreeMap::new();
    for (key, entry) in object {
        if !matches!(key.as_str(), "claude" | "codex" | "cursor") {
            return Err(slot_message(
                slot,
                "prompt_files keys must be claude, codex, or cursor",
            ));
        }
        let text = entry
            .as_str()
            .filter(|text| !text.trim().is_empty())
            .ok_or_else(|| slot_message(slot, "prompt_files values must be non-empty strings"))?;
        let _replaced = parsed.insert(key.clone(), text.to_owned());
    }
    if parsed.is_empty() {
        return Err(slot_message(slot, "prompt_files must not be empty"));
    }
    Ok(Some(parsed))
}

fn parse_nonnegative_int(raw: Option<&Value>, slot: &str, field: &str) -> Result<i64, String> {
    let reject = || slot_message(slot, &format!("{field} must be a non-negative integer"));
    match raw {
        None | Some(Value::Null) => Ok(0),
        Some(Value::Number(number)) => number
            .as_i64()
            .filter(|value| *value >= 0)
            .ok_or_else(reject),
        Some(Value::String(text)) => {
            let trimmed = text.trim();
            if trimmed.is_empty() && text.is_empty() {
                return Ok(0);
            }
            if !trimmed.is_empty() && trimmed.bytes().all(|byte| byte.is_ascii_digit()) {
                return trimmed.parse::<i64>().map_err(|_error| reject());
            }
            Err(reject())
        }
        Some(_) => Err(reject()),
    }
}

fn parse_payload_files(
    raw: Option<&Value>,
    slot: &str,
) -> Result<Option<BTreeMap<String, i64>>, String> {
    let Some(value) = raw.filter(|value| !value.is_null()) else {
        return Ok(None);
    };
    let Some(object) = value.as_object() else {
        return Err(slot_message(slot, "payload_files must be an object"));
    };
    let mut parsed = BTreeMap::new();
    for (key, entry) in object {
        if !matches!(key.as_str(), "claude" | "codex" | "cursor") {
            return Err(slot_message(
                slot,
                "payload_files keys must be claude, codex, or cursor",
            ));
        }
        let bytes = parse_nonnegative_int(Some(entry), slot, &format!("payload_files.{key}"))?;
        let _replaced = parsed.insert(key.clone(), bytes);
    }
    if parsed.is_empty() {
        return Err(slot_message(slot, "payload_files must not be empty"));
    }
    Ok(Some(parsed))
}

fn parse_model_role(raw: Option<&Value>, slot: &str, row: &str) -> Result<String, String> {
    match raw {
        None | Some(Value::Null) => Ok(String::new()),
        Some(Value::String(value)) => {
            if value.is_empty() || is_model_role(value) {
                Ok(value.clone())
            } else {
                Err(slot_message(
                    slot,
                    "model_role must be default, review, vote, or fix",
                ))
            }
        }
        Some(_) => Err(invalid_row_message(row)),
    }
}

fn parse_cursor_model(raw: Option<&Value>, slot: &str, row: &str) -> Result<String, String> {
    match raw {
        None | Some(Value::Null) => Ok(String::new()),
        Some(Value::String(value)) => {
            if value.trim().is_empty() {
                return Err(slot_message(
                    slot,
                    "cursor_model must be a non-empty string",
                ));
            }
            if value.chars().any(is_control_character) {
                return Err(slot_message(
                    slot,
                    "cursor_model must not contain control characters",
                ));
            }
            Ok(value.clone())
        }
        Some(_) => Err(invalid_row_message(row)),
    }
}

fn validate_prompt_sources(
    slot: &str,
    agent: &str,
    prompt_file: &str,
    prompt_files: Option<&BTreeMap<String, String>>,
) -> Result<(), String> {
    let has_prompt_source = !prompt_file.is_empty() || prompt_files.is_some();
    if !agent.is_empty() && has_prompt_source {
        if !prompt_file.is_empty() && prompt_files.is_none() {
            return Err(slot_message(
                slot,
                "must not set both agent and prompt_file",
            ));
        }
        return Err(slot_message(
            slot,
            "must not set both agent and prompt source",
        ));
    }
    if agent.is_empty() && !has_prompt_source {
        return Err(slot_message(slot, "must set either agent or prompt_file"));
    }
    Ok(())
}

fn optional_string(data: &Map<String, Value>, key: &str, row: &str) -> Result<String, String> {
    match data.get(key) {
        None | Some(Value::Null) => Ok(String::new()),
        Some(Value::String(value)) => Ok(value.clone()),
        Some(_) => Err(invalid_row_message(row)),
    }
}

fn parse_slot_row(row: &str) -> Result<Slot, String> {
    let value: Value = serde_json::from_str(row).map_err(|_error| invalid_row_message(row))?;
    let data = value.as_object().ok_or_else(|| invalid_row_message(row))?;
    let name = data
        .get("slot")
        .and_then(Value::as_str)
        .filter(|name| !name.is_empty())
        .ok_or_else(|| invalid_row_message(row))?
        .to_owned();
    let tool = match data.get("tool").and_then(Value::as_str) {
        Some("codex") => LaunchTool::Codex,
        Some("cursor") => LaunchTool::Cursor,
        _ => return Err(invalid_row_message(row)),
    };
    let output = data
        .get("output")
        .and_then(Value::as_str)
        .filter(|output| !output.is_empty())
        .ok_or_else(|| invalid_row_message(row))?
        .to_owned();
    if output.contains(['\n', '\r']) {
        return Err(format!(
            "{PROG}: slot '{name}' output path contains a newline or carriage return (line-oriented paths-file contract)"
        ));
    }
    let agent = optional_string(data, "agent", row)?;
    let prompt_file = optional_string(data, "prompt_file", row)?;
    let prompt_files = parse_prompt_files(data.get("prompt_files"), &name)?;
    validate_prompt_sources(&name, &agent, &prompt_file, prompt_files.as_ref())?;
    let model_role = parse_model_role(data.get("model_role"), &name, row)?;
    let cursor_model = parse_cursor_model(data.get("cursor_model"), &name, row)?;
    if !cursor_model.is_empty() && tool != LaunchTool::Cursor {
        return Err(slot_message(
            &name,
            "cursor_model is only valid for cursor slots",
        ));
    }
    let payload_bytes = parse_nonnegative_int(data.get("payload_bytes"), &name, "payload_bytes")?;
    let payload_files = parse_payload_files(data.get("payload_files"), &name)?;
    Ok(Slot {
        name,
        tool,
        output,
        agent,
        prompt_file,
        model_role,
        cursor_model,
        prompt_files,
        payload_bytes,
        payload_files,
    })
}

fn invalid_drop_for_row(line: usize, row: &str, message: String) -> InvalidSlotDrop {
    let slot = serde_json::from_str::<Value>(row)
        .ok()
        .and_then(|value| {
            value
                .get("slot")
                .and_then(Value::as_str)
                .filter(|slot| !slot.is_empty())
                .map(str::to_owned)
        })
        .unwrap_or_default();
    InvalidSlotDrop {
        line,
        slot,
        snippet: truncate_chars(&flatten_field(row), SNIPPET_CHARS),
        message,
    }
}

fn load_slots(
    slots_file: &str,
    skip_invalid: bool,
) -> Result<(Vec<Slot>, Vec<InvalidSlotDrop>), String> {
    let text = fs::read(slots_file)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|_error| format!("{PROG}: --slots-file must name a file"))?;
    let mut slots = Vec::new();
    let mut invalid = Vec::new();
    for (offset, row) in text.lines().enumerate() {
        if row.is_empty() {
            continue;
        }
        match parse_slot_row(row) {
            Ok(slot) => slots.push(slot),
            Err(message) => {
                if !skip_invalid {
                    return Err(message);
                }
                invalid.push(invalid_drop_for_row(offset + 1, row, message));
            }
        }
    }
    if slots.is_empty() && (!skip_invalid || invalid.is_empty()) {
        return Err(format!("{PROG}: slots file contains no slot rows"));
    }
    Ok((slots, invalid))
}

// ---------------------------------------------------------------------------
// Text helpers
// ---------------------------------------------------------------------------

fn flatten_field(text: &str) -> String {
    text.replace(['\t', '\n', '\r'], " ")
}

fn truncate_chars(text: &str, limit: usize) -> String {
    text.chars().take(limit).collect()
}

fn snippet_from_file(path: &Path) -> String {
    let Ok(bytes) = fs::read(path) else {
        return String::new();
    };
    let head = &bytes[..bytes.len().min(SNIPPET_SOURCE_BYTES)];
    truncate_chars(
        &flatten_field(&String::from_utf8_lossy(head)),
        SNIPPET_CHARS,
    )
}

fn first_nonblank_trimmed(text: &str) -> String {
    text.lines()
        .find(|line| !line.trim().is_empty())
        .map(|line| line.trim().to_owned())
        .unwrap_or_default()
}

fn read_lossy(path: &Path) -> Option<String> {
    fs::read(path)
        .ok()
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn output_for_phase(base: &str, phase: Phase) -> String {
    match phase {
        Phase::One => base.to_owned(),
        Phase::Two | Phase::Three => base.strip_suffix(".txt").map_or_else(
            || format!("{base}-{}", phase.as_str()),
            |stem| format!("{stem}-{}.txt", phase.as_str()),
        ),
    }
}

fn timing_kind(tool: LaunchTool, phase: Phase, slot_name: &str) -> String {
    let kind = format!("{}-{}-{slot_name}", tool.as_str(), phase.as_str());
    if kind.chars().count() <= TIMING_KIND_MAX {
        return kind;
    }
    truncate_chars(&kind, TIMING_KIND_MAX)
        .trim_end_matches('-')
        .to_owned()
}

// ---------------------------------------------------------------------------
// Slot launches
// ---------------------------------------------------------------------------

/// One running slot child and everything the dispatcher needs to reap it.
struct Launch {
    index: usize,
    output: String,
    tool: LaunchTool,
    cancellation: Cancellation,
    exit_code: Arc<Mutex<Option<i32>>>,
    handle: Mutex<Option<JoinHandle<()>>>,
}

impl Launch {
    fn poll(&self) -> Option<i32> {
        *self
            .exit_code
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
    }

    /// Terminate this launch's process group and wait for its worker thread.
    fn terminate(&self) {
        self.cancellation.cancel();
        let worker = self
            .handle
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .take();
        if let Some(handle) = worker {
            let _joined = handle.join();
        }
    }
}

/// Every launch this process started, so a shutdown signal reaches all of them.
struct LaunchRegistry {
    root: Cancellation,
    launches: Mutex<Vec<Arc<Launch>>>,
}

impl LaunchRegistry {
    /// Create the registry and arm the shutdown watchdog that drains it.
    fn create() -> Arc<Self> {
        let registry = Arc::new(Self {
            root: Cancellation::new(),
            launches: Mutex::new(Vec::new()),
        });
        spawn_shutdown_watchdog(Arc::clone(&registry));
        registry
    }

    fn register(&self, launch: &Arc<Launch>) {
        self.launches
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .push(Arc::clone(launch));
    }

    fn take_all(&self) -> Vec<Arc<Launch>> {
        std::mem::take(&mut *self.launches.lock().unwrap_or_else(PoisonError::into_inner))
    }

    fn terminate_all(&self) {
        for launch in self.take_all() {
            launch.terminate();
        }
    }

    fn is_cancelled(&self) -> bool {
        self.root.is_cancelled()
    }
}

/// Cancel every live slot child when the operating system asks us to stop.
///
/// The retired dispatcher installed a `SIGTERM` handler plus an exit hook so an
/// interrupted dispatch left no orphan. The shared runtime already owns signal
/// registration, so this waits on it and drains the registry before exiting.
fn spawn_shutdown_watchdog(registry: Arc<LaunchRegistry>) {
    let _worker = thread::spawn(move || {
        let Ok(runtime) = LarchRuntime::current_thread() else {
            return;
        };
        if runtime
            .block_on(cancel_on_shutdown_signal(&registry.root))
            .is_err()
        {
            return;
        }
        let launches = registry.take_all();
        let deadline = Instant::now() + SHUTDOWN_DRAIN;
        while Instant::now() < deadline && launches.iter().any(|launch| launch.poll().is_none()) {
            thread::sleep(REAP_POLL_INTERVAL);
        }
        std::process::exit(i32::from(SHUTDOWN_EXIT_CODE));
    });
}

fn prompt_file_for_tool(slot: &Slot, tool: LaunchTool) -> Option<&str> {
    slot.prompt_files.as_ref().map_or_else(
        || Some(slot.prompt_file.as_str()).filter(|value| !value.trim().is_empty()),
        |files| {
            files
                .get(tool.as_str())
                .map(String::as_str)
                .filter(|value| !value.trim().is_empty())
        },
    )
}

fn payload_bytes_for_tool(slot: &Slot, tool: LaunchTool) -> i64 {
    slot.payload_files
        .as_ref()
        .map_or(slot.payload_bytes, |files| {
            files.get(tool.as_str()).copied().unwrap_or_default()
        })
}

fn can_launch_with_prompt(slot: &Slot, tool: LaunchTool) -> bool {
    !slot.agent.is_empty() || prompt_file_for_tool(slot, tool).is_some()
}

fn common_arguments(options: &Options) -> Vec<String> {
    let mut arguments = Vec::new();
    for (flag, value) in [
        ("--diff-file", &options.diff_file),
        ("--commit-count", &options.commit_count),
        ("--plan-file", &options.plan_file),
        ("--feature-file", &options.feature_file),
        ("--scope-files", &options.scope_files),
        ("--description-text", &options.description_text),
        ("--difficulty", &options.difficulty),
    ] {
        if !value.is_empty() {
            arguments.push(flag.to_owned());
            arguments.push(value.clone());
        }
    }
    if !options.session_env_path.is_empty() {
        arguments.push("--session-env-path".to_owned());
        arguments.push(options.session_env_path.clone());
    }
    arguments
}

/// Build the bootstrap argv one slot launch runs.
fn launch_arguments(
    slot: &Slot,
    options: &Options,
    phase: Phase,
    tool: LaunchTool,
    output: &str,
) -> Vec<String> {
    let prompt_file = prompt_file_for_tool(slot, tool);
    let mut argv = vec!["agent".to_owned()];
    if tool == LaunchTool::Claude {
        argv.push("launch-claude-review".to_owned());
        argv.extend(["--output".to_owned(), output.to_owned()]);
    } else {
        argv.push("launch-review".to_owned());
        argv.extend([
            "--tool".to_owned(),
            tool.as_str().to_owned(),
            "--output".to_owned(),
            output.to_owned(),
        ]);
    }
    match prompt_file {
        Some(path) => argv.extend(["--prompt-file".to_owned(), path.to_owned()]),
        None => argv.extend(["--agent-file".to_owned(), slot.agent.clone()]),
    }
    if tool == LaunchTool::Claude && !options.claude_read_tools_add_dir.is_empty() {
        argv.extend([
            "--read-tools-add-dir".to_owned(),
            options.claude_read_tools_add_dir.clone(),
        ]);
    }
    argv.extend([
        "--mode".to_owned(),
        options.mode.clone(),
        "--timeout".to_owned(),
        options.timeout.clone(),
        "--timing-task-kind".to_owned(),
        timing_kind(tool, phase, &slot.name),
    ]);
    argv.extend(common_arguments(options));
    if tool != LaunchTool::Claude {
        argv.extend(vendor_launch_arguments(slot, options, tool));
    }
    argv
}

fn vendor_launch_arguments(slot: &Slot, options: &Options, tool: LaunchTool) -> Vec<String> {
    let mut argv = vec!["--site".to_owned(), options.site.clone()];
    if options.competition_notice {
        argv.push("--competition-notice".to_owned());
    }
    if !options.competition_notice_file.is_empty() {
        argv.extend([
            "--competition-notice-file".to_owned(),
            options.competition_notice_file.clone(),
        ]);
    }
    if tool == LaunchTool::Codex {
        let role = if slot.model_role.is_empty() {
            &options.model_role
        } else {
            &slot.model_role
        };
        if !role.is_empty() {
            argv.extend(["--model-role".to_owned(), role.clone()]);
        }
        if !options.default_model.is_empty() {
            argv.extend(["--default-model".to_owned(), options.default_model.clone()]);
        }
    } else if tool == LaunchTool::Cursor && !slot.cursor_model.is_empty() {
        argv.extend(["--cursor-model".to_owned(), slot.cursor_model.clone()]);
    }
    argv
}

/// The panel-context rows one slot launch publishes to its child.
///
/// The retired dispatcher composed a full child environment; the typed process
/// layer takes overrides instead, so the same panel keys are published as rows
/// and an absent payload size stays absent rather than leaking an inherited one.
fn panel_dispatch_rows(
    artifact_dir: &Path,
    options: &Options,
    slot: &Slot,
    phase: Phase,
    tool: LaunchTool,
) -> Vec<(ChildEnvironment, OsString)> {
    let round_dir = round_directory(artifact_dir);
    let source_agent = if !options.panel_source_agent_file.is_empty() {
        options.panel_source_agent_file.clone()
    } else if slot.agent.is_empty() {
        env::var("LARCH_PANEL_SOURCE_AGENT_FILE").unwrap_or_default()
    } else {
        slot.agent.clone()
    };
    let mut rows = vec![
        (
            ChildEnvironment::LarchPanelArtifactDir,
            artifact_dir.as_os_str().to_owned(),
        ),
        (
            ChildEnvironment::LarchPanelSite,
            OsString::from(&options.site),
        ),
        (ChildEnvironment::LarchPanelSlot, OsString::from(&slot.name)),
        (
            ChildEnvironment::LarchPanelPhase,
            OsString::from(phase.as_str()),
        ),
        (
            ChildEnvironment::LarchPanelPrimaryTool,
            OsString::from(tool.as_str()),
        ),
        (
            ChildEnvironment::LarchPanelSourceAgentFile,
            OsString::from(source_agent),
        ),
    ];
    if let Some(directory) = round_dir.as_ref() {
        rows.push((
            ChildEnvironment::LarchPanelRoundDir,
            directory.as_os_str().to_owned(),
        ));
    }
    if let Some(number) = options
        .panel_round_num
        .parse::<u64>()
        .ok()
        .filter(|number| *number > 0)
        .or_else(|| round_number_from_path(artifact_dir))
    {
        rows.push((
            ChildEnvironment::LarchPanelRoundNum,
            OsString::from(number.to_string()),
        ));
    }
    rows.push((
        ChildEnvironment::LarchPanelPayloadBytes,
        OsString::from(payload_bytes_for_tool(slot, tool).to_string()),
    ));
    rows
}

/// The round directory an artifact directory *is*, never one it merely lives in.
fn round_directory(artifact_dir: &Path) -> Option<PathBuf> {
    round_component(artifact_dir.file_name()?.to_str()?).map(|_number| artifact_dir.to_path_buf())
}

/// The nearest `round-N` component, searching from the leaf upward.
///
/// A panel artifact directory is often a sibling of the round directory rather
/// than the round directory itself, and the round number still has to reach the
/// prompt-size ledger.
fn round_number_from_path(path: &Path) -> Option<u64> {
    path.components()
        .rev()
        .filter_map(|component| component.as_os_str().to_str())
        .find_map(round_component)
}

fn round_component(name: &str) -> Option<u64> {
    let digits = name.strip_prefix("round-")?;
    (!digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| digits.parse().ok())
        .flatten()
}

/// Session rows every slot child inherits from this dispatch.
///
/// The voter dispatcher spawns this command as its own child and reuses the
/// same set, so one owner decides what session context reaches a vendor launch.
pub fn inherited_child_rows() -> Vec<(ChildEnvironment, OsString)> {
    [
        ChildEnvironment::AnthropicApiKey,
        ChildEnvironment::ClaudePluginData,
        ChildEnvironment::ClaudeProjectDir,
        ChildEnvironment::CodexHome,
        ChildEnvironment::CursorApiKey,
        ChildEnvironment::CursorConfigDir,
        ChildEnvironment::DesignTmpdir,
        ChildEnvironment::GhConfigDir,
        ChildEnvironment::ImplementTmpdir,
        ChildEnvironment::LarchRenderCacheDir,
        ChildEnvironment::LarchTimingLedger,
        ChildEnvironment::LarchTimingSkill,
        ChildEnvironment::LarchTokenLedger,
        ChildEnvironment::LarchTokenSessionId,
        ChildEnvironment::NoOpenBrowser,
        ChildEnvironment::OpenAiApiKey,
        ChildEnvironment::ResearchTmpdir,
        ChildEnvironment::ReviewTmpdir,
        ChildEnvironment::SessionEnvPath,
        ChildEnvironment::SessionTmpdir,
        ChildEnvironment::XdgConfigHome,
    ]
    .into_iter()
    .filter_map(|key| env::var_os(key.name()).map(|value| (key, value)))
    .collect()
}

/// Everything one slot launch needs before its child process starts.
struct LaunchPlan<'a> {
    index: usize,
    phase: Phase,
    tool: LaunchTool,
    output: String,
    slot: &'a Slot,
    options: &'a Options,
    plugin_root: &'a Path,
}

/// Start one slot child and return the handle the reaper polls.
fn start_launch(plan: &LaunchPlan<'_>, registry: &LaunchRegistry) -> Result<Arc<Launch>, String> {
    if prompt_file_for_tool(plan.slot, plan.tool).is_none() && plan.slot.agent.is_empty() {
        return Err(slot_message(
            &plan.slot.name,
            &format!("has no prompt_file for launch tool {}", plan.tool.as_str()),
        ));
    }
    let output_path = PathBuf::from(&plan.output);
    let (root, _target) = confined_target(&output_path)
        .ok_or_else(|| format!("{PROG}: slot output is not writable: {}", plan.output))?;
    let request = build_launch_request(plan)?;
    let routing = build_launch_routing(&root, &plan.output)?;
    let cancellation = registry.root.child();
    let exit_code = Arc::new(Mutex::new(None));
    let handle = spawn_launch_worker(
        request,
        routing,
        cancellation.clone(),
        Arc::clone(&exit_code),
    );
    let launch = Arc::new(Launch {
        index: plan.index,
        output: plan.output.clone(),
        tool: plan.tool,
        cancellation,
        exit_code,
        handle: Mutex::new(Some(handle)),
    });
    registry.register(&launch);
    Ok(launch)
}

fn build_launch_request(plan: &LaunchPlan<'_>) -> Result<ProcessRequest, String> {
    let program = LarchProgram::bootstrap(plan.plugin_root).map_err(|error| error.to_string())?;
    let argv = launch_arguments(plan.slot, plan.options, plan.phase, plan.tool, &plan.output);
    let timeout =
        Duration::from_secs(plan.options.timeout.parse().unwrap_or(1800)) + LAUNCH_TIMEOUT_MARGIN;
    let working_directory = env::current_dir().map_err(|error| error.to_string())?;
    let mut request = ProcessRequest::new(
        ExternalProgram::Larch(program),
        argv.into_iter().map(OsString::from),
        working_directory,
        timeout,
        LAUNCH_SHUTDOWN_GRACE,
        NonZeroUsize::new(COLLECTOR_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| error.to_string())?;
    // The bootstrap refuses to run without an explicit root, so publish the one
    // this dispatch resolved even when no caller supplied it.
    request = request.with_environment(
        ChildEnvironment::ClaudePluginRoot,
        plan.plugin_root.as_os_str().to_owned(),
    );
    for (key, value) in inherited_child_rows() {
        request = request.with_environment(key, value);
    }
    let artifact_dir = panel_artifact_dir(plan.options);
    if let Some(directory) = artifact_dir {
        for (key, value) in
            panel_dispatch_rows(&directory, plan.options, plan.slot, plan.phase, plan.tool)
        {
            request = request.with_environment(key, value);
        }
    }
    Ok(request)
}

fn panel_artifact_dir(options: &Options) -> Option<PathBuf> {
    let inherited = env::var("LARCH_PANEL_ARTIFACT_DIR").unwrap_or_default();
    let raw = if options.panel_artifact_dir.is_empty() {
        inherited
    } else {
        options.panel_artifact_dir.clone()
    };
    (!raw.is_empty()).then(|| PathBuf::from(raw))
}

/// Route the child's streams: stderr to the launch sidecar, stdout discarded.
///
/// The retired dispatcher sent the child's standard output to `/dev/null` and
/// its standard error to `<output>.launch-stderr`. The typed routing has no
/// discard mode, so standard output lands in a sibling file that
/// [`finish_launch`] removes, which keeps the published artifact set identical
/// while never letting a child's key-value stream reach this command's stdout.
fn build_launch_routing(root: &TemporaryRoot, output: &str) -> Result<ProcessFileRouting, String> {
    let confine = |suffix: &str| {
        let name = Path::new(output)
            .file_name()
            .ok_or_else(|| format!("{PROG}: slot output is not a file: {output}"))?;
        let mut file_name = name.to_os_string();
        file_name.push(suffix);
        root.confine(root.path().join(file_name), PathIntent::Write)
            .map_err(|error| error.to_string())
    };
    Ok(ProcessFileRouting::separate(
        confine(".launch-stdout")?,
        confine(LauncherArtifactKind::LaunchStderr.suffix())?,
    ))
}

fn spawn_launch_worker(
    request: ProcessRequest,
    routing: ProcessFileRouting,
    cancellation: Cancellation,
    exit_code: Arc<Mutex<Option<i32>>>,
) -> JoinHandle<()> {
    thread::spawn(move || {
        let resolved = LarchRuntime::current_thread().map_or(127, |runtime| {
            let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
            match runtime.block_on(runner.run_with_files(request, &cancellation, routing)) {
                Ok(output) => output.status().code().unwrap_or(TERMINATED_EXIT_CODE),
                Err(error) => error
                    .output()
                    .and_then(|output| output.status().code())
                    .unwrap_or(TERMINATED_EXIT_CODE),
            }
        });
        *exit_code.lock().unwrap_or_else(PoisonError::into_inner) = Some(resolved);
    })
}

/// Publish the completion sentinel and drop the discarded stdout sidecar.
fn finish_launch(launch: &Launch, exit_code: i32) {
    let done = PathBuf::from(format!(
        "{}{}",
        launch.output,
        LauncherArtifactKind::Done.suffix()
    ));
    if !done.is_file() {
        write_confined(&done, &format!("{exit_code}\n"));
    }
    let _removed = fs::remove_file(format!("{}.launch-stdout", launch.output));
}

// ---------------------------------------------------------------------------
// Phase execution
// ---------------------------------------------------------------------------

/// One phase's launched slots, plus the slots it refused before launching.
struct PhaseStart {
    outputs: Vec<String>,
    launches: Vec<Arc<Launch>>,
    prompt_missing: Vec<usize>,
}

struct PhaseRequest<'a> {
    phase: Phase,
    tools: Vec<(usize, LaunchTool)>,
    slots: &'a [Slot],
    options: &'a Options,
    plugin_root: &'a Path,
}

fn start_phase(
    request: &PhaseRequest<'_>,
    registry: &LaunchRegistry,
    drops: &mut [DropState],
) -> Result<PhaseStart, String> {
    let mut start = PhaseStart {
        outputs: Vec::new(),
        launches: Vec::new(),
        prompt_missing: Vec::new(),
    };
    for (index, tool) in &request.tools {
        let slot = &request.slots[*index];
        if !can_launch_with_prompt(slot, *tool) {
            drops[*index] = DropState::new(
                "prompt-missing",
                format!(
                    "slot {} has no prompt file for launch tool {}",
                    slot.name,
                    tool.as_str()
                ),
            );
            start.prompt_missing.push(*index);
            continue;
        }
        let output = output_for_phase(&slot.output, request.phase);
        let plan = LaunchPlan {
            index: *index,
            phase: request.phase,
            tool: *tool,
            output: output.clone(),
            slot,
            options: request.options,
            plugin_root: request.plugin_root,
        };
        start.launches.push(start_launch(&plan, registry)?);
        start.outputs.push(output);
    }
    Ok(start)
}

/// Tunables that decide when a phase cuts its remaining stragglers.
struct StragglerPolicy {
    enabled: bool,
    multiple: f64,
    floor: f64,
    ceiling: f64,
    needed: usize,
}

fn straggler_policy(options: &Options, phase_slots: usize) -> StragglerPolicy {
    let multiple = env_f64(
        "LARCH_REVIEWER_STRAGGLER_MULTIPLE",
        STRAGGLER_MULTIPLE_DEFAULT,
    );
    let ceiling = options
        .timeout
        .parse::<u64>()
        .unwrap_or(u64::MAX)
        .min(env_positive_u64(
            "LARCH_REVIEWER_STRAGGLER_MAX_SECONDS",
            STRAGGLER_MAX_SECONDS_DEFAULT,
        ));
    StragglerPolicy {
        enabled: options.straggler_cutoff
            && multiple > 0.0
            && phase_slots >= MIN_STRAGGLER_PHASE_SLOTS,
        multiple,
        #[expect(
            clippy::cast_precision_loss,
            reason = "straggler seconds are small operator-set bounds"
        )]
        floor: env_u64(
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS",
            STRAGGLER_FLOOR_SECONDS_DEFAULT,
        ) as f64,
        #[expect(
            clippy::cast_precision_loss,
            reason = "straggler seconds are small operator-set bounds"
        )]
        ceiling: ceiling as f64,
        needed: phase_slots.div_ceil(2),
    }
}

fn env_f64(name: &str, fallback: f64) -> f64 {
    env::var(name)
        .ok()
        .and_then(|raw| raw.parse().ok())
        .unwrap_or(fallback)
}

fn env_u64(name: &str, fallback: u64) -> u64 {
    env::var(name).ok().map_or(fallback, |raw| {
        raw.parse::<i64>()
            .map_or(fallback, |value| u64::try_from(value).unwrap_or(0))
    })
}

fn env_positive_u64(name: &str, fallback: u64) -> u64 {
    env::var(name).ok().map_or(fallback, |raw| {
        raw.parse::<i64>().map_or(fallback, |value| {
            u64::try_from(value)
                .ok()
                .filter(|v| *v > 0)
                .unwrap_or(fallback)
        })
    })
}

/// Wait for one phase's launches, cutting stragglers once the half-mark lands.
fn reap_phase(launches: &[Arc<Launch>], options: &Options, gates: &ResultGates) -> Vec<usize> {
    let policy = straggler_policy(options, launches.len());
    let mut pending: Vec<Arc<Launch>> = launches.to_vec();
    let mut stragglers = Vec::new();
    let mut accepted = 0usize;
    let mut deadline: Option<f64> = None;
    let start = Instant::now();
    while !pending.is_empty() {
        let mut finished = Vec::new();
        for launch in &pending {
            let Some(code) = launch.poll() else {
                continue;
            };
            finish_launch(launch, code);
            finished.push(Arc::clone(launch));
            if policy.enabled
                && deadline.is_none()
                && slot_collector_accepted(launch, options, gates)
            {
                accepted += 1;
                if accepted >= policy.needed {
                    let anchor = start.elapsed().as_secs_f64();
                    deadline = Some(
                        policy
                            .ceiling
                            .min((policy.multiple * anchor).max(policy.floor)),
                    );
                }
            }
        }
        pending.retain(|launch| !finished.iter().any(|done| Arc::ptr_eq(done, launch)));
        if let Some(cutoff) = deadline
            && !pending.is_empty()
            && start.elapsed().as_secs_f64() >= cutoff
        {
            for launch in &pending {
                launch.terminate();
                finish_launch(launch, launch.poll().unwrap_or(TERMINATED_EXIT_CODE));
                stragglers.push(launch.index);
            }
            pending.clear();
            break;
        }
        if !pending.is_empty() {
            thread::sleep(REAP_POLL_INTERVAL);
        }
    }
    stragglers
}

// ---------------------------------------------------------------------------
// Result collection
// ---------------------------------------------------------------------------

/// Collect one or more launcher outputs through the shared collector owner.
///
/// The collector runs in process rather than as a delegated verb: it returns
/// its records directly, and the caller decides whether its diagnostics reach
/// the operator. A summary pass drops them, matching the retired dispatcher's
/// discarded child stderr.
fn run_collector(
    outputs: &[&str],
    options: &Options,
    publication: Publication,
) -> Vec<CollectorRecord> {
    let request = CollectorOptions {
        timeout: options.timeout.parse().unwrap_or(DEFAULT_COLLECTOR_TIMEOUT),
        output_files: outputs.iter().map(|value| (*value).to_owned()).collect(),
        substantive: SubstantiveValidation::Off,
        structured: StructuredValidation::Off,
        publication,
    };
    let outcome = collect(&request);
    if publication == Publication::Full {
        for line in &outcome.diagnostics {
            eprintln!("{line}");
        }
    }
    outcome.records
}

/// What one collector summary block reported for a single slot.
#[derive(Clone, Debug, Eq, PartialEq)]
enum CollectorStatus {
    /// A complete result the acceptance gates still judge.
    Ok,
    /// A token-capped result the gates deliberately skip.
    CapHit,
    /// A refusal, carrying the label reported back to the drop record.
    Refused(String),
}

impl CollectorStatus {
    fn from_label(label: &str) -> Self {
        match label {
            "OK" => Self::Ok,
            "cap_hit" => Self::CapHit,
            "" => Self::Refused("unknown".to_owned()),
            other => Self::Refused(other.to_owned()),
        }
    }
}

/// One collected slot's verdict: the published output, or why it was dropped.
enum CollectorVerdict {
    Accepted(String),
    Dropped(DropState),
}

fn apply_collector_block(
    output: &str,
    record: Option<&CollectorRecord>,
    gates: &ResultGates,
) -> CollectorVerdict {
    let reviewer_file = record.map_or("", CollectorRecord::reviewer_file);
    match &CollectorStatus::from_label(record.map_or("", CollectorRecord::status)) {
        CollectorStatus::Refused(label) => {
            CollectorVerdict::Dropped(collector_failure_drop(output, label))
        }
        CollectorStatus::Ok => apply_result_gates(output, reviewer_file, gates)
            .unwrap_or_else(|| CollectorVerdict::Accepted(published_result(output, reviewer_file))),
        CollectorStatus::CapHit => {
            CollectorVerdict::Accepted(published_result(output, reviewer_file))
        }
    }
}

fn published_result(output: &str, reviewer_file: &str) -> String {
    if reviewer_file.is_empty() {
        output.to_owned()
    } else {
        reviewer_file.to_owned()
    }
}

fn collector_failure_drop(output: &str, label: &str) -> DropState {
    let snippet = snippet_from_file(Path::new(&format!(
        "{output}{}",
        LauncherArtifactKind::LaunchStderr.suffix()
    )));
    let detail = if snippet.is_empty() {
        format!("STATUS={label}")
    } else {
        format!("STATUS={label} {snippet}")
    };
    DropState::new("collector-failure", detail)
}

fn apply_result_gates(
    output: &str,
    reviewer_file: &str,
    gates: &ResultGates,
) -> Option<CollectorVerdict> {
    let check_file = if reviewer_file.is_empty() {
        output
    } else {
        reviewer_file
    };
    if let Some(pattern) = gates.result.as_ref() {
        let Some(content) = readable_result(check_file, "--require-result-pattern") else {
            return Some(unreadable_result(check_file));
        };
        if !pattern.is_match(&content) {
            return Some(CollectorVerdict::Dropped(DropState::new(
                "result-gate-miss",
                snippet_from_file(Path::new(check_file)),
            )));
        }
    }
    let pattern = gates.first_line.as_ref()?;
    let Some(content) = readable_result(check_file, "--require-first-line-pattern") else {
        return Some(unreadable_result(check_file));
    };
    let first_nonblank = first_nonblank_trimmed(&content);
    if pattern.is_match(&first_nonblank) {
        return None;
    }
    if first_nonblank.is_empty() {
        return Some(CollectorVerdict::Dropped(DropState::new("empty", "")));
    }
    if salvage_first_line(check_file, pattern) {
        return None;
    }
    Some(CollectorVerdict::Dropped(DropState::new(
        "format-gate-miss",
        snippet_from_file(Path::new(check_file)),
    )))
}

fn readable_result(check_file: &str, flag: &str) -> Option<String> {
    if !Path::new(check_file).is_file() {
        refuse(&format!(
            "{PROG}: result file not readable for {flag} check: {check_file}"
        ));
        return None;
    }
    read_lossy(Path::new(check_file))
}

fn unreadable_result(check_file: &str) -> CollectorVerdict {
    CollectorVerdict::Dropped(DropState::new(
        "result-unreadable",
        format!("result file not readable: {check_file}"),
    ))
}

/// Drop a preamble the reviewer wrote above its first contract-shaped line.
fn salvage_first_line(check_file: &str, pattern: &Regex) -> bool {
    let Some(text) = read_lossy(Path::new(check_file)) else {
        return false;
    };
    let lines: Vec<&str> = text.split_inclusive('\n').collect();
    let Some(index) = lines
        .iter()
        .position(|line| pattern.is_match(line.trim_end_matches('\n')))
    else {
        return false;
    };
    if index == 0 {
        return false;
    }
    let path = PathBuf::from(check_file);
    let Some((root, target)) = confined_target(&path) else {
        return false;
    };
    atomic_write_utf8_in(&root, &target, &lines[index..].concat(), true, 0o600).is_ok()
}

fn slot_collector_accepted(launch: &Launch, options: &Options, gates: &ResultGates) -> bool {
    let records = run_collector(&[launch.output.as_str()], options, Publication::SummaryOnly);
    matches!(
        apply_collector_block(&launch.output, records.first(), gates),
        CollectorVerdict::Accepted(_)
    )
}

/// The mutable per-slot result state one phase updates.
struct SlotResults {
    outputs: Vec<String>,
    tools: Vec<String>,
    drops: Vec<DropState>,
}

fn collect_phase(
    launches: &[Arc<Launch>],
    options: &Options,
    gates: &ResultGates,
    results: &mut SlotResults,
) -> Vec<usize> {
    if launches.is_empty() {
        return Vec::new();
    }
    let stragglers = reap_phase(launches, options, gates);
    let outputs: Vec<&str> = launches
        .iter()
        .map(|launch| launch.output.as_str())
        .collect();
    let records = run_collector(&outputs, options, Publication::SummaryOnly);
    let mut failed = Vec::new();
    for (position, launch) in launches.iter().enumerate() {
        let index = launch.index;
        if stragglers.contains(&index) {
            results.drops[index] =
                DropState::new("straggler-dropped", "cut at adaptive straggler deadline");
            continue;
        }
        match apply_collector_block(&launch.output, records.get(position), gates) {
            CollectorVerdict::Accepted(final_output) => {
                results.outputs[index] = final_output;
                launch.tool.as_str().clone_into(&mut results.tools[index]);
                results.drops[index] = DropState::default();
            }
            CollectorVerdict::Dropped(drop) => {
                results.drops[index] = drop;
                failed.push(index);
            }
        }
    }
    failed
}

// ---------------------------------------------------------------------------
// Sidecar publication
// ---------------------------------------------------------------------------

fn write_sidecar(path: &Path, text: &str, message: String) -> Result<(), String> {
    let (root, target) = confined_target(path).ok_or_else(|| message.clone())?;
    atomic_write_utf8_in(&root, &target, text, true, 0o600).map_err(|_error| message)?;
    Ok(())
}

fn write_counter(path: &str, combined_fallback: u64) {
    if path.is_empty() {
        return;
    }
    let prior = read_lossy(Path::new(path))
        .and_then(|raw| parse_uint(raw.trim()))
        .unwrap_or_default();
    write_confined(
        Path::new(path),
        &format!("{}\n", prior.saturating_add(combined_fallback)),
    );
}

fn dropped_diagnostic_name(slot: &Slot, reason: &str) -> String {
    let reason = if reason.is_empty() { "unknown" } else { reason };
    let raw = format!("dropped-{}-{}-{reason}", slot.name, slot.tool.as_str());
    let collapsed = collapse_runs(&raw, |character| {
        is_control_character(character) || matches!(character, '/' | '\t' | '\r' | '\n')
    });
    let safe = collapse_runs(&collapsed, |character| {
        !(character.is_ascii_alphanumeric() || matches!(character, '_' | '.' | '-'))
    });
    let trimmed = safe.trim_matches(|character| matches!(character, '.' | '-'));
    if trimmed.is_empty() {
        "dropped-slot.txt".to_owned()
    } else {
        format!("{trimmed}.txt")
    }
}

/// Replace every run of matching characters with one `-`, as the retired
/// dispatcher's two regular-expression substitutions did.
fn collapse_runs(text: &str, matches: impl Fn(char) -> bool) -> String {
    let mut out = String::with_capacity(text.len());
    let mut in_run = false;
    for character in text.chars() {
        if matches(character) {
            if !in_run {
                out.push('-');
                in_run = true;
            }
        } else {
            out.push(character);
            in_run = false;
        }
    }
    out
}

/// Preserve one dropped slot's diagnostic carrier beside its round directory.
fn preserve_drop_diagnostic(slot: &Slot, reason: &str) {
    let Some(parent) = Path::new(&slot.output).parent() else {
        return;
    };
    let destination = parent.join(dropped_diagnostic_name(slot, reason));
    let Ok(round_dir) = parent.canonicalize() else {
        return;
    };
    for phase in [Phase::One, Phase::Two, Phase::Three] {
        let output = output_for_phase(&slot.output, phase);
        if let Ok(artifacts) = LauncherArtifacts::create(&output) {
            let _written = write_failure_diag(&artifacts.root, &artifacts.paths, None, None, None);
        }
        for suffix in [
            LauncherArtifactKind::FailureDiag.suffix(),
            LauncherArtifactKind::LaunchStderr.suffix(),
        ] {
            if copy_confined_carrier(&format!("{output}{suffix}"), &round_dir, &destination) {
                return;
            }
        }
    }
}

fn copy_confined_carrier(source: &str, round_dir: &Path, destination: &Path) -> bool {
    let path = PathBuf::from(source);
    let Ok(metadata) = fs::symlink_metadata(&path) else {
        return false;
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() || metadata.len() == 0 {
        return false;
    }
    let Ok(resolved) = path.canonicalize() else {
        return false;
    };
    if !resolved.starts_with(round_dir) || !resolved.is_file() {
        return false;
    }
    let Some(text) = read_lossy(&resolved) else {
        return false;
    };
    write_confined(destination, &text);
    true
}

fn write_drops(path: &str, slots: &[Slot], results: &SlotResults) -> Result<String, String> {
    let mut body = String::new();
    for (index, slot) in slots.iter().enumerate() {
        if !results.outputs[index].is_empty() {
            continue;
        }
        let drop = &results.drops[index];
        let reason = if drop.reason.is_empty() {
            "unknown"
        } else {
            drop.reason.as_str()
        };
        preserve_drop_diagnostic(slot, reason);
        let _written = writeln!(
            body,
            "{}\t{}\t{reason}\t{}",
            flatten_field(&slot.name),
            flatten_field(slot.tool.as_str()),
            drop.detail
        );
    }
    if body.is_empty() {
        return Ok(String::new());
    }
    let dropped_slots_file = format!("{path}.dropped-slots");
    write_sidecar(
        Path::new(&dropped_slots_file),
        &body,
        format!("{PROG}: dropped-slots sidecar not writable: {path}"),
    )?;
    Ok(dropped_slots_file)
}

fn write_invalid_slot_drops(path: &str, invalid: &[InvalidSlotDrop]) -> Result<String, String> {
    let invalid_slots_file = format!("{path}.invalid-slots");
    let mut body = String::new();
    for drop in invalid {
        let record = serde_json::json!({
            "line": drop.line,
            "slot": drop.slot,
            "snippet": drop.snippet,
            "message": drop.message,
        });
        body.push_str(&serde_json::to_string(&record).unwrap_or_default());
        body.push('\n');
    }
    write_sidecar(
        Path::new(&invalid_slots_file),
        &body,
        format!("{PROG}: invalid-slots sidecar not writable: {invalid_slots_file}"),
    )?;
    Ok(invalid_slots_file)
}

fn write_paths_file(path: &str, outputs: &[String]) -> Result<(), String> {
    let mut body = String::new();
    for output in outputs.iter().filter(|output| !output.is_empty()) {
        body.push_str(output);
        body.push('\n');
    }
    write_sidecar(
        Path::new(path),
        &body,
        format!("{PROG}: paths-file not writable: {path}"),
    )
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

/// Whether each dispatch family still reports success.
struct DispatchStatus {
    dispatch_ok: bool,
    static_ok: bool,
    dynamic_ok: bool,
}

impl DispatchStatus {
    const fn new() -> Self {
        Self {
            dispatch_ok: true,
            static_ok: true,
            dynamic_ok: true,
        }
    }

    fn record(&mut self, slot: &Slot) {
        if slot.name.starts_with("dyn-") {
            self.dynamic_ok = false;
        } else {
            self.static_ok = false;
        }
    }
}

/// The per-phase output lists reported on stdout.
#[derive(Default)]
struct PhaseOutputs {
    phase1: Vec<String>,
    phase2: Vec<String>,
    phase3: Vec<String>,
}

fn dispatch(
    options: &Options,
    registry: &LaunchRegistry,
) -> Result<WaterfallDispatchOutcome, String> {
    let gates = ResultGates {
        result: compile_pattern(&options.require_result_pattern, "--require-result-pattern")?,
        first_line: compile_pattern(
            &options.require_first_line_pattern,
            "--require-first-line-pattern",
        )?,
    };
    let (slots, invalid) = load_slots(&options.slots_file, options.skip_invalid_slots)?;
    if options.skip_invalid_slots && slots.is_empty() {
        return Err(format!("{PROG}: slots file contains no valid slot rows"));
    }
    let resolved_paths_file = if options.paths_file.is_empty() {
        format!("{}.output-files", options.slots_file)
    } else {
        options.paths_file.clone()
    };
    if resolved_paths_file.contains(['\n', '\r']) {
        return Err(format!(
            "{PROG}: paths-file path contains a newline or carriage return (line-oriented paths-file contract)"
        ));
    }
    let paths_directory = Path::new(&resolved_paths_file)
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    if !paths_directory.is_dir() {
        return Err(format!(
            "{PROG}: paths-file parent directory does not exist: {}",
            paths_directory.display()
        ));
    }
    let invalid_slots_file = if invalid.is_empty() {
        String::new()
    } else {
        write_invalid_slot_drops(&resolved_paths_file, &invalid)?
    };
    let plugin_root =
        plugin_root_directory().ok_or_else(|| format!("{PROG}: cannot resolve the plugin root"))?;
    let mut results = SlotResults {
        outputs: vec![String::new(); slots.len()],
        tools: vec![String::new(); slots.len()],
        drops: vec![DropState::default(); slots.len()],
    };
    let mut phase_outputs = PhaseOutputs::default();
    let mut status = DispatchStatus::new();
    let fallback_count = run_phases(
        &PhaseContext {
            slots: &slots,
            options,
            gates: &gates,
            plugin_root: &plugin_root,
        },
        registry,
        &mut results,
        &mut phase_outputs,
        &mut status,
    )?;
    if registry.is_cancelled() {
        // A terminated dispatch publishes no envelope: its slots were cut, so a
        // success-shaped key-value block would misreport the round.
        return Ok(WaterfallDispatchOutcome::default());
    }
    write_counter(&options.fallback_counter_file, fallback_count);
    let report = DispatchReport {
        slots: &slots,
        options,
        results: &results,
        phase_outputs: &phase_outputs,
        status: &status,
        fallback_count,
        invalid_count: invalid.len(),
        invalid_slots_file,
        resolved_paths_file,
    };
    publish(&report)
}

struct PhaseContext<'a> {
    slots: &'a [Slot],
    options: &'a Options,
    gates: &'a ResultGates,
    plugin_root: &'a Path,
}

fn run_phases(
    context: &PhaseContext<'_>,
    registry: &LaunchRegistry,
    results: &mut SlotResults,
    phase_outputs: &mut PhaseOutputs,
    status: &mut DispatchStatus,
) -> Result<u64, String> {
    let mut phase1_queue = Vec::new();
    let mut phase1_tools = Vec::new();
    for (index, slot) in context.slots.iter().enumerate() {
        if present_for_tool(slot.tool, context.options) {
            phase1_tools.push((index, slot.tool));
        } else {
            phase1_queue.push(index);
        }
    }
    let start = start_phase(
        &PhaseRequest {
            phase: Phase::One,
            tools: phase1_tools,
            slots: context.slots,
            options: context.options,
            plugin_root: context.plugin_root,
        },
        registry,
        &mut results.drops,
    )?;
    phase_outputs.phase1 = start.outputs;
    let mut phase1_failed = start.prompt_missing;
    phase1_failed.extend(collect_phase(
        &start.launches,
        context.options,
        context.gates,
        results,
    ));
    if context.options.no_fallback {
        for index in &phase1_queue {
            results.drops[*index] = DropState::new(
                "tool-absent",
                format!(
                    "primary tool {} not present",
                    context.slots[*index].tool.as_str()
                ),
            );
        }
        for index in phase1_queue.iter().chain(&phase1_failed) {
            status.record(&context.slots[*index]);
        }
        return Ok(0);
    }
    let mut queue = phase1_queue;
    queue.extend(phase1_failed);
    run_fallback_phases(context, registry, results, phase_outputs, status, &queue)
}

fn run_fallback_phases(
    context: &PhaseContext<'_>,
    registry: &LaunchRegistry,
    results: &mut SlotResults,
    phase_outputs: &mut PhaseOutputs,
    status: &mut DispatchStatus,
    queue: &[usize],
) -> Result<u64, String> {
    let mut phase3_seed = Vec::new();
    let mut phase2_tools = Vec::new();
    for index in queue {
        let alternate = context.slots[*index].tool.opposite();
        if present_for_tool(alternate, context.options) {
            phase2_tools.push((*index, alternate));
        } else {
            phase3_seed.push(*index);
        }
    }
    let phase2 = start_phase(
        &PhaseRequest {
            phase: Phase::Two,
            tools: phase2_tools,
            slots: context.slots,
            options: context.options,
            plugin_root: context.plugin_root,
        },
        registry,
        &mut results.drops,
    )?;
    phase_outputs.phase2 = phase2.outputs;
    phase3_seed.extend(phase2.prompt_missing);
    let phase2_failed = collect_phase(&phase2.launches, context.options, context.gates, results);
    phase3_seed.extend(phase2_failed);
    let phase3_tools: Vec<(usize, LaunchTool)> = phase3_seed
        .iter()
        .map(|index| (*index, LaunchTool::Claude))
        .collect();
    let phase3 = start_phase(
        &PhaseRequest {
            phase: Phase::Three,
            tools: phase3_tools,
            slots: context.slots,
            options: context.options,
            plugin_root: context.plugin_root,
        },
        registry,
        &mut results.drops,
    )?;
    phase_outputs.phase3 = phase3.outputs;
    let fallback_count = u64::try_from(phase3.launches.len()).unwrap_or(u64::MAX);
    let phase3_failed = collect_phase(&phase3.launches, context.options, context.gates, results);
    for index in &phase3_failed {
        results.outputs[*index] = output_for_phase(&context.slots[*index].output, Phase::Three);
        LaunchTool::Claude
            .as_str()
            .clone_into(&mut results.tools[*index]);
        status.dispatch_ok = false;
        status.record(&context.slots[*index]);
    }
    for index in &phase3.prompt_missing {
        status.dispatch_ok = false;
        status.record(&context.slots[*index]);
    }
    if !phase3_failed.is_empty() {
        let outputs: Vec<&str> = phase3_failed
            .iter()
            .map(|index| results.outputs[*index].as_str())
            .collect();
        // The terminal pass reports the collector's own diagnostics directly:
        // the collector now runs in process, so no child stderr is at stake.
        let _reported = run_collector(&outputs, context.options, Publication::Full);
    }
    Ok(fallback_count)
}

const fn present_for_tool(tool: LaunchTool, options: &Options) -> bool {
    match tool {
        LaunchTool::Codex => options.codex_present,
        LaunchTool::Cursor => options.cursor_present,
        LaunchTool::Claude => false,
    }
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

struct DispatchReport<'a> {
    slots: &'a [Slot],
    options: &'a Options,
    results: &'a SlotResults,
    phase_outputs: &'a PhaseOutputs,
    status: &'a DispatchStatus,
    fallback_count: u64,
    invalid_count: usize,
    invalid_slots_file: String,
    resolved_paths_file: String,
}

fn publish(report: &DispatchReport<'_>) -> Result<WaterfallDispatchOutcome, String> {
    for (index, output) in report.results.outputs.iter().enumerate() {
        if output.contains(['\n', '\r']) {
            return Err(format!(
                "{PROG}: output path for slot '{}' contains a newline or carriage return (line-oriented paths-file contract)",
                report.slots[index].name
            ));
        }
    }
    let mut all_output_files = Vec::new();
    let mut all_output_tools = Vec::new();
    for (index, output) in report.results.outputs.iter().enumerate() {
        if output.is_empty() {
            continue;
        }
        all_output_files.push(output.clone());
        all_output_tools.push(report.results.tools[index].clone());
    }
    // Persist dropped slots whenever any slot ends with a drop reason, regardless
    // of fallback mode. Straggler drops in fallback-mode dispatch must still reach
    // the coverage gate so it can excuse the dropped archetype instead of producing
    // a spurious panel-failed stall (issue #5047).
    let dropped_slots_file = if report
        .results
        .drops
        .iter()
        .any(|drop| !drop.reason.is_empty())
    {
        write_drops(&report.resolved_paths_file, report.slots, report.results)?
    } else {
        String::new()
    };
    write_paths_file(&report.resolved_paths_file, &report.results.outputs)?;
    let straggler_dropped_count = report
        .results
        .drops
        .iter()
        .filter(|drop| drop.reason == "straggler-dropped")
        .count();
    let mut warnings = Vec::new();
    if report.fallback_count > fallback_warn_threshold() {
        warnings.push("cost-fallback-exceeded-threshold");
    }
    if straggler_dropped_count > 0 {
        warnings.push("reviewer-straggler-dropped");
    }
    if report.invalid_count > 0 {
        warnings.push("invalid-slots-dropped");
    }
    let all_slots_dropped =
        report.options.no_fallback && all_output_files.is_empty() && !report.slots.is_empty();
    Ok(WaterfallDispatchOutcome {
        phase1_slots: report.phase_outputs.phase1.clone(),
        phase2_slots: report.phase_outputs.phase2.clone(),
        phase3_slots: report.phase_outputs.phase3.clone(),
        all_output_files,
        all_output_tools,
        paths_file: report.resolved_paths_file.clone(),
        dropped_slots_file,
        fallback_count: report.fallback_count,
        straggler_dropped_count,
        invalid_slot_drop_count: report.invalid_count,
        invalid_slots_file: report.invalid_slots_file.clone(),
        warning: warnings.join(";"),
        dispatch_ok: report.status.dispatch_ok,
        static_dispatch_ok: report.status.static_ok,
        dynamic_dispatch_ok: report.status.dynamic_ok,
        all_slots_dropped,
    })
}

fn report_rows(outcome: &WaterfallDispatchOutcome) -> Vec<(&'static str, String)> {
    let mut rows = vec![
        ("PHASE1_SLOTS", outcome.phase1_slots.join(" ")),
        ("PHASE2_SLOTS", outcome.phase2_slots.join(" ")),
        ("PHASE3_SLOTS", outcome.phase3_slots.join(" ")),
        ("ALL_OUTPUT_FILES", outcome.all_output_files.join(" ")),
        ("ALL_OUTPUT_FILES_PATH", outcome.paths_file.clone()),
        ("ALL_OUTPUT_TOOLS", outcome.all_output_tools.join(" ")),
        ("FALLBACK_COUNT", outcome.fallback_count.to_string()),
        (
            "COMBINED_FALLBACK_COUNT",
            outcome.fallback_count.to_string(),
        ),
        (
            "STRAGGLER_DROPPED_COUNT",
            outcome.straggler_dropped_count.to_string(),
        ),
    ];
    if outcome.invalid_slot_drop_count > 0 {
        rows.push((
            "INVALID_SLOT_DROP_COUNT",
            outcome.invalid_slot_drop_count.to_string(),
        ));
        rows.push((
            "INVALID_SLOT_DROPS_FILE",
            outcome.invalid_slots_file.clone(),
        ));
    }
    if !outcome.warning.is_empty() {
        rows.push(("WARN", outcome.warning.clone()));
    }
    rows.push(("DISPATCH_OK", word(outcome.dispatch_ok).to_owned()));
    rows.push((
        "STATIC_DISPATCH_OK",
        word(outcome.static_dispatch_ok).to_owned(),
    ));
    rows.push((
        "DYNAMIC_DISPATCH_OK",
        word(outcome.dynamic_dispatch_ok).to_owned(),
    ));
    if outcome.all_slots_dropped {
        rows.push(("ALL_SLOTS_DROPPED", "true".to_owned()));
    }
    if !outcome.dropped_slots_file.is_empty() {
        rows.push(("DROPPED_SLOTS_FILE", outcome.dropped_slots_file.clone()));
    }
    rows
}

/// Render the exact `agent dispatch-waterfall` stdout contract without emitting it.
///
/// Review aggregation archives this stream as a forensic artifact while calling the
/// dispatch owner in-process, so it must retain the public command's row order.
pub fn render_dispatch_report(outcome: &WaterfallDispatchOutcome) -> String {
    report_rows(outcome)
        .into_iter()
        .map(|(key, value)| render_kv_row(key, &value))
        .collect()
}

fn render_kv_row(key: &str, value: &str) -> String {
    // Keep the same scalar-envelope safety boundary as `larch_core::emit_kv`.
    // This in-process rendering path must not let a path or warning forge a
    // second line in the archived dispatch artifact.
    assert!(
        !key.contains(['\n', '\r']),
        "emit_kv key {key:?} contains newline or carriage-return"
    );
    assert!(
        !value.contains(['\n', '\r']),
        "emit_kv value for {key:?} contains newline or carriage-return"
    );
    format!("{key}={value}\n")
}

fn emit_report(outcome: &WaterfallDispatchOutcome) {
    for (key, value) in report_rows(outcome) {
        emit_kv(key, &value);
    }
}

const fn word(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

fn fallback_warn_threshold() -> u64 {
    env::var("LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD")
        .ok()
        .and_then(|raw| parse_uint(&raw))
        .unwrap_or(FALLBACK_WARN_THRESHOLD_DEFAULT)
}

#[cfg(test)]
mod tests {
    use super::parse_dispatch_kv;

    #[test]
    fn dispatch_parser_keeps_legacy_last_value_and_malformed_line_behavior() {
        let values = parse_dispatch_kv("STATUS=first\nnot-an-envelope\nSTATUS=last\n=empty-key\n");

        assert_eq!(values.get("STATUS").map(String::as_str), Some("last"));
        assert_eq!(values.get("").map(String::as_str), Some("empty-key"));
        assert_eq!(values.len(), 2);
    }
}
