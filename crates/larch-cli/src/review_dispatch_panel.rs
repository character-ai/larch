//! Rust owner for `review dispatch-panel`, preserving its legacy envelope through the sole waterfall owner.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use crate::{
    agent_commands::generated_paths,
    argparse_compat::{ParsedCommandLine, parse, usage_error},
    launcher_support::{
        write_confined, write_confined_required as write_required,
        write_json_lines_confined as write_manifest,
    },
    python_verb::{plugin_root_directory, run_python_verb},
    rendering_commands::specialist_result,
    runtime_entrypoint::{run_verified_larch, run_verified_larch_with_timeout},
    scout_commands::filter_manifest_paths,
    waterfall_commands::{append_review_routing_arguments, dispatch_for_review, parse_dispatch_kv},
};
use larch_adapters::ensure_directory_chain;
use larch_core::{
    classify_diff, emit_kv,
    review::{
        ledger_path, ledger_root, normalize_output_base, parse_collector_records,
        with_manifest_attribution,
    },
};
use serde_json::{Map, Value, json};

const USAGE: &str = "Usage: review dispatch-panel --mode diff|description --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--tier TRIVIAL|MODERATE|HARD] [--panel simple|hard] [--dynamic-archetypes 0-1] [--pre-scouted-manifest FILE] [--prune-ledger FILE] [--site SITE] [context flags]";
const PROGRAM: &str = "review dispatch-panel";
const STATIC_ARCHETYPES: [&str; 3] = ["correctness", "edge-cases", "testing"];
const DYNAMIC_AGENT_TEMPLATE: &str = include_str!("review_dispatch_panel_prompt.md");
const OPTIONS: &str = include_str!("review_dispatch_panel_options.txt");

pub fn run(arguments: &[OsString]) -> ExitCode {
    if arguments.iter().any(|argument| argument == "--help") {
        eprintln!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let option_names = OPTIONS.split_ascii_whitespace().collect::<Vec<_>>();
    let parsed = parse(arguments, &option_names, 0);
    if let Some(error) = parsed.error() {
        return usage_error(USAGE, PROGRAM, &error, 2);
    }
    let options = match PanelOptions::new(&parsed) {
        Ok(options) => options,
        Err(error) => {
            eprintln!("{PROGRAM}: {error}");
            return ExitCode::from(2);
        }
    };
    match dispatch(&options) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{PROGRAM}: {error}");
            ExitCode::from(1)
        }
    }
}

struct PanelOptions {
    mode: String,
    review_tmpdir: PathBuf,
    codex_available: bool,
    cursor_available: bool,
    tier: String,
    escalated_round: String,
    skip_prune: String,
    audit_upgrade: String,
    dynamic_max: usize,
    round_num: usize,
    plan_file: String,
    site: String,
    session_env_path: String,
    diff_file: String,
    commit_count: String,
    scope_files: String,
    description_text: String,
    feature_file: String,
    pre_scouted_manifest: String,
    prune_ledger: String,
    competition_notice_file: String,
}

impl PanelOptions {
    fn new(parsed: &ParsedCommandLine) -> Result<Self, String> {
        let value = |name: &str| {
            parsed
                .value(name)
                .map(|value| value.to_string_lossy().into_owned())
                .unwrap_or_default()
        };
        let mode = value("--mode");
        let review_tmpdir = PathBuf::from(value("--review-tmpdir"));
        let codex_raw = value("--codex-available");
        let cursor_raw = value("--cursor-available");
        if !matches!(mode.as_str(), "diff" | "description") {
            return Err("--mode must be diff or description".to_owned());
        }
        if review_tmpdir.as_os_str().is_empty() {
            return Err("--review-tmpdir is required".to_owned());
        }
        if !matches!(codex_raw.as_str(), "true" | "false")
            || !matches!(cursor_raw.as_str(), "true" | "false")
        {
            return Err("availability flags must be true or false".to_owned());
        }
        let raw_tier = value("--tier");
        let tier = normalize_tier(&raw_tier);
        if !raw_tier.is_empty() && tier.is_empty() {
            return Err("--tier must be TRIVIAL, MODERATE, or HARD".to_owned());
        }
        let mut panel = value("--panel");
        let tier = if tier.is_empty() {
            if panel.is_empty() {
                "hard".clone_into(&mut panel);
            }
            if panel == "simple" {
                "TRIVIAL".to_owned()
            } else {
                "MODERATE".to_owned()
            }
        } else {
            panel_for_tier(&tier).clone_into(&mut panel);
            tier
        };
        if !matches!(panel.as_str(), "simple" | "hard") {
            return Err("--panel must be simple or hard".to_owned());
        }
        let escalated_round = default_value(value("--escalated-round"), "false");
        let skip_prune = default_value(value("--skip-prune"), "false");
        if !matches!(escalated_round.as_str(), "true" | "false")
            || !matches!(skip_prune.as_str(), "true" | "false")
        {
            return Err("--escalated-round/--skip-prune must be true or false".to_owned());
        }
        let dynamic_raw = default_value(
            value("--dynamic-archetypes"),
            &default_value(
                env::var("LARCH_DYNAMIC_ARCHETYPES_MAX").unwrap_or_default(),
                "0",
            ),
        );
        if !matches!(dynamic_raw.as_str(), "0" | "1") {
            return Err(
                "--dynamic-archetypes/LARCH_DYNAMIC_ARCHETYPES_MAX must be an integer from 0 to 1"
                    .to_owned(),
            );
        }
        let round_raw = default_value(value("--round-num"), "1");
        let round_num = round_raw
            .parse::<usize>()
            .ok()
            .filter(|value| *value > 0)
            .ok_or_else(|| "--round-num must be a positive integer".to_owned())?;
        let plan_file = value("--plan-file");
        if plan_file.is_empty() || !Path::new(&plan_file).is_file() {
            return Err("--plan-file is required".to_owned());
        }
        Ok(Self {
            mode,
            review_tmpdir,
            codex_available: codex_raw == "true",
            cursor_available: cursor_raw == "true",
            tier,
            escalated_round,
            skip_prune,
            audit_upgrade: value("--audit-upgrade"),
            dynamic_max: dynamic_raw.parse().unwrap_or_default(),
            round_num,
            plan_file,
            site: default_value(value("--site"), "review Step 2"),
            session_env_path: default_value(
                value("--session-env-path"),
                &env::var("SESSION_ENV_PATH").unwrap_or_default(),
            ),
            diff_file: value("--diff-file"),
            commit_count: default_value(value("--commit-count"), "0"),
            scope_files: value("--scope-files"),
            description_text: value("--description-text"),
            feature_file: value("--feature-file"),
            pre_scouted_manifest: value("--pre-scouted-manifest"),
            prune_ledger: value("--prune-ledger"),
            competition_notice_file: value("--competition-notice-file"),
        })
    }
}

fn default_value(value: String, fallback: &str) -> String {
    if value.is_empty() {
        fallback.to_owned()
    } else {
        value
    }
}

#[derive(Clone, Debug, serde::Deserialize)]
struct DynamicArchetype {
    name: String,
    focus_area: String,
    weight: i64,
    rationale: String,
    prompt_body: String,
}

#[derive(Clone, Debug, Default)]
struct ScoutResult {
    status: String,
    fail_reason: String,
    manifest: Option<PathBuf>,
}

#[derive(Clone, Debug, Default)]
struct PruneResult {
    active: String,
    status: String,
    panel_full: usize,
    eligible: usize,
    pruned_count: usize,
    pruned_combos: String,
    panel_pruned_empty: String,
}

fn dispatch(options: &PanelOptions) -> Result<(), String> {
    ensure_directory_chain(&options.review_tmpdir).map_err(|error| error.to_string())?;
    let manifest_path = options.review_tmpdir.join("panel-manifest.ndjson");
    let plugin_root =
        plugin_root_directory().ok_or_else(|| "cannot resolve the plugin root".to_owned())?;
    let mut rows = static_rows(options, &plugin_root);
    write_manifest(&manifest_path, &rows)?;

    let scout = prepare_dynamic_slots(options, &mut rows)?;
    write_manifest(&manifest_path, &rows)?;
    append_producer_scout_warning_once(options, &scout);

    let (static_slot_count, _, _, dynamic_slots) = slot_counts(&rows);
    let panel_full = static_slot_count + dynamic_slots;
    let prune = apply_prune(options, &manifest_path, &mut rows, panel_full)?;
    write_manifest(&manifest_path, &rows)?;
    if prune.panel_pruned_empty == "true" && prune.status == "pruned-empty" {
        emit_panel_envelope(
            options,
            &scout,
            &manifest_path,
            &prune,
            0,
            0,
            "",
            "",
            true,
            true,
            true,
            "",
            0,
        );
        return Ok(());
    }

    let (launch_manifest, carry_outputs, carry_tools) =
        degraded_retry_manifest(&options.review_tmpdir, &manifest_path, &rows)?;
    let (remaining_static, remaining_cursor, remaining_codex, remaining_dynamic) =
        slot_counts(&rows);
    if remaining_static + remaining_dynamic > 0 {
        eprintln!(
            "→ review: launching {} reviewers ({} Cursor static, {} Codex static, {} dynamic)",
            remaining_static + remaining_dynamic,
            remaining_cursor,
            remaining_codex,
            remaining_dynamic
        );
    }
    let artifact_dir = panel_artifact_dir(&options.review_tmpdir, options.round_num);
    let waterfall_arguments = waterfall_arguments(options, &launch_manifest, &artifact_dir);
    let outcome = match dispatch_for_review(&waterfall_arguments) {
        Ok(outcome) => outcome,
        Err(error) => {
            eprintln!("{error}");
            emit_kv("WARN", "agent dispatch-waterfall exited rc=2");
            emit_panel_envelope(
                options,
                &scout,
                &manifest_path,
                &prune,
                remaining_static,
                remaining_dynamic,
                "",
                "",
                false,
                false,
                false,
                "",
                0,
            );
            return Ok(());
        }
    };
    let mut outputs = outcome.all_output_files;
    let mut tools = outcome.all_output_tools;
    outputs.extend(carry_outputs);
    tools.extend(carry_tools);
    let (external, claude) = split_outputs(&outputs, &tools);
    emit_panel_envelope(
        options,
        &scout,
        &manifest_path,
        &prune,
        remaining_static,
        remaining_dynamic,
        &external.join(" "),
        &claude.join(" "),
        outcome.dispatch_ok,
        outcome.static_dispatch_ok,
        outcome.dynamic_dispatch_ok,
        &outcome.dropped_slots_file,
        outcome.straggler_dropped_count,
    );
    if !outcome.warning.is_empty() {
        emit_kv("WATERFALL_WARN", &outcome.warning);
    }
    Ok(())
}

fn static_rows(options: &PanelOptions, plugin_root: &Path) -> Vec<Map<String, Value>> {
    let environment = env::vars().collect::<BTreeMap<_, _>>();
    let mut rows = Vec::new();
    for archetype in STATIC_ARCHETYPES {
        for (tool, default_model) in panel_tools(options) {
            let mut row = manifest_row([
                ("slot", json!(archetype)),
                ("tool", json!(tool)),
                (
                    "output",
                    json!(
                        options
                            .review_tmpdir
                            .join(format!("{tool}-specialist-{archetype}-output.txt"))
                            .display()
                            .to_string()
                    ),
                ),
                (
                    "agent",
                    json!(
                        plugin_root
                            .join("agents")
                            .join(format!("reviewer-{archetype}.md"))
                            .display()
                            .to_string()
                    ),
                ),
            ]);
            if tool == "codex" {
                row.insert("model_role".to_owned(), Value::String("review".to_owned()));
            }
            rows.push(with_manifest_attribution(
                row,
                None,
                default_model,
                &environment,
            ));
        }
    }
    rows
}

fn panel_tools(options: &PanelOptions) -> Vec<(&'static str, &'static str)> {
    let trivial = options.tier == "TRIVIAL";
    let codex = options.codex_available && (!trivial || !options.cursor_available);
    let model = if trivial { "" } else { "gpt-5.6-terra" };
    [
        ("cursor", options.cursor_available, ""),
        ("codex", codex, model),
    ]
    .into_iter()
    .filter_map(|(tool, available, model)| available.then_some((tool, model)))
    .collect()
}

fn slot_counts(rows: &[Map<String, Value>]) -> (usize, usize, usize, usize) {
    let mut static_total = 0;
    let mut static_cursor = 0;
    let mut static_codex = 0;
    let mut dynamic = 0;
    for row in rows {
        if row.contains_key("agent") {
            static_total += 1;
            match row.get("tool").and_then(Value::as_str) {
                Some("cursor") => static_cursor += 1,
                Some("codex") => static_codex += 1,
                _ => {}
            }
        }
        if row.contains_key("prompt_file") {
            dynamic += 1;
        }
    }
    (static_total, static_cursor, static_codex, dynamic)
}

#[allow(clippy::too_many_lines)] // The legacy scout-status state machine is kept contiguous for parity auditing.
fn prepare_dynamic_slots(
    options: &PanelOptions,
    rows: &mut Vec<Map<String, Value>>,
) -> Result<ScoutResult, String> {
    if options.dynamic_max == 0 {
        return Ok(ScoutResult {
            status: "na".to_owned(),
            ..ScoutResult::default()
        });
    }
    let mut result = ScoutResult::default();
    let manifest = options
        .review_tmpdir
        .join(format!("scout-round{}-manifest.json", options.round_num));
    result.manifest = Some(manifest.clone());
    let mut diff_mode = String::new();
    if options.mode == "diff"
        && Path::new(&options.diff_file).is_file()
        && fs::metadata(&options.diff_file).is_ok_and(|metadata| metadata.len() > 0)
    {
        let diff = fs::read_to_string(&options.diff_file).map_err(|error| error.to_string())?;
        let generated =
            generated_paths().map_err(|error| format!("diff classification failed: {error}"))?;
        classify_diff(&diff, &generated)
            .as_str()
            .clone_into(&mut diff_mode);
        if matches!(
            diff_mode.as_str(),
            "docs-only" | "test-only" | "generated-only"
        ) {
            result.status = format!("skipped-{diff_mode}");
            write_dynamic_manifest(&manifest, &[])?;
            write_scout_status(options, &result)?;
            return Ok(result);
        }
    }
    let mut dynamic = Vec::new();
    if !options.pre_scouted_manifest.is_empty() {
        let (_, producer_status) = implement_scout_status();
        let producer_invalid = match (options.site.as_str(), producer_status.as_str()) {
            ("implement Step 5", "" | "ok") => false,
            ("implement Step 5", _) => true,
            _ => false,
        };
        if producer_invalid {
            "producer-invalid".clone_into(&mut result.status);
            result.fail_reason = format!("producer_status_{producer_status}");
            write_dynamic_manifest(&manifest, &[])?;
        } else {
            let raw_count = raw_dynamic_count(Path::new(&options.pre_scouted_manifest));
            let filter_ok = raw_count.is_some()
                && filter_dynamic_manifest(
                    Path::new(&options.pre_scouted_manifest),
                    &manifest,
                    options.dynamic_max,
                );
            if filter_ok {
                dynamic = dynamic_manifest(&manifest)
                    .unwrap_or_default()
                    .into_iter()
                    .take(options.dynamic_max)
                    .collect();
                if options.site == "implement Step 5"
                    && raw_count.unwrap_or_default() > 0
                    && dynamic.is_empty()
                {
                    "producer-invalid".clone_into(&mut result.status);
                    "pre_scouted_filtered_to_zero".clone_into(&mut result.fail_reason);
                    write_dynamic_manifest(&manifest, &[])?;
                } else {
                    result.status = if dynamic.is_empty() {
                        "pre-scouted-empty".to_owned()
                    } else {
                        "pre-scouted".to_owned()
                    };
                }
            } else {
                write_dynamic_manifest(&manifest, &[])?;
                let status = if options.site == "implement Step 5" {
                    "producer-invalid"
                } else {
                    "parse-failed"
                };
                status.clone_into(&mut result.status);
                "pre_scouted_manifest_validation".clone_into(&mut result.fail_reason);
            }
        }
    } else if options.site != "implement Step 5" && manifest.is_file() && nonempty(&manifest) {
        let filtered = options.review_tmpdir.join(format!(
            "scout-round{}-manifest.cached-filter.json",
            options.round_num
        ));
        let raw_count = raw_dynamic_count(&manifest);
        let cached = filter_dynamic_manifest(&manifest, &filtered, options.dynamic_max)
            .then(|| dynamic_manifest(&filtered))
            .flatten()
            .filter(|archetypes| raw_count == Some(archetypes.len()));
        let _removed = fs::remove_file(&filtered);
        let status_path = options
            .review_tmpdir
            .join(format!("scout-round{}-status.env", options.round_num));
        if status_path.is_file() {
            let status = parse_dispatch_kv(&fs::read_to_string(&status_path).unwrap_or_default());
            result.status = status
                .get("SCOUT_STATUS")
                .cloned()
                .unwrap_or_else(|| "na".to_owned());
            result.fail_reason = status.get("SCOUT_FAIL_REASON").cloned().unwrap_or_default();
            if result.status == "ok" && cached.is_some() {
                dynamic = cached
                    .unwrap_or_default()
                    .into_iter()
                    .take(options.dynamic_max)
                    .collect();
            } else if result.status == "parse-failed" && result.fail_reason.is_empty() {
                "cached_parse_failed".clone_into(&mut result.fail_reason);
            }
        } else if cached.as_ref().is_some_and(Vec::is_empty) {
            "empty".clone_into(&mut result.status);
        } else {
            "parse-failed".clone_into(&mut result.status);
            "missing_status_sidecar".clone_into(&mut result.fail_reason);
            write_dynamic_manifest(&manifest, &[])?;
        }
    } else if options.site == "implement Step 5" {
        let (implement_tmpdir, producer_status) = implement_scout_status();
        write_dynamic_manifest(&manifest, &[])?;
        let producer_artifacts = implement_tmpdir.as_ref().is_some_and(|directory| {
            directory.join("scout-coder-manifest.json").exists()
                || directory.join("step2-external-scout-eligible.txt").exists()
        });
        match (producer_status.as_str(), producer_artifacts) {
            ("", false) => {
                "producer-missing".clone_into(&mut result.status);
                "producer_sidecar_absent".clone_into(&mut result.fail_reason);
            }
            ("", true) => {
                "producer-invalid".clone_into(&mut result.status);
                "producer_sidecar_ineligible".clone_into(&mut result.fail_reason);
            }
            (status, _) => {
                "producer-invalid".clone_into(&mut result.status);
                status.clone_into(&mut result.fail_reason);
            }
        }
    } else {
        let mut arguments = vec![
            "scout".to_owned(),
            "dynamic-archetypes".to_owned(),
            "--role-id".to_owned(),
            "review.dynamic_archetype_scout".to_owned(),
            "--mode".to_owned(),
            options.mode.clone(),
            "--max-archetypes".to_owned(),
            options.dynamic_max.to_string(),
            "--output".to_owned(),
            manifest.display().to_string(),
            "--codex-present".to_owned(),
            bool_word(options.codex_available).to_owned(),
            "--cursor-present".to_owned(),
            bool_word(options.cursor_available).to_owned(),
        ];
        if options.mode == "diff" {
            arguments.extend(["--diff-file".to_owned(), options.diff_file.clone()]);
        } else {
            arguments.extend([
                "--scope-files".to_owned(),
                options.scope_files.clone(),
                "--description-text".to_owned(),
                default_value(options.description_text.clone(), "description review"),
            ]);
        }
        arguments.extend(["--plan-file".to_owned(), options.plan_file.clone()]);
        if !options.session_env_path.is_empty() {
            arguments.extend([
                "--session-env-path".to_owned(),
                options.session_env_path.clone(),
            ]);
        }
        // Preserve the retired Python `run_python_verb` 120s outer ceiling for
        // /review dynamic scout rather than the 600s verified-larch default.
        let scout_output = run_verified_larch_with_timeout(
            &arguments
                .into_iter()
                .map(OsString::from)
                .collect::<Vec<OsString>>(),
            Duration::from_secs(120),
        );
        let (ok, stdout) = scout_output.map_or_else(
            |_| (false, String::new()),
            |output| (output.status().success(), process_stdout(&output)),
        );
        let scout_kv = parse_dispatch_kv(&stdout);
        result.status = scout_kv.get("SCOUT_STATUS").cloned().unwrap_or_else(|| {
            if ok {
                "ok".to_owned()
            } else {
                "validation-failed".to_owned()
            }
        });
        result.fail_reason = scout_kv
            .get("SCOUT_FAIL_REASON")
            .cloned()
            .unwrap_or_default();
        let valid = dynamic_manifest(&manifest);
        if !ok || valid.is_none() {
            write_dynamic_manifest(&manifest, &[])?;
            result.status = if ok {
                "parse-failed".to_owned()
            } else {
                "validation-failed".to_owned()
            };
            if result.fail_reason.is_empty() {
                "dispatch_manifest_validation".clone_into(&mut result.fail_reason);
            }
        } else if result.status == "ok" {
            dynamic = valid
                .unwrap_or_default()
                .into_iter()
                .take(options.dynamic_max)
                .collect();
        }
    }
    if !dynamic.is_empty() {
        synthesize_dynamic_rows(options, rows, &dynamic, &diff_mode)?;
    }
    write_scout_status(options, &result)?;
    Ok(result)
}

fn synthesize_dynamic_rows(
    options: &PanelOptions,
    rows: &mut Vec<Map<String, Value>>,
    archetypes: &[DynamicArchetype],
    diff_mode: &str,
) -> Result<(), String> {
    let directory = options.review_tmpdir.join("dynamic-archetypes");
    ensure_directory_chain(&directory).map_err(|error| error.to_string())?;
    let environment = env::vars().collect::<BTreeMap<_, _>>();
    let ledger = ledger_path(&ledger_root(
        &options.review_tmpdir,
        (!options.session_env_path.is_empty()).then(|| Path::new(&options.session_env_path)),
        env::var_os("DESIGN_TMPDIR")
            .filter(|value| !value.is_empty())
            .as_deref()
            .map(Path::new),
    ));
    for archetype in archetypes {
        let agent = directory.join(format!("reviewer-dyn-{}.md", archetype.name));
        let prompt = directory.join(format!("dyn-{}-prompt.md", archetype.name));
        let payload_sidecar =
            directory.join(format!("dyn-{}-prompt.payload-bytes", archetype.name));
        let body = dynamic_agent_body(archetype);
        write_required(&agent, &body)?;
        let mut render = vec![
            "--agent-file".to_owned(),
            agent.display().to_string(),
            "--mode".to_owned(),
            options.mode.clone(),
            "--findings-ledger-file".to_owned(),
            ledger.display().to_string(),
            "--payload-bytes-output".to_owned(),
            payload_sidecar.display().to_string(),
            "--difficulty".to_owned(),
            options.tier.clone(),
        ];
        if !options.session_env_path.is_empty() {
            render.extend([
                "--session-env-path".to_owned(),
                options.session_env_path.clone(),
            ]);
        }
        if options.mode == "diff" {
            if !options.diff_file.is_empty() {
                render.extend(["--diff-file".to_owned(), options.diff_file.clone()]);
            }
            if !options.commit_count.is_empty() {
                render.extend(["--commit-count".to_owned(), options.commit_count.clone()]);
            }
            if !diff_mode.is_empty() {
                render.extend(["--diff-mode".to_owned(), diff_mode.to_owned()]);
            }
        } else {
            render.extend([
                "--description-text".to_owned(),
                default_value(options.description_text.clone(), "description review"),
            ]);
            if !options.scope_files.is_empty() {
                render.extend(["--scope-files".to_owned(), options.scope_files.clone()]);
            }
        }
        for (path, flag) in [
            (&options.plan_file, "--plan-file"),
            (&options.feature_file, "--feature-file"),
        ] {
            if !path.is_empty() && Path::new(path).is_file() {
                render.extend([flag.to_owned(), path.clone()]);
            }
        }
        let render_arguments = render.into_iter().map(OsString::from).collect::<Vec<_>>();
        let rendered = specialist_result(&render_arguments);
        let (payload_bytes, prompt_text) = match rendered {
            Ok(output) if !output.prompt.is_empty() => (
                read_payload_bytes(&payload_sidecar)
                    .saturating_add(archetype.rationale.len())
                    .saturating_add(archetype.prompt_body.len()),
                output.prompt,
            ),
            Ok(_output) => (read_payload_bytes(&payload_sidecar), body.clone()),
            _ => (0, body.clone()),
        };
        write_required(&prompt, &prompt_text)?;
        for (tool, default_model) in panel_tools(options) {
            rows.push(dynamic_row(
                &options.review_tmpdir,
                archetype,
                tool,
                &prompt,
                payload_bytes,
                &environment,
                default_model,
            ));
        }
    }
    Ok(())
}

fn dynamic_row(
    review_tmpdir: &Path,
    archetype: &DynamicArchetype,
    tool: &str,
    prompt: &Path,
    payload_bytes: usize,
    environment: &BTreeMap<String, String>,
    default_model: &str,
) -> Map<String, Value> {
    let suffix = if tool == "codex" { "-codex" } else { "" };
    let mut row = manifest_row([
        ("slot", json!(format!("dyn-{}{}", archetype.name, suffix))),
        ("tool", json!(tool)),
        (
            "output",
            json!(
                review_tmpdir
                    .join(format!("dyn-{}{}-output.txt", archetype.name, suffix))
                    .display()
                    .to_string()
            ),
        ),
        ("prompt_file", json!(prompt.display().to_string())),
        ("payload_bytes", json!(payload_bytes)),
        ("weight", json!(archetype.weight)),
        ("focus_area", json!(archetype.focus_area)),
    ]);
    if tool == "codex" {
        row.insert("model_role".to_owned(), Value::String("review".to_owned()));
    }
    with_manifest_attribution(row, None, default_model, environment)
}

fn apply_prune(
    options: &PanelOptions,
    manifest: &Path,
    rows: &mut Vec<Map<String, Value>>,
    panel_full: usize,
) -> Result<PruneResult, String> {
    let mut result = PruneResult {
        active: "false".to_owned(),
        status: "skipped".to_owned(),
        panel_full,
        panel_pruned_empty: "false".to_owned(),
        ..PruneResult::default()
    };
    let evaluated =
        options.escalated_round != "true" && options.skip_prune != "true" && options.round_num >= 2;
    if !options.prune_ledger.is_empty() {
        let temporary = options.review_tmpdir.join(format!(
            "panel-manifest.pruned.{}.ndjson",
            std::process::id()
        ));
        if evaluated {
            let output = run_verified_larch(&[
                "review".into(),
                "reviewer-prune".into(),
                "filter".into(),
                "--ledger".into(),
                options.prune_ledger.clone().into(),
                "--round".into(),
                options.round_num.to_string().into(),
                "--manifest".into(),
                manifest.display().to_string().into(),
                "--out".into(),
                temporary.display().to_string().into(),
            ]);
            match output {
                Ok(output) if output.status().success() => {
                    let kv = parse_dispatch_kv(&process_stdout(&output));
                    if let Some(warn) = kv.get("WARN").filter(|value| !value.is_empty()) {
                        emit_kv("WARN", warn);
                    }
                    result.active = kv
                        .get("PRUNE_ACTIVE")
                        .cloned()
                        .unwrap_or_else(|| "false".to_owned());
                    result.eligible = if result.active == "true" {
                        kv_usize(&kv, "ELIGIBLE_COUNT")
                    } else {
                        0
                    };
                    result.pruned_count = kv_usize(&kv, "PRUNED_COUNT");
                    result.pruned_combos = kv.get("PRUNED_COMBOS").cloned().unwrap_or_default();
                    result.panel_pruned_empty = kv
                        .get("PANEL_PRUNED_EMPTY")
                        .cloned()
                        .unwrap_or_else(|| "false".to_owned());
                    let fail_open = kv
                        .get("PRUNE_FAIL_OPEN")
                        .is_some_and(|value| value == "true");
                    result.status = prune_status(
                        &result.active,
                        false,
                        fail_open,
                        result.pruned_count,
                        &result.panel_pruned_empty,
                        evaluated,
                    );
                    if result.active == "true" && result.pruned_count > 0 && temporary.exists() {
                        let original =
                            fs::read_to_string(manifest).map_err(|error| error.to_string())?;
                        write_required(
                            &options
                                .review_tmpdir
                                .join("panel-manifest.pre-prune.ndjson"),
                            &original,
                        )?;
                        *rows = read_rows(&temporary)?;
                    }
                }
                _ => {
                    "failed".clone_into(&mut result.status);
                }
            }
        }
        let _removed = fs::remove_file(&temporary);
    }
    write_prune_decision(
        &options.review_tmpdir.join("prune-decision.env"),
        options.round_num,
        &result,
    )?;
    Ok(result)
}

fn degraded_retry_manifest(
    review_tmpdir: &Path,
    manifest: &Path,
    rows: &[Map<String, Value>],
) -> Result<(PathBuf, Vec<String>, Vec<String>), String> {
    if !review_tmpdir.join("degraded-retry.flag").is_file() {
        return Ok((manifest.to_path_buf(), Vec::new(), Vec::new()));
    }
    let collector = review_tmpdir.join("collector-results.env");
    if !collector.is_file() {
        return Ok((manifest.to_path_buf(), Vec::new(), Vec::new()));
    }
    let text = fs::read_to_string(&collector).map_err(|error| error.to_string())?;
    let carried = parse_collector_records(&text)
        .into_iter()
        .filter(|record| {
            matches!(
                record.get("STATUS").map(String::as_str),
                Some("OK" | "cap_hit")
            )
        })
        .filter_map(|record| {
            let file = record.get("REVIEWER_FILE")?.to_owned();
            (!file.is_empty() && nonempty(Path::new(&file))).then(|| {
                (
                    normalize_output_base(&file),
                    (file, record.get("TOOL").cloned().unwrap_or_default()),
                )
            })
        })
        .collect::<BTreeMap<_, _>>();
    if carried.is_empty() {
        return Ok((manifest.to_path_buf(), Vec::new(), Vec::new()));
    }
    let mut relaunch = Vec::new();
    let mut outputs = Vec::new();
    let mut tools = Vec::new();
    for row in rows {
        let output = row
            .get("output")
            .and_then(Value::as_str)
            .unwrap_or_default();
        if let Some((carried_file, tool)) = carried.get(&normalize_output_base(output)) {
            outputs.push(carried_file.clone());
            tools.push(tool.clone());
        } else {
            relaunch.push(row.clone());
        }
    }
    if outputs.is_empty() || relaunch.is_empty() {
        return Ok((manifest.to_path_buf(), Vec::new(), Vec::new()));
    }
    let relaunch_path = review_tmpdir.join("panel-manifest.relaunch.ndjson");
    write_manifest(&relaunch_path, &relaunch)?;
    eprintln!(
        "→ review: degraded retry carrying forward {} substantive slot(s), re-launching {}",
        outputs.len(),
        relaunch.len()
    );
    Ok((relaunch_path, outputs, tools))
}

fn waterfall_arguments(
    options: &PanelOptions,
    manifest: &Path,
    artifact_dir: &Path,
) -> Vec<OsString> {
    let mut arguments = vec![
        "--slots-file".into(),
        manifest.display().to_string().into(),
        "--panel-artifact-dir".into(),
        artifact_dir.display().to_string().into(),
        "--panel-round-num".into(),
        options.round_num.to_string().into(),
        "--codex-present".into(),
        bool_word(options.codex_available).into(),
        "--cursor-present".into(),
        bool_word(options.cursor_available).into(),
        "--mode".into(),
        options.mode.clone().into(),
        "--timeout".into(),
        "1800".into(),
        "--straggler-cutoff".into(),
    ];
    append_review_routing_arguments(
        &mut arguments,
        &options.site,
        &options.tier,
        (options.tier != "TRIVIAL").then_some("gpt-5.6-terra"),
    );
    if options.mode == "diff" && !options.diff_file.is_empty() {
        arguments.extend([
            "--diff-file".into(),
            options.diff_file.clone().into(),
            "--commit-count".into(),
            options.commit_count.clone().into(),
        ]);
    }
    if options.mode == "description" && !options.scope_files.is_empty() {
        arguments.extend([
            "--description-text".into(),
            default_value(options.description_text.clone(), "description review").into(),
            "--scope-files".into(),
            options.scope_files.clone().into(),
        ]);
    }
    for (path, flag) in [
        (&options.plan_file, "--plan-file"),
        (&options.feature_file, "--feature-file"),
    ] {
        if !path.is_empty() && Path::new(path).is_file() {
            arguments.extend([flag.into(), path.clone().into()]);
        }
    }
    if !options.competition_notice_file.is_empty()
        && Path::new(&options.competition_notice_file).is_file()
    {
        arguments.extend([
            "--competition-notice".into(),
            "--competition-notice-file".into(),
            options.competition_notice_file.clone().into(),
        ]);
    }
    if !options.session_env_path.is_empty() {
        arguments.extend([
            "--session-env-path".into(),
            options.session_env_path.clone().into(),
        ]);
    }
    arguments
}

#[allow(clippy::too_many_arguments)]
fn emit_panel_envelope(
    options: &PanelOptions,
    scout: &ScoutResult,
    manifest: &Path,
    prune: &PruneResult,
    static_slots: usize,
    dynamic_slots: usize,
    external_outputs: &str,
    claude_outputs: &str,
    dispatch_ok: bool,
    static_ok: bool,
    dynamic_ok: bool,
    dropped_slots_file: &str,
    straggler_dropped_count: usize,
) {
    let counts = [
        dynamic_slots.to_string(),
        static_slots.to_string(),
        (static_slots + dynamic_slots).to_string(),
        prune.panel_full.to_string(),
        prune.eligible.to_string(),
        prune.pruned_count.to_string(),
    ];
    let panel_manifest = manifest.display().to_string();
    for (key, value) in [
        ("EXTERNAL_OUTPUT_FILES", external_outputs),
        ("CLAUDE_OUTPUT_FILES", claude_outputs),
        ("PANEL_MODE", "waterfall"),
        (
            "PANEL_SHAPE",
            if options.tier == "TRIVIAL" {
                "singles"
            } else {
                "pairs"
            },
        ),
        ("PANEL_TIER", &options.tier),
        ("PANEL_ROUND_CAP", "2"),
        ("PANEL_ESCALATED_ROUND", &options.escalated_round),
        ("SCOUT_STATUS", &scout.status),
        ("DYNAMIC_SLOTS", &counts[0]),
        ("STATIC_SLOT_COUNT", &counts[1]),
        ("SLOT_COUNT", &counts[2]),
        ("PANEL_MANIFEST", &panel_manifest),
        ("PRUNE_ACTIVE", &prune.active),
        ("PRUNE_STATUS", &prune.status),
        ("PANEL_FULL", &counts[3]),
        ("ELIGIBLE", &counts[4]),
        ("PRUNED_COUNT", &counts[5]),
        ("PRUNED_COMBOS", &prune.pruned_combos),
        ("PANEL_PRUNED_EMPTY", &prune.panel_pruned_empty),
        ("DISPATCH_OK", bool_word(dispatch_ok)),
        ("STATIC_DISPATCH_OK", bool_word(static_ok)),
        ("DYNAMIC_DISPATCH_OK", bool_word(dynamic_ok)),
    ] {
        emit_kv(key, value);
    }
    for (key, value) in [
        ("AUDIT_UPGRADE", &options.audit_upgrade),
        ("SCOUT_FAIL_REASON", &scout.fail_reason),
    ] {
        if !value.is_empty() {
            emit_kv(key, value);
        }
    }
    if let Some(scout_manifest) = &scout.manifest {
        emit_kv("SCOUT_MANIFEST", &scout_manifest.display().to_string());
    }
    let scout_difficulty = options
        .review_tmpdir
        .join("scout-difficulty-rating.raw.json");
    if scout_difficulty.is_file() {
        emit_kv(
            "SCOUT_DIFFICULTY_RATING",
            &scout_difficulty.display().to_string(),
        );
        emit_kv("SCOUT_DIFFICULTY_STATUS", "ok");
    }
    if !dropped_slots_file.is_empty() {
        emit_kv("DROPPED_SLOTS_FILE", dropped_slots_file);
    }
    if straggler_dropped_count > 0 {
        emit_kv(
            "STRAGGLER_DROPPED_COUNT",
            &straggler_dropped_count.to_string(),
        );
    }
}

fn append_producer_scout_warning_once(_options: &PanelOptions, scout: &ScoutResult) {
    if !matches!(
        scout.status.as_str(),
        "producer-missing" | "producer-invalid"
    ) {
        return;
    }
    let (implement_tmpdir, _) = implement_scout_status();
    let Some(implement_tmpdir) = implement_tmpdir else {
        return;
    };
    let sentinel = implement_tmpdir.join(".producer-scout-warning-logged");
    if sentinel.exists() {
        return;
    }
    let reason = if scout.fail_reason.is_empty() {
        String::new()
    } else {
        format!(" ({})", scout.fail_reason)
    };
    let output = run_python(vec![
        "run-log".to_owned(),
        "append-entry".to_owned(),
        "--log".to_owned(),
        implement_tmpdir
            .join("execution-issues.md")
            .display()
            .to_string(),
        "--category".to_owned(),
        "Warnings".to_owned(),
        "--entry".to_owned(),
        format!(
            "Step 5 — coder-produced dynamic-archetype manifest {}{}; static reviewers only.",
            scout.status.trim_start_matches("producer-"),
            reason
        ),
    ]);
    if output.is_ok_and(|output| output.status().success()) {
        write_confined(&sentinel, "logged\n");
    } else {
        eprintln!(
            "**⚠ review dispatch-panel: failed to persist producer-scout warning; continuing.**"
        );
    }
}

fn implement_scout_status() -> (Option<PathBuf>, String) {
    let Some(directory) = env::var_os("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
    else {
        return (None, String::new());
    };
    let status = fs::read_to_string(directory.join("step2-scout-coder-status.env"))
        .ok()
        .map(|text| {
            parse_dispatch_kv(&text)
                .get("SCOUT_CODER_STATUS")
                .cloned()
                .unwrap_or_default()
        })
        .unwrap_or_default();
    (Some(directory), status)
}

fn write_scout_status(options: &PanelOptions, scout: &ScoutResult) -> Result<(), String> {
    let Some(manifest) = &scout.manifest else {
        return Ok(());
    };
    let mut text = format!("SCOUT_STATUS={}\n", scout.status);
    if !scout.fail_reason.is_empty() {
        writeln!(&mut text, "SCOUT_FAIL_REASON={}", scout.fail_reason)
            .expect("writing to String cannot fail");
    }
    writeln!(&mut text, "SCOUT_MANIFEST={}", manifest.display())
        .expect("writing to String cannot fail");
    write_required(
        &options
            .review_tmpdir
            .join(format!("scout-round{}-status.env", options.round_num)),
        &text,
    )
}

fn write_prune_decision(path: &Path, round_num: usize, result: &PruneResult) -> Result<(), String> {
    write_required(
        path,
        &format!(
            "ROUND={round_num}\nPRUNE_ACTIVE={}\nPRUNE_STATUS={}\nPANEL_FULL={}\nELIGIBLE={}\nPRUNED_COUNT={}\nPRUNED_COMBOS={}\nPANEL_PRUNED_EMPTY={}\n",
            result.active,
            result.status,
            result.panel_full,
            result.eligible,
            result.pruned_count,
            result.pruned_combos,
            result.panel_pruned_empty,
        ),
    )
}

fn raw_dynamic_count(path: &Path) -> Option<usize> {
    let value = serde_json::from_str::<Value>(&fs::read_to_string(path).ok()?).ok()?;
    value.get("archetypes")?.as_array().map(Vec::len)
}

fn dynamic_manifest(path: &Path) -> Option<Vec<DynamicArchetype>> {
    let value = serde_json::from_str::<Value>(&fs::read_to_string(path).ok()?).ok()?;
    serde_json::from_value(value.get("archetypes")?.clone()).ok()
}

fn filter_dynamic_manifest(input: &Path, output: &Path, max: usize) -> bool {
    let outcome = filter_manifest_paths(input, output, max, "review");
    outcome.emit_warnings();
    outcome.usable()
}

fn write_dynamic_manifest(path: &Path, archetypes: &[DynamicArchetype]) -> Result<(), String> {
    let rows = archetypes
        .iter()
        .map(|row| {
            json!({
                "name": row.name,
                "focus_area": row.focus_area,
                "weight": row.weight,
                "rationale": row.rationale,
                "prompt_body": row.prompt_body,
            })
        })
        .collect::<Vec<_>>();
    let text = format!(
        "{}\n",
        serde_json::to_string(&json!({"archetypes": rows})).map_err(|error| error.to_string())?
    );
    write_required(path, &text)
}

fn dynamic_agent_body(archetype: &DynamicArchetype) -> String {
    DYNAMIC_AGENT_TEMPLATE
        .replace("{name}", &archetype.name)
        .replace("{focus_area}", &archetype.focus_area)
        .replace("{rationale}", &archetype.rationale)
        .replace("{prompt}", &archetype.prompt_body.replace('\n', "\n  "))
}

fn manifest_row(entries: impl IntoIterator<Item = (&'static str, Value)>) -> Map<String, Value> {
    entries
        .into_iter()
        .map(|(key, value)| (key.to_owned(), value))
        .collect()
}

fn read_rows(path: &Path) -> Result<Vec<Map<String, Value>>, String> {
    fs::read_to_string(path)
        .map_err(|error| error.to_string())?
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).map_err(|error| error.to_string()))
        .collect()
}

fn panel_artifact_dir(review_tmpdir: &Path, round_num: usize) -> PathBuf {
    if review_tmpdir
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(is_round_directory)
    {
        return review_tmpdir.to_path_buf();
    }
    let round = review_tmpdir.join(format!("round-{round_num}"));
    if round.is_dir() {
        round
    } else {
        review_tmpdir.to_path_buf()
    }
}

fn is_round_directory(name: &str) -> bool {
    name.strip_prefix("round-").is_some_and(|suffix| {
        !suffix.is_empty() && suffix.bytes().all(|byte| byte.is_ascii_digit())
    })
}

fn split_outputs(outputs: &[String], tools: &[String]) -> (Vec<String>, Vec<String>) {
    let mut external = Vec::new();
    let mut claude = Vec::new();
    for (index, output) in outputs.iter().enumerate() {
        if tools.get(index).is_some_and(|tool| tool == "claude") {
            claude.push(output.clone());
        } else {
            external.push(output.clone());
        }
    }
    (external, claude)
}

fn process_stdout(output: &larch_core::ProcessOutput) -> String {
    String::from_utf8_lossy(output.stdout()).into_owned()
}

fn run_python(arguments: Vec<String>) -> Result<larch_core::ProcessOutput, String> {
    run_python_verb(
        arguments.into_iter().map(OsString::from),
        Duration::from_secs(120),
    )
}

fn kv_usize(kv: &BTreeMap<String, String>, key: &str) -> usize {
    kv.get(key)
        .and_then(|value| value.parse().ok())
        .unwrap_or_default()
}

fn nonempty(path: &Path) -> bool {
    path.is_file() && fs::metadata(path).is_ok_and(|metadata| metadata.len() > 0)
}

fn read_payload_bytes(path: &Path) -> usize {
    fs::read_to_string(path)
        .ok()
        .and_then(|value| value.trim().parse::<i64>().ok())
        .and_then(|value| usize::try_from(value).ok())
        .unwrap_or_default()
}

fn normalize_tier(value: &str) -> String {
    match value.trim().to_ascii_uppercase().as_str() {
        "TRIVIAL" | "MODERATE" | "HARD" => value.trim().to_ascii_uppercase(),
        _ => String::new(),
    }
}

fn panel_for_tier(tier: &str) -> &'static str {
    if tier == "TRIVIAL" { "simple" } else { "hard" }
}

const fn bool_word(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

fn prune_status(
    active: &str,
    filter_failed: bool,
    fail_open: bool,
    pruned_count: usize,
    pruned_empty: &str,
    evaluated: bool,
) -> String {
    if filter_failed || fail_open {
        "failed".to_owned()
    } else if pruned_empty == "true" {
        "pruned-empty".to_owned()
    } else if active != "true" || !evaluated {
        "skipped".to_owned()
    } else if pruned_count > 0 {
        "active-dropped".to_owned()
    } else {
        "active-kept-all".to_owned()
    }
}
