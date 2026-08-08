//! `agent dispatch-voters`: the code-review judge panel dispatcher.
//!
//! Three fixed voter slots — validity, plan fidelity, and pragmatism — vote on
//! one deduplicated findings ballot. Every slot is rendered once per launchable
//! vendor, written into a single slot manifest, and handed to the waterfall
//! owner in one dispatch, so a runtime vendor failure re-dispatches the slot
//! through the same three-phase ladder a statically absent vendor would take.
//!
//! Voter one always runs. Voters two and three join only when at least one
//! external vendor is present, so a both-external-down panel shrinks to the
//! single Claude anchor instead of spawning redundant same-model judges.
//!
//! This command owns no spawn of its own. `agent dispatch-waterfall` runs
//! through the verified bootstrap entrypoint, and the sibling verbs Python
//! still owns — `render voter`, `voter-calibration snapshot`,
//! `voting parse-rate-retry`, and `timing record-vendor-task` — run through the
//! shared delegated-verb seam.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    io::Read,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use larch_adapters::atomic_write_bytes_in;
use larch_core::{
    CODEX_REVIEW_MODEL_DEFAULT, CODEX_VOTE_MODEL_DEFAULT, ChildEnvironment, DuplicatePolicy,
    ExternalProgram, KvDocument, LarchProgram, ParseOptions, ProcessRequest, SafeText, emit_kv,
};
use serde_json::{Map, Value};

use crate::agent_commands::AgentRawArguments;
use crate::agent_review::findings_ledger_path;
use crate::argparse_compat::parse;
use crate::child_process::{bounded_request, run_bounded};
use crate::launcher_support::{confined_target, parse_presence, validate_site, write_confined};
use crate::python_verb::{plugin_root_directory, run_python_verb};
use crate::waterfall_commands::inherited_child_rows;

/// Program name every refusal carries, matching the retired Python command.
const PROG: &str = "agent dispatch-voters";
/// Dispatch mode the voter waterfall always runs in.
const MODE: &str = "description";
/// Panel-role sentence every voter prompt renders with.
const VOTER_PANEL_ROLE: &str = "scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted";
/// Ballot pointer every rendered voter prompt must carry.
const BALLOT_POINTER: &str = "Read the ballot from this path";
/// Longest diff prefix copied into the bounded voter context file.
const DIFF_CONTEXT_MAX_BYTES: u64 = 200_000;
/// Longest plan prefix copied into the bounded voter context file.
const PLAN_CONTEXT_MAX_BYTES: u64 = 60_000;
/// Per-slot deadline forwarded to the waterfall.
const WATERFALL_TIMEOUT_SECONDS: &str = "1200";
/// Backstop above the forwarded deadline before the runner reaps the dispatch.
const WATERFALL_MARGIN: Duration = Duration::from_secs(900);
/// Grace a cancelled waterfall child gets before its process group is killed.
const WATERFALL_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
/// Bounded capture for the waterfall child's standard streams.
const WATERFALL_OUTPUT_LIMIT: usize = 1024 * 1024;
/// Deadline for one delegated Python verb.
const VERB_TIMEOUT: Duration = Duration::from_secs(900);
/// Every long flag this command accepts.
const OPTIONS: [&str; 10] = [
    "--ballot-file",
    "--review-tmpdir",
    "--codex-available",
    "--cursor-available",
    "--session-env-path",
    "--diff-file",
    "--plan-file",
    "--round-num",
    "--site",
    "--tier",
];
/// Flags `argparse` declared as required.
const REQUIRED: [&str; 4] = [
    "--ballot-file",
    "--review-tmpdir",
    "--codex-available",
    "--cursor-available",
];
/// `argparse` renders this usage block at its 80-column fallback width.
const USAGE: &str = concat!(
    "usage: agent dispatch-voters [-h] --ballot-file BALLOT_FILE --review-tmpdir\n",
    "                             REVIEW_TMPDIR --codex-available CODEX_AVAILABLE\n",
    "                             --cursor-available CURSOR_AVAILABLE\n",
    "                             [--session-env-path SESSION_ENV_PATH]\n",
    "                             [--diff-file DIFF_FILE] [--plan-file PLAN_FILE]\n",
    "                             [--round-num ROUND_NUM] [--site SITE]\n",
    "                             [--tier TIER]\n",
);

/// One fixed voter slot, resolved from the `review.voters` topology role.
struct VoterPolicy {
    /// Manifest slot name the waterfall binds outputs back to.
    slot_name: &'static str,
    /// Vendor phase one dispatches this slot to.
    primary_tool: &'static str,
    /// Wire tool label a skipped or failed slot reports.
    default_label: &'static str,
    /// Voter archetype the prompt renders.
    archetype: &'static str,
    /// Prompt-file and artifact prefix.
    prompt_label: &'static str,
    /// Output basename inside the review tmpdir.
    output_name: &'static str,
    /// Wire tool label per launched vendor.
    semantic_labels: &'static [(&'static str, &'static str)],
}

/// The three code-review voter slots, in canonical wire order.
const VOTER_POLICIES: [VoterPolicy; 3] = [
    VoterPolicy {
        slot_name: "voter-1",
        primary_tool: "codex",
        default_label: "codex-validity",
        archetype: "validity-correctness",
        prompt_label: "validity",
        output_name: "codex-validity-vote-output.txt",
        semantic_labels: &[
            ("codex", "codex-validity"),
            ("cursor", "cursor-validity"),
            ("claude", "claude"),
        ],
    },
    VoterPolicy {
        slot_name: "voter-2",
        primary_tool: "codex",
        default_label: "codex-plan-fidelity",
        archetype: "plan-fidelity-completeness",
        prompt_label: "plan-fidelity",
        output_name: "codex-plan-fidelity-vote-output.txt",
        semantic_labels: &[
            ("codex", "codex-plan-fidelity"),
            ("cursor", "cursor-plan-fidelity"),
            ("claude", "claude"),
        ],
    },
    VoterPolicy {
        slot_name: "voter-3",
        primary_tool: "codex",
        default_label: "codex-pragmatism",
        archetype: "pragmatism-cost",
        prompt_label: "pragmatism",
        output_name: "codex-pragmatism-vote-output.txt",
        semantic_labels: &[
            ("codex", "codex-pragmatism"),
            ("cursor", "cursor-pragmatism"),
            ("claude", "claude"),
        ],
    },
];

/// Every option the voter grammar accepts, already validated.
struct Options {
    ballot_file: String,
    review_tmpdir: PathBuf,
    codex_available: bool,
    cursor_available: bool,
    session_env_path: String,
    diff_file: String,
    plan_file: String,
    round_num: u64,
    site: String,
    tier: String,
}

/// One voter slot's resolved wire state.
#[derive(Clone)]
struct VoterState {
    /// Output path, empty when the slot never produced one.
    path: String,
    /// Wire tool label.
    tool: String,
    /// `launched`, `failed`, or `skipped`.
    status: String,
    /// `SKIPPED`, `OK`, or `NOT_SUBSTANTIVE`.
    parse_rate_status: String,
}

/// Run `agent dispatch-voters`.
pub fn dispatch_voters(arguments: &AgentRawArguments) -> ExitCode {
    if arguments
        .arguments
        .iter()
        .any(|argument| argument == "-h" || argument == "--help")
    {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    match parse_options(&arguments.arguments) {
        Ok(options) => run(&options),
        Err(message) => refuse(&message),
    }
}

/// Report one operator-facing refusal, redacted like the retired diagnostic.
fn refuse(message: &str) -> ExitCode {
    eprintln!("{}", SafeText::diagnostic(message));
    ExitCode::from(2)
}

/// Emit one operator-facing note without changing the command's exit.
fn note(message: &str) {
    eprintln!("{}", SafeText::diagnostic(message));
}

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

fn parse_options(arguments: &[OsString]) -> Result<Options, String> {
    let parsed = parse(arguments, &OPTIONS, 0);
    if let Some(error) = parsed.value_error() {
        return Err(format!("{USAGE}{PROG}: error: {error}"));
    }
    let missing: Vec<&str> = REQUIRED
        .into_iter()
        .filter(|option| parsed.value(option).is_none())
        .collect();
    if !missing.is_empty() {
        return Err(format!(
            "{USAGE}{PROG}: error: the following arguments are required: {}",
            missing.join(", ")
        ));
    }
    if let Some(error) = parsed.error() {
        return Err(format!("{USAGE}{PROG}: error: {error}"));
    }
    let text = |option: &str, fallback: &str| {
        parsed.value(option).map_or_else(
            || fallback.to_owned(),
            |value| value.to_string_lossy().into_owned(),
        )
    };
    let session_default = env::var("SESSION_ENV_PATH").unwrap_or_default();
    let options = Options {
        ballot_file: text("--ballot-file", ""),
        review_tmpdir: PathBuf::from(text("--review-tmpdir", "")),
        codex_available: false,
        cursor_available: false,
        session_env_path: text("--session-env-path", &session_default),
        diff_file: text("--diff-file", ""),
        plan_file: text("--plan-file", ""),
        round_num: 1,
        site: text("--site", "review Step 2"),
        tier: String::new(),
    };
    finish_options(
        options,
        &text("--round-num", "1"),
        &text("--tier", ""),
        &parsed_flags(&parsed),
    )
}

/// The two tristate presence flags, still in their raw spelling.
fn parsed_flags(parsed: &crate::argparse_compat::ParsedCommandLine) -> (String, String) {
    let raw = |option: &str| {
        parsed
            .value(option)
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default()
    };
    (raw("--codex-available"), raw("--cursor-available"))
}

/// Apply the validations `argparse` ran after consuming the command line.
fn finish_options(
    mut options: Options,
    round_num: &str,
    tier: &str,
    availability: &(String, String),
) -> Result<Options, String> {
    if round_num.is_empty()
        || !round_num.bytes().all(|byte| byte.is_ascii_digit())
        || round_num.parse::<u64>().unwrap_or(0) == 0
    {
        return Err(format!("{PROG}: --round-num must be a positive integer"));
    }
    options.round_num = round_num.parse::<u64>().unwrap_or(1);
    validate_site(PROG, &options.site)?;
    let normalized = tier.trim().to_ascii_uppercase();
    if !tier.is_empty() && !matches!(normalized.as_str(), "TRIVIAL" | "MODERATE" | "HARD") {
        return Err(format!("{PROG}: --tier must be TRIVIAL, MODERATE, or HARD"));
    }
    options.tier = normalized;
    if options.ballot_file.is_empty() || !Path::new(&options.ballot_file).is_file() {
        return Err(format!("{PROG}: --ballot-file must name a file"));
    }
    if options.review_tmpdir.as_os_str().is_empty() {
        return Err(format!("{PROG}: --review-tmpdir is required"));
    }
    options.codex_available = parse_presence(PROG, "--codex-available", &availability.0)?;
    options.cursor_available = parse_presence(PROG, "--cursor-available", &availability.1)?;
    Ok(options)
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

fn run(options: &Options) -> ExitCode {
    let prep_start = unix_seconds();
    let Some(plugin_root) = plugin_root_directory() else {
        return refuse(&format!("{PROG}: cannot resolve the plugin root"));
    };
    let dispatcher = plugin_root.join("python/cli.py");
    if !dispatcher.is_file() {
        return refuse(&format!(
            "{PROG}: missing python/cli.py at {}",
            dispatcher.display()
        ));
    }
    if let Err(error) = fs::create_dir_all(&options.review_tmpdir) {
        return refuse(&format!("{PROG}: cannot create the review tmpdir: {error}"));
    }
    let context = bounded_context(options);
    let launched = launched_policies(options);
    let calibration = fresh_calibration_snapshot(options);
    let prompts = match build_prompts(options, launched, calibration.as_deref()) {
        Ok(prompts) => prompts,
        Err(message) => return refuse(&message),
    };
    let manifest = options.review_tmpdir.join("code-voter-slots.ndjson");
    write_confined(&manifest, &manifest_rows(options, launched, &prompts));
    let prep_end = unix_seconds();
    let waterfall = dispatch_waterfall(options, &manifest, &context, &plugin_root);
    record_prep_span(options, prep_start, prep_end);
    publish(options, launched, &manifest, &waterfall, &context)
}

/// Voter one always runs; voters two and three need one external vendor.
const fn launched_policies(options: &Options) -> usize {
    if options.codex_available || options.cursor_available {
        VOTER_POLICIES.len()
    } else {
        1
    }
}

/// Bounded copies of the caller's diff and plan, plus the flags that name them.
struct Context {
    diff: String,
    plan: String,
}

impl Context {
    /// Waterfall context flags, in the retired command's order.
    fn waterfall_flags(&self) -> Vec<String> {
        let mut flags = Vec::new();
        if !self.diff.is_empty() {
            flags.extend(["--diff-file".to_owned(), self.diff.clone()]);
        }
        if !self.plan.is_empty() {
            flags.extend(["--plan-file".to_owned(), self.plan.clone()]);
        }
        flags
    }

    /// The same context, spelled the way `voting parse-rate-retry` accepts it.
    fn parse_rate_flags(&self) -> Vec<String> {
        let mut flags = Vec::new();
        if !self.diff.is_empty() {
            flags.extend([
                "--ctx=--diff-file".to_owned(),
                "--ctx".to_owned(),
                self.diff.clone(),
            ]);
        }
        if !self.plan.is_empty() {
            flags.extend([
                "--ctx=--plan-file".to_owned(),
                "--ctx".to_owned(),
                self.plan.clone(),
            ]);
        }
        flags
    }
}

fn bounded_context(options: &Options) -> Context {
    Context {
        diff: bounded_copy(options, "diff", &options.diff_file, DIFF_CONTEXT_MAX_BYTES),
        plan: bounded_copy(options, "plan", &options.plan_file, PLAN_CONTEXT_MAX_BYTES),
    }
}

/// Copy at most `max_bytes` of one source into a review-local context file.
///
/// The prefix is read rather than the whole file: a caller's diff can be far
/// larger than the bound, and the retired command never held one in memory.
/// Bytes are copied verbatim, so a diff that is not valid UTF-8 — or one whose
/// bound falls inside a multi-byte character — reaches the voter unchanged.
fn bounded_copy(options: &Options, label: &str, source: &str, max_bytes: u64) -> String {
    if source.is_empty() || !Path::new(source).is_file() {
        return String::new();
    }
    let Ok(handle) = fs::File::open(source) else {
        return String::new();
    };
    let mut buffer = Vec::new();
    if Read::read_to_end(&mut Read::take(handle, max_bytes), &mut buffer).is_err() {
        return String::new();
    }
    let destination = options.review_tmpdir.join(format!("{label}-context.txt"));
    let Some((root, target)) = confined_target(&destination) else {
        return String::new();
    };
    if atomic_write_bytes_in(&root, &target, &buffer, true, 0o600).is_err() {
        return String::new();
    }
    destination.display().to_string()
}

/// Seconds since the epoch, as the timing ledger records them.
fn unix_seconds() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |elapsed| elapsed.as_secs())
}

// ---------------------------------------------------------------------------
// Calibration snapshot
// ---------------------------------------------------------------------------

/// Publish a nonempty voter-calibration snapshot beside the review tmpdir.
///
/// A stale snapshot is worse than none: the previous run's file is removed
/// first, and a failed or empty refresh leaves the calibration flag off.
fn fresh_calibration_snapshot(options: &Options) -> Option<String> {
    let target = options.review_tmpdir.join("voter-calibration-stats.tsv");
    let _removed = fs::remove_file(&target);
    if env::var("LARCH_VOTER_CALIBRATION_FEEDBACK")
        .unwrap_or_default()
        .trim()
        == "0"
    {
        return None;
    }
    let log_root = calibration_log_root(options)?;
    let mut arguments = vec![
        OsString::from("voter-calibration"),
        OsString::from("snapshot"),
        OsString::from("--log-root"),
        log_root.into_os_string(),
        OsString::from("--out"),
        target.as_os_str().to_owned(),
    ];
    if let Some(window) =
        env::var_os("LARCH_VOTER_CALIBRATION_WINDOW").filter(|value| !value.is_empty())
    {
        arguments.extend([OsString::from("--window"), window]);
    }
    let output = run_python_verb(arguments, VERB_TIMEOUT).ok()?;
    let usable = output.status().success()
        && fs::metadata(&target).is_ok_and(|meta| meta.is_file() && meta.len() > 0);
    if usable {
        return Some(target.display().to_string());
    }
    let _removed = fs::remove_file(&target);
    None
}

/// Resolve the consumer repository's `larch-logs` root for one review session.
///
/// The environment anchors win, then the implement session that owns this
/// review tmpdir, then the working tree. The plugin's own checkout is never a
/// calibration corpus, so a root that resolves to it is refused.
fn calibration_log_root(options: &Options) -> Option<PathBuf> {
    for name in ["LARCH_CONSUMER_REPO", "CLAUDE_PROJECT_DIR", "REPO_ROOT"] {
        let raw = env::var(name).unwrap_or_default();
        if raw.trim().is_empty() {
            continue;
        }
        if let Some(root) = consumer_root(Path::new(raw.trim())).and_then(reject_plugin_root) {
            return Some(root.join("larch-logs"));
        }
    }
    let session = implement_session_root(&options.review_tmpdir);
    session
        .and_then(reject_plugin_root)
        .map(|root| root.join("larch-logs"))
}

/// Resolve one anchor to its work-tree root, or to the anchor itself.
fn consumer_root(anchor: &Path) -> Option<PathBuf> {
    crate::launcher_support::git_workdir(anchor).or_else(|| fs::canonicalize(anchor).ok())
}

/// Refuse the plugin's own checkout as a calibration corpus root.
fn reject_plugin_root(root: PathBuf) -> Option<PathBuf> {
    let plugin = plugin_root_directory()?;
    let resolved = fs::canonicalize(&root).unwrap_or_else(|_| root.clone());
    let plugin_resolved = fs::canonicalize(&plugin).unwrap_or(plugin);
    (resolved != plugin_resolved).then_some(root)
}

/// Resolve the consumer repository the implement session recorded.
fn implement_session_root(review_tmpdir: &Path) -> Option<PathBuf> {
    let parent = review_tmpdir.parent().unwrap_or(review_tmpdir);
    let implement =
        if parent.join("session-env.sh").is_file() || parent.join(".larch-keepalive").is_file() {
            parent.to_path_buf()
        } else {
            review_tmpdir.to_path_buf()
        };
    for key in ["CLAUDE_PROJECT_DIR", "REPO_CWD"] {
        let value = session_env_value(&implement.join("session-env.sh"), key);
        if let Some(root) = anchor_root(&value) {
            return Some(root);
        }
    }
    for keepalive in [
        implement.join(".larch-keepalive"),
        review_tmpdir.join(".larch-keepalive"),
    ] {
        let clone = session_env_value(&keepalive, "CLONE_PATH");
        if let Some(root) = anchor_root(&clone) {
            return Some(root);
        }
    }
    None
}

fn anchor_root(raw: &str) -> Option<PathBuf> {
    let trimmed = raw.trim();
    (!trimmed.is_empty())
        .then(|| consumer_root(Path::new(trimmed)))
        .flatten()
}

/// Read one `KEY=value` row from a session record, ignoring symlinked files.
fn session_env_value(path: &Path, key: &str) -> String {
    if path.symlink_metadata().is_ok_and(|meta| meta.is_symlink()) {
        return String::new();
    }
    let Ok(text) = fs::read_to_string(path) else {
        return String::new();
    };
    let Ok(document) = KvDocument::parse(&text, ParseOptions::legacy()) else {
        return String::new();
    };
    document
        .select(DuplicatePolicy::First)
        .get(key)
        .map(|value| value.trim().trim_matches(['\'', '"']).to_owned())
        .unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Prompt rendering
// ---------------------------------------------------------------------------

/// One slot's rendered prompt files and payload sizes, keyed by vendor.
struct SlotPrompts {
    prompt_files: BTreeMap<String, String>,
    payload_files: BTreeMap<String, i64>,
}

/// Vendors this slot may launch, in waterfall order.
///
/// Phase one is the slot's primary vendor when present, phase two the opposite
/// vendor when present, and phase three always Claude.
fn launchable_tools(policy: &VoterPolicy, options: &Options) -> Vec<&'static str> {
    let present = |tool: &str| match tool {
        "codex" => options.codex_available,
        "cursor" => options.cursor_available,
        _ => true,
    };
    let mut tools: Vec<&'static str> = Vec::new();
    if present(policy.primary_tool) {
        tools.push(policy.primary_tool);
    }
    if matches!(policy.primary_tool, "codex" | "cursor") {
        let opposite = if policy.primary_tool == "codex" {
            "cursor"
        } else {
            "codex"
        };
        if present(opposite) {
            tools.push(opposite);
        }
        tools.push("claude");
    } else if !tools.contains(&"claude") {
        tools.push("claude");
    }
    tools.retain(|tool| {
        policy
            .semantic_labels
            .iter()
            .any(|(labelled, _label)| labelled == tool)
    });
    tools
}

fn build_prompts(
    options: &Options,
    launched: usize,
    calibration: Option<&str>,
) -> Result<Vec<SlotPrompts>, String> {
    let mut rendered = Vec::new();
    for policy in VOTER_POLICIES.iter().take(launched) {
        let mut prompt_files = BTreeMap::new();
        let mut payload_files = BTreeMap::new();
        for tool in launchable_tools(policy, options) {
            let prompt = options
                .review_tmpdir
                .join(format!("{}-vote-prompt-{tool}.txt", policy.prompt_label));
            let payload = render_voter_prompt(options, policy, tool, calibration, &prompt)?;
            prompt_files.insert(tool.to_owned(), prompt.display().to_string());
            payload_files.insert(tool.to_owned(), payload);
        }
        rendered.push(SlotPrompts {
            prompt_files,
            payload_files,
        });
    }
    Ok(rendered)
}

/// Render one voter prompt and return its accounted payload size.
///
/// A render failure, a truncated capture, or a prompt without its ballot
/// pointer aborts the dispatch: launching a judge that cannot find the ballot
/// would report a full panel that voted on nothing.
fn render_voter_prompt(
    options: &Options,
    policy: &VoterPolicy,
    tool: &str,
    calibration: Option<&str>,
    prompt: &Path,
) -> Result<i64, String> {
    let mut sidecar = prompt.as_os_str().to_owned();
    sidecar.push(".payload-bytes");
    let sidecar = PathBuf::from(sidecar);
    let ledger = findings_ledger_path(&options.review_tmpdir, &options.session_env_path);
    let mut arguments = vec![
        OsString::from("render"),
        OsString::from("voter"),
        OsString::from("--ballot-file"),
        OsString::from(&options.ballot_file),
        OsString::from("--panel-role"),
        OsString::from(VOTER_PANEL_ROLE),
        OsString::from("--id-grammar"),
        OsString::from("finding-oos"),
        OsString::from("--verification-context"),
        OsString::from("code"),
        OsString::from("--findings-ledger-file"),
        ledger.into_os_string(),
        OsString::from("--payload-bytes-output"),
        sidecar.as_os_str().to_owned(),
        OsString::from("--archetype"),
        OsString::from(policy.archetype),
        OsString::from("--voter-tool"),
        OsString::from(tool),
    ];
    if let Some(stats) = calibration {
        arguments.extend([
            OsString::from("--calibration-stats-file"),
            OsString::from(stats),
        ]);
    }
    let failure = format!(
        "{PROG}: python/cli.py render voter failed for {} voter; aborting",
        policy.prompt_label
    );
    let output = run_python_verb(arguments, VERB_TIMEOUT).map_err(|_error| failure.clone())?;
    let text = String::from_utf8_lossy(output.stdout()).into_owned();
    write_confined(prompt, &text);
    if !output.status().success() || output.stdout_truncated() {
        return Err(failure);
    }
    if !text.contains(BALLOT_POINTER) {
        return Err(format!(
            "{PROG}: python/cli.py render voter output for {} voter is missing ballot pointer; aborting",
            policy.prompt_label
        ));
    }
    Ok(read_payload_bytes(&sidecar))
}

fn read_payload_bytes(path: &Path) -> i64 {
    fs::read_to_string(path)
        .ok()
        .and_then(|text| text.trim().parse::<i64>().ok())
        .filter(|value| *value >= 0)
        .unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Slot manifest
// ---------------------------------------------------------------------------

fn manifest_rows(options: &Options, launched: usize, prompts: &[SlotPrompts]) -> String {
    let vote_default = vote_model_for_tier(&options.tier);
    let mut rendered = String::new();
    for (policy, slot) in VOTER_POLICIES.iter().take(launched).zip(prompts) {
        let mut row = Map::new();
        row.insert("slot".to_owned(), Value::from(policy.slot_name));
        row.insert("tool".to_owned(), Value::from(policy.primary_tool));
        row.insert(
            "output".to_owned(),
            Value::from(
                options
                    .review_tmpdir
                    .join(policy.output_name)
                    .display()
                    .to_string(),
            ),
        );
        row.insert("prompt_files".to_owned(), json_map(&slot.prompt_files));
        row.insert(
            "payload_files".to_owned(),
            json_numbers(&slot.payload_files),
        );
        row.insert("model_role".to_owned(), Value::from("vote"));
        if let Some(model) = resolved_model(policy.primary_tool, vote_default) {
            row.insert("resolved_model".to_owned(), Value::from(model));
        }
        rendered.push_str(&Value::Object(row).to_string());
        rendered.push('\n');
    }
    rendered
}

fn json_map(values: &BTreeMap<String, String>) -> Value {
    Value::Object(
        values
            .iter()
            .map(|(key, value)| (key.clone(), Value::from(value.clone())))
            .collect(),
    )
}

fn json_numbers(values: &BTreeMap<String, i64>) -> Value {
    Value::Object(
        values
            .iter()
            .map(|(key, value)| (key.clone(), Value::from(*value)))
            .collect(),
    )
}

/// Codex vote model pinned for one applied difficulty tier.
const fn vote_model_for_tier(tier: &str) -> &'static str {
    match tier.as_bytes() {
        b"TRIVIAL" => CODEX_REVIEW_MODEL_DEFAULT,
        b"MODERATE" | b"HARD" => CODEX_VOTE_MODEL_DEFAULT,
        _ => "",
    }
}

/// Resolve the model one manifest row attributes its slot to.
fn resolved_model(tool: &str, default_model: &str) -> Option<String> {
    let (parsed, role, flag) = match tool {
        "codex" => (
            larch_core::ModelTool::Codex,
            larch_core::CodexModelRole::Vote,
            "-m",
        ),
        "cursor" => (
            larch_core::ModelTool::Cursor,
            larch_core::CodexModelRole::Default,
            "--model",
        ),
        _ => return None,
    };
    let environment: BTreeMap<String, String> = env::vars().collect();
    let resolved = larch_core::resolve_model_args(
        parsed,
        tool == "codex",
        if tool == "codex" { default_model } else { "" },
        role,
        &environment,
    );
    let Ok(result) = resolved else {
        return Some("unknown".to_owned());
    };
    let argv = result.argv();
    let index = argv.iter().position(|token| token == flag);
    Some(
        index
            .and_then(|position| argv.get(position + 1))
            .cloned()
            .unwrap_or_else(|| "unknown".to_owned()),
    )
}

// ---------------------------------------------------------------------------
// Waterfall dispatch
// ---------------------------------------------------------------------------

/// Where one panel's prompt-size artifacts land, and the round that owns them.
struct PanelArtifacts {
    directory: PathBuf,
    round_dir: Option<PathBuf>,
}

fn panel_artifacts(options: &Options) -> PanelArtifacts {
    if is_round_directory(&options.review_tmpdir) {
        return PanelArtifacts {
            directory: options.review_tmpdir.clone(),
            round_dir: Some(options.review_tmpdir.clone()),
        };
    }
    let nested = options
        .review_tmpdir
        .join(format!("round-{}", options.round_num));
    if nested.is_dir() {
        return PanelArtifacts {
            directory: nested.clone(),
            round_dir: Some(nested),
        };
    }
    PanelArtifacts {
        directory: options.review_tmpdir.clone(),
        round_dir: None,
    }
}

fn is_round_directory(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .and_then(|name| name.strip_prefix("round-"))
        .is_some_and(|tail| !tail.is_empty() && tail.bytes().all(|byte| byte.is_ascii_digit()))
}

fn waterfall_arguments(
    options: &Options,
    manifest: &Path,
    artifacts: &PanelArtifacts,
    context: &Context,
) -> Vec<OsString> {
    let mut arguments: Vec<OsString> = vec![
        OsString::from("agent"),
        OsString::from("dispatch-waterfall"),
        OsString::from("--slots-file"),
        manifest.as_os_str().to_owned(),
        OsString::from("--panel-artifact-dir"),
        artifacts.directory.as_os_str().to_owned(),
        OsString::from("--codex-present"),
        OsString::from(bool_text(options.codex_available)),
        OsString::from("--cursor-present"),
        OsString::from(bool_text(options.cursor_available)),
        OsString::from("--mode"),
        OsString::from(MODE),
        OsString::from("--timeout"),
        OsString::from(WATERFALL_TIMEOUT_SECONDS),
        OsString::from("--model-role"),
        OsString::from("vote"),
        OsString::from("--site"),
        OsString::from(&options.site),
        // The terminal Claude voter tier reads the ballot from the round
        // directory, so grant it that root rather than prompting mid-dispatch.
        OsString::from("--claude-read-tools-add-dir"),
        options.review_tmpdir.as_os_str().to_owned(),
    ];
    arguments.extend(context.waterfall_flags().into_iter().map(OsString::from));
    let vote_default = vote_model_for_tier(&options.tier);
    if !vote_default.is_empty() {
        arguments.extend([
            OsString::from("--default-model"),
            OsString::from(vote_default),
        ]);
    }
    arguments
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

/// Panel rows the waterfall child and its slot launches record against.
fn panel_rows(options: &Options, artifacts: &PanelArtifacts) -> Vec<(ChildEnvironment, OsString)> {
    let mut rows = vec![
        (
            ChildEnvironment::LarchPanelArtifactDir,
            artifacts.directory.as_os_str().to_owned(),
        ),
        (
            ChildEnvironment::LarchPanelSite,
            OsString::from(&options.site),
        ),
        (ChildEnvironment::LarchPanelSlot, OsString::new()),
        (ChildEnvironment::LarchPanelPhase, OsString::new()),
        (ChildEnvironment::LarchPanelPrimaryTool, OsString::new()),
        (ChildEnvironment::LarchPanelSourceAgentFile, OsString::new()),
        (
            ChildEnvironment::LarchPanelRoundNum,
            OsString::from(options.round_num.to_string()),
        ),
    ];
    if let Some(round) = &artifacts.round_dir {
        rows.push((
            ChildEnvironment::LarchPanelRoundDir,
            round.as_os_str().to_owned(),
        ));
    }
    rows
}

/// Run the waterfall owner and return its captured key-value stdout.
///
/// A nonzero dispatch is a degraded panel, not a failed command: the retired
/// dispatcher recorded it and published whatever the slots produced.
fn dispatch_waterfall(
    options: &Options,
    manifest: &Path,
    context: &Context,
    plugin_root: &Path,
) -> String {
    let artifacts = panel_artifacts(options);
    let request = match build_waterfall_request(options, manifest, context, plugin_root, &artifacts)
    {
        Ok(request) => request,
        Err(message) => {
            note(&format!("{PROG}: {message}"));
            return String::new();
        }
    };
    match run_bounded(request) {
        Ok(output) => {
            if !output.status().success() {
                note(&format!(
                    "{PROG}: agent dispatch-waterfall exited {}: proceeding with partial or empty result",
                    output.status().code().unwrap_or(-1)
                ));
            }
            String::from_utf8_lossy(output.stdout()).into_owned()
        }
        Err(message) => {
            note(&format!(
                "{PROG}: agent dispatch-waterfall did not run: {message}: proceeding with partial or empty result"
            ));
            String::new()
        }
    }
}

fn build_waterfall_request(
    options: &Options,
    manifest: &Path,
    context: &Context,
    plugin_root: &Path,
    artifacts: &PanelArtifacts,
) -> Result<ProcessRequest, String> {
    let program = LarchProgram::bootstrap(plugin_root).map_err(|error| error.to_string())?;
    let mut request = bounded_request(
        ExternalProgram::Larch(program),
        waterfall_arguments(options, manifest, artifacts, context),
        Duration::from_secs(WATERFALL_TIMEOUT_SECONDS.parse().unwrap_or(1200)) + WATERFALL_MARGIN,
        WATERFALL_SHUTDOWN_GRACE,
        WATERFALL_OUTPUT_LIMIT,
    )?;
    request = request.with_environment(
        ChildEnvironment::ClaudePluginRoot,
        plugin_root.as_os_str().to_owned(),
    );
    for (key, value) in inherited_child_rows() {
        request = request.with_environment(key, value);
    }
    for (key, value) in panel_rows(options, artifacts) {
        request = request.with_environment(key, value);
    }
    Ok(request)
}

/// Record the serial pre-dispatch window as one `voter-dispatch-prep` row.
///
/// A voter stamps its own start only after the waterfall spawns it, so without
/// this row the timing Gantt shows a blank band where the calibration
/// snapshot, the prompt renders, and the manifest write actually ran.
fn record_prep_span(options: &Options, start: u64, end: u64) {
    if resolved_timing_ledger().is_none_or(|ledger| !ledger.is_file()) {
        return;
    }
    let output = format!("voter-dispatch-prep-round-{}.out", options.round_num);
    crate::python_verb::record_vendor_timing(
        "claude",
        "voter-dispatch-prep",
        start,
        end,
        Path::new(&output),
        0,
        "complete",
    );
}

/// Resolve the timing ledger this session records against, if it has one.
fn resolved_timing_ledger() -> Option<PathBuf> {
    let declared = env::var("LARCH_TIMING_LEDGER").unwrap_or_default();
    if !declared.is_empty()
        && !Path::new(&declared)
            .components()
            .any(|part| part.as_os_str() == "..")
    {
        return Some(PathBuf::from(declared));
    }
    for key in [
        "IMPLEMENT_TMPDIR",
        "SESSION_ENV_PATH",
        "DESIGN_TMPDIR",
        "REVIEW_TMPDIR",
    ] {
        let raw = env::var(key).unwrap_or_default();
        if raw.is_empty() {
            continue;
        }
        let base = if key == "SESSION_ENV_PATH" {
            Path::new(&raw).parent().map(Path::to_path_buf)
        } else {
            Some(PathBuf::from(&raw))
        };
        if let Some(directory) = base.filter(|path| path.is_dir()) {
            return Some(directory.join("timing-ledger.tsv"));
        }
    }
    None
}

// ---------------------------------------------------------------------------
// Result publication
// ---------------------------------------------------------------------------

fn publish(
    options: &Options,
    launched: usize,
    manifest: &Path,
    waterfall: &str,
    context: &Context,
) -> ExitCode {
    let values = parse_kv(waterfall);
    if let Some(warning) = values.get("WARN").filter(|value| !value.is_empty()) {
        emit_kv("WARN", warning);
    }
    let bindings = crate::slot_binding::bind_manifest_slot_outputs(manifest, &values);
    let mut states = slot_states(launched, &bindings);
    for state in &mut states {
        if state.status != "skipped" && !completed(&state.path) {
            "failed".clone_into(&mut state.status);
        }
    }
    run_parse_rate_checks(options, context, &mut states);
    let effective = states
        .iter()
        .filter(|state| {
            state.status != "failed"
                && state.status != "skipped"
                && state.parse_rate_status != "NOT_SUBSTANTIVE"
                && is_nonempty(&state.path)
        })
        .count();
    if effective < launched {
        let warning = format!(
            "**⚠ Degraded code-review panel: {effective}/{launched} effective judges produced output.**"
        );
        note(&warning);
        emit_kv("DEGRADED_PANEL_WARNING", &warning);
    }
    let paths_file = write_voter_paths_file(options, &states);
    let dispatch_ok = effective > 0
        && states[0].status != "failed"
        && values.get("DISPATCH_OK").map(String::as_str) != Some("false");
    emit_voter_rows(&states, &paths_file, dispatch_ok);
    ExitCode::SUCCESS
}

/// Resolve the fixed three-slot wire state from the waterfall's slot bindings.
fn slot_states(
    launched: usize,
    bindings: &BTreeMap<String, crate::slot_binding::SlotOutputBinding>,
) -> Vec<VoterState> {
    VOTER_POLICIES
        .iter()
        .enumerate()
        .map(|(index, policy)| {
            if index >= launched {
                return VoterState {
                    path: String::new(),
                    tool: policy.default_label.to_owned(),
                    status: "skipped".to_owned(),
                    parse_rate_status: "SKIPPED".to_owned(),
                };
            }
            let binding = bindings.get(policy.slot_name);
            let resolved = binding.filter(|binding| !binding.dropped && !binding.path.is_empty());
            resolved.map_or_else(
                || VoterState {
                    path: String::new(),
                    tool: policy.default_label.to_owned(),
                    status: "failed".to_owned(),
                    parse_rate_status: "SKIPPED".to_owned(),
                },
                |binding| {
                    let tool = if binding.tool.is_empty() {
                        policy.primary_tool
                    } else {
                        binding.tool.as_str()
                    };
                    VoterState {
                        path: binding.path.clone(),
                        tool: semantic_label(policy, tool).to_owned(),
                        status: "launched".to_owned(),
                        parse_rate_status: "SKIPPED".to_owned(),
                    }
                },
            )
        })
        .collect()
}

fn semantic_label<'a>(policy: &'a VoterPolicy, tool: &str) -> &'a str {
    policy
        .semantic_labels
        .iter()
        .find(|(labelled, _label)| *labelled == tool)
        .map_or(policy.default_label, |(_labelled, label)| *label)
}

/// Whether one slot produced a nonempty result and a zero completion sentinel.
fn completed(path: &str) -> bool {
    if !is_nonempty(path) {
        return false;
    }
    fs::read_to_string(format!("{path}.done"))
        .ok()
        .and_then(|text| text.lines().next().map(str::to_owned))
        .is_some_and(|first| first == "0")
}

fn is_nonempty(path: &str) -> bool {
    !path.is_empty() && fs::metadata(path).is_ok_and(|meta| meta.is_file() && meta.len() > 0)
}

/// Run the parse-rate guard for every voter that produced usable output.
fn run_parse_rate_checks(options: &Options, context: &Context, states: &mut [VoterState]) {
    let plugin_root = plugin_root_directory().unwrap_or_default();
    for (index, state) in states.iter_mut().enumerate() {
        if state.status == "failed" || state.status == "skipped" {
            continue;
        }
        let mut arguments: Vec<OsString> = vec![
            OsString::from("voting"),
            OsString::from("parse-rate-retry"),
            OsString::from("--ballot-file"),
            OsString::from(&options.ballot_file),
            OsString::from("--id-grammar"),
            OsString::from("finding-oos"),
            OsString::from("--review-tmpdir"),
            options.review_tmpdir.as_os_str().to_owned(),
            OsString::from("--plugin-root"),
            plugin_root.as_os_str().to_owned(),
            OsString::from("--dispatch-label"),
            OsString::from(PROG),
        ];
        arguments.extend(context.parse_rate_flags().into_iter().map(OsString::from));
        arguments.extend([
            OsString::from("--slot"),
            OsString::from((index + 1).to_string()),
            OsString::from("--voter-file"),
            OsString::from(&state.path),
            OsString::from("--voter-tool"),
            OsString::from(&state.tool),
        ]);
        state.parse_rate_status = parse_rate_status(arguments);
    }
}

/// Fail closed on every malformed parse-rate result.
fn parse_rate_status(arguments: Vec<OsString>) -> String {
    let Ok(output) = run_python_verb(arguments, VERB_TIMEOUT) else {
        return "NOT_SUBSTANTIVE".to_owned();
    };
    if !output.status().success() {
        return "NOT_SUBSTANTIVE".to_owned();
    }
    let text = String::from_utf8_lossy(output.stdout()).into_owned();
    let last = text
        .lines()
        .map(str::trim)
        .rfind(|line| !line.is_empty())
        .unwrap_or_default();
    if last == "OK" {
        "OK".to_owned()
    } else {
        "NOT_SUBSTANTIVE".to_owned()
    }
}

/// Publish the voter paths every downstream tally reads.
///
/// Slot one always contributes when it has a path; slots two and three
/// contribute unless the panel never launched them.
fn write_voter_paths_file(options: &Options, states: &[VoterState]) -> String {
    let target = options.review_tmpdir.join("code-voter-paths.txt");
    let mut body = String::new();
    for (index, state) in states.iter().enumerate() {
        if index > 0 && state.status == "skipped" {
            continue;
        }
        if !state.path.is_empty() {
            body.push_str(&state.path);
            body.push('\n');
        }
    }
    write_confined(&target, &body);
    target.display().to_string()
}

fn emit_voter_rows(states: &[VoterState], paths_file: &str, dispatch_ok: bool) {
    for (index, state) in states.iter().enumerate() {
        let slot = index + 1;
        emit_kv(&format!("VOTER_{slot}_PATH"), &state.path);
        emit_kv(&format!("VOTER_{slot}_TOOL"), &state.tool);
        emit_kv(&format!("VOTER_{slot}_STATUS"), &state.status);
        emit_kv(
            &format!("VOTER_{slot}_PARSE_RATE_STATUS"),
            &state.parse_rate_status,
        );
    }
    emit_kv("VOTER_PATHS_FILE", paths_file);
    emit_kv("DISPATCH_OK", bool_text(dispatch_ok));
}

/// Read the waterfall's `KEY=value` stdout, last spelling winning.
fn parse_kv(output: &str) -> BTreeMap<String, String> {
    KvDocument::parse(output, ParseOptions::legacy()).map_or_else(
        |_error| BTreeMap::new(),
        |document| document.select(DuplicatePolicy::Last),
    )
}

#[cfg(test)]
mod tests {
    use super::{
        Options, VOTER_POLICIES, launchable_tools, resolved_model, semantic_label,
        vote_model_for_tier,
    };
    use std::path::PathBuf;

    fn options(codex: bool, cursor: bool) -> Options {
        Options {
            ballot_file: String::new(),
            review_tmpdir: PathBuf::new(),
            codex_available: codex,
            cursor_available: cursor,
            session_env_path: String::new(),
            diff_file: String::new(),
            plan_file: String::new(),
            round_num: 1,
            site: "review Step 2".to_owned(),
            tier: String::new(),
        }
    }

    #[test]
    fn launchable_tools_follow_the_waterfall_order() {
        let policy = &VOTER_POLICIES[0];
        assert_eq!(
            launchable_tools(policy, &options(true, true)),
            ["codex", "cursor", "claude"]
        );
        assert_eq!(
            launchable_tools(policy, &options(false, true)),
            ["cursor", "claude"]
        );
        assert_eq!(launchable_tools(policy, &options(false, false)), ["claude"]);
    }

    #[test]
    fn semantic_labels_fall_back_to_the_slot_default() {
        assert_eq!(
            semantic_label(&VOTER_POLICIES[1], "cursor"),
            "cursor-plan-fidelity"
        );
        assert_eq!(
            semantic_label(&VOTER_POLICIES[1], "nothing"),
            "codex-plan-fidelity"
        );
    }

    #[test]
    fn vote_model_follows_the_difficulty_tier() {
        assert_eq!(vote_model_for_tier("TRIVIAL"), "gpt-5.6-luna");
        assert_eq!(vote_model_for_tier("HARD"), "gpt-5.6-terra");
        assert_eq!(vote_model_for_tier(""), "");
    }

    #[test]
    fn a_manifest_row_resolves_only_a_vendor_model() {
        assert_eq!(
            resolved_model("codex", "gpt-5.6-terra"),
            Some("gpt-5.6-terra".to_owned())
        );
        assert!(
            resolved_model("cursor", "")
                .is_some_and(|model| !model.is_empty() && model != "unknown")
        );
        assert_eq!(resolved_model("claude", ""), None);
    }
}
