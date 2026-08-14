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
use larch_adapters::{ensure_directory_chain, validate_design_tmpdir};
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
    launcher_support::{
        parse_presence, write_confined_required as write_required,
        write_json_lines_confined as write_manifest,
    },
    python_verb::run_python_verb,
    runtime_entrypoint::run_verified_larch,
    voter_dispatch_commands::{
        VOTER_POLICIES, bool_text, completed, fresh_plan_calibration_snapshot, is_nonempty,
        launchable_tools, read_payload_bytes, record_prep_span, unix_seconds,
    },
    waterfall_commands::{
        WaterfallDispatchOutcome, append_review_routing_arguments, dispatch_for_review,
        parse_dispatch_kv, render_dispatch_report,
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
    /// Emit the reviewed plan and terminal diff-lines value.
    #[command(name = "emit", disable_help_flag = true)]
    Emit(AgentRawArguments),
    /// Emit rejected findings not already represented in the ledger.
    #[command(name = "emit-rejected", disable_help_flag = true)]
    EmitRejected(AgentRawArguments),
    /// Filter Gate B skipped findings from the accepted artifact.
    #[command(name = "filter-gate-b-skipped", disable_help_flag = true)]
    FilterGateBSkipped(AgentRawArguments),
    /// Count accepted Gate B findings.
    #[command(name = "gate-b-counts", disable_help_flag = true)]
    GateBCounts(AgentRawArguments),
    /// Remove duplicate Gate B plan lines.
    #[command(name = "gate-b-dedup", disable_help_flag = true)]
    GateBDedup(AgentRawArguments),
    /// Render the selected Gate B finding line.
    #[command(name = "gate-b-finding-line", disable_help_flag = true)]
    GateBFindingLine(AgentRawArguments),
    /// Persist the accepted-finding audit record.
    #[command(name = "persist-accepted-audit", disable_help_flag = true)]
    PersistAcceptedAudit(AgentRawArguments),
    /// Snapshot the pre-review plan and optional trailers.
    #[command(name = "snapshot-pre-review", disable_help_flag = true)]
    SnapshotPreReview(AgentRawArguments),
    /// Tally plan-review votes and persist round artifacts.
    #[command(name = "tally", disable_help_flag = true)]
    Tally(AgentRawArguments),
}
/// Dispatch one Rust-owned plan-review command.
pub fn run(command: PlanReviewCommand) -> ExitCode {
    match command {
        PlanReviewCommand::PanelDispatch(arguments) => panel_dispatch(&arguments.arguments),
        PlanReviewCommand::VoterDispatch(arguments) => voter_dispatch(&arguments.arguments),
        PlanReviewCommand::Emit(arguments) => emit(&arguments.arguments),
        PlanReviewCommand::EmitRejected(arguments) => emit_rejected(&arguments.arguments),
        PlanReviewCommand::FilterGateBSkipped(arguments) => {
            filter_gate_b_skipped(&arguments.arguments)
        }
        PlanReviewCommand::GateBCounts(arguments) => gate_b_counts(&arguments.arguments),
        PlanReviewCommand::GateBDedup(arguments) => gate_b_dedup(&arguments.arguments),
        PlanReviewCommand::GateBFindingLine(arguments) => gate_b_finding_line(&arguments.arguments),
        PlanReviewCommand::PersistAcceptedAudit(arguments) => {
            persist_accepted_audit(&arguments.arguments)
        }
        PlanReviewCommand::SnapshotPreReview(arguments) => {
            snapshot_pre_review(&arguments.arguments)
        }
        PlanReviewCommand::Tally(arguments) => tally(&arguments.arguments),
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
    ];
    append_review_routing_arguments(
        &mut arguments,
        "design Step 3",
        &options.tier,
        (options.tier != "TRIVIAL").then_some(CODEX_PLAN_REVIEW_MODEL),
    );
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
// Rust owners for the plan-review tally, Gate B, and accepted-finding audit.

// Keep this compatibility owner at a wider width so the nine-command atomic cutover
// stays near the migration program's review-size budget.
#[rustfmt::skip]
mod implementation {
    #![allow(clippy::cast_precision_loss, clippy::format_collect, clippy::format_push_string, clippy::if_not_else, clippy::option_if_let_else, clippy::struct_field_names, clippy::suboptimal_flops, clippy::too_many_lines)] // Frozen scoring arithmetic, table rendering, and transaction order intentionally mirror Python.

    use crate::argparse_compat::{ParsedCommandLine, parse_required_with_help as parsed, parse_with_flags, usage_error};
    use larch_adapters::{TemporaryRoot, atomic_write_utf8_in, ensure_directory_chain, remove_file_if_present, validate_design_tmpdir};
    use larch_core::review::{
        BoundaryMode, FINDINGS_CLASSIFICATION_HEADER, ItemAdjudicationResult, ItemContext, ItemKind, LedgerRow, adjudicate_item, alias_ballot_id, ballot_blocks, classify_plan_review_gate_b, filter_plan_review_gate_b_skipped, finding_dedup_key, is_security_block_text, parse_blocks, parse_judge_vote_text, parse_plan_review_accepted_findings, plan_review_gate_b_display_rows, reviewer_for_block_text,
        grow_reviewer_labels, proposer_map_item_mismatch, slot_human_label, split_classification_attribution, vote_for_id_text, write_round,
    };
    use larch_core::{cleanup_cache_sessions_root, file_line_regex, private_atomic_write, python_float, split_lines_keep_ends, split_text_lines, terminal_plan_trailer_value, trim_python_whitespace};
    use regex::Regex;
    use sha2::{Digest as _, Sha256};
    use std::{
        collections::{BTreeMap, BTreeSet, HashSet},
        env,
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        process::ExitCode,
    };

    const EMIT_USAGE: &str = "usage: cli.py plan-review emit [-h] --design-tmpdir DESIGN_TMPDIR";
    const EMIT_REJECTED_USAGE: &str = "usage: cli.py plan-review emit-rejected [-h] --design-tmpdir DESIGN_TMPDIR\n                                        [--report-framing]";
    const COUNTS_USAGE: &str = "usage: cli.py plan-review gate-b-counts [-h] --design-tmpdir DESIGN_TMPDIR";
    const FINDING_LINE_USAGE: &str = "usage: cli.py plan-review gate-b-finding-line [-h] --design-tmpdir\n                                              DESIGN_TMPDIR --finding-id\n                                              FINDING_ID [--ordinal ORDINAL]";
    const DEDUP_USAGE: &str = "usage: cli.py plan-review gate-b-dedup [-h] --design-tmpdir DESIGN_TMPDIR\n                                       [--snapshot-trailers] [--dedup]";
    const SNAPSHOT_USAGE: &str = "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR";
    const FILTER_USAGE: &str = "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR --accepted ACCEPTED\n              --rejected REJECTED";
    const AUDIT_USAGE: &str = "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR\n              (--assessment {clean} | --assessment-file ASSESSMENT_FILE)";
    const EMIT_HELP: &str = "usage: cli.py plan-review emit [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR";
    const EMIT_REJECTED_HELP: &str = "usage: cli.py plan-review emit-rejected [-h] --design-tmpdir DESIGN_TMPDIR\n                                        [--report-framing]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --report-framing";
    const COUNTS_HELP: &str = "usage: cli.py plan-review gate-b-counts [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR";
    const FINDING_LINE_HELP: &str = "usage: cli.py plan-review gate-b-finding-line [-h] --design-tmpdir\n                                              DESIGN_TMPDIR --finding-id\n                                              FINDING_ID [--ordinal ORDINAL]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --finding-id FINDING_ID\n  --ordinal ORDINAL";
    const DEDUP_HELP: &str = "usage: cli.py plan-review gate-b-dedup [-h] --design-tmpdir DESIGN_TMPDIR\n                                       [--snapshot-trailers] [--dedup]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --snapshot-trailers\n  --dedup";
    const SNAPSHOT_HELP: &str = "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR\n\nSnapshot plan.txt before a /design Step 3 review entry\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR";
    const FILTER_HELP: &str = "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR --accepted ACCEPTED\n              --rejected REJECTED\n\nFilter Gate B one-by-one skipped findings from accepted findings\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --accepted ACCEPTED\n  --rejected REJECTED";
    const AUDIT_HELP: &str = "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR\n              (--assessment {clean} | --assessment-file ASSESSMENT_FILE)\n\nPersist the Gate C accepted-findings audit\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --assessment {clean}\n  --assessment-file ASSESSMENT_FILE";
    const TALLY_USAGE: &str = "usage: tally-plan-review.sh --ballot-file FILE [--voter SLOT:FILE...|POS:TOOL:FILE...] [--voter-files FILE...] --design-tmpdir DIR [--findings-classification-out FILE]";
    const REPORT_HEADING: &str = "## Considered Plan Review Suggestions (Not Adopted)";
    const REPORT_NOTE: &str = "These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.";

    fn option(parsed: &ParsedCommandLine, name: &str) -> String {
        parsed.value(name).map_or_else(String::new, |value| value.to_string_lossy().into_owned())
    }
    fn design_root(raw: &str, require_existing: bool) -> Result<PathBuf, String> {
        validate_design_tmpdir(raw, env::var_os("TMPDIR").as_deref(), &cleanup_cache_sessions_root(env::var_os("XDG_CACHE_HOME").as_deref(), env::var_os("HOME").as_deref()))?;
        let path = PathBuf::from(raw);
        if require_existing && !path.is_dir() {
            return Err("design-tmpdir: path must name a directory".to_owned());
        }
        if !path.exists() {
            fs::create_dir_all(&path).map_err(|error| error.to_string())?;
        }
        fs::canonicalize(path).map_err(|error| error.to_string())
    }
    fn command_root(raw: &str, program: &str) -> Result<PathBuf, ExitCode> {
        let path = Path::new(raw);
        if !path.is_dir() {
            eprintln!("{program}: DESIGN_TMPDIR required");
            return Err(ExitCode::from(2));
        }
        if path.is_symlink() {
            eprintln!("{program}: design-tmpdir must not be a symlink");
            return Err(ExitCode::from(2));
        }
        design_root(raw, true).map_err(|message| {
            eprintln!("{program}: {message}");
            ExitCode::from(2)
        })
    }
    fn write(root: &Path, path: &Path, text: &str) -> Result<(), String> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
        private_atomic_write(path, text, root).map_err(|error| error.to_string())
    }
    fn read_text(path: &Path) -> Result<String, String> {
        fs::read(path).map(|bytes| String::from_utf8_lossy(&bytes).replace("\r\n", "\n").replace('\r', "\n")).map_err(|error| format!("{}: {error}", path.display()))
    }
    fn optional_text(path: &Path) -> Result<String, String> {
        if path.is_file() && !path.is_symlink() { read_text(path) } else { Ok(String::new()) }
    }
    fn best_effort_text(path: &Path) -> String {
        read_text(path).unwrap_or_default()
    }
    fn accepted(root: &Path) -> Result<Vec<larch_core::review::PlanReviewAcceptedFinding>, String> {
        optional_text(&root.join("accepted-plan-findings.md")).map(|text| parse_plan_review_accepted_findings(&text))
    }
    fn positive(raw: &str, option_name: &str, usage: &str, program: &str) -> Result<String, ExitCode> {
        if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) || raw.bytes().all(|byte| byte == b'0') {
            return Err(usage_error(usage, program, &format!("argument {option_name}: requires a non-empty positive integer"), 2));
        }
        Ok(raw.trim_start_matches('0').to_owned())
    }
    fn before_help(arguments: &[OsString]) -> &[OsString] {
        let end = arguments.iter().position(|argument| { let text = argument.to_string_lossy(); let (name, inline) = crate::argparse_compat::split_inline_option(&text); inline.is_none() && crate::argparse_compat::resolve_option(name, &["-h", "--help"]).is_some() }).unwrap_or(arguments.len());
        &arguments[..end]
    }
    fn validate_finding_prefix(arguments: &[OsString]) -> Result<(), ExitCode> {
        let parsed = parse_with_flags(before_help(arguments), &["--design-tmpdir", "--finding-id", "--ordinal"], &["-h", "--help"], 0);
        for (name, value) in parsed.entries().iter().filter(|(name, _)| matches!(*name, "--finding-id" | "--ordinal")) { positive(&value.to_string_lossy(), name, FINDING_LINE_USAGE, "cli.py plan-review gate-b-finding-line")?; }
        if let Some(error) = parsed.value_error() { return Err(usage_error(FINDING_LINE_USAGE, "cli.py plan-review gate-b-finding-line", error, 2)); }
        Ok(())
    }
    fn validate_audit_prefix(arguments: &[OsString]) -> Result<(), ExitCode> {
        let parsed = parse_with_flags(before_help(arguments), &["--design-tmpdir", "--assessment", "--assessment-file"], &["-h", "--help"], 0); let mut action = None;
        for (name, value) in parsed.entries().iter().filter(|(name, _)| matches!(*name, "--assessment" | "--assessment-file")) {
            let value = value.to_string_lossy();
            if *name == "--assessment" && value != "clean" { return Err(usage_error(AUDIT_USAGE, "cli.py", &format!("argument --assessment: invalid choice: '{value}' (choose from 'clean')"), 2)); }
            if let Some(previous) = action.filter(|previous| previous != name) { return Err(usage_error(AUDIT_USAGE, "cli.py", &format!("argument {name}: not allowed with argument {previous}"), 2)); }
            action = Some(*name);
        }
        if let Some(error) = parsed.value_error() { return Err(usage_error(AUDIT_USAGE, "cli.py", error, 2)); }
        Ok(())
    }

    #[must_use]
    pub fn emit(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py plan-review emit", EMIT_USAGE, EMIT_HELP, &["--design-tmpdir"], &[], &["--design-tmpdir"]) { Ok(value) => value, Err(code) => return code };
        let root = match command_root(&option(&parsed, "--design-tmpdir"), "cli.py plan-review emit") { Ok(value) => value, Err(code) => return code };
        let plan_text = match optional_text(&root.join("plan.txt")) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review emit: {error}");
                return ExitCode::FAILURE;
            }
        };
        let Some(raw_lines) = terminal_plan_trailer_value(&plan_text, "diff_lines") else {
            println!("EMIT_PLAN_STATUS=missing-diff-lines");
            return ExitCode::FAILURE;
        };
        let lines = { let normalized = raw_lines.trim_start_matches('0'); if normalized.is_empty() { "0" } else { normalized } };
        if let Err(error) = write(&root, &root.join("diff-lines.txt"), &format!("{lines}\n")) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
        println!("EMIT_PLAN_STATUS=ok\nDIFF_LINES={lines}");
        ExitCode::SUCCESS
    }

    fn format_rejected(body: String, framing: bool) -> String {
        if framing && !body.is_empty() { format!("{REPORT_HEADING}\n\n{REPORT_NOTE}\n\n{body}") } else { body }
    }
    fn applied_keys(root: &Path) -> Result<BTreeSet<String>, String> {
        let mut keys = larch_core::review::all_applied_finding_keys(&optional_text(&root.join(".step3-applied-finding-keys.tsv"))?);
        keys.extend(split_text_lines(&optional_text(&root.join(".step3-already-addressed-finding-keys.tsv"))?).into_iter().map(trim_python_whitespace).filter(|line| !line.is_empty()).map(str::to_owned));
        Ok(keys)
    }
    fn filter_wrapped(text: &str, applied: &BTreeSet<String>) -> Option<String> {
        let marker = Regex::new(r"(?m)^### \[Plan Review\] ").expect("static wrapper regex");
        let matches = marker.find_iter(text).collect::<Vec<_>>();
        if matches.is_empty() {
            return None;
        }
        let mut out = text[..matches[0].start()].to_owned();
        for (index, found) in matches.iter().enumerate() {
            let end = matches.get(index + 1).map_or(text.len(), regex::Match::start);
            let block = &text[found.start()..end];
            let finding = parse_blocks(block, BoundaryMode::ItemHeading).into_iter().find(|item| item.kind == ItemKind::Finding);
            let candidate = finding.as_ref().map_or(block, |item| &block[..block.find(&item.block).unwrap_or(0) + item.block.len()]);
            if applied.contains(&finding_dedup_key(candidate)) || block.to_lowercase().contains("[already_addressed]") {
                out.push_str(&block[candidate.len()..]);
            } else {
                out.push_str(block);
            }
        }
        Some(out)
    }
    fn filter_canonical(text: &str, applied: &BTreeSet<String>) -> Option<String> {
        let blocks = parse_blocks(text, BoundaryMode::ItemHeading).into_iter().filter(|item| item.kind == ItemKind::Finding).collect::<Vec<_>>();
        if blocks.is_empty() {
            return None;
        }
        let first = text.find(&blocks[0].block).unwrap_or(0);
        let mut out = text[..first].to_owned();
        for block in blocks {
            if !applied.contains(&finding_dedup_key(&block.block)) && !block.block.to_lowercase().contains("[already_addressed]") {
                out.push_str(&block.block);
            }
        }
        Some(out)
    }
    #[must_use]
    pub fn emit_rejected(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py plan-review emit-rejected", EMIT_REJECTED_USAGE, EMIT_REJECTED_HELP, &["--design-tmpdir"], &["--report-framing"], &["--design-tmpdir"]) { Ok(value) => value, Err(code) => return code };
        let root = match command_root(&option(&parsed, "--design-tmpdir"), "cli.py plan-review emit-rejected") { Ok(value) => value, Err(code) => return code };
        let path = root.join("rejected-findings.md");
        if !path.is_file() || path.is_symlink() {
            return ExitCode::SUCCESS;
        }
        let text = match read_text(&path) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review emit-rejected: {error}");
                return ExitCode::FAILURE;
            }
        };
        if trim_python_whitespace(&text).is_empty() {
            return ExitCode::SUCCESS;
        }
        let keys = match applied_keys(&root) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review emit-rejected: {error}");
                return ExitCode::FAILURE;
            }
        };
        let tagged = text.to_lowercase().contains("[already_addressed]");
        let output = if keys.is_empty() && !tagged {
            text
        } else if let Some(body) = filter_wrapped(&text, &keys).or_else(|| filter_canonical(&text, &keys)) {
            body
        } else {
            eprintln!("WARN=emit-rejected: applied-finding ledger present but rejected-findings.md has no recognizable blocks; emitting empty body");
            String::new()
        };
        print!("{}", format_rejected(output, parsed.flag("--report-framing")));
        ExitCode::SUCCESS
    }

    #[must_use]
    pub fn gate_b_counts(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py plan-review gate-b-counts", COUNTS_USAGE, COUNTS_HELP, &["--design-tmpdir"], &["--preview"], &["--design-tmpdir"]) { Ok(value) => value, Err(code) => return code };
        let root = match command_root(&option(&parsed, "--design-tmpdir"), "cli.py plan-review gate-b-counts") { Ok(value) => value, Err(code) => return code };
        let findings = match accepted(&root) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review gate-b-counts: {error}");
                return ExitCode::FAILURE;
            }
        };
        if parsed.flag("--preview") {
            println!("## Plan Review Findings: Review\n");
            for row in plan_review_gate_b_display_rows(&findings) {
                println!("FINDING_{} | {} | {} | {}", row.finding_id, row.display_severity_label, row.reviewer_text, row.excerpt);
            }
            for (name, heading) in [("rejected-findings.md", "## Rejected Findings: Context"), ("oos.md", "## Out-of-Scope Findings: Context")] {
                let text = match optional_text(&root.join(name)) {
                    Ok(value) => value,
                    Err(error) => {
                        eprintln!("cli.py plan-review gate-b-counts: {error}");
                        return ExitCode::FAILURE;
                    }
                };
                if !trim_python_whitespace(&text).is_empty() {
                    print!("\n{heading}\n\n{text}{}", if text.ends_with('\n') { "" } else { "\n" });
                }
            }
            return ExitCode::SUCCESS;
        }
        let summary = classify_plan_review_gate_b(&findings);
        let ids = summary.finding_ids.join(",");
        println!("ACCEPTED_COUNT={}\nHIGH_ACCEPTED_COUNT={}\nMEDIUM_ACCEPTED_COUNT={}\nLOW_ACCEPTED_COUNT={}\nCRITICAL_ACCEPTED_COUNT={}\nGATE_B_SEVERITY_MODE={}\nFINDING_IDS={ids}", findings.len(), summary.high_count, summary.medium_count, summary.low_count, summary.critical_count, summary.mode);
        ExitCode::SUCCESS
    }

    #[must_use]
    pub fn gate_b_finding_line(arguments: &[OsString]) -> ExitCode {
        if let Err(code) = validate_finding_prefix(arguments) { return code; }
        let parsed = match parsed(arguments, "cli.py plan-review gate-b-finding-line", FINDING_LINE_USAGE, FINDING_LINE_HELP, &["--design-tmpdir", "--finding-id", "--ordinal"], &[], &["--design-tmpdir", "--finding-id"]) { Ok(value) => value, Err(code) => return code };
        let finding_id = option(&parsed, "--finding-id").trim_start_matches('0').to_owned();
        let root = match command_root(&option(&parsed, "--design-tmpdir"), "cli.py plan-review gate-b-finding-line") { Ok(value) => value, Err(code) => return code };
        let findings = match accepted(&root) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review gate-b-finding-line: {error}");
                return ExitCode::FAILURE;
            }
        };
        let rows = plan_review_gate_b_display_rows(&findings);
        let Some((index, row)) = rows.iter().enumerate().find(|(_, row)| row.finding_id == finding_id) else {
            eprintln!("cli.py plan-review gate-b-finding-line: unknown finding id FINDING_{finding_id}");
            return ExitCode::FAILURE;
        };
        let ordinal = if let Some(value) = parsed.value("--ordinal") {
            match positive(&value.to_string_lossy(), "--ordinal", FINDING_LINE_USAGE, "cli.py plan-review gate-b-finding-line") {
                Ok(value) => value.parse::<usize>().unwrap_or(usize::MAX),
                Err(code) => return code,
            }
        } else {
            index + 1
        };
        if ordinal > rows.len() || rows[ordinal - 1].finding_id != finding_id {
            eprintln!("cli.py plan-review gate-b-finding-line: ordinal does not match FINDING_{finding_id}");
            return ExitCode::FAILURE;
        }
        let detail = match (row.reviewer_text.is_empty(), row.excerpt.is_empty()) {
            (false, false) => format!("{}: {}", row.reviewer_text, row.excerpt),
            (false, true) => row.reviewer_text.clone(),
            _ => row.excerpt.clone(),
        };
        let prompt = if detail.is_empty() { format!("FINDING_{finding_id} [{}] — Apply this finding to the plan?", row.display_severity_label) } else { format!("FINDING_{finding_id} [{}] — {detail}. Apply this finding to the plan?", row.display_severity_label) };
        println!("FINDING_ID={finding_id}\nDISPLAY_SEVERITY={}\nREVIEWER_TEXT={}\nCONCERN_EXCERPT={}\nONE_BY_ONE_ORDINAL={ordinal}\nONE_BY_ONE_TOTAL={}\nONE_BY_ONE_HEADER=Finding {ordinal}/{}\nONE_BY_ONE_PROMPT_LINE={prompt}", row.display_severity_label, row.reviewer_text, row.excerpt, rows.len(), rows.len());
        ExitCode::SUCCESS
    }

    fn trailer_map(text: &str) -> BTreeMap<String, String> {
        let regex = Regex::new(r"^([a-z_]+):[\s\x{1c}-\x{1f}]*(.*?)[\s\x{1c}-\x{1f}]*$").expect("static trailer regex");
        let allowed = ["diff_added", "diff_deleted", "mechanical_churn", "oversize_override"];
        split_text_lines(text).into_iter().filter_map(|line| regex.captures(line)).filter(|row| allowed.contains(&&row[1])).map(|row| (row[1].to_owned(), row[2].to_owned())).collect()
    }
    fn sha256(text: &str) -> String {
        format!("{:x}", Sha256::digest(text.as_bytes()))
    }
    #[must_use]
    pub fn gate_b_dedup(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py plan-review gate-b-dedup", DEDUP_USAGE, DEDUP_HELP, &["--design-tmpdir"], &["--snapshot-trailers", "--dedup"], &["--design-tmpdir"]) { Ok(value) => value, Err(code) => return code };
        let root = match command_root(&option(&parsed, "--design-tmpdir"), "cli.py plan-review gate-b-dedup") { Ok(value) => value, Err(code) => return code };
        let plan = root.join("plan.txt");
        let original = match optional_text(&plan) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review gate-b-dedup: {error}");
                return ExitCode::FAILURE;
            }
        };
        let keys = root.join(".gate-b-optional-trailer-keys");
        let values = root.join(".gate-b-optional-trailer-keys.values");
        if parsed.flag("--snapshot-trailers") {
            let trailers = trailer_map(&original);
            let key_text = trailers.keys().map(|key| format!("{key}\n")).collect::<String>();
            let value_text = trailers.iter().map(|(key, value)| format!("{key}={value}\n")).collect::<String>();
            if write(&root, &keys, &key_text).and_then(|()| write(&root, &values, &value_text)).is_err() {
                return ExitCode::FAILURE;
            }
            println!("GATE_B_DEDUP_STATUS=snapshot-ok");
            return ExitCode::SUCCESS;
        }
        if !parsed.flag("--dedup") {
            return usage_error(DEDUP_USAGE, "cli.py plan-review gate-b-dedup", "one of --snapshot-trailers or --dedup is required", 2);
        }
        if !keys.is_file() || keys.is_symlink() || !values.is_file() || values.is_symlink() {
            println!("GATE_B_DEDUP_STATUS=missing-snapshot");
            return ExitCode::from(3);
        }
        let snapshot_text = match read_text(&keys) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("cli.py plan-review gate-b-dedup: {error}");
                return ExitCode::FAILURE;
            }
        };
        let snapshot = split_text_lines(&snapshot_text).into_iter().map(trim_python_whitespace).filter(|line| !line.is_empty()).collect::<BTreeSet<_>>();
        let current = trailer_map(&original);
        let current_keys = current.keys().map(String::as_str).collect::<BTreeSet<_>>();
        if snapshot != current_keys {
            println!("GATE_B_DEDUP_STATUS=trailer-key-drift");
            return ExitCode::FAILURE;
        }
        let mut seen = HashSet::new();
        let mut removed = 0;
        let mut lines = Vec::new();
        let trailer = Regex::new(r"^[a-z_]+:[\s\x{1c}-\x{1f}]*").expect("static trailer regex");
        for line in split_text_lines(&original) {
            if trailer.is_match(line) {
                lines.push(line);
            } else if !line.is_empty() && !seen.insert(line) {
                removed += 1;
            } else {
                lines.push(line);
            }
        }
        let output = format!("{}{}", lines.join("\n"), if original.ends_with('\n') { "\n" } else { "" });
        if write(&root, &plan, &output).is_err() {
            return ExitCode::FAILURE;
        }
        let authority = root.join(".gate-b-oversize-override.sha256");
        let trusted = authority.is_file() && !authority.is_symlink() && trim_python_whitespace(&best_effort_text(&authority)) == sha256(&original);
        let authority_result = if terminal_plan_trailer_value(&output, "oversize_override") == Some("operator") && trusted {
            write(&root, &authority, &format!("{}\n", sha256(&output)))
        } else {
            remove_file_if_present(&authority)
        };
        if let Err(error) = authority_result {
            eprintln!("cli.py plan-review gate-b-dedup: {error}");
            return ExitCode::FAILURE;
        }
        println!("dedup-sweep: removed {removed} duplicate line(s) from plan.txt\nGATE_B_DEDUP_STATUS=ok");
        ExitCode::SUCCESS
    }

    fn audit_error(operation: &str, error: &str, input: bool) -> ExitCode {
        if input {
            eprintln!("ERROR: {error}");
            ExitCode::from(2)
        } else {
            eprintln!("ERROR: {operation} failed: {error}");
            ExitCode::FAILURE
        }
    }
    fn audit_root(raw: &str) -> Result<PathBuf, ExitCode> {
        design_root(raw, true).map_err(|error| audit_error("", &error, true))
    }
    fn existing_under(root: &Path, raw: &str, label: &str) -> Result<PathBuf, String> {
        let path = PathBuf::from(raw);
        if path.is_symlink() {
            return Err(format!("{label}: refusing symlink file"));
        }
        if !path.is_file() {
            return Err(format!("{label}: file is required"));
        }
        let resolved = fs::canonicalize(path).map_err(|_| format!("{label}: file resolution failed"))?;
        if !resolved.starts_with(root) {
            return Err(format!("{label}: path must stay under design-tmpdir"));
        }
        Ok(resolved)
    }
    fn optional_under(root: &Path, raw: &str, label: &str) -> Result<PathBuf, String> {
        let path = PathBuf::from(raw);
        if path.is_symlink() {
            return Err(format!("{label}: refusing symlink file"));
        }
        if path.exists() {
            return existing_under(root, raw, label);
        }
        let parent = fs::canonicalize(path.parent().unwrap_or_else(|| Path::new(""))).map_err(|_| format!("{label}: parent resolution failed"))?;
        let resolved = parent.join(path.file_name().unwrap_or_default());
        if !resolved.starts_with(root) {
            return Err(format!("{label}: path must stay under design-tmpdir"));
        }
        Ok(resolved)
    }
    #[must_use]
    pub fn snapshot_pre_review(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py", SNAPSHOT_USAGE, SNAPSHOT_HELP, &["--design-tmpdir"], &[], &["--design-tmpdir"]) { Ok(value) => value, Err(code) => return code };
        let root = match audit_root(&option(&parsed, "--design-tmpdir")) { Ok(value) => value, Err(code) => return code };
        let plan = match existing_under(&root, &root.join("plan.txt").to_string_lossy(), "plan.txt") {
            Ok(value) => value,
            Err(error) => return audit_error("", &error, true),
        };
        let text = match read_text(&plan) {
            Ok(value) => value,
            Err(error) => return audit_error("snapshot-pre-review", &error, false),
        };
        match write(&root, &root.join("plan-before-review.txt"), &text) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => audit_error("snapshot-pre-review", &error, false),
        }
    }
    #[must_use]
    pub fn filter_gate_b_skipped(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py", FILTER_USAGE, FILTER_HELP, &["--design-tmpdir", "--accepted", "--rejected"], &[], &["--design-tmpdir", "--accepted", "--rejected"]) { Ok(value) => value, Err(code) => return code };
        let root = match audit_root(&option(&parsed, "--design-tmpdir")) { Ok(value) => value, Err(code) => return code };
        let accepted = match existing_under(&root, &option(&parsed, "--accepted"), "accepted") {
            Ok(value) => value,
            Err(error) => return audit_error("", &error, true),
        };
        let rejected = match optional_under(&root, &option(&parsed, "--rejected"), "rejected") {
            Ok(value) => value,
            Err(error) => return audit_error("", &error, true),
        };
        let accepted_text = match read_text(&accepted) {
            Ok(value) => value,
            Err(error) => return audit_error("filter-gate-b-skipped", &error, false),
        };
        let rejected_text = if rejected.is_file() {
            match read_text(&rejected) {
                Ok(value) => value,
                Err(error) => return audit_error("filter-gate-b-skipped", &error, false),
            }
        } else {
            String::new()
        };
        print!("{}", filter_plan_review_gate_b_skipped(&accepted_text, &rejected_text));
        ExitCode::SUCCESS
    }
    #[must_use]
    pub fn persist_accepted_audit(arguments: &[OsString]) -> ExitCode {
        if let Err(code) = validate_audit_prefix(arguments) { return code; }
        let parsed = match parsed(arguments, "cli.py", AUDIT_USAGE, AUDIT_HELP, &["--design-tmpdir", "--assessment", "--assessment-file"], &[], &["--design-tmpdir"]) { Ok(value) => value, Err(code) => return code };
        let group_action = parsed.entries().iter().rev().find(|(name, _)| matches!(*name, "--assessment" | "--assessment-file")).map(|(name, _)| *name);
        let assessment = option(&parsed, "--assessment");
        let assessment_file = option(&parsed, "--assessment-file");
        if group_action.is_none() {
            return usage_error(AUDIT_USAGE, "cli.py", "one of the arguments --assessment --assessment-file is required", 2);
        }
        let root = match audit_root(&option(&parsed, "--design-tmpdir")) { Ok(value) => value, Err(code) => return code };
        let text = if assessment == "clean" {
            "Accepted plan-review audit: no concerns.\n".to_owned()
        } else {
            let path = match existing_under(&root, &assessment_file, "assessment-file") {
                Ok(value) => value,
                Err(error) => return audit_error("", &error, true),
            };
            let value = match read_text(&path) {
                Ok(value) => trim_python_whitespace(&value).to_owned(),
                Err(error) => return audit_error("persist-accepted-audit", &error, false),
            };
            if value.is_empty() {
                return audit_error("", "assessment-file: content is required", true);
            }
            format!("{value}\n")
        };
        match write(&root, &root.join("accepted-plan-findings-audit.md"), &text) {
            Ok(()) => {
                println!("ACCEPTED_AUDIT_STATUS=ok");
                ExitCode::SUCCESS
            }
            Err(error) => audit_error("persist-accepted-audit", &error, false),
        }
    }

    #[derive(Default)]
    struct TallyArgs { design: String, ballot: String, findings: String, proposer_map: String, voters: Vec<String>, voter_files: Vec<String>, seen_voters: bool, seen_files: bool }
    fn tally_args(arguments: &[OsString]) -> Result<Option<TallyArgs>, ExitCode> {
        let args = arguments.iter().map(|value| value.to_string_lossy().into_owned()).collect::<Vec<_>>();
        let mut out = TallyArgs::default();
        let mut index = 0;
        while index < args.len() {
            let arg = &args[index];
            if matches!(arg.as_str(), "-h" | "--help") {
                eprintln!("{TALLY_USAGE}");
                return Ok(None);
            }
            let target = match arg.as_str() {
                "--design-tmpdir" => Some(&mut out.design),
                "--ballot-file" => Some(&mut out.ballot),
                "--findings-classification-out" => Some(&mut out.findings),
                "--proposer-map-file" => Some(&mut out.proposer_map),
                "--voter" => {
                    out.seen_voters = true;
                    None
                }
                "--voter-files" => {
                    out.seen_files = true;
                    index += 1;
                    while index < args.len() && !args[index].starts_with("--") {
                        out.voter_files.push(args[index].clone());
                        index += 1;
                    }
                    continue;
                }
                _ => {
                    eprintln!("tally-plan-review.sh: unknown argument: {arg}\n{TALLY_USAGE}");
                    return Err(ExitCode::from(2));
                }
            };
            if index + 1 >= args.len() {
                eprintln!("{} requires {}", arg, if arg == "--voter" { "SLOT:PATH" } else { "a value" });
                return Err(ExitCode::from(2));
            }
            index += 1;
            if arg == "--voter" {
                out.voters.push(args[index].clone());
            } else if let Some(target) = target {
                args[index].clone_into(target);
            }
            index += 1;
        }
        if out.design.is_empty() || out.ballot.is_empty() {
            eprintln!("tally-plan-review.sh: --design-tmpdir and --ballot-file are required\n{TALLY_USAGE}");
            return Err(ExitCode::from(2));
        }
        Ok(Some(out))
    }

    #[derive(Clone, Default)]
    struct VoterSlot { tool: String, path: String, text: String }
    #[derive(Default)]
    struct ProposerMap { rows: BTreeMap<String, (String, String)>, neutral_hash: String, unreadable: bool }
    fn proposer_map(path: &Path) -> ProposerMap {
        let mut map = ProposerMap::default();
        let Ok(text) = read_text(path) else { map.unreadable = true; return map; };
        for line in split_text_lines(&text) {
            if let Some(value) = line.strip_prefix("# neutral_ballot_sha256=") {
                trim_python_whitespace(value).clone_into(&mut map.neutral_hash);
                continue;
            }
            let cells = line.split('\t').map(trim_python_whitespace).collect::<Vec<_>>();
            if cells.len() == 3 && matches!(cells[0].split_once('_'), Some(("FINDING" | "OOS", digits)) if !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit())) && !cells[1].is_empty() && !cells[2].is_empty() {
                map.rows.insert(cells[0].to_owned(), (trim_python_whitespace(&cells[1].replace('*', "")).to_owned(), cells[2].to_owned()));
            }
        }
        map
    }
    fn neutralized(text: &str) -> bool {
        parse_blocks(text, BoundaryMode::ItemHeading).into_iter().find_map(|parsed| split_text_lines(&parsed.block).into_iter().find_map(reviewer_line_value)).is_some_and(|value| value.eq_ignore_ascii_case("anonymous"))
    }
    fn reviewer_line_value(line: &str) -> Option<String> {
        let regex = Regex::new(r"^[\s\x{1c}-\x{1f}-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)[\s\x{1c}-\x{1f}]*:[\s\x{1c}-\x{1f}]*(.*?)[ \t]*$").expect("static reviewer regex");
        regex.captures(line).map(|found| trim_python_whitespace(&found[1].replace('*', "")).to_owned())
    }
    fn restore_reviewer(block: &str, line: &str) -> String {
        if line.is_empty() {
            return block.to_owned();
        }
        let mut lines = split_lines_keep_ends(block).into_iter().map(str::to_owned).collect::<Vec<_>>();
        for current in &mut lines {
            let newline = if current.ends_with('\n') { "\n" } else { "" };
            if reviewer_line_value(current.trim_end_matches('\n')).is_some() {
                if reviewer_line_value(current.trim_end_matches('\n')).is_some_and(|value| value.eq_ignore_ascii_case("anonymous")) {
                    *current = format!("{line}{newline}");
                }
                return lines.concat();
            }
        }
        block.find('\n').map_or_else(|| format!("{block}\n{line}\n"), |pos| format!("{}\n{line}\n{}", &block[..pos], &block[pos + 1..]))
    }
    fn infer_slot(path: &str, index: usize) -> String {
        let base = Path::new(path).file_name().unwrap_or_default().to_string_lossy().to_lowercase();
        for (needle, label) in [("codex-validity-vote-output", "codex-validity"), ("cursor-validity-vote-output", "cursor-validity"), ("codex-plan-fidelity-vote-output", "codex-plan-fidelity"), ("cursor-plan-fidelity-vote-output", "cursor-plan-fidelity"), ("codex-pragmatism-vote-output", "codex-pragmatism"), ("cursor-pragmatism-vote-output", "cursor-pragmatism")] {
            if base.contains(needle) {
                return label.to_owned();
            }
        }
        if base.contains("claude") {
            "Claude".to_owned()
        } else if base.contains("codex") {
            "Codex".to_owned()
        } else if base.contains("cursor") {
            "Cursor".to_owned()
        } else {
            ["Claude", "Codex", "Cursor"][index.min(2)].to_owned()
        }
    }
    fn position(tool: &str, path: &str, slots: &[VoterSlot; 3]) -> usize {
        let base = Path::new(path).file_name().unwrap_or_default().to_string_lossy().to_lowercase();
        let needles = [
            ["voter-1", "voter1", "slot1", "slot-1", "claude-vote-output", "codex-validity-vote-output", "cursor-validity-vote-output"],
            ["voter-2", "voter2", "slot2", "slot-2", "codex-vote-output", "codex-plan-fidelity-vote-output", "cursor-plan-fidelity-vote-output"],
            ["voter-3", "voter3", "slot3", "slot-3", "cursor-vote-output", "codex-pragmatism-vote-output", "cursor-pragmatism-vote-output"],
        ];
        for (index, group) in needles.iter().enumerate() {
            if group.iter().any(|needle| base.contains(needle)) {
                return index;
            }
        }
        let preferred = match tool {
            "Claude" | "claude" | "codex-validity" | "cursor-validity" => Some(0),
            "Codex" | "codex-plan-fidelity" | "cursor-plan-fidelity" => Some(1),
            "Cursor" | "codex-pragmatism" | "cursor-pragmatism" => Some(2),
            _ => None,
        };
        preferred.filter(|index| slots[*index].path.is_empty()).or_else(|| slots.iter().position(|slot| slot.path.is_empty())).unwrap_or(3)
    }
    fn canonical_tool(slot: &str) -> String {
        match slot {
            "Claude" => "Claude",
            "Codex" => "Codex",
            "Cursor" => "Cursor",
            "1" => "codex-validity",
            "2" => "codex-plan-fidelity",
            "3" => "codex-pragmatism",
            value => value,
        }
        .to_owned()
    }
    fn canonical_position(slot: &str) -> usize {
        match slot {
            "1" | "Claude" | "claude" | "codex-validity" | "cursor-validity" => 0,
            "2" | "Codex" | "codex-plan-fidelity" | "cursor-plan-fidelity" => 1,
            "3" | "Cursor" | "codex-pragmatism" | "cursor-pragmatism" => 2,
            _ => 3,
        }
    }

    struct Tally { args: TallyArgs, root: PathBuf, findings: PathBuf, tally: PathBuf, tally_display: PathBuf, slots: [VoterSlot; 3], main: Option<VoterSlot>, eligible: usize, blocks: Vec<(String, String)>, map: ProposerMap, map_required: bool }
    impl Tally {
        fn error(&self, diagnostic: &str, stub: &str, classification: bool) -> ExitCode {
            eprintln!("{diagnostic}");
            if !stub.is_empty() && let Err(error) = write(&self.root, &self.tally, &format!("# Plan Review Voting Tally\n\n{stub}\n")) {
                let error = if self.tally.is_dir() { format!("[Errno 21] Is a directory: '{}'", self.tally.display()) } else { error };
                return self.unexpected(&error);
            }
            if classification && let Err(error) = outside_atomic(&self.root, &self.findings, &format!("{FINDINGS_CLASSIFICATION_HEADER}\n")) {
                return self.unexpected(&error);
            }
            if self.tally.metadata().is_ok_and(|meta| meta.len() > 0) {
                println!("VOTING_TALLY_FILE={}", self.tally_display.display());
            }
            println!("TALLY_PLAN_REVIEW_STATUS=tally-error");
            ExitCode::from(2)
        }
        fn unexpected(&self, error: &str) -> ExitCode {
            eprintln!("tally-plan-review: unexpected error: {error}");
            if self.tally.metadata().is_ok_and(|meta| meta.len() > 0) {
                println!("VOTING_TALLY_FILE={}", self.tally_display.display());
            }
            println!("TALLY_PLAN_REVIEW_STATUS=tally-error");
            ExitCode::from(2)
        }
        fn assign(&mut self, slot: usize, tool: String, path: String) -> Result<(), ExitCode> {
            if slot >= 3 {
                return Err(self.error("tally-plan-review.sh: too many voters; expected at most three non-MainAgent voters", "**⚠ Tally aborted: too many voters; at most three non-MainAgent voters allowed.**", true));
            }
            if !self.slots[slot].path.is_empty() {
                return Err(self.error(&format!("error: duplicate voter position {}", slot + 1), &format!("**⚠ Tally aborted: duplicate voter position {}.**", slot + 1), true));
            }
            self.slots[slot] = VoterSlot { tool, path, text: String::new() };
            Ok(())
        }
        fn resolve_voters(&mut self) -> Result<(), ExitCode> {
            if self.args.seen_voters {
                for spec in self.args.voters.clone() {
                    let Some((slot, tail)) = spec.split_once(':') else {
                        return Err(self.error(&format!("error: invalid voter slot: {spec} (must be 1|2|3|Claude|Codex|Cursor|MainAgent)"), &format!("**⚠ Tally aborted: invalid voter slot: {spec}; no votes tallied.**"), false));
                    };
                    let valid = ["1", "2", "3", "Claude", "Codex", "Cursor", "codex-validity", "cursor-validity", "codex-plan-fidelity", "cursor-plan-fidelity", "codex-pragmatism", "cursor-pragmatism", "claude", "MainAgent"];
                    if !valid.contains(&slot) {
                        return Err(self.error(&format!("error: invalid voter slot: {slot} (must be 1|2|3|Claude|Codex|Cursor|MainAgent)"), &format!("**⚠ Tally aborted: invalid voter slot: {slot}; no votes tallied.**"), false));
                    }
                    let (tool, path) = if matches!(slot, "1" | "2" | "3") { tail.split_once(':').filter(|(tool, _)| !tool.is_empty()).map_or_else(|| (canonical_tool(slot), tail.to_owned()), |(tool, path)| (tool.to_owned(), path.to_owned())) } else { (canonical_tool(slot), tail.to_owned()) };
                    self.args.voter_files.push(path.clone());
                    if slot == "MainAgent" {
                        self.main = Some(VoterSlot { tool, path, text: String::new() });
                    } else {
                        self.assign(canonical_position(slot), tool, path)?;
                    }
                }
            } else {
                if self.args.seen_files {
                    eprintln!("deprecated: --voter-files; use --voter <SLOT>:<PATH>");
                }
                for (index, path) in self.args.voter_files.clone().into_iter().enumerate() {
                    let tool = infer_slot(&path, index);
                    let slot = position(&tool, &path, &self.slots);
                    self.assign(slot, tool, path)?;
                }
            }
            if self.main.is_some() && (self.slots.iter().any(|slot| !slot.path.is_empty()) || self.args.voters.len() > 1) {
                return Err(self.error("error: --voter MainAgent is only valid as the sole voter (0-judge fallback path)", "**⚠ Tally aborted: --voter MainAgent is only valid as the sole voter; no votes tallied.**", true));
            }
            if let Some(path) = self.args.voter_files.iter().find(|path| path.is_empty() || !Path::new(path).is_file() || fs::read(path).is_err()) {
                let path = path.to_owned();
                return Err(self.error(&format!("tally-plan-review.sh: voter file is missing or unreadable: {path}"), &format!("**⚠ Tally aborted: voter file unreadable: {path}; no votes tallied.**"), true));
            }
            self.eligible = if self.main.is_some() { 1 } else { self.slots.iter().filter(|slot| !slot.path.is_empty()).count() };
            let texts = self.slots.iter().chain(self.main.iter()).map(|slot| if slot.path.is_empty() { Ok(String::new()) } else { read_text(Path::new(&slot.path)).map_err(|_| slot.path.clone()) }).collect::<Result<Vec<_>, _>>();
            let texts = match texts {
                Ok(value) => value,
                Err(path) => {
                    return Err(self.error(&format!("tally-plan-review.sh: voter file is missing or unreadable: {path}"), &format!("**⚠ Tally aborted: voter file unreadable: {path}; no votes tallied.**"), true));
                }
            };
            for (slot, text) in self.slots.iter_mut().chain(self.main.iter_mut()).zip(texts) {
                slot.text = text;
            }
            Ok(())
        }
        fn context(&self, item_id: &str, block: &str, ids: &HashSet<String>) -> Result<ItemContext, ExitCode> {
            let alias = alias_ballot_id(item_id, ids);
            let (mut cells, voter_votes, severities) = if let Some(main) = &self.main {
                let parsed = parse_judge_vote_text(item_id, &main.text, &alias);
                (Vec::new(), vec![("MainAgent".to_owned(), vote_for_id_text(item_id, &main.text, &alias).to_owned())], vec![parsed.severity])
            } else {
                let mut cells = Vec::new();
                let mut votes = Vec::new();
                let mut severities = Vec::new();
                for slot in &self.slots {
                    if slot.path.is_empty() {
                        cells.push((String::new(), String::new(), String::new(), String::new(), String::new(), Some(slot.tool.clone())));
                    } else {
                        let parsed = parse_judge_vote_text(item_id, &slot.text, &alias);
                        let vote = vote_for_id_text(item_id, &slot.text, &alias).to_owned();
                        cells.push((vote.clone(), parsed.correctness, parsed.severity.clone(), parsed.quality, parsed.uncertain, Some(slot.tool.clone())));
                        votes.push((slot.tool.clone(), vote));
                        severities.push(parsed.severity);
                    }
                }
                (cells, votes, severities)
            };
            while cells.len() < 3 {
                cells.push((String::new(), String::new(), String::new(), String::new(), String::new(), None));
            }
            let yes = voter_votes.iter().filter(|(_, vote)| vote == "YES").count();
            let no = voter_votes.iter().filter(|(_, vote)| vote == "NO").count();
            let raw_reviewer = reviewer_for_block_text(block);
            let reviewer = if raw_reviewer.eq_ignore_ascii_case("anonymous") && self.map_required {
                match self.map.rows.get(item_id) {
                    Some((reviewer, _)) if !reviewer.eq_ignore_ascii_case("anonymous") && !reviewer.is_empty() => reviewer.clone(),
                    _ => {
                        return Err(self.error(&format!("tally-plan-review.sh: missing proposer map entry for neutralized item {item_id}"), &format!("**⚠ Tally aborted: missing proposer attribution for {item_id}; no votes tallied.**"), true));
                    }
                }
            } else {
                raw_reviewer
            };
            let line = self.map.rows.get(item_id).map_or("", |row| row.1.as_str());
            Ok(ItemContext { item_id: item_id.to_owned(), block_path: PathBuf::new(), block_text: block.to_owned(), artifact_text: restore_reviewer(block, line), reviewer, cells, yes, no, judge_error: voter_votes.len() - yes - no, is_oos: item_id.starts_with("OOS_"), eligible_voters: self.eligible, voter_votes, voter_severities: severities })
        }
    }

    fn outside_atomic(root: &Path, path: &Path, text: &str) -> Result<(), String> {
        if path.starts_with(root) {
            let trusted = TemporaryRoot::resolve(Some(root)).map_err(|error| error.to_string())?;
            return atomic_write_utf8_in(&trusted, path, text, true, 0o600).map_err(|error| error.to_string());
        }
        let parent = path.parent().ok_or_else(|| "findings output has no parent".to_owned())?;
        ensure_directory_chain(parent).map_err(|error| error.to_string())?;
        let trusted = TemporaryRoot::resolve(Some(parent)).map_err(|error| error.to_string())?;
        let target = trusted.path().join(path.file_name().ok_or_else(|| "findings output has no file name".to_owned())?);
        atomic_write_utf8_in(&trusted, &target, text, false, 0o600).map_err(|error| error.to_string())
    }
    fn sorted_blocks(mut blocks: Vec<(String, String)>) -> Vec<(String, String)> {
        blocks.retain(|(id, _)| matches!(id.split_once('_'), Some(("FINDING" | "OOS", digits)) if digits.bytes().all(|byte| byte.is_ascii_digit())));
        blocks.sort_by_key(|(id, _)| { let digits = id.split_once('_').map_or("", |(_, value)| value).trim_start_matches('0'); let digits = if digits.is_empty() { "0" } else { digits }; (if id.starts_with("FINDING_") { 1 } else { 2 }, digits.len(), digits.to_owned()) });
        blocks
    }
    fn tsv_cell(value: &str) -> String {
        let mut cell = value.replace(['\t', '\n'], " ");
        if cell.bytes().next().is_some_and(|byte| (b'+'..=b'@').contains(&byte)) {
            cell.insert(0, '\'');
        }
        cell
    }
    fn body_severity(block: &str) -> String {
        let regex = Regex::new(r"^[\s\x{1c}-\x{1f}-]*\*\*Severity\*\*:[ \t]*").expect("static severity regex");
        split_text_lines(block).into_iter().find(|line| regex.is_match(line)).map_or_else(String::new, |line| regex.replace(line, "").trim_end_matches([' ', '\t']).to_owned())
    }
    fn ledger_title(block: &str, item_id: &str) -> String {
        let regex = Regex::new(&format!(r"^###[\s\x{{1c}}-\x{{1f}}]+{}:[\s\x{{1c}}-\x{{1f}}]*", regex::escape(item_id))).expect("escaped title regex");
        let title = trim_python_whitespace(&regex.replace(split_text_lines(block).first().copied().unwrap_or(""), "")).to_owned();
        if title.is_empty() { item_id.to_owned() } else { title }
    }
    fn ledger_file_line(block: &str) -> String {
        for name in ["long-re", "short-path-re", "short-line-re", "extensionless-re", "any-re", "long-exts", "short-exts"] {
            let regex = Regex::new(&file_line_regex(name).expect("known regex")).expect("static file regex");
            if let Some(found) = regex.find(block) {
                return found.as_str().trim_matches(|character: char| " \t\n\r`*()[],:;".contains(character)).to_owned();
            }
        }
        String::new()
    }
    fn ledger_reason(block: &str) -> String {
        let regex = Regex::new(r"(?i)^[- ]*(Concern|Scenario|Reason|Suggested (revision|fix)):[\s\x{1c}-\x{1f}]*").expect("static reason regex");
        split_text_lines(block)
            .into_iter()
            .skip(1)
            .find_map(|line| {
                let clean = trim_python_whitespace(&line.replace('*', "")).to_owned();
                regex.is_match(&clean).then(|| trim_python_whitespace(&regex.replace(&clean, "")).to_owned())
            })
            .unwrap_or_default()
    }

    #[derive(Default)]
    struct ReviewerStat { proposed: usize, accepted: usize, neutral: usize, rejected: usize, oos_proposed: usize, oos_accepted: usize, oos_neutral: usize, oos_rejected: usize, accepted_weight: f64, bonus: f64 }
    #[derive(Default)]
    struct AgreementStat { eligible: usize, agree: usize, disagree: usize, missing: usize }
    #[derive(Default)]
    struct SeverityStat { yes: usize, major: usize, minor: usize, nit: usize, missing: usize }
    fn attribution_labels(tally: &Tally) -> Result<Vec<String>, String> {
        let mut labels = Vec::new();
        let mut add = |value: &str| {
            for part in value.split(',').map(trim_python_whitespace).filter(|part| !part.is_empty()) {
                if !labels.iter().any(|known| known == part) {
                    labels.push(part.to_owned());
                }
            }
        };
        for line in split_text_lines(&optional_text(&tally.root.join("plan-review-prune-label-map.tsv"))?) {
            if let Some(value) = line.split('\t').nth(1) {
                add(value);
            }
        }
        for slot in &tally.slots {
            add(&slot.tool);
        }
        for line in split_text_lines(&optional_text(&tally.root.join("panel-manifest.ndjson"))?) {
            if let Ok(row) = serde_json::from_str::<serde_json::Value>(line) && let Some(slot) = row.get("slot").and_then(|value| value.as_str()) {
                add(&slot_human_label(slot));
            }
        }
        grow_reviewer_labels(&mut labels, tally.map.rows.values().map(|(reviewer, _)| reviewer.clone()));
        grow_reviewer_labels(&mut labels, tally.blocks.iter().map(|(_, block)| reviewer_for_block_text(block)));
        Ok(labels)
    }
    fn reviewer_scoreboard(tally: &Tally, results: &[ItemAdjudicationResult], bonus: f64) -> Result<(String, usize), String> {
        let labels = attribution_labels(tally)?;
        let mut rows: BTreeMap<String, ReviewerStat> = BTreeMap::new();
        let mut rewarded = 0;
        for result in results {
            let mut reviewers = split_classification_attribution(&result.context.reviewer, "finding_reviewers", &labels);
            if reviewers.is_empty() {
                reviewers = result.context.reviewer.split(',').map(trim_python_whitespace).filter(|value| !value.is_empty()).map(str::to_owned).collect();
            }
            let active = result.unique_finder_eligible && reviewers.len() == 1 && bonus > 0.0;
            if active {
                rewarded += 1;
            }
            for reviewer in reviewers {
                let row = rows.entry(reviewer).or_default();
                if result.score_kind == "finding" {
                    row.proposed += 1;
                    match result.score_result.as_str() {
                        "accepted" => {
                            row.accepted += 1;
                            row.accepted_weight += f64::from(result.accepted_weight);
                            if active {
                                row.bonus += bonus;
                            }
                        }
                        "neutral" => row.neutral += 1,
                        _ => row.rejected += 1,
                    }
                } else {
                    row.oos_proposed += 1;
                    match result.score_result.as_str() {
                        "accepted" => row.oos_accepted += 1,
                        "neutral" => row.oos_neutral += 1,
                        _ => row.oos_rejected += 1,
                    }
                }
            }
        }
        let output = rows
            .into_iter()
            .map(|(reviewer, row)| {
                let score = row.accepted_weight - row.neutral as f64 * 0.25 + row.oos_accepted as f64 - row.rejected as f64 - row.oos_rejected as f64 + row.bonus;
                format!("| {reviewer} | {} | {} | {} | {} | {} | {} | {} | {} | {} |\n", row.proposed, row.accepted, row.neutral, row.rejected, row.oos_proposed, row.oos_accepted, row.oos_neutral, row.oos_rejected, crate::voting_commands::format_score(score))
            })
            .collect();
        Ok((output, rewarded))
    }
    fn voter_scoreboards(tally: &Tally, results: &[ItemAdjudicationResult]) -> String {
        let mut agreement: BTreeMap<String, AgreementStat> = BTreeMap::new();
        let mut severity: BTreeMap<String, SeverityStat> = BTreeMap::new();
        if tally.main.is_none() {
            for result in results {
                if !matches!(result.voting_result.as_str(), "accepted" | "rejected") {
                    continue;
                }
                let parseable = result.context.cells.iter().filter(|cell| matches!(cell.0.as_str(), "YES" | "NO")).count();
                if parseable < 2 {
                    continue;
                }
                for (index, cell) in result.context.cells.iter().enumerate() {
                    let label = cell.5.as_deref().filter(|value| !value.is_empty()).unwrap_or(["codex-validity", "codex-plan-fidelity", "codex-pragmatism"][index]);
                    let vote = if cell.0 == "JUDGE_ERROR" { "" } else { &cell.0 };
                    let row = agreement.entry(label.to_owned()).or_default();
                    if matches!(vote, "YES" | "NO") {
                        row.eligible += 1;
                        if (result.voting_result == "accepted" && vote == "YES") || (result.voting_result == "rejected" && vote == "NO") {
                            row.agree += 1;
                        } else {
                            row.disagree += 1;
                        }
                    } else {
                        row.missing += 1;
                    }
                    let severity_row = severity.entry(label.to_owned()).or_default();
                    if vote == "YES" {
                        severity_row.yes += 1;
                        match trim_python_whitespace(&cell.2).to_lowercase().as_str() {
                            "major" | "blocker" => severity_row.major += 1,
                            "minor" => severity_row.minor += 1,
                            "nit" => severity_row.nit += 1,
                            _ => severity_row.missing += 1,
                        }
                    }
                }
            }
        }
        let mut out = "## Voter Agreement Scoreboard\n\n| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |\n|---|---|---:|---:|---:|---:|---:|---|\n".to_owned();
        if agreement.is_empty() {
            out.push_str("| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |\n\nAgreement is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n");
        } else {
            for (voter, row) in &agreement {
                let rate = if row.agree + row.disagree == 0 { "n/a".to_owned() } else { format!("{:.3}", row.agree as f64 / (row.agree + row.disagree) as f64) };
                let outlier = row.eligible >= 20 && rate.parse::<f64>().is_ok_and(|value| value < 0.5);
                out.push_str(&format!("| design | {voter} | {} | {} | {} | {} | {rate} | {outlier} |\n", row.eligible, row.agree, row.disagree, row.missing));
            }
        }
        out.push_str("\n## Voter Severity Scoreboard\n\n| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n");
        if severity.is_empty() {
            out.push_str("| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |\n\nSeverity calibration is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n");
        } else {
            for (voter, row) in severity {
                let valid = row.major + row.minor + row.nit;
                let (rate, calibration, uncalibrated) = if valid == 0 {
                    ("n/a".to_owned(), "n/a".to_owned(), false)
                } else {
                    let value = row.major as f64 / valid as f64;
                    let score = if value <= 0.9 { 1.0 } else { (1.0 - ((value - 0.9) / 0.1)).clamp(0.0, 1.0) };
                    (format!("{value:.3}"), format!("{score:.3}"), value > 0.9)
                };
                out.push_str(&format!("| design | {voter} | {} | {} | {} | {} | {} | {rate} | {calibration} | {uncalibrated} |\n", row.yes, row.major, row.minor, row.nit, row.missing));
            }
        }
        out
    }
    fn trailing_newline(text: &str) -> String {
        if text.ends_with('\n') { text.to_owned() } else { format!("{text}\n") }
    }
    fn artifact_blocks(text: &str) -> Vec<String> {
        let normalized = text.replace("\r\n", "\n").replace('\r', "\n");
        if trim_python_whitespace(&normalized).is_empty() {
            return Vec::new();
        }
        let parsed = parse_blocks(&normalized, BoundaryMode::ItemHeading);
        if parsed.is_empty() {
            return vec![trailing_newline(&normalized)];
        }
        let first_byte = normalized.char_indices().nth(parsed[0].start).map_or(normalized.len(), |(index, _)| index);
        let mut blocks = Vec::new();
        if !trim_python_whitespace(&normalized[..first_byte]).is_empty() {
            blocks.push(trailing_newline(&normalized[..first_byte]));
        }
        blocks.extend(parsed.into_iter().filter(|block| !trim_python_whitespace(&block.block).is_empty()).map(|block| trailing_newline(&block.block)));
        blocks
    }
    fn append_chunks(root: &Path, path: &Path, chunks: &[String], unique: bool) -> Result<(), String> {
        if chunks.is_empty() {
            return Ok(());
        }
        let existing = optional_text(path)?;
        let added = if unique {
            let mut seen = artifact_blocks(&existing).into_iter().collect::<HashSet<_>>();
            chunks.iter().flat_map(|chunk| artifact_blocks(chunk)).filter(|block| seen.insert(block.clone())).collect::<String>()
        } else {
            chunks.concat()
        };
        if added.is_empty() {
            return Ok(());
        }
        let separator = if unique && !existing.is_empty() && !existing.ends_with('\n') { "\n" } else { "" };
        write(root, path, &format!("{existing}{separator}{added}"))
    }
    fn round_num(path: &Path) -> u64 {
        let parts = path.components().map(|part| part.as_os_str().to_string_lossy()).collect::<Vec<_>>();
        parts.windows(2).find_map(|parts| (parts[0] == "plan-review").then(|| parts[1].strip_prefix("round-").and_then(|value| value.parse().ok())).flatten()).unwrap_or(1)
    }
    fn classification(tally: &Tally, results: &[ItemAdjudicationResult]) -> Result<String, String> {
        let mut out = format!("{FINDINGS_CLASSIFICATION_HEADER}\n");
        for result in results {
            let mut row = vec![result.context.item_id.clone(), tsv_cell(&result.context.reviewer), if tally.main.is_some() { "rejected".to_owned() } else { result.voting_result.clone() }];
            for cell in &result.context.cells {
                row.extend([tsv_cell(if cell.0 == "JUDGE_ERROR" { "" } else { &cell.0 }), tsv_cell(&cell.1), tsv_cell(&cell.2), tsv_cell(&cell.3), tsv_cell(&cell.4), tsv_cell(cell.5.as_deref().unwrap_or(""))]);
            }
            row.push(tsv_cell(&body_severity(&result.context.block_text)));
            row.push(result.classification_scope.clone());
            out.push_str(&row.join("\t"));
            out.push('\n');
        }
        outside_atomic(&tally.root, &tally.findings, &out)?;
        Ok(out)
    }
    fn write_ledger(tally: &Tally, results: &[ItemAdjudicationResult]) -> Result<(), String> {
        let rows = results.iter().map(|result| LedgerRow::new(round_num(&tally.findings), &result.context.item_id, &ledger_title(&result.context.block_text, &result.context.item_id), &ledger_file_line(&result.context.block_text), &result.ledger_outcome, &format!("YES={}/{}", result.context.yes, tally.eligible), &ledger_reason(&result.context.block_text))).collect();
        write_round(&tally.root, round_num(&tally.findings), rows).map_err(|error| error.to_string())
    }
    fn render_tally(tally: &Tally, results: &[ItemAdjudicationResult]) -> Result<(), String> {
        let bonus = env::var("LARCH_UNIQUE_FINDER_BONUS").ok().and_then(|value| python_float(&value)).filter(|value| value.is_finite() && *value > 0.0).unwrap_or(0.0);
        let mut out = "# Plan Review Voting Tally\n\n".to_owned();
        if tally.main.is_some() {
            out.push_str("**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-adjudicated.**\n\n");
        } else if tally.eligible < 3 {
            let tier = ["main-agent-required", "single-judge", "unanimous-2"][tally.eligible];
            out.push_str(&format!("**⚠ Degraded plan-review panel: {} judge(s) available. Panel tier: {tier}.**\n\n", tally.eligible));
        }
        out.push_str("## Findings\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n");
        let mut accepted = Vec::new();
        let mut rejected = Vec::new();
        let mut oos = Vec::new();
        let mut oos_accepted = Vec::new();
        let mut oos_pool = Vec::new();
        let mut security_oos = Vec::new();
        for result in results {
            let context = &result.context;
            out.push_str(&format!("| {} | {} | {} | {} | {} |\n", context.item_id, context.yes, context.no, context.judge_error, result.voting_result));
            if !context.is_oos {
                if result.voting_result == "accepted" {
                    accepted.push(format!("{}\n", context.artifact_text));
                } else if !result.reroute_marker.is_empty() {
                    let artifact = format!("{}\nVote tally: YES={} NO={} JUDGE_ERROR={} Result={} ({})\n\n", context.artifact_text, context.yes, context.no, context.judge_error, result.voting_result, result.reroute_marker);
                    if result.security == Some(true) {
                        security_oos.push(artifact);
                    } else {
                        oos.push(artifact);
                    }
                } else {
                    rejected.push(format!("### [Plan Review] {}\n\n{}\n", context.item_id, context.artifact_text));
                }
            } else {
                let artifact = format!("{}\nVote tally: YES={} NO={} JUDGE_ERROR={} Result={} Fileable={}\n\n", context.artifact_text, context.yes, context.no, context.judge_error, result.voting_result, result.fileable_oos);
                if result.security == Some(true) {
                    security_oos.push(artifact);
                } else {
                    oos.push(artifact.clone());
                    if result.fileable_oos {
                        oos_pool.push(artifact);
                        oos_accepted.push(format!("{}\n", context.artifact_text));
                    }
                }
            }
        }
        out.push_str("\n## Reviewer Competition Scoreboard\n\n| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n");
        let (scores, rewarded) = reviewer_scoreboard(tally, results, bonus)?;
        out.push_str(&scores);
        if bonus > 0.0 && rewarded > 0 {
            out.push_str(&format!("\n**Unique finder bonus active:** {rewarded} accepted in-scope sole-finder finding(s) received +{} each.\n", crate::voting_commands::format_score(bonus)));
        }
        out.push('\n');
        out.push_str(&voter_scoreboards(tally, results));
        write(&tally.root, &tally.tally, &out)?;
        append_chunks(&tally.root, &tally.root.join("accepted-plan-findings.md"), &accepted, false)?;
        append_chunks(&tally.root, &tally.root.join("accepted-plan-findings-all.md"), &accepted, true)?;
        append_chunks(&tally.root, &tally.root.join("rejected-findings.md"), &rejected, false)?;
        append_chunks(&tally.root, &tally.root.join("oos.md"), &oos, false)?;
        append_chunks(&tally.root, &tally.root.join("oos-accepted-design.md"), &oos_accepted, true)?;
        append_chunks(&tally.root, &tally.root.join("oos-aggregate-pool.md"), &oos_pool, true)?;
        append_chunks(&tally.root, &tally.root.join("security-oos-observations.md"), &security_oos, true)
    }

    #[must_use]
    pub fn tally(arguments: &[OsString]) -> ExitCode {
        let args = match tally_args(arguments) {
            Ok(Some(value)) => value,
            Ok(None) => return ExitCode::SUCCESS,
            Err(code) => return code,
        };
        let root = match design_root(&args.design, false) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::from(2);
            }
        };
        let findings = if args.findings.is_empty() { root.join("plan-review/round-1/findings-classification.tsv") } else { PathBuf::from(&args.findings) };
        let tally_path = root.join("voting-tally.md");
        let tally_display = PathBuf::from(&args.design).join("voting-tally.md");
        let mut tally = Tally { args, root, findings, tally: tally_path, tally_display, slots: Default::default(), main: None, eligible: 0, blocks: Vec::new(), map: ProposerMap::default(), map_required: false };
        let ballot_path = PathBuf::from(&tally.args.ballot);
        let preflight_ballot = read_text(&ballot_path).ok().filter(|_| ballot_path.is_file()).unwrap_or_default();
        let is_neutral = neutralized(&preflight_ballot);
        if tally.args.proposer_map.is_empty() && is_neutral && tally.root.join("proposer-map.tsv").is_file() {
            tally.args.proposer_map = tally.root.join("proposer-map.tsv").to_string_lossy().into_owned();
        }
        tally.map_required = is_neutral || !tally.args.proposer_map.is_empty();
        if !tally.args.proposer_map.is_empty() {
            tally.map = proposer_map(Path::new(&tally.args.proposer_map));
        }
        if is_neutral && !tally.args.proposer_map.is_empty() {
            let ballot_ids = parse_blocks(&preflight_ballot, BoundaryMode::ItemHeading).into_iter().filter(|block| matches!(block.kind, ItemKind::Finding | ItemKind::Oos)).map(|block| block.item_id).collect::<BTreeSet<_>>();
            let map_ids = tally.map.rows.keys().cloned().collect::<BTreeSet<_>>();
            let map_error = if !Path::new(&tally.args.proposer_map).is_file() {
                Some(format!("proposer map file missing: {}", tally.args.proposer_map))
            } else if tally.map.unreadable {
                Some(format!("proposer map unreadable: {}", tally.args.proposer_map))
            } else if tally.map.neutral_hash.is_empty() {
                Some("proposer map missing neutral_ballot_sha256 stamp".to_owned())
            } else if sha256(&preflight_ballot) != tally.map.neutral_hash {
                Some("proposer map stale for current ballot".to_owned())
            } else if let Some(error) = proposer_map_item_mismatch(&ballot_ids, &map_ids) {
                Some(error)
            } else if let Some((item_id, _)) = tally.map.rows.iter().find(|(_, (reviewer, _))| reviewer.is_empty() || reviewer.eq_ignore_ascii_case("anonymous")) {
                Some(format!("proposer map has neutral or empty reviewer for {item_id}"))
            } else {
                None
            };
            if let Some(error) = map_error {
                eprintln!("tally-plan-review.sh: {error}\ntally-plan-review: unexpected error: [Errno 21] Is a directory: '.'");
                println!("TALLY_PLAN_REVIEW_STATUS=tally-error");
                return ExitCode::from(2);
            }
        }
        if tally.args.seen_voters && tally.args.seen_files {
            return tally.error("error: --voter and --voter-files are mutually exclusive", "**⚠ Tally aborted: --voter and --voter-files are mutually exclusive; no votes tallied.**", false);
        }
        let ballot = match read_text(&ballot_path) {
            Ok(value) if ballot_path.is_file() => value,
            _ => {
            return tally.error(&format!("tally-plan-review.sh: ballot file is missing or unreadable: {}", tally.args.ballot), &format!("**⚠ Tally aborted: ballot file unreadable: {}; no votes tallied.**", tally.args.ballot), true);
            }
        };
        if let Err(code) = tally.resolve_voters() {
            return code;
        }
        tally.blocks = match ballot_blocks(&ballot) {
            Ok(blocks) => sorted_blocks(blocks),
            Err(_) => return tally.error("tally-plan-review.sh: duplicate or malformed FINDING/OOS headings in ballot", "**⚠ Tally aborted: duplicate or malformed FINDING/OOS headings in ballot; no votes tallied.**", true),
        };
        for name in ["accepted-plan-findings.md", "rejected-findings.md", "oos.md"] {
            if let Err(error) = write(&tally.root, &tally.root.join(name), "") {
                return tally.unexpected(&error);
            }
        }
        let ids = tally.blocks.iter().map(|(id, _)| id.clone()).collect::<HashSet<_>>();
        let mut results = Vec::new();
        for (id, block) in tally.blocks.clone() {
            let context = match tally.context(&id, &block, &ids) {
                Ok(value) => value,
                Err(code) => return code,
            };
            let mut result = adjudicate_item(context);
            result.security = Some(if tally.eligible == 0 { false } else { is_security_block_text(&result.context.artifact_text) });
            results.push(result);
        }
        if tally.eligible == 0 {
            let scoreboards = voter_scoreboards(&tally, &[]);
            if let Err(error) = write(&tally.root, &tally.tally, &format!("# Plan Review Voting Tally\n\n**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-required.**\n\n{scoreboards}")).and_then(|()| classification(&tally, &results).map(|_| ())) {
                return tally.unexpected(&error);
            }
            println!("TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nVOTING_TALLY_FILE={}", tally.tally_display.display());
            return ExitCode::SUCCESS;
        }
        if let Err(error) = render_tally(&tally, &results).and_then(|()| classification(&tally, &results).map(|_| ())).and_then(|()| write_ledger(&tally, &results)) {
            return tally.unexpected(&error);
        }
        println!("TALLY_PLAN_REVIEW_STATUS=ok\nVOTING_TALLY_FILE={}", tally.tally_display.display());
        ExitCode::SUCCESS
    }
}

pub use implementation::{
    emit, emit_rejected, filter_gate_b_skipped, gate_b_counts, gate_b_dedup, gate_b_finding_line,
    persist_accepted_audit, snapshot_pre_review, tally,
};
