//! Topology anchor: round gated static plus dynamic.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use clap::Subcommand;
use larch_adapters::{atomic_write_utf8_in, ensure_directory_chain, validate_design_tmpdir};
use larch_core::{
    cleanup_cache_sessions_root, emit_kv, redact_secrets_only, redact_sensitive_paths,
    review::{
        VoterOutputBinding, VoterPathsFilePolicy, VoterRowLayout, VoterSlotPolicy, VoterSlotState,
        voter_states_from_bindings, voter_status_rows, with_manifest_attribution,
    },
};
use serde_json::{Map, Value, json};

use crate::{
    agent_commands::AgentRawArguments,
    argparse_compat::{ParsedCommandLine, parse, usage_error},
    launcher_support::{confined_target, parse_presence},
    python_verb::run_python_verb,
    runtime_entrypoint::run_verified_larch,
    voter_dispatch_commands::{
        VOTER_POLICIES, bool_text, completed, fresh_plan_calibration_snapshot, is_nonempty,
        launchable_tools, read_payload_bytes, record_prep_span, unix_seconds,
    },
    waterfall_commands::{
        WaterfallDispatchOutcome, dispatch_for_review, parse_dispatch_kv, render_dispatch_report,
    },
};

const PANEL_PROG: &str = "cli.py plan-review panel-dispatch";
const PANEL_USAGE: &str = "usage: cli.py plan-review panel-dispatch [-h] --design-tmpdir DESIGN_TMPDIR [--round-num ROUND_NUM] [--prune-round-num PRUNE_ROUND_NUM] --codex-present CODEX_PRESENT --cursor-present CURSOR_PRESENT --plan-file PLAN_FILE --feature-file FEATURE_FILE [--timeout TIMEOUT] [--tier TIER] [--escalated-round ESCALATED_ROUND]";
const VOTER_PROG: &str = "cli.py plan-review voter-dispatch";
const VOTER_USAGE: &str = "usage: cli.py plan-review voter-dispatch [-h] --ballot-file BALLOT_FILE --design-tmpdir DESIGN_TMPDIR --codex-available CODEX_AVAILABLE --cursor-available CURSOR_AVAILABLE [--scope-anchor-file SCOPE_ANCHOR_FILE] --round-num ROUND_NUM";
const STATIC_ARCHETYPES: [&str; 4] = ["arch", "innovation", "pragmatic", "requirements"];
const PLAN_VOTER_PANEL_ROLE: &str = "senior engineer on a voting panel deciding which proposed plan modifications should be accepted";
const CODEX_PLAN_REVIEW_MODEL: &str = "gpt-5.6-terra";
const BALLOT_POINTER: &str = "Read the ballot from this path";
const PYTHON_TIMEOUT: Duration = Duration::from_secs(900);
type PanelRows = Vec<Map<String, Value>>;
type DynamicRenderFailures = Vec<(String, String, i32)>;
/// Rust-owned plan-review dispatch commands.
#[derive(Subcommand)]
pub enum PlanReviewCommand {
    /// Materialize and dispatch the plan reviewer panel.
    #[command(name = "panel-dispatch", disable_help_flag = true)]
    PanelDispatch(AgentRawArguments),
    /// Dispatch the fixed three plan-review voter roles.
    #[command(name = "voter-dispatch", disable_help_flag = true)]
    VoterDispatch(AgentRawArguments),
}
/// Dispatch one Rust-owned plan-review command.
pub fn run(command: PlanReviewCommand) -> ExitCode {
    match command {
        PlanReviewCommand::PanelDispatch(arguments) => panel_dispatch(&arguments.arguments),
        PlanReviewCommand::VoterDispatch(arguments) => voter_dispatch(&arguments.arguments),
    }
}
struct PanelOptions {
    design: PathBuf,
    round_num: i64,
    prune_round_num: i64,
    codex_present: bool,
    cursor_present: bool,
    plan_file: String,
    feature_file: String,
    timeout: String,
    tier: String,
    escalated_round: bool,
}
fn panel_dispatch(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        println!("{PANEL_USAGE}");
        return ExitCode::SUCCESS;
    }
    let options = match parse_panel_options(arguments) {
        Ok(options) => options,
        Err(message) => return usage_error(PANEL_USAGE, PANEL_PROG, &message, 2),
    };
    match run_panel(&options) {
        Ok(code) => code,
        Err(message) => {
            eprintln!("{PANEL_PROG}: {message}");
            ExitCode::FAILURE
        }
    }
}
fn parse_panel_options(arguments: &[OsString]) -> Result<PanelOptions, String> {
    const OPTIONS: [&str; 10] = [
        "--design-tmpdir",
        "--round-num",
        "--prune-round-num",
        "--codex-present",
        "--cursor-present",
        "--plan-file",
        "--feature-file",
        "--timeout",
        "--tier",
        "--escalated-round",
    ];
    const REQUIRED: [&str; 5] = [
        "--design-tmpdir",
        "--codex-present",
        "--cursor-present",
        "--plan-file",
        "--feature-file",
    ];
    let parsed = parse(arguments, &OPTIONS, 0);
    require_options(&parsed, &REQUIRED)?;
    if let Some(error) = parsed.error() {
        return Err(error);
    }
    let round_num = parse_integer(&parsed_text(&parsed, "--round-num", "1"), "--round-num")?;
    let prune_round_num = parse_integer(
        &parsed_text(&parsed, "--prune-round-num", "0"),
        "--prune-round-num",
    )?;
    let tier = parsed_text(&parsed, "--tier", "MODERATE")
        .trim()
        .to_ascii_uppercase();
    if !matches!(tier.as_str(), "TRIVIAL" | "MODERATE" | "HARD") {
        return Err("--tier must be TRIVIAL, MODERATE, or HARD".to_owned());
    }
    let escalated = parsed_text(&parsed, "--escalated-round", "false");
    if !matches!(escalated.as_str(), "true" | "false") {
        return Err("--escalated-round must be true or false".to_owned());
    }
    let design = validated_design_tmpdir(&parsed_text(&parsed, "--design-tmpdir", ""), false)?;
    Ok(PanelOptions {
        design,
        round_num,
        prune_round_num,
        codex_present: parse_presence(
            PANEL_PROG,
            "--codex-present",
            &parsed_text(&parsed, "--codex-present", ""),
        )?,
        cursor_present: parse_presence(
            PANEL_PROG,
            "--cursor-present",
            &parsed_text(&parsed, "--cursor-present", ""),
        )?,
        plan_file: parsed_text(&parsed, "--plan-file", ""),
        feature_file: parsed_text(&parsed, "--feature-file", ""),
        timeout: parsed_text(&parsed, "--timeout", "600"),
        tier,
        escalated_round: escalated == "true",
    })
}
fn run_panel(options: &PanelOptions) -> Result<ExitCode, String> {
    let round_dir = options
        .design
        .join("plan-review")
        .join(format!("round-{}", options.round_num));
    ensure_directory_chain(&round_dir).map_err(|error| error.to_string())?;
    let environment = env::vars().collect::<BTreeMap<_, _>>();
    let mut rows = static_panel_rows(options, &round_dir, &environment)?;
    let static_count = rows.len();
    let dynamic = load_dynamic_archetypes(&options.design);
    let (dynamic_rows, failures) = dynamic_panel_rows(options, &round_dir, &dynamic, &environment)?;
    rows.extend(dynamic_rows);
    let manifest = options.design.join("plan-review-slots.ndjson");
    write_manifest(&manifest, &rows)?;

    let prune_round = if options.escalated_round {
        0
    } else if options.prune_round_num == 0 {
        options.round_num
    } else {
        options.prune_round_num
    };
    let prune = filter_pruned(&options.design, &manifest, prune_round)?;
    let dynamic_warning = dynamic_render_warning(&failures);
    if prune
        .get("PANEL_PRUNED_EMPTY")
        .is_some_and(|value| value == "true")
    {
        emit_optional("DYNAMIC_RENDER_PANEL_WARNING", &dynamic_warning);
        emit_kv("PANEL_PRUNED_EMPTY", "true");
        emit_kv("STATIC_SLOT_COUNT", &static_count.to_string());
        emit_kv("DYNAMIC_SLOT_COUNT", &(dynamic.len() * 2).to_string());
        emit_kv(
            "PANEL_PATHS_FILE",
            &options
                .design
                .join("plan-review-panel-paths.txt")
                .display()
                .to_string(),
        );
        return Ok(ExitCode::SUCCESS);
    }

    let waterfall = panel_waterfall_arguments(options, &manifest, &round_dir);
    let outcome = match dispatch_for_review(&waterfall) {
        Ok(outcome) => outcome,
        Err(message) => {
            let code = 2;
            write_panel_failure(options, code, &message)?;
            eprintln!("{}", sanitize_warning(&message));
            emit_kv("PANEL_DISPATCH_EXIT_CODE", &code.to_string());
            emit_kv(
                "PANEL_FAILURE_DETAIL_LOG",
                &options
                    .design
                    .join("plan-review-panel-failure.log")
                    .display()
                    .to_string(),
            );
            emit_panel_counts(static_count, dynamic.len() * 2, &prune);
            emit_optional("DYNAMIC_RENDER_PANEL_WARNING", &dynamic_warning);
            return Ok(ExitCode::from(code));
        }
    };
    print!("{}", render_dispatch_report(&outcome));
    emit_panel_counts(static_count, dynamic.len() * 2, &prune);
    let fallback_paths = options
        .design
        .join("plan-review-panel-paths.txt")
        .display()
        .to_string();
    let paths_file = if outcome.paths_file.is_empty() {
        &fallback_paths
    } else {
        &outcome.paths_file
    };
    emit_kv("PANEL_PATHS_FILE", paths_file);
    emit_optional("DROPPED_SLOTS_FILE", &outcome.dropped_slots_file);
    emit_invalid_slot_warning(&outcome);
    emit_optional("DYNAMIC_RENDER_PANEL_WARNING", &dynamic_warning);
    Ok(ExitCode::SUCCESS)
}

fn static_panel_rows(
    options: &PanelOptions,
    round_dir: &Path,
    environment: &BTreeMap<String, String>,
) -> Result<Vec<Map<String, Value>>, String> {
    let mut rows = Vec::new();
    for archetype in STATIC_ARCHETYPES {
        for (tool, present) in [
            ("cursor", options.cursor_present),
            ("codex", options.codex_present),
        ] {
            if !present {
                continue;
            }
            let slot = format!("{tool}-plan-{archetype}");
            let prompt = options
                .design
                .join(format!("render-plan-{tool}-{archetype}.prompt"));
            let payload = payload_sidecar(&prompt);
            let _removed = fs::remove_file(&payload);
            let rendered =
                render_plan_prompt(options, tool, Some(archetype), None, &payload, false);
            let (prompt_text, payload_bytes) = rendered.map_or_else(
                |_| {
                    (
                        format!("Review the design plan with a {archetype} lens."),
                        0,
                    )
                },
                |text| {
                    if text.is_empty() {
                        (
                            format!("Review the design plan with a {archetype} lens."),
                            0,
                        )
                    } else {
                        let bytes = read_payload_bytes(&payload).max(0);
                        (text, bytes)
                    }
                },
            );
            write_required(&prompt, &prompt_text)?;
            let output = if tool == "codex" {
                format!("codex-primary-plan-{archetype}-output.txt")
            } else {
                format!("cursor-plan-{archetype}-output.txt")
            };
            let mut row = base_panel_row(
                tool,
                &slot,
                archetype,
                &round_dir.join(output),
                &prompt,
                payload_bytes,
            );
            let default_model = panel_default_model(&options.tier, tool);
            row = with_manifest_attribution(
                row,
                (tool == "codex").then_some("review"),
                default_model,
                environment,
            );
            rows.push(row);
        }
    }
    Ok(rows)
}

#[derive(Clone, Debug)]
struct DynamicArchetype {
    name: String,
    focus: String,
    prompt: String,
}

fn load_dynamic_archetypes(design: &Path) -> Vec<DynamicArchetype> {
    let manifest = design.join("scout-plan-manifest.json");
    if manifest
        .symlink_metadata()
        .is_ok_and(|data| data.is_symlink())
        || !manifest.is_file()
    {
        return Vec::new();
    }
    let Some(value) = fs::read_to_string(manifest)
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
    else {
        return Vec::new();
    };
    let Some(archetypes) = value.get("archetypes").and_then(Value::as_array) else {
        return Vec::new();
    };
    archetypes
        .iter()
        .filter_map(|raw| {
            let object = raw.as_object()?;
            let name = object.get("name").and_then(Value::as_str)?.trim();
            if name.is_empty() {
                return None;
            }
            let focus = object
                .get("focus_area")
                .and_then(Value::as_str)
                .unwrap_or("correctness")
                .trim();
            Some(DynamicArchetype {
                name: name.to_owned(),
                focus: if focus.is_empty() {
                    "correctness"
                } else {
                    focus
                }
                .to_owned(),
                prompt: object
                    .get("prompt_body")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .trim()
                    .to_owned(),
            })
        })
        .collect()
}

fn dynamic_panel_rows(
    options: &PanelOptions,
    round_dir: &Path,
    dynamic: &[DynamicArchetype],
    environment: &BTreeMap<String, String>,
) -> Result<(PanelRows, DynamicRenderFailures), String> {
    let mut rows = Vec::new();
    let mut failures = Vec::new();
    for archetype in dynamic {
        for tool in ["cursor", "codex"] {
            let slot = format!("dyn-{tool}-plan-{}", archetype.name);
            let component = safe_component(&slot);
            let body = round_dir.join(format!("{component}.body"));
            let prompt = round_dir.join(format!("{component}.prompt"));
            let payload = payload_sidecar(&prompt);
            write_required(&body, &archetype.prompt)?;
            let _removed = fs::remove_file(&payload);
            let rendered = render_plan_prompt(options, tool, None, Some(&body), &payload, true);
            let (prompt_text, payload_bytes) = match rendered {
                Ok(text) if !text.is_empty() => (text, read_payload_bytes(&payload).max(0)),
                Ok(_) => (
                    format!("Review the design plan with a {} lens.", archetype.focus),
                    0,
                ),
                Err(failure) => {
                    failures.push((slot.clone(), tool.to_owned(), failure.code));
                    append_dynamic_render_warning(
                        &options.design,
                        &slot,
                        tool,
                        failure.code,
                        &failure.diagnostic,
                    );
                    (
                        format!("Review the design plan with a {} lens.", archetype.focus),
                        0,
                    )
                }
            };
            write_required(&prompt, &prompt_text)?;
            let mut row = base_panel_row(
                tool,
                &slot,
                &archetype.focus,
                &round_dir.join(format!("{component}.txt")),
                &prompt,
                payload_bytes,
            );
            row = with_manifest_attribution(
                row,
                (tool == "codex").then_some("review"),
                panel_default_model(&options.tier, tool),
                environment,
            );
            rows.push(row);
        }
    }
    Ok((rows, failures))
}

struct RenderFailure {
    code: i32,
    diagnostic: String,
}

fn render_plan_prompt(
    options: &PanelOptions,
    tool: &str,
    archetype: Option<&str>,
    body: Option<&Path>,
    payload: &Path,
    body_payload: bool,
) -> Result<String, RenderFailure> {
    let mut arguments = vec![
        "render".into(),
        "plan-review".into(),
        "--vendor".into(),
        tool.into(),
    ];
    if let Some(archetype) = archetype {
        arguments.extend(["--archetype".into(), archetype.into()]);
    }
    arguments.extend([
        "--plan-file".into(),
        options.plan_file.clone().into(),
        "--design-tmpdir".into(),
        options.design.as_os_str().to_owned(),
        "--feature-file".into(),
        options.feature_file.clone().into(),
    ]);
    if let Some(body) = body {
        arguments.extend(["--body-file".into(), body.as_os_str().to_owned()]);
    }
    arguments.extend([
        "--findings-ledger-file".into(),
        options
            .design
            .join("findings-ledger.tsv")
            .as_os_str()
            .to_owned(),
        "--payload-bytes-output".into(),
        payload.as_os_str().to_owned(),
        "--difficulty".into(),
        options.tier.clone().into(),
    ]);
    if body_payload {
        arguments.push("--body-file-payload".into());
    }
    let output = run_python_verb(arguments, PYTHON_TIMEOUT).map_err(|message| RenderFailure {
        code: 1,
        diagnostic: message,
    })?;
    if !output.status().success() || output.stdout_truncated() {
        let error = output.stderr();
        let diagnostic = error.first().map_or_else(|| output.stdout(), |_| error);
        return Err(RenderFailure {
            code: output.status().code().unwrap_or(1),
            diagnostic: String::from_utf8_lossy(diagnostic).into_owned(),
        });
    }
    Ok(String::from_utf8_lossy(output.stdout()).into_owned())
}

fn base_panel_row(
    tool: &str,
    slot: &str,
    focus: &str,
    output: &Path,
    prompt: &Path,
    payload_bytes: i64,
) -> Map<String, Value> {
    let mut row = Map::from_iter([
        ("tool".to_owned(), json!(tool)),
        ("slot".to_owned(), json!(slot)),
        ("name".to_owned(), json!(slot)),
        ("focus_area".to_owned(), json!(focus)),
        (
            "prompt_file".to_owned(),
            json!(prompt.display().to_string()),
        ),
        ("output".to_owned(), json!(output.display().to_string())),
    ]);
    if payload_bytes > 0 {
        row.insert("payload_bytes".to_owned(), json!(payload_bytes));
    }
    row
}

fn panel_default_model(tier: &str, tool: &str) -> &'static str {
    if tool == "codex" && tier != "TRIVIAL" {
        CODEX_PLAN_REVIEW_MODEL
    } else {
        ""
    }
}

fn panel_waterfall_arguments(
    options: &PanelOptions,
    manifest: &Path,
    round_dir: &Path,
) -> Vec<OsString> {
    let mut arguments = vec![
        "--slots-file".into(),
        manifest.as_os_str().to_owned(),
        "--panel-artifact-dir".into(),
        round_dir.as_os_str().to_owned(),
        "--panel-round-num".into(),
        options.round_num.to_string().into(),
        "--plan-file".into(),
        options.plan_file.clone().into(),
        "--feature-file".into(),
        options.feature_file.clone().into(),
        "--codex-present".into(),
        bool_text(options.codex_present).into(),
        "--cursor-present".into(),
        bool_text(options.cursor_present).into(),
        "--mode".into(),
        "description".into(),
        "--timeout".into(),
        options.timeout.clone().into(),
        "--skip-invalid-slots".into(),
        "--site".into(),
        "design Step 3".into(),
        "--model-role".into(),
        "review".into(),
        "--difficulty".into(),
        options.tier.clone().into(),
        "--no-fallback".into(),
    ];
    if options.tier != "TRIVIAL" {
        arguments.extend(["--default-model".into(), CODEX_PLAN_REVIEW_MODEL.into()]);
    }
    arguments
}

fn filter_pruned(
    design: &Path,
    manifest: &Path,
    prune_round_num: i64,
) -> Result<BTreeMap<String, String>, String> {
    let default = || {
        BTreeMap::from([
            ("PANEL_PRUNED_EMPTY".to_owned(), "false".to_owned()),
            ("PRUNED_COUNT".to_owned(), "0".to_owned()),
        ])
    };
    if prune_round_num < 2 {
        return Ok(default());
    }
    let pre = design.join("plan-review-slots.pre-prune.ndjson");
    let output = design.join("plan-review-slots.pruned.ndjson");
    let source = fs::read_to_string(manifest).map_err(|error| error.to_string())?;
    write_required(&pre, &source)?;
    let result = run_verified_larch(&[
        "review".into(),
        "reviewer-prune".into(),
        "filter".into(),
        "--ledger".into(),
        design.join("reviewer-prune-ledger.tsv").into_os_string(),
        "--round".into(),
        prune_round_num.to_string().into(),
        "--manifest".into(),
        pre.as_os_str().to_owned(),
        "--out".into(),
        output.as_os_str().to_owned(),
    ]);
    let Ok(result) = result else {
        let mut values = default();
        values.insert("PRUNE_FAIL_OPEN".to_owned(), "true".to_owned());
        return Ok(values);
    };
    if !result.status().success() {
        let mut values = default();
        values.insert("PRUNE_FAIL_OPEN".to_owned(), "true".to_owned());
        return Ok(values);
    }
    let values = parse_dispatch_kv(&String::from_utf8_lossy(result.stdout()));
    let pruned = values
        .get("PRUNED_COUNT")
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or_default();
    if pruned == 0 {
        let _removed = fs::remove_file(&pre);
    } else {
        let filtered = fs::read_to_string(&output).map_err(|error| error.to_string())?;
        write_required(manifest, &filtered)?;
    }
    let _removed = fs::remove_file(output);
    Ok(values)
}

fn write_panel_failure(options: &PanelOptions, code: u8, message: &str) -> Result<(), String> {
    let redacted = redact_sensitive_paths(&redact_secrets_only(message));
    write_required(
        &options.design.join("plan-review-panel-failure.log"),
        &format!("agent dispatch-waterfall exited {code}\n{redacted}"),
    )
}

fn emit_panel_counts(static_count: usize, dynamic_count: usize, prune: &BTreeMap<String, String>) {
    emit_kv("STATIC_SLOT_COUNT", &static_count.to_string());
    emit_kv("DYNAMIC_SLOT_COUNT", &dynamic_count.to_string());
    emit_kv(
        "PANEL_PRUNED_EMPTY",
        prune
            .get("PANEL_PRUNED_EMPTY")
            .map_or("false", String::as_str),
    );
}

fn emit_invalid_slot_warning(outcome: &WaterfallDispatchOutcome) {
    if outcome.invalid_slot_drop_count == 0 {
        return;
    }
    let summary = invalid_slot_drop_summary(&outcome.invalid_slots_file);
    let warning = sanitize_warning(&format!(
        "**⚠ Degraded plan-review panel: {} invalid slot row(s) dropped; continuing with remaining reviewers.**{summary}",
        outcome.invalid_slot_drop_count,
    ));
    emit_kv("INVALID_SLOT_PANEL_WARNING", &warning);
}

fn invalid_slot_drop_summary(path: &str) -> String {
    let Ok(text) = fs::read_to_string(path) else {
        return String::new();
    };
    let labels = text
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter_map(|row| {
            row.get("slot")
                .and_then(Value::as_str)
                .filter(|slot| !slot.is_empty())
                .map(sanitize_slot_label)
                .or_else(|| {
                    row.get("line").and_then(|line| {
                        let value = line
                            .as_str()
                            .map_or_else(|| line.to_string(), ToOwned::to_owned);
                        (!value.is_empty()).then(|| format!("line {value}"))
                    })
                })
        })
        .collect::<Vec<_>>();
    if labels.is_empty() {
        return String::new();
    }
    let shown = labels.iter().take(3).cloned().collect::<Vec<_>>();
    let suffix = if labels.len() > shown.len() {
        format!(", +{} more", labels.len() - shown.len())
    } else {
        String::new()
    };
    format!(" Dropped: {}{suffix}.", shown.join(", "))
}

fn dynamic_render_warning(failures: &[(String, String, i32)]) -> String {
    if failures.is_empty() {
        return String::new();
    }
    let names = failures
        .iter()
        .map(|(slot, _tool, _code)| sanitize_slot_label(slot))
        .filter(|slot| !slot.is_empty())
        .collect::<Vec<_>>();
    let shown = names.iter().take(3).cloned().collect::<Vec<_>>();
    let suffix = if names.len() > shown.len() {
        format!(", +{} more", names.len() - shown.len())
    } else {
        String::new()
    };
    let detail = if shown.is_empty() {
        String::new()
    } else {
        format!(" Fallback slots: {}{suffix}.", shown.join(", "))
    };
    sanitize_warning(&format!(
        "**⚠ Degraded plan-review panel: {} dynamic render failure(s); using fallback prompts.**{detail}",
        failures.len(),
    ))
}

fn append_dynamic_render_warning(
    design: &Path,
    slot: &str,
    tool: &str,
    code: i32,
    diagnostic: &str,
) {
    let detail = sanitize_warning(&redact_sensitive_paths(&redact_secrets_only(diagnostic)));
    let mut entry = format!(
        "- **Dynamic plan-review render failed for {} ({tool}, exit {code}); using fallback prompt.**",
        sanitize_slot_label(slot),
    );
    if !detail.is_empty() {
        entry.push(' ');
        entry.push_str(&detail);
    }
    let _ignored = crate::run_log_entry_commands::append_execution_issue(
        &design.join("execution-issues.md"),
        "Warnings",
        &entry,
    );
}

fn sanitize_slot_label(value: &str) -> String {
    sanitize_warning(value).chars().take(200).collect()
}

fn sanitize_warning(value: &str) -> String {
    value.replace(['\r', '\n', '\t'], " ").trim().to_owned()
}

fn safe_component(value: &str) -> String {
    value
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-') {
                character
            } else {
                '_'
            }
        })
        .collect()
}

fn emit_optional(key: &str, value: &str) {
    if !value.is_empty() {
        emit_kv(key, value);
    }
}

struct VoterOptions {
    ballot_file: String,
    design: PathBuf,
    codex_available: bool,
    cursor_available: bool,
    scope_anchor: String,
    round_num: u64,
}

fn voter_dispatch(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        println!("{VOTER_USAGE}");
        return ExitCode::SUCCESS;
    }
    let options = match parse_voter_options(arguments) {
        Ok(options) => options,
        Err(message) => return usage_error(VOTER_USAGE, VOTER_PROG, &message, 2),
    };
    match run_voters(&options) {
        Ok(code) => code,
        Err(message) => {
            eprintln!("{VOTER_PROG}: {message}");
            ExitCode::from(2)
        }
    }
}

fn parse_voter_options(arguments: &[OsString]) -> Result<VoterOptions, String> {
    const OPTIONS: [&str; 6] = [
        "--ballot-file",
        "--design-tmpdir",
        "--codex-available",
        "--cursor-available",
        "--scope-anchor-file",
        "--round-num",
    ];
    const REQUIRED: [&str; 5] = [
        "--ballot-file",
        "--design-tmpdir",
        "--codex-available",
        "--cursor-available",
        "--round-num",
    ];
    let parsed = parse(arguments, &OPTIONS, 0);
    require_options(&parsed, &REQUIRED)?;
    if let Some(error) = parsed.error() {
        return Err(error);
    }
    let round_raw = parsed_text(&parsed, "--round-num", "");
    let round_num = round_raw
        .parse::<u64>()
        .ok()
        .filter(|round| *round > 0)
        .ok_or_else(|| "--round-num must be positive".to_owned())?;
    let design = validated_design_tmpdir(&parsed_text(&parsed, "--design-tmpdir", ""), true)?;
    let requested_scope = parsed_text(&parsed, "--scope-anchor-file", "");
    let default_scope = design.join("plan-review-scope-anchor.txt");
    let scope_anchor = if requested_scope.is_empty() {
        default_scope.display().to_string()
    } else {
        requested_scope
    };
    Ok(VoterOptions {
        ballot_file: parsed_text(&parsed, "--ballot-file", ""),
        design,
        codex_available: parse_presence(
            VOTER_PROG,
            "--codex-available",
            &parsed_text(&parsed, "--codex-available", ""),
        )?,
        cursor_available: parse_presence(
            VOTER_PROG,
            "--cursor-available",
            &parsed_text(&parsed, "--cursor-available", ""),
        )?,
        scope_anchor: if Path::new(&scope_anchor).is_file() {
            scope_anchor
        } else {
            String::new()
        },
        round_num,
    })
}

struct VoterPrompts {
    by_slot: BTreeMap<String, BTreeMap<String, String>>,
    payloads: BTreeMap<String, BTreeMap<String, i64>>,
}
#[allow(clippy::too_many_lines)] // Keep the legacy voter state machine contiguous for parity review.
fn run_voters(options: &VoterOptions) -> Result<ExitCode, String> {
    let prep_start = unix_seconds();
    let round_dir = options
        .design
        .join("plan-review")
        .join(format!("round-{}", options.round_num));
    ensure_directory_chain(&round_dir).map_err(|error| error.to_string())?;
    let launched = if options.codex_available || options.cursor_available {
        VOTER_POLICIES.len()
    } else {
        1
    };
    let calibration = fresh_plan_calibration_snapshot(&options.design);
    let prompts = build_voter_prompts(options, launched, calibration.as_deref())?;
    let manifest = options.design.join("plan-voter-slots.ndjson");
    write_voter_manifest(options, launched, &prompts, &manifest)?;
    let prep_end = unix_seconds();
    let external_floor = !options.codex_available && !options.cursor_available;
    let (waterfall, voter_1_retried) =
        dispatch_voter_waterfall(options, &manifest, &round_dir, external_floor);
    if !external_floor {
        record_prep_span(&options.design, options.round_num, prep_start, prep_end);
    }

    let (values, waterfall_ok) = match waterfall {
        Ok(outcome) => (
            parse_dispatch_kv(&render_dispatch_report(&outcome)),
            outcome.dispatch_ok,
        ),
        Err(message) => {
            eprintln!("{}", sanitize_warning(&message));
            (BTreeMap::new(), false)
        }
    };
    let raw_bindings = crate::slot_binding::bind_manifest_slot_outputs(&manifest, &values);
    let bindings = raw_bindings
        .into_iter()
        .map(|(slot, binding)| {
            (
                slot,
                VoterOutputBinding {
                    path: binding.path,
                    tool: binding.tool,
                    dropped: binding.dropped,
                },
            )
        })
        .collect::<BTreeMap<_, _>>();
    let policies = voter_policies();
    let launched_slots = policies
        .iter()
        .take(launched)
        .map(|policy| policy.slot_name.clone())
        .collect::<BTreeSet<_>>();
    let fallback_paths = VOTER_POLICIES
        .iter()
        .map(|policy| {
            (
                policy.slot_name.to_owned(),
                options
                    .design
                    .join(policy.output_name)
                    .display()
                    .to_string(),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let mut states =
        voter_states_from_bindings(&policies, &bindings, &launched_slots, &fallback_paths)
            .map_err(|error| error.to_string())?;
    if external_floor {
        normalize_floor_voter_path(&options.design, &mut states[0])?;
    }
    for state in &mut states {
        if state.status != "skipped" && !completed(&state.path) {
            "failed".clone_into(&mut state.status);
        }
    }
    run_plan_parse_rate_checks(options, &prompts, &mut states);
    for state in &mut states {
        if state.status != "failed" && state.parse_rate_status == "NOT_SUBSTANTIVE" {
            "failed".clone_into(&mut state.status);
        }
    }
    if external_floor {
        mark_floor_placeholders(&mut states);
    }
    let effective = effective_judges(&states);
    let paths_file = write_plan_voter_paths(&options.design, &states)?;
    let dispatch_ok = effective > 0 && waterfall_ok;
    emit_plan_voter_rows(&states, &paths_file, dispatch_ok)?;
    if effective < VOTER_POLICIES.len() {
        let reason = if external_floor { " quota hit" } else { "" };
        let warning = format!(
            "**⚠ Degraded plan-review panel: {effective}/{} effective judges produced substantive vote output.**{reason}",
            VOTER_POLICIES.len(),
        );
        if !external_floor {
            eprintln!("{warning}");
        }
        emit_kv("DEGRADED_PANEL_WARNING", &warning);
        emit_kv("DEGRADED_PANEL", "1");
    }
    emit_kv("VOTER_1_RETRIED", bool_text(voter_1_retried));
    if external_floor || dispatch_ok {
        Ok(ExitCode::SUCCESS)
    } else {
        Ok(ExitCode::FAILURE)
    }
}

fn voter_policies() -> Vec<VoterSlotPolicy> {
    VOTER_POLICIES
        .iter()
        .map(|policy| VoterSlotPolicy {
            slot_name: policy.slot_name.to_owned(),
            primary_tool: policy.primary_tool.to_owned(),
            default_label: policy.default_label.to_owned(),
            semantic_labels: policy
                .semantic_labels
                .iter()
                .map(|(tool, label)| ((*tool).to_owned(), (*label).to_owned()))
                .collect(),
        })
        .collect()
}

fn build_voter_prompts(
    options: &VoterOptions,
    launched: usize,
    calibration: Option<&str>,
) -> Result<VoterPrompts, String> {
    let mut by_slot = BTreeMap::new();
    let mut payloads = BTreeMap::new();
    for policy in VOTER_POLICIES.iter().take(launched) {
        let mut slot_prompts = BTreeMap::new();
        let mut slot_payloads = BTreeMap::new();
        for tool in launchable_tools(policy, options.codex_available, options.cursor_available) {
            let prompt = options.design.join(format!(
                "{}-plan-voter-prompt-{tool}.txt",
                policy.default_label,
            ));
            let payload = render_voter_prompt(options, tool, calibration, &prompt)?;
            slot_prompts.insert(tool.to_owned(), prompt.display().to_string());
            slot_payloads.insert(tool.to_owned(), payload);
        }
        by_slot.insert(policy.slot_name.to_owned(), slot_prompts);
        payloads.insert(policy.slot_name.to_owned(), slot_payloads);
    }
    Ok(VoterPrompts { by_slot, payloads })
}

fn render_voter_prompt(
    options: &VoterOptions,
    tool: &str,
    calibration: Option<&str>,
    prompt: &Path,
) -> Result<i64, String> {
    let payload = payload_sidecar(prompt);
    let _removed = fs::remove_file(&payload);
    let mut arguments = vec![
        "render".into(),
        "voter".into(),
        "--ballot-file".into(),
        options.ballot_file.clone().into(),
        "--panel-role".into(),
        PLAN_VOTER_PANEL_ROLE.into(),
        "--id-grammar".into(),
        "finding-oos".into(),
        "--verification-context".into(),
        "plan".into(),
        "--findings-ledger-file".into(),
        options
            .design
            .join("findings-ledger.tsv")
            .as_os_str()
            .to_owned(),
        "--payload-bytes-output".into(),
        payload.as_os_str().to_owned(),
    ];
    if !options.scope_anchor.is_empty() {
        arguments.extend([
            "--scope-anchor-file".into(),
            options.scope_anchor.clone().into(),
        ]);
    }
    arguments.extend(["--voter-tool".into(), tool.into()]);
    if let Some(calibration) = calibration {
        arguments.extend(["--calibration-stats-file".into(), calibration.into()]);
    }
    let output = run_python_verb(arguments, PYTHON_TIMEOUT)
        .map_err(|_| format!("render voter failed for {tool}"))?;
    let text = String::from_utf8_lossy(output.stdout()).into_owned();
    if !output.status().success() || output.stdout_truncated() || !text.contains(BALLOT_POINTER) {
        return Err(format!("render voter failed for {tool}"));
    }
    write_required(prompt, &text)?;
    Ok(read_payload_bytes(&payload))
}

fn write_voter_manifest(
    options: &VoterOptions,
    launched: usize,
    prompts: &VoterPrompts,
    manifest: &Path,
) -> Result<(), String> {
    let environment = env::vars().collect::<BTreeMap<_, _>>();
    let mut rows = Vec::new();
    for policy in VOTER_POLICIES.iter().take(launched) {
        let mut row = Map::from_iter([
            ("slot".to_owned(), json!(policy.slot_name)),
            ("tool".to_owned(), json!(policy.primary_tool)),
            (
                "output".to_owned(),
                json!(
                    options
                        .design
                        .join(policy.output_name)
                        .display()
                        .to_string()
                ),
            ),
            (
                "prompt_files".to_owned(),
                serde_json::to_value(
                    prompts
                        .by_slot
                        .get(policy.slot_name)
                        .cloned()
                        .unwrap_or_default(),
                )
                .map_err(|error| error.to_string())?,
            ),
            (
                "payload_files".to_owned(),
                serde_json::to_value(
                    prompts
                        .payloads
                        .get(policy.slot_name)
                        .cloned()
                        .unwrap_or_default(),
                )
                .map_err(|error| error.to_string())?,
            ),
            ("model_role".to_owned(), json!("vote")),
        ]);
        row = with_manifest_attribution(row, None, "", &environment);
        rows.push(row);
    }
    write_manifest(manifest, &rows)
}

fn voter_waterfall_arguments(
    options: &VoterOptions,
    manifest: &Path,
    round_dir: &Path,
) -> Vec<OsString> {
    vec![
        "--slots-file".into(),
        manifest.as_os_str().to_owned(),
        "--panel-artifact-dir".into(),
        round_dir.as_os_str().to_owned(),
        "--panel-round-num".into(),
        options.round_num.to_string().into(),
        "--codex-present".into(),
        bool_text(options.codex_available).into(),
        "--cursor-present".into(),
        bool_text(options.cursor_available).into(),
        "--mode".into(),
        "description".into(),
        "--model-role".into(),
        "vote".into(),
        "--site".into(),
        "design Step 3".into(),
        "--timeout".into(),
        (if options.codex_available || options.cursor_available {
            "1860"
        } else {
            "1200"
        })
        .into(),
        "--claude-read-tools-add-dir".into(),
        options.design.as_os_str().to_owned(),
    ]
}

fn dispatch_voter_waterfall(
    options: &VoterOptions,
    manifest: &Path,
    round_dir: &Path,
    external_floor: bool,
) -> (Result<WaterfallDispatchOutcome, String>, bool) {
    let arguments = voter_waterfall_arguments(options, manifest, round_dir);
    let first = dispatch_for_review(&arguments);
    let retry = external_floor
        && first
            .as_ref()
            .ok()
            .and_then(|outcome| outcome.all_output_files.first())
            .is_none_or(|path| floor_voter_needs_retry(Path::new(path)));
    if retry {
        (dispatch_for_review(&arguments), true)
    } else {
        (first, false)
    }
}

fn run_plan_parse_rate_checks(
    options: &VoterOptions,
    prompts: &VoterPrompts,
    states: &mut [VoterSlotState],
) {
    let plugin_root = crate::python_verb::plugin_root_directory().unwrap_or_default();
    for (index, state) in states.iter_mut().enumerate() {
        if matches!(state.status.as_str(), "failed" | "skipped") {
            continue;
        }
        let policy = &VOTER_POLICIES[index];
        let base_tool = base_voter_tool(&state.tool).unwrap_or(policy.primary_tool);
        let prompt = prompts
            .by_slot
            .get(policy.slot_name)
            .and_then(|values| values.get(base_tool).or_else(|| values.values().next()))
            .cloned()
            .unwrap_or_default();
        let arguments = vec![
            "--ballot-file".into(),
            options.ballot_file.clone().into(),
            "--id-grammar".into(),
            "finding-oos".into(),
            "--review-tmpdir".into(),
            options.design.as_os_str().to_owned(),
            "--plugin-root".into(),
            plugin_root.as_os_str().to_owned(),
            "--dispatch-label".into(),
            "plan-review voter-dispatch".into(),
            "--retry-prefix-kind".into(),
            "plan".into(),
            "--launch-mode".into(),
            "description".into(),
            "--slot".into(),
            (index + 1).to_string().into(),
            "--voter-file".into(),
            state.path.clone().into(),
            "--voter-tool".into(),
            state.tool.clone().into(),
            "--prompt-file".into(),
            prompt.into(),
        ];
        crate::voting_commands::parse_rate_retry_status(&arguments)
            .unwrap_or("NOT_SUBSTANTIVE")
            .clone_into(&mut state.parse_rate_status);
    }
}

fn base_voter_tool(label: &str) -> Option<&'static str> {
    ["codex", "cursor", "claude"]
        .into_iter()
        .find(|tool| label == *tool || label.starts_with(&format!("{tool}-")))
}

fn effective_judges(states: &[VoterSlotState]) -> usize {
    states
        .iter()
        .filter(|state| {
            state.status != "failed"
                && state.status != "skipped"
                && state.parse_rate_status != "NOT_SUBSTANTIVE"
                && is_nonempty(&state.path)
        })
        .count()
}

fn mark_floor_placeholders(states: &mut [VoterSlotState]) {
    for state in states.iter_mut().skip(1) {
        "failed".clone_into(&mut state.status);
        "not-run".clone_into(&mut state.parse_rate_status);
    }
}

fn floor_voter_needs_retry(path: &Path) -> bool {
    if !fs::metadata(path).is_ok_and(|metadata| metadata.len() > 0) {
        return true;
    }
    fs::read_to_string(format!("{}.done", path.display()))
        .ok()
        .and_then(|text| text.lines().next().map(str::to_owned))
        .is_some_and(|code| code == "124")
}

fn normalize_floor_voter_path(design: &Path, state: &mut VoterSlotState) -> Result<(), String> {
    let target = design.join(VOTER_POLICIES[0].output_name);
    let source = PathBuf::from(&state.path);
    if source != target {
        for (from, to) in [
            (source.clone(), target.clone()),
            (
                PathBuf::from(format!("{}.done", source.display())),
                PathBuf::from(format!("{}.done", target.display())),
            ),
        ] {
            let _removed = fs::remove_file(&to);
            if from.is_file() {
                fs::rename(&from, &to).map_err(|error| error.to_string())?;
            }
        }
    }
    state.path = target.display().to_string();
    let paths = format!("{}\n", state.path);
    write_required(&design.join("plan-voter-slots.ndjson.output-files"), &paths)?;
    Ok(())
}

fn write_plan_voter_paths(design: &Path, states: &[VoterSlotState]) -> Result<PathBuf, String> {
    let path = design.join("plan-review-voter-paths.txt");
    let mut text = String::new();
    for state in states {
        if state.status != "failed" && is_nonempty(&state.path) {
            text.push_str(&state.path);
            text.push('\n');
        }
    }
    write_required(&path, &text)?;
    Ok(path)
}

fn emit_plan_voter_rows(
    states: &[VoterSlotState],
    paths_file: &Path,
    dispatch_ok: bool,
) -> Result<(), String> {
    let path = paths_file.display().to_string();
    let rows = voter_status_rows(
        states,
        &path,
        VoterRowLayout::PlanReviewInterleaved,
        VoterPathsFilePolicy::Nonempty,
        is_nonempty(&path),
    )
    .map_err(|error| error.to_string())?;
    for (key, value) in rows {
        emit_kv(&key, &value);
    }
    emit_kv("DISPATCH_OK", bool_text(dispatch_ok));
    Ok(())
}

fn help_requested(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

fn require_options(parsed: &ParsedCommandLine, required: &[&str]) -> Result<(), String> {
    if let Some(error) = parsed.value_error() {
        return Err(error.to_owned());
    }
    let missing = required
        .iter()
        .filter(|option| parsed.value(option).is_none())
        .copied()
        .collect::<Vec<_>>();
    if missing.is_empty() {
        Ok(())
    } else {
        Err(format!(
            "the following arguments are required: {}",
            missing.join(", ")
        ))
    }
}

fn parsed_text(parsed: &ParsedCommandLine, option: &str, fallback: &str) -> String {
    parsed.value(option).map_or_else(
        || fallback.to_owned(),
        |value| value.to_string_lossy().into_owned(),
    )
}

fn parse_integer(value: &str, option: &str) -> Result<i64, String> {
    value
        .parse::<i64>()
        .map_err(|_| format!("argument {option}: invalid int value: {value:?}"))
}

fn validated_design_tmpdir(candidate: &str, create: bool) -> Result<PathBuf, String> {
    validate_design_tmpdir(
        candidate,
        env::var_os("TMPDIR").as_deref(),
        &cleanup_cache_sessions_root(
            env::var_os("XDG_CACHE_HOME").as_deref(),
            env::var_os("HOME").as_deref(),
        ),
    )?;
    let path = PathBuf::from(candidate);
    if path.symlink_metadata().is_ok_and(|data| data.is_symlink()) {
        return Err("design-tmpdir: path must not be a symlink".to_owned());
    }
    if create {
        ensure_directory_chain(&path).map_err(|error| error.to_string())?;
    }
    if !path.is_dir() {
        return Err("design-tmpdir: path must name a directory".to_owned());
    }
    fs::canonicalize(path).map_err(|error| error.to_string())
}

fn payload_sidecar(path: &Path) -> PathBuf {
    let mut sidecar = path.as_os_str().to_owned();
    sidecar.push(".payload-bytes");
    PathBuf::from(sidecar)
}

fn write_manifest(path: &Path, rows: &[Map<String, Value>]) -> Result<(), String> {
    let mut text = String::new();
    for row in rows {
        text.push_str(&serde_json::to_string(row).map_err(|error| error.to_string())?);
        text.push('\n');
    }
    write_required(path, &text)
}

fn write_required(path: &Path, text: &str) -> Result<(), String> {
    let (root, target) =
        confined_target(path).ok_or_else(|| format!("cannot safely write {}", path.display()))?;
    atomic_write_utf8_in(&root, &target, text, true, 0o600).map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{
        dynamic_render_warning, panel_default_model, safe_component, sanitize_slot_label,
        voter_policies,
    };

    #[test]
    fn plan_roles_keep_the_shared_three_voter_policy() {
        let policies = voter_policies();
        assert_eq!(policies.len(), 3);
        assert_eq!(policies[0].slot_name, "voter-1");
        assert_eq!(policies[1].default_label, "codex-plan-fidelity");
        assert_eq!(policies[2].semantic_labels["claude"], "claude");
    }

    #[test]
    fn panel_model_tiering_matches_the_migrated_contract() {
        assert_eq!(panel_default_model("TRIVIAL", "codex"), "");
        assert_eq!(panel_default_model("MODERATE", "codex"), "gpt-5.6-terra");
        assert_eq!(panel_default_model("HARD", "cursor"), "");
    }

    #[test]
    fn untrusted_dynamic_names_cannot_escape_the_round_directory() {
        assert_eq!(
            safe_component("dyn-codex-plan-../../bad"),
            "dyn-codex-plan-.._.._bad"
        );
        assert_eq!(sanitize_slot_label("bad\nslot"), "bad slot");
    }

    #[test]
    fn dynamic_warning_is_bounded_and_stable() {
        let warning = dynamic_render_warning(&[
            ("one".to_owned(), "codex".to_owned(), 1),
            ("two".to_owned(), "cursor".to_owned(), 2),
            ("three".to_owned(), "codex".to_owned(), 3),
            ("four".to_owned(), "cursor".to_owned(), 4),
        ]);
        assert!(warning.contains("4 dynamic render failure(s)"));
        assert!(warning.ends_with("one, two, three, +1 more."));
    }
}
