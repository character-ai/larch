// `implement checks-commit-route` composite, included into
// `implement_commit_route_commands.rs`.

/// Resolve the session `REPO_ROOT`, failing closed with the retired diagnostic.
fn session_validated_repo_root(tmpdir: &Path) -> Result<PathBuf, String> {
    let resolve = resolve_repo_root_output(tmpdir);
    if !resolve.status().success() {
        let detail_raw = {
            let stderr = stderr_text(&resolve);
            if stderr.trim().is_empty() {
                stdout_text(&resolve)
            } else {
                stderr
            }
        };
        let detail = detail_raw.trim();
        let detail = detail.strip_prefix("ERROR=").unwrap_or(detail);
        let detail = if detail.is_empty() {
            "resolve-repo-root failed"
        } else {
            detail
        };
        return Err(format!("checks-commit-route: {detail}"));
    }
    let text = stdout_text(&resolve);
    let root = text
        .lines()
        .find_map(|line| line.strip_prefix("REPO_ROOT="))
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "checks-commit-route: REPO_ROOT missing from resolve-repo-root".to_owned())?;
    Ok(PathBuf::from(root))
}

/// Run the site's relevant checks leg and project its first KV line.
fn run_relevant_checks_for_site(
    plugin_root: &Path,
    tmpdir: &Path,
    repo_root: &Path,
    checks_site: &str,
    deadline_ms: u64,
) -> (BTreeMap<String, String>, bool) {
    let env = [
        (
            ChildEnvironment::ClaudeProjectDir,
            repo_root.as_os_str().to_owned(),
        ),
        (ChildEnvironment::RepoRoot, repo_root.as_os_str().to_owned()),
        (
            ChildEnvironment::ImplementTmpdir,
            tmpdir.as_os_str().to_owned(),
        ),
    ];
    let args = checks_run_relevant_args(checks_site, tmpdir, repo_root);
    let result = run_larch(plugin_root, repo_root, &args, &env, leg_timeout(deadline_ms));
    let output = match result {
        Ok(output) => output,
        Err(_error) => {
            let mut fail = BTreeMap::new();
            fail.insert("STATUS".to_owned(), "fail".to_owned());
            fail.insert("FAILURE_REASON".to_owned(), "checks-leg-timeout".to_owned());
            return (fail, true);
        }
    };
    let rc = output.status().code().unwrap_or(1);
    let stdout = stdout_text(&output);
    let first_line = stdout.lines().next().unwrap_or("");
    let mut captured = parse_whitespace_kv_line(first_line);
    if captured.is_empty() {
        captured.insert("STATUS".to_owned(), "fail".to_owned());
        captured.insert("FAILURE_REASON".to_owned(), "checks-child-failed".to_owned());
        captured.insert(
            "EXIT_CODE".to_owned(),
            if rc == 0 { "1".to_owned() } else { rc.to_string() },
        );
    } else if rc != 0 {
        captured.remove("RELEVANT_CHECKS_OK");
        captured.remove("RELEVANT_CHECKS_SKIPPED");
        captured.entry("STATUS".to_owned()).or_insert_with(|| "fail".to_owned());
        captured
            .entry("FAILURE_REASON".to_owned())
            .or_insert_with(|| "checks-child-failed".to_owned());
        captured
            .entry("EXIT_CODE".to_owned())
            .or_insert_with(|| rc.to_string());
    }
    (captured, false)
}

/// Recompute the Step 4 recovery pathspec and gate it against plan scope.
fn run_step4_recovery_recompute(
    plugin_root: &Path,
    tmpdir: &Path,
    repo_root: &Path,
) -> i32 {
    if !tmpdir.join("recovery-metadata.json").is_file() {
        return 0;
    }
    if capture_postlaunch_porcelain(repo_root, tmpdir) != 0 {
        return 1;
    }
    let final_paths = tmpdir.join("step2-recovery-paths-final.nul");
    let inputs = larch_core::RecoveryPorcelainInputs {
        prelaunch_porcelain: tmpdir.join("step2-prelaunch-porcelain.nul"),
        postlaunch_porcelain: tmpdir.join("step2-postlaunch-porcelain.nul"),
        prelaunch_digests: tmpdir.join("step2-prelaunch-content-digests.txt"),
    };
    if larch_core::compute_recovery_paths(repo_root, tmpdir, &inputs, &final_paths).is_err() {
        return 1;
    }
    let plan_file = tmpdir.join("plan.txt");
    let args = vec![
        OsString::from("dirty-tree"),
        OsString::from("scope-check"),
        OsString::from("--plan-file"),
        plan_file.into_os_string(),
        OsString::from("--paths-file"),
        final_paths.into_os_string(),
    ];
    match run_larch(plugin_root, repo_root, &args, &[], Duration::from_secs(600)) {
        Ok(output) if output.status().code() == Some(0) => 0,
        Ok(output) => {
            let _ = std::io::stderr().write_all(output.stdout());
            forward_stderr(&output);
            emit_kv("BAIL_REASON", "recovery-out-of-scope");
            output.status().code().filter(|code| *code != 0).unwrap_or(1)
        }
        Err(error) => {
            eprintln!("checks-commit-route: recovery scope-check failed: {error}");
            emit_kv("BAIL_REASON", "recovery-out-of-scope");
            1
        }
    }
}

// -- Step 4 commit leg -----------------------------------------------------

fn step4_noop(cwd: &Path, reason: &str) -> (&'static str, String) {
    let sha = head_sha(cwd);
    let short = if sha.len() >= 12 { &sha[..12] } else { sha.as_str() };
    eprintln!("⏩ 4: commit (impl) status=skip reason={reason} sha={short} elapsed=0s");
    ("noop", "COMMIT_ROUTE_OUTCOME=noop\nCOMMIT_OUTCOME=noop\n".to_owned())
}

fn step4_commit_seed_from_files(
    message_path: &Path,
    pathspec: &Path,
    refresh_step3_self_edits: bool,
) -> Option<Step4CommitSeed> {
    if !path_readable_nonempty(message_path) {
        return None;
    }
    let message = read_redacted_message(message_path);
    if message.is_empty() || !path_readable_nonempty(pathspec) {
        return None;
    }
    Some(Step4CommitSeed {
        message,
        pathspec: Some(pathspec.to_path_buf()),
        noop_reason: String::new(),
        refresh_step3_self_edits,
    })
}

/// Build the NUL pathspec of the dispatcher-committed dirty paths.
fn dispatcher_committed_dirty_pathspec(tmpdir: &Path, repo_root: &Path) -> (Option<PathBuf>, bool) {
    let Some(paths) = working_tree_paths(repo_root) else {
        return (None, false);
    };
    if paths.is_empty() {
        return (None, true);
    }
    let pathspec = tmpdir.join("dispatcher-committed-dirty-paths.nul");
    if write_bytes_atomic(&pathspec, &nul_pathspec_bytes(&paths)).is_err() {
        return (None, false);
    }
    (Some(pathspec), true)
}

fn step4_dispatcher_committed_seed(tmpdir: &Path, repo_root: &Path) -> Option<Step4CommitSeed> {
    let (pathspec, status_ok) = dispatcher_committed_dirty_pathspec(tmpdir, repo_root);
    if !status_ok {
        return None;
    }
    pathspec.map_or_else(
        || {
            Some(Step4CommitSeed {
                message: String::new(),
                pathspec: None,
                noop_reason: "dispatcher-committed".to_owned(),
                refresh_step3_self_edits: false,
            })
        },
        |pathspec| {
            Some(Step4CommitSeed {
                message: "Apply post-dispatch checks fixes".to_owned(),
                pathspec: Some(pathspec),
                noop_reason: String::new(),
                refresh_step3_self_edits: false,
            })
        },
    )
}

fn resolve_step4_commit_seed(
    tmpdir: &Path,
    repo_root: &Path,
    dispatcher_commit_complete: bool,
) -> Option<Step4CommitSeed> {
    if path_readable_nonempty(&tmpdir.join("recovery-metadata.json")) {
        return step4_commit_seed_from_files(
            &tmpdir.join("recovery-commit-message.txt"),
            &tmpdir.join("step2-recovery-paths-final.nul"),
            false,
        );
    }
    if path_readable_nonempty(&tmpdir.join("implementation-commit-message.txt")) {
        return step4_commit_seed_from_files(
            &tmpdir.join("implementation-commit-message.txt"),
            &tmpdir.join("implementation-commit-paths.nul"),
            true,
        );
    }
    if dispatcher_commit_complete {
        return step4_dispatcher_committed_seed(tmpdir, repo_root);
    }
    None
}

/// Union still-attributed Step 3 self-edits into the frozen pathspec.
fn step4_pathspec_with_step3_self_edits(
    tmpdir: &Path,
    pathspec: &Path,
    repo_root: &Path,
) -> (Option<PathBuf>, bool) {
    let Some(dirty_paths) = working_tree_paths(repo_root) else {
        return (None, false);
    };
    if dirty_paths.is_empty() {
        return (Some(pathspec.to_path_buf()), true);
    }
    let additions = step3_self_edit_additions(tmpdir, repo_root, &dirty_paths);
    if additions.is_empty() {
        return (Some(pathspec.to_path_buf()), true);
    }
    let mut union: std::collections::BTreeSet<String> =
        read_nul_pathspec(pathspec).into_iter().collect();
    union.extend(additions);
    let paths: Vec<String> = union.into_iter().collect();
    let refreshed = tmpdir.join("step4-commit-paths.nul");
    if write_bytes_atomic(&refreshed, &nul_pathspec_bytes(&paths)).is_err() {
        return (None, false);
    }
    (Some(refreshed), true)
}

fn pathspec_clean_relative_to_head(repo_root: &Path, pathspec: &Path) -> bool {
    let paths = read_nul_pathspec(pathspec);
    if paths.is_empty() {
        return false;
    }
    subset_clean(repo_root, Some(&paths)).unwrap_or(false)
}

fn step4_commit_failure(
    ctx: &StallContext,
    exit_code: i32,
    reason: &str,
    stdout: String,
    stderr: String,
) -> &'static str {
    let failure = CommitRouteFailure {
        site_name: "step4".to_owned(),
        site: STEP4_COMMIT_SITE,
        exit_code,
        reason: reason.to_owned(),
        stdout,
        stderr,
    };
    let failure_log = write_failure_log(ctx.tmpdir, &failure);
    log_failure(
        ctx.plugin_root,
        ctx.cwd,
        ctx.tmpdir,
        "step4",
        STEP4_COMMIT_SITE.failure_log_label,
        "scripts/larch.sh implement commit",
        exit_code,
        &failure_log,
    );
    let seeded = seed_durable_stall(
        ctx.plugin_root,
        ctx.cwd,
        ctx.tmpdir,
        STEP4_COMMIT_SITE.stall_step,
        STEP4_COMMIT_SITE.bail_reason,
    );
    if seeded { "seeded-stall" } else { "seed-failed" }
}

fn run_step4_commit_leg(ctx: &StallContext, deadline_ms: u64) -> (String, String) {
    let seed_file = ctx.tmpdir.join("ship-seed-input.env");
    let manifest_path = read_kv_first(&seed_file, "MANIFEST_PATH");
    let dispatcher_committed = read_kv_first(&seed_file, "DISPATCHER_COMMITTED") == "true";
    let dispatcher_commit_complete = dispatcher_committed
        && !manifest_path.is_empty()
        && path_readable_nonempty(Path::new(&manifest_path));
    let Some(seed) = resolve_step4_commit_seed(ctx.tmpdir, ctx.cwd, dispatcher_commit_complete)
    else {
        return ("seed-failed".to_owned(), "COMMIT_ROUTE_OUTCOME=seed-failed\n".to_owned());
    };
    let Some(mut pathspec) = seed.pathspec.clone() else {
        let (outcome, stdout) = step4_noop(ctx.cwd, &seed.noop_reason);
        return (outcome.to_owned(), stdout);
    };
    if seed.refresh_step3_self_edits {
        let Some(repo_root) = repo_root_toplevel() else {
            return ("seed-failed".to_owned(), "COMMIT_ROUTE_OUTCOME=seed-failed\n".to_owned());
        };
        let (refreshed, ok) = step4_pathspec_with_step3_self_edits(ctx.tmpdir, &pathspec, &repo_root);
        match (ok, refreshed) {
            (true, Some(refreshed)) => pathspec = refreshed,
            _ => {
                return (
                    "seed-failed".to_owned(),
                    "COMMIT_ROUTE_OUTCOME=seed-failed\n".to_owned(),
                );
            }
        }
    }
    if pathspec_clean_relative_to_head(ctx.cwd, &pathspec) {
        let noop_reason = if dispatcher_commit_complete {
            "dispatcher-committed"
        } else {
            "already-committed"
        };
        let (outcome, stdout) = step4_noop(ctx.cwd, noop_reason);
        return (outcome.to_owned(), stdout);
    }
    let env = [(
        ChildEnvironment::ImplementTmpdir,
        ctx.tmpdir.as_os_str().to_owned(),
    )];
    let args = vec![
        OsString::from("implement"),
        OsString::from("commit"),
        OsString::from("--message"),
        OsString::from(&seed.message),
        OsString::from("--pathspec-from-file"),
        pathspec.into_os_string(),
        OsString::from("--pathspec-file-nul"),
    ];
    match run_larch(ctx.plugin_root, ctx.cwd, &args, &env, leg_timeout(deadline_ms)) {
        Err(error) => {
            let outcome = step4_commit_failure(ctx, 124, "implementation-commit-timeout", String::new(), error);
            (outcome.to_owned(), String::new())
        }
        Ok(output) => {
            let rc = output.status().code().unwrap_or(1);
            let stdout = stdout_text(&output);
            let committed = parse_line_anchored(&stdout, "COMMITTED");
            if rc == 0 && committed == ["true"] {
                ("continue".to_owned(), format!("COMMIT_ROUTE_OUTCOME=continue\n{stdout}"))
            } else {
                let outcome = step4_commit_failure(
                    ctx,
                    if rc == 0 { 1 } else { rc },
                    "implementation-commit-failed",
                    stdout.clone(),
                    stderr_text(&output),
                );
                (outcome.to_owned(), format!("COMMIT_ROUTE_OUTCOME={outcome}\n{stdout}"))
            }
        }
    }
}

// -- commit-route leg ------------------------------------------------------

fn run_commit_route_leg(
    ctx: &StallContext,
    site_name: &str,
    site: &CommitRouteSite,
    deadline_ms: u64,
) -> (String, String) {
    let args = vec![
        OsString::from("implement"),
        OsString::from("commit-route"),
        OsString::from("--site"),
        OsString::from(site_name),
        OsString::from("--implement-tmpdir"),
        ctx.tmpdir.as_os_str().to_owned(),
        OsString::from("--emit-next-action"),
        OsString::from("false"),
    ];
    let result = run_larch(ctx.plugin_root, ctx.cwd, &args, &[], leg_timeout(deadline_ms));
    let output = match result {
        Ok(output) => output,
        Err(error) => {
            let failure = CommitRouteFailure {
                site_name: site_name.to_owned(),
                site: site.clone(),
                exit_code: 124,
                reason: "commit-leg-timeout".to_owned(),
                stdout: String::new(),
                stderr: error,
            };
            let failure_log = write_failure_log(ctx.tmpdir, &failure);
            log_failure(
                ctx.plugin_root,
                ctx.cwd,
                ctx.tmpdir,
                site_name,
                site.failure_log_label,
                "scripts/larch.sh review-and-fix commit-fixes --stage-all",
                124,
                &failure_log,
            );
            let seeded = seed_durable_stall(
                ctx.plugin_root,
                ctx.cwd,
                ctx.tmpdir,
                site.stall_step,
                site.bail_reason,
            );
            let outcome = if seeded { "seeded-stall" } else { "seed-failed" };
            return (outcome.to_owned(), String::new());
        }
    };
    let stdout = stdout_text(&output);
    let outcomes = parse_line_anchored(&stdout, "COMMIT_ROUTE_OUTCOME");
    let valid = ["continue", "seeded-stall", "seed-failed", "noop"];
    if outcomes.len() != 1 || !valid.contains(&outcomes[0].as_str()) {
        return ("seed-failed".to_owned(), stdout);
    }
    (outcomes[0].clone(), stdout)
}

// -- rebase checkpoint relays ----------------------------------------------

fn run_rebase_checkpoint(
    plugin_root: &Path,
    cwd: &Path,
    step_prefix: &str,
    short_name: &str,
    forked_target: &str,
) -> i32 {
    let args = vec![
        OsString::from("push"),
        OsString::from("checkpoint-probe"),
        OsString::from(step_prefix),
        OsString::from(short_name),
        OsString::from("--forked-target"),
        OsString::from(forked_target),
    ];
    match run_larch(plugin_root, cwd, &args, &[], Duration::from_secs(900)) {
        Ok(output) => {
            for line in stdout_text(&output).lines() {
                if !line.is_empty() {
                    println!("{line}");
                }
            }
            forward_stderr(&output);
            output.status().code().unwrap_or(1)
        }
        Err(error) => {
            eprintln!("checks-commit-route: checkpoint probe failed: {error}");
            1
        }
    }
}

// -- entry -----------------------------------------------------------------

struct ChecksArgs {
    checks_site: String,
    commit_site: String,
    checks_deadline_ms: u64,
    commit_deadline_ms: u64,
    emit_step7_breadcrumb: bool,
    rebase_checkpoint_4r: bool,
    rebase_checkpoint_7r: bool,
    forked_target: String,
}

fn parse_deadline(value: Option<&OsStr>, default: u64) -> Result<u64, ()> {
    value.map_or(Ok(default), |raw| {
        raw.to_string_lossy().parse::<u64>().map_err(|_| ())
    })
}

/// `implement checks-commit-route` compatibility command.
pub fn checks_commit_route(arguments: &[OsString]) -> ExitCode {
    let flags = ["--emit-step7-breadcrumb", "--rebase-checkpoint-4r", "--rebase-checkpoint-7r"];
    let parsed = match parse_required_with_help(
        arguments,
        CHECKS_PROG,
        CHECKS_USAGE,
        CHECKS_HELP,
        &CHECKS_OPTIONS,
        &flags,
        &["--checks-site", "--commit-site"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let commit_sites = ["step4", "step5-resume-handoff", "step5-self-review", "step7"];
    if let Some(error) = choice_error(
        arguments,
        &CHECKS_OPTIONS,
        &[
            ("--commit-site", &commit_sites),
            ("--forked-target", &["true", "false"]),
        ],
    ) {
        return usage_error(CHECKS_USAGE, CHECKS_PROG, &error, 2);
    }
    let Ok(checks_deadline_ms) =
        parse_deadline(parsed.value("--checks-deadline-ms"), CHECKS_DEADLINE_MS)
    else {
        return usage_error(
            CHECKS_USAGE,
            CHECKS_PROG,
            "argument --checks-deadline-ms: invalid int value",
            2,
        );
    };
    let Ok(commit_deadline_ms) =
        parse_deadline(parsed.value("--commit-deadline-ms"), COMMIT_ROUTE_DEADLINE_MS)
    else {
        return usage_error(
            CHECKS_USAGE,
            CHECKS_PROG,
            "argument --commit-deadline-ms: invalid int value",
            2,
        );
    };
    let args = ChecksArgs {
        checks_site: parsed
            .value("--checks-site")
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default(),
        commit_site: parsed
            .value("--commit-site")
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default(),
        checks_deadline_ms,
        commit_deadline_ms,
        emit_step7_breadcrumb: parsed.flag("--emit-step7-breadcrumb"),
        rebase_checkpoint_4r: parsed.flag("--rebase-checkpoint-4r"),
        rebase_checkpoint_7r: parsed.flag("--rebase-checkpoint-7r"),
        forked_target: parsed.value("--forked-target").map_or_else(
            || "false".to_owned(),
            |value| value.to_string_lossy().into_owned(),
        ),
    };

    let tmpdir = match env::var("IMPLEMENT_TMPDIR") {
        Ok(raw) if !raw.is_empty() => PathBuf::from(raw),
        _ => {
            eprintln!("IMPLEMENT_TMPDIR required");
            return ExitCode::from(2);
        }
    };
    let plugin_root = match resolve_plugin_root_or_tmpdir(&tmpdir) {
        Ok(root) => root,
        Err(error) => {
            eprintln!("checks-commit-route: {error}");
            return ExitCode::from(2);
        }
    };
    checks_commit_route_impl(&plugin_root, &tmpdir, &args)
}

fn checks_commit_route_impl(plugin_root: &Path, tmpdir: &Path, args: &ChecksArgs) -> ExitCode {
    let repo_root = match session_validated_repo_root(tmpdir) {
        Ok(root) => root,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(2);
        }
    };
    let (captured, timed_out) = run_relevant_checks_for_site(
        plugin_root,
        tmpdir,
        &repo_root,
        &args.checks_site,
        args.checks_deadline_ms,
    );
    println!("{}", checks_relay_line(&captured));
    if timed_out || !checks_pass(&captured) {
        emit_kv("NEXT_ACTION", "checks-failed");
        return ExitCode::SUCCESS;
    }
    if args.emit_step7_breadcrumb {
        eprintln!("> **🔶 /implement 7: commit (review)**");
    }
    let ctx = StallContext {
        plugin_root,
        cwd: &repo_root,
        tmpdir,
    };
    let (outcome, commit_stdout) = if args.commit_site == "step4" {
        let recompute_rc = run_step4_recovery_recompute(plugin_root, tmpdir, &repo_root);
        if recompute_rc != 0 {
            return ExitCode::from(u8::try_from(recompute_rc).unwrap_or(1));
        }
        run_step4_commit_leg(&ctx, args.commit_deadline_ms)
    } else {
        let Some(site) = commit_route_site(&args.commit_site) else {
            eprintln!("checks-commit-route: invalid commit site");
            return ExitCode::from(2);
        };
        run_commit_route_leg(&ctx, &args.commit_site, &site, args.commit_deadline_ms)
    };
    if !commit_stdout.is_empty() {
        print!("{commit_stdout}");
        if !commit_stdout.ends_with('\n') {
            println!();
        }
    }
    match outcome.as_str() {
        "continue" | "noop" => {
            let coverage_rc = relay_scope_coverage(tmpdir);
            if coverage_rc != 0 {
                return ExitCode::from(u8::try_from(coverage_rc).unwrap_or(1));
            }
            if args.commit_site == "step4" && args.rebase_checkpoint_4r {
                let rc = run_rebase_checkpoint(
                    plugin_root,
                    &repo_root,
                    "4.r",
                    "commit (impl)",
                    &args.forked_target,
                );
                emit_kv("NEXT_ACTION", "continue");
                return ExitCode::from(u8::try_from(rc).unwrap_or(1));
            }
            let checkpoint_rc = if args.rebase_checkpoint_7r {
                run_rebase_checkpoint(
                    plugin_root,
                    &repo_root,
                    "7.r",
                    "commit (review)",
                    &args.forked_target,
                )
            } else {
                0
            };
            emit_kv("NEXT_ACTION", "continue");
            ExitCode::from(u8::try_from(checkpoint_rc).unwrap_or(1))
        }
        "seeded-stall" => {
            emit_kv("NEXT_ACTION", "stall");
            ExitCode::SUCCESS
        }
        _ => ExitCode::from(1),
    }
}
