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

#[cfg(test)]
mod route_tests {
    use super::*;
    use super::fixtures::*;

    fn sample_coverage(fingerprint: &str, disposition_required: bool) -> PlanCoverage {
        crate::implement_scope_disposition_commands::PlanCoverage {
            total: 4,
            touched: 3,
            untouched: 1,
            untouched_percent: 25,
            band: "LOW".to_owned(),
            plan_paths: vec!["a.rs".to_owned()],
            touched_paths: vec!["a.rs".to_owned()],
            untouched_paths: vec!["b.rs".to_owned()],
            todos_left_count: 0,
            todos_left: Vec::new(),
            fingerprint: fingerprint.to_owned(),
            disposition_required,
            plan_fidelity_forced: false,
            coverage_file: String::new(),
            untouched_file: String::new(),
            todos_file: String::new(),
        }
    }

    // -- launcher_args ---------------------------------------------------------

    #[test]
    fn launcher_args_names_the_launcher_and_its_bounded_artifact_paths() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let args: Vec<String> = launcher_args(&state)
            .into_iter()
            .map(|part| part.to_string_lossy().into_owned())
            .collect();
        assert_eq!(args[0], "agent");
        assert_eq!(args[1], "launch-codex-implement");
        assert!(args.contains(&"--transcript-path".to_owned()));
        assert!(args.contains(&"--manifest-path".to_owned()));
        assert!(args.contains(&"--timeout".to_owned()));
        assert!(args.contains(&LAUNCHER_TIMEOUT_SECONDS.to_owned()));
    }

    #[test]
    fn launcher_args_includes_difficulty_for_codex_and_cursor_but_not_claude() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        for coder in ["codex", "cursor"] {
            let mut state = test_dispatch_state(&tmpdir, &repo_root, coder);
            state.difficulty = "HARD".to_owned();
            let args: Vec<String> = launcher_args(&state)
                .into_iter()
                .map(|part| part.to_string_lossy().into_owned())
                .collect();
            assert!(args.contains(&"--difficulty".to_owned()), "{coder}: {args:?}");
            assert!(args.contains(&"HARD".to_owned()), "{coder}: {args:?}");
        }
        let mut claude_state = test_dispatch_state(&tmpdir, &repo_root, "claude");
        claude_state.difficulty = "HARD".to_owned();
        let args: Vec<String> = launcher_args(&claude_state)
            .into_iter()
            .map(|part| part.to_string_lossy().into_owned())
            .collect();
        assert!(!args.contains(&"--difficulty".to_owned()), "{args:?}");
    }

    #[test]
    fn launcher_args_includes_answers_and_completion_retry_files_when_present() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let mut state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let answers = tmpdir.path().join("answers.json");
        test_write_fixture(&answers, "{}");
        state.answers_file = Some(answers.clone());
        test_write_fixture(&state.completion_retry_feedback_file, "feedback\n");
        let args: Vec<String> = launcher_args(&state)
            .into_iter()
            .map(|part| part.to_string_lossy().into_owned())
            .collect();
        assert!(args.contains(&"--answers-file".to_owned()));
        assert!(args.contains(&answers.to_string_lossy().into_owned()));
        assert!(args.contains(&"--completion-retry-file".to_owned()));
    }

    // -- manifest reading -------------------------------------------------------

    #[test]
    fn manifest_complete_salvageable_file_reads_schema_and_status() {
        let dir = tempfile::tempdir().expect("dir");
        let path = dir.path().join("manifest.json");
        assert!(!manifest_complete_salvageable_file(&path));
        test_write_fixture(&path, r#"{"schema_version": 1, "status": "complete"}"#);
        assert!(manifest_complete_salvageable_file(&path));
        test_write_fixture(&path, r#"{"schema_version": 1, "status": "bailed"}"#);
        assert!(!manifest_complete_salvageable_file(&path));
        test_write_fixture(&path, "not json");
        assert!(!manifest_complete_salvageable_file(&path));
    }

    #[test]
    fn read_json_parses_valid_json_and_refuses_the_rest() {
        let dir = tempfile::tempdir().expect("dir");
        let path = dir.path().join("value.json");
        assert!(read_json(&path).is_none());
        test_write_fixture(&path, "not json");
        assert!(read_json(&path).is_none());
        test_write_fixture(&path, r#"{"a": 1}"#);
        assert_eq!(read_json(&path), Some(serde_json::json!({"a": 1})));
    }

    // -- codex gate --------------------------------------------------------------

    #[test]
    fn codex_gate_after_launch_is_none_for_non_codex_coders() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "cursor");
        assert!(codex_gate_after_launch(&state, "anything").is_none());
    }

    #[test]
    fn codex_gate_after_launch_is_none_when_the_manifest_is_already_salvageable() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        test_write_fixture(
            &state.manifest_path,
            r#"{"schema_version": 1, "status": "complete"}"#,
        );
        assert!(codex_gate_after_launch(&state, "anything").is_none());
    }

    #[test]
    fn codex_gate_dispatch_result_falls_back_to_claude_when_the_tree_is_untouched() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        state.baseline_sha = head_sha(repo.path());
        let detail = detect_codex_cli_gate("Model metadata for gpt-5 not found", "gpt-5")
            .expect("gate detail");
        let code = codex_gate_dispatch_result(&state, &detail);
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert!(tmpdir.path().join("step2-baseline.txt").is_file());
    }

    #[test]
    fn codex_gate_dispatch_result_bails_when_the_tree_has_moved() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        // baseline_sha is left empty, which never matches the repo's real head.
        let state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        let detail = detect_codex_cli_gate("Model metadata for gpt-5 not found", "gpt-5")
            .expect("gate detail");
        let code = codex_gate_dispatch_result(&state, &detail);
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert!(
            !tmpdir.path().join("step2-baseline.txt").is_file(),
            "a bail must not write a claude-fallback baseline"
        );
    }

    // -- rater model resolution ---------------------------------------------

    #[test]
    fn first_model_value_prefers_the_session_record_over_the_default() {
        let dir = tempfile::tempdir().expect("dir");
        let session = dir.path().join("session-env.sh");
        test_write_fixture(&session, "LARCH_CODEX_MODEL=gpt-codex-custom\n");
        let value = first_model_value(
            &session,
            &["LARCH_CODEX_MODEL", "CLAUDE_PLUGIN_OPTION_CODEX_MODEL"],
            "fallback-model",
        );
        assert_eq!(value, "gpt-codex-custom");
    }

    #[test]
    fn first_model_value_falls_back_to_the_default_when_unset() {
        let dir = tempfile::tempdir().expect("dir");
        let session = dir.path().join("session-env.sh");
        let value = first_model_value(&session, &["LARCH_CODEX_MODEL"], "fallback-model");
        assert_eq!(value, "fallback-model");
    }

    #[test]
    fn resolve_implement_rater_model_dispatches_by_tool_and_sanitizes() {
        let dir = tempfile::tempdir().expect("dir");
        let session = dir.path().join("session-env.sh");
        assert_eq!(resolve_implement_rater_model("other", &session, ""), "unknown");
        assert!(!resolve_implement_rater_model("cursor", &session, "").is_empty());
        assert!(!resolve_implement_rater_model("codex", &session, "").is_empty());
    }

    // -- needs_qa repair / post-implementer safety --------------------------

    #[test]
    fn repair_needs_qa_questions_repairs_from_qa_pending_when_absent() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        test_write_fixture(
            &state.qa_pending_path,
            r#"{"items": [{"area": "scope", "risk": "unclear", "suggested_check": "ask"}]}"#,
        );
        let object = Map::new();
        let bail = repair_needs_qa_questions(&state, &object);
        assert!(bail.is_none(), "{bail:?}");
        let repaired = fs::read_to_string(&state.qa_pending_path).expect("repaired qa");
        assert!(repaired.contains("questions"));
    }

    #[test]
    fn repair_needs_qa_questions_bails_without_any_recoverable_questions() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let object = Map::new();
        let bail = repair_needs_qa_questions(&state, &object);
        assert_eq!(bail, Some("manifest-schema-invalid".to_owned()));
    }

    #[test]
    fn post_implementer_safety_reason_is_none_for_a_clean_matching_tree() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        state.spawn_branch = abbrev_ref(repo.path());
        assert_eq!(post_implementer_safety_reason(&state), None);
    }

    #[test]
    fn post_implementer_safety_reason_flags_a_branch_change() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        state.spawn_branch = "some-other-branch".to_owned();
        assert_eq!(
            post_implementer_safety_reason(&state),
            Some("branch-changed".to_owned())
        );
    }

    #[test]
    fn post_implementer_safety_reason_flags_head_movement_for_cursor() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = test_dispatch_state(&tmpdir, repo.path(), "cursor");
        state.spawn_branch = abbrev_ref(repo.path());
        state.baseline_sha = "0".repeat(40);
        assert!(state.requires_head_unchanged);
        assert_eq!(
            post_implementer_safety_reason(&state),
            Some("cursor-modified-history".to_owned())
        );
    }

    #[test]
    fn post_implementer_safety_reason_flags_a_path_inside_a_declared_submodule() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        test_write_fixture(
            &repo.path().join(".gitmodules"),
            "[submodule \"vendor\"]\n\tpath = vendor\n",
        );
        test_git(repo.path(), &["add", ".gitmodules"]);
        test_commit_everything(repo.path(), "add submodule declaration");
        fs::create_dir_all(repo.path().join("vendor")).expect("vendor dir");
        test_write_fixture(&repo.path().join("vendor/file.txt"), "inside\n");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        state.spawn_branch = abbrev_ref(repo.path());
        assert_eq!(
            post_implementer_safety_reason(&state),
            Some("submodule-dirty".to_owned())
        );
    }

    // -- manifest-invalid recovery -------------------------------------------

    #[test]
    fn manifest_invalid_bail_reason_rejects_a_non_object_manifest() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        assert_eq!(
            manifest_invalid_bail_reason(&state, "", None),
            Some("manifest-schema-invalid".to_owned())
        );
        let array = serde_json::json!([1, 2, 3]);
        assert_eq!(
            manifest_invalid_bail_reason(&state, "", Some(&array)),
            Some("manifest-schema-invalid".to_owned())
        );
    }

    #[test]
    fn manifest_invalid_bail_reason_rejects_a_declared_status_without_legacy_shape() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let object = serde_json::json!({"status": "needs_qa"});
        assert_eq!(
            manifest_invalid_bail_reason(&state, "needs_qa", Some(&object)),
            Some("manifest-schema-invalid".to_owned())
        );
    }

    #[test]
    fn emit_manifest_invalid_or_recover_bails_for_an_undeclared_status() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let code = emit_manifest_invalid_or_recover(&state, "", None);
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
    }

    #[test]
    fn recovery_paths_submodule_clean_reports_true_without_any_submodules() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        fs::write(&state.recovery_paths_file, b"src/lib.rs\0src/main.rs\0")
            .expect("recovery paths");
        assert!(recovery_paths_submodule_clean(&state));
    }

    #[test]
    fn recovery_paths_submodule_clean_flags_a_path_inside_a_declared_submodule() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        fs::create_dir_all(&repo_root).expect("repo root");
        test_write_fixture(
            &repo_root.join(".gitmodules"),
            "[submodule \"vendor\"]\n\tpath = vendor\n",
        );
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        fs::write(&state.recovery_paths_file, b"vendor/file.txt\0").expect("recovery paths");
        assert!(!recovery_paths_submodule_clean(&state));
    }

    #[test]
    fn recovery_paths_submodule_clean_fails_closed_without_a_recovery_file() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        assert!(!recovery_paths_submodule_clean(&state));
    }

    #[test]
    fn finalize_manifest_invalid_recovery_renames_the_raw_manifest_and_writes_metadata() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        test_write_fixture(&state.manifest_raw_path, r#"{"status": "bogus"}"#);
        finalize_manifest_invalid_recovery(&state);
        assert!(!state.manifest_raw_path.exists());
        assert!(tmpdir.path().join("manifest-raw.invalid.json").is_file());
        let metadata =
            fs::read_to_string(tmpdir.path().join("recovery-metadata.json")).expect("metadata");
        assert!(metadata.contains("manifest-schema-invalid"));
        assert!(metadata.contains("codex"));
    }

    // -- complete-manifest commit --------------------------------------------

    #[test]
    fn commit_complete_manifest_commits_and_returns_no_exit_code() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        test_write_fixture(&repo.path().join("a.txt"), "two\n");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        let object = serde_json::json!({"commit_message": "Implement feature X"})
            .as_object()
            .expect("object")
            .clone();
        let outcome = commit_complete_manifest(&state, &object);
        assert!(outcome.is_none(), "a successful commit must not return an exit code");
    }

    #[test]
    fn commit_complete_manifest_reports_failure_and_discards_both_manifests() {
        let repo = test_init_repo(); // no commits, nothing staged: git commit fails.
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let state = test_dispatch_state(&tmpdir, repo.path(), "codex");
        test_write_fixture(&state.manifest_path, "{}");
        test_write_fixture(&state.manifest_raw_path, "{}");
        let object = serde_json::json!({"commit_message": "no-op"})
            .as_object()
            .expect("object")
            .clone();
        let outcome = commit_complete_manifest(&state, &object);
        assert!(outcome.is_some());
        assert!(!state.manifest_path.exists());
        assert!(!state.manifest_raw_path.exists());
    }

    // -- completion retry ------------------------------------------------------

    #[test]
    fn read_completion_retry_state_reads_missing_valid_and_invalid_records() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        assert_eq!(read_completion_retry_state(&state), Ok(None));
        let fingerprint = "f".repeat(64);
        test_write_fixture(
            &state.completion_retry_state_file,
            &format!("COMPLETION_RETRY_COUNT=2\nPLAN_COVERAGE_FINGERPRINT={fingerprint}\n"),
        );
        let retry = read_completion_retry_state(&state)
            .expect("valid retry state")
            .expect("some");
        assert_eq!(retry.count, 2);
        assert_eq!(retry.fingerprint, fingerprint);
        test_write_fixture(
            &state.completion_retry_state_file,
            "COMPLETION_RETRY_COUNT=not-a-number\n",
        );
        assert!(read_completion_retry_state(&state).is_err());
    }

    #[test]
    fn retry_incomplete_completion_stops_once_the_cap_is_exhausted() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let mut request = test_base_step2_request(tmpdir.path(), "codex");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let fingerprint = "a".repeat(64);
        test_write_fixture(
            &state.completion_retry_state_file,
            &format!("COMPLETION_RETRY_COUNT=3\nPLAN_COVERAGE_FINGERPRINT={fingerprint}\n"),
        );
        let coverage = sample_coverage(&fingerprint, true);
        let result = retry_incomplete_completion(&mut request, &state, &coverage);
        assert!(result.is_none());
    }

    #[test]
    fn retry_incomplete_completion_bails_on_an_invalid_retry_record() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let mut request = test_base_step2_request(tmpdir.path(), "codex");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        test_write_fixture(
            &state.completion_retry_state_file,
            "COMPLETION_RETRY_COUNT=not-a-number\n",
        );
        let coverage = sample_coverage(&"a".repeat(64), true);
        let result = retry_incomplete_completion(&mut request, &state, &coverage);
        assert!(result.is_some());
    }

    // -- terminal contract / coverage rows ------------------------------------

    #[test]
    fn emit_terminal_contract_reports_success_for_every_routed_status() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let object = Map::new();
        for status in ["complete", "needs_qa", "bailed"] {
            let code = emit_terminal_contract(&state, status, &object, None, 0, false);
            assert_eq!(
                format!("{code:?}"),
                format!("{:?}", ExitCode::SUCCESS),
                "status={status}"
            );
        }
    }

    #[test]
    fn emit_terminal_contract_reports_uncovered_plan_paths_and_a_coverage_row() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        let object = Map::new();
        let coverage = sample_coverage(&"a".repeat(64), false);
        let code = emit_terminal_contract(&state, "complete", &object, Some(&coverage), 3, true);
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
    }

    #[test]
    fn emit_terminal_contract_bails_when_the_completion_retry_record_is_invalid() {
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let repo_root = tmpdir.path().join("repo");
        let state = test_dispatch_state(&tmpdir, &repo_root, "codex");
        test_write_fixture(
            &state.completion_retry_state_file,
            "COMPLETION_RETRY_COUNT=not-a-number\n",
        );
        let object = Map::new();
        let code = emit_terminal_contract(&state, "complete", &object, None, 0, false);
        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
    }

    #[test]
    fn coverage_rows_forwards_to_the_scope_disposition_contract() {
        let coverage = sample_coverage(&"a".repeat(64), false);
        let rows = coverage_rows(&coverage);
        assert!(!rows.is_empty());
    }

    // -- quota detection -------------------------------------------------------

    #[test]
    fn quota_failure_detects_rate_limit_signatures_and_ignores_clean_logs() {
        let dir = tempfile::tempdir().expect("dir");
        let quota_log = dir.path().join("quota.log");
        test_write_fixture(&quota_log, "Error: usage limit reached, please retry later\n");
        assert!(quota_failure(&quota_log));
        let clean_log = dir.path().join("clean.log");
        test_write_fixture(&clean_log, "all good\n");
        assert!(!quota_failure(&clean_log));
        assert!(!quota_failure(&dir.path().join("missing.log")));
    }

    // -- dispatch_launch_and_route / run_launcher, end to end through a real
    // `scripts/larch.sh` stub (#8623 coverage) -------------------------------
    //
    // `state_larch` runs the verified `larch` entrypoint as a real child
    // process; there is no Rust-side seam to intercept it. These tests stand
    // up a fixture plugin root whose `scripts/larch.sh` plays the external
    // implementer launcher, so `dispatch_launch_and_route` and everything it
    // calls (`run_launcher`, `route_manifest`, `complete_preflight_and_commit`,
    // `emit_terminal_contract`) run for real. The control files the stub reads
    // live beside `--manifest-path`, which is unique per test tmpdir, so
    // concurrent tests cannot race each other through it.

    /// Answers `agent launch-{codex,cursor}-implement` and `oos
    /// materialize-manifest`. Every other verb is a harmless no-op, matching
    /// how the real dispatcher tolerates a failed non-fatal forwarded call.
    #[cfg(unix)]
    const LAUNCH_STUB: &str = r#"#!/usr/bin/env bash
set -euo pipefail

manifest=""
qa_pending=""
args=("$@")
i=0
while [ "$i" -lt "${#args[@]}" ]; do
  case "${args[$i]}" in
    --manifest-path) manifest="${args[$((i + 1))]}"; i=$((i + 2)) ;;
    --qa-pending-path) qa_pending="${args[$((i + 1))]}"; i=$((i + 2)) ;;
    *) i=$((i + 1)) ;;
  esac
done

case "${1:-} ${2:-}" in
  "agent launch-codex-implement"|"agent launch-cursor-implement")
    control="$(dirname "$manifest")"
    mode="complete"
    if [ -f "$control/launch-stub-mode.txt" ]; then
      mode="$(cat "$control/launch-stub-mode.txt")"
    fi
    count_file="$control/launch-stub-count.txt"
    count=0
    if [ -f "$count_file" ]; then
      count="$(cat "$count_file")"
    fi
    count=$((count + 1))
    printf '%s' "$count" > "$count_file"
    write_manifest=true
    if [ "$mode" = "empty-then-complete" ] && [ "$count" -eq 1 ]; then
      write_manifest=false
    fi
    if [ "$write_manifest" = true ]; then
      printf 'external edit %s\n' "$count" > repo-edit.txt
      cp "$control/launch-stub-manifest.json" "$manifest"
      if [ -f "$control/launch-stub-qa.json" ]; then
        cp "$control/launch-stub-qa.json" "$qa_pending"
      fi
    fi
    echo "LAUNCHER_EXIT=0"
    if [ "$write_manifest" = true ]; then
      echo "MANIFEST_WRITTEN=true"
    else
      echo "MANIFEST_WRITTEN=false"
    fi
    echo "STATUS=ok"
    exit 0
    ;;
  "oos materialize-manifest")
    for arg in "${args[@]}"; do
      if [ "$arg" = "--count-only" ]; then
        echo 0
        exit 0
      fi
    done
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
"#;

    #[cfg(unix)]
    const COMPLETE_MANIFEST: &str = r#"{"schema_version":1,"status":"complete","files_touched":[{"path":"repo-edit.txt"}],"tests_added_or_modified":[],"summary_bullets":["Implemented the stub change."],"commit_message":"Implement stub feature for coverage","todos_left":[],"oos_observations":[],"difficulty":{"predicted_tier":"TRIVIAL","confidence":"high","rationale":"Stub rating for a coverage-only launch."}}"#;

    /// A ready-to-launch `codex` state whose stub script and manifest control
    /// files live under `state.manifest_path`'s own directory.
    ///
    /// Writes a trivial `plan.txt` (no firm-scope paths, so plan coverage is
    /// `advisory`/non-disposition-required) and freezes `step2-baseline.txt`
    /// up front: this repo fixture has no remote, so `resolve_baseline` falls
    /// back to that frozen file instead of `origin/HEAD`.
    #[cfg(unix)]
    fn launch_stub_state(tmpdir: &tempfile::TempDir, repo_root: &Path) -> DispatchState {
        let mut state = test_dispatch_state(tmpdir, repo_root, "codex");
        state.baseline_sha = head_sha(repo_root);
        state.spawn_branch = abbrev_ref(repo_root);
        test_write_fixture(&state.plan_file, "");
        test_write_fixture(&state.feature_file, "Coverage fixture feature.\n");
        ensure_step2_baseline(tmpdir.path(), Some(repo_root));
        test_stub_larch_sh(&state.plugin_root, LAUNCH_STUB);
        state
    }

    #[cfg(unix)]
    fn control_dir(state: &DispatchState) -> PathBuf {
        state
            .manifest_path
            .parent()
            .expect("manifest has a parent")
            .to_path_buf()
    }

    #[test]
    #[cfg(unix)]
    fn dispatch_launch_and_route_commits_a_complete_manifest_and_reports_success() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = launch_stub_state(&tmpdir, repo.path());
        test_write_fixture(
            &control_dir(&state).join("launch-stub-manifest.json"),
            COMPLETE_MANIFEST,
        );
        let mut request = test_base_step2_request(tmpdir.path(), "codex");
        let before_head = head_sha(repo.path());

        let code = dispatch_launch_and_route(&mut request, &mut state);

        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert_ne!(
            head_sha(repo.path()),
            before_head,
            "a complete manifest must commit the coder's edit"
        );
        let manifest_text = fs::read_to_string(&state.manifest_path).expect("manifest");
        assert!(manifest_text.contains("\"complete\""));
    }

    #[test]
    #[cfg(unix)]
    fn dispatch_launch_and_route_retries_once_then_commits_after_an_empty_first_launch() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = launch_stub_state(&tmpdir, repo.path());
        let control = control_dir(&state);
        test_write_fixture(&control.join("launch-stub-mode.txt"), "empty-then-complete");
        test_write_fixture(&control.join("launch-stub-manifest.json"), COMPLETE_MANIFEST);
        let mut request = test_base_step2_request(tmpdir.path(), "codex");
        let before_head = head_sha(repo.path());

        let code = dispatch_launch_and_route(&mut request, &mut state);

        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert_eq!(
            fs::read_to_string(control.join("launch-stub-count.txt")).expect("count"),
            "2",
            "an empty first launch must trigger exactly one relaunch"
        );
        assert_ne!(
            head_sha(repo.path()),
            before_head,
            "the retried launch's complete manifest must still commit"
        );
    }

    #[test]
    #[cfg(unix)]
    fn dispatch_launch_and_route_routes_a_needs_qa_manifest_without_committing() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = launch_stub_state(&tmpdir, repo.path());
        let control = control_dir(&state);
        test_write_fixture(
            &control.join("launch-stub-manifest.json"),
            r#"{"schema_version":1,"status":"needs_qa","needs_qa":{"questions":[{"id":"q1","text":"Please confirm scope."}]}}"#,
        );
        test_write_fixture(
            &control.join("launch-stub-qa.json"),
            r#"{"questions":[{"id":"q1","text":"Please confirm scope."}]}"#,
        );
        let mut request = test_base_step2_request(tmpdir.path(), "codex");
        let before_head = head_sha(repo.path());

        let code = dispatch_launch_and_route(&mut request, &mut state);

        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert_eq!(
            head_sha(repo.path()),
            before_head,
            "a needs_qa manifest must not commit"
        );
        assert!(state.qa_pending_path.is_file());
    }

    #[test]
    #[cfg(unix)]
    fn dispatch_launch_and_route_routes_a_bailed_manifest_without_committing() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let mut state = launch_stub_state(&tmpdir, repo.path());
        test_write_fixture(
            &control_dir(&state).join("launch-stub-manifest.json"),
            r#"{"schema_version":1,"status":"bailed","bail_reason":"stub bail for coverage"}"#,
        );
        let mut request = test_base_step2_request(tmpdir.path(), "codex");
        let before_head = head_sha(repo.path());

        let code = dispatch_launch_and_route(&mut request, &mut state);

        assert_eq!(format!("{code:?}"), format!("{:?}", ExitCode::SUCCESS));
        assert_eq!(
            head_sha(repo.path()),
            before_head,
            "a bailed manifest must not commit"
        );
    }

    #[test]
    #[cfg(unix)]
    fn run_launcher_reports_the_external_stubs_kv_envelope() {
        let repo = test_init_repo();
        test_write_fixture(&repo.path().join("a.txt"), "one\n");
        test_commit_everything(repo.path(), "base");
        let tmpdir = tempfile::tempdir().expect("tmpdir");
        let state = launch_stub_state(&tmpdir, repo.path());
        test_write_fixture(
            &control_dir(&state).join("launch-stub-manifest.json"),
            COMPLETE_MANIFEST,
        );

        let run = run_launcher(&state);

        assert_eq!(run.wrapper_rc, 0);
        assert_eq!(run.launcher_exit, "0");
        assert_eq!(run.manifest_written, "true");
        assert_eq!(run.status, "ok");
        assert!(state.manifest_path.is_file());
    }
}
