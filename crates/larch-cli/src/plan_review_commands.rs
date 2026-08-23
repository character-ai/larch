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
    /// Capture and persist the Step 3 loop process identity.
    #[command(name = "write-loop-identity", disable_help_flag = true)]
    WriteLoopIdentity(AgentRawArguments),
    /// Wait for the persisted Step 3 loop process to exit.
    #[command(name = "await-loop-identity", disable_help_flag = true)]
    AwaitLoopIdentity(AgentRawArguments),
    /// Terminate a still-matching Step 3 loop process group.
    #[command(name = "teardown-loop-identity", disable_help_flag = true)]
    TeardownLoopIdentity(AgentRawArguments),
    /// Run the bounded Step 3 plan-review loop.
    #[command(name = "run", disable_help_flag = true)]
    Run(AgentRawArguments),
    /// Decide whether another plan-review round is required.
    #[command(name = "continuation", disable_help_flag = true)]
    Continuation(AgentRawArguments),
    /// Materialize the empty final plan-review artifacts when absent.
    #[command(name = "finalize", disable_help_flag = true)]
    Finalize(AgentRawArguments),
    /// Render the Step 3 plan-candidate preview, Gate B findings, or Gate C final-plan preview.
    #[command(name = "preview", disable_help_flag = true)]
    Preview(AgentRawArguments),
    /// Persist a terminal failure that happened before reviewer launch.
    #[command(name = "prelaunch-failure", disable_help_flag = true)]
    PrelaunchFailure(AgentRawArguments),
    /// Prepare the scope anchor for a direct Step 3 entry.
    #[command(name = "step3-entry", disable_help_flag = true)]
    Step3Entry(AgentRawArguments),
    /// Render the direct Step 3 entry preview.
    #[command(name = "step3-entry-preview", disable_help_flag = true)]
    Step3EntryPreview(AgentRawArguments),
    /// Reset state for a direct Step 3 entry.
    #[command(name = "step3-entry-state", disable_help_flag = true)]
    Step3EntryState(AgentRawArguments),
    /// Mutate Step 3 completion and re-entry state.
    #[command(name = "step3-state", disable_help_flag = true)]
    Step3State(AgentRawArguments),
    /// Run the existing `MainAgent`-vote wrapper.
    #[command(name = "step3-mav", disable_help_flag = true)]
    Step3Mav(AgentRawArguments),
    /// Record a Gate B bypass unless Step 3.5 is already partial.
    #[command(name = "step3-gate-b-bypass", disable_help_flag = true)]
    Step3GateBBypass(AgentRawArguments),
    /// Run the existing post-Step-3b tail wrapper.
    #[command(name = "step3b-tail", disable_help_flag = true)]
    Step3bTail(AgentRawArguments),
    /// Prepare Step 3.5 state.
    #[command(name = "step35", disable_help_flag = true)]
    Step35(AgentRawArguments),
    /// Settle the Gate A/B/C or discussion-round2 post-plan state (#8585).
    #[command(name = "step35-settle", disable_help_flag = true)]
    Step35Settle(AgentRawArguments),
    /// Normalize the Step 3 result envelope.
    #[command(name = "normalize-status", disable_help_flag = true)]
    NormalizeStatus(AgentRawArguments),
    /// Persist the result of a `MainAgent` retally.
    #[command(name = "persist-retally-env", disable_help_flag = true)]
    PersistRetallyEnv(AgentRawArguments),
    /// Persist a round start timestamp once.
    #[command(name = "persist-round-start-s", disable_help_flag = true)]
    PersistRoundStartS(AgentRawArguments),
    /// Read a boolean from a JSON object.
    #[command(name = "json-get-bool", disable_help_flag = true)]
    JsonGetBool(AgentRawArguments),
    /// Initialize the plan-size drift baseline once.
    #[command(name = "drift-baseline", disable_help_flag = true)]
    DriftBaseline(AgentRawArguments),
    /// Test whether a round artifact belongs in the durable snapshot.
    #[command(name = "round-artifact-included", disable_help_flag = true)]
    RoundArtifactIncluded(AgentRawArguments),
    /// Test whether a revise artifact belongs in the durable snapshot.
    #[command(name = "round-revise-artifact-included", disable_help_flag = true)]
    RoundReviseArtifactIncluded(AgentRawArguments),
    /// Test whether a revise artifact must be excluded from the durable snapshot.
    #[command(name = "round-revise-artifact-excluded", disable_help_flag = true)]
    RoundReviseArtifactExcluded(AgentRawArguments),
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
        PlanReviewCommand::WriteLoopIdentity(arguments) => {
            crate::review_loop_identity_commands::write_plan_review(&arguments.arguments)
        }
        PlanReviewCommand::AwaitLoopIdentity(arguments) => {
            crate::review_loop_identity_commands::await_plan_review(&arguments.arguments)
        }
        PlanReviewCommand::TeardownLoopIdentity(arguments) => {
            crate::review_loop_identity_commands::teardown_plan_review(&arguments.arguments)
        }
        PlanReviewCommand::Run(arguments) => loop_implementation::run(&arguments.arguments),
        PlanReviewCommand::Continuation(arguments) => {
            loop_implementation::continuation(&arguments.arguments)
        }
        PlanReviewCommand::Finalize(arguments) => {
            loop_implementation::finalize(&arguments.arguments)
        }
        PlanReviewCommand::Preview(arguments) => loop_implementation::preview(&arguments.arguments),
        PlanReviewCommand::PrelaunchFailure(arguments) => {
            loop_implementation::prelaunch_failure(&arguments.arguments)
        }
        PlanReviewCommand::Step3Entry(arguments) => {
            loop_implementation::step3_entry(&arguments.arguments)
        }
        PlanReviewCommand::Step3EntryPreview(arguments) => {
            loop_implementation::step3_entry_preview(&arguments.arguments)
        }
        PlanReviewCommand::Step3EntryState(arguments) => {
            loop_implementation::step3_entry_state(&arguments.arguments)
        }
        PlanReviewCommand::Step3State(arguments) => {
            loop_implementation::step3_state(&arguments.arguments)
        }
        PlanReviewCommand::Step3Mav(arguments) => {
            loop_implementation::delegate_script("design-step3-mav.sh", &arguments.arguments)
        }
        PlanReviewCommand::Step3GateBBypass(arguments) => {
            loop_implementation::step3_gate_b_bypass(&arguments.arguments)
        }
        PlanReviewCommand::Step3bTail(arguments) => {
            loop_implementation::delegate_script("design-step3b-tail.sh", &arguments.arguments)
        }
        PlanReviewCommand::Step35(arguments) => loop_implementation::step35(&arguments.arguments),
        PlanReviewCommand::Step35Settle(arguments) => {
            crate::design_settle_commands::step35_settle(&arguments.arguments)
        }
        PlanReviewCommand::NormalizeStatus(arguments) => {
            loop_implementation::normalize_status(&arguments.arguments)
        }
        PlanReviewCommand::PersistRetallyEnv(arguments) => {
            loop_implementation::persist_retally_env(&arguments.arguments)
        }
        PlanReviewCommand::PersistRoundStartS(arguments) => {
            loop_implementation::persist_round_start_s(&arguments.arguments)
        }
        PlanReviewCommand::JsonGetBool(arguments) => {
            loop_implementation::json_get_bool(&arguments.arguments)
        }
        PlanReviewCommand::DriftBaseline(arguments) => {
            loop_implementation::drift_baseline(&arguments.arguments)
        }
        PlanReviewCommand::RoundArtifactIncluded(arguments) => {
            loop_implementation::artifact_filter(
                &arguments.arguments,
                loop_implementation::ArtifactFilter::Round,
            )
        }
        PlanReviewCommand::RoundReviseArtifactIncluded(arguments) => {
            loop_implementation::artifact_filter(
                &arguments.arguments,
                loop_implementation::ArtifactFilter::ReviseIncluded,
            )
        }
        PlanReviewCommand::RoundReviseArtifactExcluded(arguments) => {
            loop_implementation::artifact_filter(
                &arguments.arguments,
                loop_implementation::ArtifactFilter::ReviseExcluded,
            )
        }
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

// Rust owners for the Step 3 loop, entry points, and persistence utilities.
// The deliberately compact layout keeps the atomic migration within #8449's
// review budget while the state transitions remain named and table driven.
#[rustfmt::skip]
mod loop_implementation {
    #![allow(
        clippy::cast_precision_loss,
        clippy::cognitive_complexity,
        clippy::collapsible_if,
        clippy::format_collect,
        clippy::format_push_string,
        clippy::if_not_else,
        clippy::implicit_clone,
        clippy::manual_let_else,
        clippy::needless_pass_by_value,
        clippy::option_if_let_else,
        clippy::or_fun_call,
        clippy::possible_missing_else,
        clippy::redundant_pub_crate,
        clippy::redundant_clone,
        clippy::single_match_else,
        clippy::too_many_lines,
    )] // Frozen Python transaction order stays compact enough for #8449's explicit line budget.

    use crate::{
        argparse_compat::{ParsedCommandLine, missing, parse_required_with_help as parsed, parse_required_with_help_allow_unknown as parsed_known, parse_with_flags, python_repr, usage_error},
        python_verb::run_python_verb,
        runtime_entrypoint::{
            plugin_root, run_verified_larch, run_verified_larch_with_environment,
            run_verified_larch_with_timeout,
        },
        difficulty_commands::extract_plan_difficulty,
    };
    use larch_adapters::validate_design_tmpdir;
    use larch_core::{
        BuildRecord, ChildEnvironment, CommentPolicy, DuplicatePolicy, EmptyKeyPolicy,
        FLOOR_MANIFEST_RELPATH, KvDocument, ParseOptions, WhitespacePolicy, blank_merge_explicit,
        build_record, cleanup_cache_sessions_root, emit_kv, load_floor_manifest, load_record_data,
        merge_existing_record_fields, parse_allowlisted_env_line, parse_single_kv_row, python_bigint,
        read_rating_file, resolve_panel_tier, validate_progress_run_id, write_record_map,
        private_atomic_write, redact_secrets_only, terminal_plan_trailer_value,
        review::{BoundaryMode, MERGE_KEYS, PlanReviewAggregationOutcome, PlanReviewBallotOutcome, PlanReviewCollectorRecord, PlanReviewManifestSlot, PlanReviewReviewerStatus, PlanReviewRoundArtifacts, PlanReviewRoundInput, PlanReviewRoundState, PlanReviewStructuredFinding, PlanReviewTallyOutcome, PlanReviewVoterOutcome, STEP3_NORMALIZE_ALLOW_KEYS, applied_finding_keys_before, ballot_blocks, finding_dedup_key, merge_already_addressed_finding_keys, normalize_collected_findings, parse_blocks, parse_plan_review_accepted_findings, render_reviewer_status_table, render_reviewer_status_tsv, replace_applied_finding_keys, reviewer_status_rows, run_plan_review_round, step3_loop_status_to_loop_status, step3_next_action, step3_status_from_loop_status},
    };
    use regex::Regex;
    use nix::unistd::setsid;
    use serde_json::Value;
    use sha2::{Digest as _, Sha256};
    use std::{
        collections::{BTreeMap, BTreeSet}, env, ffi::OsString, fs,
        io::{self, Write as _}, path::{Path, PathBuf}, process::{Command, ExitCode}, time::{Duration, SystemTime, UNIX_EPOCH},
    };

    const SIMPLE_TIMEOUT: Duration = Duration::from_secs(120);
    const FINALIZE_USAGE: &str = "usage: cli.py plan-review finalize [-h] --design-tmpdir DESIGN_TMPDIR";
    const FINALIZE_HELP: &str = "usage: cli.py plan-review finalize [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR";
    const CONTINUATION_USAGE: &str = "usage: cli.py plan-review continuation [-h] --design-tmpdir DESIGN_TMPDIR\n                                       --approve-requested {true,false}";
    const CONTINUATION_HELP: &str = "usage: cli.py plan-review continuation [-h] --design-tmpdir DESIGN_TMPDIR\n                                       --approve-requested {true,false}\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --approve-requested {true,false}";
    const STATE_USAGE: &str = "usage: cli.py plan-review step3-state [-h] --design-tmpdir DESIGN_TMPDIR\n                                      [--direct-review-entry]\n                                      [--direct-review-pause-hygiene]\n                                      [--auto-continuation-entry]\n                                      [--gate-b-bypass]";
    const STATE_HELP: &str = "usage: cli.py plan-review step3-state [-h] --design-tmpdir DESIGN_TMPDIR\n                                      [--direct-review-entry]\n                                      [--direct-review-pause-hygiene]\n                                      [--auto-continuation-entry]\n                                      [--gate-b-bypass]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --direct-review-entry\n  --direct-review-pause-hygiene\n  --auto-continuation-entry\n  --gate-b-bypass";
    const RETALLY_USAGE: &str = "usage: cli.py plan-review persist-retally-env [-h] --design-tmpdir\n                                              DESIGN_TMPDIR\n                                              --retally-stdout-file\n                                              RETALLY_STDOUT_FILE\n                                              [--retally-input-anchor RETALLY_INPUT_ANCHOR]\n                                              --tally-plan-review-status\n                                              TALLY_PLAN_REVIEW_STATUS\n                                              --loop-status LOOP_STATUS";
    const RETALLY_HELP: &str = "usage: cli.py plan-review persist-retally-env [-h] --design-tmpdir\n                                              DESIGN_TMPDIR\n                                              --retally-stdout-file\n                                              RETALLY_STDOUT_FILE\n                                              [--retally-input-anchor RETALLY_INPUT_ANCHOR]\n                                              --tally-plan-review-status\n                                              TALLY_PLAN_REVIEW_STATUS\n                                              --loop-status LOOP_STATUS\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --retally-stdout-file RETALLY_STDOUT_FILE\n  --retally-input-anchor RETALLY_INPUT_ANCHOR\n  --tally-plan-review-status TALLY_PLAN_REVIEW_STATUS\n  --loop-status LOOP_STATUS";
    const ROUND_START_USAGE: &str = "usage: cli.py plan-review persist-round-start-s [-h] --design-tmpdir\n                                                DESIGN_TMPDIR --round-num\n                                                ROUND_NUM --start-s START_S";
    const ROUND_START_HELP: &str = "usage: cli.py plan-review persist-round-start-s [-h] --design-tmpdir\n                                                DESIGN_TMPDIR --round-num\n                                                ROUND_NUM --start-s START_S\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --round-num ROUND_NUM\n  --start-s START_S";
    const JSON_BOOL_USAGE: &str = "usage: cli.py plan-review json-get-bool [-h] --path PATH --key KEY\n                                        [--default {true,false}]";
    const JSON_BOOL_HELP: &str = "usage: cli.py plan-review json-get-bool [-h] --path PATH --key KEY\n                                        [--default {true,false}]\n\noptions:\n  -h, --help            show this help message and exit\n  --path PATH\n  --key KEY\n  --default {true,false}";
    const ENTRY_USAGE: &str = "usage: cli.py plan-review step3-entry [-h] --design-tmpdir DESIGN_TMPDIR\n                                      [--reentry]";
    const ENTRY_HELP: &str = "usage: cli.py plan-review step3-entry [-h] --design-tmpdir DESIGN_TMPDIR\n                                      [--reentry]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --reentry";
    const PRELAUNCH_USAGE: &str = "usage: cli.py plan-review prelaunch-failure [-h] --design-tmpdir DESIGN_TMPDIR\n                                            [--reason REASON]";
    const PRELAUNCH_HELP: &str = "usage: cli.py plan-review prelaunch-failure [-h] --design-tmpdir DESIGN_TMPDIR\n                                            [--reason REASON]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --reason REASON";
    const NORMALIZE_USAGE: &str = "usage: cli.py plan-review normalize-status [-h] --design-tmpdir DESIGN_TMPDIR\n                                           [--stdout-file STDOUT_FILE]\n                                           [--loop-rc LOOP_RC]\n                                           [--read-result-env]";
    const NORMALIZE_HELP: &str = "usage: cli.py plan-review normalize-status [-h] --design-tmpdir DESIGN_TMPDIR\n                                           [--stdout-file STDOUT_FILE]\n                                           [--loop-rc LOOP_RC]\n                                           [--read-result-env]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --stdout-file STDOUT_FILE\n  --loop-rc LOOP_RC\n  --read-result-env";
    const STEP35_USAGE: &str = "usage: cli.py plan-review step35 [-h] --design-tmpdir DESIGN_TMPDIR";
    const STEP35_HELP: &str = "usage: cli.py plan-review step35 [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR";

    fn text(parsed: &ParsedCommandLine, name: &str) -> String { parsed.value(name).map_or_else(String::new, |v| v.to_string_lossy().into_owned()) }
    fn root(raw: &str, program: &str) -> Result<PathBuf, ExitCode> {
        let path = Path::new(raw);
        if !path.is_dir() { eprintln!("{program}: DESIGN_TMPDIR required"); return Err(ExitCode::from(2)); }
        if path.is_symlink() { eprintln!("{program}: design-tmpdir must not be a symlink"); return Err(ExitCode::from(2)); }
        if let Err(message) = validate_design_tmpdir(raw, env::var_os("TMPDIR").as_deref(), &cleanup_cache_sessions_root(env::var_os("XDG_CACHE_HOME").as_deref(), env::var_os("HOME").as_deref())) {
            eprintln!("{program}: {message}"); return Err(ExitCode::from(2));
        }
        fs::canonicalize(path).map_err(|error| { eprintln!("{program}: {error}"); ExitCode::from(2) })
    }
    fn root_quiet(raw:&str)->Option<PathBuf>{let path=Path::new(raw);if !path.is_dir()||path.is_symlink(){return None;}validate_design_tmpdir(raw,env::var_os("TMPDIR").as_deref(),&cleanup_cache_sessions_root(env::var_os("XDG_CACHE_HOME").as_deref(),env::var_os("HOME").as_deref())).ok()?;fs::canonicalize(path).ok()}
    fn write(root: &Path, path: &Path, body: &str) -> Result<(), String> {
        if path.is_symlink() { return Err(format!("refusing to write symlink result env: {}", path.display())); }
        if let Some(parent) = path.parent() { fs::create_dir_all(parent).map_err(|error| error.to_string())?; }
        private_atomic_write(path, body, root).map_err(|error| error.to_string())
    }
    fn read(path: &Path) -> String { if path.is_file() && !path.is_symlink() { fs::read(path).map(|v| String::from_utf8_lossy(&v).replace("\r\n", "\n").replace('\r', "\n")).unwrap_or_default() } else { String::new() } }
    fn env_rows(path: &Path) -> BTreeMap<String, String> {
        let mut out = BTreeMap::new();
        for line in read(path).lines() {
            let candidate = line.trim().strip_prefix("export ").unwrap_or(line.trim());
            let options = ParseOptions {
                comments: CommentPolicy::Skip,
                empty_keys: EmptyKeyPolicy::Skip,
                key_whitespace: WhitespacePolicy::Trim,
                ..ParseOptions::legacy()
            };
            let Ok(document) = KvDocument::parse(candidate, options) else { continue; };
            let [row] = document.rows() else { continue; };
            let key = row.key();
            if key.is_empty() || !key.bytes().all(|b| b == b'_' || b.is_ascii_uppercase() || b.is_ascii_digit()) { continue; }
            if let Some((_, value)) = parse_allowlisted_env_line(line, &[key], None, true) { out.insert(key.to_owned(), value); }
        }
        out
    }
    fn strict_result_rows(path:&Path,allowed:&[&str])->Result<Vec<(String,String)>,String>{
        let bytes=fs::read(path).map_err(|error|format!("failed to read result env {}: {error}",path.display()))?;
        let text=String::from_utf8_lossy(&bytes);
        let mut grouped:Vec<(String,Vec<String>)>=Vec::new();
        for line in text.split('\n').filter(|line|!line.contains('\r')){
            let Some(row)=parse_single_kv_row(line,ParseOptions::legacy())else{continue};
            let key=row.key();let value=row.value();
            if !allowed.contains(&key){continue;}
            if let Some((_,values))=grouped.iter_mut().find(|(existing,_)|existing==key){values.push(value.to_owned());}else{grouped.push((key.to_owned(),vec![value.to_owned()]));}
        }
        Ok(grouped.into_iter().flat_map(|(key,values)|values.into_iter().map(move|value|(key.clone(),value))).collect())
    }
    fn render_rows(rows: impl IntoIterator<Item=(String, String)>) -> Result<String, String> {
        let mut out = String::new();
        for (key, value) in rows { if value.contains(['\n', '\r']) { return Err(format!("result env value contains newline: {key}")); } out.push_str(&key); out.push('='); out.push_str(&value); out.push('\n'); }
        Ok(out)
    }
    fn write_rows(root: &Path, path: &Path, rows: impl IntoIterator<Item=(String, String)>) -> Result<(), String> { write(root, path, &render_rows(rows)?) }
    fn touch(path: &Path) -> io::Result<()> { if let Some(parent) = path.parent() { fs::create_dir_all(parent)?; } fs::OpenOptions::new().create(true).append(true).open(path).map(drop) }
    fn remove(path: &Path) { if path.is_file() && !path.is_symlink() || path.is_symlink() { let _ = fs::remove_file(path); } }
    fn digits(value: &str) -> bool { !value.is_empty() && value.bytes().all(|b| b.is_ascii_digit()) }
    fn positive(value: &str) -> bool { digits(value) && value.bytes().any(|b| b != b'0') }
    fn read_count(root: &Path) -> u64 { let value = read(&root.join("review-round-count.txt")).trim().to_owned(); if digits(&value) { value.parse().unwrap_or(0) } else { 0 } }
    fn write_count(root: &Path, count: u64) { let _ = write(root, &root.join("review-round-count.txt"), &format!("{count}\n")); }
    fn completed(root: &Path, both: bool) -> Result<(), String> { let directory=root.join(".completed");if directory.is_symlink()||directory.exists()&&!directory.is_dir(){return Err(format!("refusing invalid completion directory: {}",directory.display()));}fs::create_dir_all(&directory).map_err(|error|format!("failed to create completion directory {}: {error}",directory.display()))?;for name in if both { &["step-3", "step-3.5"][..] } else { &["step-3"][..] } { let path=directory.join(name); if path.is_symlink() || path.exists() && !path.is_file() { return Err(format!("refusing invalid completion marker: {}",path.display())); } touch(&path).map_err(|error|format!("failed to write completion marker {}: {error}",path.display()))?; } Ok(()) }
    fn child_owned(args: Vec<OsString>) -> Result<larch_core::ProcessOutput, String> { run_verified_larch(&args) }
    fn forward(output: &larch_core::ProcessOutput) { let _ = io::stdout().write_all(output.stdout()); let _ = io::stderr().write_all(output.stderr()); }
    fn code(output: &larch_core::ProcessOutput) -> i32 { output.status().code().unwrap_or(1) }
    fn kv_text(text: &str) -> BTreeMap<String, String> { let document=KvDocument::parse(text,ParseOptions::legacy()).expect("legacy result envelope parser accepts every text input");let mut out=document.select(DuplicatePolicy::Last);out.remove("");out.retain(|_,value|!value.contains(['\n','\r']));out }
    fn progress_note(root:&Path,text:&str){let mut candidates=vec![env::var("LARCH_RUN_ID").unwrap_or_default()];for name in ["session-env.sh","source-env.sh"]{if let Some(value)=env_rows(&root.join(name)).get("LARCH_RUN_ID"){candidates.push(value.clone());}}let Some(run_id)=candidates.into_iter().find(|value|validate_progress_run_id(value).is_some())else{return;};let Ok(repo)=env::current_dir()else{return;};let _=child_owned(vec!["progress".into(),"note".into(),"--repo-root".into(),repo.into_os_string(),"--run-id".into(),run_id.into(),"--skill".into(),"design".into(),"--step".into(),"3".into(),text.into()]);}

    #[must_use] pub fn finalize(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments, "cli.py plan-review finalize", FINALIZE_USAGE, FINALIZE_HELP, &["--design-tmpdir"], &[], &["--design-tmpdir"]) { Ok(v) => v, Err(c) => return c };
        let root = match root(&text(&parsed, "--design-tmpdir"), "cli.py plan-review finalize") { Ok(v) => v, Err(c) => return c };
        for name in ["voting-tally.md", "accepted-plan-findings.md", "rejected-findings.md", "oos.md"] { let path = root.join(name); if path.is_symlink() || path.exists() && !path.is_file() { emit_kv("FINALIZE_PLAN_STATUS", "invalid-artifact"); return ExitCode::FAILURE; } }
        for (name, body) in [("voting-tally.md", "## Plan Review Tally\n\n"), ("accepted-plan-findings.md", ""), ("rejected-findings.md", ""), ("oos.md", "")] { let path = root.join(name); if !path.exists() && write(&root, &path, body).is_err() { emit_kv("FINALIZE_PLAN_STATUS", "invalid-artifact"); return ExitCode::FAILURE; } }
        emit_kv("FINALIZE_PLAN_STATUS", "ok"); ExitCode::SUCCESS
    }

    #[must_use] pub fn preview(arguments: &[OsString]) -> ExitCode {
        let parsed = parse_with_flags(arguments, &["--design-tmpdir", "--variant"], &[], 0);
        let variant = parsed.value("--variant").map_or("step3".to_owned(), |v| v.to_string_lossy().into_owned());
        let raw = text(&parsed, "--design-tmpdir");
        let missing = match variant.as_str() { "step2b" => "**⚠ 2b:** DESIGN_TMPDIR missing or invalid; cannot present implementation plan", "gate-b" => "**⚠ 3.5: DESIGN_TMPDIR missing or invalid; cannot present Gate B findings review**", "gatec" | "full" => "**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**", _ => "**⚠ 3: DESIGN_TMPDIR missing or invalid; cannot present plan candidate for review**" };
        let denied = match variant.as_str() { "step2b" => "**⚠ 2b:** DESIGN_TMPDIR not under allowlist; cannot present implementation plan", "gate-b" => "**⚠ 3.5: DESIGN_TMPDIR not under allowlist; cannot present Gate B findings review**", "gatec" | "full" => "**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**", _ => "**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**" };
        let path=Path::new(&raw); let validation=validate_design_tmpdir(&raw,env::var_os("TMPDIR").as_deref(),&cleanup_cache_sessions_root(env::var_os("XDG_CACHE_HOME").as_deref(),env::var_os("HOME").as_deref()));
        if raw.is_empty()||!path.is_dir()||path.is_symlink(){println!("{missing}");return ExitCode::SUCCESS;}if validation.is_err(){println!("{denied}");return ExitCode::SUCCESS;}let root=match fs::canonicalize(path){Ok(v)=>v,Err(_)=>{println!("{missing}");return ExitCode::SUCCESS;}};
        if variant == "gate-b" { match child_owned(vec!["plan-review".into(), "gate-b-counts".into(), "--design-tmpdir".into(), root.as_os_str().into(), "--preview".into()]) { Ok(out) => { forward(&out); return ExitCode::from(u8::try_from(code(&out)).unwrap_or(1)); }, Err(error) => { eprintln!("{error}"); return ExitCode::FAILURE; } } }
        if variant == "full" { if let Some(script) = env::var_os("EMIT_DESIGN_PLAN_PREVIEW_SH").map(PathBuf::from).filter(|p| p.is_file()) { let status = Command::new(script) // lint-subprocess-via-runner: ok retained deterministic preview harness override has no typed executable owner
                .args(["--design-tmpdir", &root.display().to_string(), "--variant", "full"]).status(); return status.map_or(ExitCode::FAILURE, |s| ExitCode::from(u8::try_from(s.code().unwrap_or(1)).unwrap_or(1))); } }
        let body = read(&root.join("plan.txt")); let threshold = env::var("LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD").ok().filter(|v| digits(v)).and_then(|v| v.parse::<usize>().ok()).unwrap_or(120);
        println!("{}\n", match variant.as_str() { "gatec" | "full" => "## Final Design Plan", "step2b" => "## Implementation Plan", _ => { let _ = touch(&root.join(".step3-entry-plan-printed")); "## Plan Candidate for Review" } });
        if body.lines().count() > threshold { println!("The plan is very large. Showing the full plan body below.\n"); }
        print!("{body}"); if !body.is_empty() && !body.ends_with('\n') { println!(); } ExitCode::SUCCESS
    }

    #[must_use] pub fn persist_retally_env(arguments: &[OsString]) -> ExitCode {
        let values = ["--design-tmpdir", "--retally-stdout-file", "--retally-input-anchor", "--tally-plan-review-status", "--loop-status"];
        let parsed = match parsed(arguments, "cli.py plan-review persist-retally-env", RETALLY_USAGE, RETALLY_HELP, &values, &[], &["--design-tmpdir", "--retally-stdout-file", "--tally-plan-review-status", "--loop-status"]) { Ok(v) => v, Err(c) => return c };
        let root = match root(&text(&parsed,"--design-tmpdir"), "cli.py plan-review persist-retally-env") { Ok(v) => v, Err(c) => return c }; let retally = env_rows(Path::new(&text(&parsed,"--retally-stdout-file"))); let status = text(&parsed,"--tally-plan-review-status"); let existing = env_rows(&root.join(".step3-plan-review-result.env"));
        let mut rows = Vec::<(String,String)>::new(); if status == "tally-error" { rows.push(("NEXT_ACTION".into(),"step3b-bypass".into())); } rows.extend([("TALLY_PLAN_REVIEW_STATUS".into(),status.clone()), ("LOOP_STATUS".into(),text(&parsed,"--loop-status")), ("VOTING_TALLY_FILE".into(),retally.get("VOTING_TALLY_FILE").cloned().unwrap_or_default())]);
        for key in ["ROUNDS_COMPLETED","FINAL_ROUND_NUM","STEP3_REVIEW_ROUND_NUM"] { if let Some(v) = existing.get(key).filter(|v| digits(v)) { rows.push((key.into(),v.clone())); } }
        if status == "tally-error" { for name in ["accepted-plan-findings.md","rejected-findings.md","oos.md"] { let _ = write(&root,&root.join(name),""); } rows.extend([("ACCEPTED_COUNT".into(),"0".into()),("IMPORTANT_ACCEPTED_COUNT".into(),"0".into())]); } else { rows.extend([("ACCEPTED_COUNT".into(),retally.get("ACCEPTED_COUNT").cloned().unwrap_or_else(||"0".into())),("IMPORTANT_ACCEPTED_COUNT".into(),retally.get("IMPORTANT_ACCEPTED_COUNT").cloned().unwrap_or_else(||"0".into()))]); let root_prefix=format!("{}/",root.display());if let Some(scope)=retally.get("SCOPE_ANCHOR_FILE").filter(|v| !v.contains(['\n','\r']) && Path::new(v).is_absolute() && v.starts_with(&root_prefix)) { rows.push(("SCOPE_ANCHOR_FILE".into(),scope.clone())); } }
        for name in [".step3-plan-review-result.env",".step3-review-result.env"] { let path=root.join(name); let mut current=rows.clone(); if let Some(v)=env_rows(&path).get("ROUND_NUM").filter(|v| digits(v)) { current.push(("ROUND_NUM".into(),v.clone())); } if write_rows(&root,&path,current).is_err() { return ExitCode::FAILURE; } }
        emit_kv("PERSIST_RETALLY_STATUS","ok"); ExitCode::SUCCESS
    }

    #[must_use] pub fn persist_round_start_s(arguments: &[OsString]) -> ExitCode {
        let parsed=parse_with_flags(arguments,&["--design-tmpdir","--round-num","--start-s"],&["-h","--help"],0);if parsed.flag("-h")||parsed.flag("--help"){println!("{ROUND_START_HELP}");return ExitCode::SUCCESS;}let mut integers=BTreeMap::new();for(option,value)in parsed.entries(){if matches!(*option,"--round-num"|"--start-s"){let raw=value.to_string_lossy();let Some(number)=python_bigint(&raw)else{return usage_error(ROUND_START_USAGE,"cli.py plan-review persist-round-start-s",&format!("argument {option}: invalid int value: {}",python_repr(&raw)),2)};integers.insert(*option,number.to_string());}}if let Some(error)=parsed.value_error(){return usage_error(ROUND_START_USAGE,"cli.py plan-review persist-round-start-s",error,2);}let states=[("--design-tmpdir",parsed.value("--design-tmpdir").is_some()),("--round-num",parsed.value("--round-num").is_some()),("--start-s",parsed.value("--start-s").is_some())];if states.iter().any(|(_,present)|!*present){return usage_error(ROUND_START_USAGE,"cli.py plan-review persist-round-start-s",&missing(&states),2);}if let Some(error)=parsed.error(){return usage_error(ROUND_START_USAGE,"cli.py plan-review persist-round-start-s",&error,2);}
        let raw=text(&parsed,"--design-tmpdir"); let Some(root)=root_quiet(&raw)else{return ExitCode::FAILURE;}; let round=&integers["--round-num"]; let start=&integers["--start-s"];
        let parent=root.join("plan-review"); if parent.is_symlink() { return ExitCode::SUCCESS; } let dir=parent.join(format!("round-{round}")); if fs::create_dir_all(&dir).is_err() { return ExitCode::SUCCESS; } let path=dir.join("round-start-s"); if path.exists() || path.is_symlink() { return ExitCode::SUCCESS; } let _=fs::OpenOptions::new().write(true).create_new(true).open(path).and_then(|mut f| writeln!(f,"{start}")); ExitCode::SUCCESS
    }

    #[must_use] pub fn json_get_bool(arguments: &[OsString]) -> ExitCode {
        let parsed = match parsed(arguments,"cli.py plan-review json-get-bool",JSON_BOOL_USAGE,JSON_BOOL_HELP,&["--path","--key","--default"],&[],&["--path","--key"]) { Ok(v)=>v,Err(c)=>return c }; let default=text(&parsed,"--default"); if !default.is_empty() && !matches!(default.as_str(),"true"|"false") { return usage_error(JSON_BOOL_USAGE,"cli.py plan-review json-get-bool",&format!("argument --default: invalid choice: '{default}' (choose from 'true', 'false')"),2); }
        let path=PathBuf::from(text(&parsed,"--path")); let key=text(&parsed,"--key"); let value=if path.is_file()&&!path.is_symlink(){ serde_json::from_str::<Value>(&read(&path)).ok().and_then(|v|v.as_object().and_then(|o|o.get(&key)).and_then(Value::as_bool)) }else{None}.unwrap_or(default=="true"); println!("{}",if value{"true"}else{"false"}); ExitCode::SUCCESS
    }

    pub enum ArtifactFilter { Round, ReviseIncluded, ReviseExcluded }
    #[must_use] pub fn artifact_filter(arguments: &[OsString], kind: ArtifactFilter) -> ExitCode {
        let parsed=parse_with_flags(arguments,&["--name"],&["-h","--help"],1); if parsed.flag("-h")||parsed.flag("--help") { println!("usage: cli.py plan-review round-artifact-included [-h] [--name NAME_OPT]\n                                                  [name]\n\npositional arguments:\n  name\n\noptions:\n  -h, --help       show this help message and exit\n  --name NAME_OPT"); return ExitCode::SUCCESS; } let name=parsed.value("--name").or_else(||parsed.positional(0)).map(|v|Path::new(v).file_name().unwrap_or(v).to_string_lossy().into_owned()).unwrap_or_default(); if name.is_empty(){return usage_error("usage: cli.py plan-review round-artifact-included [-h] [--name NAME_OPT]\n                                                  [name]","cli.py plan-review round-artifact-included","artifact name is required",2);}
        let included=match kind { ArtifactFilter::Round => ["round-summary.env","findings-classification.tsv","prune-decision.env","prune-nit.env","reviewer-status.tsv"].contains(&name.as_str()) || env::var("LARCH_FLUSH_DEBUG").as_deref()==Ok("1") && ["-vote-output.txt","-vote-output-first-pass.txt",".failure-diag"].iter().any(|s|name.ends_with(s)), ArtifactFilter::ReviseIncluded => false, ArtifactFilter::ReviseExcluded => ["revise.env","prompt.txt"].contains(&name.as_str()) || ["-output.txt","-output-candidate.patch",".done",".dirty-tree",".meta",".prompt",".sidecar",".sidecar.history",".events.jsonl",".events.history",".untracked-baseline",".diag",".failure-diag",".json",".stderr",".token-record",".stderr-tail"].iter().any(|s|name.ends_with(s)) }; if included{ExitCode::SUCCESS}else{ExitCode::FAILURE}
    }

    #[must_use] pub fn drift_baseline(arguments: &[OsString]) -> ExitCode {
        if arguments.first().and_then(|v|v.to_str())!=Some("write-once") { eprintln!("usage: cli.py plan-review drift-baseline write-once --design-tmpdir DIR --plan-lines N --diff-lines N"); return ExitCode::from(2); } let parsed=parse_with_flags(&arguments[1..],&["--design-tmpdir","--plan-lines","--diff-lines"],&["-h","--help"],0); if parsed.flag("-h")||parsed.flag("--help"){println!("usage: cli.py plan-review drift-baseline write-once [-h] --design-tmpdir DESIGN_TMPDIR --plan-lines PLAN_LINES --diff-lines DIFF_LINES");return ExitCode::SUCCESS;} if parsed.error().is_some()||["--design-tmpdir","--plan-lines","--diff-lines"].iter().any(|k|parsed.value(k).is_none()){return usage_error("usage: cli.py plan-review drift-baseline write-once [-h] --design-tmpdir DESIGN_TMPDIR --plan-lines PLAN_LINES --diff-lines DIFF_LINES","cli.py plan-review drift-baseline write-once","required arguments missing",2);} let Some(root)=root_quiet(&text(&parsed,"--design-tmpdir"))else{return ExitCode::FAILURE}; let plan=text(&parsed,"--plan-lines");let diff=text(&parsed,"--diff-lines");if !digits(&plan)||!digits(&diff){return ExitCode::FAILURE;}let path=root.join("drift-baseline.env");if path.is_file()&&!path.is_symlink(){return ExitCode::SUCCESS;}if path.is_symlink(){remove(&path);}if write(&root,&path,&format!("BASELINE_PLAN_LINES={plan}\nBASELINE_DIFF_LINES={diff}\n")).is_ok(){ExitCode::SUCCESS}else{ExitCode::FAILURE}
    }

    fn clear_downstream(root:&Path){for rel in [".completed/step-3",".completed/step-3.5",".completed/step-3b",".completed/step-4",".completed/step-4b","bgjob/design-step3-review.result.env","bgjob/design-step4-tail.result.env"]{remove(&root.join(rel));}if let Ok(entries)=fs::read_dir(root){for entry in entries.flatten(){if entry.file_name().to_string_lossy().starts_with(".gate-b-postapply-ready-"){remove(&entry.path());}}}}
    fn cleanup_loop_state(root:&Path,max:u64){if let Ok(entries)=fs::read_dir(root){for entry in entries.flatten(){let name=entry.file_name().to_string_lossy().into_owned();let number=name.strip_prefix(".step3-round-").and_then(|v|v.strip_suffix(".phase")).or_else(||name.strip_prefix("plan-pre-apply-round-").and_then(|v|v.strip_suffix(".txt")));if number.and_then(|v|v.parse::<u64>().ok()).is_some_and(|n|n<=max)&&!entry.path().is_symlink(){remove(&entry.path());}}}}
    #[must_use] pub fn step3_state(arguments:&[OsString])->ExitCode{
        let parsed=match parsed(arguments,"cli.py plan-review step3-state",STATE_USAGE,STATE_HELP,&["--design-tmpdir"],&["--direct-review-entry","--direct-review-pause-hygiene","--auto-continuation-entry","--gate-b-bypass"],&["--design-tmpdir"]){Ok(v)=>v,Err(c)=>return c};let root=match root(&text(&parsed,"--design-tmpdir"),"cli.py plan-review step3-state"){Ok(v)=>v,Err(c)=>return c};let _=fs::create_dir_all(root.join(".completed"));let count=read_count(&root);let state=if parsed.flag("--auto-continuation-entry"){clear_downstream(&root);cleanup_loop_state(&root,count);"auto-continuation-entry"}else if parsed.flag("--gate-b-bypass"){if root.join(".completed/step-3.5").exists(){"refused-partial-gate-b-bypass"}else if let Err(error)=completed(&root,true){eprintln!("cli.py plan-review step3-state: {error}");return ExitCode::FAILURE}else{"gate-b-bypass"}}else if parsed.flag("--direct-review-entry")||parsed.flag("--direct-review-pause-hygiene"){let action=if parsed.flag("--direct-review-entry"){"direct-review-entry"}else{"direct-review-pause-hygiene"};if !root.join(".step3-reentry").is_file(){"noop"}else{clear_downstream(&root);for name in ["step-1e","step-2a","step-2b","step-2b.5"]{let _=touch(&root.join(".completed").join(name));}if parsed.flag("--direct-review-entry"){cleanup_loop_state(&root,count);for rel in ["accepted-plan-findings-all.md",".accepted-plan-findings-all.prev.md",".step3-applied-finding-keys.tsv","oos-accepted-design.md",".oos-accepted-design.prev.md",".step3-reentry"]{remove(&root.join(rel));}}action}}else{"ok"};emit_kv("STEP3_STATE",state);emit_kv("REVIEW_ROUND_COUNT",&count.to_string());ExitCode::SUCCESS
    }

    fn session_values(arguments:&[OsString])->Result<(String,String,String),String>{
        let parsed=parse_with_flags(arguments,&["--session-env-path","--claude-pid","--plugin-root","--design-tmpdir"],&["-h","--help"],0);if let Some(error)=parsed.error(){return Err(error);}let mut source=text(&parsed,"--session-env-path");let pid=text(&parsed,"--claude-pid");if !source.is_empty()&&Path::new(&source).is_symlink(){let out=child_owned(vec!["session".into(),"resolve-trusted-design-env".into(),"--session-env-path".into(),source.clone().into(),"--claude-pid".into(),pid.into()]).map_err(|e|format!("/design wrapper: {e}"))?;if !out.status().success(){return Err(format!("/design wrapper: refusing untrusted session-env symlink: {source}"));}source=kv_text(&String::from_utf8_lossy(out.stdout())).get("TRUSTED_SOURCE").cloned().ok_or_else(||format!("/design wrapper: refusing untrusted session-env symlink: {source}"))?;}
        let values=if source.is_empty(){BTreeMap::new()}else{env_rows(Path::new(&source))};let design=if !text(&parsed,"--design-tmpdir").is_empty(){text(&parsed,"--design-tmpdir")}else{values.get("DESIGN_TMPDIR").cloned().or_else(||env::var("DESIGN_TMPDIR").ok()).unwrap_or_default()};let issue=values.get("ISSUE_NUMBER").cloned().or_else(||env::var("ISSUE_NUMBER").ok()).unwrap_or_default();let repo=values.get("REPO").cloned().or_else(||env::var("REPO").ok()).unwrap_or_default();Ok((design,issue,repo))
    }
    fn pause(root:&Path,issue:&str,repo:&str)->ExitCode{let mut args=vec!["design".into(),"pause-save".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--issue".into(),issue.into()];if !repo.is_empty(){args.extend(["--repo".into(),repo.into()]);}match run_verified_larch(&args){Ok(out)=>{forward(&out);ExitCode::from(u8::try_from(code(&out)).unwrap_or(1))},Err(error)=>{eprintln!("{error}");ExitCode::FAILURE}}}
    #[must_use] pub fn step3_entry_preview(arguments:&[OsString])->ExitCode{if arguments.iter().any(|a|matches!(a.to_str(),Some("-h"|"--help"))){println!("usage: cli.py plan-review step3-entry-preview [-h]\n\noptions:\n  -h, --help  show this help message and exit");return ExitCode::SUCCESS;}let(design,issue,repo)=match session_values(arguments){Ok(v)=>v,Err(e)=>{eprintln!("{e}");return ExitCode::FAILURE}};let path=PathBuf::from(&design);if !design.is_empty()&&path.join(".pause-requested").is_file(){return pause(&path,&issue,&repo);}let allowed=validate_design_tmpdir(&design,env::var_os("TMPDIR").as_deref(),&cleanup_cache_sessions_root(env::var_os("XDG_CACHE_HOME").as_deref(),env::var_os("HOME").as_deref())).is_ok();if allowed&&path.is_dir()&&path.join(".step3-entry-plan-printed").exists(){return ExitCode::SUCCESS;}let code=preview(&["--design-tmpdir".into(),design.into(),"--variant".into(),"step3".into()]);println!();code}
    #[must_use] pub fn step3_entry_state(arguments:&[OsString])->ExitCode{if arguments.iter().any(|a|matches!(a.to_str(),Some("-h"|"--help"))){println!("usage: cli.py plan-review step3-entry-state [-h]\n\noptions:\n  -h, --help  show this help message and exit");return ExitCode::SUCCESS;}let(design,issue,repo)=match session_values(arguments){Ok(v)=>v,Err(e)=>{eprintln!("{e}");return ExitCode::FAILURE}};let path=PathBuf::from(&design);if !design.is_empty()&&path.join(".pause-requested").is_file(){return pause(&path,&issue,&repo);}let code=step3_state(&["--design-tmpdir".into(),design.into(),"--direct-review-entry".into()]);if code==ExitCode::SUCCESS{let _=run_verified_larch_with_environment(&["timing".into(),"mark".into(),"design Step 3 — plan review".into()],&[(ChildEnvironment::LarchTimingSkill,"design".into())]);}code}
    #[must_use] pub fn step3_gate_b_bypass(arguments:&[OsString])->ExitCode{if plugin_root().is_err(){eprintln!("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort");return ExitCode::FAILURE;}if arguments.iter().any(|a|matches!(a.to_str(),Some("-h"|"--help"))){println!("usage: cli.py plan-review step3-gate-b-bypass [-h]\n\noptions:\n  -h, --help  show this help message and exit");return ExitCode::SUCCESS;}let(design,issue,repo)=match session_values(arguments){Ok(v)=>v,Err(e)=>{eprintln!("{e}");return ExitCode::FAILURE}};if design.is_empty(){eprintln!("/design Step 3 gate-b-bypass: DESIGN_TMPDIR required");return ExitCode::FAILURE;}let path=PathBuf::from(&design);if path.join(".pause-requested").is_file(){return pause(&path,&issue,&repo);}if path.join(".completed/step-3.5").is_file(){println!("STEP3_STATE=skipped-step-3.5-present");return ExitCode::SUCCESS;}step3_state(&["--design-tmpdir".into(),design.into(),"--gate-b-bypass".into()])}
    #[must_use] pub fn step35(arguments:&[OsString])->ExitCode{if plugin_root().is_err(){eprintln!("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort");return ExitCode::FAILURE;}let parsed=match parsed_known(arguments,"cli.py plan-review step35",STEP35_USAGE,STEP35_HELP,&["--design-tmpdir"],&[],&["--design-tmpdir"]){Ok(v)=>v,Err(c)=>return c};let root=match root(&text(&parsed,"--design-tmpdir"),"cli.py plan-review step35"){Ok(v)=>v,Err(c)=>return c};let values=env_rows(&root.join(".step3-review-result.env"));let loop_status=values.get("LOOP_STATUS").cloned().or_else(||env::var("LOOP_STATUS").ok()).unwrap_or_default();let status=values.get("STEP3_REVIEW_LOOP_STATUS").cloned().or_else(||env::var("STEP3_REVIEW_LOOP_STATUS").ok()).unwrap_or_default();if ["main-agent-apply-required","per-round-approval-required","postplan-operator-required"].contains(&status.as_str())||status.is_empty()&&["complete","zero-findings-degraded-panel","main-agent-vote-required"].contains(&loop_status.as_str()){if let Err(error)=completed(&root,false){eprintln!("cli.py plan-review step35: {error}");return ExitCode::FAILURE;}}let approve=json_bool_value(&root.join("run-params.json"),"approve_requested",false);emit_kv("APPROVE_REQUESTED",if approve{"true"}else{"false"});ExitCode::SUCCESS}
    fn json_bool_value(path:&Path,key:&str,default:bool)->bool{if !path.is_file()||path.is_symlink(){return default;}serde_json::from_str::<Value>(&read(path)).ok().and_then(|v|v.as_object().and_then(|o|o.get(key)).and_then(Value::as_bool)).unwrap_or(default)}

    #[derive(Default)]struct CollectorRow{reviewer:String,tool:String,status:String,exit_code:String,failure_reason:String,sidecar:String}
    fn collector_rows(body:&str)->Vec<CollectorRow>{let mut rows=Vec::new();let mut current:Option<BTreeMap<String,String>>=None;for line in body.lines(){if let Some(parsed)=parse_single_kv_row(line,ParseOptions::legacy()){let key=parsed.key();let value=parsed.value();if key=="REVIEWER_FILE"{if let Some(row)=current.take(){rows.push(row);}current=Some(BTreeMap::from([(key.into(),value.into())]));}else if let Some(row)=current.as_mut(){row.insert(key.into(),value.into());}}else if line.trim().is_empty(){if let Some(row)=current.take(){rows.push(row);}}}if let Some(row)=current{rows.push(row);}rows.into_iter().map(|r|CollectorRow{reviewer:r.get("REVIEWER_FILE").cloned().unwrap_or_default(),tool:r.get("TOOL").cloned().unwrap_or_default(),status:r.get("STATUS").cloned().unwrap_or_default(),exit_code:r.get("EXIT_CODE").cloned().unwrap_or_default(),failure_reason:r.get("FAILURE_REASON").cloned().unwrap_or_default(),sidecar:r.get("STRUCTURED_SIDECAR").cloned().unwrap_or_default()}).collect()}
    fn manifest_rows(path:&Path)->Vec<PlanReviewManifestSlot>{read(path).lines().filter_map(|line|serde_json::from_str::<Value>(line).ok()).filter_map(|v|{let o=v.as_object()?;Some(PlanReviewManifestSlot{slot:o.get("slot").and_then(Value::as_str).unwrap_or("").trim().into(),tool:o.get("tool").and_then(Value::as_str).unwrap_or("").into(),output:o.get("output").and_then(Value::as_str).unwrap_or("").into(),agent:o.get("agent").and_then(Value::as_str).unwrap_or("").into(),prompt_file:o.get("prompt_file").and_then(Value::as_str).unwrap_or("").into()})}).collect()}
    fn structured_rows(path:&Path)->Vec<PlanReviewStructuredFinding>{if !path.is_file()||path.is_symlink(){return Vec::new();}let body=read(path);let mut maps=Vec::<BTreeMap<String,String>>::new();if path.extension().and_then(|v|v.to_str())==Some("jsonl"){for line in body.lines(){if let Ok(Value::Object(row))=serde_json::from_str::<Value>(line){maps.push(row.into_iter().map(|(k,v)|(k,v.as_str().map_or_else(||v.to_string(),str::to_owned))).collect());}}}else{let mut lines=body.lines();let headers=lines.next().map(|v|v.split('\t').map(str::to_owned).collect::<Vec<_>>()).unwrap_or_default();for line in lines{maps.push(headers.iter().cloned().zip(line.split('\t').map(str::to_owned)).collect());}}maps.into_iter().map(|m|PlanReviewStructuredFinding{scope:m.get("scope").map_or("",String::as_str).trim().to_ascii_lowercase(),severity:m.get("severity").map_or("",String::as_str).trim().into(),focus_area:m.get("focus_area").map_or("",String::as_str).trim().into(),location:m.get("location").map_or("",String::as_str).trim().into(),what:m.get("what").map_or("",String::as_str).trim().into(),scenario_or_breakage:m.get("scenario_or_breakage").map_or("",String::as_str).trim().into(),suggested_fix:m.get("suggested_fix").map_or("",String::as_str).trim().into()}).collect()}
    fn collector_core(root:&Path,body:&str)->Vec<PlanReviewCollectorRecord>{collector_rows(body).into_iter().map(|row|{let candidates=[PathBuf::from(&row.sidecar),PathBuf::from(format!("{}.tsv",row.reviewer)),PathBuf::from(format!("{}.jsonl",row.reviewer))];let mut sidecar=candidates.into_iter().find(|p|!p.as_os_str().is_empty()&&p.is_file());if sidecar.is_none()&&!row.reviewer.is_empty()&&Path::new(&row.reviewer).is_file(){let extension=if matches!(row.tool.as_str(),"cursor"|"codex"){"tsv"}else{"jsonl"};let output=PathBuf::from(format!("{}.{extension}",row.reviewer));let args=vec!["eval".into(),"validate-research-output".into(),"--structured-reviewer-mode".into(),"--write-structured".into(),output.as_os_str().into(),row.reviewer.clone().into()];if child_owned(args).is_ok_and(|v|v.status().success())&&output.is_file(){sidecar=Some(output);}}if row.status!="OK"{let slug=Regex::new(r"[^A-Za-z0-9._+-]+").expect("static slug regex").replace_all(Path::new(&row.reviewer).file_stem().and_then(|v|v.to_str()).unwrap_or("slot"),"_");let log=root.join(format!("{}-collector.failure.log",slug.trim_matches('_')));let _=write(root,&log,&format!("REVIEWER_FILE={}|TOOL={}|STATUS={}|EXIT_CODE={}|FAILURE_REASON={}\n",row.reviewer,row.tool,row.status,row.exit_code,row.failure_reason));let _=child_owned(vec!["run-log".into(),"append-failure".into(),"--log".into(),root.join("execution-issues.md").into_os_string(),"--site".into(),"design Step 3".into(),"--tool".into(),format!("collect-results {} {}",row.tool,row.status).into(),"--exit-code".into(),if row.exit_code.is_empty(){"1".into()}else{row.exit_code.into()},"--category".into(),"External Reviewer Issues".into(),"--output-file".into(),log.into_os_string(),"--redact".into()]);}PlanReviewCollectorRecord{reviewer_file:row.reviewer,tool:row.tool,status:row.status,structured_findings:sidecar.as_deref().map(structured_rows).unwrap_or_default()}}).collect()}
    fn write_status_records(root:&Path,round:u64,slots:&[PlanReviewManifestSlot],records:&[PlanReviewCollectorRecord],header_fallback:bool){let artifacts=PlanReviewRoundArtifacts::new(root,round);let rows=reviewer_status_rows(slots,records);if rows.is_empty()&&!header_fallback{return;}let _=fs::create_dir_all(artifacts.round_dir());if artifacts.reviewer_status_tsv().is_symlink(){return;}let tsv=render_reviewer_status_tsv(&rows);let _=write(root,&artifacts.reviewer_status_tsv(),&tsv);if !artifacts.latest_reviewer_status_tsv().is_symlink(){let _=write(root,&artifacts.latest_reviewer_status_tsv(),&tsv);}if let Some(table)=render_reviewer_status_table(&rows){let table=format!("{table}\n");if !artifacts.reviewer_status_table().is_symlink(){let _=write(root,&artifacts.reviewer_status_table(),&table);}if !artifacts.stable_reviewer_status_table().is_symlink(){let _=write(root,&artifacts.stable_reviewer_status_table(),&table);}}else{remove(&artifacts.reviewer_status_table());remove(&artifacts.stable_reviewer_status_table());}}
    fn materialize_status(root:&Path,round:u64,collect:Option<&str>,header_fallback:bool){let artifacts=PlanReviewRoundArtifacts::new(root,round);let slots=manifest_rows(&artifacts.slots_manifest());let owned;let body=if let Some(value)=collect{value}else{owned=read(&artifacts.collector_results());&owned};let records=collector_core(root,body);write_status_records(root,round,&slots,&records,header_fallback);}
    fn materialize_existing_status(root:&Path,round:u64,sync_latest:bool){let artifacts=PlanReviewRoundArtifacts::new(root,round);let source=artifacts.reviewer_status_tsv();let stable=artifacts.stable_reviewer_status_table();if !source.is_file()||source.is_symlink()||artifacts.round_dir().is_symlink(){remove(&stable);return;}if sync_latest&&!artifacts.latest_reviewer_status_tsv().is_symlink(){let _=fs::copy(&source,artifacts.latest_reviewer_status_tsv());}if stable.is_symlink(){remove(&stable);}let body=String::from_utf8_lossy(&fs::read(&source).unwrap_or_default()).into_owned();let mut reader=csv::ReaderBuilder::new().delimiter(b'\t').flexible(true).from_reader(body.as_bytes());let Ok(headers)=reader.headers().cloned()else{remove(&artifacts.reviewer_status_table());remove(&stable);return;};let Some(slot_i)=headers.iter().position(|v|v=="slot")else{remove(&artifacts.reviewer_status_table());remove(&stable);return;};let Some(status_i)=headers.iter().position(|v|v=="status")else{remove(&artifacts.reviewer_status_table());remove(&stable);return;};let elapsed_i=headers.iter().position(|v|v=="elapsed");let rows=reader.records().filter_map(Result::ok).filter_map(|row|{let slot=row.get(slot_i).unwrap_or("").trim();if slot.is_empty(){return None;}Some(PlanReviewReviewerStatus{slot:slot.into(),status:row.get(status_i).unwrap_or("").trim().to_ascii_lowercase(),elapsed:elapsed_i.and_then(|i|row.get(i)).unwrap_or("").trim().into()})}).collect::<Vec<_>>();if let Some(table)=render_reviewer_status_table(&rows){let body=format!("{table}\n");if !artifacts.reviewer_status_table().is_symlink(){let _=write(root,&artifacts.reviewer_status_table(),&body);}let _=write(root,&stable,&body);}else{remove(&artifacts.reviewer_status_table());remove(&stable);}}
    fn clean_round(root:&Path,round:u64){let dir=root.join(format!("plan-review/round-{round}"));if !dir.is_dir()||dir.is_symlink(){return;}if let Ok(entries)=fs::read_dir(dir){for entry in entries.flatten(){let path=entry.path();let status_link=entry.file_name()=="reviewer-status.tsv"&&path.is_symlink();if entry.file_name()!="round-start-s"&&(path.is_file()&&!path.is_symlink()||status_link){remove(&path);}}}}
    fn now_s()->u64{SystemTime::now().duration_since(UNIX_EPOCH).map_or(0,|v|v.as_secs())}
    fn child_quiet(args:Vec<OsString>)->Result<larch_core::ProcessOutput,String>{run_verified_larch_with_environment(&args,&[(ChildEnvironment::LarchQuietDisable,"1".into())])}
    fn prune(root:&Path,round:u64,path:&Path)->String{let out=child_quiet(vec!["review".into(),"prune-nit-findings".into(),"--findings-file".into(),path.as_os_str().into(),"--audit-file".into(),root.join(format!("plan-review/round-{round}/oos-dropped-before-vote.md")).into_os_string(),"--security-audit-file".into(),root.join("security-oos-observations.md").into_os_string()]);out.map_or_else(|_|String::new(),|v|String::from_utf8_lossy(v.stdout()).into_owned())}
    const EMPTY_SCOREBOARDS:&str="## Voter Agreement Scoreboard\n\n| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |\n|---|---|---:|---:|---:|---:|---:|---|\n| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |\n\nAgreement is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n\n## Voter Severity Scoreboard\n\n| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |\n\nSeverity calibration is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n";
    fn reset_zero(root:&Path)->String{for name in ["accepted-plan-findings.md","rejected-findings.md","oos.md"]{let _=write(root,&root.join(name),"");}let tally=root.join("voting-tally.md");let _=write(root,&tally,&format!("# Plan Review Voting Tally\n\n**Zero findings: reviewers reported no actionable items; voting skipped.**\n\n{EMPTY_SCOREBOARDS}"));tally.display().to_string()}
    fn emit_round(values:&BTreeMap<String,String>){let order=["PANEL_PRUNED_EMPTY","TALLY_PLAN_REVIEW_STATUS","AGGREGATOR_STATUS","ACCEPTED_COUNT","DEGRADED_PANEL","INVALID_SLOT_PANEL_WARNING","DEGRADED_PANEL_WARNING","VOTING_TALLY_FILE","SCOPE_ANCHOR_FILE","LOOP_STATUS","REASON","ROUNDS_COMPLETED"];let mut seen=BTreeSet::new();for key in order{if let Some(value)=values.get(key){emit_kv(key,value);seen.insert(key);}}for(key,value)in values{if !seen.contains(key.as_str()){emit_kv(key,value);}}}
    fn attributed_ballot(root:&Path,oos:&str)->String{let ins=read(&root.join("findings-in-scope.md"));let parts=[ins.trim(),oos.trim()].into_iter().filter(|v|!v.is_empty()).collect::<Vec<_>>();if parts.is_empty(){String::new()}else{format!("{}\n",parts.join("\n\n"))}}
    pub(crate) fn proposer_map(ballot:&str)->Result<(String,String),String>{let blocks=ballot_blocks(ballot)?;let attr=Regex::new(r"(?m)^(?P<prefix>[ \t-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)[ \t]*:[ \t]*)(?P<value>.*?)(?P<trailing>[ \t]*)$").expect("static attribution regex");let mut map_rows=Vec::new();let mut neutral=ballot.to_owned();for(id,block)in &blocks{let found=attr.captures(block).ok_or_else(||format!("proposer map missing item(s): {id}"))?;let reviewer=found.name("value").map_or("",|v|v.as_str()).replace('*',"").trim().to_owned();if reviewer.is_empty()||reviewer.eq_ignore_ascii_case("anonymous"){return Err(format!("ballot item {id} has missing or neutral reviewer attribution"));}let line=found.get(0).map_or("",|v|v.as_str());map_rows.push((id.clone(),reviewer.replace(['\t','\r','\n']," "),line.replace(['\t','\r','\n']," ")));let neutral_block=attr.replacen(block,1,"${prefix}anonymous${trailing}");neutral=neutral.replacen(block,&neutral_block,1);}let attributed_hash=format!("{:x}",Sha256::digest(ballot.as_bytes()));let neutral_hash=format!("{:x}",Sha256::digest(neutral.as_bytes()));let mut map=format!("# attributed_ballot_sha256={attributed_hash}\n# neutral_ballot_sha256={neutral_hash}\nitem_id\treviewer\treviewer_line\n");for(id,reviewer,line)in map_rows{map.push_str(&format!("{id}\t{reviewer}\t{line}\n"));}Ok((map,neutral))}
    fn record_prune(root:&Path,round:u64){let artifacts=PlanReviewRoundArtifacts::new(root,round);if !artifacts.findings_classification_tsv().is_file(){return;}let slots=manifest_rows(&artifacts.slots_manifest());let label=root.join("plan-review-prune-label-map.tsv");let labels=slots.iter().map(|s|format!("{}\t{}\n",s.slot,larch_core::review::slot_human_label(&s.slot))).collect::<String>();let _=write(root,&label,&labels);let out=child_owned(vec!["review".into(),"reviewer-prune".into(),"record".into(),"--ledger".into(),root.join("reviewer-prune-ledger.tsv").into_os_string(),"--round".into(),round.to_string().into(),"--manifest".into(),artifacts.slots_manifest().into_os_string(),"--classification".into(),artifacts.findings_classification_tsv().into_os_string(),"--label-map".into(),label.into_os_string(),"--reviewer-status".into(),artifacts.reviewer_status_tsv().into_os_string()]);if let Err(error)=out{emit_kv("WARN",&format!("plan-review reviewer-prune record failed for round {round}: {error}"));}}
    fn snapshot_aggregator(root:&Path,round:u64){let dir=root.join(format!("plan-review/round-{round}"));let _=fs::create_dir_all(&dir);for name in ["aggregator-dispatch.env","aggregator-output.txt","aggregator.stderr","aggregator-output.candidate.txt","aggregator-validation.env","aggregator-validation.stderr","aggregator-validation-output.txt"]{let source=root.join(name);let target=dir.join(name);if source.is_file()&&!source.is_symlink()&&!target.is_symlink(){let _=fs::copy(source,target);}}}
    fn log_insufficient(root:&Path,round:u64){let note=root.join(format!("aggregator-insufficient-input-round-{round}.warning.log"));let _=write(root,&note,&format!("plan-review round {round} aggregator returned insufficient-input: too few reviewers survived for the aggregator to produce meaningful output; the round produced no useful review coverage.\n"));let _=child_owned(vec!["run-log".into(),"append-failure".into(),"--log".into(),root.join("execution-issues.md").into_os_string(),"--site".into(),"design Step 3".into(),"--tool".into(),format!("plan-review aggregator round {round}").into(),"--exit-code".into(),"0".into(),"--category".into(),"Warnings".into(),"--output-file".into(),note.into_os_string(),"--redact".into(),"--status-label".into(),"insufficient-input".into()]);}

    fn apply_round_state(values:&mut BTreeMap<String,String>,state:&PlanReviewRoundState){values.insert("PANEL_PRUNED_EMPTY".into(),if state.panel_pruned_empty{"true".into()}else{"false".into()});values.insert("LOOP_STATUS".into(),state.loop_status.clone());values.insert("TALLY_PLAN_REVIEW_STATUS".into(),state.tally_status.clone());values.insert("AGGREGATOR_STATUS".into(),state.aggregator_status.clone());values.insert("ACCEPTED_COUNT".into(),state.accepted_count.to_string());values.insert("DEGRADED_PANEL".into(),if state.degraded_panel{"1".into()}else{"0".into()});if let Some(rounds)=state.rounds_completed{values.insert("ROUNDS_COMPLETED".into(),rounds.to_string());}}
    fn finish_round(root:&Path,round:u64,state:PlanReviewRoundState,mut values:BTreeMap<String,String>,write_summary:bool)->(i32,BTreeMap<String,String>){apply_round_state(&mut values,&state);if write_summary{let artifacts=PlanReviewRoundArtifacts::new(root,round);let _=fs::create_dir_all(artifacts.round_dir());let _=write(root,&artifacts.round_summary_env(),&state.summary().render());}emit_round(&values);(state.exit_code,values)}
    fn log_dropped_slots(root:&Path,dropped_file:&str)->Result<(),String>{if dropped_file.is_empty(){return Ok(());}let path=Path::new(dropped_file);if !path.is_file()||path.is_symlink(){return Ok(());}let slug_pattern=Regex::new(r"[^A-Za-z0-9._+-]+").expect("static slug regex");for line in read(path).lines().filter(|line|!line.is_empty()){let mut fields=line.split('\t');let slot=fields.next().unwrap_or("");let tool=fields.next().unwrap_or("");let reason=fields.next().unwrap_or("");let detail=fields.next().unwrap_or("");if reason!="collector-failure"{continue;}let slug=slug_pattern.replace_all(slot,"_");let slug=slug.trim_matches('_').chars().take(200).collect::<String>();let fail_log=root.join(format!("{}-dispatch-drop.failure.log",if slug.is_empty(){"slot"}else{&slug}));write(root,&fail_log,&format!("reviewer slot {slot} ({tool}) dropped by waterfall dispatcher before collection: {reason}\n{detail}\n"))?;let _=child_owned(vec!["run-log".into(),"append-failure".into(),"--log".into(),root.join("execution-issues.md").into_os_string(),"--site".into(),"design Step 3".into(),"--tool".into(),format!("plan-review dispatcher-drop {tool} {reason}").into(),"--exit-code".into(),"1".into(),"--category".into(),"External Reviewer Issues".into(),"--output-file".into(),fail_log.into_os_string(),"--redact".into()]);}Ok(())}
    fn epoch_s_f64()->f64{SystemTime::now().duration_since(UNIX_EPOCH).map_or(0.0,|value|value.as_secs_f64())}
    fn record_reviewer_collect(root:&Path,round:u64,start:f64){let ledger=root.join("timing-ledger.tsv");if !ledger.is_file()||ledger.is_symlink(){return;}let args=vec!["--ledger".into(),ledger.clone().into_os_string(),"--vendor".into(),"claude".into(),"--task-kind".into(),"reviewer-collect".into(),"--start-s".into(),start.to_string().into(),"--end-s".into(),epoch_s_f64().to_string().into(),"--output".into(),format!("reviewer-collect-round-{round}.out").into(),"--exit-code".into(),"0".into(),"--status".into(),"complete".into()];let environment=[("LARCH_TIMING_SKILL",OsString::from("design")),("LARCH_TIMING_LEDGER",ledger.into_os_string()),("DESIGN_TMPDIR",root.as_os_str().into())];let _=crate::timing_commands::record_vendor_task_with_environment(&args,&environment);}
    fn round_once(root:&Path,round:u64)->(i32,BTreeMap<String,String>){
        let mut values=BTreeMap::from([("PANEL_PRUNED_EMPTY".into(),"false".into()),("TALLY_PLAN_REVIEW_STATUS".into(),"ok".into()),("AGGREGATOR_STATUS".into(),"ok".into()),("ACCEPTED_COUNT".into(),"0".into()),("DEGRADED_PANEL".into(),"0".into())]);
        let mut input=PlanReviewRoundInput::default();
        let mut transcript=String::new();
        let codex=env::var("CODEX_BINARY_FOUND").unwrap_or_else(|_|"false".into());
        let cursor=env::var("CURSOR_BINARY_FOUND").unwrap_or_else(|_|"false".into());
        let (tier,escalated)=match resolve_difficulty(root,Some(round)){Ok(value)=>value,Err(error)=>{eprintln!("plan-review round: {error}");input.panel.exit_code=1;materialize_status(root,round,Some(""),true);return finish_round(root,round,run_plan_review_round(round,&input),values,false)}};
        let panel=child_quiet(vec!["plan-review".into(),"panel-dispatch".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--round-num".into(),round.to_string().into(),"--prune-round-num".into(),round.to_string().into(),"--plan-file".into(),root.join("plan.txt").into_os_string(),"--feature-file".into(),root.join("feature-description.txt").into_os_string(),"--codex-present".into(),codex.clone().into(),"--cursor-present".into(),cursor.clone().into(),"--timeout".into(),"1860".into(),"--tier".into(),tier.into(),"--escalated-round".into(),if escalated{"true".into()}else{"false".into()}]);
        let panel=match panel{Ok(value)=>value,Err(error)=>{eprintln!("plan-review round: {error}");input.panel.exit_code=1;materialize_status(root,round,Some(""),true);return finish_round(root,round,run_plan_review_round(round,&input),values,false)}};
        let collect_start=epoch_s_f64();
        input.panel.exit_code=code(&panel);
        if input.panel.exit_code!=0{let _=io::stderr().write_all(panel.stderr());materialize_status(root,round,Some(""),true);return finish_round(root,round,run_plan_review_round(round,&input),values,false);}
        transcript.push_str(&String::from_utf8_lossy(panel.stdout()));
        let panel_kv=kv_text(&String::from_utf8_lossy(panel.stdout()));
        input.panel.panel_pruned_empty=panel_kv.get("PANEL_PRUNED_EMPTY").map(String::as_str)==Some("true");
        if let Some(warn)=panel_kv.get("INVALID_SLOT_PANEL_WARNING").or_else(||panel_kv.get("DEGRADED_PANEL_WARNING")){values.insert("INVALID_SLOT_PANEL_WARNING".into(),warn.clone());}
        if input.panel.panel_pruned_empty{values.insert("VOTING_TALLY_FILE".into(),reset_zero(root));materialize_status(root,round,Some(""),true);return finish_round(root,round,run_plan_review_round(round,&input),values,true);}
        if let Err(error)=log_dropped_slots(root,panel_kv.get("DROPPED_SLOTS_FILE").map_or("",String::as_str)){eprintln!("plan-review round: {error}");input.panel.exit_code=1;return finish_round(root,round,run_plan_review_round(round,&input),values,false);}

        let paths=panel_kv.get("PANEL_PATHS_FILE").or_else(||panel_kv.get("ALL_OUTPUT_FILES_PATH")).cloned().unwrap_or_else(||root.join("plan-review-panel-paths.txt").display().to_string());
        let path=PathBuf::from(paths);
        let (collect_rc,collect_text)=if path.is_file()&&path.metadata().is_ok_and(|meta|meta.len()>0){match child_quiet(vec!["agent".into(),"collect-results".into(),"--timeout".into(),"1860".into(),"--substantive-validation".into(),"--validation-mode".into(),"--paths-file".into(),path.into_os_string()]){Ok(output)=>(code(&output),String::from_utf8_lossy(output.stdout()).into_owned()),Err(_)=>(1,String::new())}}else{(0,String::new())};
        let collector_body=format!("{}{}",collect_text,if collect_text.is_empty()||collect_text.ends_with('\n'){""}else{"\n"});
        let _=write(root,&root.join("collector-results.env"),&collector_body);
        let raw_records=collector_rows(&collect_text);
        input.collection.exit_code=collect_rc;
        input.collection.record_count=raw_records.len();
        if collect_rc!=0&&raw_records.is_empty(){materialize_status(root,round,Some(&collect_text),false);return finish_round(root,round,run_plan_review_round(round,&input),values,false);}
        let slots=manifest_rows(&root.join("plan-review-slots.ndjson"));
        let records=collector_core(root,&collect_text);
        let findings=normalize_collected_findings(&records,&slots);
        input.collection.ok_count=findings.ok_count;
        input.collection.failure_count=findings.failure_count;
        write_status_records(root,round,&slots,&records,false);
        let _=write(root,&root.join("findings-in-scope.pre-dedup.md"),&findings.in_scope_markdown);
        let _=write(root,&root.join("findings-oos.pre-dedup.md"),&findings.out_of_scope_markdown);
        let _=write(root,&root.join("findings-oos.md"),&findings.out_of_scope_markdown);
        let findings_path=root.join("findings-in-scope.md");
        let oos_path=root.join("findings-oos.md");
        let _=write(root,&findings_path,&findings.in_scope_markdown);
        transcript.push_str(&prune(root,round,&findings_path));
        transcript.push_str(&prune(root,round,&oos_path));
        record_reviewer_collect(root,round,collect_start);

        let aggregate=child_quiet(vec!["review".into(),"aggregate-findings".into(),"--findings-file".into(),findings_path.as_os_str().into(),"--review-tmpdir".into(),root.as_os_str().into(),"--codex-present".into(),codex.clone().into(),"--cursor-present".into(),cursor.clone().into(),"--mode".into(),"description".into(),"--input-mode".into(),"plan".into(),"--plan-file".into(),root.join("plan.txt").into_os_string(),"--scope-anchor-file".into(),root.join("plan-review-scope-anchor.txt").into_os_string(),"--round-dir".into(),root.join(format!("plan-review/round-{round}")).into_os_string()]);
        match aggregate{Ok(output)=>{let agg_kv=kv_text(&String::from_utf8_lossy(output.stdout()));input.aggregation=PlanReviewAggregationOutcome{exit_code:code(&output),reason:agg_kv.get("REASON").cloned().unwrap_or_default(),aggregated:agg_kv.get("AGGREGATED").map(String::as_str)==Some("true")};},Err(_)=>input.aggregation.exit_code=1}
        input.ballot.has_canonical_items=true;
        input.voter.dispatch_ok=true;
        let aggregation_state=run_plan_review_round(round,&input);
        if aggregation_state.aggregator_status=="insufficient-input"&&findings.ok_count<2{log_insufficient(root,round);}else if !matches!(aggregation_state.aggregator_status.as_str(),"ok"|"disabled"){snapshot_aggregator(root,round);}
        if aggregation_state.loop_status=="panel-failed"{return finish_round(root,round,aggregation_state,values,true);}
        transcript.push_str(&prune(root,round,&findings_path));
        transcript.push_str(&prune(root,round,&oos_path));
        let oos=read(&oos_path);
        let ballot_text=attributed_ballot(root,&oos);
        let ballot=root.join("ballot.txt");
        let proposer=root.join("proposer-map.tsv");
        let ballot_result=proposer_map(&ballot_text).and_then(|(map,neutral)|{write(root,&ballot,&neutral)?;write(root,&proposer,&map)?;Ok(())});
        let preparation_failed=match &ballot_result{Ok(())=>false,Err(_)=>true};
        input.ballot=PlanReviewBallotOutcome{preparation_failed,has_canonical_items:ballot_blocks(&ballot_text).is_ok_and(|blocks|!blocks.is_empty())};
        if let Err(error)=ballot_result{eprintln!("plan-review round: proposer map preparation failed: {error}");return finish_round(root,round,run_plan_review_round(round,&input),values,true);}
        let ballot_state=run_plan_review_round(round,&input);
        if ballot_state.loop_status=="zero-findings-degraded-panel"{values.insert("VOTING_TALLY_FILE".into(),reset_zero(root));values.entry("REASON".into()).or_insert_with(||"zero-findings-degraded-panel".into());return finish_round(root,round,ballot_state,values,true);}

        let voter=child_quiet(vec!["plan-review".into(),"voter-dispatch".into(),"--ballot-file".into(),ballot.as_os_str().into(),"--design-tmpdir".into(),root.as_os_str().into(),"--codex-available".into(),codex.into(),"--cursor-available".into(),cursor.into(),"--round-num".into(),round.to_string().into()]);
        let voter=match voter{Ok(output)=>output,Err(_)=>{input.voter=PlanReviewVoterOutcome{exit_code:1,dispatch_ok:false,degraded_panel:true};return finish_round(root,round,run_plan_review_round(round,&input),values,false)}};
        transcript.push_str(&String::from_utf8_lossy(voter.stdout()));
        let voter_kv=kv_text(&String::from_utf8_lossy(voter.stdout()));
        if let Some(warning)=voter_kv.get("DEGRADED_PANEL_WARNING"){values.insert("DEGRADED_PANEL_WARNING".into(),warning.clone());}
        input.voter=PlanReviewVoterOutcome{exit_code:code(&voter),dispatch_ok:voter_kv.get("DISPATCH_OK").map(String::as_str)==Some("true"),degraded_panel:voter_kv.get("DISPATCH_OK").map(String::as_str)!=Some("true")||voter_kv.get("DEGRADED_PANEL").is_some_and(|value|value.parse::<u64>().unwrap_or(0)==1)};
        let voter_state=run_plan_review_round(round,&input);
        if voter_state.loop_status=="panel-failed"{return finish_round(root,round,voter_state,values,false);}

        let artifacts=PlanReviewRoundArtifacts::new(root,round);
        let mut tally_args=vec!["plan-review".into(),"tally".into(),"--ballot-file".into(),ballot.into_os_string(),"--design-tmpdir".into(),root.as_os_str().into(),"--proposer-map-file".into(),proposer.into_os_string()];
        for(slot,key)in[("1","VOTER_1"),("2","VOTER_2"),("3","VOTER_3")]{let path=voter_kv.get(&format!("{key}_PATH")).cloned().unwrap_or_default();let tool=voter_kv.get(&format!("{key}_TOOL")).cloned().unwrap_or_default();let status=voter_kv.get(&format!("{key}_STATUS")).cloned().unwrap_or_default();if !path.is_empty()&&status!="failed"{let label=match tool.as_str(){"claude"=>"Claude","codex"=>"Codex","cursor"=>"Cursor",_=>&tool};tally_args.extend(["--voter".into(),format!("{slot}:{label}:{path}").into()]);}}
        let _=fs::create_dir_all(artifacts.round_dir());
        tally_args.extend(["--findings-classification-out".into(),artifacts.findings_classification_tsv().into_os_string()]);
        let tally=child_quiet(tally_args);
        let tally=match tally{Ok(output)=>output,Err(_)=>{input.tally=PlanReviewTallyOutcome{exit_code:1,status:String::new(),accepted_count:0};return finish_round(root,round,run_plan_review_round(round,&input),values,true)}};
        transcript.push_str(&String::from_utf8_lossy(tally.stdout()));
        let tally_kv=kv_text(&String::from_utf8_lossy(tally.stdout()));
        values.extend(tally_kv);
        let tally_status=values.get("TALLY_PLAN_REVIEW_STATUS").cloned().unwrap_or_else(||if code(&tally)==0{"ok".into()}else{"tally-error".into()});
        let accepted=parse_plan_review_accepted_findings(&read(&root.join("accepted-plan-findings.md"))).len();
        input.tally=PlanReviewTallyOutcome{exit_code:code(&tally),status:tally_status,accepted_count:accepted};
        let state=run_plan_review_round(round,&input);
        if state.loop_status=="zero-findings-degraded-panel"{values.entry("REASON".into()).or_insert_with(||"zero-findings-degraded-panel".into());}
        apply_round_state(&mut values,&state);
        let _=write(root,&artifacts.round_summary_env(),&state.summary().render());
        if !matches!(state.loop_status.as_str(),"tally-error"|"main-agent-vote-required"){record_prune(root,round);}
        if matches!(state.loop_status.as_str(),"complete"|"zero-findings-degraded-panel"|"degraded-empty-collector"){print!("{transcript}");}
        emit_round(&values);
        (state.exit_code,values)
    }

    #[must_use] pub fn delegate_script(name:&str,arguments:&[OsString])->ExitCode{let Ok(root)=plugin_root()else{return ExitCode::from(2)};let script=root.join("skills/design/scripts").join(name);if !script.is_file()||script.is_symlink(){return ExitCode::from(2);}let status=Command::new("bash").arg(script).args(arguments).current_dir(&root).status();/* lint-subprocess-via-runner: ok fixed retained generated wrapper with no typed executable owner */status.map_or(ExitCode::FAILURE,|s|ExitCode::from(u8::try_from(s.code().unwrap_or(1)).unwrap_or(1)))}

    #[must_use] pub fn step3_entry(arguments:&[OsString])->ExitCode{let parsed=match parsed_known(arguments,"cli.py plan-review step3-entry",ENTRY_USAGE,ENTRY_HELP,&["--design-tmpdir"],&["--reentry"],&["--design-tmpdir"]){Ok(v)=>v,Err(c)=>return c};let root=match root(&text(&parsed,"--design-tmpdir"),"cli.py plan-review step3-entry"){Ok(v)=>v,Err(c)=>return c};if parsed.flag("--reentry"){let _=touch(&root.join(".step3-reentry"));}remove(&root.join(".pause-save-complete"));let stripped=root.join(".plan-review-scope-stripped.txt");let source=[root.join("issue-body.txt"),root.join("feature-description.txt")].into_iter().find(|p|p.is_file()&&p.metadata().is_ok_and(|m|m.len()>0));if let Some(source)=source{let out=child_owned(vec!["plan-block".into(),"strip-body".into(),"--file".into(),source.into_os_string(),"--output".into(),stripped.as_os_str().into()]);if !out.is_ok_and(|v|v.status().success()){let _=prelaunch_failure(&["--design-tmpdir".into(),root.as_os_str().into(),"--reason".into(),"strip-body-failure".into()]);return ExitCode::FAILURE;}}else{let _=write(&root,&stripped,"");}let mut body=read(&stripped);if root.join("design-outline.md").is_file()&&root.join(".outline-approved").is_file(){body.push_str("\n\n## Approved direction (outline)\n\n");body.push_str(&read(&root.join("design-outline.md")));}let body=body.trim();if body.is_empty(){let _=prelaunch_failure(&["--design-tmpdir".into(),root.as_os_str().into(),"--reason".into(),"scope-anchor-missing".into()]);return ExitCode::FAILURE;}let redacted=redact_secrets_only(body);if redacted.trim().is_empty()||write(&root,&root.join("plan-review-scope-anchor.txt"),&format!("{}{}",redacted,if redacted.ends_with('\n'){""}else{"\n"})).is_err(){let _=prelaunch_failure(&["--design-tmpdir".into(),root.as_os_str().into(),"--reason".into(),"scope-anchor-missing".into()]);return ExitCode::FAILURE;}emit_kv("SCOPE_ANCHOR_FILE",&root.join("plan-review-scope-anchor.txt").display().to_string());ExitCode::SUCCESS}

    fn record_evidence(root:&Path,status:&str)->bool{if !["panel-failed","panel-init-failed","tally-error","degraded-empty-collector"].contains(&status){return true;}let sentinel=root.join(format!(".step3-report-{status}.recorded"));if sentinel.exists()||sentinel.is_symlink(){return true;}let args=vec!["stall-recovery".into(),"record-escalation".into(),"--profile".into(),"generic".into(),"--artifact-prefix".into(),"design-failure".into(),"--implement-tmpdir".into(),root.as_os_str().into(),"--site".into(),"step3-review".into(),"--trigger".into(),status.into(),"--step".into(),"step3".into(),"--phase".into(),"validation".into(),"--dispatcher".into(),"design-step3-review".into()];match child_owned(args){Ok(out)=>{let _=write(root,&root.join(format!("step3-record-escalation-{status}.stdout.log")),&String::from_utf8_lossy(out.stdout()));let _=write(root,&root.join(format!("step3-record-escalation-{status}.stderr.log")),&String::from_utf8_lossy(out.stderr()));if out.status().success(){let _=touch(&sentinel);true}else{false}},Err(_)=>false}}
    fn stage_postplan(root:&Path,postplan_rc:&str)->bool{let sentinel=root.join(".step3-postplan-terminal-state.recorded");if sentinel.exists()||sentinel.is_symlink(){return true;}let args=vec!["design".into(),"stage-terminal-state".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--outcome".into(),"failed-postplan".into(),"--step".into(),"postplan".into(),"--phase".into(),"postplan".into(),"--site".into(),"step3-review".into(),"--trigger".into(),"postplan-failed".into(),"--bail-reason".into(),"postplan-failed".into(),"--exit-code".into(),postplan_rc.into(),"--source-script".into(),"design-step3-review".into(),"--summary-outcome".into(),"failed-postplan".into()];match run_python_verb(args,SIMPLE_TIMEOUT){Ok(out)=>{let _=write(root,&root.join("step3-stage-terminal-state.stdout.log"),&String::from_utf8_lossy(out.stdout()));let _=write(root,&root.join("step3-stage-terminal-state.stderr.log"),&String::from_utf8_lossy(out.stderr()));if out.status().success(){let _=touch(&sentinel);true}else{false}},Err(_)=>false}}
    fn stage_panel_init(root:&Path,reason:&str)->bool{let sentinel=root.join(".step3-panel-init-terminal-state.recorded");if sentinel.exists()||sentinel.is_symlink(){return true;}let slug=reason.chars().map(|c|if c.is_ascii_alphanumeric()||matches!(c,'_'|'-'){c}else{'-'}).collect::<String>().trim_matches('-').to_owned();let args=vec!["design".into(),"stage-terminal-state".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--outcome".into(),"failed-judge-panel".into(),"--step".into(),"step3".into(),"--phase".into(),"validation".into(),"--site".into(),"step3-review".into(),"--trigger".into(),"panel-init-failed".into(),"--bail-reason".into(),"panel-init-failed".into(),"--exit-code".into(),"1".into(),"--source-script".into(),"design-step3-review".into(),"--summary-outcome".into(),"failed-judge-panel".into(),"--evidence-ref".into(),format!("prelaunch-{}",if slug.is_empty(){"unknown"}else{&slug}).into()];match run_python_verb(args,SIMPLE_TIMEOUT){Ok(out)=>{let _=write(root,&root.join("step3-panel-init-terminal-state.stdout.log"),&String::from_utf8_lossy(out.stdout()));let _=write(root,&root.join("step3-panel-init-terminal-state.stderr.log"),&String::from_utf8_lossy(out.stderr()));if out.status().success(){let _=touch(&sentinel);true}else{false}},Err(_)=>false}}

    fn persist_envelope(root:&Path,status:&str,round:u64,rounds:u64,final_round:u64,values:&BTreeMap<String,String>)->Result<(),String>{let fallback=values.get("LOOP_STATUS").map_or("complete",String::as_str);let loop_status=step3_loop_status_to_loop_status(status,fallback);let persisted_round=if status=="cap-hit"||["tally-error","degraded-empty-collector","panel-failed","postplan-failed"].contains(&status){String::new()}else if round>0{round.to_string()}else{String::new()};let review_count=if status=="cap-hit"{rounds}else if ["tally-error","degraded-empty-collector","panel-failed","postplan-failed"].contains(&status){read_count(root)}else{round};let mut rows:Vec<(String,String)>=Vec::new();let action=step3_next_action(status,&loop_status,values.get("TALLY_PLAN_REVIEW_STATUS").map_or("",String::as_str));if !action.is_empty(){rows.push(("NEXT_ACTION".into(),action));}if loop_status!="zero-findings-degraded-panel"{rows.push(("STEP3_REVIEW_LOOP_STATUS".into(),status.into()));}for(k,v)in[("LOOP_STATUS",loop_status),("FINAL_ROUND_NUM",(if final_round>0{final_round}else{round}).to_string()),("ROUNDS_COMPLETED",rounds.to_string()),("ACCEPTED_COUNT",values.get("ACCEPTED_COUNT").cloned().unwrap_or_else(||"0".into())),("IMPORTANT_ACCEPTED_COUNT",values.get("IMPORTANT_ACCEPTED_COUNT").cloned().unwrap_or_else(||"0".into())),("DEGRADED_PANEL",values.get("DEGRADED_PANEL").cloned().unwrap_or_else(||"0".into())),("STEP3_REVIEW_ROUND_NUM",persisted_round),("REVIEW_ROUND_COUNT",review_count.to_string()),("ROUND_NUM",values.get("ROUND_NUM").cloned().unwrap_or_else(||round.to_string())),("TALLY_PLAN_REVIEW_STATUS",values.get("TALLY_PLAN_REVIEW_STATUS").cloned().unwrap_or_default()),("AGGREGATOR_STATUS",values.get("AGGREGATOR_STATUS").cloned().unwrap_or_default()),("VOTING_TALLY_FILE",values.get("VOTING_TALLY_FILE").cloned().unwrap_or_default()),("PANEL_PRUNED_EMPTY",values.get("PANEL_PRUNED_EMPTY").cloned().unwrap_or_else(||"false".into())),("REASON",values.get("REASON").cloned().unwrap_or_default())]{rows.push((k.into(),v));}for key in ["POSTPLAN_RC","DEDUP_RC","DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING","PLAN_REVIEW_CONTINUE_REASON","SCOPE_ANCHOR_FILE"]{if let Some(v)=values.get(key).filter(|v|!v.is_empty()&&!v.contains(['\n','\r'])){rows.push((key.into(),v.clone()));}}let existing=env_rows(&root.join(".step3-review-result.env"));let present=rows.iter().filter(|(_,v)|!v.is_empty()).map(|(k,_)|k.clone()).collect::<BTreeSet<_>>();for key in MERGE_KEYS{if !present.contains(key){if let Some(v)=existing.get(key).filter(|v|!v.is_empty()){rows.push((key.into(),v.replace(['\n','\r'],"")));}}}write_rows(root,&root.join(".step3-review-result.env"),rows)}
    fn emit_envelope(root:&Path,status:&str,round:u64,rounds:u64,final_round:u64,values:&BTreeMap<String,String>)->Result<(),String>{if status=="postplan-failed"{if !stage_postplan(root,values.get("POSTPLAN_RC").map_or("unknown",String::as_str)){emit_kv("WARN","Step 3: failed to stage failed-postplan terminal state");}}else if !record_evidence(root,status){emit_kv("WARN",&format!("Step 3: failed to record design escalation evidence for {status}"));}let loop_status=values.get("LOOP_STATUS").map_or("",String::as_str);let action=step3_next_action(status,loop_status,values.get("TALLY_PLAN_REVIEW_STATUS").map_or("",String::as_str));if !action.is_empty(){emit_kv("NEXT_ACTION",&action);}if loop_status!="zero-findings-degraded-panel"{emit_kv("STEP3_REVIEW_LOOP_STATUS",status);}emit_kv("ROUNDS_COMPLETED",&rounds.to_string());emit_kv("FINAL_ROUND_NUM",&(if final_round>0{final_round}else{round}).to_string());emit_kv("ACCEPTED_COUNT",values.get("ACCEPTED_COUNT").map_or("0",String::as_str));emit_kv("DEGRADED_PANEL",values.get("DEGRADED_PANEL").map_or("0",String::as_str));for key in ["DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING","SCOPE_ANCHOR_FILE"]{if let Some(v)=values.get(key).filter(|v|!v.contains(['\n','\r'])){emit_kv(key,v);}}emit_kv("PLAN_REVIEW_CONTINUE_REASON",values.get("PLAN_REVIEW_CONTINUE_REASON").map_or("",String::as_str));emit_kv("REASON",values.get("REASON").map_or("",String::as_str));for key in ["POSTPLAN_RC","DEDUP_RC"]{if let Some(v)=values.get(key).filter(|v|!v.contains(['\n','\r'])){emit_kv(key,v);}}for(key,value)in env_rows(&root.join(".design-postplan-emit-result.env")){if ["POSTPLAN_EMIT_STATUS","EMIT_PLAN_STATUS","DIFF_LINES","VALIDATE_STATUS","VALIDATE_DEFECT_COUNT","PLAN_SIZE_STATUS","SIZE_TRIGGER_FIRED","TRIGGER_REASONS","PLAN_LINES","DIFF_ADDED","DIFF_DELETED","MECHANICAL_CHURN","FIRM_HEADINGS","SURFACES_TOUCHED","OVERSIZE_OVERRIDE","SOFT_ADVISORY","DRIFT_TRIGGER_FIRED","DRIFT_MULTIPLE","DRIFT_PLAN_RATIO","DRIFT_DIFF_RATIO","BASELINE_PLAN_LINES","BASELINE_DIFF_LINES","PARTITION_REQUESTED"].contains(&key.as_str()){emit_kv(&key,&value);}}persist_envelope(root,status,round,rounds,final_round,values)}
    fn emit_envelope_exit(root:&Path,status:&str,round:u64,rounds:u64,final_round:u64,values:&BTreeMap<String,String>)->ExitCode{match emit_envelope(root,status,round,rounds,final_round,values){Ok(())=>ExitCode::SUCCESS,Err(error)=>{eprintln!("plan-review run: {error}");ExitCode::FAILURE}}}
    fn complete_and_emit(root:&Path,both:bool,status:&str,round:u64,rounds:u64,final_round:u64,values:&BTreeMap<String,String>)->ExitCode{if let Err(error)=completed(root,both){eprintln!("plan-review run: {error}");return ExitCode::FAILURE;}emit_envelope_exit(root,status,round,rounds,final_round,values)}
    #[must_use] pub fn prelaunch_failure(arguments:&[OsString])->ExitCode{let parsed=match parsed(arguments,"cli.py plan-review prelaunch-failure",PRELAUNCH_USAGE,PRELAUNCH_HELP,&["--design-tmpdir","--reason"],&[],&["--design-tmpdir"]){Ok(v)=>v,Err(c)=>return c};let root=match root(&text(&parsed,"--design-tmpdir"),"cli.py plan-review prelaunch-failure"){Ok(v)=>v,Err(c)=>return c};let reason=if text(&parsed,"--reason").is_empty(){"panel-init-failed".into()}else{text(&parsed,"--reason")};if !stage_panel_init(&root,&reason){emit_kv("WARN","Step 3: failed to stage panel-init-failed terminal state");}let values=BTreeMap::from([("REASON".into(),reason),("LOOP_STATUS".into(),"panel-init-failed".into())]);emit_envelope_exit(&root,"panel-init-failed",0,0,0,&values)}

    fn normalized_tier(value:&str)->String{let value=value.to_ascii_uppercase();if matches!(value.as_str(),"TRIVIAL"|"MODERATE"|"HARD"){value}else{String::new()}}
    fn resolution_persisted(value:&Value)->bool{value.get("override_source").and_then(Value::as_str)==Some("operator")||value.get("audit_evaluated").is_some_and(|v|!v.is_null())||value.get("audit_upgrade").is_some_and(|v|!v.is_null())||value.get("escalations").and_then(Value::as_array).is_some_and(|rows|!rows.is_empty())}
    fn write_design_record(output:&Path,raw:&Path)->Result<(),String>{
        let rating=read_rating_file(raw).ok_or_else(||"invalid design rating".to_owned())?;
        let floors=plugin_root().ok().and_then(|root|load_floor_manifest(&root.join(FLOOR_MANIFEST_RELPATH)).ok()).unwrap_or_default();
        let record=build_record(BuildRecord{rater:"design",rater_tool:"claude",rater_model:"unknown",design_rating:Some(&rating),implement_rating:None,fallback_rating:None,changed_paths:&[],floors:&floors,panel_skipped:"",audit_upgrade:"",escalations:&[],override_source:"",override_tier:"",panel_tier:"",round_cap:None,codex_model_role:"",audit_evaluated:None,escalated_round:None})?;
        let merged=merge_existing_record_fields(record,&load_record_data(output),&blank_merge_explicit());
        write_record_map(output,&merged)
    }
    fn seed_difficulty(root:&Path)->Result<(),String>{
        let record_path=root.join("difficulty-rating.json");
        if record_path.is_symlink(){return Ok(());}
        let existing=serde_json::from_str::<Value>(&read(&record_path)).ok().filter(Value::is_object);
        if existing.as_ref().is_some_and(resolution_persisted){return Ok(());}
        let raw=root.join("design-difficulty-rating.raw.json");
        if raw.is_file()&&!raw.is_symlink(){
            if read_rating_file(&raw).is_none(){return Ok(());}
            write_design_record(&record_path,&raw)?;
            return Ok(());
        }
        if raw.exists()||raw.is_symlink(){return Ok(());}
        let plan=root.join("plan.txt");
        if !plan.is_file()||plan.is_symlink(){return Ok(());}
        let Ok(extracted)=extract_plan_difficulty(&plan) else {return Ok(());};
        let tier=normalized_tier(&extracted);
        if tier.is_empty(){return Ok(());}
        let seed_path=root.join(".plan-review-difficulty-seed.json");
        write(root,&seed_path,&format!("{{\n  \"confidence\": \"medium\",\n  \"predicted_tier\": \"{tier}\",\n  \"rationale\": \"design plan metadata\"\n}}\n"))?;
        let result=write_design_record(&record_path,&seed_path);
        remove(&seed_path);
        result
    }
    fn resolve_difficulty(root:&Path,round:Option<u64>)->Result<(String,bool),String>{seed_difficulty(root)?;let override_tier=serde_json::from_str::<Value>(&read(&root.join("run-params.json"))).ok().and_then(|value|value.get("difficulty_override").and_then(Value::as_str).map(normalized_tier)).unwrap_or_default();let resolution=resolve_panel_tier(&root.join("difficulty-rating.json"),&override_tier,None,true,None)?;let tier=normalized_tier(&resolution.panel_tier);if tier.is_empty(){return Err("difficulty resolution returned invalid PANEL_TIER".into());}let escalated=if let Some(round)=round{serde_json::from_str::<Value>(&read(&root.join("difficulty-rating.json"))).ok().and_then(|value|value.get("escalations").cloned()).and_then(|value|value.as_array().cloned()).is_some_and(|rows|rows.iter().any(|row|row.get("round").and_then(|value|value.as_u64().or_else(||value.as_str().and_then(|text|text.parse().ok())))==Some(round)))}else{resolution.escalated_round};Ok((tier,escalated))}
    fn append_escalation(root:&Path,round:u64,from:&str)->Result<(),String>{let path=root.join("difficulty-rating.json");let mut value=serde_json::from_str::<Value>(&read(&path)).ok().filter(Value::is_object).unwrap_or_else(||serde_json::json!({"schema_version":3,"rater":"fallback","rater_tool":"unknown","rater_model":"unknown","predicted_tier":from,"confidence":"medium","rationale":"escalation record","design_tier":null,"implement_tier":null,"floors_applied":[],"override_source":"none","audit_upgrade":null,"panel_skipped":null}));if let Some(object)=value.as_object_mut(){let escalations=object.entry("escalations").or_insert_with(||Value::Array(Vec::new()));if let Some(items)=escalations.as_array_mut(){items.push(serde_json::json!({"round":round,"from_tier":from,"to_tier":"HARD","trigger":"escalated-high-accepted"}));}object.insert("applied_tier".into(),"HARD".into());object.insert("panel_tier".into(),"HARD".into());object.insert("round_cap".into(),2.into());object.insert("codex_model_role".into(),"review".into());object.insert("escalated_round".into(),true.into());}let body=serde_json::to_string_pretty(&value).map_err(|error|error.to_string())?;write(root,&path,&format!("{body}\n"))}
    fn already_addressed_keys(root:&Path)->Vec<String>{let tag=Regex::new(r"(?i)\[ALREADY_ADDRESSED\]").expect("static tag regex");parse_blocks(&read(&root.join("rejected-findings.md")),BoundaryMode::ItemHeading).into_iter().filter(|b|b.kind==larch_core::review::ItemKind::Finding&&tag.is_match(&b.block)).map(|b|finding_dedup_key(&tag.replace_all(&b.block,"")).to_string()).filter(|v|!v.is_empty()).collect()}
    #[must_use] pub fn continuation(arguments:&[OsString])->ExitCode{
        let parsed=match parsed(arguments,"cli.py plan-review continuation",CONTINUATION_USAGE,CONTINUATION_HELP,&["--design-tmpdir","--approve-requested"],&[],&["--design-tmpdir","--approve-requested"]){Ok(v)=>v,Err(c)=>return c};let approve=text(&parsed,"--approve-requested");if !matches!(approve.as_str(),"true"|"false"){return usage_error(CONTINUATION_USAGE,"cli.py plan-review continuation",&format!("argument --approve-requested: invalid choice: '{approve}' (choose from 'true', 'false')"),2);}let root=match root(&text(&parsed,"--design-tmpdir"),"cli.py plan-review continuation"){Ok(v)=>v,Err(c)=>return c};let review_count=read_count(&root);let result=env_rows(&root.join(".step3-review-result.env"));let mut degraded=usize::from(matches!(result.get("DEGRADED_PANEL").map(String::as_str),Some("1"|"true")));let tally=result.get("TALLY_PLAN_REVIEW_STATUS").map_or("",String::as_str);let loop_status=result.get("LOOP_STATUS").map_or("",String::as_str);let reason0=result.get("REASON").map_or("",String::as_str);let pruned=result.get("PANEL_PRUNED_EMPTY").map_or("",String::as_str);let findings=parse_plan_review_accepted_findings(&read(&root.join("accepted-plan-findings.md")));let structured=!findings.is_empty()&&findings.iter().all(|f|matches!(f.severity_raw.as_str(),"major"|"minor"|"nit"));let accepted=findings.len();let nit=findings.iter().filter(|f|f.severity_raw=="nit").count();let non_nit=accepted.saturating_sub(nit);let high=if structured{findings.iter().filter(|f|f.severity_raw=="major").count()}else{let high_re=Regex::new(r"(?i)critical|\bhigh\b|data loss|regression|missing required").expect("static high regex");findings.iter().filter(|f|high_re.is_match(&f.block)).count()};let prior=applied_finding_keys_before(&read(&root.join(".step3-applied-finding-keys.tsv")),review_count);let keys=findings.iter().map(|f|finding_dedup_key(&f.block)).collect::<Vec<_>>();let fresh=keys.iter().map(|k|!prior.contains(k)).collect::<Vec<_>>();let duplicate=fresh.iter().filter(|v|!**v).count();let new_count=fresh.iter().filter(|v|**v).count();let nit_new=findings.iter().zip(&fresh).filter(|(f,n)|**n&&f.severity_raw=="nit").count();let non_nit_new=new_count.saturating_sub(nit_new);let high_new=if structured{findings.iter().zip(&fresh).filter(|(f,n)|**n&&f.severity_raw=="major").count()}else{let re=Regex::new(r"(?i)critical|\bhigh\b|data loss|regression|missing required").expect("static high regex");findings.iter().zip(&fresh).filter(|(f,n)|**n&&re.is_match(&f.block)).count()};let plan=read(&root.join("plan.txt"));let diff=terminal_plan_trailer_value(&plan,"diff_lines").and_then(|v|v.parse::<u64>().ok()).unwrap_or(0);let structural=diff>500||plan.lines().count()>120;if tally=="ok"&&loop_status=="complete"{degraded=0;}let resolved_tier=match resolve_difficulty(&root,None){Ok((tier,_))=>tier,Err(error)=>{eprintln!("cli.py plan-review continuation: {error}");return ExitCode::FAILURE}};let mut cont=false;let mut reason="small-clean".to_owned();let mut tier=String::new();
        if reason0.starts_with("ballot-items-lost")&&accepted==0&&degraded==1&&tally=="ok"&&loop_status=="zero-findings-degraded-panel"{cont=true;reason="ballot-items-lost".into();}else if approve=="true"{reason="explicit-approve".into();}else if high>=2&&high_new>0&&review_count<2{cont=true;if resolved_tier!="HARD"{reason="escalated-high-accepted".into();if let Err(error)=append_escalation(&root,review_count+1,&resolved_tier){eprintln!("cli.py plan-review continuation: {error}");return ExitCode::FAILURE;}}else{reason="high-accepted".into();}tier="HARD".into();}else if review_count>=2{reason="cap-reached".into();}else if pruned=="true"{reason="converged-pruned-empty".into();}else if degraded==1&&(high_new>0||non_nit_new>5){cont=true;reason="degraded-panel".into();}else if high_new>0{cont=true;reason="high-accepted".into();}else if non_nit_new>5{cont=true;reason="non-nit-accepted".into();}else if structural&&non_nit>0&&review_count<2{cont=true;reason="structural-or-large-change".into();}if !cont&&reason=="small-clean"&&duplicate>0&&high_new==0&&non_nit_new<=5&&(high>0||non_nit>5){reason="converged-no-new-findings".into();}
        let ledger=replace_applied_finding_keys(&read(&root.join(".step3-applied-finding-keys.tsv")),review_count,&keys);let _=write(&root,&root.join(".step3-applied-finding-keys.tsv"),&ledger);let addressed=already_addressed_keys(&root);if !addressed.is_empty(){let merged=merge_already_addressed_finding_keys(&read(&root.join(".step3-already-addressed-finding-keys.tsv")),&addressed);let _=write(&root,&root.join(".step3-already-addressed-finding-keys.tsv"),&merged);}for(k,v)in[("PLAN_REVIEW_CONTINUE",if cont{"true".into()}else{"false".into()}),("PLAN_REVIEW_CONTINUE_REASON",reason),("REVIEW_ROUND_COUNT",review_count.to_string()),("REVIEW_ROUND_CAP","2".into()),("PANEL_TIER",tier),("ACCEPTED_COUNT",accepted.to_string()),("NIT_ACCEPTED_COUNT",nit.to_string()),("NON_NIT_ACCEPTED_COUNT",non_nit.to_string()),("HIGH_ACCEPTED_COUNT",high.to_string()),("NEW_HIGH_ACCEPTED_COUNT",high_new.to_string()),("NEW_NON_NIT_ACCEPTED_COUNT",non_nit_new.to_string()),("DUPLICATE_ACCEPTED_COUNT",duplicate.to_string()),("DEGRADED_PANEL",degraded.to_string()),("STRUCTURAL_OR_LARGE_CHANGE",if structural{"true".into()}else{"false".into()})]{emit_kv(k,&v);}ExitCode::SUCCESS
    }
    const READ_RESULT_KEYS:[&str;10]=["BGJOB_RC","NEXT_ACTION","STEP3_REVIEW_LOOP_STATUS","LOOP_STATUS","ROUNDS_COMPLETED","FINAL_ROUND_NUM","ACCEPTED_COUNT","DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING","REASON"];
    const NORMALIZE_EMIT_KEYS:[&str;22]=["NEXT_ACTION","STEP3_REVIEW_LOOP_STATUS","LOOP_STATUS","POSTPLAN_RC","DEDUP_RC","FINAL_ROUND_NUM","TALLY_PLAN_REVIEW_STATUS","SCOPE_ANCHOR_FILE","STEP3_REVIEW_ROUND_NUM","ROUND_NUM","REVIEW_ROUND_COUNT","ROUNDS_COMPLETED","ACCEPTED_COUNT","IMPORTANT_ACCEPTED_COUNT","STEP3_REVIEW_CAP_REACHED","AGGREGATOR_STATUS","VOTING_TALLY_FILE","DEGRADED_PANEL","DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING","PLAN_REVIEW_CONTINUE_REASON","REASON"];
    fn replay_warn_error(path:&Path){if !path.is_file()||path.is_symlink(){return;}for line in read(path).lines(){if let Some(row)=parse_single_kv_row(line,ParseOptions::legacy())&&matches!(row.key(),"WARN"|"ERROR"){emit_kv(row.key(),row.value());}}}
    fn selected_result(root:&Path)->(PathBuf,&'static str){let bg=root.join("bgjob/design-step3-review.result.env");if bg.is_file()&&!bg.is_symlink(){return(bg,"ok");}let legacy=root.join(".step3-review-result.env");if legacy.is_file()&&!legacy.is_symlink(){return(legacy,"ok");}(bg,"missing")}
    fn normalize_read_result(root:&Path)->ExitCode{let(path,status)=selected_result(root);let mut values=env_rows(&path);let bgjob=values.get("BGJOB_RC").cloned().unwrap_or_default();let next=values.get("NEXT_ACTION").cloned().unwrap_or_default();let route=!next.is_empty()||values.get("STEP3_REVIEW_LOOP_STATUS").is_some_and(|v|!v.is_empty())||values.get("LOOP_STATUS").is_some_and(|v|!v.is_empty());let terminal=next.starts_with("final-summary:");if (!matches!(bgjob.as_str(),""|"0")&&!terminal)||!route{values.insert("NEXT_ACTION".into(),String::new());emit_kv("READ_RESULT_ENV_STATUS",if !bgjob.is_empty()&&bgjob!="0"{"invalid"}else{"missing"});for key in READ_RESULT_KEYS{emit_kv(key,values.get(key).map_or("",String::as_str));}return ExitCode::FAILURE;}if next.is_empty(){let action=step3_next_action(values.get("STEP3_REVIEW_LOOP_STATUS").map_or("",String::as_str),values.get("LOOP_STATUS").map_or("",String::as_str),"");values.insert("NEXT_ACTION".into(),action);}emit_kv("READ_RESULT_ENV_STATUS",status);for key in READ_RESULT_KEYS{emit_kv(key,values.get(key).map_or("",String::as_str));}ExitCode::SUCCESS}
    fn zero_coverage(root:&Path,rounds:u64)->bool{if rounds==0{return true;}let dir=root.join("plan-review/round-1");if !dir.is_dir(){return true;}fs::read_dir(dir).map_or(true,|entries|!entries.flatten().any(|entry|entry.path().is_file()&&!entry.path().is_symlink()))}
    fn synthesize_result(root:&Path,status:&str,reason:&str,rounds:u64)->Result<(),String>{let path=root.join(".step3-review-result.env");if path.is_symlink()||path.is_file(){remove(&path);}else if path.exists(){return Err(format!("refusing invalid result env: {}",path.display()));}let action=step3_next_action(status,status,"");let rows=[("NEXT_ACTION",action),("STEP3_REVIEW_LOOP_STATUS",status.into()),("LOOP_STATUS",status.into()),("REASON",reason.into()),("TALLY_PLAN_REVIEW_STATUS",status.into()),("STEP3_REVIEW_CAP_REACHED","false".into()),("STEP3_REVIEW_ROUND_NUM",String::new()),("ROUND_NUM",String::new()),("ROUNDS_COMPLETED",rounds.to_string()),("REVIEW_ROUND_COUNT",rounds.to_string())].into_iter().map(|(k,v)|(k.into(),v));write_rows(root,&path,rows)}
    fn persist_next_action(root:&Path,action:&str)->Result<(),String>{if action.is_empty(){return Ok(());}let path=root.join(".step3-review-result.env");if !path.is_file()||path.is_symlink(){return Ok(());}let current=read(&path);let preserved=current.lines().filter(|line|!line.starts_with("NEXT_ACTION=")).collect::<Vec<_>>();let body=format!("NEXT_ACTION={action}\n{}{}",preserved.join("\n"),if preserved.is_empty(){""}else{"\n"});write(root,&path,&body)}
    #[must_use] pub fn normalize_status(arguments:&[OsString])->ExitCode{
        let parsed=match parsed(arguments,"cli.py plan-review normalize-status",NORMALIZE_USAGE,NORMALIZE_HELP,&["--design-tmpdir","--stdout-file","--loop-rc"],&["--read-result-env"],&["--design-tmpdir"]){Ok(v)=>v,Err(c)=>return c};let root=match root(&text(&parsed,"--design-tmpdir"),"cli.py plan-review normalize-status"){Ok(v)=>v,Err(c)=>return c};if parsed.flag("--read-result-env"){return normalize_read_result(&root);}let stdout=PathBuf::from(text(&parsed,"--stdout-file"));let bg=root.join("bgjob/design-step3-review.result.env");let legacy=root.join(".step3-review-result.env");let primary_regular=bg.is_file()&&!bg.is_symlink();let selected=if primary_regular{Some(bg)}else if legacy.is_file()&&!legacy.is_symlink(){Some(legacy)}else{None};if selected.is_none(){eprintln!("**⚠ Step 3: could not read step3 review result env; recovering from plan-review stdout when possible**");}let mut values=selected.as_ref().map_or_else(BTreeMap::new,|p|env_rows(p));let stdout_regular=stdout.is_file()&&!stdout.is_symlink();let selected_has_values=!values.is_empty();if let Some(path)=if selected_has_values{selected.as_ref()}else if stdout_regular{Some(&stdout)}else{selected.as_ref()}{replay_warn_error(path);}if stdout_regular{let overlay=env_rows(&stdout);for key in STEP3_NORMALIZE_ALLOW_KEYS{if let Some(value)=overlay.get(key).filter(|v|!v.is_empty()){values.insert(key.into(),value.clone());}}if selected_has_values&&selected.as_ref()!=Some(&stdout){for line in read(&stdout).lines().filter(|line|line.starts_with("WARN=")){println!("{line}");}}}if text(&parsed,"--loop-rc")=="2"{eprintln!("**⚠ Step 3: plan-review run configuration error (exit 2); aborting plan review**");return ExitCode::FAILURE;}
        let mut status=values.get("STEP3_REVIEW_LOOP_STATUS").cloned().unwrap_or_default();let mut loop_status=values.get("LOOP_STATUS").cloned().unwrap_or_default();if matches!(status.as_str(),""){status=step3_status_from_loop_status(&loop_status);if !matches!(status.as_str(),""){values.insert("STEP3_REVIEW_LOOP_STATUS".into(),status.clone());}else if loop_status!="zero-findings-degraded-panel"{eprintln!("**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**");status="panel-failed".into();loop_status="panel-failed".into();values.insert("STEP3_REVIEW_LOOP_STATUS".into(),status.clone());values.insert("LOOP_STATUS".into(),loop_status.clone());}}
        let valid_status=["complete","cap-hit","main-agent-vote-required","main-agent-apply-required","per-round-approval-required","postplan-operator-required","postplan-failed","panel-failed","panel-init-failed","tally-error","degraded-empty-collector"];let valid_loop=["complete","cap-reached","zero-findings-degraded-panel","tally-error","degraded-empty-collector","panel-failed","panel-init-failed","main-agent-vote-required","main-agent-apply-required","per-round-approval-required","postplan-operator-required","postplan-failed"];if !matches!(status.as_str(),""){if !valid_status.contains(&status.as_str()){eprintln!("**⚠ Step 3: missing or invalid STEP3_REVIEW_LOOP_STATUS after plan-review run; treating plan review as panel-failed**");status="panel-failed".into();values.insert("STEP3_REVIEW_LOOP_STATUS".into(),status.clone());}loop_status=step3_loop_status_to_loop_status(&status,values.get("LOOP_STATUS").map_or("complete",String::as_str));values.insert("LOOP_STATUS".into(),loop_status.clone());}else if !valid_loop.contains(&loop_status.as_str()){eprintln!("**⚠ Step 3: missing or invalid LOOP_STATUS after plan-review run; treating plan review as panel-failed**");loop_status="panel-failed".into();values.insert("LOOP_STATUS".into(),loop_status.clone());}
        let mut rounds=values.get("ROUNDS_COMPLETED").or_else(||values.get("REVIEW_ROUND_COUNT")).filter(|v|digits(v)).and_then(|v|v.parse().ok()).unwrap_or(0);if values.get("STEP3_REVIEW_LOOP_STATUS").map(String::as_str)==Some("panel-failed")&&values.get("REASON").map(String::as_str)!=Some("orphan-timeout")&&zero_coverage(&root,rounds){eprintln!("**⚠ Step 3: panel failed before any reviewer round launched; treating as panel-init-failed**");for(k,v)in[("STEP3_REVIEW_LOOP_STATUS","panel-init-failed"),("LOOP_STATUS","panel-init-failed"),("TALLY_PLAN_REVIEW_STATUS","panel-init-failed"),("ROUNDS_COMPLETED","0"),("REVIEW_ROUND_COUNT","0"),("REASON","panel-failed-zero-coverage")]{values.insert(k.into(),v.into());}rounds=0;if let Err(error)=synthesize_result(&root,"panel-init-failed","panel-failed-zero-coverage",0){eprintln!("cli.py plan-review normalize-status: {error}");return ExitCode::FAILURE;}}
        let status=values.get("STEP3_REVIEW_LOOP_STATUS").cloned().unwrap_or_default();let result=root.join(".step3-review-result.env");if ["panel-failed","panel-init-failed","tally-error","degraded-empty-collector","postplan-failed"].contains(&status.as_str())&&(!result.is_file()||result.is_symlink()){eprintln!("**⚠ Step 3: {status} without a persisted result env; synthesizing terminal result env for Step 3 routing**");if let Err(error)=synthesize_result(&root,&status,values.get("REASON").map_or("result-env-missing-after-loop",String::as_str),rounds){eprintln!("cli.py plan-review normalize-status: {error}");return ExitCode::FAILURE;}}if ["complete","cap-hit","panel-failed","panel-init-failed","tally-error","degraded-empty-collector","postplan-failed"].contains(&status.as_str()){if let Err(error)=completed(&root,false){eprintln!("cli.py plan-review normalize-status: {error}");return ExitCode::FAILURE;}}let action=step3_next_action(&status,values.get("LOOP_STATUS").map_or("",String::as_str),values.get("TALLY_PLAN_REVIEW_STATUS").map_or("",String::as_str));values.insert("NEXT_ACTION".into(),action.clone());if let Err(error)=persist_next_action(&root,&action){eprintln!("cli.py plan-review normalize-status: {error}");return ExitCode::FAILURE;}for key in NORMALIZE_EMIT_KEYS{if let Some(value)=values.get(key).filter(|v|!v.is_empty()){emit_kv(key,value);}}if ["panel-failed","panel-init-failed","tally-error","degraded-empty-collector"].contains(&status.as_str())&&!record_evidence(&root,&status){eprintln!("**⚠ Step 3: failed to record escalation evidence for {status}**");}if status=="postplan-failed"{println!("SUMMARY_OUTCOME=failed-postplan");return ExitCode::FAILURE;}if status=="panel-init-failed"{println!("SUMMARY_OUTCOME=failed-judge-panel");return ExitCode::FAILURE;}ExitCode::SUCCESS
    }
    fn phase(root:&Path,round:u64)->String{read(&root.join(format!(".step3-round-{round}.phase"))).trim().into()}
    fn write_phase(root:&Path,round:u64,value:&str){let _=write(root,&root.join(format!(".step3-round-{round}.phase")),&format!("{value}\n"));}
    fn round_start(root:&Path,round:u64){let parent=root.join("plan-review");if parent.is_symlink(){return;}let dir=parent.join(format!("round-{round}"));if fs::create_dir_all(&dir).is_err(){return;}let path=dir.join("round-start-s");if path.exists()||path.is_symlink(){return;}let _=fs::OpenOptions::new().write(true).create_new(true).open(path).and_then(|mut file|writeln!(file,"{}",now_s()));}
    fn run_override(path:&Path,args:&[OsString],root:&Path)->(i32,String,String){let output=Command::new(path) // lint-subprocess-via-runner: ok retained deterministic plan-review harness override has no typed executable owner
            .args(args).env("DESIGN_TMPDIR",root).env("CLAUDE_PLUGIN_ROOT",plugin_root().unwrap_or_default()).env("PLUGIN_ROOT",plugin_root().unwrap_or_default()).output();match output{Ok(v)=>(v.status.code().unwrap_or(1),String::from_utf8_lossy(&v.stdout).into_owned(),String::from_utf8_lossy(&v.stderr).into_owned()),Err(error)=>(1,String::new(),error.to_string())}}
    fn run_round_body(root:&Path,round:u64)->(i32,BTreeMap<String,String>){progress_note(root,&format!("round {round} launched"));round_start(root,round);clean_round(root,round);let(rc,mut values)=if let Some(path)=env::var_os("RUN_STEP3_PLAN_REVIEW_LOOP_SH").map(PathBuf::from).filter(|p|!p.as_os_str().is_empty()){let args=[OsString::from("--design-tmpdir"),root.as_os_str().into(),"--round-num".into(),round.to_string().into(),"--prune-round-num".into(),round.to_string().into()];let(rc,out,err)=run_override(&path,&args,root);let all=format!("{out}{err}");print!("{all}");let parsed=kv_text(&all);let artifacts=PlanReviewRoundArtifacts::new(root,round);if artifacts.reviewer_status_tsv().is_file()&&!artifacts.reviewer_status_tsv().is_symlink(){materialize_existing_status(root,round,true);}else{remove(&artifacts.reviewer_status_tsv());let terminal=parsed.get("LOOP_STATUS").map(String::as_str)==Some("zero-findings-degraded-panel")||parsed.get("LOOP_STATUS").map(String::as_str)==Some("panel-failed")&&matches!(parsed.get("AGGREGATOR_STATUS").map(String::as_str),Some("skipped"|"skipped-pruned-empty"));if terminal{let _=write(root,&root.join("collector-results.env"),"");materialize_status(root,round,Some(""),true);}else{materialize_status(root,round,None,true);}}(rc,parsed)}else{round_once(root,round)};if !values.contains_key("REASON"){if let Some(reason)=env_rows(&root.join(".step3-review-result.env")).get("REASON"){values.insert("REASON".into(),reason.clone());}}let mut status=values.get("LOOP_STATUS").cloned().unwrap_or_else(||if rc==0{"complete".into()}else{"panel-failed".into()});if rc!=0&&!["tally-error","degraded-empty-collector","panel-failed"].contains(&status.as_str()){status=if values.get("TALLY_PLAN_REVIEW_STATUS").map(String::as_str)==Some("tally-error"){"tally-error".into()}else{"panel-failed".into()};}if values.contains_key("STEP3_REVIEW_LOOP_STATUS"){status=values.get("LOOP_STATUS").cloned().unwrap_or(status);}if matches!(status.as_str(),"complete"|"zero-findings-degraded-panel"){let accepted=parse_plan_review_accepted_findings(&read(&root.join("accepted-plan-findings.md"))).len().max(values.get("ACCEPTED_COUNT").and_then(|v|v.parse().ok()).unwrap_or(0));progress_note(root,&format!("round {round} complete with {accepted} accepted"));}values.insert("LOOP_STATUS".into(),status);materialize_existing_status(root,round,false);(rc,values)}
    fn snapshot(root:&Path,round:u64)->PathBuf{let path=root.join(format!("plan-pre-apply-round-{round}.txt"));if !path.exists(){let _=fs::copy(root.join("plan.txt"),&path);}path}
    fn dedup(root:&Path,round:u64,values:&mut BTreeMap<String,String>)->i32{let before=snapshot(root,round);let args1=[OsString::from("--design-tmpdir"),root.as_os_str().into(),"--snapshot-trailers".into()];let args2=[OsString::from("--design-tmpdir"),root.as_os_str().into(),"--dedup".into()];let invoke=|args:&[OsString]|->i32{if let Some(path)=env::var_os("RUN_STEP3_DEDUP_PLAN_SH").map(PathBuf::from).filter(|p|!p.as_os_str().is_empty()){run_override(&path,args,root).0}else{child_owned(std::iter::once(OsString::from("plan-review")).chain(std::iter::once(OsString::from("gate-b-dedup"))).chain(args.iter().cloned()).collect()).map_or(1,|out|code(&out))}};progress_note(root,&format!("round {round}: plan-review dedup running"));let mut rc=invoke(&args1);if rc==0{rc=invoke(&args2);}if rc!=0{values.insert("DEDUP_RC".into(),rc.to_string());if before.is_file(){let _=fs::copy(before,root.join("plan.txt"));}write_phase(root,round,"awaiting-apply");return 22;}if let Ok(out)=child_owned(vec!["design".into(),"dialectic-clear-stale".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--reason".into(),"plan-rewrite".into()]){if !out.status().success(){eprintln!("**⚠ plan-review: dialectic-clear-stale failed after dedup; stale clarifier artifacts may linger (Gate C fingerprint binding still gates debate).**");}}let _=touch(&root.join(format!(".gate-b-postapply-ready-{round}")));remove(&root.join(format!(".gate-b-per-round-approval-round-{round}.env")));0}
    fn gate_b_start(root:&Path,round_start:u64,end:u64,output:&str)->Option<u64>{let mut latest=None;for line in read(&root.join("timing-ledger.tsv")).lines(){let cols=line.split('\t').collect::<Vec<_>>();if cols.len()<13||cols[0]!="v1"||cols[1]!="vendor"{continue;}if cols[6]=="gate-b-apply"&&Path::new(cols[10]).file_name().and_then(|v|v.to_str())==Some(output){return None;}if cols[6]=="gate-b-apply"{continue;}let Ok(start)=cols[7].parse::<u64>()else{continue;};let Ok(row_end)=cols[8].parse::<u64>()else{continue;};if row_end<=round_start||start>=end{continue;}latest=Some(latest.map_or(row_end,|value:u64|value.max(row_end)));}latest.filter(|value|*value<end)}
    fn write_round_meta(root:&Path,round:u64){let _=child_owned(vec!["progress".into(),"write-design-round-meta".into(),"--round-dir".into(),root.join(format!("plan-review/round-{round}")).into_os_string()]);let start=read(&root.join(format!("plan-review/round-{round}/round-start-s"))).trim().parse::<u64>().ok();if let Some(start)=start.filter(|v|*v>0){let end=now_s();let ledger=root.join("timing-ledger.tsv");let timing_env=[(ChildEnvironment::LarchTimingSkill,OsString::from("design")),(ChildEnvironment::LarchTimingLedger,ledger.clone().into_os_string()),(ChildEnvironment::DesignTmpdir,root.as_os_str().into())];if root.join(format!(".gate-b-postapply-ready-{round}")).is_file(){let output=format!("gate-b-apply-round-{round}.out");if let Some(gate_start)=gate_b_start(root,start,end,&output){let args=vec!["timing".into(),"record-vendor-task".into(),"--ledger".into(),ledger.clone().into_os_string(),"--vendor".into(),"claude".into(),"--task-kind".into(),"gate-b-apply".into(),"--start-s".into(),gate_start.to_string().into(),"--end-s".into(),end.to_string().into(),"--output".into(),output.into(),"--exit-code".into(),"0".into(),"--status".into(),"complete".into()];let _=run_verified_larch_with_environment(&args,&timing_env);}}let args=vec!["timing".into(),"record-round".into(),"--ledger".into(),ledger.into_os_string(),"--skill".into(),"design".into(),"--step".into(),"design Step 3 — plan review".into(),"--round".into(),round.to_string().into(),"--start-s".into(),start.to_string().into(),"--end-s".into(),end.to_string().into(),"--accepted".into(),"0".into(),"--rejected".into(),"0".into(),"--if-round-exists".into()];let _=run_verified_larch_with_environment(&args,&timing_env);}}
    fn clear_scout(root:&Path){if let Ok(entries)=fs::read_dir(root){for entry in entries.flatten(){let name=entry.file_name().to_string_lossy().into_owned();if name=="scout-plan-manifest.json"||name.starts_with("scout-plan-manifest.json.candidate.")||name.starts_with("scout-plan-manifest.json.filtered."){remove(&entry.path());}}}}
    fn revise(root:&Path,round:u64,values:&mut BTreeMap<String,String>)->i32{let before=snapshot(root,round);let current=phase(root,round);let ready=root.join(format!(".gate-b-postapply-ready-{round}")).is_file();if before.is_file()&&root.join("plan.txt").is_file()&&fs::read(&before).ok()!=fs::read(root.join("plan.txt")).ok(){if current=="awaiting-post-apply"||ready{return dedup(root,round,values);}if current=="awaiting-revise"{let _=fs::copy(&before,root.join("plan.txt"));}}write_phase(root,round,"awaiting-revise");clear_scout(root);let args=vec!["--design-tmpdir".into(),root.as_os_str().into(),"--plan-file".into(),root.join("plan.txt").into_os_string(),"--findings-file".into(),root.join("accepted-plan-findings.md").into_os_string(),"--feature-file".into(),root.join("feature-description.txt").into_os_string(),"--round-num".into(),round.to_string().into(),"--codex-binary-found".into(),env::var_os("CODEX_BINARY_FOUND").unwrap_or_default(),"--cursor-binary-found".into(),env::var_os("CURSOR_BINARY_FOUND").unwrap_or_default(),"--patch-format".into(),"file-replacement".into()];let(rc,stdout)=if let Some(path)=env::var_os("RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH").map(PathBuf::from).filter(|p|!p.as_os_str().is_empty()){let(rc,out,_)=run_override(&path,&args,root);(rc,out)}else{match run_verified_larch_with_timeout(&std::iter::once(OsString::from("plan")).chain(std::iter::once(OsString::from("revise-waterfall"))).chain(args).collect::<Vec<_>>(),Duration::from_secs(900)){Ok(out)=>(code(&out),String::from_utf8_lossy(out.stdout()).into_owned()),Err(_)=>(1,String::new())}};let status=kv_text(&stdout).get("REVISE_STATUS").cloned().unwrap_or_default();if rc!=0||!matches!(status.as_str(),"ok"|"ok-fallback"){write_phase(root,round,"awaiting-apply");return 21;}write_round_meta(root,round);write_phase(root,round,"awaiting-post-apply");dedup(root,round,values)}
    fn pause_env(root:&Path)->i32{if let Some(path)=env::var_os("RUN_STEP3_DESIGN_PAUSE_SAVE_SH").map(PathBuf::from).filter(|p|!p.as_os_str().is_empty()){let mut args=vec!["--design-tmpdir".into(),root.as_os_str().into()];if let Some(issue)=env::var_os("ISSUE_NUMBER").filter(|v|!v.is_empty()){args.extend(["--issue".into(),issue]);}return run_override(&path,&args,root).0;}let mut args=vec!["design".into(),"pause-save".into(),"--design-tmpdir".into(),root.as_os_str().into()];if let Some(issue)=env::var_os("ISSUE_NUMBER").filter(|v|!v.is_empty()){args.extend(["--issue".into(),issue]);}run_verified_larch(&args).map_or(1,|out|code(&out))}
    fn post_apply(root:&Path,round:u64,values:&mut BTreeMap<String,String>)->i32{let args=[OsString::from("--design-tmpdir"),root.as_os_str().into(),"--with-plan-size".into()];progress_note(root,&format!("round {round}: plan-review post-apply running"));let rc=if let Some(path)=env::var_os("RUN_STEP3_POSTPLAN_EMIT_SH").map(PathBuf::from).filter(|p|!p.as_os_str().is_empty()){run_override(&path,&args,root).0}else{run_python_verb(std::iter::once("design").chain(std::iter::once("postplan-emit")).map(OsString::from).chain(args),Duration::from_secs(900)).map_or(1,|out|code(&out))};if rc==0{progress_note(root,&format!("round {round}: plan-review awaiting continuation"));write_phase(root,round,"awaiting-continuation");return 0;}if rc==11{return pause_env(root);}if rc==12{emit_kv("WARN",&format!("plan-size trigger (postplan rc=12) in continuation (round {round}): proceeding as warning-only"));write_phase(root,round,"awaiting-continuation");return 0;}values.insert("POSTPLAN_RC".into(),rc.to_string());if matches!(rc,10|13){32}else{33}}
    fn continuation_child(root:&Path,approve:bool)->BTreeMap<String,String>{if let Some(path)=env::var_os("RUN_STEP3_CONTINUATION_SH").map(PathBuf::from).filter(|p|!p.as_os_str().is_empty()){let args=[OsString::from("--design-tmpdir"),root.as_os_str().into(),"--approve-requested".into(),if approve{"true".into()}else{"false".into()}];let(rc,out,_)=run_override(&path,&args,root);if rc!=0{return BTreeMap::from([("PLAN_REVIEW_CONTINUE".into(),"false".into()),("PLAN_REVIEW_CONTINUE_REASON".into(),"continuation-failed".into())]);}let values=kv_text(&out);if values.contains_key("PLAN_REVIEW_CONTINUE"){return values;}return BTreeMap::from([("PLAN_REVIEW_CONTINUE".into(),"false".into()),("PLAN_REVIEW_CONTINUE_REASON".into(),"continuation-malformed".into())]);}match child_owned(vec!["plan-review".into(),"continuation".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--approve-requested".into(),if approve{"true".into()}else{"false".into()}]){Ok(out)if out.status().success()=>{let values=kv_text(&String::from_utf8_lossy(out.stdout()));if values.contains_key("PLAN_REVIEW_CONTINUE"){values}else{BTreeMap::from([("PLAN_REVIEW_CONTINUE".into(),"false".into()),("PLAN_REVIEW_CONTINUE_REASON".into(),"continuation-malformed".into())])}},_=>BTreeMap::from([("PLAN_REVIEW_CONTINUE".into(),"false".into()),("PLAN_REVIEW_CONTINUE_REASON".into(),"continuation-failed".into())])}}
    fn carry(degraded:bool,values:&BTreeMap<String,String>)->BTreeMap<String,String>{if degraded{return values.clone();}let mut out=BTreeMap::new();for key in ["DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING"]{if let Some(v)=values.get(key).filter(|v|!v.is_empty()){out.insert(key.into(),v.clone());}}out}
    fn orphan_elapsed(root:&Path,timeout:Option<f64>)->bool{let Some(timeout)=timeout else{return false};if root.join(".step3-reattach-active").is_file(){return false;}let marker=root.join(".step3-wrapper-detached");if !marker.is_file()||marker.is_symlink(){return false;}if let Some(epoch)=env_rows(&marker).get("DETACHED_AT_EPOCH").and_then(|v|v.parse::<f64>().ok()).filter(|v|*v>0.0){return now_s() as f64-epoch>=timeout;}marker.metadata().and_then(|m|m.modified()).ok().and_then(|m|SystemTime::now().duration_since(m).ok()).is_some_and(|age|age.as_secs_f64()>=timeout)}
    #[must_use] pub fn run(arguments:&[OsString])->ExitCode{
        if let Some(index)=arguments.iter().position(|argument|argument=="--record-report-evidence"){
            let Some(status)=arguments.get(index+1).and_then(|value|value.to_str())else{eprintln!("plan-review run: --record-report-evidence requires a value");return ExitCode::from(2)};
            let design=arguments.iter().position(|argument|argument=="--design-tmpdir").and_then(|position|arguments.get(position+1)).and_then(|value|value.to_str());
            let Some(design)=design else{eprintln!("plan-review run: --design-tmpdir is required with --record-report-evidence");return ExitCode::from(2)};
            let root=match root(design,"plan-review run"){Ok(value)=>value,Err(_)=>return ExitCode::from(2)};
            if !record_evidence(&root,status){emit_kv("WARN",&format!("Step 3: failed to record design escalation evidence for {status}"));return ExitCode::FAILURE;}
            return ExitCode::SUCCESS;
        }
        let usage="usage: cli.py plan-review run [-h] --design-tmpdir DESIGN_TMPDIR [--mode MODE]\n                              [--starting-round STARTING_ROUND]\n                              [--read-result-env] [--no-preview]\n                              [--new-process-group]\n                              [--orphan-timeout-s ORPHAN_TIMEOUT_S]";
        let parsed=parse_with_flags(arguments,&["--design-tmpdir","--mode","--starting-round","--orphan-timeout-s"],&["-h","--help","--read-result-env","--no-preview","--new-process-group"],0);
        if parsed.flag("-h")||parsed.flag("--help"){println!("{usage}\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --mode MODE\n  --starting-round STARTING_ROUND\n  --read-result-env\n  --no-preview\n  --new-process-group\n  --orphan-timeout-s ORPHAN_TIMEOUT_S");return ExitCode::SUCCESS;}
        let Some(raw)=parsed.value("--design-tmpdir").map(|value|value.to_string_lossy().into_owned())else{return usage_error(usage,"cli.py plan-review run","the following arguments are required: --design-tmpdir",2)};
        let start=text(&parsed,"--starting-round");
        if !start.is_empty()&&!positive(&start){return usage_error(usage,"cli.py plan-review run","argument --starting-round: requires a non-empty positive integer",2);}
        let timeout_raw=text(&parsed,"--orphan-timeout-s");
        let timeout=if timeout_raw.is_empty(){None}else{match timeout_raw.parse::<f64>().ok().filter(|value|*value>0.0){Some(value)=>Some(value),None=>{eprintln!("cli.py plan-review run: --orphan-timeout-s must be positive");return ExitCode::from(2)}}};
        let root=match root(&raw,"cli.py plan-review run"){Ok(value)=>value,Err(code)=>return code};
        if parsed.flag("--read-result-env"){
            let result=root.join(".step3-review-result.env");
            if !result.is_file()||result.is_symlink(){eprintln!("cli.py plan-review run: result env is not a regular file: {}",result.display());return ExitCode::FAILURE;}
            let allowed=["NEXT_ACTION","STEP3_REVIEW_LOOP_STATUS","LOOP_STATUS","TALLY_PLAN_REVIEW_STATUS","ROUNDS_COMPLETED","FINAL_ROUND_NUM","ACCEPTED_COUNT","DEGRADED_PANEL","DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING","REASON"];
            let values=match strict_result_rows(&result,&allowed){Ok(values)=>values,Err(error)=>{eprintln!("cli.py plan-review run: {error}");return ExitCode::FAILURE;}};
            for(key,value)in values{emit_kv(&key,&value);}
            return ExitCode::SUCCESS;
        }
        if parsed.flag("--new-process-group")&&setsid().is_err(){eprintln!("cli.py plan-review run: --new-process-group failed");return ExitCode::from(2);}
        let approve=json_bool_value(&root.join("run-params.json"),"approve_requested",false);
        let mut round=start.parse::<u64>().ok().unwrap_or_else(||read_count(&root)+1);
        let mut degraded=false;
        let mut degraded_values:BTreeMap<String,String>=BTreeMap::new();

        loop{
            if orphan_elapsed(&root,timeout){let values=BTreeMap::from([("REASON".into(),"orphan-timeout".into()),("LOOP_STATUS".into(),"panel-failed".into()),("TALLY_PLAN_REVIEW_STATUS".into(),"panel-failed".into())]);return complete_and_emit(&root,false,"panel-failed",round,round.saturating_sub(1),round,&values);}
            let current=phase(&root,round);
            if current.is_empty(){
                let count=read_count(&root);
                if count>=2{
                    let values=BTreeMap::from([("TALLY_PLAN_REVIEW_STATUS".into(),"skipped-cap-reached".into()),("LOOP_STATUS".into(),"cap-reached".into())]);
                    if let Err(error)=write_rows(&root,&root.join(".step3-review-cap.env"),[("LOOP_STATUS".into(),"cap-reached".into()),("TALLY_PLAN_REVIEW_STATUS".into(),"skipped-cap-reached".into())]){eprintln!("plan-review run: {error}");return ExitCode::FAILURE;}
                    remove(&root.join("accepted-plan-findings.md"));
                    remove(&root.join("voting-tally.md"));
                    if let Err(error)=completed(&root,true){eprintln!("plan-review run: {error}");return ExitCode::FAILURE;}
                    emit_kv("NEXT_ACTION","step3b-bypass");emit_kv("LOOP_STATUS","cap-reached");emit_kv("TALLY_PLAN_REVIEW_STATUS","skipped-cap-reached");emit_kv("INFO",&format!("cap reached; skipping review round {}",count+1));
                    return match persist_envelope(&root,"cap-hit",count+1,count,count+1,&values){Ok(())=>ExitCode::SUCCESS,Err(error)=>{eprintln!("plan-review run: {error}");ExitCode::FAILURE}};
                }
                write_count(&root,round);
                let(_,mut values)=run_round_body(&root,round);
                let status=values.get("LOOP_STATUS").cloned().unwrap_or_default();
                if status=="cap-reached"{return complete_and_emit(&root,true,"cap-hit",round,round.saturating_sub(1),round,&values);}
                if ["tally-error","degraded-empty-collector","panel-failed"].contains(&status.as_str()){
                    if matches!(status.as_str(),"tally-error"|"degraded-empty-collector"){write_count(&root,round.saturating_sub(1));}else{write_count(&root,round.max(read_count(&root)));}
                    return complete_and_emit(&root,false,&status,round,round,round,&values);
                }
                if status=="main-agent-vote-required"{write_phase(&root,round,"awaiting-apply");return emit_envelope_exit(&root,"main-agent-vote-required",round,round,round,&values);}
                if matches!(status.as_str(),"complete"|"zero-findings-degraded-panel"){
                    for key in ["DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING"]{if !values.contains_key(key){if let Some(value)=degraded_values.get(key){values.insert(key.into(),value.clone());}}}
                    let accepted=parse_plan_review_accepted_findings(&read(&root.join("accepted-plan-findings.md"))).len().max(values.get("ACCEPTED_COUNT").and_then(|value|value.parse().ok()).unwrap_or(0));
                    values.insert("ACCEPTED_COUNT".into(),accepted.to_string());
                    for key in ["DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING"]{if let Some(value)=values.get(key).filter(|value|!value.is_empty()){degraded_values.insert(key.into(),value.clone());}}
                    if status=="zero-findings-degraded-panel"{
                        let rows=vec![("NEXT_ACTION".into(),"step3b".into()),("LOOP_STATUS".into(),status.clone()),("ROUNDS_COMPLETED".into(),round.to_string()),("REVIEW_ROUND_COUNT".into(),round.to_string()),("PANEL_PRUNED_EMPTY".into(),values.get("PANEL_PRUNED_EMPTY").cloned().unwrap_or_else(||"true".into())),("TALLY_PLAN_REVIEW_STATUS".into(),values.get("TALLY_PLAN_REVIEW_STATUS").cloned().unwrap_or_else(||"ok".into())),("ACCEPTED_COUNT".into(),accepted.to_string()),("DEGRADED_PANEL".into(),values.get("DEGRADED_PANEL").cloned().unwrap_or_else(||"0".into())),("DEGRADED_PANEL_WARNING".into(),values.get("DEGRADED_PANEL_WARNING").cloned().unwrap_or_default()),("INVALID_SLOT_PANEL_WARNING".into(),values.get("INVALID_SLOT_PANEL_WARNING").cloned().unwrap_or_default()),("REASON".into(),values.get("REASON").cloned().unwrap_or_default())];
                        if let Err(error)=write_rows(&root,&root.join(".step3-review-result.env"),rows){eprintln!("plan-review run: {error}");return ExitCode::FAILURE;}
                        degraded=true;degraded_values=values.clone();
                    }
                    if accepted==0{write_round_meta(&root,round);write_phase(&root,round,"awaiting-continuation");continue;}
                    if approve{write_phase(&root,round,"awaiting-apply");return emit_envelope_exit(&root,"per-round-approval-required",round,round,round,&values);}
                    write_phase(&root,round,"awaiting-revise");continue;
                }
                emit_kv("WARN",&format!("missing or invalid LOOP_STATUS={status:?}; treating as panel-failed"));
                return complete_and_emit(&root,false,"panel-failed",round,round,round,&values);
            }
            if current=="awaiting-revise"{
                let mut values=degraded_values.clone();
                if revise(&root,round,&mut values)!=0{let status=if approve&&!root.join(format!(".gate-b-per-round-approval-round-{round}.env")).is_file(){"per-round-approval-required"}else{"main-agent-apply-required"};return emit_envelope_exit(&root,status,round,round,round,&values);}
                continue;
            }
            if current=="awaiting-apply"{
                let values=degraded_values.clone();
                if root.join(format!(".gate-b-postapply-ready-{round}")).is_file(){write_phase(&root,round,"awaiting-post-apply");continue;}
                let status=if approve&&!root.join(format!(".gate-b-per-round-approval-round-{round}.env")).is_file(){"per-round-approval-required"}else{"main-agent-apply-required"};
                return emit_envelope_exit(&root,status,round,round,round,&values);
            }
            if matches!(current.as_str(),"awaiting-post-apply"|"awaiting-postplan-operator"){
                if current=="awaiting-postplan-operator"{
                    let sentinel=root.join(format!(".postplan-operator-continue-{round}"));
                    if sentinel.is_file(){remove(&sentinel);write_phase(&root,round,"awaiting-continuation");continue;}
                    let values=carry(degraded,&degraded_values);
                    return emit_envelope_exit(&root,"postplan-operator-required",round,round,round,&values);
                }
                let mut values=carry(degraded,&degraded_values);
                if !root.join(format!(".gate-b-postapply-ready-{round}")).is_file()&&dedup(&root,round,&mut values)!=0{return emit_envelope_exit(&root,"main-agent-apply-required",round,round,round,&values);}
                let rc=post_apply(&root,round,&mut values);
                if rc==0{continue;}
                if rc==32{write_phase(&root,round,"awaiting-postplan-operator");return emit_envelope_exit(&root,"postplan-operator-required",round,round,round,&values);}
                return emit_envelope_exit(&root,"postplan-failed",round,round,round,&values);
            }
            if current=="awaiting-continuation"{
                if root.join(format!(".gate-b-postapply-ready-{round}")).is_file(){write_round_meta(&root,round);}
                write_count(&root,round);
                let cont=continuation_child(&root,approve);
                if cont.get("PLAN_REVIEW_CONTINUE").map(String::as_str)==Some("true"){
                    remove(&root.join(".step3-review-result.env"));
                    let _=child_owned(vec!["plan-review".into(),"step3-state".into(),"--design-tmpdir".into(),root.as_os_str().into(),"--auto-continuation-entry".into()]);
                    remove(&root.join(".step3-entry-plan-printed"));
                    round+=1;degraded=false;degraded_values=carry(false,&degraded_values);continue;
                }
                if degraded{
                    if let Err(error)=completed(&root,true){eprintln!("plan-review run: {error}");return ExitCode::FAILURE;}
                    emit_kv("NEXT_ACTION","step3b");emit_kv("LOOP_STATUS","zero-findings-degraded-panel");emit_kv("ROUNDS_COMPLETED",&round.to_string());emit_kv("REVIEW_ROUND_COUNT",&round.to_string());
                    for key in ["PANEL_PRUNED_EMPTY","TALLY_PLAN_REVIEW_STATUS","ACCEPTED_COUNT","DEGRADED_PANEL","DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING","REASON"]{if let Some(value)=degraded_values.get(key).filter(|value|!value.is_empty()){emit_kv(key,value);}}
                    return ExitCode::SUCCESS;
                }
                let mut values=degraded_values.clone();
                for key in ["PLAN_REVIEW_CONTINUE_REASON","ACCEPTED_COUNT","DEGRADED_PANEL","DEGRADED_PANEL_WARNING","INVALID_SLOT_PANEL_WARNING"]{if let Some(value)=cont.get(key){values.insert(key.into(),value.clone());}}
                if let Err(error)=write(&root,&root.join(".step3-review-cap.env"),&format!("STEP3_REVIEW_CAP_REACHED=false\nSTEP3_REVIEW_ROUND_NUM={round}\n")){eprintln!("plan-review run: {error}");return ExitCode::FAILURE;}
                return complete_and_emit(&root,true,"complete",round,round,round,&values);
            }
            let values=BTreeMap::from([("REASON".into(),format!("invalid-phase:{}",if current.is_empty(){"missing"}else{&current}))]);
            let _=emit_envelope_exit(&root,"postplan-failed",round,round,round,&values);
            return ExitCode::from(2);
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        use tempfile::TempDir;

        #[test]
        fn dispatcher_drops_become_per_slot_failure_logs() {
            let sandbox=TempDir::new().expect("sandbox");
            let root=sandbox.path();
            let dropped=root.join("dropped.tsv");
            fs::write(&dropped,"codex plan/arch\tcodex\tcollector-failure\tworker exited 9\nignored\tcursor\tno-capacity\tnone\n").expect("dropped rows");
            log_dropped_slots(root,dropped.to_str().expect("path")).expect("log dropped slot");
            assert_eq!(read(&root.join("codex_plan_arch-dispatch-drop.failure.log")),"reviewer slot codex plan/arch (codex) dropped by waterfall dispatcher before collection: collector-failure\nworker exited 9\n");
            assert!(!root.join("ignored-dispatch-drop.failure.log").exists());
        }

        #[test]
        fn reviewer_collect_fills_the_timing_ledger_gap() {
            let sandbox=TempDir::new().expect("sandbox");
            let root=sandbox.path();
            let ledger=root.join("timing-ledger.tsv");
            fs::write(&ledger,"v1\tvendor\t3\tdesign\t-\tcodex\tcodex-plan-requirements\t1\t2\t1\tprior.out\t0\tcomplete\n").expect("ledger");
            record_reviewer_collect(root,7,1.0);
            let body=read(&ledger);
            assert!(body.lines().any(|line|{let fields=line.split('\t').collect::<Vec<_>>();fields.len()>=13&&fields[1]=="vendor"&&fields[3]=="design"&&fields[5]=="claude"&&fields[6]=="reviewer-collect"&&fields[10]=="reviewer-collect-round-7.out"&&fields[12]=="complete"}),"{body}");
        }
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
#[allow(clippy::redundant_pub_crate)]
pub(crate) use loop_implementation::proposer_map;
