//! Atomic checkpoint, refresh, transcript, and terminal-snapshot orchestration.
//!
//! The four public selectors in this module own the mutable run-log flush. Token
//! reports, difficulty records, and timing reports render in process, while the
//! Rust owner performs report rendering, batch staging, and every manifest
//! transition.
#![allow(clippy::possible_missing_else)] // Compact independent phases are sequential, not branches.
use std::{
    collections::BTreeMap, env, ffi::OsString, fs, path::{Path, PathBuf}, process::ExitCode,
};

use larch_adapters::{
    run_log_manifest::{ManifestStore, utc_now}, stall_recovery::normalize_outcome,
}; use larch_core::{
    ManifestDocument, ManifestRecord, ManifestUpdate, ManifestV2Seed, RecordLabels,
    RunLogLayout, RunLogSlug, emit_kv, is_terminal_merge_result,
    parse_preterminal_outcome_label, redact, render_session_transcript,
}; use serde_json::Value; use sha2::{Digest as _, Sha256}; use tempfile::NamedTempFile;
use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags},
    execution_issue_commands::write_execution_issue_records,
    python_verb::plugin_root_directory,
    run_log_commands::resolve_log_root,
    run_log_entry_commands::{
        append_execution_issue, effort_level, main_model_for_source, plugin_version, read_lossy,
        stage_append_batch, stage_replace_batch, write_run_log_file,
    },
};
const RC_INTERNAL: u8 = 1; const RC_USAGE: u8 = 2;

#[derive(Clone, Copy, Eq, PartialEq)]
enum FlushMode {
    Checkpoint, Refresh,
}
struct FlushContext {
    tmpdir: PathBuf, log_root: PathBuf, run_id: String, state_file: Option<PathBuf>,
    repo_root: Option<PathBuf>, no_logs_commit: bool, merge_result: String, forked: bool,
    stall_tracking: bool, stall_step: String, pr_number: String, source_file: String,
    token_session_id: String, timing_ledger: String,
}

impl FlushContext {
    fn run_dir(&self) -> PathBuf {
        self.log_root.join("implement").join(&self.run_id)
    }

    fn issue_log(&self) -> PathBuf {
        self.tmpdir.join("execution-issues.md")
    }
}

struct TranscriptOutcome {
    status: String, source_configured: bool, artifact_present: bool, omission_recorded: bool,
}

impl TranscriptOutcome {
    fn terminal_ok(&self) -> bool {
        if self.source_configured {
            matches!(
                self.status.as_str(), "captured" | "suppressed-no-logs-commit"
            )
        } else {
            self.artifact_present || self.omission_recorded
        }
    }
}

/// Refresh recoverable local artifacts at a commit-tail checkpoint.
#[must_use]
pub fn checkpoint(arguments: &[OsString]) -> ExitCode {
    if let Some(argument) = arguments.first() {
        eprintln!(
            "python3 python/cli.py run-log checkpoint: unknown argument: {}",
            argument.to_string_lossy()
        ); return ExitCode::SUCCESS;
    } let Some(tmpdir) = env::var_os("IMPLEMENT_TMPDIR").filter(|value| !value.is_empty()) else {
        return ExitCode::SUCCESS;
    }; if env::var("LARCH_NO_LOGS_COMMIT").is_ok_and(|value| value == "true") {
        return ExitCode::SUCCESS;
    } let tmpdir = PathBuf::from(tmpdir); let session_id = tmpdir.join("session-id");
    if !session_id.exists() || tmpdir.join("post-merge-sentinel").exists() {
        return ExitCode::SUCCESS;
    } let run_id = read_lossy(&session_id)
        .unwrap_or_default() .trim() .to_owned();
    if RunLogSlug::parse(&run_id).is_err() {
        return ExitCode::SUCCESS;
    } let context = context_from_values(
        tmpdir, run_id, None, env::current_dir().ok(), false, "", "", "", "", "",
    ); match stage_checkpoint(&context, FlushMode::Checkpoint, false) {
        Ok(_transcript) => ExitCode::SUCCESS, Err(message) => {
            eprintln!(
                "WARN: run-log checkpoint failed: {}", one_line(&message, 1000)
            ); ExitCode::from(RC_INTERNAL)
        }
    }
}

/// Render and stage a filtered session transcript.
#[must_use]
pub fn capture_transcript(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments, &[
            "--source-file", "--log-root", "--tmpdir", "--skill", "--run-id", "--no-logs-commit",
            "--execution-issues-log", "--warning-step-label", "--refresh-mode", "--defer-commit",
        ], &[], 0,
    ); if parsed.error().is_some()
        || required_text(&parsed, "--log-root").is_none()
        || required_text(&parsed, "--skill").is_none()
        || required_text(&parsed, "--run-id").is_none()
        || bool_option(&parsed, "--no-logs-commit", false).is_none()
        || bool_option(&parsed, "--refresh-mode", false).is_none()
        || bool_option(&parsed, "--defer-commit", false).is_none()
    {
        emit_kv("SESSION_TRANSCRIPT_STATUS", "usage-error"); return ExitCode::SUCCESS;
    } let raw_log_root = text(&parsed, "--log-root");
    let log_root = match resolve_log_root(&raw_log_root) {
        Ok(path) => canonicalize_with_missing_leaf(&path), Err(message) => {
            let issues = optional_path(&parsed, "--execution-issues-log");
            let step = nonempty_or(&parsed, "--warning-step-label", "7a");
            let outcome = transcript_failure(
                issues.as_deref(), &step, "write-failed",
                &format!("larch-log root resolution failed; transcript was not captured: {message}"),
                true, false,
            ); emit_kv("SESSION_TRANSCRIPT_STATUS", &outcome.status);
            return ExitCode::SUCCESS;
        }
    };
    let run_id = text(&parsed, "--run-id"); let skill = text(&parsed, "--skill");
    let issues = optional_path(&parsed, "--execution-issues-log");
    let step = nonempty_or(&parsed, "--warning-step-label", "7a");
    let outcome = capture_transcript_inner(
        &text(&parsed, "--source-file"), &log_root, optional_path(&parsed, "--tmpdir").as_deref(),
        &skill, &run_id, bool_option(&parsed, "--no-logs-commit", false).unwrap_or(false),
        issues.as_deref(), &step, bool_option(&parsed, "--refresh-mode", false).unwrap_or(false),
    ); emit_kv("SESSION_TRANSCRIPT_STATUS", &outcome.status); ExitCode::SUCCESS
}

/// Refresh the mutable implement run-log tree without publishing it.
#[must_use]
pub fn refresh(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments, &[
            "--state-file", "--implement-tmpdir", "--run-id", "--repo-root", "--no-logs-commit",
            "--merge-result", "--forked-target", "--stall-tracking", "--stall-step", "--pr-number",
            "--source-file", "--token-session-id", "--timing-ledger", "--postmerge",
            "--strict-final-report", "--render-reports",
        ], &[], 0,
    ); if parsed.error().is_some() {
        println!("REFRESH_COMMITTED=false REASON=usage-error"); return ExitCode::SUCCESS;
    } let tmpdir_text = nonempty_or_env(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    let tmpdir = PathBuf::from(tmpdir_text); let state_file =
        optional_path(&parsed, "--state-file").unwrap_or_else(|| tmpdir.join("finalize-state.sh"));
    let internal_context = parsed.value("--run-id").is_some();
    let state_selected = parsed.value("--state-file").is_some() || !internal_context;
    let state_present = state_selected && regular_file(&state_file);
    let explicit_run_id = text(&parsed, "--run-id");
    if !internal_context && !state_present {
        println!("REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed");
        return ExitCode::SUCCESS;
    } let postmerge = bool_value(&text(&parsed, "--postmerge")).unwrap_or(false);
    let run_id = if state_present { read_key(&state_file, "RUN_ID") } else { first_nonempty(&[
        explicit_run_id, read_key(&tmpdir.join("finalize-state.sh"), "RUN_ID"),
    ]) };
    let no_logs = if state_present && !postmerge {
        read_key(&state_file, "NO_LOGS_COMMIT") == "true"
    } else {
        bool_value(&text(&parsed, "--no-logs-commit")).unwrap_or(false)
    }; let merge_result = first_nonempty(&[
        text(&parsed, "--merge-result"), read_key(&state_file, "MERGE_RESULT"),
        read_key(&tmpdir.join("finalize-state.sh"), "MERGE_RESULT"),
    ]); if !postmerge {
        if run_id.is_empty() {
            println!("REFRESH_SKIPPED=true REASON=no-run-id"); return ExitCode::SUCCESS;
        } if RunLogSlug::parse(&run_id).is_err() {
            println!("REFRESH_SKIPPED=true REASON=invalid-run-id"); return ExitCode::SUCCESS;
        } if no_logs {
            println!("REFRESH_SKIPPED=true REASON=no-logs-commit"); return ExitCode::SUCCESS;
        } if is_terminal_merge_result(&merge_result)
            || (tmpdir.join("post-merge-sentinel").is_file() && merge_result.is_empty())
        {
            println!("REFRESH_SKIPPED=true REASON=post-merge"); return ExitCode::SUCCESS;
        }
    } if RunLogSlug::parse(&run_id).is_err() {
        println!("REFRESH_COMMITTED=false REASON=manifest-recovery-failed");
        return ExitCode::SUCCESS;
    } let context = context_from_parsed(
        &parsed, tmpdir, run_id, state_file, state_selected, state_present, no_logs, &merge_result,
    );
    let strict = bool_value(&text(&parsed, "--strict-final-report")).unwrap_or(false);
    let result = if postmerge {
        refresh_postmerge(
            &context, bool_value(&text(&parsed, "--render-reports")).unwrap_or(true),
        )
    } else {
        refresh_local(&context, strict)
    }; match result {
        Ok(()) => println!("REFRESH_COMMITTED=true"), Err(message) => {
            let reason = if !postmerge && message.starts_with("preterminal-outcome: ") {
                "preterminal-outcome"
            } else if postmerge && message.starts_with("post-merge-refresh: ") {
                if message.to_lowercase().contains("redaction") { "redaction-failed" }
                else { "post-merge-refresh-failed" }
            } else { "manifest-recovery-failed" };
            let detail = one_line(&message, 500); if detail.is_empty() {
                println!("REFRESH_COMMITTED=false REASON={reason}");
            } else {
                println!("REFRESH_COMMITTED=false REASON={reason} ERROR={detail}");
            }
        }
    } ExitCode::SUCCESS
}

/// Prepare the complete mutable snapshot immediately before publication.
#[must_use]
pub fn prepare_terminal_snapshot(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments, &[
            "--implement-tmpdir", "--run-id", "--repo-root", "--no-logs-commit",
        ], &[], 0,
    ); if parsed.error().is_some()
        || required_text(&parsed, "--implement-tmpdir").is_none()
        || required_text(&parsed, "--run-id").is_none()
        || bool_option(&parsed, "--no-logs-commit", false).is_none()
    {
        terminal_result(false, "usage-error"); return ExitCode::from(RC_USAGE);
    } let tmpdir = PathBuf::from(text(&parsed, "--implement-tmpdir")); if !tmpdir.is_absolute()
        || !tmpdir.is_dir() || tmpdir.is_symlink()
    {
        terminal_result(false, "invalid-implement-tmpdir"); return ExitCode::from(RC_USAGE);
    } let run_id = text(&parsed, "--run-id"); if RunLogSlug::parse(&run_id).is_err() {
        terminal_result(false, "terminal snapshot requires a valid run id");
        return ExitCode::from(RC_INTERNAL);
    } let state_file = tmpdir.join("finalize-state.sh"); let context = context_from_values(
        tmpdir, run_id, Some(state_file), optional_path(&parsed, "--repo-root"),
        bool_option(&parsed, "--no-logs-commit", false).unwrap_or(false), "", "", "", "", "",
    ); match terminal_snapshot(&context) {
        Ok(()) => {
            terminal_result(true, ""); ExitCode::SUCCESS
        } Err(message) => {
            let detail = one_line(&message, 1000); record_terminal_failure(&context, &detail);
            terminal_result(false, &detail); ExitCode::from(RC_INTERNAL)
        }
    }
}

fn terminal_result(ok: bool, error: &str) {
    emit_kv(
        "TERMINAL_SNAPSHOT_STATUS", if ok { "prepared" } else { "failed" },
    ); emit_kv("TERMINAL_SNAPSHOT_ERROR", error);
}

fn refresh_local(context: &FlushContext, strict: bool) -> Result<(), String> {
    ensure_manifest(context)?;
    let _transcript = stage_checkpoint(context, FlushMode::Refresh, strict)?;
    ensure_manifest(context)?; reconcile_manifest(context, false, true, true)
}

fn refresh_postmerge(context: &FlushContext, render_reports: bool) -> Result<(), String> {
    ensure_manifest(context)?;
    (|| {
        if render_reports {
            write_final_report(context, false, false, false)?;
            render_ledger_reports(context, false)?;
        } render_derived_reports(context)
    })().map_err(|error| format!("post-merge-refresh: {error}"))?;
    if regular_file(&context.run_dir().join("final-summary.md")) {
        reconcile_manifest(context, true, false, false)?;
    } let mut updates = Vec::<ManifestUpdate>::new();
    if is_terminal_merge_result(&context.merge_result) {
        updates.push(("status".to_owned(), Value::String("done".to_owned())));
    } if let Some(number) = positive_number(&context.pr_number) {
        updates.push(("pr_number".to_owned(), Value::from(number)));
    } update_manifest(context, &updates)
}

fn terminal_snapshot(context: &FlushContext) -> Result<(), String> {
    ensure_manifest(context)?;
    fs::create_dir_all(context.run_dir()).map_err(|error| error.to_string())?;
    refresh_difficulty(context); write_final_report(context, true, true, false)?;
    render_ledger_reports(context, true)?; render_derived_reports(context)?;
    stage_vendor_diagnostics(context, true)?; stage_outcomes(context, true)?;
    let transcript = capture_for_context(context, "18"); if !transcript.terminal_ok() {
        return Err(format!(
            "terminal transcript refresh failed: status={}; the prior staged transcript was retained when available",
            transcript.status
        ));
    } flush_execution_issues(context, "18", "execution-issues.md terminal snapshot", true)?;
    write_final_report(context, true, true, false)?; reconcile_manifest(context, false, false, false)?;
    ensure_manifest(context)?;
    let mut updates = vec![("steps_ran.step18".to_owned(), Value::Bool(true))];
    if context.stall_tracking {
        updates.push((
            "stalled_at_step".to_owned(), Value::String(if context.stall_step.is_empty() {
                "unknown".to_owned()
            } else {
                context.stall_step.clone()
            }),
        ));
    } update_manifest(context, &updates)?; verify_terminal_files(context, &transcript)
}

fn stage_checkpoint(
    context: &FlushContext, mode: FlushMode, strict: bool,
) -> Result<TranscriptOutcome, String> {
    fs::create_dir_all(context.run_dir()).map_err(|error| error.to_string())?;
    refresh_difficulty(context); if mode == FlushMode::Refresh {
        flush_execution_issues(
            context, "pre-push", "execution-issues.md pre-push refresh", false,
        )?; let final_result = write_final_report(context, strict, strict, true); if strict {
            final_result?; if !regular_file(&context.run_dir().join("final-summary.md")) {
                return Err("final-summary.md missing after final report write".to_owned());
            }
        } ensure_preterminal_summary_neutral(context)?;
        render_ledger_reports(context, false)?; render_derived_reports(context)?;
    } else {
        flush_execution_issues(
            context, "commit-tail", "execution-issues.md commit-tail", false,
        )?;
    } stage_vendor_diagnostics(context, false)?; stage_outcomes(context, false)?;
    if mode != FlushMode::Refresh {
        return Ok(TranscriptOutcome {
            status: "not-attempted".to_owned(), source_configured: false,
            artifact_present: regular_file(&context.run_dir().join("session-transcript.jsonl")),
            omission_recorded: false,
        });
    } let transcript = capture_for_context(context, "pre-push-refresh"); flush_execution_issues(
        context, "pre-push-post-transcript", "execution-issues.md post-transcript refresh", false,
    )?; let final_result = write_final_report(context, true, strict, true); if strict {
        final_result?;
    } ensure_preterminal_summary_neutral(context)?;
    if regular_file(&context.run_dir().join("final-summary.md")) {
        reconcile_manifest(context, false, false, true)?;
    } Ok(transcript)
}

#[allow(clippy::too_many_arguments)]
fn context_from_values(
    tmpdir: PathBuf, run_id: String, state_file: Option<PathBuf>, repo_root: Option<PathBuf>,
    no_logs_commit: bool, merge_result: &str, pr_number: &str, source_file: &str,
    token_session_id: &str, timing_ledger: &str,
) -> FlushContext {
    let tmpdir = fs::canonicalize(&tmpdir).unwrap_or(tmpdir);
    let state = state_file.as_deref(); let session = tmpdir.join("session-env.sh");
    let final_state = tmpdir.join("finalize-state.sh");
    let state_value = |key| state.map_or_else(String::new, |path| read_key(path, key));
    let resolved_merge_result = first_nonempty(&[
        merge_result.to_owned(), state_value("MERGE_RESULT"),
        read_key(&final_state, "MERGE_RESULT"),
    ]); let forked = state_value("FORKED_TARGET") == "true";
    let stall_tracking = state_value("STALL_TRACKING") == "true";
    let stall_step = state_value("STALL_STEP"); let resolved_pr_number = first_nonempty(&[
        state_value("PR_NUMBER"), pr_number.to_owned(), read_key(&final_state, "PR_NUMBER"),
    ]); FlushContext {
        log_root: tmpdir.join("larch-logs"), run_id, state_file, repo_root, no_logs_commit,
        merge_result: resolved_merge_result, forked, stall_tracking, stall_step,
        pr_number: resolved_pr_number, source_file: first_nonempty(&[
            source_file.to_owned(), read_key(&session, "LARCH_CLAUDE_SOURCE_FILE"),
            env::var("LARCH_CLAUDE_SOURCE_FILE").unwrap_or_default(),
        ]), token_session_id: first_nonempty(&[
            token_session_id.to_owned(), read_key(&session, "LARCH_TOKEN_SESSION_ID"),
            env::var("LARCH_TOKEN_SESSION_ID").unwrap_or_default(),
        ]), timing_ledger: first_nonempty(&[
            timing_ledger.to_owned(), read_key(&session, "LARCH_TIMING_LEDGER"),
            env::var("LARCH_TIMING_LEDGER").unwrap_or_default(),
        ]), tmpdir,
    }
}

#[allow(clippy::too_many_arguments)] // Mirrors the raw compatibility context boundary.
fn context_from_parsed(
    parsed: &ParsedCommandLine, tmpdir: PathBuf, run_id: String, state_file: PathBuf,
    state_selected: bool, state_present: bool, no_logs_commit: bool, merge_result: &str,
) -> FlushContext {
    let selected_state = state_selected.then_some(state_file); let mut context = context_from_values(
        tmpdir, run_id, selected_state,
        optional_path(parsed, "--repo-root").or_else(|| env::current_dir().ok()), no_logs_commit,
        merge_result, &text(parsed, "--pr-number"), &text(parsed, "--source-file"),
        &text(parsed, "--token-session-id"), &text(parsed, "--timing-ledger"),
    ); if !state_present {
        if let Some(value) = bool_value(&text(parsed, "--forked-target")) {
            context.forked = value;
        } if let Some(value) = bool_value(&text(parsed, "--stall-tracking")) {
            context.stall_tracking = value;
        } let stall_step = text(parsed, "--stall-step"); if !stall_step.is_empty() {
            context.stall_step = stall_step;
        }
    } context
}

fn ensure_manifest(context: &FlushContext) -> Result<ManifestRecord, String> {
    let path = context.run_dir().join("manifest.json"); if regular_file(&path)
        && let Ok(bytes) = fs::read(&path)
        && let Ok(record) = ManifestRecord::parse_bytes(&bytes) && record.run_id() == context.run_id
    {
        return Ok(record);
    } let mut steps = BTreeMap::new(); if context.run_dir().is_dir() {
        steps.insert("recovered".to_owned(), Value::Bool(true));
        if regular_file(&context.run_dir().join("execution-issues.ndjson")) {
            steps.insert("execution_issues".to_owned(), Value::Bool(true));
        } if regular_file(&context.run_dir().join("token-report.ndjson")) {
            steps.insert("token_report".to_owned(), Value::Bool(true));
        }
    } let mut extra = BTreeMap::new();
    extra.insert("status".to_owned(), Value::String("partial".to_owned())); extra.insert(
        "recovery_reason".to_owned(), Value::String("manifest-lost".to_owned()),
    ); let state_issue = context
        .state_file .as_deref() .map_or_else(String::new, |state| {
            first_nonempty(&[read_key(state, "ISSUE_NUMBER"), read_key(state, "ISSUE")])
        }); let issue = first_nonempty(&[
        state_issue, read_key(&context.tmpdir.join("parent-issue.md"), "ISSUE_NUMBER"),
        read_key(&context.tmpdir.join("parent-issue.md"), "ISSUE"),
    ]);
    if let Some(number) = positive_number(&issue) {
        extra.insert("issue_number".to_owned(), Value::from(number));
    } let document = ManifestDocument::synthesize_v2(ManifestV2Seed {
        skill: "implement".to_owned(), run_id: context.run_id.clone(), timestamp: utc_now(),
        larch_version: plugin_version(),
        main_model: main_model_for_source(
            (!context.source_file.is_empty()).then(|| Path::new(&context.source_file)),
        ),
        effort: effort_level(), steps_ran: steps, extra,
    }) .map_err(|error| error.to_string())?; write_run_log_file(&path, &document.canonical_json())?;
    ManifestRecord::parse_bytes(&fs::read(path).map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())
}

fn update_manifest(context: &FlushContext, updates: &[ManifestUpdate]) -> Result<(), String> {
    if updates.is_empty() {
        return Ok(());
    } let current = ensure_manifest(context)?; let pending = updates
        .iter() .filter(|(key, value)| !manifest_has_update(&current, key, value))
        .cloned() .collect::<Vec<_>>(); if pending.is_empty() {
        return Ok(());
    } fs::create_dir_all(&context.log_root).map_err(|error| error.to_string())?;
    let skill = RunLogSlug::parse("implement").map_err(|error| error.to_string())?;
    let run_id = RunLogSlug::parse(&context.run_id).map_err(|error| error.to_string())?;
    let layout = RunLogLayout::new(&context.log_root, skill, run_id);
    ManifestStore::open(&context.log_root)
        .and_then(|store| store.update(&layout, &pending, &utc_now())) .map(|_path| ())
        .map_err(|error| error.to_string())
}

fn manifest_has_update(record: &ManifestRecord, key: &str, value: &Value) -> bool {
    key.strip_prefix("steps_ran.").map_or_else(
        || if key == "status" {
            value.as_str() == Some(record.status())
        } else {
            record.reserved().get(key).or_else(|| record.extra().get(key)) == Some(value)
        },
        |step| record.steps_ran().get(step) == Some(value),
    )
}

fn reconcile_manifest(
    context: &FlushContext, postmerge: bool, include_step9_heuristic: bool,
    preterminal: bool,
) -> Result<(), String> {
    let record = ensure_manifest(context)?; let run_dir = context.run_dir(); let mut updates = vec![
        (
            "steps_ran.step8".to_owned(), Value::Bool(
                regular_file(&run_dir.join("final-summary.md"))
                    || regular_file(&run_dir.join("version-bump-reasoning.md")),
            ),
        ), (
            "steps_ran.step7a".to_owned(), Value::Bool(
                [
                    "token-report.json", "timing-report.json", "execution-issues.ndjson",
                    "session-transcript.jsonl",
                ] .iter() .any(|name| regular_file(&run_dir.join(name))),
            ),
        ),
    ]; if !regular_file(&run_dir.join("run-statistics.md")) {
        updates.push(("steps_ran.step9a1".to_owned(), Value::Bool(false)));
    } if include_step9_heuristic && let Some(value) = step9a1_heuristic(context, &record) {
        updates.push(("steps_ran.step9a1".to_owned(), Value::Bool(value)));
    } let outcome = if preterminal {
        preterminal_outcome(context)
    } else {
        normalized_outcome(context)
    }; if matches!(
        outcome.as_str(), "pr-created" | "pr-created-draft" | "shipping"
    ) {
        updates.push(("status".to_owned(), Value::String("in-progress".to_owned())));
    } if postmerge && is_terminal_merge_result(&context.merge_result) {
        updates.push(("status".to_owned(), Value::String("done".to_owned())));
    } if let Some(number) = positive_number(&context.pr_number) {
        updates.push(("pr_number".to_owned(), Value::from(number)));
    } update_manifest(context, &updates)
}

fn step9a1_heuristic(context: &FlushContext, manifest: &ManifestRecord) -> Option<bool> {
    let design_done = read_key(
        &context.tmpdir.join("finalize-state.sh"), "DESIGN_ONLY_DONE",
    ) == "true";
    let no_issues = read_key(&context.tmpdir.join("run-flags.sh"), "NO_ISSUES") == "true";
    if design_done && no_issues {
        return Some(false);
    } let stats = regular_file(&context.run_dir().join("run-statistics.md"));
    if manifest.steps_ran().get("step9a1") == Some(&Value::Bool(false)) {
        return Some(false);
    } if manifest.steps_ran().get("step9a1") == Some(&Value::Bool(true)) {
        return Some(stats);
    } if stats {
        return Some(true);
    } if context.forked {
        return Some(false);
    } let oos = context.run_dir().join("oos-issues.ndjson");
    if oos.metadata().is_ok_and(|metadata| metadata.len() > 0) {
        return Some(false);
    } None
}

fn normalized_outcome(context: &FlushContext) -> String {
    normalized_outcome_values(context)
        .remove("IMPLEMENT_NORMALIZED_OUTCOME") .unwrap_or_else(|| "bailed".to_owned())
}

fn normalized_outcome_values(context: &FlushContext) -> BTreeMap<String, String> {
    normalize_outcome(&context.tmpdir, "")
        .map_or_else(|_error| BTreeMap::from([
            ("IMPLEMENT_NORMALIZED_OUTCOME".to_owned(), "bailed".to_owned()),
            ("IMPLEMENT_MERGE_DOWNGRADED".to_owned(), "false".to_owned()),
        ]), |rows| rows.into_iter().collect())
}

fn is_preterminal_outcome(outcome: &str) -> bool {
    matches!(outcome, "pr-created" | "pr-created-draft" | "shipping")
}

fn preterminal_outcome(context: &FlushContext) -> String {
    let outcome = normalized_outcome(context);
    if is_preterminal_outcome(&outcome) {
        outcome
    } else {
        // A mutable refresh is not terminal reconciliation. A stale terminal
        // overlay may remain until ship reentry clears it, but it must not
        // reproduce a terminal staging label on every retry.
        "shipping".to_owned()
    }
}

fn ensure_preterminal_summary_neutral(context: &FlushContext) -> Result<(), String> {
    let summary_path = context.run_dir().join("final-summary.md");
    if !regular_file(&summary_path) {
        return Ok(());
    }
    let summary = read_lossy(&summary_path)
        .map_err(|error| format!("preterminal-outcome: cannot read final summary: {error}"))?;
    if let Some(label) = parse_preterminal_outcome_label(&summary)
        .filter(|label| !is_preterminal_outcome(label))
    {
        return Err(format!(
            "preterminal-outcome: final summary retained terminal outcome label '{label}'"
        ));
    }
    Ok(())
}

fn write_final_report(
    context: &FlushContext, skip_tracking: bool, strict_reconcile: bool,
    preterminal: bool,
) -> Result<(), String> {
    let outcomes = normalized_outcome_values(context);
    let outcome = outcomes
        .get("IMPLEMENT_NORMALIZED_OUTCOME") .map_or("bailed", String::as_str);
    let outcome = if preterminal && !is_preterminal_outcome(outcome) {
        "shipping"
    } else {
        outcome
    };
    let merge_downgraded = if outcomes
        .get("IMPLEMENT_MERGE_DOWNGRADED") .is_some_and(|value| value == "true")
    { "true" } else { "false" };
    let mut arguments = vec![
        OsString::from("final-report"), OsString::from("write"),
        OsString::from("--implement-tmpdir"), context.tmpdir.as_os_str().to_owned(),
        OsString::from("--reconcile-stalled-summary"), OsString::from("--normalized-outcome"),
        OsString::from(outcome), OsString::from("--normalized-merge-downgraded"),
        OsString::from(merge_downgraded),
    ]; if skip_tracking {
        arguments.push(OsString::from("--skip-tracking-upsert"));
    } if strict_reconcile {
        arguments.push(OsString::from("--strict-stalled-summary"));
    } let cost_overrides = token_cost_overrides(); if cost_overrides != "{}" {
        arguments.extend([OsString::from("--cost-overrides-json"), OsString::from(cost_overrides)]);
    } crate::final_report_commands::write_report(&arguments[2..])
}

fn render_ledger_reports(context: &FlushContext, strict: bool) -> Result<(), String> {
    let token_output = context.tmpdir.join("token-report-refresh.json");
    let timing_output = context.tmpdir.join("timing-report-refresh.json");
    let token_ledger = token_ledger_path(context); let mut token_args = vec![
        os("token"), os("report"), os("--full"), os("--format"), os("json"), os("--output"),
        token_output.as_os_str().to_owned(), os("--ledger"), token_ledger.as_os_str().to_owned(),
        os("--implement-tmpdir"), context.tmpdir.as_os_str().to_owned(),
    ]; if !context.source_file.is_empty() {
        token_args.extend([os("--source-file"), os(&context.source_file)]);
    } let token_result = crate::token_commands::report_result(&token_args[2..]);
    let timing_ledger = if context.timing_ledger.is_empty() {
        context.tmpdir.join("timing-ledger.tsv")
    } else {
        PathBuf::from(&context.timing_ledger)
    }; let mut timing_args = vec![
        os("--full"), os("--format"), os("json"), os("--output"),
        timing_output.as_os_str().to_owned(), os("--ledger"),
        timing_ledger.as_os_str().to_owned(), os("--implement-tmpdir"),
        context.tmpdir.as_os_str().to_owned(),
    ]; if let Some(value) =
        env::var_os("LARCH_TIMING_OUTLIER_THRESHOLD_S").filter(|value| !value.is_empty())
    {
        timing_args.extend([os("--outlier-threshold"), value]);
    } if let Some(value) = env::var_os("LARCH_TEST_TIMING_NOW").filter(|value| !value.is_empty()) {
        timing_args.extend([os("--test-now"), value]);
    } let timing_result = crate::timing_commands::render_report_arguments(&timing_args);
    let mut errors = Vec::new(); if strict {
        match token_result.as_ref() {
            Err(message) => errors.push(format!(
                "token report render failed: {}",
                safe_detail(message)
            )),
            Ok(status) if *status != ExitCode::SUCCESS => {
                errors.push("token report render failed".to_owned());
            }
            Ok(_) => {}
        } if let Err(message) = timing_result.as_ref() {
            errors.push(format!("timing report render failed: {message}"));
        }
    } if token_output.is_file() {
        if let Err(message) = stage_replace_batch(
            &context.log_root, "implement", &context.run_id, "token-report", &token_output,
        ) {
            errors.push(format!("token report staging failed: {message}"));
        }
    } else if strict {
        errors.push(token_result.as_ref().err().map_or_else(
            || "token-report.json source was not produced".to_owned(),
            |message| {
                format!(
                    "token-report.json source was not produced: {}",
                    safe_detail(message)
                )
            },
        ));
    } if timing_output.is_file() {
        if let Err(message) = stage_replace_batch(
            &context.log_root, "implement", &context.run_id, "timing-report", &timing_output,
        ) {
            errors.push(format!("timing report staging failed: {message}"));
        }
    } else if strict {
        errors.push(timing_result.as_ref().err().map_or_else(
            || "timing-report.json source was not produced".to_owned(),
            |message| format!("timing-report.json source was not produced: {message}"),
        ));
    } if strict && !errors.is_empty() {
        return Err(errors.join("; "));
    } Ok(())
}

fn token_ledger_path(context: &FlushContext) -> PathBuf {
    if let Some(path) = env::var_os("LARCH_TOKEN_LEDGER").filter(|path| !path.is_empty()) {
        return PathBuf::from(path);
    }
    let session_id = if context.token_session_id.is_empty() {
        let local = read_lossy(&context.tmpdir.join("session-id")).unwrap_or_default();
        if local.trim().is_empty() {
            context.run_id.as_str()
        } else {
            // The owned string lives until this function returns.
            return context.tmpdir.join(format!(
                "larch-tokens-{:x}.jsonl", Sha256::digest(local.trim().as_bytes())
            ));
        }
    } else {
        context.token_session_id.as_str()
    }; context.tmpdir.join(format!(
        "larch-tokens-{:x}.jsonl", Sha256::digest(session_id.as_bytes())
    ))
}

fn render_derived_reports(context: &FlushContext) -> Result<(), String> {
    let refresh_token = context.tmpdir.join("token-report-refresh.json");
    let refresh_timing = context.tmpdir.join("timing-report-refresh.json");
    let mut token_sources = sidecars(&context.tmpdir, "tokens");
    let mut timing_sources = sidecars(&context.tmpdir, "timing");
    let canonical_present = !token_sources.is_empty() || !timing_sources.is_empty();
    if !canonical_present && !refresh_token.is_file() {
        return Ok(());
    }
    if refresh_token.is_file() {
        token_sources.push(("refresh".to_owned(), refresh_token));
    } if refresh_timing.is_file() {
        timing_sources.push(("refresh".to_owned(), refresh_timing));
    } if !canonical_present {
        token_sources.retain(|(tool, _path)| tool == "refresh");
        timing_sources.retain(|(tool, _path)| tool == "refresh");
    } let scratch = tempfile::tempdir_in(&context.tmpdir).map_err(|error| error.to_string())?;
    let token_output = scratch.path().join("token-report.ndjson");
    let timing_output = scratch.path().join("timing-report.ndjson");
    let mut arguments = vec![
        os("token"), os("report"), os("--scrape-run-output"),
        token_output.as_os_str().to_owned(), os("--scrape-timing-output"),
        timing_output.as_os_str().to_owned(), os("--implement-tmpdir"),
        context.tmpdir.as_os_str().to_owned(),
    ]; for (option, sources) in [
        ("--scrape-sidecar", token_sources), ("--scrape-timing-sidecar", timing_sources),
    ] {
        for (tool, path) in sources {
            arguments.extend([
                os(option), OsString::from(format!("{tool}={}", path.display())),
            ]);
        }
    } match crate::token_commands::report_result(&arguments[2..]) {
        Err(message) => {
            return Err(format!(
                "derived token/timing refresh failed: {}",
                safe_detail(&message)
            ));
        }
        Ok(status) if status != ExitCode::SUCCESS => {
            return Err("derived token/timing refresh failed".to_owned());
        }
        Ok(_) => {}
    } for (source, name) in [
        (token_output, "token-report.ndjson"), (timing_output, "timing-report.ndjson"),
    ] {
        if source.is_file() {
            let text = read_lossy(&source)?;
            write_run_log_file(&context.run_dir().join(name), &text)?;
        }
    } Ok(())
}

fn sidecars(tmpdir: &Path, kind: &str) -> Vec<(String, PathBuf)> {
    ["codex", "cursor", "claude"]
        .into_iter() .filter_map(|tool| {
            let path = tmpdir.join(format!("{tool}-{kind}.json"));
            regular_file(&path).then(|| (tool.to_owned(), path))
        }) .collect()
}

fn refresh_difficulty(context: &FlushContext) {
    let record = context.run_dir().join("difficulty-rating.json");
    let Some(repo_root) = context.repo_root.as_deref() else {
        return;
    }; if !record.is_file() || record.is_symlink() {
        return;
    }
    if crate::difficulty_commands::refresh_existing_at(&record, repo_root).is_err() {
        return;
    } let _ = stage_replace_batch(
        &context.log_root, "implement", &context.run_id, "difficulty-rating", &record,
    );
}

fn stage_vendor_diagnostics(context: &FlushContext, strict: bool) -> Result<(), String> {
    let root = context.tmpdir.join("vendor-failure-diagnostics.parts"); let mut parts = Vec::new();
    if let Err(error) = collect_parts(&root, &mut parts) {
        return if strict { Err(error) } else { Ok(()) };
    } parts.sort(); if parts.is_empty() {
        return Ok(());
    } let mut payload = Vec::new(); for path in parts {
        match fs::read(&path) {
            Ok(bytes) if !bytes.is_empty() => payload.extend(bytes), Ok(_bytes) => {}
            Err(error) => {
                return if strict { Err(format!("{}: {error}", path.display())) } else { Ok(()) };
            }
        }
    } let text = String::from_utf8_lossy(&payload);
    let canonical = context.tmpdir.join("vendor-failure-diagnostics.txt");
    if let Err(error) = write_run_log_file(&canonical, &text) {
        return if strict { Err(format!("vendor diagnostics refresh failed: {error}")) } else { Ok(()) };
    } if payload.is_empty() {
        return Ok(());
    } let result = stage_replace_batch(
        &context.log_root, "implement", &context.run_id, "vendor-failure-diagnostics", &canonical,
    ) .map(|_path| ()) .map_err(|error| format!("vendor diagnostics refresh failed: {error}")); if strict {
        result
    } else {
        let _ = result; Ok(())
    }
}

fn collect_parts(directory: &Path, output: &mut Vec<PathBuf>) -> Result<(), String> {
    if !fs::symlink_metadata(directory)
        .is_ok_and(|metadata| metadata.file_type().is_dir())
    {
        return Ok(());
    }
    let entries = fs::read_dir(directory)
        .map_err(|error| format!("{}: {error}", directory.display()))?;
    for entry in entries {
        let entry = entry.map_err(|error| format!("{}: {error}", directory.display()))?;
        let kind = entry.file_type().map_err(|error| format!("{}: {error}", entry.path().display()))?;
        let path = entry.path(); if kind.is_dir() {
            collect_parts(&path, output)?;
        } else if kind.is_file()
            && path
                .file_name() .is_some_and(|name| name.to_string_lossy().starts_with("part."))
        {
            output.push(path);
        }
    } Ok(())
}

fn stage_outcomes(context: &FlushContext, strict_handoff: bool) -> Result<(), String> {
    for (name, batch, strict, label) in [
        (
            "architectural-invariant-outcome.json", "architectural-invariant-outcome", true,
            "invariant outcome",
        ), (
            "architectural-guideline-outcome.json", "architectural-guideline-outcome", true,
            "guideline outcome",
        ), (
            ".ship-route-exit-handoff.env", "ship-route-exit-handoff", strict_handoff,
            "ship route handoff",
        ),
    ] {
        let path = context.tmpdir.join(name); if !path.is_file() || path.is_symlink() {
            continue;
        } let result = stage_replace_batch(
            &context.log_root, "implement", &context.run_id, batch, &path,
        ) .map(|_path| ()) .map_err(|error| format!("{label} staging failed: {error}")); if strict {
            result?;
        }
    } Ok(())
}

fn flush_execution_issues(
    context: &FlushContext, step: &str, source: &str, terminal: bool,
) -> Result<(), String> {
    let issue_log = context.issue_log();
    let batch = context.run_dir().join("execution-issues.ndjson");
    if batch.exists() && !regular_file(&batch) {
        return Err(format!("execution-issues batch is not a regular file: {}", batch.display()));
    }
    if !terminal && !should_flush_execution_issues(context, &issue_log, &batch) {
        return Ok(());
    } if !issue_log
        .metadata() .is_ok_and(|metadata| metadata.len() > 0)
    {
        if terminal && !batch.exists() {
            write_run_log_file(&batch, "")?;
        } return Ok(());
    } let digest = format!(
        "{:x}", Sha256::digest(fs::read(&issue_log).map_err(|error| error.to_string())?)
    ); let record = NamedTempFile::new_in(&context.tmpdir).map_err(|error| error.to_string())?;
    let record_path = record.path().to_path_buf();
    record.close().map_err(|error| error.to_string())?;
    let result = (|| {
    // The checkpoint stages the composed rows itself, so it asks the ledger
    // owner for records only; it never lets that owner publish or clear.
    write_execution_issue_records(
        &issue_log, &record_path, Some(&batch),
        RecordLabels { step, source },
    ) .map_err(|error| format!("execution-issues checkpoint failed: {error}"))?;
    let rendered = record_path.metadata().is_ok_and(|metadata| metadata.len() > 0);
    if rendered {
        stage_append_batch(
            &context.log_root, "implement", &context.run_id, "execution-issues", &record_path,
        )?;
    } if terminal && !batch.exists() {
        write_run_log_file(&batch, "")?;
    } if !terminal && rendered {
        write_run_log_file(
            &context.tmpdir.join(".execution-issues-flushed.sha"), &digest,
        )?;
    } Ok(())
    })(); let _ = fs::remove_file(record_path); result
}

fn should_flush_execution_issues(context: &FlushContext, issue_log: &Path, batch: &Path) -> bool {
    issue_log
        .metadata() .is_ok_and(|metadata| metadata.len() > 0) && (context
            .tmpdir .join(".execution-issues-step7a-reached") .is_file() || context
                .tmpdir .join(".execution-issues-flushed.sha") .is_file()
            || batch.is_file())
}

fn capture_for_context(context: &FlushContext, step: &str) -> TranscriptOutcome {
    let existing = context.run_dir().join("session-transcript.jsonl");
    if context.source_file.is_empty() {
        emit_kv("SESSION_TRANSCRIPT_STATUS", "source-not-configured");
        let omission = if regular_file(&existing) {
            false
        } else {
            transcript_warning(
                Some(&context.issue_log()), step, "source-not-configured",
                "LARCH_CLAUDE_SOURCE_FILE was not configured; session-transcript.jsonl could not be refreshed.",
            )
        }; return TranscriptOutcome {
            status: "source-not-configured".to_owned(), source_configured: false,
            artifact_present: regular_file(&existing), omission_recorded: omission,
        };
    } let outcome = capture_transcript_inner(
        &context.source_file, &context.log_root, Some(&context.tmpdir), "implement",
        &context.run_id, context.no_logs_commit, Some(&context.issue_log()), step, true,
    ); emit_kv("SESSION_TRANSCRIPT_STATUS", &outcome.status); outcome
}

#[allow(clippy::too_many_arguments)]
fn capture_transcript_inner(
    source_file: &str, log_root: &Path, tmpdir: Option<&Path>, skill: &str, run_id: &str,
    no_logs_commit: bool, issues_log: Option<&Path>, step: &str, refresh_mode: bool,
) -> TranscriptOutcome {
    let existing = log_root
        .join(skill) .join(run_id) .join("session-transcript.jsonl");
    if RunLogSlug::parse(run_id).is_err() {
        return transcript_failure(
            issues_log, step, "invalid-run-id", "run-id was invalid; transcript capture skipped.",
            true, regular_file(&existing),
        );
    } let source = Path::new(source_file);
    if source_file.is_empty()
        || !fs::symlink_metadata(source)
            .is_ok_and(|metadata| metadata.file_type().is_file() && metadata.len() > 0)
    {
        let retained = refresh_mode && regular_file(&existing); let message = if retained {
            "Claude source file was empty or not a regular file; refresh skipped and prior transcript retained."
        } else {
            "Claude source file was empty or not a regular file; transcript capture skipped."
        }; return transcript_failure(
            issues_log, step, "source-file-missing", message, true, regular_file(&existing),
        );
    } let transcript = read_key_value(source, "TRANSCRIPT_PATH")
        .map(|value| PathBuf::from(value.trim()));
    let Some(transcript) = transcript.filter(|path| regular_file(path)) else {
        let retained = refresh_mode && regular_file(&existing); let message = if retained {
            "Claude source file did not contain a TRANSCRIPT_PATH entry; refresh skipped and prior transcript retained."
        } else {
            "Claude source file did not contain a TRANSCRIPT_PATH entry; transcript capture skipped."
        }; return transcript_failure(
            issues_log, step, "transcript-path-missing", message, true, regular_file(&existing),
        );
    }; let scratch = tmpdir.map_or_else(|| transcript_scratch_dir(log_root), Path::to_path_buf);
    if let Err(error) = fs::create_dir_all(&scratch) {
        return transcript_failure(
            issues_log, step, "write-failed",
            &format!("session-transcript scratch directory could not be created: {error}"), true,
            regular_file(&existing),
        );
    } let rendered = match NamedTempFile::new_in(&scratch) {
        Ok(file) => file, Err(error) => {
            return transcript_failure(
                issues_log, step, "write-failed",
                &format!("session-transcript scratch file could not be created: {error}"), true,
                regular_file(&existing),
            );
        }
    }; let document =
        match render_session_transcript(&transcript, plugin_root_directory().as_deref()) {
            Ok(document) => document, Err(error) => {
                return transcript_failure(
                    issues_log, step, "render-failed", &format!(
                        "session-transcript render failed; transcript was not staged: {}",
                        safe_detail(&error.to_string())
                    ), true, regular_file(&existing),
                );
            }
        }; for line in document.warnings.lines() {
        let _recorded = transcript_warning(
            issues_log, step, "render-bounded",
            &format!("session-transcript renderer {line}."),
        );
    } if let Err(error) = fs::write(rendered.path(), document.text.as_bytes()) {
        return transcript_failure(
            issues_log, step, "write-failed", &format!(
                "session-transcript scratch write failed; transcript was not staged: {}",
                safe_detail(&error.to_string())
            ), true, regular_file(&existing),
        );
    } if !rendered
        .path() .metadata() .is_ok_and(|metadata| metadata.len() > 0)
    {
        return transcript_failure(
            issues_log, step, "render-empty",
            "session-transcript renderer produced an empty file; transcript was not staged.", true,
            regular_file(&existing),
        );
    } if let Err(message) = stage_replace_batch(
        log_root, skill, run_id, "session-transcript", rendered.path(),
    ) {
        return transcript_failure(
            issues_log, step, "write-failed",
            &format!("larch-log write failed; transcript was not captured: {message}"), true,
            regular_file(&existing),
        );
    } let status = if no_logs_commit {
        let message = "--no-logs-commit was set; transcript was written under the staging log root but not published.";
        let _recorded = transcript_warning(issues_log, step, "suppressed-no-logs-commit", message);
        "suppressed-no-logs-commit"
    } else {
        "captured"
    }; TranscriptOutcome {
        status: status.to_owned(), source_configured: true, artifact_present: regular_file(&existing),
        omission_recorded: false,
    }
}

fn transcript_failure(
    issues_log: Option<&Path>, step: &str, status: &str, message: &str, source_configured: bool,
    artifact_present: bool,
) -> TranscriptOutcome {
    let omission_recorded = transcript_warning(issues_log, step, status, message);
    TranscriptOutcome {
        status: status.to_owned(), source_configured, artifact_present, omission_recorded,
    }
}

fn transcript_scratch_dir(log_root: &Path) -> PathBuf {
    let parent = log_root.parent().unwrap_or(log_root); let mut roots = Vec::new();
    if let Some(root) = plugin_root_directory() { roots.push(root); }
    if let Ok(mut root) = env::current_dir() { loop {
        if root.join(".git").exists() { roots.push(root); break; }
        if !root.pop() { break; }
    }} if roots
        .iter() .any(|root| parent.starts_with(root) || root.starts_with(parent))
    {
        env::var_os("HOME").map_or_else(env::temp_dir, |home| {
            PathBuf::from(home).join(".cache/larch/sessions")
        })
    } else { parent.to_path_buf() }
}

fn transcript_warning(issues_log: Option<&Path>, step: &str, status: &str, message: &str) -> bool {
    let Some(path) = issues_log else {
        return false;
    }; append_execution_issue(
        path, "Warnings",
        &format!("- **Step {step}: session-transcript status={status}:** {message}"),
    ) .is_ok()
}

fn verify_terminal_files(
    context: &FlushContext, transcript: &TranscriptOutcome,
) -> Result<(), String> {
    let mut missing = [
        "final-summary.md", "token-report.json", "timing-report.json", "execution-issues.ndjson",
    ] .iter() .filter(|name| !regular_file(&context.run_dir().join(name))) .copied()
    .collect::<Vec<_>>();
    if transcript.source_configured
        && !regular_file(&context.run_dir().join("session-transcript.jsonl"))
    {
        missing.push("session-transcript.jsonl");
    } if missing.is_empty() {
        Ok(())
    } else {
        Err(format!(
            "terminal snapshot missing required files: {}", missing.join(", ")
        ))
    }
}

fn record_terminal_failure(context: &FlushContext, message: &str) {
    let entry = format!(
        "- **Step 18 terminal snapshot**: {}", one_line(message, 1000)
    ); let _ignored = append_execution_issue(&context.issue_log(), "Tool Failures", &entry);
    let _ignored =
        flush_execution_issues(context, "18", "execution-issues.md terminal snapshot", true);
}

/// Reduce one local error message to a redacted, bounded, single-line detail.
fn safe_detail(message: &str) -> String {
    one_line(redact(message).text(), 300)
}

fn read_key(path: &Path, key: &str) -> String {
    read_key_value(path, key).unwrap_or_default()
}

fn read_key_value(path: &Path, key: &str) -> Option<String> {
    if !regular_file(path) { return None; }
    let prefix = format!("{key}="); read_lossy(path)
        .ok()? .lines() .find_map(|line| line.strip_prefix(&prefix).map(str::to_owned))
}

fn regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_file())
}

fn canonicalize_with_missing_leaf(path: &Path) -> PathBuf {
    fs::canonicalize(path).ok().or_else(|| {
        let parent = path.parent()?;
        let name = path.file_name()?;
        fs::canonicalize(parent).ok().map(|resolved| resolved.join(name))
    }).unwrap_or_else(|| path.to_path_buf())
}

fn text(parsed: &ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option) .map_or_else(String::new, |value| value.to_string_lossy().into_owned())
}

fn required_text(parsed: &ParsedCommandLine, option: &str) -> Option<String> {
    let value = text(parsed, option); (!value.is_empty()).then_some(value)
}

fn optional_path(parsed: &ParsedCommandLine, option: &str) -> Option<PathBuf> {
    required_text(parsed, option).map(PathBuf::from)
}

fn nonempty_or(parsed: &ParsedCommandLine, option: &str, fallback: &str) -> String {
    let value = text(parsed, option); if value.is_empty() {
        fallback.to_owned()
    } else {
        value
    }
}

fn nonempty_or_env(parsed: &ParsedCommandLine, option: &str, key: &str) -> String {
    let value = text(parsed, option); if value.is_empty() {
        env::var(key).unwrap_or_default()
    } else {
        value
    }
}

fn bool_option(parsed: &ParsedCommandLine, option: &str, default: bool) -> Option<bool> {
    let value = text(parsed, option); if value.is_empty() {
        Some(default)
    } else {
        bool_value(&value)
    }
}

fn bool_value(value: &str) -> Option<bool> {
    match value {
        "true" => Some(true), "false" => Some(false), _ => None,
    }
}

fn first_nonempty(values: &[String]) -> String {
    values
        .iter() .find(|value| !value.is_empty()) .cloned() .unwrap_or_default()
}

fn positive_number(value: &str) -> Option<u64> {
    value
        .bytes() .all(|byte| byte.is_ascii_digit()) .then(|| value.parse().ok()) .flatten()
        .filter(|number| *number > 0)
}

fn one_line(value: &str, limit: usize) -> String {
    value
        .split_whitespace() .collect::<Vec<_>>() .join(" ") .chars() .take(limit) .collect()
}

fn token_cost_overrides() -> String {
    const KEYS: &str = "LARCH_CLAUDE_INPUT_RATE_PER_M LARCH_CLAUDE_CACHE_READ_RATE_PER_M LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M LARCH_CLAUDE_OUTPUT_RATE_PER_M LARCH_CODEX_INPUT_RATE_PER_M LARCH_CODEX_CACHED_INPUT_RATE_PER_M LARCH_CODEX_OUTPUT_RATE_PER_M LARCH_CODEX_MINI_INPUT_RATE_PER_M LARCH_CODEX_MINI_CACHED_INPUT_RATE_PER_M LARCH_CODEX_MINI_OUTPUT_RATE_PER_M LARCH_CURSOR_INPUT_RATE_PER_M LARCH_CURSOR_CACHE_READ_RATE_PER_M LARCH_CURSOR_OUTPUT_RATE_PER_M LARCH_CLAUDE_RATE_PER_M LARCH_CODEX_RATE_PER_M LARCH_CURSOR_RATE_PER_M LARCH_CURSOR_GROK_INPUT_RATE_PER_M LARCH_CURSOR_GROK_CACHE_READ_RATE_PER_M LARCH_CURSOR_GROK_OUTPUT_RATE_PER_M LARCH_CURSOR_TEAMS_SURCHARGE_PER_M LARCH_TOKEN_RATE_PER_M LARCH_RATE_CLAUDE_INPUT LARCH_RATE_CLAUDE_CACHE_READ LARCH_RATE_CLAUDE_CACHE_CREATE LARCH_RATE_CLAUDE_CACHE_CREATE_5M LARCH_RATE_CLAUDE_CACHE_CREATE_1H LARCH_RATE_CLAUDE_OUTPUT LARCH_RATE_CLAUDE_AGGREGATE LARCH_RATE_CODEX_INPUT LARCH_RATE_CODEX_CACHE_READ LARCH_RATE_CODEX_CACHED_INPUT LARCH_RATE_CODEX_OUTPUT LARCH_RATE_CODEX_AGGREGATE LARCH_RATE_CODEX_MINI_INPUT LARCH_RATE_CODEX_MINI_CACHE_READ LARCH_RATE_CODEX_MINI_CACHED_INPUT LARCH_RATE_CODEX_MINI_OUTPUT LARCH_RATE_CURSOR_INPUT LARCH_RATE_CURSOR_CACHE_READ LARCH_RATE_CURSOR_OUTPUT LARCH_RATE_CURSOR_AGGREGATE";
    serde_json::to_string(&KEYS.split_ascii_whitespace().filter_map(|key| {
        env::var(key).ok().map(|value| (key, value))
    }).collect::<BTreeMap<_, _>>()).unwrap_or_else(|_error| "{}".to_owned())
}

fn os(value: &str) -> OsString {
    OsString::from(value)
}
