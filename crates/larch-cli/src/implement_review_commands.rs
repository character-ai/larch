//! Rust owners for the `/implement` Step 5-7a review-routing commands:
//! `step-5-review`, `step-5-resume`, `checks-step5-resume`, `step-6-entry`,
//! and `step-7a`. The parents launch or rejoin the shared bgjob adapter and the
//! children delegate the still-Python composites and already-Rust verbs through
//! the verified `scripts/larch.sh` bootstrap.

use std::{
    collections::HashMap,
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use larch_adapters::GixRepository;
use larch_core::{
    ChildEnvironment, ExternalProgram, LarchProgram, ProcessOutput, RepositoryRead, Revision,
    log_paths, resolve_run_id, result_env_path, write_bytes_atomic,
};

use crate::{
    argparse_compat::{choice_error, parse_required_with_help, usage_error},
    child_process::{bounded_request_in, run_bounded},
    implement_child_seam::resolve_plugin_root,
    implement_dispatch_commands::{
        LaunchIdentity, checks_launch_identity, delegate_python, delegate_verified_larch,
        format_rows, opt_string, owner_pid_string, prepare_checks_rejoin, publish_identity_child,
        publish_rows, safe_merge_env, unlink_safe,
    },
    python_verb::publish_session_environment,
};

const STEP5_REVIEW_STEP: &str = "implement-step5-review";
const STEP5_RESUME_STEP: &str = "implement-step5-resume";
const STEP6_CHECKS_STEP: &str = "implement-step6-checks";
const STEP7A_STEP: &str = "implement-step7a";

const CHECKS_HEAD: &str = "CHECKS_INPUT_HEAD_SHA";
const CHECKS_FP: &str = "CHECKS_INPUT_TREE_FP";
const CHECKS_SCHEMA: &str = "CHECKS_INPUT_FP_SCHEMA";
const BGJOB_RC_KEY: &str = "BGJOB_RC";

const STEP5_RESULT_ENVELOPE_KEYS: &[&str] = &[
    "STEP5_REVIEW_STATUS",
    "STALL_TRACKING",
    "STALL_REASON",
    "ROUNDS_COMPLETED",
    "FINAL_ROUND_NUM",
    "FINAL_REVIEW_AND_FIX_STATUS",
    "CODER_STATUS",
    "FILES_CHANGED_HINT",
    "EFFECTIVE_ROUND_CAP",
];

const STEP5_RESUME_COMMIT_RELAY_KEYS: &[&str] =
    &["COMMITTED", "ERROR", "SHA", "COMMIT_OUTCOME", "NEXT_ACTION"];

const ADAPT_TIMEOUT: Duration = Duration::from_secs(600);
const ADAPT_GRACE: Duration = Duration::from_secs(5);
const ADAPT_OUTPUT_LIMIT: usize = 256 * 1024;

// ---------------------------------------------------------------------------
// step-5-review
// ---------------------------------------------------------------------------

const STEP5_REVIEW_PROG: &str = "cli.py implement step-5-review";
const STEP5_REVIEW_USAGE: &str = "usage: cli.py implement step-5-review [-h] [--bgjob-child]\n                                      [--merge-result-env MERGE_RESULT_ENV]\n";
const STEP5_REVIEW_HELP: &str = "usage: cli.py implement step-5-review [-h] [--bgjob-child]\n                                      [--merge-result-env MERGE_RESULT_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n";

/// `implement step-5-review` compatibility command.
pub fn step5_review(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        STEP5_REVIEW_PROG,
        STEP5_REVIEW_USAGE,
        STEP5_REVIEW_HELP,
        &["--merge-result-env"],
        &["--bgjob-child"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let Ok(tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    rehydrate(&tmpdir);
    if parsed.flag("--bgjob-child") {
        let merge_raw = opt_string(parsed.value("--merge-result-env"));
        if merge_raw.is_empty() {
            eprintln!("step-5-review: --merge-result-env is required in child mode");
            return ExitCode::from(2);
        }
        let (rc, output) = step5_review_worker(&tmpdir);
        if !publish_step5_child(&tmpdir, &merge_raw, &output) {
            return ExitCode::from(2);
        }
        print!("{output}");
        let _ = std::io::stdout().flush();
        return exit_code(rc);
    }
    run_parent_flow(|| {
        let state = step5_canonical_result_env_state(&tmpdir)?;
        prepare_step5_result(&tmpdir, STEP5_REVIEW_STEP, &state)?;
        let merge_env = safe_merge_env(&tmpdir, &tmpdir.join(".step5-review-result.env"))?;
        run_adapter(&AdapterSpec {
            tmpdir: tmpdir.clone(),
            step: STEP5_REVIEW_STEP,
            budget_s: 21600,
            verb: "step-5-review",
            public_args: Vec::new(),
            merge_env,
            initial_merge_rows: Vec::new(),
            repo_root: None,
        })
    })
}

fn step5_review_worker(tmpdir: &Path) -> (i32, String) {
    let _ = larch_env(
        &[
            OsString::from("timing"),
            OsString::from("telemetry-mark"),
            OsString::from("--implement-tmpdir"),
            tmpdir.as_os_str().to_owned(),
            OsString::from("--label"),
            OsString::from("Step 5 — code review"),
        ],
        &[],
    );
    let dynamic_cap = resolve_dynamic_cap(tmpdir);
    if dynamic_cap != "0" && dynamic_cap != "1" {
        eprintln!(
            "ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: {dynamic_cap}"
        );
        return (2, String::new());
    }
    eprintln!(
        "> **🔶 /implement 5: code review: review-and-fix step5 --mode loop, fixed tier cap 2; escalated rounds skip pruning; prune-to-empty converges; no round-5 re-probe; dynamic-archetypes cap={dynamic_cap}**"
    );
    let mut command = vec![
        OsString::from("review-and-fix"),
        OsString::from("step5"),
        OsString::from("--implement-tmpdir"),
        tmpdir.as_os_str().to_owned(),
        OsString::from("--mode"),
        OsString::from("loop"),
        OsString::from("--starting-round"),
        OsString::from("1"),
    ];
    let difficulty = difficulty_override(tmpdir);
    if !difficulty.is_empty() {
        command.push(OsString::from("--difficulty"));
        command.push(OsString::from(&difficulty));
    }
    forward_worker(larch_env(
        &command,
        &[(
            ChildEnvironment::LarchDynamicArchetypesMax,
            OsString::from(&dynamic_cap),
        )],
    ))
}

// ---------------------------------------------------------------------------
// step-5-resume
// ---------------------------------------------------------------------------

const STEP5_RESUME_PROG: &str = "cli.py implement step-5-resume";
const STEP5_RESUME_USAGE: &str = "usage: cli.py implement step-5-resume [-h] --final-round-num FINAL_ROUND_NUM\n                                      [--checks-site CHECKS_SITE]\n                                      [--ready-to-commit] [--record-only]\n                                      [--bgjob-child]\n                                      [--merge-result-env MERGE_RESULT_ENV]\n";
const STEP5_RESUME_HELP: &str = "usage: cli.py implement step-5-resume [-h] --final-round-num FINAL_ROUND_NUM\n                                      [--checks-site CHECKS_SITE]\n                                      [--ready-to-commit] [--record-only]\n                                      [--bgjob-child]\n                                      [--merge-result-env MERGE_RESULT_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --final-round-num FINAL_ROUND_NUM\n  --checks-site CHECKS_SITE\n  --ready-to-commit\n  --record-only\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n";

/// `implement step-5-resume` compatibility command.
pub fn step5_resume(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        STEP5_RESUME_PROG,
        STEP5_RESUME_USAGE,
        STEP5_RESUME_HELP,
        &["--final-round-num", "--checks-site", "--merge-result-env"],
        &["--ready-to-commit", "--record-only", "--bgjob-child"],
        &["--final-round-num"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let final_round_num = opt_string(parsed.value("--final-round-num"));
    if !is_digits(&final_round_num) {
        eprintln!("step-5-resume: --final-round-num must be numeric");
        return ExitCode::from(2);
    }
    let Ok(tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    rehydrate(&tmpdir);
    let checks_site = opt_string(parsed.value("--checks-site"));
    let ready_to_commit = parsed.flag("--ready-to-commit");
    let bgjob_child = parsed.flag("--bgjob-child");
    if parsed.flag("--record-only") {
        if bgjob_child {
            eprintln!("step-5-resume: --record-only cannot run in child mode");
            return ExitCode::from(2);
        }
        record_step5_handoff_timing(&tmpdir, &final_round_num);
        return ExitCode::SUCCESS;
    }
    if bgjob_child {
        let merge_raw = opt_string(parsed.value("--merge-result-env"));
        if merge_raw.is_empty() {
            eprintln!("step-5-resume: --merge-result-env is required in child mode");
            return ExitCode::from(2);
        }
        let (rc, output) =
            step5_resume_worker(&tmpdir, &final_round_num, &checks_site, ready_to_commit);
        if !publish_step5_child(&tmpdir, &merge_raw, &output) {
            return ExitCode::from(2);
        }
        print!("{output}");
        let _ = std::io::stdout().flush();
        return exit_code(rc);
    }
    let mut public_args = vec![
        OsString::from("--final-round-num"),
        OsString::from(&final_round_num),
    ];
    if ready_to_commit {
        public_args.push(OsString::from("--ready-to-commit"));
    }
    if !checks_site.is_empty() {
        public_args.push(OsString::from("--checks-site"));
        public_args.push(OsString::from(&checks_site));
    }
    run_parent_flow(|| {
        let state = step5_resume_result_env_state(&tmpdir)?;
        prepare_step5_result(&tmpdir, STEP5_RESUME_STEP, &state)?;
        let merge_env = safe_merge_env(
            &tmpdir,
            &tmpdir
                .join("bgjob")
                .join(format!("{STEP5_RESUME_STEP}.merge.env")),
        )?;
        run_adapter(&AdapterSpec {
            tmpdir: tmpdir.clone(),
            step: STEP5_RESUME_STEP,
            budget_s: 32700,
            verb: "step-5-resume",
            public_args: public_args.clone(),
            merge_env,
            initial_merge_rows: Vec::new(),
            repo_root: None,
        })
    })
}

fn step5_resume_worker(
    tmpdir: &Path,
    final_round_num: &str,
    checks_site: &str,
    ready_to_commit: bool,
) -> (i32, String) {
    record_step5_handoff_timing(tmpdir, final_round_num);
    let mut out = String::new();
    if !checks_site.is_empty() {
        let (rc, text) = run_checks_step5_resume(tmpdir, checks_site, final_round_num);
        out.push_str(&text);
        return (rc, out);
    }
    let ready = ready_to_commit
        || env::var("STEP5_HANDOFF_READY_TO_COMMIT").ok().as_deref() == Some("true");
    if ready {
        let (commit_rc, text) = step5_resume_commit_phase();
        out.push_str(&text);
        if let Some(rc) = commit_rc {
            if rc == 0 {
                out.push_str("STEP5_REVIEW_STATUS=stall\n");
            }
            return (rc, out);
        }
    }
    let next_round = match final_round_num.parse::<u64>() {
        Ok(value) => (value + 1).to_string(),
        Err(_) => return (2, out),
    };
    let mut command = vec![
        OsString::from("review-and-fix"),
        OsString::from("step5"),
        OsString::from("--implement-tmpdir"),
        tmpdir.as_os_str().to_owned(),
        OsString::from("--mode"),
        OsString::from("loop"),
        OsString::from("--starting-round"),
        OsString::from(&next_round),
    ];
    let difficulty = difficulty_override(tmpdir);
    if !difficulty.is_empty() {
        command.push(OsString::from("--difficulty"));
        command.push(OsString::from(&difficulty));
    }
    let (rc, text) = forward_worker(larch(&command));
    out.push_str(&text);
    (rc, out)
}

/// Run the shared commit-route and relay its routing envelope.
///
/// Returns `(None, output)` on the continue path so the caller resumes the next
/// review round; otherwise `(Some(rc), output)`.
fn step5_resume_commit_phase() -> (Option<i32>, String) {
    let mut out = String::new();
    let Ok(commit) = delegate_python([
        OsString::from("implement"),
        OsString::from("commit-route"),
        OsString::from("--site"),
        OsString::from("step5-resume-handoff"),
    ]) else {
        return (Some(1), out);
    };
    if !commit.stderr().is_empty() {
        let _ = std::io::stderr().write_all(commit.stderr());
    }
    let commit_output = String::from_utf8_lossy(commit.stdout()).into_owned();
    let rc = commit.status().code().unwrap_or(1);
    let next_actions = parse_line_anchored(&commit_output, "NEXT_ACTION");
    if next_actions.len() == 1 && (next_actions[0] == "continue" || next_actions[0] == "stall") {
        out.push_str("NEXT_ACTION=");
        out.push_str(&next_actions[0]);
        out.push('\n');
        out.push_str(&relay_commit_kvs(&commit_output, false));
        if next_actions[0] == "stall" {
            return (Some(0), out);
        }
        if rc != 0 {
            return (Some(rc), out);
        }
        return (None, out);
    }
    out.push_str(&relay_commit_kvs(&commit_output, true));
    (Some(if rc != 0 { rc } else { 1 }), out)
}

// ---------------------------------------------------------------------------
// checks-step5-resume
// ---------------------------------------------------------------------------

const CHECKS_STEP5_PROG: &str = "cli.py implement checks-step5-resume";
const CHECKS_STEP5_USAGE: &str = "usage: cli.py implement checks-step5-resume [-h] --checks-site CHECKS_SITE\n                                            --final-round-num FINAL_ROUND_NUM\n                                            [--checks-deadline-ms CHECKS_DEADLINE_MS]\n                                            [--resume-deadline-ms RESUME_DEADLINE_MS]\n";
const CHECKS_STEP5_HELP: &str = "usage: cli.py implement checks-step5-resume [-h] --checks-site CHECKS_SITE\n                                            --final-round-num FINAL_ROUND_NUM\n                                            [--checks-deadline-ms CHECKS_DEADLINE_MS]\n                                            [--resume-deadline-ms RESUME_DEADLINE_MS]\n\noptions:\n  -h, --help            show this help message and exit\n  --checks-site CHECKS_SITE\n  --final-round-num FINAL_ROUND_NUM\n  --checks-deadline-ms CHECKS_DEADLINE_MS\n  --resume-deadline-ms RESUME_DEADLINE_MS\n";

/// `implement checks-step5-resume` compatibility command.
pub fn checks_step5_resume(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        CHECKS_STEP5_PROG,
        CHECKS_STEP5_USAGE,
        CHECKS_STEP5_HELP,
        &[
            "--checks-site",
            "--final-round-num",
            "--checks-deadline-ms",
            "--resume-deadline-ms",
        ],
        &[],
        &["--checks-site", "--final-round-num"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let final_round_num = opt_string(parsed.value("--final-round-num"));
    if !is_digits(&final_round_num) {
        eprintln!("checks-step5-resume: --final-round-num must be numeric");
        return ExitCode::from(2);
    }
    let Ok(tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    rehydrate(&tmpdir);
    let checks_site = opt_string(parsed.value("--checks-site"));
    let (rc, output) = run_checks_step5_resume(&tmpdir, &checks_site, &final_round_num);
    print!("{output}");
    let _ = std::io::stdout().flush();
    exit_code(rc)
}

fn run_checks_step5_resume(
    tmpdir: &Path,
    checks_site: &str,
    final_round_num: &str,
) -> (i32, String) {
    let mut out = String::new();
    let repo_root = match resolve_session_repo_root(tmpdir) {
        Ok(root) => root,
        Err(message) => {
            eprintln!("{message}");
            return (2, out);
        }
    };
    let (captured, timed_out) = run_relevant_checks_for_site(tmpdir, checks_site, &repo_root);
    out.push_str(&checks_relay_line(&captured));
    out.push('\n');
    if timed_out || !checks_pass(&captured) {
        out.push_str("NEXT_ACTION=checks-failed\n");
        return (0, out);
    }
    let (rc, resume_stdout) = run_step5_resume_leg(tmpdir, final_round_num);
    if !resume_stdout.is_empty() {
        out.push_str(&resume_stdout);
        if !resume_stdout.ends_with('\n') {
            out.push('\n');
        }
    }
    (rc, out)
}

fn run_step5_resume_leg(tmpdir: &Path, final_round_num: &str) -> (i32, String) {
    let merge_env = tmpdir
        .join("bgjob")
        .join(format!("{STEP5_RESUME_STEP}.merge.env"));
    let args = vec![
        OsString::from("implement"),
        OsString::from("step-5-resume"),
        OsString::from("--final-round-num"),
        OsString::from(final_round_num),
        OsString::from("--ready-to-commit"),
        OsString::from("--bgjob-child"),
        OsString::from("--merge-result-env"),
        merge_env.into_os_string(),
    ];
    larch(&args).map_or_else(
        |_| (2, String::new()),
        |output| {
            if !output.stderr().is_empty() {
                let _ = std::io::stderr().write_all(output.stderr());
            }
            (
                output.status().code().unwrap_or(1),
                String::from_utf8_lossy(output.stdout()).into_owned(),
            )
        },
    )
}

// ---------------------------------------------------------------------------
// step-6-entry
// ---------------------------------------------------------------------------

const STEP6_PROG: &str = "cli.py implement step-6-entry";
const STEP6_USAGE: &str = "usage: cli.py implement step-6-entry [-h] [--forked-target {true,false}]\n                                     [--force-checks {true,false}] [--bgjob-child]\n                                     [--merge-result-env MERGE_RESULT_ENV]\n                                     [--repo-root REPO_ROOT] [--launch-head LAUNCH_HEAD]\n                                     [--launch-fp LAUNCH_FP] [--launch-schema LAUNCH_SCHEMA]\n";
const STEP6_HELP: &str = "usage: cli.py implement step-6-entry [-h] [--forked-target {true,false}]\n                                     [--force-checks {true,false}] [--bgjob-child]\n                                     [--merge-result-env MERGE_RESULT_ENV]\n                                     [--repo-root REPO_ROOT] [--launch-head LAUNCH_HEAD]\n                                     [--launch-fp LAUNCH_FP] [--launch-schema LAUNCH_SCHEMA]\n\noptions:\n  -h, --help            show this help message and exit\n  --forked-target {true,false}\n  --force-checks {true,false}\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n  --repo-root REPO_ROOT\n  --launch-head LAUNCH_HEAD\n  --launch-fp LAUNCH_FP\n  --launch-schema LAUNCH_SCHEMA\n";

/// `implement step-6-entry` compatibility command.
#[allow(clippy::too_many_lines)] // Parent and child bgjob legs share one compatibility boundary.
pub fn step6_entry(arguments: &[OsString]) -> ExitCode {
    if let Some(error) = choice_error(
        arguments,
        &[
            "--forked-target",
            "--force-checks",
            "--merge-result-env",
            "--repo-root",
            "--launch-head",
            "--launch-fp",
            "--launch-schema",
            "--bgjob-child",
            "-h",
            "--help",
        ],
        &[
            ("--forked-target", &["true", "false"]),
            ("--force-checks", &["true", "false"]),
        ],
    ) {
        return usage_error(STEP6_USAGE, STEP6_PROG, &error, 2);
    }
    let parsed = match parse_required_with_help(
        arguments,
        STEP6_PROG,
        STEP6_USAGE,
        STEP6_HELP,
        &[
            "--forked-target",
            "--force-checks",
            "--merge-result-env",
            "--repo-root",
            "--launch-head",
            "--launch-fp",
            "--launch-schema",
        ],
        &["--bgjob-child"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let forked_target = default_false(parsed.value("--forked-target"));
    let force_checks = default_false(parsed.value("--force-checks"));
    let Ok(tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    rehydrate(&tmpdir);
    if parsed.flag("--bgjob-child") {
        let result = (|| -> Result<ExitCode, String> {
            let merge_env = safe_merge_env(
                &tmpdir,
                Path::new(&opt_string(parsed.value("--merge-result-env"))),
            )?;
            let launch = identity_from_child_args(
                &opt_string(parsed.value("--repo-root")),
                &opt_string(parsed.value("--launch-head")),
                &opt_string(parsed.value("--launch-fp")),
                &opt_string(parsed.value("--launch-schema")),
            )?;
            publish_session_environment(vec![
                (
                    ChildEnvironment::RepoRoot,
                    launch.repo_root.as_os_str().into(),
                ),
                (
                    ChildEnvironment::ClaudeProjectDir,
                    launch.repo_root.as_os_str().into(),
                ),
                (ChildEnvironment::ImplementTmpdir, tmpdir.as_os_str().into()),
            ]);
            publish_identity_child(
                &tmpdir,
                STEP6_CHECKS_STEP,
                &merge_env,
                &launch,
                true,
                || Ok(step6_entry_worker(&forked_target, &force_checks, &tmpdir)),
            )
        })();
        return result.unwrap_or_else(|_| ExitCode::from(2));
    }
    let public_args = vec![
        OsString::from("--forked-target"),
        OsString::from(&forked_target),
        OsString::from("--force-checks"),
        OsString::from(&force_checks),
    ];
    let result = (|| -> Result<ExitCode, String> {
        let identity = checks_launch_identity(&tmpdir)?;
        let merge_env = safe_merge_env(
            &tmpdir,
            &tmpdir
                .join("bgjob")
                .join(format!("{STEP6_CHECKS_STEP}.merge.env")),
        )?;
        prepare_checks_rejoin(&tmpdir, STEP6_CHECKS_STEP, &merge_env, &identity)?;
        let mut args = public_args.clone();
        args.extend([
            OsString::from("--repo-root"),
            identity.repo_root.as_os_str().to_owned(),
            OsString::from("--launch-head"),
            OsString::from(&identity.head_sha),
            OsString::from("--launch-fp"),
            OsString::from(&identity.tree_fp),
            OsString::from("--launch-schema"),
            OsString::from(&identity.schema),
        ]);
        run_adapter(&AdapterSpec {
            tmpdir: tmpdir.clone(),
            step: STEP6_CHECKS_STEP,
            budget_s: 15600,
            verb: "step-6-entry",
            public_args: args,
            merge_env,
            initial_merge_rows: identity.as_rows(),
            repo_root: Some(identity.repo_root),
        })
    })();
    match result {
        Ok(code) => code,
        Err(message) => {
            eprintln!("step-6-entry: {message}");
            ExitCode::from(2)
        }
    }
}

fn step6_entry_worker(forked_target: &str, force_checks: &str, tmpdir: &Path) -> (i32, String) {
    let _ = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(tmpdir.join(".review-boundary-passed"));
    if force_checks == "true" {
        return run_step6_composite(forked_target);
    }
    let mut out = String::new();
    let (cc_rc, cc_stdout) = forward_worker(larch(&[
        OsString::from("review-and-fix"),
        OsString::from("check-changes"),
        OsString::from("--baseline"),
        tmpdir.join("pre-review-untracked.txt").into_os_string(),
        OsString::from("--head-baseline"),
        tmpdir.join("pre-review-head.txt").into_os_string(),
    ]));
    out.push_str(&cc_stdout);
    let files_changed = parse_line_anchored(&cc_stdout, "FILES_CHANGED");
    if cc_rc != 0
        || files_changed.len() != 1
        || (files_changed[0] != "true" && files_changed[0] != "false")
    {
        let (rc, text) = step6_entry_seed_stall(tmpdir);
        out.push_str(&text);
        return (rc, out);
    }
    if files_changed[0] == "false" {
        out.push_str("NEXT_ACTION=skip-to-7a\n");
        return (0, out);
    }
    let (rc, text) = run_step6_composite(forked_target);
    out.push_str(&text);
    (rc, out)
}

fn run_step6_composite(forked_target: &str) -> (i32, String) {
    let args = vec![
        OsString::from("implement"),
        OsString::from("checks-commit-route"),
        OsString::from("--checks-site"),
        OsString::from("step6"),
        OsString::from("--commit-site"),
        OsString::from("step7"),
        OsString::from("--emit-step7-breadcrumb"),
        OsString::from("--rebase-checkpoint-7r"),
        OsString::from("--forked-target"),
        OsString::from(forked_target),
    ];
    forward_worker(larch(&args))
}

fn step6_entry_seed_stall(tmpdir: &Path) -> (i32, String) {
    let seeded = larch(&[
        OsString::from("implement"),
        OsString::from("step-8-seed-initial"),
        OsString::from("--stall-tracking"),
        OsString::from("true"),
        OsString::from("--stall-step"),
        OsString::from("6"),
        OsString::from("--bail-reason"),
        OsString::from("review-change-detection-failed"),
    ]);
    let ok = seeded.is_ok_and(|output| {
        if !output.stderr().is_empty() {
            let _ = std::io::stderr().write_all(output.stderr());
        }
        output.status().success()
    });
    let _ = tmpdir;
    if !ok {
        return (1, String::new());
    }
    (0, "NEXT_ACTION=stall\n".to_owned())
}

fn identity_from_child_args(
    repo_root: &str,
    launch_head: &str,
    launch_fp: &str,
    launch_schema: &str,
) -> Result<LaunchIdentity, String> {
    if repo_root.is_empty()
        || launch_head.is_empty()
        || launch_fp.is_empty()
        || launch_schema.is_empty()
    {
        return Err("launch identity args required in child mode".into());
    }
    Ok(LaunchIdentity {
        head_sha: launch_head.to_owned(),
        tree_fp: launch_fp.to_owned(),
        schema: launch_schema.to_owned(),
        repo_root: PathBuf::from(repo_root),
    })
}

// ---------------------------------------------------------------------------
// step-7a
// ---------------------------------------------------------------------------

/// `implement step-7a` compatibility command.
pub fn step7a(arguments: &[OsString]) -> ExitCode {
    let Ok(args) = Step7aArgs::parse(arguments) else {
        return emit_arg_failure("argv");
    };
    let raw_tmpdir = if args.implement_tmpdir.is_empty() {
        env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
    } else {
        args.implement_tmpdir.clone()
    };
    if raw_tmpdir.is_empty() {
        return emit_arg_failure("missing-implement-tmpdir");
    }
    let tmpdir = PathBuf::from(&raw_tmpdir);
    if has_symlink_ancestor(&tmpdir) {
        return emit_arg_failure("invalid-implement-tmpdir");
    }
    if args.bgjob_launch == "true" {
        return launch_step7a_bgjob(&tmpdir, &args);
    }
    let merge_env = if args.bgjob_merge_result_env.is_empty() {
        None
    } else {
        Some(PathBuf::from(&args.bgjob_merge_result_env))
    };
    exit_code(run_step7a(&tmpdir, &args, merge_env.as_deref()))
}

struct Step7aArgs {
    implement_tmpdir: String,
    issue_number: String,
    run_id: String,
    no_logs_commit: String,
    forked_target: String,
    base_remote: String,
    base_ref: String,
    bgjob_launch: String,
    bgjob_merge_result_env: String,
}

impl Step7aArgs {
    fn parse(arguments: &[OsString]) -> Result<Self, ()> {
        let mut out = Self {
            implement_tmpdir: String::new(),
            issue_number: String::new(),
            run_id: String::new(),
            no_logs_commit: "false".to_owned(),
            forked_target: "false".to_owned(),
            base_remote: "origin".to_owned(),
            base_ref: "main".to_owned(),
            bgjob_launch: "false".to_owned(),
            bgjob_merge_result_env: String::new(),
        };
        let mut index = 0;
        while index < arguments.len() {
            let token = arguments[index].to_string_lossy().into_owned();
            let (name, inline) = match token.split_once('=') {
                Some((name, value)) => (name.to_owned(), Some(value.to_owned())),
                None => (token.clone(), None),
            };
            let value_for = |index: &mut usize| -> Result<String, ()> {
                if let Some(value) = &inline {
                    return Ok(value.clone());
                }
                *index += 1;
                arguments
                    .get(*index)
                    .map(|value| value.to_string_lossy().into_owned())
                    .ok_or(())
            };
            match name.as_str() {
                "--implement-tmpdir" => out.implement_tmpdir = value_for(&mut index)?,
                "--issue-number" => out.issue_number = value_for(&mut index)?,
                "--run-id" => out.run_id = value_for(&mut index)?,
                "--no-logs-commit" => out.no_logs_commit = choice(value_for(&mut index)?)?,
                "--forked-target" => out.forked_target = choice(value_for(&mut index)?)?,
                "--base-remote" => out.base_remote = value_for(&mut index)?,
                "--base-ref" => out.base_ref = value_for(&mut index)?,
                "--bgjob-launch" => out.bgjob_launch = choice(value_for(&mut index)?)?,
                "--bgjob-merge-result-env" => out.bgjob_merge_result_env = value_for(&mut index)?,
                _ => return Err(()),
            }
            index += 1;
        }
        Ok(out)
    }
}

fn choice(value: String) -> Result<String, ()> {
    if value == "true" || value == "false" {
        Ok(value)
    } else {
        Err(())
    }
}

fn emit_arg_failure(bail_reason: &str) -> ExitCode {
    for (key, value) in [
        ("DIAGRAM_STATUS", "failed"),
        ("DIAGRAM_REASON", ""),
        ("DIAGRAM_PATH", ""),
        ("COMMENT_URL", ""),
        ("LOG_CHECKPOINT_STATUS", "skip"),
        ("STEP_7A_BAIL_REASON", bail_reason),
        ("REBASE_OUTCOME", "skipped"),
    ] {
        println!("{key}={value}");
    }
    ExitCode::from(2)
}

fn launch_step7a_bgjob(tmpdir: &Path, args: &Step7aArgs) -> ExitCode {
    let merge_env = tmpdir
        .join("bgjob")
        .join(format!("{STEP7A_STEP}.merge.env"));
    if let Some(parent) = merge_env.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if write_bytes_atomic(&merge_env, b"").is_err() {
        return ExitCode::from(2);
    }
    let Ok(root) = resolve_plugin_root() else {
        return ExitCode::from(2);
    };
    let entry = root.join("scripts").join("larch.sh");
    let command = vec![
        OsString::from("bgjob"),
        OsString::from("start"),
        OsString::from("--step"),
        OsString::from(STEP7A_STEP),
        OsString::from("--tmpdir"),
        tmpdir.as_os_str().to_owned(),
        OsString::from("--budget-s"),
        OsString::from("1800"),
        OsString::from("--merge-result-env"),
        merge_env.as_os_str().to_owned(),
        OsString::from("--terminal-stdout-key"),
        OsString::from("DIAGRAM_STATUS"),
        OsString::from("--"),
        entry.into_os_string(),
        OsString::from("implement"),
        OsString::from("step-7a"),
        OsString::from("--implement-tmpdir"),
        tmpdir.as_os_str().to_owned(),
        OsString::from("--issue-number"),
        OsString::from(&args.issue_number),
        OsString::from("--run-id"),
        OsString::from(&args.run_id),
        OsString::from("--no-logs-commit"),
        OsString::from(&args.no_logs_commit),
        OsString::from("--forked-target"),
        OsString::from(&args.forked_target),
        OsString::from("--base-remote"),
        OsString::from(&args.base_remote),
        OsString::from("--base-ref"),
        OsString::from(&args.base_ref),
        OsString::from("--bgjob-merge-result-env"),
        merge_env.as_os_str().to_owned(),
    ];
    larch(&command).map_or_else(
        |_| ExitCode::from(2),
        |output| {
            let _ = std::io::stdout().write_all(output.stdout());
            let _ = std::io::stdout().flush();
            if !output.stderr().is_empty() {
                let _ = std::io::stderr().write_all(output.stderr());
            }
            exit_code(output.status().code().unwrap_or(1))
        },
    )
}

#[allow(clippy::too_many_lines, clippy::cognitive_complexity)] // Pinned Step 7a phase order is one compatibility transaction.
fn run_step7a(tmpdir: &Path, args: &Step7aArgs, merge_env: Option<&Path>) -> i32 {
    let _ = fs::create_dir_all(tmpdir);
    let session_env = tmpdir.join("session-env.sh");
    let mut issue_number = args.issue_number.clone();
    if issue_number.is_empty() {
        issue_number = read_kv_file(&session_env, "LARCH_ISSUE_NUMBER");
    }
    let mut run_id = args.run_id.clone();
    if run_id.is_empty() {
        run_id = read_kv_file(&session_env, "LARCH_RUN_ID");
        if run_id.is_empty() {
            let session_id = tmpdir.join("session-id");
            if session_id.is_file() {
                let text = fs::read_to_string(&session_id).unwrap_or_default();
                run_id.clear();
                run_id.push_str(text.trim());
            }
        }
    }
    let forked_target = args.forked_target == "true"
        || (session_env.is_file() && read_kv_file(&session_env, "LARCH_FORKED_TARGET") == "true");
    let base_remote = if forked_target {
        "upstream".to_owned()
    } else {
        args.base_remote.clone()
    };
    let mut repo = String::new();
    if session_env.is_file() {
        if forked_target {
            repo = read_kv_file(&session_env, "UPSTREAM_REPO");
        }
        if repo.is_empty() {
            repo = read_kv_file(&session_env, "REPO");
        }
        if repo.is_empty() {
            repo = read_kv_file(&session_env, "UPSTREAM_REPO");
        }
    }

    mark_step("Step 7a — pre-ship");

    let mut rows: Vec<(String, String)> = Vec::new();
    let mut comment_url = String::new();

    let (diagram_status, diagram_path, diagram_reason) =
        if is_small_non_runtime_change(&base_remote, &args.base_ref) {
            cleanup_diagram_artifacts(tmpdir);
            println!("⏩ 7a: pre-ship status=skip reason=small-non-runtime-change elapsed=0s");
            ("skip".to_owned(), String::new(), String::new())
        } else {
            let (status, path, reason) =
                generate_code_flow_diagram(tmpdir, &base_remote, &args.base_ref);
            let reason = if status == "failed" {
                reason
            } else {
                String::new()
            };
            (status, path, reason)
        };

    let section = tmpdir.join("code-flow-section.md");
    if !issue_number.is_empty()
        && section.is_file()
        && section.metadata().map(|m| m.len() > 0).unwrap_or(false)
    {
        let mut upsert_args = vec![
            OsString::from("diagrams"),
            OsString::from("upsert"),
            OsString::from("--issue"),
            OsString::from(&issue_number),
            OsString::from("--code-flow-file"),
            section.as_os_str().to_owned(),
        ];
        if !repo.is_empty() {
            upsert_args.push(OsString::from("--repo"));
            upsert_args.push(OsString::from(&repo));
        }
        if let Ok(output) = larch(&upsert_args)
            && output.status().success()
        {
            let text = String::from_utf8_lossy(output.stdout());
            let upsert_status = first_line_value(&text, "UPSERT_STATUS");
            if upsert_status.as_deref() != Some("failed")
                && let Some(url) = first_line_value(&text, "COMMENT_URL")
            {
                comment_url = url;
            }
        }
    }

    let probe = larch(&[
        OsString::from("push"),
        OsString::from("checkpoint-probe"),
        OsString::from("7a.r"),
        OsString::from("diagrams"),
        OsString::from("--forked-target"),
        OsString::from("false"),
        OsString::from("--base-remote"),
        OsString::from(&base_remote),
        OsString::from("--base-ref"),
        OsString::from(&args.base_ref),
    ]);
    let (probe_rc, probe_stdout, probe_stderr) = probe.map_or_else(
        |_| (3, String::new(), Vec::new()),
        |output| {
            (
                output.status().code().unwrap_or(1),
                String::from_utf8_lossy(output.stdout()).into_owned(),
                output.stderr().to_vec(),
            )
        },
    );
    let _ = write_bytes_atomic(
        &tmpdir.join("rebase-checkpoint-probe.stdout"),
        probe_stdout.as_bytes(),
    );
    if !probe_stderr.is_empty() {
        let _ = std::io::stderr().write_all(&probe_stderr);
    }
    for line in probe_stdout.lines() {
        if !line.trim().is_empty() {
            emit_line(line, &mut rows);
        }
    }
    let log_checkpoint_status = checkpoint_execution_issues(tmpdir, &run_id);
    if probe_rc != 0 {
        let outcome = if probe_rc == 1 { "conflict" } else { "failed" };
        emit_final(
            &mut rows,
            &diagram_status,
            &diagram_reason,
            &diagram_path,
            &comment_url,
            &log_checkpoint_status,
            "",
            outcome,
        );
        flush_result_env(merge_env, &rows);
        return probe_rc;
    }
    let mut rebase_outcome = "skipped".to_owned();
    for line in probe_stdout.lines() {
        if let Some(rest) = line.strip_prefix("REBASE_OUTCOME=") {
            let value = rest.trim();
            rebase_outcome = if value.is_empty() {
                "skipped".to_owned()
            } else {
                value.to_owned()
            };
        }
    }
    emit_final(
        &mut rows,
        &diagram_status,
        &diagram_reason,
        &diagram_path,
        &comment_url,
        &log_checkpoint_status,
        "",
        &rebase_outcome,
    );
    flush_result_env(merge_env, &rows);
    0
}

#[allow(clippy::too_many_arguments)]
fn emit_final(
    rows: &mut Vec<(String, String)>,
    diagram_status: &str,
    diagram_reason: &str,
    diagram_path: &str,
    comment_url: &str,
    log_checkpoint_status: &str,
    bail: &str,
    rebase_outcome: &str,
) {
    for (key, value) in [
        ("DIAGRAM_STATUS", diagram_status),
        ("DIAGRAM_REASON", diagram_reason),
        ("DIAGRAM_PATH", diagram_path),
        ("COMMENT_URL", comment_url),
        ("LOG_CHECKPOINT_STATUS", log_checkpoint_status),
        ("STEP_7A_BAIL_REASON", bail),
        ("REBASE_OUTCOME", rebase_outcome),
    ] {
        emit_kv(key, value, rows);
    }
}

fn generate_code_flow_diagram(
    tmpdir: &Path,
    base_remote: &str,
    base_ref: &str,
) -> (String, String, String) {
    let output = larch(&[
        OsString::from("diagram"),
        OsString::from("code-flow"),
        OsString::from("--implement-tmpdir"),
        tmpdir.as_os_str().to_owned(),
        OsString::from("--base-remote"),
        OsString::from(base_remote),
        OsString::from("--base-ref"),
        OsString::from(base_ref),
    ]);
    let (exit, stdout) = output.map_or_else(
        |_| (1, String::new()),
        |output| {
            (
                output.status().code().unwrap_or(1),
                String::from_utf8_lossy(output.stdout()).into_owned(),
            )
        },
    );
    let status = first_line_value(&stdout, "STATUS").unwrap_or_default();
    let diagram_file = first_line_value(&stdout, "DIAGRAM_FILE").unwrap_or_default();
    let reason = first_line_value(&stdout, "SKIP_REASON").unwrap_or_default();

    let retry_sidecar = tmpdir.join("code-flow-diagram.retried");
    if retry_sidecar.is_file() {
        let first_rc = read_kv_file_last(&retry_sidecar, "FIRST_RC");
        let retry_msg = format!("code-flow subprocess transient (rc={first_rc}); retried once");
        append_diagram_warning(tmpdir, &retry_msg);
        let _ = fs::remove_file(&retry_sidecar);
    }
    if status == "ok" && !diagram_file.is_empty() {
        if let Ok(diagram) = fs::read_to_string(tmpdir.join("code-flow-diagram.md")) {
            let _ = write_bytes_atomic(&tmpdir.join("code-flow-section.md"), diagram.as_bytes());
        }
        return (status, diagram_file, reason);
    }
    cleanup_diagram_artifacts(tmpdir);
    if exit == 0 && status != "failed" {
        return (status, diagram_file, reason);
    }
    let reason = if reason.is_empty() {
        "generation failed".to_owned()
    } else {
        reason
    };
    append_diagram_warning(tmpdir, &reason);
    ("failed".to_owned(), String::new(), reason)
}

fn append_diagram_warning(tmpdir: &Path, message: &str) {
    let entry = format!("- **Step 7a — code flow diagram**: {message}");
    let _ = larch(&[
        OsString::from("execution-issues"),
        OsString::from("append"),
        OsString::from("--log"),
        tmpdir.join("execution-issues.md").into_os_string(),
        OsString::from("--category"),
        OsString::from("Warnings"),
        OsString::from("--entry"),
        OsString::from(entry),
        OsString::from("--report-status"),
        OsString::from("--spaced-section"),
    ]);
}

fn cleanup_diagram_artifacts(tmpdir: &Path) {
    let _ = fs::remove_file(tmpdir.join("code-flow-section.md"));
    let _ = fs::remove_file(tmpdir.join("code-flow-diagram.md"));
}

fn checkpoint_execution_issues(tmpdir: &Path, run_id: &str) -> String {
    mark_step("Step 8 — ship PR");
    if run_id.is_empty() {
        return "skip".to_owned();
    }
    let output = larch(&[
        OsString::from("execution-issues"),
        OsString::from("flush"),
        OsString::from("--log-root"),
        tmpdir.join("larch-logs").into_os_string(),
        OsString::from("--run-id"),
        OsString::from(run_id),
        OsString::from("--issue-log"),
        tmpdir.join("execution-issues.md").into_os_string(),
        OsString::from("--step-label"),
        OsString::from("7a"),
        OsString::from("--source-label"),
        OsString::from("execution-issues.md Step 7a checkpoint"),
    ]);
    output.map_or_else(
        |_| "degraded".to_owned(),
        |output| {
            let text = String::from_utf8_lossy(output.stdout());
            let status = first_line_value(&text, "FLUSH_STATUS").unwrap_or_default();
            let allowed = ["skip", "already-flushed", "no-records", "ok", "rendered"];
            let has_error = first_line_value(&text, "ERROR").is_some();
            if output.status().success() && allowed.contains(&status.as_str()) && !has_error {
                "ok".to_owned()
            } else {
                "degraded".to_owned()
            }
        },
    )
}

/// Emit token and timing marks under the implement timing skill.
fn mark_step(label: &str) {
    let _ = larch_env(
        &[
            OsString::from("token"),
            OsString::from("mark"),
            OsString::from(label),
        ],
        &[(
            ChildEnvironment::LarchTimingSkill,
            OsString::from("implement"),
        )],
    );
    let _ = larch_env(
        &[
            OsString::from("timing"),
            OsString::from("mark"),
            OsString::from(label),
        ],
        &[(
            ChildEnvironment::LarchTimingSkill,
            OsString::from("implement"),
        )],
    );
}

fn is_small_non_runtime_change(base_remote: &str, base_ref: &str) -> bool {
    let Some(paths) = small_change_paths(base_remote, base_ref) else {
        return false;
    };
    if paths.is_empty() || paths.len() > 2 {
        return false;
    }
    paths.iter().all(|path| is_non_runtime_path(path))
}

/// Name-only view of the committed diff against the base branch, resolved
/// through the typed `gix` port so the change probe never shells out to `git`.
fn small_change_paths(base_remote: &str, base_ref: &str) -> Option<Vec<String>> {
    let cwd = env::current_dir().ok()?;
    let repository = GixRepository::discover(&cwd).ok()?;
    let head = repository.resolve_revision(&Revision::new("HEAD")).ok()?;
    let base = repository
        .resolve_revision(&Revision::new(
            format!("{base_remote}/{base_ref}").into_bytes(),
        ))
        .ok()?;
    let merge_base = repository.merge_base(&head, &base).ok()?;
    let base_tree = repository
        .resolve_revision(&Revision::new(
            format!("{}^{{tree}}", merge_base.to_hex()).into_bytes(),
        ))
        .ok()?;
    let head_tree = repository
        .resolve_revision(&Revision::new("HEAD^{tree}"))
        .ok()?;
    let changes = repository.tree_changes(&base_tree, &head_tree).ok()?;
    Some(
        changes
            .paths()
            .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
            .collect(),
    )
}

fn is_non_runtime_path(path: &str) -> bool {
    if path.starts_with("docs/") {
        return true;
    }
    let base = Path::new(path)
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default();
    if base == "README.md" {
        return true;
    }
    if !path.contains('.') {
        return false;
    }
    let ext = path.rsplit('.').next().unwrap_or_default();
    ext == "txt" || ext == "tsv"
}

// ---------------------------------------------------------------------------
// step-5 result-env classification
// ---------------------------------------------------------------------------

fn step5_canonical_result_env_state(tmpdir: &Path) -> Result<String, String> {
    let path = result_env_path(tmpdir, STEP5_REVIEW_STEP).map_err(|e| e.to_string())?;
    let Some(rows) = read_result_rows(&path, tmpdir)? else {
        return Ok("absent".to_owned());
    };
    let status = rows.get("STEP5_REVIEW_STATUS").cloned().unwrap_or_default();
    if rows.get("STEP").map(String::as_str) != Some(STEP5_REVIEW_STEP)
        || !STEP5_RESULT_ENVELOPE_KEYS
            .iter()
            .all(|key| rows.contains_key(*key))
    {
        return Ok("stale".to_owned());
    }
    if rows.get(BGJOB_RC_KEY).map(String::as_str) == Some("0") && status == "complete" {
        if !step5_result_identity_ok(tmpdir, &rows) {
            return Ok("stale".to_owned());
        }
        return Ok("complete".to_owned());
    }
    if status == "stall" {
        return Ok("stall".to_owned());
    }
    Ok("stale".to_owned())
}

fn step5_resume_result_env_state(tmpdir: &Path) -> Result<String, String> {
    let path = result_env_path(tmpdir, STEP5_RESUME_STEP).map_err(|e| e.to_string())?;
    let Some(rows) = read_result_rows(&path, tmpdir)? else {
        return Ok("absent".to_owned());
    };
    let status = rows.get("STEP5_REVIEW_STATUS").cloned().unwrap_or_default();
    if rows.get("STEP").map(String::as_str) == Some(STEP5_RESUME_STEP)
        && rows.get(BGJOB_RC_KEY).map(String::as_str) == Some("0")
        && (status == "complete" || status == "stall")
    {
        if !step5_result_identity_ok(tmpdir, &rows) {
            return Ok("stale".to_owned());
        }
        return Ok("complete".to_owned());
    }
    Ok("stale".to_owned())
}

fn prepare_step5_result(tmpdir: &Path, step: &str, state: &str) -> Result<(), String> {
    if state == "complete" {
        return Ok(());
    }
    let result = result_env_path(tmpdir, step).map_err(|e| e.to_string())?;
    if result.exists() || result.is_symlink() {
        unlink_safe(&result, tmpdir)?;
    }
    Ok(())
}

fn step5_result_identity_ok(tmpdir: &Path, rows: &HashMap<String, String>) -> bool {
    let Ok(live) = checks_launch_identity(tmpdir) else {
        return false;
    };
    rows.get(CHECKS_HEAD).map(String::as_str) == Some(live.head_sha.as_str())
        && rows.get(CHECKS_FP).map(String::as_str) == Some(live.tree_fp.as_str())
        && rows.get(CHECKS_SCHEMA).map(String::as_str) == Some(live.schema.as_str())
}

fn publish_step5_child(tmpdir: &Path, merge_env_raw: &str, output: &str) -> bool {
    let mut merged = output.to_owned();
    if let Ok(identity) = checks_launch_identity(tmpdir) {
        let identity_rows = format_rows(&identity.as_rows());
        if !identity_rows.is_empty() {
            if !merged.is_empty() && !merged.ends_with('\n') {
                merged.push('\n');
            }
            merged.push_str(&identity_rows);
        }
    }
    publish_rows(tmpdir, Path::new(merge_env_raw), &merged).is_ok()
}

fn read_result_rows(path: &Path, tmpdir: &Path) -> Result<Option<HashMap<String, String>>, String> {
    if let Ok(meta) = fs::symlink_metadata(path)
        && (meta.file_type().is_symlink() || !meta.is_file())
    {
        return Err("unsafe result file".into());
    }
    let _ = larch_core::ensure_under(path, tmpdir, "result file").map_err(|e| e.to_string())?;
    if !path.exists() {
        return Ok(None);
    }
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    if text.contains('\r') {
        return Err("carriage return in result env".into());
    }
    let mut rows = HashMap::new();
    for line in text.lines() {
        if let Some((key, value)) = line.split_once('=')
            && !key.is_empty()
            && key
                .bytes()
                .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
            && !rows.contains_key(key)
        {
            rows.insert(key.to_owned(), value.to_owned());
        }
    }
    Ok(Some(rows))
}

// ---------------------------------------------------------------------------
// checks relay helpers
// ---------------------------------------------------------------------------

fn resolve_session_repo_root(tmpdir: &Path) -> Result<PathBuf, String> {
    let output = delegate_python([
        OsString::from("implement"),
        OsString::from("checks-result-identity"),
        OsString::from("resolve-repo-root"),
        OsString::from("--implement-tmpdir"),
        tmpdir.as_os_str().to_owned(),
    ])?;
    if !output.status().success() {
        let err = String::from_utf8_lossy(output.stderr());
        let message = if err.trim().is_empty() {
            String::from_utf8_lossy(output.stdout()).into_owned()
        } else {
            err.into_owned()
        };
        return Err(message.trim().to_owned());
    }
    let text = String::from_utf8_lossy(output.stdout()).into_owned();
    first_line_value(&text, "REPO_ROOT")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .ok_or_else(|| "checks-step5-resume: REPO_ROOT unavailable".to_owned())
}

fn run_relevant_checks_for_site(
    tmpdir: &Path,
    checks_site: &str,
    repo_root: &Path,
) -> (HashMap<String, String>, bool) {
    let output = larch_in(
        repo_root,
        &[
            OsString::from("checks"),
            OsString::from("run-relevant"),
            OsString::from("--site"),
            OsString::from(checks_site),
            OsString::from("--tmpdir"),
            tmpdir.as_os_str().to_owned(),
            OsString::from("--repo-root"),
            repo_root.as_os_str().to_owned(),
        ],
    );
    let (rc, stdout) = output.map_or_else(
        |_| (1, String::new()),
        |output| {
            (
                output.status().code().unwrap_or(1),
                String::from_utf8_lossy(output.stdout()).into_owned(),
            )
        },
    );
    let first_line = stdout.lines().next().unwrap_or_default();
    let mut captured = parse_whitespace_kv_line(first_line);
    if captured.is_empty() {
        captured.insert("STATUS".into(), "fail".into());
        captured.insert("FAILURE_REASON".into(), "checks-child-failed".into());
        captured.insert(
            "EXIT_CODE".into(),
            (if rc == 0 { 1 } else { rc }).to_string(),
        );
    } else if rc != 0 {
        captured.remove("RELEVANT_CHECKS_OK");
        captured.remove("RELEVANT_CHECKS_SKIPPED");
        captured
            .entry("STATUS".into())
            .or_insert_with(|| "fail".into());
        captured
            .entry("FAILURE_REASON".into())
            .or_insert_with(|| "checks-child-failed".into());
        captured
            .entry("EXIT_CODE".into())
            .or_insert_with(|| rc.to_string());
    }
    (captured, false)
}

fn checks_relay_line(captured: &HashMap<String, String>) -> String {
    let get = |key: &str| captured.get(key).cloned().unwrap_or_default();
    if get("RELEVANT_CHECKS_SKIPPED") == "true" {
        return format!("RELEVANT_CHECKS_SKIPPED=true SITE={}", get("SITE"));
    }
    if get("RELEVANT_CHECKS_OK") == "true" {
        let mut line = format!(
            "RELEVANT_CHECKS_OK=true SITE={} COVERAGE={} PHASE={}",
            get("SITE"),
            get("COVERAGE"),
            get("PHASE"),
        );
        if !get("WARN").is_empty() {
            line.push_str(" WARN=");
            line.push_str(&get("WARN"));
        }
        return line;
    }
    let mut parts = vec![
        "STATUS=fail".to_owned(),
        format!(
            "FAILURE_REASON={}",
            captured
                .get("FAILURE_REASON")
                .cloned()
                .unwrap_or_else(|| "checks-failed".to_owned())
        ),
    ];
    for key in ["EXIT_CODE", "PHASE", "DIGEST_FILE", "REDACTED_LOG_FILE"] {
        if let Some(value) = captured.get(key).filter(|value| !value.is_empty()) {
            parts.push(format!("{key}={value}"));
        }
    }
    parts.join(" ")
}

fn checks_pass(captured: &HashMap<String, String>) -> bool {
    if captured.get("STATUS").map(String::as_str) == Some("fail") {
        return false;
    }
    captured.get("RELEVANT_CHECKS_OK").map(String::as_str) == Some("true")
        || captured.get("RELEVANT_CHECKS_SKIPPED").map(String::as_str) == Some("true")
}

fn parse_whitespace_kv_line(line: &str) -> HashMap<String, String> {
    let mut rows = HashMap::new();
    for token in line.split_whitespace() {
        if let Some((key, value)) = token.split_once('=')
            && !key.is_empty()
            && key
                .bytes()
                .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
            && !rows.contains_key(key)
        {
            rows.insert(key.to_owned(), value.to_owned());
        }
    }
    rows
}

// ---------------------------------------------------------------------------
// step-5 handoff timing
// ---------------------------------------------------------------------------

fn record_step5_handoff_timing(tmpdir: &Path, final_round_num: &str) {
    let _ = larch_env(
        &[
            OsString::from("timing"),
            OsString::from("mark"),
            OsString::from("Step 5: review handoff"),
        ],
        &[
            (
                ChildEnvironment::LarchTimingSkill,
                OsString::from("implement"),
            ),
            (
                ChildEnvironment::ImplementTmpdir,
                tmpdir.as_os_str().to_owned(),
            ),
            (ChildEnvironment::DesignTmpdir, OsString::new()),
        ],
    );
    let round_start_file = tmpdir
        .join(format!("round-{final_round_num}"))
        .join("round-start-s");
    if !round_start_file.is_file() {
        return;
    }
    let start_s = fs::read_to_string(&round_start_file)
        .unwrap_or_default()
        .trim()
        .to_owned();
    if !is_digits(&start_s) {
        return;
    }
    let ledger = tmpdir.join("timing-ledger.tsv");
    let round_num: u64 = match final_round_num.parse() {
        Ok(value) => value,
        Err(_) => return,
    };
    let round_decimal = round_num.to_string();
    if ledger.is_file()
        && let Ok(text) = fs::read_to_string(&ledger)
    {
        for line in text.lines() {
            let cols: Vec<&str> = line.split('\t').collect();
            if cols.len() >= 7
                && cols[1] == "round"
                && cols[3] == "implement"
                && cols[4] == "Step 5 — code review"
                && cols[5] == round_decimal
                && cols[6] == start_s
            {
                return;
            }
        }
    }
    let round_dir = tmpdir.join(format!("round-{final_round_num}"));
    let (accepted, rejected) = step5_round_timing_counts(&round_dir);
    let end_s = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
        .to_string();
    let _ = larch_env(
        &[
            OsString::from("timing"),
            OsString::from("record-round"),
            OsString::from("--skill"),
            OsString::from("implement"),
            OsString::from("--step"),
            OsString::from("Step 5 — code review"),
            OsString::from("--round"),
            OsString::from(&round_decimal),
            OsString::from("--start-s"),
            OsString::from(&start_s),
            OsString::from("--end-s"),
            OsString::from(&end_s),
            OsString::from("--accepted"),
            OsString::from(accepted.to_string()),
            OsString::from("--rejected"),
            OsString::from(rejected.to_string()),
        ],
        &[
            (
                ChildEnvironment::LarchTimingSkill,
                OsString::from("implement"),
            ),
            (
                ChildEnvironment::ImplementTmpdir,
                tmpdir.as_os_str().to_owned(),
            ),
        ],
    );
}

fn step5_round_timing_counts(round_dir: &Path) -> (u64, u64) {
    let tally = round_dir.join("review-tally.env");
    let accepted_raw = {
        let value = read_kv_file(&tally, "ACCEPTED_COUNT");
        if value.is_empty() {
            read_kv_file(&tally, "ACCEPTED")
        } else {
            value
        }
    };
    let rejected_raw = {
        let value = read_kv_file(&tally, "REJECTED_COUNT");
        if value.is_empty() {
            read_kv_file(&tally, "REJECTED")
        } else {
            value
        }
    };
    let accepted = if is_digits(&accepted_raw) {
        accepted_raw.parse().unwrap_or(0)
    } else {
        count_finding_headings(&round_dir.join("accepted-findings.md"))
    };
    if is_digits(&rejected_raw) {
        return (accepted, rejected_raw.parse().unwrap_or(0));
    }
    let rejected_text =
        fs::read_to_string(round_dir.join("rejected-findings.md")).unwrap_or_default();
    let mut rejected = count_matches(
        &rejected_text,
        &regex::Regex::new(r"(?m)^###\s+\[(?:rejected|Code Review)\]\s+").unwrap(),
    );
    if rejected == 0 {
        rejected = count_matches(
            &rejected_text,
            &regex::Regex::new(
                r"(?m)^(?:[0-9]+:FINDING_[A-Za-z0-9_]+_OUTCOME=rejected|\[[^\]]+\]|- )",
            )
            .unwrap(),
        );
    }
    if rejected == 0 && !rejected_text.is_empty() {
        rejected = 1;
    }
    (accepted, rejected)
}

fn count_finding_headings(path: &Path) -> u64 {
    let text = fs::read_to_string(path).unwrap_or_default();
    count_matches(&text, &regex::Regex::new(r"(?m)^###\s+").unwrap())
}

fn count_matches(text: &str, pattern: &regex::Regex) -> u64 {
    pattern.find_iter(text).count() as u64
}

// ---------------------------------------------------------------------------
// bgjob adapter
// ---------------------------------------------------------------------------

struct AdapterSpec {
    tmpdir: PathBuf,
    step: &'static str,
    budget_s: u32,
    verb: &'static str,
    public_args: Vec<OsString>,
    merge_env: PathBuf,
    initial_merge_rows: Vec<(String, String)>,
    repo_root: Option<PathBuf>,
}

fn run_adapter(spec: &AdapterSpec) -> Result<ExitCode, String> {
    let root = resolve_plugin_root()?;
    let entry = root.join("scripts").join("larch.sh");
    let clone = env::current_dir().map_err(|e| e.to_string())?;
    let run_id = resolve_run_id("", &spec.tmpdir, &clone);
    let (log_dir, _, _) = log_paths(&spec.tmpdir, None, spec.step).map_err(|e| e.to_string())?;
    let owner_pid = owner_pid_string();
    let mut argv: Vec<OsString> = vec![
        "bgjob".into(),
        "adapt".into(),
        "--step".into(),
        spec.step.into(),
        "--tmpdir".into(),
        spec.tmpdir.as_os_str().into(),
        "--run-id".into(),
        run_id.into(),
        "--budget-s".into(),
        spec.budget_s.to_string().into(),
        "--log-dir".into(),
        log_dir.into(),
    ];
    if !owner_pid.is_empty() {
        argv.extend(["--owner-pid".into(), owner_pid.into()]);
    }
    argv.extend([
        "--merge-result-env".into(),
        spec.merge_env.as_os_str().into(),
    ]);
    for (key, value) in &spec.initial_merge_rows {
        argv.extend([
            "--initial-merge-row".into(),
            format!("{key}={value}").into(),
        ]);
    }
    argv.extend([
        "--".into(),
        entry.into_os_string(),
        "implement".into(),
        spec.verb.into(),
    ]);
    argv.extend(spec.public_args.iter().cloned());
    let cwd = spec.repo_root.clone().unwrap_or(clone);
    let output = delegate_verified_larch(&cwd, &root, &argv)?;
    let _ = std::io::stdout().write_all(output.stdout());
    let _ = std::io::stdout().flush();
    if !output.stderr().is_empty() {
        let _ = std::io::stderr().write_all(output.stderr());
    }
    Ok(exit_code(output.status().code().unwrap_or(1)))
}

fn run_parent_flow(build: impl FnOnce() -> Result<ExitCode, String>) -> ExitCode {
    build().unwrap_or_else(|_| {
        println!("BGJOB_ERROR=invalid-input");
        ExitCode::from(2)
    })
}

// ---------------------------------------------------------------------------
// shared helpers
// ---------------------------------------------------------------------------

fn larch(args: &[OsString]) -> Result<ProcessOutput, String> {
    let root = resolve_plugin_root()?;
    let cwd = env::current_dir().map_err(|e| e.to_string())?;
    delegate_verified_larch(&cwd, &root, args)
}

fn larch_in(cwd: &Path, args: &[OsString]) -> Result<ProcessOutput, String> {
    let root = resolve_plugin_root()?;
    delegate_verified_larch(cwd, &root, args)
}

fn larch_env(
    args: &[OsString],
    extra: &[(ChildEnvironment, OsString)],
) -> Result<ProcessOutput, String> {
    let root = resolve_plugin_root()?;
    let cwd = env::current_dir().map_err(|e| e.to_string())?;
    let program = LarchProgram::bootstrap(&root)
        .map_err(|error| format!("could not select verified larch entrypoint: {error}"))?;
    let mut request = bounded_request_in(
        ExternalProgram::Larch(program),
        args.iter().cloned(),
        &cwd,
        ADAPT_TIMEOUT,
        ADAPT_GRACE,
        ADAPT_OUTPUT_LIMIT,
    )?;
    request = request.with_environment(
        ChildEnvironment::ClaudePluginRoot,
        root.as_os_str().to_owned(),
    );
    request = request.with_environment(
        ChildEnvironment::ImplementTmpdir,
        env::var_os("IMPLEMENT_TMPDIR").unwrap_or_default(),
    );
    request = request.with_environment(ChildEnvironment::RepoRoot, cwd.as_os_str().to_owned());
    for (key, value) in extra {
        request = request.with_environment(*key, value.clone());
    }
    run_bounded(request).map_err(|error| format!("could not start verified larch: {error}"))
}

/// Mirror the Python `_forward_result` capture: return the child's exit code and
/// stdout while streaming its stderr to the real stderr.
fn forward_worker(result: Result<ProcessOutput, String>) -> (i32, String) {
    match result {
        Ok(output) => {
            if !output.stderr().is_empty() {
                let _ = std::io::stderr().write_all(output.stderr());
            }
            (
                output.status().code().unwrap_or(1),
                String::from_utf8_lossy(output.stdout()).into_owned(),
            )
        }
        Err(message) => {
            eprintln!("{message}");
            (1, String::new())
        }
    }
}

fn parse_line_anchored(stdout: &str, key: &str) -> Vec<String> {
    let prefix = format!("{key}=");
    stdout
        .lines()
        .filter_map(|line| line.strip_prefix(&prefix).map(str::to_owned))
        .collect()
}

fn relay_commit_kvs(commit_output: &str, include_next_action: bool) -> String {
    let mut out = String::new();
    for line in commit_output.lines() {
        let Some((key, _)) = line.split_once('=') else {
            continue;
        };
        if key.is_empty() {
            continue;
        }
        if !STEP5_RESUME_COMMIT_RELAY_KEYS.contains(&key) {
            continue;
        }
        if !include_next_action && key == "NEXT_ACTION" {
            continue;
        }
        out.push_str(line);
        out.push('\n');
    }
    out
}

fn emit_line(line: &str, rows: &mut Vec<(String, String)>) {
    record_result_line(line, rows);
    println!("{line}");
}

fn emit_kv(key: &str, value: &str, rows: &mut Vec<(String, String)>) {
    let line = format!("{key}={value}");
    record_result_line(&line, rows);
    println!("{line}");
}

fn record_result_line(line: &str, rows: &mut Vec<(String, String)>) {
    if line.contains('\n') || line.contains('\r') {
        return;
    }
    let Some((key, value)) = line.split_once('=') else {
        return;
    };
    if !key.is_empty()
        && key
            .bytes()
            .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
    {
        rows.push((key.to_owned(), value.to_owned()));
    }
}

fn flush_result_env(merge_env: Option<&Path>, rows: &[(String, String)]) {
    let Some(path) = merge_env else {
        return;
    };
    let mut body = String::new();
    for (key, value) in rows {
        body.push_str(key);
        body.push('=');
        body.push_str(value);
        body.push('\n');
    }
    let _ = write_bytes_atomic(path, body.as_bytes());
}

fn resolve_dynamic_cap(tmpdir: &Path) -> String {
    let value = read_kv_file(
        &tmpdir.join("session-env.sh"),
        "LARCH_DYNAMIC_ARCHETYPES_MAX",
    );
    if !value.is_empty() {
        return value;
    }
    match env::var("LARCH_DYNAMIC_ARCHETYPES_MAX") {
        Ok(value) if !value.is_empty() => value,
        _ => "1".to_owned(),
    }
}

fn difficulty_override(tmpdir: &Path) -> String {
    let value = read_kv_file(&tmpdir.join("run-flags.sh"), "DIFFICULTY_OVERRIDE");
    if value == "TRIVIAL" || value == "MODERATE" || value == "HARD" {
        value
    } else {
        String::new()
    }
}

fn read_kv_file(path: &Path, key: &str) -> String {
    read_kv_file_impl(path, key, false)
}

fn read_kv_file_last(path: &Path, key: &str) -> String {
    read_kv_file_impl(path, key, true)
}

fn read_kv_file_impl(path: &Path, key: &str, last: bool) -> String {
    let Ok(text) = fs::read_to_string(path) else {
        return String::new();
    };
    let mut found = String::new();
    let prefix = format!("{key}=");
    for line in text.lines() {
        let line = line.trim_start_matches("export ").trim_start();
        if let Some(rest) = line.strip_prefix(&prefix) {
            let value = rest.trim().trim_matches(['\'', '"']).to_owned();
            if !last {
                return value;
            }
            found = value;
        }
    }
    found
}

fn first_line_value(text: &str, key: &str) -> Option<String> {
    let prefix = format!("{key}=");
    text.lines()
        .find_map(|line| line.strip_prefix(&prefix).map(str::to_owned))
}

fn has_symlink_ancestor(path: &Path) -> bool {
    if path.is_symlink() {
        return true;
    }
    path.ancestors().skip(1).any(Path::is_symlink)
}

fn tmpdir_from_env() -> Result<PathBuf, ()> {
    let raw = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    if raw.is_empty() {
        eprintln!("IMPLEMENT_TMPDIR required");
        return Err(());
    }
    Ok(PathBuf::from(raw))
}

fn rehydrate(tmpdir: &Path) {
    let mut rows = Vec::new();
    if env::var_os("CLAUDE_PLUGIN_ROOT").is_none()
        && let Some(root) = session_value(tmpdir, "plugin-root.env", "CLAUDE_PLUGIN_ROOT")
            .or_else(|| session_value(tmpdir, "session-env.sh", "LARCH_CLAUDE_PLUGIN_ROOT"))
    {
        rows.push((ChildEnvironment::ClaudePluginRoot, OsString::from(root)));
    }
    for (env_key, child_key) in [
        (
            "LARCH_TOKEN_SESSION_ID",
            ChildEnvironment::LarchTokenSessionId,
        ),
        (
            "LARCH_CLAUDE_SOURCE_FILE",
            ChildEnvironment::LarchClaudeSourceFile,
        ),
        ("LARCH_TIMING_LEDGER", ChildEnvironment::LarchTimingLedger),
    ] {
        if env::var_os(env_key).is_none()
            && let Some(value) = session_value(tmpdir, "session-env.sh", env_key)
        {
            rows.push((child_key, OsString::from(value)));
        }
    }
    rows.push((ChildEnvironment::ImplementTmpdir, tmpdir.as_os_str().into()));
    publish_session_environment(rows);
}

fn session_value(tmpdir: &Path, file: &str, key: &str) -> Option<String> {
    let value = read_kv_file(&tmpdir.join(file), key);
    if value.is_empty() { None } else { Some(value) }
}

fn is_digits(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|b| b.is_ascii_digit())
}

fn default_false(value: Option<&OsStr>) -> String {
    let raw = opt_string(value);
    if raw.is_empty() {
        "false".to_owned()
    } else {
        raw
    }
}

fn exit_code(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}
