// Included by `implement_step2_commands_impl.rs`; not a standalone module.
//
// Owns the second half of Step 2: launching the external implementer, routing
// its manifest, committing a complete result, and emitting the contract.

/// One launcher run's exit code, parsed envelope, and captured diagnostics.
struct LauncherRun {
    wrapper_rc: i32,
    launcher_exit: String,
    manifest_written: String,
    status: String,
    capture: String,
}

/// Build the `agent launch-<tool>-implement` argument vector.
fn launcher_args(state: &DispatchState) -> Vec<OsString> {
    let mut args: Vec<OsString> = vec![
        "agent".into(),
        format!("launch-{}-implement", state.tool_tag).into(),
        "--transcript-path".into(),
        state.transcript_path.clone().into_os_string(),
        "--sidecar-log".into(),
        state.sidecar_log.clone().into_os_string(),
        "--manifest-path".into(),
        state.manifest_path.clone().into_os_string(),
        "--qa-pending-path".into(),
        state.qa_pending_path.clone().into_os_string(),
        "--scout-manifest-path".into(),
        state.launch_scout_manifest.clone().into_os_string(),
        "--plan-file".into(),
        state.plan_file.clone().into_os_string(),
        "--feature-file".into(),
        state.feature_file.clone().into_os_string(),
        "--agent-prompt".into(),
        external_implementer_prompt_path(&state.plugin_root, &state.tool_tag).into_os_string(),
        "--timeout".into(),
        LAUNCHER_TIMEOUT_SECONDS.into(),
    ];
    if let Some(cap) =
        env::var_os("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT").filter(|value| !value.is_empty())
    {
        args.extend(["--token-budget-cap".into(), cap]);
    }
    if (state.tool_tag == "codex" || state.tool_tag == "cursor") && !state.difficulty.is_empty() {
        args.extend(["--difficulty".into(), state.difficulty.clone().into()]);
    }
    if let Some(answers) = state.answers_file.as_ref() {
        args.extend(["--answers-file".into(), answers.clone().into_os_string()]);
    }
    if state.completion_retry_feedback_file.is_file() {
        args.extend([
            "--completion-retry-file".into(),
            state.completion_retry_feedback_file.clone().into_os_string(),
        ]);
    }
    args
}

/// Run the external implementer launcher once.
fn run_launcher(state: &DispatchState) -> LauncherRun {
    let args = launcher_args(state);
    let (wrapper_rc, stdout, stderr) =
        crate::implement_child_seam::child_streams(&state_larch(state, &args));
    let scanned: String = stdout.chars().take(LAUNCHER_KV_LIMIT).collect();
    LauncherRun {
        wrapper_rc,
        launcher_exit: {
            let value = kv_value(&scanned, "LAUNCHER_EXIT");
            if value.is_empty() { "99".to_owned() } else { value }
        },
        manifest_written: {
            let value = kv_value(&scanned, "MANIFEST_WRITTEN");
            if value.is_empty() {
                "false".to_owned()
            } else {
                value
            }
        },
        status: kv_value(&scanned, "STATUS"),
        capture: stdout + &stderr,
    }
}

/// Launch the external implementer and route whatever it produced.
#[allow(clippy::too_many_lines)]
fn dispatch_launch_and_route(request: &mut Step2Request, state: &mut DispatchState) -> ExitCode {
    let mut run = run_launcher(state);
    if run.wrapper_rc == WRAPPER_VALIDATION_RC {
        return emit_bailed(state, "wrapper-validation-failure", false);
    }
    if run.status == "cap_hit" {
        return emit_bailed(state, "cap_hit", false);
    }
    if let Some(detail) = codex_gate_after_launch(state, &run.capture)
        && !manifest_complete_salvageable_file(&state.manifest_path)
    {
        return codex_gate_dispatch_result(state, &detail);
    }
    // A written manifest is the only outcome worth routing, so it is the only
    // condition that suppresses the single relaunch.
    if run.manifest_written != "true" {
        if working_tree_changed_since_baseline(state) {
            return emit_bailed(state, "dirty-state-after-timeout", false);
        }
        run = run_launcher(state);
        if run.wrapper_rc == WRAPPER_VALIDATION_RC {
            return emit_bailed(state, "wrapper-validation-failure", false);
        }
        if run.status == "cap_hit" {
            return emit_bailed(state, "cap_hit", false);
        }
        if let Some(detail) = codex_gate_after_launch(state, &run.capture) {
            return codex_gate_dispatch_result(state, &detail);
        }
    }
    if run.wrapper_rc != 0 || run.manifest_written != "true" {
        let token = state.runtime_failure_token.clone();
        return emit_bailed(state, &token, false);
    }
    let mut warn_nonzero = false;
    if run.launcher_exit != "0" {
        if state.coder == "codex" && manifest_complete_salvageable_file(&state.manifest_path) {
            warn_nonzero = true;
            append_warning(
                state,
                &format!(
                    "Step 4 — {tool} exited non-zero (LAUNCHER_EXIT={exit}) after atomically writing a complete manifest; not discarding it — continuing to validation/commit ({token}=true). A self-verification step likely failed after the implementation work completed.",
                    tool = state.tool_tag,
                    exit = run.launcher_exit,
                    token = state.nonzero_exit_warn_token,
                ),
            );
        } else {
            let token = state.runtime_failure_token.clone();
            return emit_bailed(state, &token, false);
        }
    }
    if !nonempty_file(&state.manifest_path) {
        return emit_bailed(state, "manifest-missing", false);
    }
    if fs::copy(&state.manifest_path, &state.manifest_raw_path).is_err() {
        return emit_bailed(state, "manifest-missing", false);
    }
    route_manifest(request, state, warn_nonzero, &run)
}

/// True when the tree moved off its baseline, or when a probe failed closed.
fn working_tree_changed_since_baseline(state: &DispatchState) -> bool {
    let Some(tree) = working_tree(&state.repo_root) else {
        return true;
    };
    tree.dirty()
        || state.repo_root.join(".git").join("index.lock").exists()
        || head_sha(&state.repo_root) != state.baseline_sha
}

fn manifest_complete_salvageable_file(path: &Path) -> bool {
    let value = read_json(path);
    larch_core::implement::manifest_complete_salvageable(value.as_ref())
}

fn read_json(path: &Path) -> Option<Value> {
    let text = fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

/// Detect a Codex CLI authorization or quota gate from this launch.
fn codex_gate_after_launch(
    state: &DispatchState,
    launcher_capture: &str,
) -> Option<larch_core::CodexGateDetail> {
    if state.coder != "codex" || manifest_complete_salvageable_file(&state.manifest_path) {
        return None;
    }
    let mut diagnostics = vec![launcher_capture.to_owned()];
    for path in [&state.sidecar_log, &state.transcript_path] {
        if path.is_file()
            && let Ok(bytes) = fs::read(path)
        {
            diagnostics.push(String::from_utf8_lossy(&bytes).into_owned());
        }
    }
    let model = resolve_implement_rater_model(
        "codex",
        &state.tmpdir.join("session-env.sh"),
        &state.difficulty,
    );
    detect_codex_cli_gate(&diagnostics.join("\n"), &model)
}

/// Route a Codex gate: recover to Claude only from a provably untouched tree.
fn codex_gate_dispatch_result(
    state: &DispatchState,
    detail: &larch_core::CodexGateDetail,
) -> ExitCode {
    if working_tree_changed_since_baseline(state) {
        return emit_bailed(state, detail.message(), false);
    }
    emit_claude_fallback(
        &state.tmpdir,
        Some(&state.repo_root),
        detail.message(),
        &state.tool_tag,
    );
    ExitCode::SUCCESS
}

/// Resolve the model token recorded as this run's implement difficulty rater.
fn resolve_implement_rater_model(tool: &str, session_env: &Path, difficulty_tier: &str) -> String {
    let value = match tool {
        "cursor" => first_model_value(
            session_env,
            &["LARCH_CURSOR_MODEL", "CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"],
            cursor_implement_model(difficulty_tier),
        ),
        "codex" => first_model_value(
            session_env,
            &["LARCH_CODEX_MODEL", "CLAUDE_PLUGIN_OPTION_CODEX_MODEL"],
            CODEX_IMPLEMENT_MODEL,
        ),
        _other => "unknown".to_owned(),
    };
    model_value_safe(&value)
}

fn first_model_value(session_env: &Path, keys: &[&str], default: &str) -> String {
    for key in keys {
        if let Some(value) = env::var(key).ok().filter(|value| !value.trim().is_empty()) {
            return value;
        }
    }
    for key in keys {
        let value = read_kv_first(session_env, key);
        if !value.trim().is_empty() {
            return value.trim().to_owned();
        }
    }
    default.to_owned()
}

// ---------------------------------------------------------------------------
// manifest routing
// ---------------------------------------------------------------------------

/// Validate the returned manifest, then route to complete, QA, or bail.
#[allow(clippy::too_many_lines)]
fn route_manifest(
    request: &mut Step2Request,
    state: &mut DispatchState,
    warn_nonzero: bool,
    run: &LauncherRun,
) -> ExitCode {
    let _ = run;
    let raw = read_json(&state.manifest_raw_path);
    let status = manifest_status(raw.as_ref());
    let Some(object) = raw.as_ref().and_then(Value::as_object).cloned() else {
        return emit_manifest_invalid_or_recover(state, &status, raw.as_ref());
    };
    if (status == "complete" || status == "needs_qa")
        && architectural_knowledge_required(state)
        && !require_architectural_acknowledgment(&object)
    {
        return emit_bailed(state, "architectural-acknowledgment-missing", false);
    }
    let schema_version = json_scalar_string(object.get("schema_version"));
    if !schema_version.is_empty() && schema_version != "1" {
        return emit_bailed(state, "manifest-schema-invalid", false);
    }
    if schema_version != "1" {
        return emit_manifest_invalid_or_recover(state, &status, raw.as_ref());
    }
    if !MANIFEST_STATUSES.contains(&status.as_str()) {
        return emit_manifest_invalid_or_recover(state, &status, raw.as_ref());
    }
    match status.as_str() {
        "complete" => {
            if !complete_schema_valid(&object) {
                return emit_manifest_invalid_or_recover(state, &status, raw.as_ref());
            }
        }
        "needs_qa" => {
            if let Some(bail) = repair_needs_qa_questions(state, &object) {
                return emit_bailed(state, &bail, false);
            }
        }
        _bailed => {
            let reason = object.get("bail_reason").and_then(Value::as_str);
            if reason.is_none_or(str::is_empty) {
                return emit_manifest_invalid_or_recover(state, &status, raw.as_ref());
            }
        }
    }
    if status != "bailed" {
        if let Some(reason) = post_implementer_safety_reason(state) {
            return emit_bailed(state, &reason, false);
        }
        normalize_scout(state);
    }

    let mut coverage: Option<Box<PlanCoverage>> = None;
    let mut uncovered_plan_path_count = 0_usize;
    if status == "complete" {
        match complete_preflight_and_commit(request, state, &object) {
            CompleteOutcome::Bailed(code) | CompleteOutcome::Retried(code) => return code,
            CompleteOutcome::Committed {
                plan_coverage,
                uncovered,
            } => {
                coverage = plan_coverage;
                uncovered_plan_path_count = uncovered;
            }
        }
    }

    let sanitized = sanitize_manifest_obj(&object);
    let rendered = serde_json::to_string_pretty(&Value::Object(sanitized)).unwrap_or_default();
    let _written = write_atomic(&state.manifest_path, &format!("{rendered}\n"));
    if status == "complete" {
        let oos_nonempty = object
            .get("oos_observations")
            .and_then(Value::as_array)
            .is_some_and(|items| !items.is_empty());
        if let Some(reason) = materialize_oos(state, oos_nonempty) {
            return emit_bailed(state, &reason, false);
        }
    }
    emit_terminal_contract(
        state,
        &status,
        &object,
        coverage.as_deref(),
        uncovered_plan_path_count,
        warn_nonzero,
    )
}

/// Repair a `needs_qa` manifest that omitted its own questions, or refuse.
fn repair_needs_qa_questions(
    state: &DispatchState,
    object: &Map<String, Value>,
) -> Option<String> {
    if !needs_qa_questions_present(object) {
        let qa = read_json(&state.qa_pending_path);
        let Some(repaired) = repaired_qa_questions(qa.as_ref()) else {
            return Some("manifest-schema-invalid".to_owned());
        };
        let text = serde_json::to_string(&repaired).unwrap_or_default();
        if write_atomic(&state.qa_pending_path, &format!("{text}\n")).is_err() {
            return Some("manifest-schema-invalid".to_owned());
        }
    }
    if qa_pending_valid(read_json(&state.qa_pending_path).as_ref()) {
        None
    } else {
        Some("qa-pending-missing".to_owned())
    }
}

/// Refuse a result the external implementer produced from an unsafe tree.
fn post_implementer_safety_reason(state: &DispatchState) -> Option<String> {
    if abbrev_ref(&state.repo_root) != state.spawn_branch {
        return Some("branch-changed".to_owned());
    }
    if submodule_status_dirty(&submodule_status_text(&state.repo_root)) {
        return Some("submodule-dirty".to_owned());
    }
    let roots = submodule_roots(&state.repo_root);
    if !roots.is_empty() {
        let Some(tree) = working_tree(&state.repo_root) else {
            return Some("submodule-dirty".to_owned());
        };
        if tree
            .all_paths()
            .iter()
            .any(|path| larch_core::implement::path_under_submodule(path, &roots))
        {
            return Some("submodule-dirty".to_owned());
        }
    }
    if state.requires_head_unchanged && head_sha(&state.repo_root) != state.baseline_sha {
        return Some(format!("{}-modified-history", state.tool_tag));
    }
    None
}

/// Normalize the coder's dynamic-archetype manifest for Step 5.
fn normalize_scout(state: &mut DispatchState) {
    let argv: Vec<OsString> = vec![
        "implement".into(),
        "normalize-coder-scout".into(),
        "--tmpdir".into(),
        state.tmpdir.clone().into_os_string(),
        "--input".into(),
        state.launch_scout_manifest.clone().into_os_string(),
        "--producer".into(),
        "external".into(),
    ];
    let status = match state_larch(state, &argv) {
        Ok(output) => {
            let text = String::from_utf8_lossy(output.stdout()).into_owned();
            let value = kv_value(&text, "SCOUT_CODER_STATUS");
            if value.is_empty() {
                read_kv_first(
                    &state.tmpdir.join("step2-scout-coder-status.env"),
                    "SCOUT_CODER_STATUS",
                )
            } else {
                value
            }
        }
        Err(_failed) => String::new(),
    };
    state.scout_status = if status.is_empty() {
        "missing-or-invalid".to_owned()
    } else {
        status
    };
}

/// Route a manifest that failed schema validation.
///
/// Recovery to Claude is allowed only for a manifest that is merely stale in
/// shape *and* whose working-tree delta is provably attributable and outside
/// every submodule; anything else bails.
fn emit_manifest_invalid_or_recover(
    state: &DispatchState,
    status: &str,
    raw: Option<&Value>,
) -> ExitCode {
    if let Some(bail) = manifest_invalid_bail_reason(state, status, raw) {
        return emit_bailed(state, &bail, false);
    }
    finalize_manifest_invalid_recovery(state);
    ExitCode::SUCCESS
}

fn manifest_invalid_bail_reason(
    state: &DispatchState,
    status: &str,
    raw: Option<&Value>,
) -> Option<String> {
    let Some(object) = raw.and_then(Value::as_object) else {
        return Some("manifest-schema-invalid".to_owned());
    };
    let legacy = match status {
        // Only a manifest that declares no status at all can be merely stale in
        // shape; any declared status is taken at its word.
        "" => manifest_legacy_fingerprint(&Value::Object(object.clone())),
        _ => false,
    };
    if status != "complete" && !legacy {
        return Some("manifest-schema-invalid".to_owned());
    }
    if read_kv_first(&state.prelaunch_index_flag, "PRELAUNCH_INDEX_NONEMPTY") == "true" {
        return Some("manifest-schema-invalid".to_owned());
    }
    if capture_postlaunch_porcelain(&state.repo_root, &state.tmpdir) != 0 {
        return Some("manifest-schema-invalid".to_owned());
    }
    if !attribute_recovery_paths(state).unwrap_or(false) {
        return Some("manifest-schema-invalid".to_owned());
    }
    if !recovery_paths_submodule_clean(state) {
        return Some("submodule-dirty".to_owned());
    }
    post_implementer_safety_reason(state)
}

/// True when no recovered path lives inside a submodule.
fn recovery_paths_submodule_clean(state: &DispatchState) -> bool {
    let roots = submodule_roots(&state.repo_root);
    let Ok(bytes) = fs::read(&state.recovery_paths_file) else {
        return false;
    };
    bytes
        .split(|byte| *byte == 0)
        .filter(|record| !record.is_empty())
        .all(|record| {
            !larch_core::implement::path_under_submodule(
                &String::from_utf8_lossy(record),
                &roots,
            )
        })
}

/// Hand the recovered edits to Claude with their provenance recorded.
fn finalize_manifest_invalid_recovery(state: &DispatchState) {
    let invalid = state.tmpdir.join("manifest-raw.invalid.json");
    if state.manifest_raw_path.exists() {
        let _renamed = fs::rename(&state.manifest_raw_path, &invalid);
    }
    let metadata = serde_json::json!({
        "schema_version": 1,
        "recovery_from": "manifest-schema-invalid",
        "prior_tool": state.tool_tag,
        "recovery_paths_file": state
            .recovery_paths_file
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default(),
    });
    let text = serde_json::to_string(&metadata).unwrap_or_default();
    let _written = write_atomic(
        &state.tmpdir.join("recovery-metadata.json"),
        &format!("{text}\n"),
    );
    emit_kv("STATUS", "claude_fallback");
    emit_kv("TOOL", &state.tool_tag);
    emit_dispatch_artifact_rows(state);
    emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "allowed");
    emit_kv("RECOVERY_FROM", "manifest-schema-invalid");
    emit_kv("RECOVERY_PRIOR_TOOL", &state.tool_tag);
    emit_kv(
        "RECOVERY_PATHS_FILE",
        &state.recovery_paths_file.display().to_string(),
    );
    clear_external_scout_state(&state.tmpdir);
}

// ---------------------------------------------------------------------------
// complete: coverage, difficulty, commit
// ---------------------------------------------------------------------------

/// What the complete-status pre-commit sequence decided.
enum CompleteOutcome {
    /// The dispatch bailed; the contract is already emitted.
    Bailed(ExitCode),
    /// The dispatch re-entered itself for a completion retry.
    Retried(ExitCode),
    /// The result was committed and may proceed to the terminal contract.
    Committed {
        plan_coverage: Option<Box<PlanCoverage>>,
        uncovered: usize,
    },
}

/// Validate, measure, and commit a complete external implementation.
#[allow(clippy::too_many_lines)]
fn complete_preflight_and_commit(
    request: &mut Step2Request,
    state: &DispatchState,
    object: &Map<String, Value>,
) -> CompleteOutcome {
    let roots = submodule_roots(&state.repo_root);
    let invalid = validate_manifest_paths(object, &roots);
    if !invalid.is_empty() {
        return CompleteOutcome::Bailed(emit_bailed(state, invalid, false));
    }
    let Some(tree) = working_tree(&state.repo_root) else {
        append_warning(
            state,
            "Step 7a.1 — plan coverage compute failed closed because git probe(s) failed: git status",
        );
        return CompleteOutcome::Bailed(emit_bailed(state, "plan-coverage-compute-failed", false));
    };
    let touched = tree.all_paths();
    let declared: std::collections::BTreeSet<String> = declared_paths(object).into_iter().collect();
    let missing: Vec<&String> = touched
        .iter()
        .filter(|path| !path.is_empty() && !declared.contains(*path))
        .collect();
    if !missing.is_empty() {
        let sample: Vec<String> = missing.iter().take(5).map(|path| (*path).clone()).collect();
        append_warning(
            state,
            &format!(
                "- **Step 7a.1 — {count} working-tree path(s) not declared in manifest files_touched/tests_added_or_modified (may include pre-existing dirty files). First 5**: {sample}",
                count = missing.len(),
                sample = sample.join(", "),
            ),
        );
    }
    write_step2_difficulty_record(state, object, &touched);
    let coverage = match compute_plan_coverage(state, true) {
        Ok(coverage) => coverage,
        Err(detail) => {
            append_warning(
                state,
                &format!("Step 7a.1 — plan coverage compute failed closed: {detail}"),
            );
            return CompleteOutcome::Bailed(emit_bailed(
                state,
                "plan-coverage-compute-failed",
                false,
            ));
        }
    };
    if coverage.disposition_required
        && (quota_failure(&state.sidecar_log) || quota_failure(&state.transcript_path))
    {
        return CompleteOutcome::Bailed(emit_bailed(state, "quota", false));
    }
    if coverage.disposition_required
        && let Some(code) = retry_incomplete_completion(request, state, &coverage)
    {
        return CompleteOutcome::Retried(code);
    }
    let uncovered = coverage.untouched_paths.len();
    if uncovered > 0 {
        let sample: Vec<String> = coverage.untouched_paths.iter().take(10).cloned().collect();
        append_warning(
            state,
            &format!(
                "- **Step 7a.1 — {uncovered} explicit plan-listed path(s) untouched by the working-tree delta before dispatcher commit. First 10**: {sample}",
                sample = sample.join(", "),
            ),
        );
    }
    if let Some(code) = commit_complete_manifest(state, object) {
        return CompleteOutcome::Bailed(code);
    }
    CompleteOutcome::Committed {
        plan_coverage: Some(Box::new(coverage)),
        uncovered,
    }
}

fn quota_failure(path: &Path) -> bool {
    let Ok(bytes) = fs::read(path) else {
        return false;
    };
    is_quota_failure(Some(&LauncherArtifact::present(
        String::from_utf8_lossy(&bytes).into_owned(),
    )))
}

/// Commit the external implementer's staged result under its own message.
fn commit_complete_manifest(
    state: &DispatchState,
    object: &Map<String, Value>,
) -> Option<ExitCode> {
    let commit_msg = redact_secrets_only(&json_scalar_string(object.get("commit_message")));
    let message_file = state
        .tmpdir
        .join(format!("{}-commit-message.txt", state.tool_tag));
    let commit_stderr = state
        .tmpdir
        .join(format!("{}-commit-stderr.txt", state.tool_tag));
    if write_atomic(&message_file, &commit_msg).is_err() {
        return Some(emit_bailed(state, "commit-failed", false));
    }
    match commit_all(&state.repo_root, &message_file) {
        Ok(()) => {
            let _removed = fs::remove_file(&commit_stderr);
            let argv: Vec<OsString> = vec!["run-log".into(), "checkpoint".into()];
            let _forwarded =
                state_larch(state, &argv);
            None
        }
        Err(detail) => {
            let _written = fs::write(&commit_stderr, detail.as_bytes());
            // Discard both manifests: a result that could not be committed must
            // not look committed to the next step.
            let _removed = fs::remove_file(&state.manifest_path);
            let _removed = fs::remove_file(&state.manifest_raw_path);
            Some(emit_bailed(state, "commit-failed", false))
        }
    }
}

/// Re-dispatch a proven-incomplete result, bounded by the configured cap.
///
/// Returns `None` when the retry budget is exhausted, which keeps the required
/// scope-disposition gate in place instead of silently accepting the result.
fn retry_incomplete_completion(
    request: &mut Step2Request,
    state: &DispatchState,
    coverage: &PlanCoverage,
) -> Option<ExitCode> {
    let Ok(retry_state) = read_completion_retry_state(state) else {
        return Some(emit_bailed(state, COMPLETION_RETRY_STATE_INVALID, false));
    };
    let count = retry_state.map_or(0, |state| state.count);
    if count >= COMPLETION_RETRY_CAP {
        append_warning(
            state,
            &format!(
                "Step 2 completion retries exhausted after {count} retry attempt(s); retaining the required scope-disposition gate."
            ),
        );
        return None;
    }
    let next_count = count + 1;
    let mut feedback = vec![
        "# Completion retry".to_owned(),
        String::new(),
        "The previous implementation attempt declared completion, but independent plan coverage found required work incomplete.".to_owned(),
        "Preserve compatible existing edits and finish the remaining plan scope. Do not declare completion until all required work is complete.".to_owned(),
        String::new(),
        format!("Retry attempt: {next_count} of {COMPLETION_RETRY_CAP}"),
        String::new(),
        "## Required plan paths still untouched".to_owned(),
        String::new(),
    ];
    feedback.extend(
        coverage
            .untouched_paths
            .iter()
            .map(|path| format!("- `{path}`")),
    );
    if !coverage.todos_left.is_empty() {
        feedback.extend([
            String::new(),
            "## Blocking deferred work reported by the prior attempt".to_owned(),
            String::new(),
        ]);
        feedback.extend(coverage.todos_left.iter().map(|item| format!("- {item}")));
    }
    if write_atomic(
        &state.completion_retry_state_file,
        &format!(
            "COMPLETION_RETRY_COUNT={next_count}\nPLAN_COVERAGE_FINGERPRINT={}\n",
            coverage.fingerprint
        ),
    )
    .is_err()
    {
        return Some(emit_bailed(state, COMPLETION_RETRY_STATE_INVALID, false));
    }
    let _written = write_atomic(
        &state.completion_retry_feedback_file,
        &format!("{}\n", feedback.join("\n")),
    );
    append_warning(
        state,
        &format!(
            "Step 2 independently found incomplete plan coverage; re-dispatching {tool} for completion retry {next_count}/{COMPLETION_RETRY_CAP}.",
            tool = state.tool_tag,
        ),
    );
    request.completion_retry = true;
    request.answers = String::new();
    Some(run_step2_dispatch(&clone_request(request)))
}

/// Read the bounded completion-retry record, failing closed on a bad one.
fn read_completion_retry_state(
    state: &DispatchState,
) -> Result<Option<CompletionRetryState>, CompletionRetryInvalid> {
    if !state.completion_retry_state_file.exists() {
        return Ok(None);
    }
    let Ok(bytes) = fs::read(&state.completion_retry_state_file) else {
        return Err(CompletionRetryInvalid);
    };
    parse_completion_retry_state(&String::from_utf8_lossy(&bytes), COMPLETION_RETRY_CAP)
}

/// Publish this run's difficulty rating and its changed-path evidence.
fn write_step2_difficulty_record(
    state: &DispatchState,
    object: &Map<String, Value>,
    changed_paths: &[String],
) {
    let Some(rating) = object.get("difficulty").filter(|value| value.is_object()) else {
        return;
    };
    let raw = state.tmpdir.join("implement-difficulty-rating.raw.json");
    let paths = state.tmpdir.join("difficulty-changed-paths.txt");
    let out = state.tmpdir.join("implement-difficulty-record.json");
    let rating_text = serde_json::to_string(rating).unwrap_or_default();
    if write_atomic(&raw, &format!("{rating_text}\n")).is_err() {
        return;
    }
    let mut sorted: Vec<&String> = changed_paths.iter().collect();
    sorted.sort_unstable();
    let mut listing = String::new();
    for path in sorted {
        listing.push_str(path);
        listing.push('\n');
    }
    let _written = write_atomic(&paths, &listing);
    let mut argv: Vec<OsString> = vec![
        "difficulty".into(),
        "write-record".into(),
        "--output".into(),
        out.clone().into_os_string(),
        "--rater".into(),
        "implement".into(),
        "--rater-tool".into(),
        state.tool_tag.clone().into(),
        "--rater-model".into(),
        resolve_implement_rater_model(
            &state.tool_tag,
            &state.tmpdir.join("session-env.sh"),
            &state.difficulty,
        )
        .into(),
        "--raw-rating-file".into(),
        raw.clone().into_os_string(),
        "--implement-raw-rating-file".into(),
        raw.into_os_string(),
        "--fallback-tier".into(),
        "MODERATE".into(),
        "--fallback-rationale".into(),
        "dispatcher fallback rating".into(),
    ];
    let prior = read_kv_first(&state.tmpdir.join("difficulty-prior.env"), "DESIGN_DIFFICULTY");
    if tier_valid(&prior) {
        argv.extend(["--design-tier".into(), prior.into()]);
    }
    if paths.is_file() {
        argv.extend(["--changed-paths-file".into(), paths.into_os_string()]);
    }
    let skipped = if read_kv_first(&state.tmpdir.join("run-flags.sh"), "SELF_REVIEW_REQUESTED")
        == "true"
    {
        "self-review"
    } else {
        ""
    };
    if !skipped.is_empty() {
        argv.extend(["--panel-skipped".into(), skipped.into()]);
    }
    let Ok(output) = state_larch(state, &argv) else {
        return;
    };
    if output.status().code() != Some(0) || !out.is_file() {
        return;
    }
    let run_id = read_kv_first(&state.tmpdir.join("parent-issue.md"), "RUN_ID");
    let log_argv: Vec<OsString> = vec![
        "run-log".into(),
        "write".into(),
        "--log-root".into(),
        state.tmpdir.join("larch-logs").into_os_string(),
        "--skill".into(),
        "implement".into(),
        "--run-id".into(),
        run_id.into(),
        "--batch".into(),
        "difficulty-rating".into(),
        "--input-file".into(),
        out.into_os_string(),
    ];
    let _forwarded = state_larch(state, &log_argv);
}

/// Materialize the manifest's OOS observations, or name the fatal failure.
fn materialize_oos(state: &DispatchState, oos_nonempty: bool) -> Option<String> {
    let log = state.tmpdir.join("materialize-manifest-oos.log");
    let _truncated = fs::write(&log, b"");
    let count_argv: Vec<OsString> = vec![
        "oos".into(),
        "materialize-manifest".into(),
        "--count-only".into(),
        "--manifest-path".into(),
        state.manifest_path.clone().into_os_string(),
        "--implement-tmpdir".into(),
        state.tmpdir.clone().into_os_string(),
    ];
    let (count_rc, count) =
        match state_larch(state, &count_argv) {
            Ok(output) => {
                let rc = output.status().code().unwrap_or(1);
                if rc == 0 {
                    (
                        0,
                        String::from_utf8_lossy(output.stdout())
                            .trim()
                            .parse::<u64>()
                            .ok(),
                    )
                } else {
                    let _written = fs::write(&log, output.stderr());
                    (rc, None)
                }
            }
            Err(detail) => {
                let _written = fs::write(&log, detail.as_bytes());
                (1, None)
            }
        };
    let full_argv: Vec<OsString> = vec![
        "oos".into(),
        "materialize-manifest".into(),
        "--manifest-path".into(),
        state.manifest_path.clone().into_os_string(),
        "--implement-tmpdir".into(),
        state.tmpdir.clone().into_os_string(),
    ];
    let materialize_failed =
        match state_larch(state, &full_argv) {
            Ok(output) if output.status().code() == Some(0) => false,
            Ok(output) => {
                append_log(&log, &String::from_utf8_lossy(output.stderr()));
                true
            }
            Err(detail) => {
                append_log(&log, &detail);
                true
            }
        };
    if materialize_failed {
        let argv: Vec<OsString> = vec![
            "run-log".into(),
            "append-failure".into(),
            "--log".into(),
            state.tmpdir.join("execution-issues.md").into_os_string(),
            "--site".into(),
            "step2-materialize-manifest-oos".into(),
            "--tool".into(),
            "larch oos materialize-manifest".into(),
            "--exit-code".into(),
            "1".into(),
            "--category".into(),
            "Tool Failures".into(),
            "--output-file".into(),
            log.into_os_string(),
            "--redact".into(),
        ];
        let _forwarded = state_larch(state, &argv);
    }
    if oos_materialize_should_bail(count_rc, count, oos_nonempty, materialize_failed) {
        return Some("manifest-oos-materialization-failed".to_owned());
    }
    None
}

fn append_log(path: &Path, text: &str) {
    let existing = fs::read_to_string(path).unwrap_or_default();
    let _written = fs::write(path, format!("{existing}{text}").as_bytes());
}

// ---------------------------------------------------------------------------
// terminal contract
// ---------------------------------------------------------------------------

/// Emit the Step 2 `KEY=value` contract for the routed status.
fn emit_terminal_contract(
    state: &DispatchState,
    status: &str,
    object: &Map<String, Value>,
    coverage: Option<&PlanCoverage>,
    uncovered_plan_path_count: usize,
    warn_nonzero: bool,
) -> ExitCode {
    match status {
        "complete" => {
            emit_kv("STATUS", "complete");
            emit_kv("TOOL", &state.tool_tag);
            emit_kv("MANIFEST", &state.manifest_path.display().to_string());
            emit_kv("TRANSCRIPT", &state.transcript_path.display().to_string());
            emit_kv("SIDECAR_LOG", &state.sidecar_log.display().to_string());
            emit_kv(
                "SCOUT_CODER_MANIFEST",
                &state.scout_coder_manifest.display().to_string(),
            );
            emit_kv("SCOUT_CODER_STATUS", &state.scout_status);
            if warn_nonzero && !state.nonzero_exit_warn_token.is_empty() {
                emit_kv(&state.nonzero_exit_warn_token, "true");
            }
            if uncovered_plan_path_count > 0 {
                emit_kv("WARN_PLAN_FILES_UNTOUCHED", "true");
                emit_kv(
                    "WARN_PLAN_FILES_UNTOUCHED_COUNT",
                    &uncovered_plan_path_count.to_string(),
                );
            }
            if let Some(coverage) = coverage {
                for (key, value) in coverage_rows(coverage) {
                    emit_kv(key, &value);
                }
            }
            match read_completion_retry_state(state) {
                Ok(Some(retry)) => emit_kv("CODER_COMPLETION_RETRIES", &retry.count.to_string()),
                Ok(None) => {}
                Err(CompletionRetryInvalid) => {
                    return emit_bailed(state, COMPLETION_RETRY_STATE_INVALID, false);
                }
            }
            emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden");
        }
        "needs_qa" => {
            emit_kv("STATUS", "needs_qa");
            emit_kv("TOOL", &state.tool_tag);
            emit_kv("MANIFEST", &state.manifest_path.display().to_string());
            emit_kv("QA_PENDING", &state.qa_pending_path.display().to_string());
            emit_kv("TRANSCRIPT", &state.transcript_path.display().to_string());
            emit_kv("SIDECAR_LOG", &state.sidecar_log.display().to_string());
            emit_kv(
                "SCOUT_CODER_MANIFEST",
                &state.scout_coder_manifest.display().to_string(),
            );
            emit_kv("SCOUT_CODER_STATUS", &state.scout_status);
            emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden");
        }
        _bailed => {
            let reason = sanitize_bail_reason(
                &json_scalar_string(object.get("bail_reason")),
                &state.bailed_no_reason_token,
            );
            emit_kv("STATUS", "bailed");
            emit_kv("REASON", &reason);
            emit_kv("TOOL", &state.tool_tag);
            emit_kv("MANIFEST", &state.manifest_path.display().to_string());
            emit_kv("TRANSCRIPT", &state.transcript_path.display().to_string());
            emit_kv("SIDECAR_LOG", &state.sidecar_log.display().to_string());
            emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden");
        }
    }
    ExitCode::SUCCESS
}

/// The plan-coverage rows the complete contract publishes, in emission order.
fn coverage_rows(coverage: &PlanCoverage) -> Vec<(&'static str, String)> {
    crate::implement_scope_disposition_commands::plan_coverage_contract_rows(coverage)
}

/// Compute plan coverage through the in-process scope-disposition owner.
fn compute_plan_coverage(
    state: &DispatchState,
    publish: bool,
) -> Result<PlanCoverage, String> {
    if publish {
        crate::implement_scope_disposition_commands::compute_and_write_plan_coverage(
            &state.tmpdir,
            &state.repo_root,
            Some(&state.plan_file),
            Some(&state.manifest_path),
        )
    } else {
        crate::implement_scope_disposition_commands::compute_plan_coverage(
            &state.tmpdir,
            &state.repo_root,
            Some(&state.plan_file),
            Some(&state.manifest_path),
        )
    }
}

type PlanCoverage = crate::implement_scope_disposition_commands::PlanCoverageView;
