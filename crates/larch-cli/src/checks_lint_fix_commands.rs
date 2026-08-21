//! Rust owners for `checks fixer-evidence` and `checks lint-fix` (#8625).
//!
//! `fixer-evidence` materializes one bounded, redacted checks-failure digest for
//! the ci-fixer subagent. `lint-fix` dispatches the delegated coder waterfall
//! (Claude, Codex, Cursor) against a captured checks log and applies the fix.
//!
//! The pure path resolution, site grammar, and evidence-path helpers live in
//! `larch_core::implement`; this module owns the impure orchestration.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::{
    ExactDiffRequest, GitPath as GitCliPath, GitRef, GixRepository, ResetMode, ResetRequest,
    RestoreRequest, TemporaryRoot, atomic_write_utf8_in,
    vendor_diagnostics::resolve_launcher_exit_from_files,
};
use larch_core::{
    Head, ObjectId, RepositoryRead, StatusOptions, VendorProgram, cursor_child_environment,
    implement::{
        self, CHECKS_FIXER_MAX_ROUNDS, CLAUDE_CI_FIX_MODEL, FIXER_LANE_TIMEOUT_SEC, FixOutcome,
        PRE_SHIP_ALL_TIERS_NO_DELTA_REASON, PROMPT_TAIL_BYTES, RepoPathState,
        build_checks_failure_digest, checks_fixer_evidence_path, classify_attempt_issue,
        coder_forbidden_paths, codex_lint_fix_prompt_appendix, compose_prompt, exhausted_outcome,
        forbidden_paths_match_count, is_known_site, ledger_phase_for_site,
        ledger_site_for_lint_site, ledger_step_for_site, ledger_trigger_for_lint_site,
        lint_fix_fast_fail_reason, path_matches_forbidden, read_log_file_text, read_log_tail,
        resolve_checks_log_path, sanitize_log_fence, site_label, snapshot_delta_paths,
        target_cmd_display_valid, tier_ledger_header, tier_ledger_line, valid_fixer_site,
        validate_session_tmpdir,
    },
    redact_run_log_payload, role_default,
};

use sha2::{Digest as _, Sha256};

use crate::{
    argparse_compat::parse_required_with_help,
    external_agent::{
        ExternalAgentLaunch, ExternalAgentRouting, run_external_agent_with_auth_retries,
    },
    git_command_runtime::GitCommandRuntime,
    implement_dispatch_commands::opt_string,
    launcher_support::{
        CursorPreflightRequest, cursor_launch_credential, cursor_model_argv, unix_seconds,
    },
    run_log_entry_commands::append_execution_issue,
    runtime_entrypoint::{run_verified_larch, run_verified_larch_with_timeout},
    timing_commands,
};

/// Margin added to the lane deadline for the larch bootstrap and teardown.
const LAUNCH_TIMEOUT_MARGIN: Duration = Duration::from_secs(120);
/// Bytes of the coder stderr-tail sidecar consulted for attempt classification.
const STDERR_TAIL_SCAN_BYTES: usize = 8192;
/// The `larch <domain>` selector for the verified stage/commit invocations.
const LARCH_GIT_DOMAIN: &str = "git";

const FIXER_EVIDENCE_PROG: &str = "cli.py checks fixer-evidence";
const FIXER_EVIDENCE_USAGE: &str = "usage: cli.py checks fixer-evidence [-h] --tmpdir TMPDIR --site SITE --round\n                                    ROUND --checks-log CHECKS_LOG";
const FIXER_EVIDENCE_HELP: &str = "usage: cli.py checks fixer-evidence [-h] --tmpdir TMPDIR --site SITE --round\n                                    ROUND --checks-log CHECKS_LOG\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --round ROUND\n  --checks-log CHECKS_LOG";

/// `checks fixer-evidence` compatibility command.
///
/// Mirrors Python `checks_fixer_evidence_main`: validate the tmpdir, site,
/// round, and checks-log candidate, then write the redacted failure digest to a
/// deterministic session-confined path.
pub fn checks_fixer_evidence(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        FIXER_EVIDENCE_PROG,
        FIXER_EVIDENCE_USAGE,
        FIXER_EVIDENCE_HELP,
        &["--tmpdir", "--site", "--round", "--checks-log"],
        &[],
        &["--tmpdir", "--site", "--round", "--checks-log"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir_raw = opt_string(parsed.value("--tmpdir"));
    let site = opt_string(parsed.value("--site"));
    let round_raw = opt_string(parsed.value("--round"));
    let checks_log = opt_string(parsed.value("--checks-log"));

    let (tmpdir, round_number) =
        match validate_fixer_evidence_args(&tmpdir_raw, &site, &round_raw, &checks_log) {
            Ok(validated) => validated,
            Err(error) => {
                println!("CHECKS_FIXER_EVIDENCE_STATUS={error}");
                return ExitCode::from(2);
            }
        };
    let Some(source) = resolve_checks_log_path(&checks_log, &tmpdir) else {
        println!("CHECKS_FIXER_EVIDENCE_STATUS=invalid-source");
        return ExitCode::from(2);
    };
    let Some(source_text) = read_log_file_text(&source) else {
        println!("CHECKS_FIXER_EVIDENCE_STATUS=source-unreadable");
        return ExitCode::from(1);
    };
    let output = checks_fixer_evidence_path(&tmpdir, &site, round_number);
    let digest = build_checks_failure_digest(&redact_run_log_payload(&source_text), &site);
    if !write_confined_evidence(&tmpdir, &output, &digest) {
        println!("CHECKS_FIXER_EVIDENCE_STATUS=write-failed");
        return ExitCode::from(1);
    }
    println!("CHECKS_FIXER_EVIDENCE_STATUS=ok");
    println!("CHECKS_FIXER_EVIDENCE_FILE={}", output.display());
    ExitCode::SUCCESS
}

/// Validate the tmpdir, site, and round; the checks-log candidate is resolved by
/// the caller so the source-path error stays distinct.
fn validate_fixer_evidence_args(
    tmpdir_raw: &str,
    site: &str,
    round_raw: &str,
    _checks_log: &str,
) -> Result<(std::path::PathBuf, u32), &'static str> {
    let Some(tmpdir) = validate_session_tmpdir(tmpdir_raw) else {
        return Err("invalid-tmpdir");
    };
    if !valid_fixer_site(site) {
        return Err("invalid-site");
    }
    let Ok(round_number) = round_raw.trim().parse::<i64>() else {
        return Err("invalid-round");
    };
    if round_number < 1 || round_number > i64::from(CHECKS_FIXER_MAX_ROUNDS) {
        return Err("invalid-round");
    }
    Ok((
        tmpdir,
        u32::try_from(round_number).unwrap_or(CHECKS_FIXER_MAX_ROUNDS),
    ))
}

/// Atomically publish the digest at mode 0o600, confined under the session root.
fn write_confined_evidence(tmpdir: &Path, output: &Path, digest: &str) -> bool {
    let Ok(root) = TemporaryRoot::resolve(Some(tmpdir)) else {
        return false;
    };
    atomic_write_utf8_in(&root, output, digest, false, 0o600).is_ok()
}

const LINT_FIX_PROG: &str = "cli.py checks lint-fix";
const LINT_FIX_USAGE: &str = "usage: cli.py checks lint-fix [-h] --tmpdir TMPDIR --site SITE --checks-log\n                              CHECKS_LOG [--repo-root REPO_ROOT]\n                              [--run-parent RUN_PARENT]";
const LINT_FIX_HELP: &str = "usage: cli.py checks lint-fix [-h] --tmpdir TMPDIR --site SITE --checks-log\n                              CHECKS_LOG [--repo-root REPO_ROOT]\n                              [--run-parent RUN_PARENT]\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --checks-log CHECKS_LOG\n  --repo-root REPO_ROOT\n  --run-parent RUN_PARENT";

/// `checks lint-fix` compatibility command (Python `checks_lint_fix_main`).
pub fn checks_lint_fix(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        LINT_FIX_PROG,
        LINT_FIX_USAGE,
        LINT_FIX_HELP,
        &[
            "--tmpdir",
            "--site",
            "--checks-log",
            "--repo-root",
            "--run-parent",
        ],
        &[],
        &["--tmpdir", "--site", "--checks-log"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir_raw = opt_string(parsed.value("--tmpdir"));
    let site = opt_string(parsed.value("--site"));
    let checks_log = opt_string(parsed.value("--checks-log"));
    let repo_root_arg = opt_string(parsed.value("--repo-root"));
    let run_parent_arg = opt_string(parsed.value("--run-parent"));

    let tmpdir_source = if tmpdir_raw.is_empty() {
        std::env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
    } else {
        tmpdir_raw
    };
    let Some(canonical_tmp) = validate_session_tmpdir(&tmpdir_source) else {
        println!("LINT_FIX_STATUS=failed");
        println!("FAILURE_REASON=tmpdir-validation");
        return ExitCode::from(2);
    };
    let repo_root = if repo_root_arg.is_empty() {
        default_repo_root()
    } else {
        repo_root_arg
    };
    let run_parent = if run_parent_arg.is_empty() {
        canonical_tmp
            .join("lint-fix-loop")
            .to_string_lossy()
            .into_owned()
    } else {
        run_parent_arg
    };
    let request = LintFixRequest {
        site,
        checks_log,
        repo_root,
        run_parent,
        allowed_tmpdir: canonical_tmp.to_string_lossy().into_owned(),
        claude_present: binary_present("CLAUDE_BINARY_FOUND", &canonical_tmp, "claude"),
        codex_present: binary_present("CODEX_BINARY_FOUND", &canonical_tmp, "codex"),
        cursor_present: binary_present("CURSOR_BINARY_FOUND", &canonical_tmp, "cursor"),
    };
    let outcome = run_lint_fix(&request);
    emit_lint_fix(&outcome)
}

/// Resolve the ambient repository root (Python `default_repo_root`).
fn default_repo_root() -> String {
    std::env::current_dir().map_or_else(
        |_| ".".to_owned(),
        |path| path.to_string_lossy().into_owned(),
    )
}

/// Recorded-or-probed availability of a coder binary (Python `_binary_flag`).
fn binary_present(name: &str, tmpdir: &Path, binary: &str) -> bool {
    if let Ok(value) = std::env::var(name)
        && (value == "true" || value == "false")
    {
        return value == "true";
    }
    let session_env = tmpdir.join("session-env.sh");
    if let Ok(text) = fs::read_to_string(&session_env) {
        for line in text.lines() {
            if let Some(rest) = line.strip_prefix(&format!("{name}="))
                && matches!(rest.trim_end_matches('\r'), "true" | "false")
            {
                return rest.trim_end_matches('\r') == "true";
            }
        }
    }
    which_on_path(binary)
}

/// True when `binary` resolves on `PATH`.
fn which_on_path(binary: &str) -> bool {
    std::env::var_os("PATH").is_some_and(|path| {
        std::env::split_paths(&path)
            .map(|directory| directory.join(binary))
            .any(|candidate| candidate.is_file() || candidate.is_symlink())
    })
}

/// Emit the `KEY=value` grammar the still-Python repair loop parses.
fn emit_lint_fix(outcome: &FixOutcome) -> ExitCode {
    println!("LINT_FIX_STATUS={}", outcome.status);
    if let Some(reason) = &outcome.failure_reason {
        println!("FAILURE_REASON={reason}");
    }
    if !outcome.stderr_tail_path.is_empty() {
        println!("STDERR_TAIL_PATH={}", outcome.stderr_tail_path);
    }
    if !outcome.coder_log_path.is_empty() {
        println!("CODER_LOG_FILE={}", outcome.coder_log_path);
    }
    if outcome.ledger_ready {
        println!("LINT_FIX_LEDGER_READY=true");
        println!("LINT_FIX_LEDGER_SITE={}", outcome.ledger_site);
        println!("LINT_FIX_LEDGER_TRIGGER={}", outcome.ledger_trigger);
        println!("LINT_FIX_LEDGER_STEP={}", outcome.ledger_step);
        println!("LINT_FIX_LEDGER_PHASE={}", outcome.ledger_phase);
        println!("LINT_FIX_LEDGER_DISPATCHER={}", outcome.ledger_dispatcher);
        if let Some(code) = outcome.ledger_exit_code {
            println!("LINT_FIX_LEDGER_EXIT_CODE={code}");
        }
        if !outcome.ledger_failure_detail_log.is_empty() {
            println!(
                "LINT_FIX_LEDGER_FAILURE_DETAIL_LOG={}",
                outcome.ledger_failure_detail_log
            );
        }
    }
    if !outcome.tier_ledger_path.is_empty() {
        println!("LINT_FIX_TIER_LEDGER_PATH={}", outcome.tier_ledger_path);
    }
    if outcome.status == "applied" && !outcome.delta_paths.is_empty() {
        println!("LINT_FIX_DELTA_COUNT={}", outcome.delta_paths.len());
        for (index, path) in outcome.delta_paths.iter().enumerate() {
            println!("LINT_FIX_DELTA_PATH_{index}={path}");
        }
    }
    if matches!(
        outcome.status.as_str(),
        "applied" | "no-changes" | "main-agent-required"
    ) {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

/// Inputs to one lint-fix dispatch (mirrors the Python `run_lint_fix` keywords).
struct LintFixRequest {
    site: String,
    checks_log: String,
    repo_root: String,
    run_parent: String,
    allowed_tmpdir: String,
    claude_present: bool,
    codex_present: bool,
    cursor_present: bool,
}

/// Run one lint-fix dispatch and record the lane timing (Python `run_lint_fix`).
fn run_lint_fix(request: &LintFixRequest) -> FixOutcome {
    let timing_root = resolve_timing_root(&request.allowed_tmpdir, &request.run_parent);
    let start_s = unix_seconds();
    let outcome = run_lint_fix_impl(request);
    if let Some(root) = timing_root
        && outcome.coder_tool.as_deref() != Some("claude")
    {
        let exit_code = i32::from(!matches!(
            outcome.status.as_str(),
            "applied" | "no-changes" | "main-agent-required"
        ));
        let output = root.join("claude-lint-fix.txt");
        let arguments = timing_commands::vendor_timing_arguments(
            "claude",
            "claude-lint-fix",
            start_s,
            unix_seconds(),
            &output,
            exit_code,
            "complete",
        );
        let _recorded = timing_commands::record_vendor_task(&arguments);
    }
    outcome
}

/// Resolve the directory that receives the lint-fix timing ledger.
fn resolve_timing_root(allowed_tmpdir: &str, run_parent: &str) -> Option<PathBuf> {
    if !allowed_tmpdir.is_empty()
        && let Ok(candidate) = fs::canonicalize(allowed_tmpdir)
        && candidate.is_dir()
    {
        return Some(candidate);
    }
    let parent = fs::canonicalize(run_parent).ok()?;
    let parent = parent.parent()?.to_path_buf();
    parent.is_dir().then_some(parent)
}

/// Terminal outcome carrying the initialized tier-ledger path (Python `_with_tier_ledger`).
fn with_tier_ledger(mut outcome: FixOutcome, tier_ledger: &str) -> FixOutcome {
    if outcome.tier_ledger_path.is_empty() {
        tier_ledger.clone_into(&mut outcome.tier_ledger_path);
    }
    outcome
}

/// The delegated dispatch engine (Python `_run_lint_fix_impl`).
#[allow(clippy::too_many_lines)]
fn run_lint_fix_impl(request: &LintFixRequest) -> FixOutcome {
    let site = request.site.as_str();
    if !is_known_site(site) {
        return FixOutcome::failed("unknown-site");
    }
    if !target_cmd_display_valid(site, None) {
        return FixOutcome::failed("target-cmd-display-invalid");
    }
    let Some(allowed_root) = resolve_allowed_root(&request.allowed_tmpdir, &request.run_parent)
    else {
        return FixOutcome::failed("checks-log-invalid");
    };
    let Some(log_path) = resolve_checks_log_path(&request.checks_log, &allowed_root) else {
        return FixOutcome::failed("checks-log-invalid");
    };
    // The ledger detail log re-resolves the same candidate under the session root.
    let ledger_root = if request.allowed_tmpdir.is_empty() {
        allowed_root.clone()
    } else {
        match fs::canonicalize(&request.allowed_tmpdir) {
            Ok(root) => root,
            Err(_) => return FixOutcome::failed("checks-log-invalid"),
        }
    };
    let Some(ledger_log_path) = resolve_checks_log_path(&log_path.to_string_lossy(), &ledger_root)
    else {
        return FixOutcome::failed("checks-log-invalid");
    };
    let ledger_log = ledger_log_path.to_string_lossy().into_owned();
    let log_size = fs::metadata(&log_path).map(|meta| meta.len()).unwrap_or(0);
    if log_size == 0 {
        return FixOutcome::no_changes();
    }
    let tail = read_log_tail(&log_path, PROMPT_TAIL_BYTES);
    if lint_fix_fast_fail_reason(&tail).is_some() {
        return FixOutcome {
            status: "main-agent-required".to_owned(),
            failure_reason: Some("structural-ruff-failure".to_owned()),
            ledger_ready: true,
            ledger_site: ledger_site_for_lint_site(site),
            ledger_trigger: ledger_trigger_for_lint_site(site),
            ledger_step: ledger_step_for_site(site),
            ledger_phase: ledger_phase_for_site(site),
            ledger_dispatcher: "lint-fix-loop".to_owned(),
            ledger_exit_code: Some(1),
            ledger_failure_detail_log: ledger_log,
            ..FixOutcome::default()
        };
    }
    let run_parent = PathBuf::from(&request.run_parent);
    if !request.claude_present && !request.codex_present && !request.cursor_present {
        if fs::create_dir_all(&run_parent).is_err() {
            return FixOutcome::failed("isolated-artifact-failed");
        }
        let Some(ledger) = initialize_tier_ledger(&run_parent) else {
            return FixOutcome::failed("isolated-artifact-failed");
        };
        return exhausted_outcome(
            site,
            "lint-fix-no-selectable-tier",
            &ledger.to_string_lossy(),
            "",
            &log_path.to_string_lossy(),
        );
    }
    let Some(site_display) = site_label(site) else {
        return FixOutcome::failed("unknown-site");
    };
    let issue_log = allowed_root.join("execution-issues.md");
    if fs::create_dir_all(&run_parent).is_err() {
        append_execution_issue_row(&issue_log, "none", "ledger-failure", "");
        return FixOutcome::failed("tier-ledger-failed");
    }
    let Some(tier_ledger) = initialize_tier_ledger(&run_parent) else {
        append_execution_issue_row(&issue_log, "none", "ledger-failure", "");
        return FixOutcome::failed("tier-ledger-failed");
    };
    let tier_ledger_str = tier_ledger.to_string_lossy().into_owned();
    let repo = Path::new(&request.repo_root);

    let Some(baseline_snapshot) = capture_snapshot(repo) else {
        return with_tier_ledger(
            FixOutcome::failed("snapshot-capture-failed"),
            &tier_ledger_str,
        );
    };
    let Some(baseline_head) = head_ref(repo) else {
        return with_tier_ledger(
            FixOutcome::failed("baseline-head-unresolved"),
            &tier_ledger_str,
        );
    };
    let baseline_branch = current_branch(repo);
    let baseline_clean = baseline_snapshot.is_empty();
    let submodules = submodule_paths(repo);
    let forbidden = coder_forbidden_paths(&submodules);
    let redacted_body = redact_run_log_payload(&sanitize_log_fence(&read_log_tail(
        &log_path,
        PROMPT_TAIL_BYTES,
    )));
    let redacted_log_path = redact_run_log_payload(&log_path.to_string_lossy());
    let prompt_body = compose_prompt(
        site_display,
        &submodules,
        None,
        &redacted_log_path,
        log_size,
        &redacted_body,
    );

    let order = role_default(implement::LINT_FIX_ROLE_ID)
        .map(|role| role.order)
        .unwrap_or(&["claude", "codex", "cursor"]);
    let mut attempted: Vec<String> = Vec::new();
    let mut remaining_budget: i64 = i64::try_from(order.len()).unwrap_or(3)
        * i64::try_from(FIXER_LANE_TIMEOUT_SEC).unwrap_or(1800);
    let mut sequence: u64 = 0;
    let mut last_stderr_tail = String::new();
    let (coder_tool, coder_log_path): (Option<String>, String) = loop {
        let Some(tier) = next_untried_tier(order, &attempted, request) else {
            let reason = if attempted.is_empty() {
                "lint-fix-no-selectable-tier"
            } else {
                PRE_SHIP_ALL_TIERS_NO_DELTA_REASON
            };
            return exhausted_outcome(
                site,
                reason,
                &tier_ledger_str,
                &last_stderr_tail,
                &log_path.to_string_lossy(),
            );
        };
        if remaining_budget < i64::try_from(FIXER_LANE_TIMEOUT_SEC).unwrap_or(1800) {
            return exhausted_outcome(
                site,
                "lint-fix-budget-exhausted",
                &tier_ledger_str,
                &last_stderr_tail,
                &log_path.to_string_lossy(),
            );
        }
        attempted.push(tier.clone());
        remaining_budget -= i64::try_from(FIXER_LANE_TIMEOUT_SEC).unwrap_or(1800);
        sequence += 1;
        let Some(run_dir) = make_attempt_dir(&run_parent, sequence, &tier) else {
            return with_tier_ledger(
                FixOutcome {
                    coder_tool: Some(tier),
                    ..FixOutcome::failed("isolated-artifact-failed")
                },
                &tier_ledger_str,
            );
        };
        let Some(attempt_baseline) = capture_snapshot(repo) else {
            return with_tier_ledger(
                FixOutcome {
                    coder_tool: Some(tier),
                    ..FixOutcome::failed("snapshot-capture-failed")
                },
                &tier_ledger_str,
            );
        };
        let Some(attempt_head) = head_ref(repo) else {
            return with_tier_ledger(
                FixOutcome {
                    coder_tool: Some(tier),
                    ..FixOutcome::failed("head-unresolved-after-dispatch")
                },
                &tier_ledger_str,
            );
        };
        let attempt_start = std::time::Instant::now();
        let (launcher_rc, log_name) = dispatch_tier(
            &tier,
            &run_dir,
            repo,
            &prompt_body,
            site,
            &request.allowed_tmpdir,
        );
        let elapsed_ms = i64::try_from(attempt_start.elapsed().as_millis()).unwrap_or(i64::MAX);
        let Some(current_snapshot) = capture_snapshot(repo) else {
            return with_tier_ledger(
                FixOutcome {
                    coder_tool: Some(tier),
                    ..FixOutcome::failed("snapshot-capture-failed")
                },
                &tier_ledger_str,
            );
        };
        let useful_delta_paths = snapshot_delta_paths(&attempt_baseline, &current_snapshot);
        let Some(current_attempt_head) = head_ref(repo) else {
            return with_tier_ledger(
                FixOutcome {
                    coder_tool: Some(tier),
                    ..FixOutcome::failed("head-unresolved-after-dispatch")
                },
                &tier_ledger_str,
            );
        };
        let useful_delta =
            !useful_delta_paths.is_empty() || current_attempt_head.hex != attempt_head.hex;
        let issue_kind = classify_attempt_issue(
            launcher_rc,
            &stderr_tail_text(&run_dir, &log_name),
            useful_delta,
        );
        let row = tier_ledger_line(
            sequence,
            &tier,
            if useful_delta {
                "useful-delta"
            } else {
                "no-useful-delta"
            },
            launcher_rc,
            elapsed_ms,
            useful_delta,
            &issue_kind,
        );
        if append_tier_ledger(&tier_ledger, &row).is_err() {
            append_execution_issue_row(&issue_log, &tier, "ledger-failure", "");
            return with_tier_ledger(
                FixOutcome {
                    coder_tool: Some(tier),
                    ..FixOutcome::failed("tier-ledger-failed")
                },
                &tier_ledger_str,
            );
        }
        let tail_path = coder_stderr_tail(&run_dir, &log_name);
        if !tail_path.is_empty() {
            last_stderr_tail = tail_path;
        }
        let attempt_log = redacted_attempt_log(&run_dir, &log_name);
        if issue_kind != "no-op" {
            let detail = execution_issue_detail(&attempt_log);
            append_execution_issue_row(&issue_log, &tier, &issue_kind, &detail);
        }
        if useful_delta {
            break (Some(tier), attempt_log);
        }
    };

    let Some(current_head) = head_ref(repo) else {
        return FixOutcome {
            coder_tool,
            coder_log_path,
            stderr_tail_path: last_stderr_tail,
            tier_ledger_path: tier_ledger_str,
            ..FixOutcome::failed("head-unresolved-after-dispatch")
        };
    };
    if head_change_invalid(
        repo,
        &baseline_head,
        &current_head,
        &baseline_branch,
        baseline_clean,
    ) {
        return FixOutcome {
            head_changed: true,
            coder_tool,
            coder_log_path,
            stderr_tail_path: last_stderr_tail,
            tier_ledger_path: tier_ledger_str,
            ..FixOutcome::failed("head-changed-after-dispatch")
        };
    }
    if current_head.hex != baseline_head.hex {
        let committed = committed_delta_paths(repo, &baseline_head.hex, &current_head.hex);
        if forbidden_paths_match_count(&committed, &forbidden) > 0 {
            let reset_ok = reset_hard(repo, &baseline_head.hex)
                && head_ref(repo).is_some_and(|head| head.hex == baseline_head.hex);
            let reason = if reset_ok {
                "forbidden-path-violation"
            } else {
                "forbidden-path-reset-failed"
            };
            return with_tier_ledger(
                FixOutcome {
                    coder_tool,
                    ..FixOutcome::failed(reason)
                },
                &tier_ledger_str,
            );
        }
        if post_dispatch_forbidden_revert(repo, &forbidden) > 0 {
            return with_tier_ledger(
                FixOutcome {
                    coder_tool,
                    ..FixOutcome::failed("forbidden-path-violation")
                },
                &tier_ledger_str,
            );
        }
        let delta = committed_delta_paths(repo, &baseline_head.hex, &current_head.hex);
        return FixOutcome {
            status: "applied".to_owned(),
            delta_paths: delta,
            commit_sha: Some(current_head.hex),
            head_changed: true,
            coder_tool,
            coder_log_path,
            tier_ledger_path: tier_ledger_str,
            ..FixOutcome::default()
        };
    }
    if post_dispatch_forbidden_revert(repo, &forbidden) > 0 {
        return with_tier_ledger(
            FixOutcome {
                coder_tool,
                ..FixOutcome::failed("forbidden-path-violation")
            },
            &tier_ledger_str,
        );
    }
    let Some(current_snapshot) = capture_snapshot(repo) else {
        return with_tier_ledger(
            FixOutcome {
                coder_tool,
                ..FixOutcome::failed("snapshot-capture-failed")
            },
            &tier_ledger_str,
        );
    };
    let delta = snapshot_delta_paths(&baseline_snapshot, &current_snapshot);
    if delta.is_empty() {
        return FixOutcome {
            status: "no-changes".to_owned(),
            coder_tool,
            coder_log_path,
            tier_ledger_path: tier_ledger_str,
            ..FixOutcome::default()
        };
    }
    let commit_sha = if baseline_clean {
        match stage_and_commit(repo, &delta, site_display) {
            Ok(sha) => sha,
            Err(reason) => {
                return with_tier_ledger(
                    FixOutcome {
                        coder_tool,
                        ..FixOutcome::failed(reason)
                    },
                    &tier_ledger_str,
                );
            }
        }
    } else {
        None
    };
    FixOutcome {
        status: "applied".to_owned(),
        delta_paths: delta,
        commit_sha,
        head_changed: false,
        coder_tool,
        coder_log_path,
        tier_ledger_path: tier_ledger_str,
        ..FixOutcome::default()
    }
}

/// Resolve the allowed-root that confines the checks log (Python `allowed_root` logic).
///
/// Every failure maps to the single `checks-log-invalid` outcome, so the caller
/// builds it; returning `None` keeps the large `FixOutcome` out of a `Result`.
fn resolve_allowed_root(allowed_tmpdir: &str, run_parent: &str) -> Option<PathBuf> {
    if allowed_tmpdir.is_empty() {
        return resolve_lenient(run_parent)
            .and_then(|parent| parent.parent().map(Path::to_path_buf));
    }
    let allowed_root = fs::canonicalize(allowed_tmpdir).ok()?;
    let expected_loop = allowed_root.join("lint-fix-loop");
    let run_parent_canonical = resolve_lenient(run_parent)?;
    let expected_canonical = resolve_lenient(&expected_loop.to_string_lossy())?;
    (run_parent_canonical == expected_canonical).then_some(allowed_root)
}

/// Resolve a path the way Python `Path.resolve()` does: canonicalize the deepest
/// existing ancestor and re-append the missing tail, so a not-yet-created
/// `lint-fix-loop` directory still normalizes to a comparable path.
fn resolve_lenient(path: &str) -> Option<PathBuf> {
    let candidate = Path::new(path);
    if let Ok(resolved) = fs::canonicalize(candidate) {
        return Some(resolved);
    }
    let parent = candidate.parent()?;
    let name = candidate.file_name()?;
    Some(fs::canonicalize(parent).ok()?.join(name))
}

/// Select the next untried tier whose binary is present (Python `next_untried_tier`).
fn next_untried_tier(
    order: &[&str],
    attempted: &[String],
    request: &LintFixRequest,
) -> Option<String> {
    order
        .iter()
        .find(|tier| {
            !attempted.iter().any(|done| done == *tier)
                && match **tier {
                    "claude" => request.claude_present,
                    "codex" => request.codex_present,
                    "cursor" => request.cursor_present,
                    _ => false,
                }
        })
        .map(|tier| (*tier).to_owned())
}

/// Initialize the tier-ledger TSV, returning its path (Python `_initialize_tier_ledger`).
fn initialize_tier_ledger(run_parent: &Path) -> Option<PathBuf> {
    let path = run_parent.join("lint-fix-tier-ledger.tsv");
    if !path.exists() && fs::write(&path, tier_ledger_header()).is_err() {
        return None;
    }
    Some(path)
}

/// Append one tier-ledger row (Python `_append_tier_ledger`).
fn append_tier_ledger(path: &Path, row: &str) -> std::io::Result<()> {
    use std::io::Write as _;
    let mut handle = fs::OpenOptions::new().append(true).open(path)?;
    handle.write_all(row.as_bytes())
}

/// Make one isolated attempt directory (Python `tempfile.mkdtemp`).
fn make_attempt_dir(run_parent: &Path, sequence: u64, tier: &str) -> Option<PathBuf> {
    for suffix in 0..4096u32 {
        let dir = run_parent.join(format!("attempt-{sequence:02}-{tier}.{suffix:04}"));
        match fs::create_dir(&dir) {
            Ok(()) => {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt as _;
                    let _ignored = fs::set_permissions(&dir, fs::Permissions::from_mode(0o700));
                }
                return Some(dir);
            }
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(_) => return None,
        }
    }
    None
}

/// One resolved HEAD reference.
struct HeadRef {
    id: ObjectId,
    hex: String,
}

/// Resolve HEAD to an object reference, or `None` on an unborn/unresolvable HEAD.
fn head_ref(root: &Path) -> Option<HeadRef> {
    let repository = GixRepository::discover(root).ok()?;
    match repository.head().ok()? {
        Head::Symbolic { target, .. } | Head::Detached { target } => Some(HeadRef {
            hex: target.to_hex(),
            id: target,
        }),
        Head::Unborn { .. } => None,
    }
}

/// Return the short current branch name, or empty when detached/unresolvable.
fn current_branch(root: &Path) -> String {
    let Ok(repository) = GixRepository::discover(root) else {
        return String::new();
    };
    match repository.head() {
        Ok(Head::Symbolic { name, .. }) => {
            let raw = name.as_bytes();
            let stripped = raw.strip_prefix(b"refs/heads/").unwrap_or(raw);
            String::from_utf8_lossy(stripped).into_owned()
        }
        _ => String::new(),
    }
}

/// Capture one repository snapshot for delta detection (Python `_snapshot_from_paths`).
fn capture_snapshot(root: &Path) -> Option<Vec<RepoPathState>> {
    let repository = GixRepository::discover(root).ok()?;
    let status = repository.local_status(&StatusOptions::default()).ok()?;
    let staged = change_fingerprints(&status.tree_to_index);
    let unstaged = change_fingerprints(&status.index_to_worktree);
    let untracked: std::collections::BTreeSet<String> = status
        .untracked
        .iter()
        .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
        .collect();
    let mut paths: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    paths.extend(staged.keys().cloned());
    paths.extend(unstaged.keys().cloned());
    paths.extend(untracked.iter().cloned());
    Some(
        paths
            .into_iter()
            .map(|path| RepoPathState {
                worktree_digest: file_digest(&root.join(&path)),
                unstaged_diff: unstaged.get(&path).cloned().unwrap_or_default(),
                staged_diff: staged.get(&path).cloned().unwrap_or_default(),
                untracked: untracked.contains(&path),
                path,
            })
            .collect(),
    )
}

/// Build a per-path fingerprint map from one name-status change set.
fn change_fingerprints(changes: &larch_core::ChangeSet) -> BTreeMap<String, String> {
    let mut map = BTreeMap::new();
    for change in changes.entries() {
        let path = String::from_utf8_lossy(change.path.as_bytes()).into_owned();
        let old = change
            .old_id
            .as_ref()
            .map(ObjectId::to_hex)
            .unwrap_or_default();
        let new = change
            .new_id
            .as_ref()
            .map(ObjectId::to_hex)
            .unwrap_or_default();
        let source = change
            .source_path
            .as_ref()
            .map(|value| String::from_utf8_lossy(value.as_bytes()).into_owned())
            .unwrap_or_default();
        map.insert(path, format!("{:?}|{old}|{new}|{source}", change.kind));
    }
    map
}

/// SHA-256 of a worktree file (Python `_file_digest`).
fn file_digest(path: &Path) -> String {
    match fs::symlink_metadata(path) {
        Ok(meta) if meta.is_file() && !meta.file_type().is_symlink() => fs::read(path).map_or_else(
            |_| "unreadable".to_owned(),
            |bytes| format!("{:x}", Sha256::digest(bytes)),
        ),
        _ => "missing".to_owned(),
    }
}

/// True when a HEAD advance is disqualifying (Python `_head_change_invalid_after_dispatch`).
fn head_change_invalid(
    root: &Path,
    baseline: &HeadRef,
    current: &HeadRef,
    baseline_branch: &str,
    baseline_clean: bool,
) -> bool {
    if current.hex == baseline.hex {
        return false;
    }
    let current_branch = current_branch(root);
    if baseline_branch.is_empty() || current_branch.is_empty() || baseline_branch != current_branch
    {
        return true;
    }
    let Ok(repository) = GixRepository::discover(root) else {
        return true;
    };
    // `baseline` is an ancestor of `current` iff nothing is in `current..baseline`.
    let is_ancestor = repository
        .commit_count_range(&current.id, &baseline.id)
        .map(|count| count == 0)
        .unwrap_or(false);
    if !is_ancestor {
        return true;
    }
    if !baseline_clean {
        return true;
    }
    // Reject a merge commit outright, mirroring the Python `current_head^2` guard:
    // a second parent that is already reachable from the baseline would otherwise
    // leave `baseline..current` at a single commit and slip past the count check.
    let is_merge = repository
        .walk_commits(&current.id, 1)
        .ok()
        .and_then(|commits| commits.into_iter().next())
        .is_some_and(|commit| commit.parents.len() >= 2);
    if is_merge {
        return true;
    }
    // A single non-merge commit past the baseline is exactly one commit ahead.
    repository.commit_count_range(&baseline.id, &current.id) != Ok(1)
}

/// Name-only committed delta for `base..head` (Python committed-path diff).
fn committed_delta_paths(root: &Path, base_hex: &str, head_hex: &str) -> Vec<String> {
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return Vec::new();
    };
    let (Ok(base), Ok(head)) = (GitRef::new(base_hex), GitRef::new(head_hex)) else {
        return Vec::new();
    };
    let request = ExactDiffRequest {
        cached: false,
        binary: false,
        no_ext_diff: true,
        unified_context: None,
        name_only: true,
        name_status: false,
        quiet: false,
        exit_code: false,
        base: Some(base),
        head: Some(head),
        paths: Vec::new(),
    };
    runtime
        .runtime
        .block_on(runtime.git_cli().exact_diff(request, &runtime.cancellation))
        .map_or_else(
            |_| Vec::new(),
            |result| {
                String::from_utf8_lossy(result.output().stdout())
                    .lines()
                    .filter_map(|line| {
                        let trimmed = line.trim();
                        (!trimmed.is_empty()).then(|| trimmed.to_owned())
                    })
                    .collect()
            },
        )
}

/// `git reset --hard <base>` through the typed runtime (Python `git.reset`).
fn reset_hard(root: &Path, base_hex: &str) -> bool {
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return false;
    };
    let Ok(target) = GitRef::new(base_hex) else {
        return false;
    };
    let request = ResetRequest {
        mode: ResetMode::Hard,
        target,
        paths: Vec::new(),
    };
    runtime
        .runtime
        .block_on(runtime.git_cli().reset(request, &runtime.cancellation))
        .is_ok()
}

/// Restore one tracked path from the index (Python `git checkout -- path`).
fn restore_path(root: &Path, path: &str) -> bool {
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return false;
    };
    let Ok(git_path) = GitCliPath::new(path) else {
        return false;
    };
    let request = RestoreRequest {
        source: None,
        staged: false,
        paths: vec![git_path],
    };
    runtime
        .runtime
        .block_on(runtime.git_cli().restore(request, &runtime.cancellation))
        .is_ok()
}

/// Revert every forbidden path the coder touched (Python `_post_dispatch_forbidden_revert`).
fn post_dispatch_forbidden_revert(root: &Path, forbidden: &[String]) -> usize {
    let (tracked, untracked) = tracked_and_untracked(root);
    let mut reverted = 0;
    let mut seen: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for path in tracked.iter().chain(untracked.iter()) {
        if path.is_empty() || !seen.insert(path.clone()) {
            continue;
        }
        if !path_matches_forbidden(path, forbidden) {
            continue;
        }
        if untracked.contains(path) {
            let _ignored = fs::remove_file(root.join(path));
        } else {
            restore_path(root, path);
        }
        reverted += 1;
    }
    reverted
}

/// Current tracked and untracked path lists (Python capture helpers).
fn tracked_and_untracked(root: &Path) -> (Vec<String>, Vec<String>) {
    let Ok(repository) = GixRepository::discover(root) else {
        return (Vec::new(), Vec::new());
    };
    let Ok(status) = repository.local_status(&StatusOptions::default()) else {
        return (Vec::new(), Vec::new());
    };
    let mut tracked: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for change in status
        .tree_to_index
        .entries()
        .iter()
        .chain(status.index_to_worktree.entries())
    {
        tracked.insert(String::from_utf8_lossy(change.path.as_bytes()).into_owned());
    }
    let untracked: Vec<String> = status
        .untracked
        .iter()
        .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
        .collect();
    (tracked.into_iter().collect(), untracked)
}

/// Discover submodule paths from `.gitmodules`.
///
/// Parity note: the Python `coder_delta_guards.submodule_paths` also unions in
/// `git submodule foreach --quiet echo $sm_path`, which surfaces a checked-out
/// path that diverges from its `.gitmodules` declaration. This port matches the
/// sibling `review-and-fix` coder guard (`revert_submodule_changes`) and reads
/// only the declared `.gitmodules` paths; the divergent-checkout case needs a
/// misconfigured repo and this repository has no submodules.
fn submodule_paths(root: &Path) -> Vec<String> {
    let source = root.join(".gitmodules");
    let mut seen: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    if let Ok(text) = fs::read_to_string(&source) {
        for line in text.lines() {
            let trimmed = line.trim_start();
            if let Some(rest) = trimmed.strip_prefix("path")
                && let Some(index) = rest.find('=')
            {
                let value = rest[index + 1..].trim();
                if !value.is_empty() {
                    seen.insert(value.to_owned());
                }
            }
        }
    }
    seen.into_iter().collect()
}

/// Stage and commit the applied delta, unstaging on any failure.
///
/// Mirrors the Python baseline-clean branch: a failed stage or commit leaves the
/// worktree edits in place but unstages them before returning the reason.
fn stage_and_commit(
    root: &Path,
    delta: &[String],
    site_display: &str,
) -> Result<Option<String>, &'static str> {
    if !larch_git_stage(root, delta) {
        unstage_paths(root, delta);
        return Err("git-add-failed");
    }
    let message = format!("Apply relevant-checks fixes ({site_display})");
    if !larch_git_commit(root, &message) {
        unstage_paths(root, delta);
        return Err("git-commit-failed");
    }
    Ok(head_ref(root).map(|head| head.hex))
}

/// Stage the applied paths via `larch git stage` (Python `larch git stage`).
fn larch_git_stage(root: &Path, paths: &[String]) -> bool {
    let mut arguments = Vec::new();
    arguments.push(OsString::from(LARCH_GIT_DOMAIN));
    arguments.push(OsString::from("stage"));
    arguments.extend(paths.iter().map(OsString::from));
    run_larch_in(root, &arguments)
        .map(|output| output.status().success())
        .unwrap_or(false)
}

/// Commit the staged fix via `larch git commit` (Python `larch git commit`).
fn larch_git_commit(root: &Path, message: &str) -> bool {
    let mut arguments = Vec::new();
    arguments.push(OsString::from(LARCH_GIT_DOMAIN));
    arguments.extend(
        ["commit", "--no-trailer", "-m", message]
            .into_iter()
            .map(OsString::from),
    );
    run_larch_in(root, &arguments)
        .map(|output| output.status().success())
        .unwrap_or(false)
}

/// Unstage the applied paths after a failed stage/commit (`git reset --quiet -- paths`).
fn unstage_paths(root: &Path, paths: &[String]) {
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return;
    };
    let Ok(target) = GitRef::new("HEAD") else {
        return;
    };
    let git_paths: Vec<GitCliPath> = paths
        .iter()
        .filter_map(|path| GitCliPath::new(path).ok())
        .collect();
    let request = ResetRequest {
        mode: ResetMode::Mixed,
        target,
        paths: git_paths,
    };
    let _ignored = runtime
        .runtime
        .block_on(runtime.git_cli().reset(request, &runtime.cancellation));
}

/// Run one verified `scripts/larch.sh` subcommand.
///
/// The `checks lint-fix` process runs inside the repository, so the verified
/// entrypoint inherits the working directory the `larch git` verbs act on.
fn run_larch_in(_root: &Path, arguments: &[OsString]) -> Result<larch_core::ProcessOutput, String> {
    run_verified_larch(arguments)
}

// ---------------------------------------------------------------------------
// Vendor lanes
// ---------------------------------------------------------------------------

/// Dispatch one tier and return `(launcher_rc, log_name)` (Python tier branch).
fn dispatch_tier(
    tier: &str,
    run_dir: &Path,
    repo_root: &Path,
    prompt_body: &str,
    site: &str,
    allowed_tmpdir: &str,
) -> (i32, String) {
    match tier {
        "claude" => (
            run_claude(run_dir, prompt_body),
            "claude-lint-fix.txt".to_owned(),
        ),
        "codex" => (
            run_codex(run_dir, repo_root, prompt_body, site, allowed_tmpdir),
            "codex.log".to_owned(),
        ),
        _ => (
            run_cursor(run_dir, repo_root, prompt_body),
            "cursor.log".to_owned(),
        ),
    }
}

/// Launch the Claude lint-fix lane (Python `_run_claude`).
fn run_claude(run_dir: &Path, prompt_body: &str) -> i32 {
    let prompt_file = run_dir.join("prompt.md");
    if fs::write(&prompt_file, prompt_body).is_err() {
        return 1;
    }
    let output = run_dir.join("claude-lint-fix.txt");
    let arguments = command_argv(&[
        "agent",
        "launch-claude-lint-fix",
        "--prompt-body-file",
        &prompt_file.to_string_lossy(),
        "--output",
        &output.to_string_lossy(),
        "--timeout",
        &FIXER_LANE_TIMEOUT_SEC.to_string(),
        "--model",
        CLAUDE_CI_FIX_MODEL,
    ]);
    launcher_exit(&arguments, &output)
}

/// Launch the Codex lint-fix lane (Python `_run_codex`).
fn run_codex(
    run_dir: &Path,
    repo_root: &Path,
    prompt_body: &str,
    site: &str,
    allowed_tmpdir: &str,
) -> i32 {
    let prompt_file = run_dir.join("prompt.md");
    let prompt = format!("{prompt_body}{}", codex_lint_fix_prompt_appendix(site));
    if fs::write(&prompt_file, &prompt).is_err() {
        return 1;
    }
    let codex_log = run_dir.join("codex.log");
    let arguments = command_argv(&[
        "agent",
        "launch-codex-exec",
        "--output",
        &codex_log.to_string_lossy(),
        "--timeout",
        &FIXER_LANE_TIMEOUT_SEC.to_string(),
        "--workdir",
        &repo_root.to_string_lossy(),
        "--add-dir",
        &run_dir.to_string_lossy(),
        "--add-dir",
        &repo_root.to_string_lossy(),
        "--usage-label",
        "codex_lint_fix",
        "--prompt-file",
        &prompt_file.to_string_lossy(),
    ]);
    let exit = launcher_exit(&arguments, &codex_log);
    let token_record = codex_log.with_extension("log.token-record");
    if token_record.is_file()
        && fs::metadata(&token_record)
            .map(|meta| meta.len() > 0)
            .unwrap_or(false)
    {
        let _ = run_verified_larch(&command_argv(&[
            "token",
            "append-record",
            "--input",
            &token_record.to_string_lossy(),
            "--tmpdir",
            allowed_tmpdir,
        ]));
        let _ = run_verified_larch(&command_argv(&[
            "token",
            "record-vendor-sidecar",
            "--input",
            &token_record.to_string_lossy(),
        ]));
    }
    exit
}

/// Launch the Cursor lint-fix lane (Python `_run_cursor`).
fn run_cursor(run_dir: &Path, repo_root: &Path, prompt_body: &str) -> i32 {
    let wrapped =
        match run_verified_larch(&command_argv(&["agent", "cursor-wrap-prompt", prompt_body])) {
            Ok(output) if output.status().success() => {
                String::from_utf8_lossy(output.stdout()).into_owned()
            }
            Ok(output) => return output.status().code().unwrap_or(1),
            Err(_) => return 1,
        };
    let credential = match cursor_launch_credential(&CursorPreflightRequest {
        diagnostic_prefix: "checks lint-fix",
        caller: "checks lint-fix",
        workdir: repo_root,
    }) {
        Ok(credential) => credential,
        Err((code, _message)) => return code,
    };
    let Ok(model_argv) = cursor_model_argv(None) else {
        return 1;
    };
    let mut argv = vec![
        "cursor".to_owned(),
        "agent".to_owned(),
        "-p".to_owned(),
        "--trust".to_owned(),
    ];
    argv.extend(model_argv);
    argv.extend([
        "--workspace".to_owned(),
        repo_root.display().to_string(),
        wrapped,
    ]);
    let output_path = run_dir.join("cursor.log");
    run_external_agent_with_auth_retries(&ExternalAgentLaunch {
        tool: "cursor".to_owned(),
        output: output_path.display().to_string(),
        timeout_seconds: FIXER_LANE_TIMEOUT_SEC,
        command: argv,
        program: VendorProgram::Cursor,
        routing: ExternalAgentRouting::CaptureCombined,
        stderr_sink: None,
        working_directory: Some(repo_root.to_path_buf()),
        environment: cursor_child_environment(credential.as_ref()),
        sentinel_suffix: ".done",
        poll_interval: Duration::from_secs(10),
        stdin: None,
        stall_watch: None,
    })
    .map_or(1, |outcome| outcome.exit_code)
}

/// Build a verified-larch argv from string slices.
fn command_argv(parts: &[&str]) -> Vec<OsString> {
    parts.iter().map(OsString::from).collect()
}

/// Resolve one launcher's exit code from its captured stdout and artifacts.
fn launcher_exit(arguments: &[OsString], output: &Path) -> i32 {
    let deadline = Duration::from_secs(FIXER_LANE_TIMEOUT_SEC) + LAUNCH_TIMEOUT_MARGIN;
    run_verified_larch_with_timeout(arguments, deadline).map_or(1, |process| {
        let stdout = String::from_utf8_lossy(process.stdout());
        let rc = process
            .status()
            .code()
            .unwrap_or_else(|| i32::from(!process.status().success()));
        resolve_launcher_exit_from_files(&stdout, Some(output), rc).unwrap_or(rc)
    })
}

// ---------------------------------------------------------------------------
// Attempt evidence helpers
// ---------------------------------------------------------------------------

/// Read the bounded tail of one lane's stderr-tail sidecar (Python classify read).
fn stderr_tail_text(run_dir: &Path, log_name: &str) -> String {
    let candidate = run_dir.join(format!("{log_name}.stderr-tail"));
    let Ok(meta) = fs::symlink_metadata(&candidate) else {
        return String::new();
    };
    if !meta.is_file() || meta.file_type().is_symlink() {
        return String::new();
    }
    let Ok(bytes) = fs::read(&candidate) else {
        return String::new();
    };
    let start = bytes.len().saturating_sub(STDERR_TAIL_SCAN_BYTES);
    String::from_utf8_lossy(&bytes[start..]).into_owned()
}

/// Publish the redacted stderr-tail copy, returning its path (Python `_coder_stderr_tail`).
fn coder_stderr_tail(run_dir: &Path, log_name: &str) -> String {
    let candidate = run_dir.join(format!("{log_name}.stderr-tail"));
    let target = run_dir.join(format!("{log_name}.stderr-tail.redacted"));
    let Ok(root) = run_dir.canonicalize() else {
        return String::new();
    };
    let Ok(meta) = fs::symlink_metadata(&candidate) else {
        return String::new();
    };
    if !meta.is_file() || meta.file_type().is_symlink() {
        return String::new();
    }
    let Ok(bytes) = fs::read(&candidate) else {
        return String::new();
    };
    let start = bytes.len().saturating_sub(4096);
    let text = String::from_utf8_lossy(&bytes[start..]).into_owned();
    if text.is_empty() {
        return String::new();
    }
    if write_redacted(&root, &target, &redact_run_log_payload(&text)) {
        target.to_string_lossy().into_owned()
    } else {
        String::new()
    }
}

/// Publish the redacted attempt-log copy, returning its path (Python `_redacted_attempt_log`).
fn redacted_attempt_log(run_dir: &Path, log_name: &str) -> String {
    let source = run_dir.join(log_name);
    let target = run_dir.join(format!("{log_name}.redacted"));
    let Ok(root) = run_dir.canonicalize() else {
        return String::new();
    };
    let Ok(meta) = fs::symlink_metadata(&source) else {
        return String::new();
    };
    if !meta.is_file() || meta.file_type().is_symlink() {
        return String::new();
    }
    let Ok(bytes) = fs::read(&source) else {
        return String::new();
    };
    let text = String::from_utf8_lossy(&bytes).into_owned();
    if write_redacted(&root, &target, &redact_run_log_payload(&text)) {
        target.to_string_lossy().into_owned()
    } else {
        String::new()
    }
}

/// Write a redacted sidecar at mode 0o600, confined under `root`.
fn write_redacted(root: &Path, target: &Path, text: &str) -> bool {
    let Ok(confined) = TemporaryRoot::resolve(Some(root)) else {
        return false;
    };
    atomic_write_utf8_in(&confined, target, text, false, 0o600).is_ok()
}

/// Collapse an attempt-log tail into a one-line detail (Python `_append_attempt_execution_issue`).
fn execution_issue_detail(attempt_log: &str) -> String {
    if attempt_log.is_empty() {
        return "attempt log unavailable".to_owned();
    }
    let Ok(bytes) = fs::read(attempt_log) else {
        return "attempt log unavailable".to_owned();
    };
    let start = bytes.len().saturating_sub(4096);
    let tail = String::from_utf8_lossy(&bytes[start..]);
    let collapsed = tail.split_whitespace().collect::<Vec<_>>().join(" ");
    if collapsed.is_empty() {
        "attempt log unavailable".to_owned()
    } else {
        collapsed
    }
}

/// Append one redacted Tool-Failures execution-issue row (best-effort telemetry).
fn append_execution_issue_row(issue_log: &Path, tier: &str, issue_kind: &str, detail: &str) {
    if issue_kind.is_empty() {
        return;
    }
    let detail = if detail.is_empty() {
        "attempt log unavailable"
    } else {
        detail
    };
    let entry = redact_run_log_payload(&format!(
        "- lint-fix tier={tier} category={issue_kind}; {detail}"
    ));
    let _ignored = append_execution_issue(issue_log, "Tool Failures", entry.trim());
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;
    use tempfile::TempDir;

    fn git(dir: &Path, args: &[&str]) {
        let output = Command::new("git")
            .args(args)
            .current_dir(dir)
            .env("GIT_AUTHOR_NAME", "t")
            .env("GIT_AUTHOR_EMAIL", "t@t")
            .env("GIT_COMMITTER_NAME", "t")
            .env("GIT_COMMITTER_EMAIL", "t@t")
            .env("GIT_CONFIG_GLOBAL", "/dev/null")
            .output()
            .expect("git runs");
        assert!(
            output.status.success(),
            "git {args:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    fn write(dir: &Path, rel: &str, body: &str) {
        let path = dir.join(rel);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).expect("mkdir");
        }
        std::fs::write(path, body).expect("write");
    }

    fn init_repo() -> TempDir {
        let dir = TempDir::new().expect("tempdir");
        git(dir.path(), &["init", "-b", "main"]);
        write(dir.path(), "a.txt", "one\n");
        git(dir.path(), &["add", "."]);
        git(dir.path(), &["commit", "-m", "base"]);
        dir
    }

    fn commit_all(dir: &Path, message: &str) -> HeadRef {
        git(dir, &["add", "-A"]);
        git(dir, &["commit", "-m", message]);
        head_ref(dir).expect("head")
    }

    #[test]
    fn head_ref_and_branch_resolve() {
        let repo = init_repo();
        let root = repo.path();
        let head = head_ref(root).expect("head");
        assert_eq!(head.hex.len(), 40);
        assert_eq!(current_branch(root), "main");
        // An unborn HEAD resolves to None.
        let empty = TempDir::new().expect("tempdir");
        git(empty.path(), &["init", "-b", "main"]);
        assert!(head_ref(empty.path()).is_none());
    }

    #[test]
    fn snapshot_delta_and_file_digest() {
        let repo = init_repo();
        let root = repo.path();
        let baseline = capture_snapshot(root).expect("baseline");
        write(root, "a.txt", "one\ntwo\n");
        let current = capture_snapshot(root).expect("current");
        let delta = snapshot_delta_paths(&baseline, &current);
        assert!(delta.contains(&"a.txt".to_owned()), "delta: {delta:?}");
        assert_ne!(file_digest(&root.join("a.txt")), "missing");
        assert_eq!(file_digest(&root.join("absent.txt")), "missing");
    }

    #[test]
    fn head_change_invalid_covers_every_branch() {
        let repo = init_repo();
        let root = repo.path();
        let base = head_ref(root).expect("base");
        // Same head is always valid.
        assert!(!head_change_invalid(root, &base, &base, "main", true));
        // One clean non-merge commit ahead is valid.
        write(root, "b.txt", "b\n");
        let ahead = commit_all(root, "ahead");
        assert!(!head_change_invalid(root, &base, &ahead, "main", true));
        // A dirty baseline is rejected.
        assert!(head_change_invalid(root, &base, &ahead, "main", false));
        // A branch switch is rejected.
        git(root, &["checkout", "-b", "feat"]);
        write(root, "c.txt", "c\n");
        let feat = commit_all(root, "feat");
        assert!(head_change_invalid(root, &base, &feat, "main", true));
        // A merge commit is rejected even on the same branch.
        git(root, &["checkout", "main"]);
        let pre_merge = head_ref(root).expect("pre-merge");
        git(root, &["merge", "--no-ff", "feat", "-m", "merge"]);
        let merged = head_ref(root).expect("merged");
        assert!(head_change_invalid(root, &pre_merge, &merged, "main", true));
        // A non-ancestor sibling on the same branch is rejected.
        git(root, &["reset", "--hard", &base.hex]);
        write(root, "d.txt", "d\n");
        let sibling = commit_all(root, "sibling");
        assert!(head_change_invalid(root, &ahead, &sibling, "main", true));
    }

    #[test]
    fn committed_delta_reset_and_restore() {
        let repo = init_repo();
        let root = repo.path();
        let base = head_ref(root).expect("base");
        write(root, "b.txt", "b\n");
        let head = commit_all(root, "add b");
        let delta = committed_delta_paths(root, &base.hex, &head.hex);
        assert_eq!(delta, vec!["b.txt".to_owned()]);
        // reset_hard returns HEAD to the baseline commit.
        assert!(reset_hard(root, &base.hex));
        assert_eq!(head_ref(root).expect("post-reset").hex, base.hex);
        // restore_path reverts an unstaged edit to a tracked file.
        write(root, "a.txt", "dirty\n");
        assert!(restore_path(root, "a.txt"));
        assert_eq!(
            std::fs::read_to_string(root.join("a.txt")).unwrap(),
            "one\n"
        );
    }

    #[test]
    fn forbidden_revert_removes_untracked_and_restores_tracked() {
        let repo = init_repo();
        let root = repo.path();
        write(root, "vendor/sub/keep.txt", "keep\n");
        commit_all(root, "add submodule-like path");
        write(root, "vendor/sub/keep.txt", "tampered\n");
        write(root, "vendor/sub/new.txt", "untracked\n");
        let forbidden = vec!["vendor/sub".to_owned()];
        let (tracked, untracked) = tracked_and_untracked(root);
        assert!(tracked.contains(&"vendor/sub/keep.txt".to_owned()));
        assert!(untracked.contains(&"vendor/sub/new.txt".to_owned()));
        let reverted = post_dispatch_forbidden_revert(root, &forbidden);
        assert_eq!(reverted, 2);
        assert!(!root.join("vendor/sub/new.txt").exists());
        assert_eq!(
            std::fs::read_to_string(root.join("vendor/sub/keep.txt")).unwrap(),
            "keep\n"
        );
    }

    #[test]
    fn submodule_paths_reads_gitmodules() {
        let repo = init_repo();
        let root = repo.path();
        write(
            root,
            ".gitmodules",
            "[submodule \"sub\"]\n\tpath = vendor/sub\n\turl = https://example.invalid\n",
        );
        assert_eq!(submodule_paths(root), vec!["vendor/sub".to_owned()]);
        // No .gitmodules yields no paths.
        let empty = init_repo();
        assert!(submodule_paths(empty.path()).is_empty());
    }

    fn applied_outcome() -> FixOutcome {
        FixOutcome {
            status: "applied".to_owned(),
            delta_paths: vec!["src/a.rs".to_owned(), "src/b.rs".to_owned()],
            commit_sha: Some("deadbeef".to_owned()),
            head_changed: true,
            coder_tool: Some("codex".to_owned()),
            coder_log_path: "/t/coder.log".to_owned(),
            tier_ledger_path: "/t/led.tsv".to_owned(),
            ..FixOutcome::no_changes()
        }
    }

    #[test]
    fn emit_lint_fix_renders_each_status() {
        // Applied with a non-empty delta, no-changes, failed, and the ledger block.
        let _applied = emit_lint_fix(&applied_outcome());
        let _no_changes = emit_lint_fix(&FixOutcome::no_changes());
        let failed = FixOutcome {
            stderr_tail_path: "/t/tail".to_owned(),
            coder_log_path: "/t/log".to_owned(),
            tier_ledger_path: "/t/led".to_owned(),
            ..FixOutcome::failed("git-commit-failed")
        };
        let _failed = emit_lint_fix(&failed);
        let ledger = FixOutcome {
            status: "main-agent-required".to_owned(),
            ledger_ready: true,
            ledger_site: "step5".to_owned(),
            ledger_trigger: "main-agent-required".to_owned(),
            ledger_step: "5".to_owned(),
            ledger_phase: "review".to_owned(),
            ledger_dispatcher: "lint-fix-loop".to_owned(),
            ledger_exit_code: Some(1),
            ledger_failure_detail_log: "/t/detail".to_owned(),
            ..FixOutcome::no_changes()
        };
        let _ledger = emit_lint_fix(&ledger);
    }

    #[test]
    fn presence_probe_reads_env_session_and_path() {
        let dir = TempDir::new().expect("tempdir");
        write(
            dir.path(),
            "session-env.sh",
            "LARCH_CLF_FAKE_FOUND=true\r\n",
        );
        assert!(binary_present(
            "LARCH_CLF_FAKE_FOUND",
            dir.path(),
            "nonexistent-binary"
        ));
        write(dir.path(), "session-env.sh", "LARCH_CLF_FAKE_FOUND=false\n");
        assert!(!binary_present(
            "LARCH_CLF_FAKE_FOUND",
            dir.path(),
            "nonexistent-binary-xyz"
        ));
        assert!(which_on_path("sh"));
        assert!(!which_on_path("larch-definitely-not-on-path-xyz"));
    }

    #[test]
    fn resolvers_and_tier_selection() {
        assert!(!default_repo_root().is_empty());
        let request = LintFixRequest {
            site: "step5".to_owned(),
            checks_log: String::new(),
            repo_root: ".".to_owned(),
            run_parent: String::new(),
            allowed_tmpdir: String::new(),
            claude_present: false,
            codex_present: true,
            cursor_present: false,
        };
        let order = ["claude", "codex", "cursor"];
        assert_eq!(
            next_untried_tier(&order, &[], &request).as_deref(),
            Some("codex")
        );
        assert_eq!(
            next_untried_tier(&order, &["codex".to_owned()], &request),
            None
        );
        let dir = TempDir::new().expect("tempdir");
        let resolved = resolve_lenient(&dir.path().to_string_lossy()).expect("resolved");
        assert!(resolved.is_absolute());
        let missing = dir.path().join("missing-leaf");
        assert!(resolve_lenient(&missing.to_string_lossy()).is_some());
    }

    #[test]
    fn tier_ledger_and_attempt_dir_roundtrip() {
        let dir = TempDir::new().expect("tempdir");
        let ledger = initialize_tier_ledger(dir.path()).expect("ledger");
        assert!(ledger.is_file());
        // A second init leaves the existing header intact.
        assert!(initialize_tier_ledger(dir.path()).is_some());
        append_tier_ledger(
            &ledger,
            "1\tcodex\tno-useful-delta\t1\t5\tfalse\tlauncher-failure\n",
        )
        .expect("append");
        let body = std::fs::read_to_string(&ledger).expect("read");
        assert!(body.contains("execution_issue_kind"));
        assert!(body.contains("launcher-failure"));
        let attempt = make_attempt_dir(dir.path(), 1, "codex").expect("attempt");
        assert!(attempt.is_dir());
        assert_eq!(command_argv(&["a", "b"]).len(), 2);
    }

    #[test]
    fn attempt_evidence_helpers_publish_redacted_sidecars() {
        let dir = TempDir::new().expect("tempdir");
        // Production attempt dirs are canonical (mkdtemp under the canonical tmp);
        // canonicalize here so the confined-write target matches its root.
        let run_dir = &dir.path().canonicalize().expect("canonical run dir");
        let run_dir = run_dir.as_path();
        // No sidecar yet.
        assert_eq!(stderr_tail_text(run_dir, "codex.log"), "");
        assert_eq!(coder_stderr_tail(run_dir, "codex.log"), "");
        write(run_dir, "codex.log.stderr-tail", "boom failure\n");
        assert!(stderr_tail_text(run_dir, "codex.log").contains("boom"));
        let redacted = coder_stderr_tail(run_dir, "codex.log");
        assert!(redacted.ends_with("codex.log.stderr-tail.redacted"));
        assert!(Path::new(&redacted).is_file());
        write(run_dir, "codex.log", "attempt transcript output\n");
        let attempt = redacted_attempt_log(run_dir, "codex.log");
        assert!(attempt.ends_with("codex.log.redacted"));
        // Execution-issue detail collapses whitespace and falls back cleanly.
        assert_eq!(execution_issue_detail(""), "attempt log unavailable");
        let detail = execution_issue_detail(&run_dir.join("codex.log").to_string_lossy());
        assert_eq!(detail, "attempt transcript output");
        append_execution_issue_row(
            &run_dir.join("issues.md"),
            "codex",
            "launcher-failure",
            &detail,
        );
        append_execution_issue_row(&run_dir.join("issues.md"), "codex", "", "skipped");
    }

    fn request(tmp: &Path, checks_log: &str, site: &str) -> LintFixRequest {
        LintFixRequest {
            site: site.to_owned(),
            checks_log: checks_log.to_owned(),
            repo_root: tmp.to_string_lossy().into_owned(),
            run_parent: tmp.join("lint-fix-loop").to_string_lossy().into_owned(),
            allowed_tmpdir: tmp.to_string_lossy().into_owned(),
            claude_present: false,
            codex_present: false,
            cursor_present: false,
        }
    }

    #[test]
    fn run_lint_fix_impl_rejects_unknown_site() {
        let outcome = run_lint_fix_impl(&request(Path::new("/tmp"), "/tmp/x", "not-a-site"));
        assert_eq!(outcome.status, "failed");
        assert_eq!(outcome.failure_reason.as_deref(), Some("unknown-site"));
    }

    #[test]
    fn run_lint_fix_impl_rejects_an_unconfined_checks_log() {
        let tmp = TempDir::new().expect("tempdir");
        let root = tmp.path().canonicalize().expect("canonical");
        let outcome = run_lint_fix_impl(&request(&root, "/etc/hostname", "step5"));
        assert_eq!(
            outcome.failure_reason.as_deref(),
            Some("checks-log-invalid")
        );
    }

    #[test]
    fn run_lint_fix_impl_empty_log_is_no_changes() {
        let tmp = TempDir::new().expect("tempdir");
        let root = tmp.path().canonicalize().expect("canonical");
        let log = root.join("checks.log");
        std::fs::write(&log, "").expect("empty log");
        let outcome = run_lint_fix_impl(&request(&root, &log.to_string_lossy(), "step5"));
        assert_eq!(outcome.status, "no-changes");
    }

    #[test]
    fn run_lint_fix_impl_structural_ruff_is_ledger_ready() {
        let tmp = TempDir::new().expect("tempdir");
        let root = tmp.path().canonicalize().expect("canonical");
        let log = root.join("checks.log");
        std::fs::write(&log, "a.py:1:1: C901 too complex\n").expect("log");
        let outcome = run_lint_fix_impl(&request(&root, &log.to_string_lossy(), "step6"));
        assert_eq!(outcome.status, "main-agent-required");
        assert!(outcome.ledger_ready);
        assert_eq!(outcome.ledger_step, "6");
    }

    #[test]
    fn git_helpers_fail_closed_on_bad_input() {
        let repo = init_repo();
        let root = repo.path();
        // A non-existent ref yields an empty committed delta rather than an error.
        assert!(committed_delta_paths(root, "not-a-ref", "also-not-a-ref").is_empty());
        // reset_hard / restore_path return false on an unresolvable target.
        assert!(!reset_hard(
            root,
            "0000000000000000000000000000000000000000"
        ));
        assert!(!restore_path(root, "missing/path.txt"));
        // A non-repository root fails closed everywhere.
        let empty = TempDir::new().expect("tempdir");
        assert!(capture_snapshot(empty.path()).is_none());
        assert_eq!(current_branch(empty.path()), "");
        assert_eq!(
            committed_delta_paths(empty.path(), "a", "b"),
            Vec::<String>::new()
        );
    }

    #[test]
    fn committed_delta_reports_a_rename() {
        let repo = init_repo();
        let root = repo.path();
        let base = head_ref(root).expect("base");
        git(root, &["mv", "a.txt", "renamed.txt"]);
        let head = commit_all(root, "rename");
        // The rename shows both the old and new path in the name-only delta.
        let delta = committed_delta_paths(root, &base.hex, &head.hex);
        assert!(
            delta.iter().any(|path| path == "renamed.txt"),
            "delta: {delta:?}"
        );
    }

    #[test]
    fn run_lint_fix_exhausts_without_a_selectable_tier() {
        let tmp = TempDir::new().expect("tempdir");
        let root = tmp.path().canonicalize().expect("canonical");
        let log = root.join("checks.log");
        std::fs::write(&log, "scripts/x.sh:1: MD038 failure\n").expect("log");
        // The wrapper records the lane timing on a non-Claude outcome.
        let outcome = run_lint_fix(&request(&root, &log.to_string_lossy(), "step5"));
        assert_eq!(outcome.status, "failed");
        assert_eq!(
            outcome.failure_reason.as_deref(),
            Some("lint-fix-no-selectable-tier")
        );
        assert!(!outcome.tier_ledger_path.is_empty());
    }
}
