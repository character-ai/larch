//! Rust owner for the code-review round orchestration command.
//!
//! The individual review phases already have Rust command owners.  This module
//! deliberately composes them through the verified plugin entrypoint so an
//! installed plugin, rather than the caller's checkout or `PATH`, remains the
//! single runtime authority.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{SystemTime, UNIX_EPOCH},
};

use larch_core::{
    SafeText, emit_kv,
    review::{self, normalize_output_base, parse_blocks, parse_legacy_collector_blocks},
};
use regex::Regex;
use sha2::{Digest as _, Sha256};

use crate::{oos_commands::atomic_write, runtime_entrypoint::run_verified_larch};

const CORE_USAGE: &str = "Usage: review core --mode diff|description --output-dir DIR --codex-available true|false --cursor-available true|false [--dynamic-archetypes 0-1] [--pre-scouted-manifest FILE] [--site SITE] [context flags]";
const CORE_OPTIONS: &[&str] = &[
    "--mode",
    "--diff-file",
    "--commit-count",
    "--scope-files",
    "--codex-available",
    "--cursor-available",
    "--plan-file",
    "--feature-file",
    "--description-text",
    "--session-env-path",
    "--panel",
    "--tier",
    "--escalated-round",
    "--dynamic-archetypes",
    "--pre-scouted-manifest",
    "--round-num",
    "--prune-ledger",
    "--site",
    "--output-dir",
    "--run-id",
];

#[derive(Clone, Debug, Default)]
struct Output {
    rc: i32,
    stdout: String,
    stderr: String,
}

type Rows = Vec<(String, String)>;

#[derive(Clone, Debug)]
struct CoreOptions {
    values: BTreeMap<String, String>,
    mode: String,
    review_tmpdir: PathBuf,
    codex_available: String,
    cursor_available: String,
    panel: String,
    tier: String,
    escalated_round: String,
    dynamic: String,
    round_num: u64,
    session_env_path: String,
    run_id: String,
    prune_ledger: String,
    site: String,
}

#[derive(Clone, Debug)]
struct CoreResult {
    rc: i32,
    rows: Rows,
}

struct TallyResult {
    output: Output,
    values: BTreeMap<String, String>,
}

/// Run `review core` with its legacy-compatible raw argument grammar.
pub fn core(arguments: &[OsString]) -> ExitCode {
    let Some(options) = parse_core_options(arguments) else {
        return if arguments.iter().any(|argument| argument == "--help") {
            ExitCode::SUCCESS
        } else {
            ExitCode::from(2)
        };
    };
    let result = run_core_with(&options, &production_runner);
    for (key, value) in result.rows {
        emit_kv(&key, &value);
    }
    exit_code(result.rc)
}

fn exit_code(rc: i32) -> ExitCode {
    ExitCode::from(u8::try_from(rc.clamp(0, 255)).unwrap_or(1))
}

fn parse_core_options(arguments: &[OsString]) -> Option<CoreOptions> {
    let raw = arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    if raw.iter().any(|value| value == "--help") {
        diagnostic(CORE_USAGE);
        return None;
    }
    let mut values = BTreeMap::new();
    let mut index = 0;
    while index < raw.len() {
        let option = &raw[index];
        if !CORE_OPTIONS.contains(&option.as_str()) {
            diagnostic(&format!("unknown option: {option}\n{CORE_USAGE}"));
            return None;
        }
        let Some(value) = raw.get(index + 1) else {
            diagnostic(&format!("{option} requires a value\n{CORE_USAGE}"));
            return None;
        };
        values.insert(option.clone(), value.clone());
        index += 2;
    }
    let value = |key: &str, default: &str| {
        values
            .get(key)
            .cloned()
            .unwrap_or_else(|| default.to_owned())
    };
    let mode = value("--mode", "");
    let output_dir = value("--output-dir", "");
    let review_tmpdir = PathBuf::from(if output_dir.is_empty() {
        "."
    } else {
        &output_dir
    });
    let codex_available = value("--codex-available", "");
    let cursor_available = value("--cursor-available", "");
    let mut panel = value("--panel", "hard");
    let raw_tier = value("--tier", "");
    let tier = normalize_tier(&raw_tier).unwrap_or_else(|| {
        if panel == "simple" {
            "TRIVIAL"
        } else {
            "MODERATE"
        }
        .to_owned()
    });
    if !raw_tier.is_empty() && normalize_tier(&raw_tier).is_none() {
        diagnostic(CORE_USAGE);
        return None;
    }
    if !raw_tier.is_empty() {
        threshold_panel(&tier).clone_into(&mut panel);
    }
    let escalated_round = value("--escalated-round", "false");
    let dynamic = value(
        "--dynamic-archetypes",
        &env::var("LARCH_DYNAMIC_ARCHETYPES_MAX").unwrap_or_else(|_| "0".to_owned()),
    );
    let round_raw = value("--round-num", "1");
    let round_num = decimal_number(&round_raw).filter(|value| *value > 0);
    if !matches!(mode.as_str(), "diff" | "description")
        || !matches!(codex_available.as_str(), "true" | "false")
        || !matches!(cursor_available.as_str(), "true" | "false")
        || !matches!(panel.as_str(), "simple" | "hard")
        || !matches!(dynamic.as_str(), "0" | "1")
        || !matches!(escalated_round.as_str(), "true" | "false")
        || round_num.is_none()
    {
        diagnostic(CORE_USAGE);
        return None;
    }
    let session_env_path = value(
        "--session-env-path",
        &env::var("SESSION_ENV_PATH").unwrap_or_default(),
    );
    let run_id = value("--run-id", "");
    let prune_ledger = value("--prune-ledger", "");
    let site = value("--site", "review Step 2");
    Some(CoreOptions {
        values,
        mode,
        review_tmpdir,
        codex_available,
        cursor_available,
        panel,
        tier,
        escalated_round,
        dynamic,
        round_num: round_num.expect("validated positive review round"),
        session_env_path,
        run_id,
        prune_ledger,
        site,
    })
}

fn normalize_tier(value: &str) -> Option<String> {
    let tier = value.trim().to_ascii_uppercase();
    match tier.as_str() {
        "TRIVIAL" | "MODERATE" | "HARD" => Some(tier),
        _ => None,
    }
}

fn threshold_panel(tier: &str) -> &'static str {
    if tier == "TRIVIAL" { "simple" } else { "hard" }
}

fn production_runner(arguments: &[String]) -> Result<Output, String> {
    let arguments = arguments.iter().map(OsString::from).collect::<Vec<_>>();
    let result = run_verified_larch(&arguments)?;
    let status = result.status();
    Ok(Output {
        rc: status
            .code()
            .unwrap_or_else(|| i32::from(!status.success())),
        stdout: String::from_utf8_lossy(result.stdout()).into_owned(),
        stderr: String::from_utf8_lossy(result.stderr()).into_owned(),
    })
}

#[allow(clippy::cognitive_complexity, clippy::too_many_lines)] // Phase order and every artifact-producing branch are one compatibility transaction.
fn run_core_with<F>(options: &CoreOptions, runner: &F) -> CoreResult
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    if let Err(error) = fs::create_dir_all(&options.review_tmpdir) {
        return failed_result(
            &options.review_tmpdir,
            options.round_num,
            "normal",
            &options.panel,
            &format!("review output directory failed: {error}"),
        );
    }
    let mut mode = options.mode.clone();
    let mut gather_args = strings(&[
        "--mode",
        &mode,
        "--output-dir",
        path(&options.review_tmpdir),
    ]);
    add_if(
        &mut gather_args,
        "--description-text",
        options.value("--description-text"),
    );
    add_if(
        &mut gather_args,
        "--scope-files",
        options.value("--scope-files"),
    );
    let gather = call(runner, "review", "gather-context", gather_args);
    let gather = match gather {
        Ok(output) => output,
        Err(error) => {
            return failed_result(
                &options.review_tmpdir,
                options.round_num,
                "normal",
                &options.panel,
                &format!("gather-context failed: {error}"),
            );
        }
    };
    let _ = write_text(
        &options.review_tmpdir.join("review-core-gather.env"),
        &gather.stdout,
    );
    let gather_values = parse_kv(&gather.stdout);
    let diff_file = nonempty(
        options.value("--diff-file"),
        get(&gather_values, "DIFF_FILE", ""),
    );
    let scope_files = nonempty(
        options.value("--scope-files"),
        get(&gather_values, "FILE_LIST_FILE", ""),
    );
    let commit_count = nonempty(
        options.value("--commit-count"),
        get(&gather_values, "COMMIT_COUNT", "0"),
    );
    if gather_values.contains_key("MODE") {
        mode = nonempty(&get(&gather_values, "MODE", ""), "diff".to_owned());
    }
    if mode == "description" && get(&gather_values, "SCOPE_FILES_COUNT", "0") == "0" {
        for name in [
            "findings.md",
            "accepted-findings.md",
            "rejected-findings.md",
            "oos-accepted-review.md",
        ] {
            let _ = write_text(&options.review_tmpdir.join(name), "");
        }
        flush_round_log(options, runner);
        let mut rows = vec![
            row("SCOUT_STATUS", "na"),
            row("DYNAMIC_SLOTS", "0"),
            row("SCOUT_MANIFEST", ""),
        ];
        rows.extend(common_rows(
            "zero-findings",
            options.round_num,
            &options.review_tmpdir,
            "normal",
            &options.panel,
            Counts::default(),
            None,
            None,
        ));
        return CoreResult { rc: 0, rows };
    }

    let mut dispatch_args = strings(&[
        "--mode",
        &mode,
        "--review-tmpdir",
        path(&options.review_tmpdir),
        "--panel",
        &options.panel,
        "--tier",
        &options.tier,
        "--escalated-round",
        &options.escalated_round,
        "--codex-available",
        &options.codex_available,
        "--cursor-available",
        &options.cursor_available,
        "--commit-count",
        &commit_count,
        "--timing-task-prefix",
        &format!("review-round{}", options.round_num),
        "--dynamic-archetypes",
        &options.dynamic,
        "--round-num",
        &options.round_num.to_string(),
        "--site",
        &options.site,
    ]);
    for (flag, value) in [
        ("--diff-file", diff_file.as_str()),
        ("--scope-files", scope_files.as_str()),
        ("--plan-file", options.value("--plan-file")),
        ("--feature-file", options.value("--feature-file")),
        ("--description-text", options.value("--description-text")),
        ("--session-env-path", options.session_env_path.as_str()),
        ("--prune-ledger", options.prune_ledger.as_str()),
        (
            "--pre-scouted-manifest",
            options.value("--pre-scouted-manifest"),
        ),
    ] {
        add_if(&mut dispatch_args, flag, value);
    }
    let competition = options.review_tmpdir.join("competition-notice.md");
    if file_exists(&competition) {
        add_if(
            &mut dispatch_args,
            "--competition-notice-file",
            path(&competition),
        );
    }
    progress_note(
        options,
        &format!(
            "round {}: reviewer panel dispatch running",
            options.round_num
        ),
    );
    let dispatch = call(runner, "review", "dispatch-panel", dispatch_args);
    let dispatch = match dispatch {
        Ok(output) => output,
        Err(error) => {
            ensure_prune_sidecars(&options.review_tmpdir, options.round_num);
            return failed_result(
                &options.review_tmpdir,
                options.round_num,
                "normal",
                &options.panel,
                &format!("dispatch-panel failed: {error}"),
            );
        }
    };
    let collect_start = epoch_seconds();
    let _ = write_text(
        &options.review_tmpdir.join("review-core-dispatch.env"),
        &dispatch.stdout,
    );
    if dispatch.rc != 0 {
        ensure_prune_sidecars(&options.review_tmpdir, options.round_num);
        flush_round_log(options, runner);
        return failed_result(
            &options.review_tmpdir,
            options.round_num,
            "normal",
            &options.panel,
            &format!("dispatch-panel exited rc={}", dispatch.rc),
        );
    }
    let dispatch_values = parse_kv(&dispatch.stdout);
    let external_outputs = split_paths(&get(&dispatch_values, "EXTERNAL_OUTPUT_FILES", ""));
    let claude_outputs = split_paths(&get(&dispatch_values, "CLAUDE_OUTPUT_FILES", ""));
    let panel_mode = get(&dispatch_values, "PANEL_MODE", "waterfall");
    let panel_shape = get(&dispatch_values, "PANEL_SHAPE", &options.panel);
    let panel_tier = get(&dispatch_values, "PANEL_TIER", &options.tier);
    let panel_manifest = get(&dispatch_values, "PANEL_MANIFEST", "");
    let scout_status = get(&dispatch_values, "SCOUT_STATUS", "na");
    let scout_fail_reason = get(&dispatch_values, "SCOUT_FAIL_REASON", "");
    let dynamic_slots = get(&dispatch_values, "DYNAMIC_SLOTS", "0");
    let static_slot_count = get(&dispatch_values, "STATIC_SLOT_COUNT", "0");
    let panel_pruned_empty = get(&dispatch_values, "PANEL_PRUNED_EMPTY", "false");
    let prune_status = get(&dispatch_values, "PRUNE_STATUS", "");
    let scout_manifest = get(&dispatch_values, "SCOUT_MANIFEST", "");
    let mut scout_text = format!("SCOUT_STATUS={scout_status}\n");
    if !scout_fail_reason.is_empty() {
        let _ = writeln!(scout_text, "SCOUT_FAIL_REASON={scout_fail_reason}");
    }
    let _ = write!(
        scout_text,
        "DYNAMIC_SLOTS={dynamic_slots}\nSCOUT_MANIFEST={scout_manifest}\n"
    );
    let _ = write_text(
        &options
            .review_tmpdir
            .join(format!("scout-round{}-status.env", options.round_num)),
        &scout_text,
    );
    let mut dispatch_rows = vec![row("SCOUT_STATUS", scout_status.clone())];
    if !scout_fail_reason.is_empty() {
        dispatch_rows.push(row("SCOUT_FAIL_REASON", &scout_fail_reason));
    }
    dispatch_rows.push(row("DYNAMIC_SLOTS", dynamic_slots.clone()));
    if !scout_manifest.is_empty() {
        dispatch_rows.push(row("SCOUT_MANIFEST", &scout_manifest));
    }
    if let Some(value) = dispatch_values
        .get("PRUNED_COMBOS")
        .filter(|value| !value.is_empty())
    {
        dispatch_rows.push(row("PRUNED_COMBOS", value));
    }
    dispatch_rows.push(row("PANEL_PRUNED_EMPTY", panel_pruned_empty.clone()));
    progress_note(
        options,
        &format!("round {}: launching reviewers", options.round_num),
    );

    if panel_pruned_empty == "true" && prune_status == "pruned-empty" {
        snapshot_oos(
            &options.review_tmpdir,
            "prune-skipped",
            &options.session_env_path,
        );
        for name in [
            "findings.md",
            "accepted-findings.md",
            "rejected-findings.md",
            "oos.md",
            "oos-accepted-review.md",
        ] {
            let _ = write_text(&options.review_tmpdir.join(name), "");
        }
        let _ = write_text(
            &options.review_tmpdir.join("voting-tally.md"),
            "# Code Review Voting Tally\n\nRound skipped: all reviewer combos pruned.\n",
        );
        restore_oos(
            &options.review_tmpdir,
            "prune-skipped",
            &options.session_env_path,
        );
        ensure_prune_sidecars(&options.review_tmpdir, options.round_num);
        flush_round_log(options, runner);
        diagnostic(&format!(
            "→ review: round {} skipped: all reviewer combos pruned",
            options.round_num
        ));
        dispatch_rows.extend(common_rows(
            "prune-skipped",
            options.round_num,
            &options.review_tmpdir,
            &panel_mode,
            &panel_shape,
            Counts::default(),
            None,
            None,
        ));
        return CoreResult {
            rc: 0,
            rows: dispatch_rows,
        };
    }

    let mut rows = dispatch_rows;
    let mut collect_args = strings(&[
        "--mode",
        &mode,
        "--timeout",
        "1860",
        "--findings-file",
        path(&options.review_tmpdir.join("findings.md")),
        "--oos-file",
        path(&options.review_tmpdir.join("oos.md")),
    ]);
    add_if(
        &mut collect_args,
        "--session-env-path",
        &options.session_env_path,
    );
    add_list_if(
        &mut collect_args,
        "--external-output-files",
        &external_outputs,
    );
    add_list_if(&mut collect_args, "--claude-output-files", &claude_outputs);
    progress_note(
        options,
        &format!("round {}: collecting reviewer outputs", options.round_num),
    );
    diagnostic("→ review: consolidating findings");
    let collect =
        call(runner, "review", "collect-findings", collect_args).unwrap_or_else(|error| Output {
            rc: 1,
            stdout: String::new(),
            stderr: error,
        });
    let _ = write_text(
        &options.review_tmpdir.join("review-core-collect.env"),
        &collect.stdout,
    );
    let collect_values = parse_kv(&collect.stdout);
    let collector_results = options.review_tmpdir.join("collector-results.env");
    let intended_slots = parse_number(
        &get(&dispatch_values, "SLOT_COUNT", ""),
        parse_number(&static_slot_count, 0) + parse_number(&dynamic_slots, 0),
    );
    let launched_slots = parse_number(&get(&dispatch_values, "LAUNCHED_SLOTS", ""), intended_slots);
    let mut threshold_args = strings(&[
        "--collector-results-file",
        path(&collector_results),
        "--panel",
        threshold_panel(&panel_tier),
        "--intended-slots",
        &intended_slots.to_string(),
        "--launched-slots",
        &launched_slots.to_string(),
        "--round-num",
        &options.round_num.to_string(),
    ]);
    let dropped_slots = get(&dispatch_values, "DROPPED_SLOTS_FILE", "");
    if file_exists(Path::new(&dropped_slots)) {
        add_if(&mut threshold_args, "--dropped-slots-file", &dropped_slots);
    }
    if file_exists(Path::new(&panel_manifest)) {
        add_if(&mut threshold_args, "--panel-manifest", &panel_manifest);
    }
    let all_outputs = external_outputs
        .iter()
        .chain(&claude_outputs)
        .cloned()
        .collect::<Vec<_>>();
    add_list_if(&mut threshold_args, "--reviewer-output-files", &all_outputs);
    progress_note(
        options,
        &format!(
            "round {}: reviewers {}/{} done",
            options.round_num,
            collector_success_count(&collector_results),
            launched_slots
        ),
    );
    progress_note(
        options,
        &format!(
            "round {}: checking reviewer failure threshold",
            options.round_num
        ),
    );
    let threshold = call(
        runner,
        "review",
        "check-reviewer-failure-threshold",
        threshold_args,
    )
    .unwrap_or_else(|error| Output {
        rc: 1,
        stdout: String::new(),
        stderr: error,
    });
    let threshold_out = options.review_tmpdir.join("review-core-threshold.env");
    let _ = write_text(&threshold_out, &threshold.stdout);
    append_threshold_metadata(&threshold_out, &dispatch_values);
    let threshold_values = parse_kv(&read_text(&threshold_out));
    let mut threshold_ok = get(&threshold_values, "THRESHOLD_OK", "true");
    let mut threshold_reason = get(&threshold_values, "THRESHOLD_REASON", "");
    let not_substantive = parse_number(&get(&threshold_values, "NOT_SUBSTANTIVE_SLOTS", "0"), 0);
    let mut coverage_recorded = false;
    if collector_success_count(&collector_results) == 0 {
        if parseable_output_present(&options.review_tmpdir) {
            let _ = append_text(
                &threshold_out,
                "COVERAGE_GATE_OK=true\nCOVERAGE_GATE_REASON=parseable reviewer output present\n",
            );
            coverage_recorded = true;
        } else if !protected_threshold_reason(&threshold_reason) {
            "false".clone_into(&mut threshold_ok);
            "no successful launched reviewer output".clone_into(&mut threshold_reason);
            rewrite_threshold(&threshold_out, &threshold_ok, &threshold_reason);
            coverage_recorded = true;
        }
    }
    if threshold_ok != "false" {
        if let Some(reason) = static_coverage_reason(
            &collector_results,
            Path::new(&panel_manifest),
            &all_outputs,
            Path::new(&dropped_slots),
        ) {
            "false".clone_into(&mut threshold_ok);
            threshold_reason.clone_from(&reason);
            let _ = append_text(
                &threshold_out,
                &format!("COVERAGE_GATE_OK=false\nCOVERAGE_GATE_REASON={reason}\n"),
            );
        } else if !coverage_recorded {
            let _ = append_text(
                &threshold_out,
                "COVERAGE_GATE_OK=true\nCOVERAGE_GATE_REASON=static reviewer coverage satisfied\n",
            );
        }
    }
    if threshold_ok == "false" {
        for name in [
            "accepted-findings.md",
            "rejected-findings.md",
            "oos-accepted-review.md",
            "oos.md",
        ] {
            let _ = write_text(&options.review_tmpdir.join(name), "");
        }
        let tally_file = options
            .review_tmpdir
            .join("review-core-panel-failed-tally.env");
        let _ = write_text(
            &tally_file,
            "ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\n",
        );
        emit_tally(
            options,
            runner,
            &mode,
            &tally_file,
            &options.review_tmpdir.join("accepted-findings.md"),
            &scout_status,
            &dynamic_slots,
            &static_slot_count,
            "review-core-panel-failed-emit.env",
        );
        copy_to_parent(
            &options.review_tmpdir.join("rejected-findings.md"),
            "rejected-findings.md",
            &options.session_env_path,
        );
        copy_to_parent(
            &options.review_tmpdir.join("oos-accepted-review.md"),
            "oos-accepted-review.md",
            &options.session_env_path,
        );
        flush_round_log(options, runner);
        rows.extend(common_rows(
            "panel-failed",
            options.round_num,
            &options.review_tmpdir,
            &panel_mode,
            &panel_shape,
            Counts::default(),
            None,
            Some(&threshold_reason),
        ));
        return CoreResult { rc: 2, rows };
    }

    let context = VoteContext {
        options,
        runner,
        mode: &mode,
        panel_mode: &panel_mode,
        panel_shape: &panel_shape,
        panel_tier: &panel_tier,
        panel_manifest: &panel_manifest,
        collector_results: &collector_results,
        not_substantive,
        scout_status: &scout_status,
        dynamic_slots: &dynamic_slots,
        static_slot_count: &static_slot_count,
        diff_file: &diff_file,
        scope_files: &scope_files,
    };
    if get(&collect_values, "FINDINGS_COUNT", "0") == "0" {
        return zero_findings(&context, rows);
    }
    if let Some(result) = prune_for_ballot(
        &context,
        &mut rows,
        &options.review_tmpdir.join("findings.md"),
    ) {
        return result;
    }
    let snapshot = options.review_tmpdir.join("findings-pre-aggregate.md");
    if let Err(error) = copy_checked(&options.review_tmpdir.join("findings.md"), &snapshot) {
        log_review_core_issue(
            &options.review_tmpdir,
            &format!("pre-aggregate snapshot failed: {error}"),
        );
        return post_gate_failure(&context, rows, "findings-pre-aggregate-snapshot-failed");
    }
    let mut aggregate_args = strings(&[
        "--findings-file",
        path(&options.review_tmpdir.join("findings.md")),
        "--review-tmpdir",
        path(&options.review_tmpdir),
        "--codex-present",
        &options.codex_available,
        "--cursor-present",
        &options.cursor_available,
        "--mode",
        &mode,
        "--round-num",
        &options.round_num.to_string(),
    ]);
    add_if(
        &mut aggregate_args,
        "--session-env-path",
        &options.session_env_path,
    );
    add_if(&mut aggregate_args, "--diff-file", &diff_file);
    add_if(
        &mut aggregate_args,
        "--plan-file",
        options.value("--plan-file"),
    );
    progress_note(
        options,
        &format!("round {}: aggregating reviewer findings", options.round_num),
    );
    record_reviewer_collect(
        &options.review_tmpdir,
        options.round_num,
        collect_start,
        epoch_seconds(),
    );
    let aggregate =
        call(runner, "review", "aggregate-findings", aggregate_args).unwrap_or_else(|error| {
            Output {
                rc: 1,
                stdout: String::new(),
                stderr: error,
            }
        });
    let _ = write_text(
        &options.review_tmpdir.join("review-core-aggregate.env"),
        &aggregate.stdout,
    );
    let aggregate_values = parse_kv(&aggregate.stdout);
    if get(&aggregate_values, "REASON", "") == "validation-exhausted" {
        if let Some(result) = prune_for_ballot(
            &context,
            &mut rows,
            &options.review_tmpdir.join("findings.md"),
        ) {
            return result;
        }
        return validation_exhausted(&context, rows);
    }
    if get(&aggregate_values, "REASON", "") == "ok"
        && get(&aggregate_values, "MERGED_COUNT", "") == "0"
    {
        if !file_exists(&snapshot) {
            return post_gate_failure(&context, rows, "findings-pre-aggregate-snapshot-missing");
        }
        if let Some(result) = prune_for_ballot(&context, &mut rows, &snapshot) {
            return result;
        }
        if let Err(error) = copy_checked(&snapshot, &options.review_tmpdir.join("findings.md")) {
            log_review_core_issue(
                &options.review_tmpdir,
                &format!("ballot promote failed: {error}"),
            );
            return post_gate_failure(&context, rows, "ballot-promote-failed");
        }
    } else if let Some(result) = prune_for_ballot(
        &context,
        &mut rows,
        &options.review_tmpdir.join("findings.md"),
    ) {
        return result;
    }
    finish_vote(
        &context,
        rows,
        "review-core-tally.env",
        "review-core-emit.env",
    )
}

impl CoreOptions {
    fn value(&self, key: &str) -> &str {
        self.values.get(key).map_or("", String::as_str)
    }
}

struct VoteContext<'a, F>
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    options: &'a CoreOptions,
    runner: &'a F,
    mode: &'a str,
    panel_mode: &'a str,
    panel_shape: &'a str,
    panel_tier: &'a str,
    panel_manifest: &'a str,
    collector_results: &'a Path,
    not_substantive: u64,
    scout_status: &'a str,
    dynamic_slots: &'a str,
    static_slot_count: &'a str,
    diff_file: &'a str,
    scope_files: &'a str,
}

fn prune_for_ballot<F>(
    context: &VoteContext<'_, F>,
    rows: &mut Rows,
    ballot: &Path,
) -> Option<CoreResult>
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let security_parent = if context.options.session_env_path.is_empty() {
        context.options.review_tmpdir.clone()
    } else {
        PathBuf::from(&context.options.session_env_path)
            .parent()
            .unwrap_or_else(|| Path::new("."))
            .to_path_buf()
    };
    let result = call(
        context.runner,
        "review",
        "prune-nit-findings",
        strings(&[
            "--findings-file",
            path(ballot),
            "--audit-file",
            path(
                &context
                    .options
                    .review_tmpdir
                    .join("oos-dropped-before-vote.md"),
            ),
            "--security-audit-file",
            path(&security_parent.join("security-oos-observations.md")),
        ]),
    )
    .unwrap_or_default();
    let _ = write_text(
        &context
            .options
            .review_tmpdir
            .join("review-core-prune-nit.env"),
        &result.stdout,
    );
    let _ = write_text(
        &context.options.review_tmpdir.join("prune-nit.env"),
        if result.stdout.is_empty() {
            "PRUNED_COUNT=0\nINSCOPE_REMAINING=0\nSTATUS=skipped\n"
        } else {
            &result.stdout
        },
    );
    let pruned_count = get(&parse_kv(&result.stdout), "PRUNED_COUNT", "0");
    if pruned_count != "0" {
        diagnostic(&format!(
            "→ review: nit filter dropped {pruned_count} finding(s) before vote"
        ));
    }
    match ballot_block_count(ballot) {
        None => Some(post_gate_failure(
            context,
            std::mem::take(rows),
            "ballot-read-failed",
        )),
        Some(0) => Some(zero_findings(context, std::mem::take(rows))),
        Some(_) => None,
    }
}

fn zero_findings<F>(context: &VoteContext<'_, F>, mut rows: Rows) -> CoreResult
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let voter = context
        .options
        .review_tmpdir
        .join("zero-findings-voter.txt");
    let _ = write_text(&voter, "");
    snapshot_oos(
        &context.options.review_tmpdir,
        "zero-findings",
        &context.options.session_env_path,
    );
    let tally = tally(
        context,
        vec![path(&voter).to_owned()],
        Vec::new(),
        None,
        "review-core-zero-findings-tally.env",
    );
    let classification = get(&tally.values, "FINDINGS_CLASSIFICATION_TSV_FILE", "");
    record_classification(
        &context.options.review_tmpdir,
        context.options.round_num,
        &classification,
        &mut rows,
    );
    if !classification.is_empty() && file_exists(Path::new(&classification)) {
        record_prune_round(context, &classification, &mut rows);
    }
    for name in [
        "accepted-findings.md",
        "rejected-findings.md",
        "oos-accepted-review.md",
    ] {
        let _ = write_text(&context.options.review_tmpdir.join(name), "");
    }
    let tally_file = PathBuf::from(get(
        &tally.values,
        "TALLY_FILE",
        path(&context.options.review_tmpdir.join("review-tally.env")),
    ));
    let accepted = PathBuf::from(get(
        &tally.values,
        "ACCEPTED_FINDINGS_FILE",
        path(&context.options.review_tmpdir.join("accepted-findings.md")),
    ));
    emit_tally(
        context.options,
        context.runner,
        context.mode,
        &tally_file,
        &accepted,
        context.scout_status,
        context.dynamic_slots,
        context.static_slot_count,
        "review-core-zero-findings-emit.env",
    );
    copy_to_parent(
        &context.options.review_tmpdir.join("rejected-findings.md"),
        "rejected-findings.md",
        &context.options.session_env_path,
    );
    restore_oos(
        &context.options.review_tmpdir,
        "zero-findings",
        &context.options.session_env_path,
    );
    flush_round_log(context.options, context.runner);
    rows.extend(common_rows(
        "zero-findings",
        context.options.round_num,
        &context.options.review_tmpdir,
        context.panel_mode,
        context.panel_shape,
        Counts::default(),
        None,
        None,
    ));
    let voting_tally = get(&tally.values, "VOTING_TALLY_FILE", "");
    if !voting_tally.is_empty() {
        rows.push(row("VOTING_TALLY_FILE", voting_tally));
    }
    CoreResult { rc: 0, rows }
}

fn validation_exhausted<F>(context: &VoteContext<'_, F>, mut rows: Rows) -> CoreResult
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let map = match prepare_proposer_map(
        &context.options.review_tmpdir.join("findings.md"),
        &context.options.review_tmpdir.join("proposer-map.tsv"),
    ) {
        Ok(path) => path,
        Err(error) => {
            diagnostic(&format!(
                "→ review: proposer map preparation failed: {error}"
            ));
            return post_gate_failure(context, rows, "proposer-map-failed");
        }
    };
    let (voter_files, voter_tools) = dispatch_voters(context, &mut rows);
    let tally = tally(
        context,
        voter_files,
        voter_tools,
        Some(&map),
        "review-core-aggregator-exhaust-tally.env",
    );
    if tally.output.rc != 0 && get(&tally.values, "TALLY_STATUS", "").is_empty() {
        return post_gate_failure(context, rows, "tally-code-votes failed");
    }
    let classification = get(&tally.values, "FINDINGS_CLASSIFICATION_TSV_FILE", "");
    record_classification(
        &context.options.review_tmpdir,
        context.options.round_num,
        &classification,
        &mut rows,
    );
    let tally_file = context
        .options
        .review_tmpdir
        .join("review-core-aggregator-exhaust-tally.env");
    emit_tally(
        context.options,
        context.runner,
        context.mode,
        &tally_file,
        &context.options.review_tmpdir.join("accepted-findings.md"),
        context.scout_status,
        context.dynamic_slots,
        context.static_slot_count,
        "review-core-aggregator-exhaust-emit.env",
    );
    flush_round_log(context.options, context.runner);
    rows.extend(common_rows(
        "aggregator-validation-exhausted",
        context.options.round_num,
        &context.options.review_tmpdir,
        context.panel_mode,
        context.panel_shape,
        Counts::default(),
        None,
        Some("aggregation-validation-exhausted"),
    ));
    if !classification.is_empty() {
        rows.push(row("FINDINGS_CLASSIFICATION_TSV_FILE", classification));
    }
    CoreResult { rc: 2, rows }
}

#[allow(clippy::too_many_lines)] // The tally, publish, and final KV sequence must remain adjacent for wire parity.
fn finish_vote<F>(
    context: &VoteContext<'_, F>,
    mut rows: Rows,
    tally_name: &str,
    emit_name: &str,
) -> CoreResult
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let map = match prepare_proposer_map(
        &context.options.review_tmpdir.join("findings.md"),
        &context.options.review_tmpdir.join("proposer-map.tsv"),
    ) {
        Ok(path) => path,
        Err(error) => {
            diagnostic(&format!(
                "→ review: proposer map preparation failed: {error}"
            ));
            return post_gate_failure(context, rows, "proposer-map-failed");
        }
    };
    progress_note(
        context.options,
        &format!("round {}: dispatching 3 voters", context.options.round_num),
    );
    let (voter_files, voter_tools) = dispatch_voters(context, &mut rows);
    progress_note(
        context.options,
        &format!("round {}: tallying votes", context.options.round_num),
    );
    let tally = tally(context, voter_files, voter_tools, Some(&map), tally_name);
    if tally.output.rc != 0 && get(&tally.values, "TALLY_STATUS", "").is_empty() {
        return post_gate_failure(context, rows, "tally-code-votes failed");
    }
    for key in [
        "VOTING_SKIPPED_WARNING",
        "YIELD_TSV_FILE",
        "VOTING_TALLY_FILE",
        "UNDER_QUORUM_COUNT",
        "UNDER_QUORUM_ITEMS",
        "PARSE_FAILED_COUNT",
        "VOTER_COUNT",
    ] {
        let value = get(&tally.values, key, "");
        if !value.is_empty() {
            rows.push(row(key, value));
        }
    }
    let classification = get(&tally.values, "FINDINGS_CLASSIFICATION_TSV_FILE", "");
    record_classification(
        &context.options.review_tmpdir,
        context.options.round_num,
        &classification,
        &mut rows,
    );
    let tally_file = PathBuf::from(get(
        &tally.values,
        "TALLY_FILE",
        path(&context.options.review_tmpdir.join("review-tally.env")),
    ));
    let accepted_file = PathBuf::from(get(
        &tally.values,
        "ACCEPTED_FINDINGS_FILE",
        path(&context.options.review_tmpdir.join("accepted-findings.md")),
    ));
    if get(&tally.values, "TALLY_STATUS", "") == "main-agent-vote-required" {
        let _ = write_text(
            &context.options.review_tmpdir.join("rejected-findings.md"),
            "",
        );
        progress_note(
            context.options,
            &format!(
                "round {}: post-fix checks running",
                context.options.round_num
            ),
        );
        emit_tally(
            context.options,
            context.runner,
            context.mode,
            &tally_file,
            &accepted_file,
            context.scout_status,
            context.dynamic_slots,
            context.static_slot_count,
            "review-core-main-agent-emit.env",
        );
        flush_round_log(context.options, context.runner);
        rows.extend(common_rows(
            "main-agent-vote-required",
            context.options.round_num,
            &context.options.review_tmpdir,
            context.panel_mode,
            context.panel_shape,
            Counts {
                oos: get(&tally.values, "OUT_OF_SCOPE_DRIFT_COUNT", "0"),
                ..Counts::default()
            },
            None,
            None,
        ));
        if !classification.is_empty() {
            rows.push(row("FINDINGS_CLASSIFICATION_TSV_FILE", classification));
        }
        return CoreResult { rc: 0, rows };
    }
    record_prune_round(context, &classification, &mut rows);
    let counts = Counts {
        accepted: get(&tally.values, "ACCEPTED_COUNT", "0"),
        rejected: get(&tally.values, "REJECTED_COUNT", "0"),
        exonerated: get(&tally.values, "EXONERATED_COUNT", "0"),
        neutral: get(&tally.values, "NEUTRAL_COUNT", "0"),
        oos: get(&tally.values, "OUT_OF_SCOPE_DRIFT_COUNT", "0"),
    };
    let accepted_total = [
        &counts.accepted,
        &counts.rejected,
        &counts.exonerated,
        &counts.neutral,
    ]
    .into_iter()
    .map(|value| parse_number(value, 0))
    .sum::<u64>();
    progress_note(
        context.options,
        &format!(
            "round {}: voting done {}/{} accepted",
            context.options.round_num, counts.accepted, accepted_total
        ),
    );
    progress_note(
        context.options,
        &format!(
            "round {}: post-fix checks running",
            context.options.round_num
        ),
    );
    emit_tally(
        context.options,
        context.runner,
        context.mode,
        &tally_file,
        &accepted_file,
        context.scout_status,
        context.dynamic_slots,
        context.static_slot_count,
        emit_name,
    );
    copy_to_parent(
        &context.options.review_tmpdir.join("rejected-findings.md"),
        "rejected-findings.md",
        &context.options.session_env_path,
    );
    copy_to_parent(
        &context.options.review_tmpdir.join("oos-accepted-review.md"),
        "oos-accepted-review.md",
        &context.options.session_env_path,
    );
    flush_round_log(context.options, context.runner);
    let accepted = parse_number(&counts.accepted, 0);
    let status = if context.mode == "diff" && accepted > 0 {
        if context.options.round_num >= 2 {
            "cap-reached"
        } else {
            "fix-required"
        }
    } else {
        "ok"
    };
    rows.extend(common_rows(
        status,
        context.options.round_num,
        &context.options.review_tmpdir,
        context.panel_mode,
        context.panel_shape,
        counts,
        Some(&accepted_file),
        None,
    ));
    rows.push(row("PANEL_TIER", context.panel_tier));
    rows.push(row("EFFECTIVE_ROUND_CAP", "2"));
    if !classification.is_empty() {
        rows.push(row("FINDINGS_CLASSIFICATION_TSV_FILE", classification));
    }
    CoreResult { rc: 0, rows }
}

fn dispatch_voters<F>(context: &VoteContext<'_, F>, rows: &mut Rows) -> (Vec<String>, Vec<String>)
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let mut args = strings(&[
        "--ballot-file",
        path(&context.options.review_tmpdir.join("findings.md")),
        "--review-tmpdir",
        path(&context.options.review_tmpdir),
        "--codex-available",
        &context.options.codex_available,
        "--cursor-available",
        &context.options.cursor_available,
        "--round-num",
        &context.options.round_num.to_string(),
        "--site",
        &context.options.site,
    ]);
    add_if(&mut args, "--tier", context.panel_tier);
    add_if(
        &mut args,
        "--session-env-path",
        &context.options.session_env_path,
    );
    add_if(&mut args, "--diff-file", context.diff_file);
    add_if(
        &mut args,
        "--plan-file",
        context.options.value("--plan-file"),
    );
    let output = call(context.runner, "agent", "dispatch-voters", args).unwrap_or_default();
    let _ = write_text(
        &context.options.review_tmpdir.join("review-core-voters.env"),
        &output.stdout,
    );
    let values = parse_kv(&output.stdout);
    let mut files = Vec::new();
    let mut tools = Vec::new();
    for (index, default_tool) in [
        (1, "codex-validity"),
        (2, "codex-plan-fidelity"),
        (3, "codex-pragmatism"),
    ] {
        let path_value = get(&values, &format!("VOTER_{index}_PATH"), "");
        let status = get(&values, &format!("VOTER_{index}_STATUS"), "");
        let reported_tool = get(&values, &format!("VOTER_{index}_TOOL"), "");
        let tool = if reported_tool.is_empty() {
            default_tool.to_owned()
        } else {
            reported_tool.clone()
        };
        tools.push(tool.clone());
        files.push(
            if !matches!(status.as_str(), "failed" | "skipped")
                && file_nonempty(Path::new(&path_value))
            {
                path_value
            } else {
                String::new()
            },
        );
        if !reported_tool.is_empty() {
            rows.push(row(&format!("VOTER_{index}_TOOL"), reported_tool));
        }
        if !status.is_empty() {
            rows.push(row(&format!("VOTER_{index}_STATUS"), status));
        }
    }
    (files, tools)
}

fn tally<F>(
    context: &VoteContext<'_, F>,
    voter_files: Vec<String>,
    voter_tools: Vec<String>,
    proposer_map: Option<&Path>,
    output_name: &str,
) -> TallyResult
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let mut args = strings(&[
        "--ballot-file",
        path(&context.options.review_tmpdir.join("findings.md")),
        "--review-tmpdir",
        path(&context.options.review_tmpdir),
        "--cursor-available",
        &context.options.cursor_available,
        "--codex-available",
        &context.options.codex_available,
        "--round-num",
        &context.options.round_num.to_string(),
    ]);
    if let Some(map_path) = proposer_map {
        add_if(&mut args, "--proposer-map-file", path(map_path));
    }
    add_if(
        &mut args,
        "--session-env-path",
        &context.options.session_env_path,
    );
    if file_nonempty(Path::new(context.scope_files)) {
        add_if(&mut args, "--scope-files", context.scope_files);
    }
    if file_exists(Path::new(context.options.value("--plan-file"))) {
        add_if(
            &mut args,
            "--plan-file",
            context.options.value("--plan-file"),
        );
    }
    if file_exists(Path::new(context.panel_manifest)) {
        add_if(&mut args, "--manifest-file", context.panel_manifest);
    }
    if file_exists(context.collector_results) {
        add_if(
            &mut args,
            "--collector-results-file",
            path(context.collector_results),
        );
    }
    if context.not_substantive != 0 {
        add_if(
            &mut args,
            "--not-substantive-count",
            &context.not_substantive.to_string(),
        );
    }
    args.push("--voter-files".to_owned());
    args.extend(voter_files);
    if !voter_tools.is_empty() {
        args.push("--voter-tools".to_owned());
        args.extend(voter_tools);
    }
    let output =
        call(context.runner, "review", "tally-code-votes", args).unwrap_or_else(|error| Output {
            rc: 1,
            stdout: String::new(),
            stderr: error,
        });
    let _ = write_text(
        &context.options.review_tmpdir.join(output_name),
        &output.stdout,
    );
    TallyResult {
        values: parse_kv(&output.stdout),
        output,
    }
}

#[allow(clippy::too_many_arguments)] // Each raw compatibility field maps directly to one nested emit flag.
fn emit_tally<F>(
    options: &CoreOptions,
    runner: &F,
    mode: &str,
    tally_file: &Path,
    accepted_file: &Path,
    scout_status: &str,
    dynamic_slots: &str,
    static_slot_count: &str,
    out_name: &str,
) where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let mut args = strings(&[
        "--tally-file",
        path(tally_file),
        "--accepted-findings-file",
        path(accepted_file),
        "--oos-file",
        path(&options.review_tmpdir.join("oos.md")),
        "--review-tmpdir",
        path(&options.review_tmpdir),
        "--round",
        &options.round_num.to_string(),
        "--mode",
        mode,
        "--scout-status",
        scout_status,
        "--dynamic-slots",
        dynamic_slots,
        "--static-slot-count",
        static_slot_count,
    ]);
    add_if(&mut args, "--session-env-path", &options.session_env_path);
    if let Ok(implement) = env::var("IMPLEMENT_TMPDIR") {
        add_if(&mut args, "--implement-tmpdir", &implement);
    }
    let output = call(runner, "review", "emit-tally", args).unwrap_or_default();
    for line in output.stderr.lines() {
        diagnostic(line);
    }
    let _ = write_text(&options.review_tmpdir.join(out_name), &output.stdout);
}

fn post_gate_failure<F>(context: &VoteContext<'_, F>, mut rows: Rows, reason: &str) -> CoreResult
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    flush_round_log(context.options, context.runner);
    rows.extend(common_rows(
        "panel-failed",
        context.options.round_num,
        &context.options.review_tmpdir,
        context.panel_mode,
        context.panel_shape,
        Counts::default(),
        None,
        Some(reason),
    ));
    CoreResult { rc: 2, rows }
}

fn failed_result(
    review_tmpdir: &Path,
    round_num: u64,
    panel_mode: &str,
    panel_shape: &str,
    reason: &str,
) -> CoreResult {
    CoreResult {
        rc: 2,
        rows: common_rows(
            "panel-failed",
            round_num,
            review_tmpdir,
            panel_mode,
            panel_shape,
            Counts::default(),
            None,
            Some(reason),
        ),
    }
}

fn diagnostic(message: &str) {
    eprintln!(
        "{}",
        SafeText::diagnostic(message)
            .as_str()
            .trim_end_matches('\n')
    );
}

#[derive(Default)]
struct Counts {
    accepted: String,
    rejected: String,
    exonerated: String,
    neutral: String,
    oos: String,
}

#[allow(clippy::too_many_arguments)] // The public core envelope keeps all stable fields visible at the construction boundary.
fn common_rows(
    status: &str,
    round: u64,
    review_tmpdir: &Path,
    panel_mode: &str,
    panel_shape: &str,
    counts: Counts,
    accepted_file: Option<&Path>,
    threshold_reason: Option<&str>,
) -> Rows {
    let mut rows = vec![
        row("REVIEW_CORE_STATUS", status),
        row("ROUND_NUM", round.to_string()),
        row("ACCEPTED_COUNT", empty_zero(counts.accepted)),
        row("REJECTED_COUNT", empty_zero(counts.rejected)),
        row("EXONERATED_COUNT", empty_zero(counts.exonerated)),
        row("NEUTRAL_COUNT", empty_zero(counts.neutral)),
        row("OUT_OF_SCOPE_DRIFT_COUNT", empty_zero(counts.oos)),
        row("FINDINGS_FILE", path(&review_tmpdir.join("findings.md"))),
        row(
            "ACCEPTED_FINDINGS_FILE",
            path(accepted_file.unwrap_or(&review_tmpdir.join("accepted-findings.md"))),
        ),
        row(
            "REJECTED_FINDINGS_FILE",
            path(&review_tmpdir.join("rejected-findings.md")),
        ),
        row("PANEL_MODE", panel_mode),
        row("PANEL_SHAPE", panel_shape),
    ];
    if status == "panel-failed" || threshold_reason.is_some() {
        rows.push(row("THRESHOLD_REASON", threshold_reason.unwrap_or("")));
    }
    rows
}

fn empty_zero(value: String) -> String {
    if value.is_empty() {
        "0".to_owned()
    } else {
        value
    }
}
fn row(key: &str, value: impl AsRef<str>) -> (String, String) {
    (key.to_owned(), value.as_ref().to_owned())
}
fn path(path: &Path) -> &str {
    path.to_str().unwrap_or("")
}
fn strings(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|part| (*part).to_owned()).collect()
}
fn add_if(arguments: &mut Vec<String>, flag: &str, value: &str) {
    if !value.is_empty() {
        arguments.push(flag.to_owned());
        arguments.push(value.to_owned());
    }
}
fn add_list_if(arguments: &mut Vec<String>, flag: &str, values: &[String]) {
    if !values.is_empty() {
        arguments.push(flag.to_owned());
        arguments.extend(values.iter().cloned());
    }
}
fn nonempty(first: &str, second: String) -> String {
    if first.is_empty() {
        second
    } else {
        first.to_owned()
    }
}
fn get(values: &BTreeMap<String, String>, key: &str, default: &str) -> String {
    values
        .get(key)
        .cloned()
        .unwrap_or_else(|| default.to_owned())
}
fn parse_number(value: &str, default: u64) -> u64 {
    decimal_number(value).unwrap_or(default)
}
fn decimal_number(value: &str) -> Option<u64> {
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse::<u64>().ok())
        .flatten()
}
fn split_paths(value: &str) -> Vec<String> {
    value.split_whitespace().map(str::to_owned).collect()
}
fn file_exists(path: &Path) -> bool {
    path.is_file()
}
fn file_nonempty(path: &Path) -> bool {
    file_exists(path)
        && fs::metadata(path)
            .map(|metadata| metadata.len() > 0)
            .unwrap_or(false)
}
fn read_text(path: &Path) -> String {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default()
}
fn write_text(path: &Path, text: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(path, text).map_err(|error| error.to_string())
}
fn append_text(path: &Path, text: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .and_then(|mut file| file.write_all(text.as_bytes()))
        .map_err(|error| error.to_string())
}
fn copy_checked(source: &Path, dest: &Path) -> Result<(), String> {
    fs::copy(source, dest)
        .map(|_| ())
        .map_err(|error| error.to_string())
}
fn parse_kv(text: &str) -> BTreeMap<String, String> {
    let mut values = BTreeMap::new();
    for line in text.lines() {
        if let Some((key, value)) = line.split_once('=')
            && !key.is_empty()
        {
            // `_kv_parse(..., skip_empty_key=True)` was the retired Python
            // reader. Its default duplicate policy is last-wins.
            values.insert(key.to_owned(), value.to_owned());
        }
    }
    values
}

fn call<F>(runner: &F, domain: &str, verb: &str, args: Vec<String>) -> Result<Output, String>
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let mut command = vec![domain.to_owned(), verb.to_owned()];
    command.extend(args);
    runner(&command)
}

fn ensure_prune_sidecars(review_tmpdir: &Path, round: u64) {
    let decision = review_tmpdir.join("prune-decision.env");
    if !file_exists(&decision) {
        let _ = write_text(
            &decision,
            &format!(
                "ROUND={round}\nPRUNE_ACTIVE=false\nPRUNE_STATUS=skipped\nPANEL_FULL=0\nELIGIBLE=0\nPRUNED_COUNT=0\nPRUNED_COMBOS=\nPANEL_PRUNED_EMPTY=false\n"
            ),
        );
    }
    let nit = review_tmpdir.join("prune-nit.env");
    if !file_exists(&nit) {
        let _ = write_text(
            &nit,
            "PRUNED_COUNT=0\nINSCOPE_REMAINING=0\nSTATUS=skipped\n",
        );
    }
}

fn flush_round_log<F>(options: &CoreOptions, runner: &F)
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    let Ok(implement) = env::var("IMPLEMENT_TMPDIR") else {
        return;
    };
    if options.run_id.is_empty() || !Path::new(&implement).is_dir() {
        return;
    }
    ensure_prune_sidecars(&options.review_tmpdir, options.round_num);
    let _ = call(
        runner,
        "run-log",
        "write-round",
        strings(&[
            "--log-root",
            path(&Path::new(&implement).join("larch-logs")),
            "--skill",
            "implement",
            "--run-id",
            &options.run_id,
            "--round",
            &options.round_num.to_string(),
            "--source-dir",
            path(&options.review_tmpdir),
        ]),
    );
}

fn log_review_core_issue(review_tmpdir: &Path, message: &str) {
    let _ = production_runner(&strings(&[
        "execution-issues",
        "append",
        "--log",
        path(&review_tmpdir.join("execution-issues.md")),
        "--category",
        "Warnings",
        "--entry",
        &format!("- REVIEW CORE WARNING: {message}"),
        "--report-status",
        "--spaced-section",
    ]));
}

fn copy_to_parent(file: &Path, name: &str, session_env: &str) {
    if session_env.is_empty() || !file_exists(file) {
        return;
    }
    if let Some(parent) = Path::new(session_env).parent() {
        let _ = copy_checked(file, &parent.join(name));
    }
}

fn parent_dir(session_env: &str, _review_tmpdir: &Path) -> Option<PathBuf> {
    if !session_env.is_empty() {
        return Path::new(session_env).parent().map(Path::to_path_buf);
    }
    env::var("IMPLEMENT_TMPDIR")
        .ok()
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn progress_note(options: &CoreOptions, text: &str) {
    let tmpdir = parent_dir(&options.session_env_path, &options.review_tmpdir);
    let Some(run_id) = owned_run_id(tmpdir.as_deref()) else {
        return;
    };
    let _ = production_runner(&strings(&[
        "progress",
        "note",
        "--repo-root",
        path(&env::current_dir().unwrap_or_else(|_| PathBuf::from("."))),
        "--run-id",
        &run_id,
        "--skill",
        "implement",
        "--step",
        "5",
        text,
    ]));
}

fn owned_run_id(tmpdir: Option<&Path>) -> Option<String> {
    let mut candidates = vec![env::var("LARCH_RUN_ID").unwrap_or_default()];
    if let Some(tmpdir) = tmpdir {
        for name in ["session-env.sh", "source-env.sh"] {
            for line in read_text(&tmpdir.join(name)).lines() {
                let value = line
                    .strip_prefix("LARCH_RUN_ID=")
                    .or_else(|| line.strip_prefix("export LARCH_RUN_ID="));
                if let Some(value) = value {
                    candidates.push(value.trim().trim_matches(['\"', '\'']).to_owned());
                }
            }
        }
    }
    candidates.into_iter().find(|value| {
        !value.is_empty()
            && value.len() <= 128
            && !matches!(value.as_str(), "." | ".." | "current")
            && value.chars().all(|character| {
                character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
            })
    })
}

fn epoch_seconds() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |duration| duration.as_secs_f64())
}

fn record_reviewer_collect(_review_tmpdir: &Path, round: u64, start: f64, end: f64) {
    let Some(ledger) = timing_ledger() else {
        return;
    };
    if !ledger.is_file() {
        return;
    }
    let _ = production_runner(&strings(&[
        "timing",
        "record-vendor-task",
        "--ledger",
        path(&ledger),
        "--vendor",
        "claude",
        "--task-kind",
        "reviewer-collect",
        "--start-s",
        &start.to_string(),
        "--end-s",
        &end.to_string(),
        "--output",
        &format!("reviewer-collect-round-{round}.out"),
        "--exit-code",
        "0",
        "--status",
        "complete",
    ]));
}

fn timing_ledger() -> Option<PathBuf> {
    let declared = env::var("LARCH_TIMING_LEDGER").unwrap_or_default();
    if !declared.is_empty() {
        let path = PathBuf::from(declared);
        if !path
            .components()
            .any(|component| component.as_os_str() == "..")
            && !path.is_symlink()
        {
            return Some(path);
        }
    }
    for key in [
        "IMPLEMENT_TMPDIR",
        "SESSION_ENV_PATH",
        "DESIGN_TMPDIR",
        "REVIEW_TMPDIR",
    ] {
        let value = env::var(key).unwrap_or_default();
        if value.is_empty() {
            continue;
        }
        let root = if key == "SESSION_ENV_PATH" {
            Path::new(&value).parent().map(Path::to_path_buf)
        } else {
            Some(PathBuf::from(value))
        };
        if let Some(root) = root.filter(|root| root.is_dir()) {
            return Some(root.join("timing-ledger.tsv"));
        }
    }
    None
}

fn snapshot_oos(review_tmpdir: &Path, stem: &str, session_env: &str) {
    for name in ["oos-accepted-review.md", "accumulated-oos.md"] {
        let source = review_tmpdir.join(name);
        let dest = review_tmpdir.join(format!("{stem}.{name}.before.md"));
        if file_exists(&source) {
            let _ = copy_checked(&source, &dest);
        } else {
            let _ = fs::remove_file(&dest);
        }
    }
    if let Some(parent) = parent_dir(session_env, review_tmpdir) {
        for name in ["oos-accepted-review.md", "accumulated-oos.md"] {
            let source = parent.join(name);
            let dest = review_tmpdir.join(format!("{stem}.parent-{name}.before.md"));
            if file_exists(&source) {
                let _ = copy_checked(&source, &dest);
            } else {
                let _ = fs::remove_file(&dest);
            }
        }
    }
}

fn restore_oos(review_tmpdir: &Path, stem: &str, session_env: &str) {
    for name in ["oos-accepted-review.md", "accumulated-oos.md"] {
        let source = review_tmpdir.join(format!("{stem}.{name}.before.md"));
        let dest = review_tmpdir.join(name);
        if file_exists(&source) {
            let _ = copy_checked(&source, &dest);
        } else if name == "oos-accepted-review.md" {
            let _ = write_text(&dest, "");
        }
    }
    if let Some(parent) = parent_dir(session_env, review_tmpdir) {
        for name in ["oos-accepted-review.md", "accumulated-oos.md"] {
            let source = review_tmpdir.join(format!("{stem}.parent-{name}.before.md"));
            if file_exists(&source) {
                let _ = copy_checked(&source, &parent.join(name));
            }
        }
    }
}

fn append_threshold_metadata(path: &Path, dispatch: &BTreeMap<String, String>) {
    let mut text = String::new();
    for key in ["STRAGGLER_DROPPED_COUNT", "WATERFALL_WARN"] {
        if let Some(value) = dispatch.get(key).filter(|value| !value.is_empty()) {
            let _ = writeln!(text, "{key}={value}");
        }
    }
    if !text.is_empty() {
        let _ = append_text(path, &text);
    }
}
fn collector_success_count(path: &Path) -> usize {
    parse_legacy_collector_blocks(&read_text(path))
        .iter()
        .filter(|record| {
            matches!(
                record.get("STATUS").map(String::as_str),
                Some("OK" | "cap_hit")
            )
        })
        .count()
}
fn parseable_output_present(review_tmpdir: &Path) -> bool {
    ["findings.md", "oos.md"]
        .iter()
        .any(|name| file_nonempty(&review_tmpdir.join(name)))
}
fn protected_threshold_reason(reason: &str) -> bool {
    [
        "dispatch-panel",
        "no successful static reviewer",
        "tally-code-votes",
        "proposer-map",
        "findings-pre-aggregate",
        "aggregation-validation-exhausted",
    ]
    .iter()
    .any(|prefix| reason.starts_with(prefix))
}
fn rewrite_threshold(path: &Path, ok: &str, reason: &str) {
    let mut seen = BTreeSet::new();
    let mut output = Vec::new();
    for line in read_text(path).lines() {
        let replacement = if line.starts_with("THRESHOLD_OK=") {
            seen.insert("ok");
            Some(format!("THRESHOLD_OK={ok}"))
        } else if line.starts_with("THRESHOLD_REASON=") {
            seen.insert("reason");
            Some(format!("THRESHOLD_REASON={reason}"))
        } else if line.starts_with("COVERAGE_GATE_OK=") {
            seen.insert("coverage_ok");
            Some("COVERAGE_GATE_OK=false".to_owned())
        } else if line.starts_with("COVERAGE_GATE_REASON=") {
            seen.insert("coverage_reason");
            Some(format!("COVERAGE_GATE_REASON={reason}"))
        } else {
            None
        };
        output.push(replacement.unwrap_or_else(|| line.to_owned()));
    }
    for (key, line) in [
        ("ok", format!("THRESHOLD_OK={ok}")),
        ("reason", format!("THRESHOLD_REASON={reason}")),
        ("coverage_ok", "COVERAGE_GATE_OK=false".to_owned()),
        ("coverage_reason", format!("COVERAGE_GATE_REASON={reason}")),
    ] {
        if !seen.contains(key) {
            output.push(line);
        }
    }
    let _ = write_text(path, &(output.join("\n") + "\n"));
}

fn static_slug(file: &str) -> Option<String> {
    let base = normalize_output_base(file);
    if base == "codex-generalist-output.txt" {
        return Some("generalist".to_owned());
    }
    let regex = Regex::new(r"^(?:cursor|codex)-specialist-(.+)-output\.txt$")
        .expect("static specialist regex");
    regex
        .captures(&base)
        .and_then(|captures| captures.get(1).map(|capture| capture.as_str().to_owned()))
}
#[allow(clippy::too_many_lines)] // The legacy static-coverage policy stays contiguous for parity auditing.
fn static_coverage_reason(
    collector: &Path,
    manifest: &Path,
    outputs: &[String],
    dropped: &Path,
) -> Option<String> {
    let records = parse_legacy_collector_blocks(&read_text(collector));
    let mut success = BTreeSet::new();
    let mut collector_success = BTreeSet::new();
    let mut rejected = BTreeSet::new();
    let mut statuses: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for record in records {
        let file = record.get("REVIEWER_FILE").cloned().unwrap_or_default();
        let Some(slug) = static_slug(&file) else {
            continue;
        };
        let status = record.get("STATUS").cloned().unwrap_or_default();
        statuses
            .entry(slug.clone())
            .or_default()
            .push(status.clone());
        if matches!(status.as_str(), "OK" | "cap_hit") {
            collector_success.insert(slug.clone());
            success.insert(slug);
        } else {
            rejected.insert(normalize_output_base(&file));
        }
    }
    for output in outputs {
        if let Some(slug) = static_slug(output)
            && !rejected.contains(&normalize_output_base(output))
            && file_nonempty(Path::new(output))
            && !read_text(Path::new(output))
                .lines()
                .any(|line| line == "STATUS=NOT_SUBSTANTIVE")
        {
            success.insert(slug);
        }
    }
    let mut expected = BTreeSet::new();
    if file_exists(manifest) {
        for line in read_text(manifest).lines() {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(line)
                && value.get("agent").is_some()
                && let Some(slug) = value
                    .get("output")
                    .and_then(serde_json::Value::as_str)
                    .and_then(static_slug)
            {
                expected.insert(slug);
            }
        }
    } else {
        expected.extend([
            "correctness".to_owned(),
            "edge-cases".to_owned(),
            "testing".to_owned(),
        ]);
    }
    let mut straggler = BTreeSet::new();
    let mut non_straggler = BTreeSet::new();
    let mut absent = BTreeSet::new();
    let mut other_failure = BTreeSet::new();
    for line in read_text(dropped).lines() {
        let fields = line.split('\t').collect::<Vec<_>>();
        if fields.len() < 3
            || fields[0].starts_with("dyn-")
            || !matches!(fields[1], "codex" | "cursor")
        {
            continue;
        }
        match fields[2] {
            "straggler-dropped" => {
                straggler.insert(fields[0].to_owned());
            }
            "tool-absent" => {
                absent.insert(fields[0].to_owned());
                non_straggler.insert(fields[0].to_owned());
            }
            _ => {
                non_straggler.insert(fields[0].to_owned());
                other_failure.insert(fields[0].to_owned());
            }
        }
    }
    let mut excused = straggler
        .difference(&non_straggler)
        .cloned()
        .collect::<BTreeSet<_>>();
    for slug in absent {
        if collector_success.contains(&slug) && !other_failure.contains(&slug) {
            excused.insert(slug);
        }
    }
    let covered_not_substantive = statuses
        .into_iter()
        .filter_map(|(slug, statuses)| {
            (!statuses.is_empty() && statuses.iter().all(|status| status == "NOT_SUBSTANTIVE"))
                .then_some(slug)
        })
        .collect::<BTreeSet<_>>();
    let missing = expected
        .difference(&success)
        .filter(|slug| !covered_not_substantive.contains(*slug) && !excused.contains(*slug))
        .cloned()
        .collect::<Vec<_>>();
    (!missing.is_empty()).then(|| {
        format!(
            "no successful static reviewer for archetype(s): {}",
            missing.join(",")
        )
    })
}

fn ballot_block_count(path: &Path) -> Option<usize> {
    fs::read_to_string(path).ok().map(|text| {
        text.lines()
            .filter(|line| {
                Regex::new(r"^### (?:FINDING|OOS)_[0-9]+:")
                    .expect("ballot heading regex")
                    .is_match(line)
            })
            .count()
    })
}
fn record_classification(review_tmpdir: &Path, round: u64, file: &str, rows: &mut Rows) {
    if file.is_empty() {
        return;
    }
    let map = review_tmpdir.join("findings-classification-round-map.env");
    let round_key = format!("FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_{round}");
    let existing = read_text(&map)
        .lines()
        .filter(|line| {
            !line.starts_with("FINDINGS_CLASSIFICATION_TSV_FILE=")
                && !line.starts_with(&(round_key.clone() + "="))
        })
        .collect::<Vec<_>>()
        .join("\n");
    let prefix = (!existing.is_empty())
        .then_some(format!("{existing}\n"))
        .unwrap_or_default();
    let _ = write_text(
        &map,
        &format!("{prefix}FINDINGS_CLASSIFICATION_TSV_FILE={file}\n{round_key}={file}\n"),
    );
    rows.push(row("FINDINGS_CLASSIFICATION_TSV_FILE", file));
    rows.push(row(&round_key, file));
}
fn record_prune_round<F>(context: &VoteContext<'_, F>, classification: &str, rows: &mut Rows)
where
    F: Fn(&[String]) -> Result<Output, String>,
{
    if context.options.prune_ledger.is_empty()
        || context.panel_manifest.is_empty()
        || classification.is_empty()
        || !file_exists(Path::new(context.panel_manifest))
        || !file_exists(Path::new(classification))
    {
        return;
    }
    let output = call(
        context.runner,
        "review",
        "reviewer-prune",
        strings(&[
            "record",
            "--ledger",
            &context.options.prune_ledger,
            "--round",
            &context.options.round_num.to_string(),
            "--manifest",
            context.panel_manifest,
            "--classification",
            classification,
        ]),
    );
    if let Ok(output) = output
        && output.rc != 0
    {
        rows.push(row(
            "WARN",
            format!(
                "reviewer-prune record failed for round {}: {}",
                context.options.round_num,
                output.stderr.trim()
            ),
        ));
    }
}

fn prepare_proposer_map(ballot: &Path, map: &Path) -> Result<PathBuf, String> {
    let text = fs::read(ballot)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| error.to_string())?;
    let blocks = parse_blocks(&text, review::BoundaryMode::ItemHeading);
    if blocks.is_empty() {
        return Err("ballot has no canonical items".to_owned());
    }
    let reviewer = Regex::new(r"^(?P<prefix>[\s-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)\s*:\s*)(?P<value>.*?)(?P<trailing>[ \t]*)$").expect("reviewer attribution regex");
    let mut entries = Vec::new();
    let mut seen = BTreeSet::new();
    for block in &blocks {
        if !seen.insert(block.item_id.clone()) {
            return Err(format!("duplicate ballot heading {}", block.item_id));
        }
        let Some(line) = block.block.lines().find(|line| reviewer.is_match(line)) else {
            return Err(format!(
                "ballot item {} has missing reviewer attribution",
                block.item_id
            ));
        };
        let captures = reviewer.captures(line).expect("matched reviewer capture");
        let value = captures
            .name("value")
            .map_or("", |value| value.as_str())
            .replace('*', "")
            .trim()
            .to_owned();
        if value.is_empty() || value.eq_ignore_ascii_case("anonymous") {
            return Err(format!(
                "ballot item {} has missing or neutral reviewer attribution",
                block.item_id
            ));
        }
        entries.push((block.item_id.clone(), value, line.to_owned()));
    }
    let neutral = neutralize_reviewer(&text, &reviewer);
    let mut rendered = format!(
        "# attributed_ballot_sha256={:x}\n# neutral_ballot_sha256={:x}\nitem_id\treviewer\treviewer_line\n",
        Sha256::digest(text.as_bytes()),
        Sha256::digest(neutral.as_bytes())
    );
    for (id, reviewer, line) in entries {
        let _ = writeln!(
            rendered,
            "{id}\t{}\t{}",
            safe_tsv(&reviewer),
            safe_tsv(&line)
        );
    }
    atomic_write(map, &rendered)?;
    write_text(ballot, &neutral)?;
    Ok(map.to_path_buf())
}
fn safe_tsv(value: &str) -> String {
    Regex::new(r"[\t\r\n]+")
        .expect("tsv whitespace regex")
        .replace_all(value, " ")
        .trim()
        .to_owned()
}
fn neutralize_reviewer(text: &str, reviewer: &Regex) -> String {
    let blocks = parse_blocks(text, review::BoundaryMode::ItemHeading);
    let mut out = String::new();
    let mut cursor = 0;
    for block in blocks {
        let start = byte_offset(text, block.start);
        let end = byte_offset(text, block.end);
        out.push_str(&text[cursor..start]);
        out.push_str(&neutralize_block(&block.block, reviewer));
        cursor = end;
    }
    out.push_str(&text[cursor..]);
    out
}
fn neutralize_block(block: &str, reviewer: &Regex) -> String {
    let mut out = String::new();
    let mut attributed = false;
    for raw in block.split_inclusive('\n') {
        let line = raw.strip_suffix('\n').unwrap_or(raw);
        if !attributed && let Some(captures) = reviewer.captures(line) {
            out.push_str(captures.name("prefix").map_or("", |value| value.as_str()));
            out.push_str("anonymous");
            out.push_str(captures.name("trailing").map_or("", |value| value.as_str()));
            if raw.ends_with('\n') {
                out.push('\n');
            }
            attributed = true;
            continue;
        }
        out.push_str(raw);
    }
    out
}
fn byte_offset(text: &str, character_offset: usize) -> usize {
    text.char_indices()
        .nth(character_offset)
        .map_or(text.len(), |(offset, _)| offset)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use tempfile::TempDir;

    #[test]
    fn core_rejects_invalid_tier_before_spawning_a_phase() {
        let args = [
            "--mode",
            "diff",
            "--output-dir",
            "/tmp/review",
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
            "--tier",
            "invalid",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert!(parse_core_options(&args).is_none());
    }

    #[test]
    fn core_rejects_non_decimal_round_numbers() {
        let args = [
            "--mode",
            "diff",
            "--output-dir",
            "/tmp/review",
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
            "--round-num",
            "+2",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert!(parse_core_options(&args).is_none());
    }

    #[test]
    fn core_kv_reader_preserves_legacy_last_value_and_skips_empty_keys() {
        let values = parse_kv("MODE=first\n=ignored\nMODE=last\n");
        assert_eq!(values.get("MODE").map(String::as_str), Some("last"));
        assert!(!values.contains_key(""));
    }

    #[test]
    fn core_keeps_empty_output_dir_current_directory_compatibility() {
        let args = [
            "--mode",
            "diff",
            "--output-dir",
            "",
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(
            parse_core_options(&args)
                .expect("valid arguments")
                .review_tmpdir,
            PathBuf::from(".")
        );
    }

    #[test]
    fn core_description_empty_short_circuits_after_gather() {
        let sandbox = TempDir::new().expect("sandbox");
        let args = [
            "--mode",
            "description",
            "--output-dir",
            sandbox.path().to_str().expect("utf8"),
            "--codex-available",
            "true",
            "--cursor-available",
            "false",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        let options = parse_core_options(&args).expect("valid arguments");
        let result = run_core_with(&options, &|command| {
            assert_eq!(command[0..2], ["review", "gather-context"]);
            Ok(Output {
                rc: 0,
                stdout: "MODE=description\nSCOPE_FILES_COUNT=0\n".to_owned(),
                stderr: String::new(),
            })
        });
        assert_eq!(result.rc, 0);
        assert!(
            result
                .rows
                .iter()
                .any(|(key, value)| key == "REVIEW_CORE_STATUS" && value == "zero-findings")
        );
    }

    #[test]
    fn core_dispatch_failure_preserves_the_failure_short_circuit() {
        let sandbox = TempDir::new().expect("sandbox");
        let args = [
            "--mode",
            "diff",
            "--output-dir",
            sandbox.path().to_str().expect("utf8"),
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        let options = parse_core_options(&args).expect("valid arguments");
        let calls = RefCell::new(Vec::new());
        let result = run_core_with(&options, &|command| {
            calls.borrow_mut().push(command[1].clone());
            Ok(match command[1].as_str() {
                "gather-context" => Output {
                    rc: 0,
                    stdout: "MODE=diff\n".to_owned(),
                    stderr: String::new(),
                },
                "dispatch-panel" => Output {
                    rc: 3,
                    stdout: "DISPATCH_OK=false\n".to_owned(),
                    stderr: String::new(),
                },
                other => panic!("unexpected phase: {other}"),
            })
        });
        assert_eq!(result.rc, 2);
        assert_eq!(calls.into_inner(), ["gather-context", "dispatch-panel"]);
        assert!(
            result
                .rows
                .iter()
                .any(|(key, value)| key == "REVIEW_CORE_STATUS" && value == "panel-failed")
        );
        assert!(sandbox.path().join("prune-decision.env").is_file());
    }

    #[test]
    fn core_pruned_panel_short_circuits_before_collection() {
        let sandbox = TempDir::new().expect("sandbox");
        let args = [
            "--mode",
            "diff",
            "--output-dir",
            sandbox.path().to_str().expect("utf8"),
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        let options = parse_core_options(&args).expect("valid arguments");
        let calls = RefCell::new(Vec::new());
        let result = run_core_with(&options, &|command| {
            calls.borrow_mut().push(command[1].clone());
            Ok(match command[1].as_str() {
                "gather-context" => Output {
                    rc: 0,
                    stdout: "MODE=diff\n".to_owned(),
                    stderr: String::new(),
                },
                "dispatch-panel" => Output {
                    rc: 0,
                    stdout: concat!(
                        "PANEL_MODE=normal\n",
                        "PANEL_SHAPE=hard\n",
                        "PANEL_PRUNED_EMPTY=true\n",
                        "PRUNE_STATUS=pruned-empty\n",
                        "SCOUT_STATUS=na\n",
                        "DYNAMIC_SLOTS=0\n"
                    )
                    .to_owned(),
                    stderr: String::new(),
                },
                other => panic!("unexpected phase: {other}"),
            })
        });
        assert_eq!(result.rc, 0);
        assert_eq!(calls.into_inner(), ["gather-context", "dispatch-panel"]);
        assert!(
            result
                .rows
                .iter()
                .any(|(key, value)| key == "REVIEW_CORE_STATUS" && value == "prune-skipped")
        );
        assert!(sandbox.path().join("voting-tally.md").is_file());
    }

    #[test]
    fn core_full_round_preserves_the_recorded_phase_order_and_envelope() {
        let sandbox = TempDir::new().expect("sandbox");
        let args = [
            "--mode",
            "diff",
            "--output-dir",
            sandbox.path().to_str().expect("utf8"),
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        let options = parse_core_options(&args).expect("valid arguments");
        let calls = RefCell::new(Vec::new());
        let result = run_core_with(&options, &|command| {
            calls
                .borrow_mut()
                .push((command[0].clone(), command[1].clone()));
            let value = |flag: &str| {
                command
                    .iter()
                    .position(|argument| argument == flag)
                    .and_then(|index| command.get(index + 1))
                    .cloned()
                    .unwrap_or_default()
            };
            Ok(match (command[0].as_str(), command[1].as_str()) {
                ("review", "gather-context") => Output {
                    rc: 1,
                    stdout: "MODE=diff\n".to_owned(),
                    stderr: String::new(),
                },
                ("review", "dispatch-panel") => {
                    let manifest = sandbox.path().join("panel-manifest.ndjson");
                    write_text(&manifest, "").expect("manifest");
                    Output {
                        rc: 0,
                        stdout: format!(
                            "PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\nPANEL_MANIFEST={}\nSCOUT_STATUS=na\nDYNAMIC_SLOTS=0\nSTATIC_SLOT_COUNT=0\nPANEL_PRUNED_EMPTY=false\nSLOT_COUNT=0\nLAUNCHED_SLOTS=0\n",
                            path(&manifest),
                        ),
                        stderr: String::new(),
                    }
                }
                ("review", "collect-findings") => {
                    let findings = PathBuf::from(value("--findings-file"));
                    write_text(
                        &findings,
                        "### FINDING_1: correctness: source: detail\n- **Reviewer(s)**: codex-specialist\n- **Concern**: concrete\n",
                    )
                    .expect("findings");
                    write_text(
                        &findings
                            .parent()
                            .expect("parent")
                            .join("collector-results.env"),
                        "REVIEWER_FILE=none\nSTATUS=OK\n",
                    )
                    .expect("collector results");
                    Output {
                        rc: 0,
                        stdout: "FINDINGS_COUNT=1\n".to_owned(),
                        stderr: String::new(),
                    }
                }
                ("review", "check-reviewer-failure-threshold") => Output {
                    rc: 0,
                    stdout: "THRESHOLD_OK=true\nTHRESHOLD_REASON=\nNOT_SUBSTANTIVE_SLOTS=0\n"
                        .to_owned(),
                    stderr: String::new(),
                },
                ("review", "prune-nit-findings") => Output {
                    rc: 0,
                    stdout: "PRUNED_COUNT=0\nINSCOPE_REMAINING=1\nSTATUS=ok\n".to_owned(),
                    stderr: String::new(),
                },
                ("review", "aggregate-findings") => Output {
                    rc: 0,
                    stdout: "REASON=ok\nMERGED_COUNT=1\n".to_owned(),
                    stderr: String::new(),
                },
                ("agent", "dispatch-voters") => {
                    let review = PathBuf::from(value("--review-tmpdir"));
                    let mut rows = Vec::new();
                    for (index, tool) in
                        ["codex-validity", "codex-plan-fidelity", "codex-pragmatism"]
                            .into_iter()
                            .enumerate()
                    {
                        let voter = review.join(format!("voter-{index}.txt"));
                        write_text(&voter, "vote").expect("voter");
                        let number = index + 1;
                        rows.push(format!("VOTER_{number}_PATH={}", path(&voter)));
                        rows.push(format!("VOTER_{number}_STATUS=complete"));
                        rows.push(format!("VOTER_{number}_TOOL={tool}"));
                    }
                    Output {
                        rc: 0,
                        stdout: rows.join("\n") + "\n",
                        stderr: String::new(),
                    }
                }
                ("review", "tally-code-votes") => {
                    let review = PathBuf::from(value("--review-tmpdir"));
                    let tally = review.join("review-tally.env");
                    let accepted = review.join("accepted-findings-custom.md");
                    write_text(&tally, "").expect("tally");
                    write_text(&accepted, "accepted").expect("accepted");
                    Output {
                        rc: 0,
                        stdout: format!(
                            "TALLY_STATUS=ok\nACCEPTED_COUNT=1\nREJECTED_COUNT=2\nEXONERATED_COUNT=3\nNEUTRAL_COUNT=4\nOUT_OF_SCOPE_DRIFT_COUNT=5\nTALLY_FILE={}\nACCEPTED_FINDINGS_FILE={}\n",
                            path(&tally),
                            path(&accepted),
                        ),
                        stderr: String::new(),
                    }
                }
                ("review", "emit-tally") => Output::default(),
                other => panic!("unexpected phase: {other:?}"),
            })
        });
        assert_eq!(
            calls.into_inner(),
            [
                ("review".to_owned(), "gather-context".to_owned()),
                ("review".to_owned(), "dispatch-panel".to_owned()),
                ("review".to_owned(), "collect-findings".to_owned()),
                (
                    "review".to_owned(),
                    "check-reviewer-failure-threshold".to_owned()
                ),
                ("review".to_owned(), "prune-nit-findings".to_owned()),
                ("review".to_owned(), "aggregate-findings".to_owned()),
                ("review".to_owned(), "prune-nit-findings".to_owned()),
                ("agent".to_owned(), "dispatch-voters".to_owned()),
                ("review".to_owned(), "tally-code-votes".to_owned()),
                ("review".to_owned(), "emit-tally".to_owned()),
            ]
        );
        assert_eq!(result.rc, 0);
        assert!(
            result
                .rows
                .contains(&row("REVIEW_CORE_STATUS", "fix-required"))
        );
        assert!(result.rows.contains(&row("ACCEPTED_COUNT", "1")));
        assert!(result.rows.contains(&row("OUT_OF_SCOPE_DRIFT_COUNT", "5")));
        assert!(result.rows.contains(&row("PANEL_TIER", "MODERATE")));
        assert!(result.rows.contains(&row(
            "ACCEPTED_FINDINGS_FILE",
            path(&sandbox.path().join("accepted-findings-custom.md"))
        )));
        assert!(
            read_text(&sandbox.path().join("review-core-threshold.env"))
                .contains("COVERAGE_GATE_REASON=static reviewer coverage satisfied")
        );
    }

    #[test]
    fn static_coverage_uses_the_manifest_as_the_expected_slot_source() {
        let sandbox = TempDir::new().expect("sandbox");
        let manifest = sandbox.path().join("panel-manifest.ndjson");
        write_text(&manifest, "").expect("manifest");
        assert_eq!(
            static_coverage_reason(
                &sandbox.path().join("collector-results.env"),
                &manifest,
                &[],
                &sandbox.path().join("dropped-slots.tsv"),
            ),
            None
        );
    }

    #[test]
    fn proposer_sidecar_is_bound_to_neutral_ballot() {
        let sandbox = TempDir::new().expect("sandbox");
        let ballot = sandbox.path().join("findings.md");
        write_text(
            &ballot,
            "### FINDING_1: title\n\n- **Reviewer(s)**: codex-reviewer\n- **Concern**: concrete\n",
        )
        .expect("ballot");
        let map = sandbox.path().join("proposer-map.tsv");
        prepare_proposer_map(&ballot, &map).expect("prepare map");
        assert!(read_text(&ballot).contains("anonymous"));
        let map_text = read_text(&map);
        assert!(map_text.contains("# neutral_ballot_sha256="));
        assert!(map_text.contains("FINDING_1\tcodex-reviewer"));
    }

    #[test]
    fn proposer_neutralization_does_not_treat_fenced_headings_as_ballot_items() {
        let reviewer = Regex::new(r"^(?P<prefix>[\s-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)\s*:\s*)(?P<value>.*?)(?P<trailing>[ \t]*)$").expect("regex");
        let ballot = r#"### FINDING_1: title
- **Reviewer**: first-reviewer
```markdown
### FINDING_2: illustrative heading
- **Reviewer**: fenced-reviewer
```
"#;
        let neutral = neutralize_reviewer(ballot, &reviewer);
        assert!(neutral.contains("- **Reviewer**: anonymous"));
        assert!(neutral.contains("- **Reviewer**: fenced-reviewer"));
    }

    #[test]
    fn proposer_sidecar_rejects_duplicate_ballot_headings() {
        let sandbox = TempDir::new().expect("sandbox");
        let ballot = sandbox.path().join("findings.md");
        write_text(
            &ballot,
            "### FINDING_1: first\n- **Reviewer**: alpha\n\n### FINDING_1: duplicate\n- **Reviewer**: beta\n",
        )
        .expect("ballot");
        let error = prepare_proposer_map(&ballot, &sandbox.path().join("proposer-map.tsv"))
            .expect_err("duplicate headings fail closed");
        assert_eq!(error, "duplicate ballot heading FINDING_1");
    }
}
