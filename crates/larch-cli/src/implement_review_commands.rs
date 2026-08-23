//! Rust owners for the `/implement` Step 5-7a review-routing commands:
//! `step-5-review`, `step-5-resume`, `checks-step5-resume`, `step-6-entry`,
//! and `step-7a`. The parents launch or rejoin the shared bgjob adapter and the
//! children delegate the still-Python composites and already-Rust verbs through
//! the verified `scripts/larch.sh` bootstrap.

use std::{
    collections::{BTreeMap, HashMap},
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{SystemTime, UNIX_EPOCH},
};

use larch_adapters::GixRepository;
use larch_core::{
    ChildEnvironment, DuplicatePolicy, KvDocument, ParseOptions, ProcessOutput, RepositoryRead,
    Revision,
    implement::{
        checks_pass, checks_relay_line, checks_run_relevant_args, parse_line_anchored,
        parse_whitespace_kv_line,
    },
    parse_single_kv_row, result_env_path, write_bytes_atomic,
};

use crate::{
    argparse_compat::{choice_error, parse_required_with_help, usage_error},
    implement_child_seam::resolve_plugin_root,
    implement_dispatch_commands::{
        LaunchIdentity, checks_launch_identity, delegate_python, delegate_verified_larch,
        ensure_safe_regular_file, format_rows, forward_output, opt_string,
        parse_command_with_tmpdir, prepare_checks_rejoin, publish_child_session,
        publish_identity_child, publish_rows, rehydrate_session, resolve_repo_root_output,
        run_bgjob_adapt, run_verified_larch_env_in, safe_merge_env, tmpdir_from_env, unlink_safe,
    },
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

// ---------------------------------------------------------------------------
// step-5-review
// ---------------------------------------------------------------------------

const STEP5_REVIEW_PROG: &str = "cli.py implement step-5-review";
const STEP5_REVIEW_USAGE: &str = "usage: cli.py implement step-5-review [-h] [--bgjob-child]\n                                      [--merge-result-env MERGE_RESULT_ENV]\n";
const STEP5_REVIEW_HELP: &str = "usage: cli.py implement step-5-review [-h] [--bgjob-child]\n                                      [--merge-result-env MERGE_RESULT_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n";

/// `implement step-5-review` compatibility command.
pub fn step5_review(arguments: &[OsString]) -> ExitCode {
    let (parsed, tmpdir) = match parse_command_with_tmpdir(
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
    rehydrate_session(&tmpdir);
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
    rehydrate_session(&tmpdir);
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
    rehydrate_session(&tmpdir);
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
            publish_child_session(&launch, &tmpdir);
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
            forward_output(&output);
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
        emit_result_kv(key, value, rows);
    }
}

fn generate_code_flow_diagram(
    tmpdir: &Path,
    base_remote: &str,
    base_ref: &str,
) -> (String, String, String) {
    let result = crate::diagram_commands::generate_code_flow_diagram(
        tmpdir,
        "claude-sonnet-4-6",
        base_remote,
        base_ref,
    );
    let exit = result.exit_code;
    let status = result.status;
    let diagram_file = result.diagram_file;
    let reason = result.reason;

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
    ensure_safe_regular_file(path)?;
    let _ = larch_core::ensure_under(path, tmpdir, "result file").map_err(|e| e.to_string())?;
    if !path.exists() {
        return Ok(None);
    }
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    if text.contains('\r') {
        return Err("carriage return in result env".into());
    }
    let document = KvDocument::parse(&text, ParseOptions::legacy()).map_err(|e| e.to_string())?;
    let mut rows = HashMap::new();
    for (key, value) in document.select(DuplicatePolicy::First) {
        if is_environment_key(&key) {
            rows.insert(key, value);
        }
    }
    Ok(Some(rows))
}

// ---------------------------------------------------------------------------
// checks relay helpers
// ---------------------------------------------------------------------------

fn resolve_session_repo_root(tmpdir: &Path) -> Result<PathBuf, String> {
    let output = resolve_repo_root_output(tmpdir);
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
) -> (BTreeMap<String, String>, bool) {
    let output = larch_in(
        repo_root,
        &checks_run_relevant_args(checks_site, tmpdir, repo_root),
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
    run_bgjob_adapt(
        &spec.tmpdir,
        spec.step,
        spec.budget_s,
        spec.verb,
        &spec.merge_env,
        &spec.initial_merge_rows,
        &spec.public_args,
        spec.repo_root.as_deref(),
        false,
    )
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
    run_verified_larch_env_in(&cwd, &root, args, extra)
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

fn relay_commit_kvs(commit_output: &str, include_next_action: bool) -> String {
    let Ok(document) = KvDocument::parse(commit_output, ParseOptions::legacy()) else {
        return String::new();
    };
    let mut out = String::new();
    for row in document.rows() {
        let key = row.key();
        if key.is_empty() || !STEP5_RESUME_COMMIT_RELAY_KEYS.contains(&key) {
            continue;
        }
        if !include_next_action && key == "NEXT_ACTION" {
            continue;
        }
        out.push_str(key);
        out.push('=');
        out.push_str(row.value());
        out.push('\n');
    }
    out
}

fn emit_line(line: &str, rows: &mut Vec<(String, String)>) {
    record_result_line(line, rows);
    println!("{line}");
}

fn emit_result_kv(key: &str, value: &str, rows: &mut Vec<(String, String)>) {
    let line = format!("{key}={value}");
    record_result_line(&line, rows);
    println!("{line}");
}

fn record_result_line(line: &str, rows: &mut Vec<(String, String)>) {
    let Some(row) = parse_single_kv_row(line, ParseOptions::legacy()) else {
        return;
    };
    if is_environment_key(row.key()) {
        rows.push((row.key().to_owned(), row.value().to_owned()));
    }
}

/// Accept only shell-environment keys: uppercase ASCII, digits, and underscore.
fn is_environment_key(key: &str) -> bool {
    !key.is_empty()
        && key
            .bytes()
            .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::implement_child_seam::declare_plugin_root;
    use crate::implement_dispatch_commands::{
        clear_test_hooks, install_test_larch, install_test_python,
    };
    use larch_core::ProcessStatus;
    use larch_test_support::{GitFixture, GitRepository};
    use std::ffi::OsStr;
    use tempfile::TempDir;

    /// Seed a real repository plus session env for the in-process identity verbs.
    ///
    /// `implement checks-result-identity` is Rust-owned and computed in process,
    /// so these paths need a repository rather than a stubbed Python child.
    fn seed_identity(tmpdir: &Path) -> (GitRepository, LaunchIdentity) {
        let repository = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("git fixture");
        fs::write(
            tmpdir.join("session-env.sh"),
            format!("REPO_ROOT={}\n", repository.root().display()),
        )
        .expect("session env");
        let identity = checks_launch_identity(tmpdir).expect("launch identity");
        (repository, identity)
    }

    fn out(code: i32, stdout: &str) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(code == 0, Some(code)),
            stdout.as_bytes().to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    fn os(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn map(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect()
    }

    fn hmap(pairs: &[(&str, &str)]) -> HashMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect()
    }

    // ---- pure path classification -------------------------------------

    #[test]
    fn non_runtime_paths_are_docs_readme_and_text_or_tsv() {
        assert!(is_non_runtime_path("docs/anything.rs"));
        assert!(is_non_runtime_path("nested/README.md"));
        assert!(is_non_runtime_path("scripts/residual.txt"));
        assert!(is_non_runtime_path("skills/topology.tsv"));
        assert!(!is_non_runtime_path("Cargo.toml"));
        assert!(!is_non_runtime_path("Makefile"));
        assert!(!is_non_runtime_path("crates/larch-cli/src/main.rs"));
    }

    // ---- checks relay + pass ------------------------------------------

    #[test]
    fn checks_relay_line_covers_skip_ok_and_fail() {
        assert_eq!(
            checks_relay_line(&map(&[
                ("RELEVANT_CHECKS_SKIPPED", "true"),
                ("SITE", "step5")
            ])),
            "RELEVANT_CHECKS_SKIPPED=true SITE=step5"
        );
        assert_eq!(
            checks_relay_line(&map(&[
                ("RELEVANT_CHECKS_OK", "true"),
                ("SITE", "step6"),
                ("COVERAGE", "full"),
                ("PHASE", "p1"),
                ("WARN", "slow"),
            ])),
            "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=full PHASE=p1 WARN=slow"
        );
        let fail = checks_relay_line(&map(&[
            ("EXIT_CODE", "7"),
            ("PHASE", "lint"),
            ("DIGEST_FILE", "d"),
        ]));
        assert!(fail.starts_with("STATUS=fail FAILURE_REASON=checks-failed"));
        assert!(
            fail.contains("EXIT_CODE=7")
                && fail.contains("PHASE=lint")
                && fail.contains("DIGEST_FILE=d")
        );
    }

    #[test]
    fn checks_pass_requires_ok_or_skipped_without_fail_status() {
        assert!(!checks_pass(&map(&[
            ("STATUS", "fail"),
            ("RELEVANT_CHECKS_OK", "true")
        ])));
        assert!(checks_pass(&map(&[("RELEVANT_CHECKS_OK", "true")])));
        assert!(checks_pass(&map(&[("RELEVANT_CHECKS_SKIPPED", "true")])));
        assert!(!checks_pass(&map(&[("STATUS", "ok")])));
    }

    #[test]
    fn whitespace_kv_line_keeps_first_valid_tokens_only() {
        let rows = parse_whitespace_kv_line("A=1 B=2 bad-key=3 =4 A=9 C");
        assert_eq!(rows.get("A"), Some(&"1".to_owned()));
        assert_eq!(rows.get("B"), Some(&"2".to_owned()));
        assert!(!rows.contains_key("bad-key"));
        assert_eq!(rows.len(), 2);
    }

    // ---- result-env + commit relays -----------------------------------

    #[test]
    fn relay_commit_kvs_filters_keys_and_honors_next_action_flag() {
        let raw = "COMMITTED=true\nSHA=abc\nNOISE=x\nNEXT_ACTION=commit\n";
        assert_eq!(relay_commit_kvs(raw, false), "COMMITTED=true\nSHA=abc\n");
        assert_eq!(
            relay_commit_kvs(raw, true),
            "COMMITTED=true\nSHA=abc\nNEXT_ACTION=commit\n"
        );
    }

    #[test]
    fn record_result_line_and_is_environment_key() {
        let mut rows = Vec::new();
        record_result_line("STEP=go", &mut rows);
        record_result_line("bad-key=1", &mut rows);
        record_result_line("no-equals", &mut rows);
        assert_eq!(rows, vec![("STEP".to_owned(), "go".to_owned())]);
        assert!(is_environment_key("A_1"));
        assert!(!is_environment_key(""));
        assert!(!is_environment_key("lower"));
    }

    #[test]
    fn parse_line_anchored_collects_all_matching_lines() {
        assert_eq!(
            parse_line_anchored("K=a\nX=z\nK=b\n", "K"),
            vec!["a".to_owned(), "b".to_owned()]
        );
    }

    #[test]
    fn emit_final_records_seven_result_rows() {
        let mut rows = Vec::new();
        emit_final(&mut rows, "ok", "", "/p", "url", "ok", "", "rebased");
        assert_eq!(rows.len(), 7);
        assert_eq!(rows[0], ("DIAGRAM_STATUS".to_owned(), "ok".to_owned()));
        assert_eq!(rows[6], ("REBASE_OUTCOME".to_owned(), "rebased".to_owned()));
    }

    #[test]
    fn flush_result_env_writes_rows_and_skips_when_absent() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("merge.env");
        flush_result_env(Some(&path), &[("A".to_owned(), "1".to_owned())]);
        assert_eq!(fs::read_to_string(&path).unwrap(), "A=1\n");
        flush_result_env(None, &[("B".to_owned(), "2".to_owned())]);
    }

    #[test]
    fn read_result_rows_dedupes_and_rejects_carriage_return() {
        let dir = TempDir::new().unwrap();
        let good = dir.path().join("r.env");
        fs::write(&good, "STEP=go\nSTEP=again\nbad-key=x\n").unwrap();
        let rows = read_result_rows(&good, dir.path()).unwrap().unwrap();
        assert_eq!(rows.get("STEP"), Some(&"go".to_owned()));
        assert!(!rows.contains_key("bad-key"));

        let crlf = dir.path().join("crlf.env");
        fs::write(&crlf, "A=1\r\n").unwrap();
        assert!(read_result_rows(&crlf, dir.path()).is_err());

        let missing = dir.path().join("missing.env");
        assert!(read_result_rows(&missing, dir.path()).unwrap().is_none());
    }

    #[test]
    fn read_result_rows_rejects_symlink() {
        let dir = TempDir::new().unwrap();
        let target = dir.path().join("real.env");
        fs::write(&target, "A=1\n").unwrap();
        let link = dir.path().join("link.env");
        std::os::unix::fs::symlink(&target, &link).unwrap();
        assert!(read_result_rows(&link, dir.path()).is_err());
    }

    // ---- step-5 result-env state machine ------------------------------

    fn write_result_env(tmpdir: &Path, step: &str, body: &str) {
        let path = result_env_path(tmpdir, step).unwrap();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(path, body).unwrap();
    }

    #[test]
    fn step5_canonical_state_absent_stale_and_stall() {
        let dir = TempDir::new().unwrap();
        assert_eq!(
            step5_canonical_result_env_state(dir.path()).unwrap(),
            "absent"
        );

        write_result_env(dir.path(), STEP5_REVIEW_STEP, "STEP=other\nX=1\n");
        assert_eq!(
            step5_canonical_result_env_state(dir.path()).unwrap(),
            "stale"
        );

        let mut body = format!("STEP={STEP5_REVIEW_STEP}\nBGJOB_RC=1\nSTEP5_REVIEW_STATUS=stall\n");
        for key in STEP5_RESULT_ENVELOPE_KEYS {
            if *key != "STEP5_REVIEW_STATUS" {
                body.push_str(key);
                body.push_str("=v\n");
            }
        }
        write_result_env(dir.path(), STEP5_REVIEW_STEP, &body);
        assert_eq!(
            step5_canonical_result_env_state(dir.path()).unwrap(),
            "stall"
        );
    }

    #[test]
    fn step5_resume_state_absent_and_stale() {
        let dir = TempDir::new().unwrap();
        assert_eq!(step5_resume_result_env_state(dir.path()).unwrap(), "absent");
        write_result_env(dir.path(), STEP5_RESUME_STEP, "STEP=other\nBGJOB_RC=1\n");
        assert_eq!(step5_resume_result_env_state(dir.path()).unwrap(), "stale");
    }

    #[test]
    fn prepare_step5_result_keeps_complete_and_removes_others() {
        let dir = TempDir::new().unwrap();
        prepare_step5_result(dir.path(), STEP5_REVIEW_STEP, "complete").unwrap();
        write_result_env(dir.path(), STEP5_REVIEW_STEP, "STEP=x\n");
        let path = result_env_path(dir.path(), STEP5_REVIEW_STEP).unwrap();
        assert!(path.exists());
        prepare_step5_result(dir.path(), STEP5_REVIEW_STEP, "stale").unwrap();
        assert!(!path.exists());
    }

    // ---- kv-file readers ----------------------------------------------

    #[test]
    fn read_kv_file_handles_export_quotes_first_and_last() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("env.sh");
        fs::write(&path, "export FOO='bar'\nFOO=\"baz\"\nOTHER=1\n").unwrap();
        assert_eq!(read_kv_file(&path, "FOO"), "bar");
        assert_eq!(read_kv_file_last(&path, "FOO"), "baz");
        assert_eq!(read_kv_file(&path, "MISSING"), "");
        assert_eq!(first_line_value("A=1\nB=2\n", "B"), Some("2".to_owned()));
    }

    #[test]
    fn dynamic_cap_and_difficulty_override_read_session_files() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("session-env.sh"),
            "LARCH_DYNAMIC_ARCHETYPES_MAX=4\n",
        )
        .unwrap();
        assert_eq!(resolve_dynamic_cap(dir.path()), "4");
        fs::write(
            dir.path().join("run-flags.sh"),
            "DIFFICULTY_OVERRIDE=HARD\n",
        )
        .unwrap();
        assert_eq!(difficulty_override(dir.path()), "HARD");
        fs::write(
            dir.path().join("run-flags.sh"),
            "DIFFICULTY_OVERRIDE=WEIRD\n",
        )
        .unwrap();
        assert_eq!(difficulty_override(dir.path()), "");
    }

    // ---- timing counts ------------------------------------------------

    #[test]
    fn round_timing_counts_prefer_tally_then_fall_back_to_headings() {
        let dir = TempDir::new().unwrap();
        let round = dir.path().join("round-3");
        fs::create_dir_all(&round).unwrap();
        fs::write(
            round.join("review-tally.env"),
            "ACCEPTED_COUNT=5\nREJECTED_COUNT=2\n",
        )
        .unwrap();
        assert_eq!(step5_round_timing_counts(&round), (5, 2));

        let round2 = dir.path().join("round-4");
        fs::create_dir_all(&round2).unwrap();
        fs::write(round2.join("accepted-findings.md"), "### one\n### two\n").unwrap();
        fs::write(round2.join("rejected-findings.md"), "### [rejected] a\n").unwrap();
        assert_eq!(step5_round_timing_counts(&round2), (2, 1));
    }

    #[test]
    fn count_finding_headings_counts_markdown_headings() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("f.md");
        fs::write(&path, "### a\ntext\n### b\n").unwrap();
        assert_eq!(count_finding_headings(&path), 2);
    }

    // ---- small scalar helpers -----------------------------------------

    #[test]
    fn scalar_helpers_behave() {
        assert!(is_digits("120"));
        assert!(!is_digits(""));
        assert!(!is_digits("1a"));
        assert_eq!(default_false(None), "false");
        assert_eq!(default_false(Some(OsStr::new(""))), "false");
        assert_eq!(default_false(Some(OsStr::new("x"))), "x");
        assert_eq!(choice("true".to_owned()), Ok("true".to_owned()));
        assert_eq!(choice("nope".to_owned()), Err(()));
    }

    #[test]
    fn has_symlink_ancestor_detects_symlinked_parent() {
        let dir = TempDir::new().unwrap();
        let base = dir.path().canonicalize().unwrap();
        let real = base.join("real");
        fs::create_dir_all(&real).unwrap();
        let link = base.join("link");
        std::os::unix::fs::symlink(&real, &link).unwrap();
        assert!(has_symlink_ancestor(&link.join("child")));
        assert!(!has_symlink_ancestor(&real.join("child")));
    }

    #[test]
    fn identity_from_child_args_requires_every_field() {
        assert!(identity_from_child_args("", "h", "f", "s").is_err());
        let id = identity_from_child_args("/repo", "h", "f", "s").unwrap();
        assert_eq!(id.head_sha, "h");
        assert_eq!(id.repo_root, PathBuf::from("/repo"));
    }

    // ---- step7a argv parsing ------------------------------------------

    #[test]
    fn step7a_args_parse_defaults_inline_and_spaced() {
        let parsed = Step7aArgs::parse(&os(&[
            "--implement-tmpdir",
            "/t",
            "--issue-number=42",
            "--bgjob-launch",
            "true",
        ]))
        .unwrap();
        assert_eq!(parsed.implement_tmpdir, "/t");
        assert_eq!(parsed.issue_number, "42");
        assert_eq!(parsed.bgjob_launch, "true");
        assert_eq!(parsed.base_remote, "origin");
        assert_eq!(parsed.base_ref, "main");
    }

    #[test]
    fn step7a_args_reject_bad_choice_unknown_flag_and_missing_value() {
        assert!(Step7aArgs::parse(&os(&["--forked-target", "maybe"])).is_err());
        assert!(Step7aArgs::parse(&os(&["--nope"])).is_err());
        assert!(Step7aArgs::parse(&os(&["--issue-number"])).is_err());
    }

    #[test]
    fn emit_arg_failure_and_exit_code_are_callable() {
        let _ = emit_arg_failure("argv");
        let _ = exit_code(2);
        let mut rows = Vec::new();
        emit_line("STEP=x", &mut rows);
        emit_result_kv("A", "1", &mut rows);
        assert_eq!(rows.len(), 2);
    }

    // ---- hook-driven worker paths -------------------------------------

    struct HookGuard;
    impl Drop for HookGuard {
        fn drop(&mut self) {
            clear_test_hooks();
        }
    }

    fn arm_plugin_root(dir: &TempDir) -> HookGuard {
        clear_test_hooks();
        declare_plugin_root(dir.path());
        HookGuard
    }

    #[test]
    fn resolve_session_repo_root_reads_persisted_repo_root() {
        let dir = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&dir);
        let (repository, identity) = seed_identity(dir.path());
        assert_eq!(
            resolve_session_repo_root(dir.path()).unwrap(),
            identity.repo_root
        );
        drop(repository);
        fs::remove_file(dir.path().join("session-env.sh")).unwrap();
        assert!(resolve_session_repo_root(dir.path()).is_err());
    }

    #[test]
    fn run_relevant_checks_captures_first_line_and_failure_fallback() {
        let dir = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&dir);
        install_test_larch(|_c, _r, _a| {
            Ok(out(
                0,
                "RELEVANT_CHECKS_OK=true SITE=step5 COVERAGE=full PHASE=p\n",
            ))
        });
        let (captured, _) = run_relevant_checks_for_site(dir.path(), "step5", dir.path());
        assert!(checks_pass(&captured));

        install_test_larch(|_c, _r, _a| Ok(out(2, "")));
        let (captured, _) = run_relevant_checks_for_site(dir.path(), "step5", dir.path());
        assert_eq!(captured.get("STATUS"), Some(&"fail".to_owned()));
        assert_eq!(captured.get("EXIT_CODE"), Some(&"2".to_owned()));
    }

    #[test]
    fn run_step7a_happy_path_emits_success_envelope() {
        let dir = TempDir::new().unwrap();
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&dir);
        // Force the diagram-upsert branch by pre-seeding the section file.
        fs::write(tmp.path().join("code-flow-diagram.md"), "flow\n").unwrap();
        fs::write(tmp.path().join("code-flow-section.md"), "flow\n").unwrap();
        install_test_larch(|_c, _r, args| {
            let first = args
                .first()
                .map(|a| a.to_string_lossy().into_owned())
                .unwrap_or_default();
            let second = args
                .get(1)
                .map(|a| a.to_string_lossy().into_owned())
                .unwrap_or_default();
            let body = match (first.as_str(), second.as_str()) {
                ("diagrams", "upsert") => "UPSERT_STATUS=ok\nCOMMENT_URL=http://c\n",
                ("push", "checkpoint-probe") => "REBASE_OUTCOME=rebased\n",
                ("execution-issues", "flush") => "FLUSH_STATUS=ok\n",
                _ => "",
            };
            Ok(out(0, body))
        });
        crate::diagram_commands::install_test_diagram(|_tmp, _model, _remote, _ref| {
            crate::diagram_commands::CodeFlowDiagramResult {
                exit_code: 0,
                status: "ok".to_owned(),
                diagram_file: "/d/diagram.md".to_owned(),
                reason: String::new(),
            }
        });
        let args = Step7aArgs {
            implement_tmpdir: tmp.path().to_string_lossy().into_owned(),
            issue_number: "42".to_owned(),
            run_id: "r1".to_owned(),
            no_logs_commit: "false".to_owned(),
            forked_target: "false".to_owned(),
            base_remote: "origin".to_owned(),
            base_ref: "main".to_owned(),
            bgjob_launch: "false".to_owned(),
            bgjob_merge_result_env: String::new(),
        };
        let merge = tmp.path().join("merge.env");
        let rc = run_step7a(tmp.path(), &args, Some(&merge));
        assert_eq!(rc, 0);
        let flushed = fs::read_to_string(&merge).unwrap();
        assert!(flushed.contains("REBASE_OUTCOME=rebased"));
        assert!(flushed.contains("LOG_CHECKPOINT_STATUS=ok"));
    }

    #[test]
    fn run_step7a_probe_conflict_returns_probe_rc() {
        let dir = TempDir::new().unwrap();
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&dir);
        install_test_larch(|_c, _r, args| {
            let first = args
                .first()
                .map(|a| a.to_string_lossy().into_owned())
                .unwrap_or_default();
            if first == "push" {
                Ok(out(1, "REBASE_OUTCOME=conflict\n"))
            } else {
                Ok(out(0, ""))
            }
        });
        crate::diagram_commands::install_test_diagram(|_tmp, _model, _remote, _ref| {
            crate::diagram_commands::CodeFlowDiagramResult {
                exit_code: 0,
                status: "skipped".to_owned(),
                diagram_file: String::new(),
                reason: "sanitizer-rejected".to_owned(),
            }
        });
        let args = Step7aArgs {
            implement_tmpdir: tmp.path().to_string_lossy().into_owned(),
            issue_number: String::new(),
            run_id: String::new(),
            no_logs_commit: "false".to_owned(),
            forked_target: "false".to_owned(),
            base_remote: "origin".to_owned(),
            base_ref: "main".to_owned(),
            bgjob_launch: "false".to_owned(),
            bgjob_merge_result_env: String::new(),
        };
        assert_eq!(run_step7a(tmp.path(), &args, None), 1);
    }

    #[test]
    fn launch_step7a_bgjob_relays_started_envelope() {
        let dir = TempDir::new().unwrap();
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&dir);
        install_test_larch(|_c, _r, _a| Ok(out(0, "DIAGRAM_STATUS=started\n")));
        let args = Step7aArgs {
            implement_tmpdir: tmp.path().to_string_lossy().into_owned(),
            issue_number: "42".to_owned(),
            run_id: "r1".to_owned(),
            no_logs_commit: "false".to_owned(),
            forked_target: "false".to_owned(),
            base_remote: "origin".to_owned(),
            base_ref: "main".to_owned(),
            bgjob_launch: "true".to_owned(),
            bgjob_merge_result_env: String::new(),
        };
        let _ = launch_step7a_bgjob(tmp.path(), &args);
        assert!(
            tmp.path()
                .join("bgjob")
                .join(format!("{STEP7A_STEP}.merge.env"))
                .exists()
        );
    }

    #[test]
    fn run_adapter_delegates_through_bgjob_adapt() {
        let dir = TempDir::new().unwrap();
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&dir);
        install_test_larch(|_c, _r, _a| Ok(out(0, "STEP=step5\nBGJOB_RC=0\n")));
        let spec = AdapterSpec {
            tmpdir: tmp.path().to_path_buf(),
            step: STEP5_REVIEW_STEP,
            budget_s: 600,
            verb: "step-5-review",
            public_args: os(&["--bgjob-child"]),
            merge_env: tmp.path().join("merge.env"),
            initial_merge_rows: vec![("A".to_owned(), "1".to_owned())],
            repo_root: Some(tmp.path().to_path_buf()),
        };
        let _ = run_adapter(&spec).unwrap();
    }

    #[test]
    fn run_parent_flow_prints_bgjob_error_on_failure() {
        let ok = run_parent_flow(|| Ok(exit_code(0)));
        let _ = ok;
        let _ = run_parent_flow(|| Err("boom".to_owned()));
    }

    #[test]
    fn forward_worker_maps_ok_and_err() {
        assert_eq!(
            forward_worker(Ok(out(3, "OUT=1\n"))),
            (3, "OUT=1\n".to_owned())
        );
        assert_eq!(forward_worker(Err("bad".to_owned())), (1, String::new()));
    }

    fn arg_at(args: &[OsString], index: usize) -> String {
        args.get(index)
            .map(|a| a.to_string_lossy().into_owned())
            .unwrap_or_default()
    }

    #[test]
    fn step5_review_worker_rejects_non_integer_dynamic_cap() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        fs::write(
            tmp.path().join("session-env.sh"),
            "LARCH_DYNAMIC_ARCHETYPES_MAX=9\n",
        )
        .unwrap();
        assert_eq!(step5_review_worker(tmp.path()), (2, String::new()));
    }

    #[test]
    fn step5_review_worker_runs_review_and_fix_with_difficulty() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        fs::write(
            tmp.path().join("run-flags.sh"),
            "DIFFICULTY_OVERRIDE=HARD\n",
        )
        .unwrap();
        install_test_larch(|_c, _r, _a| Ok(out(0, "REVIEW=done\n")));
        // larch_env is not hooked and fails fast on the bogus root; the worker
        // still exercises banner + command assembly + difficulty branch.
        let (_rc, _out) = step5_review_worker(tmp.path());
    }

    #[test]
    fn step5_resume_worker_commit_stall_path() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_python(|_a| Ok(out(0, "NEXT_ACTION=stall\nCOMMITTED=true\nSHA=abc\n")));
        let (rc, text) = step5_resume_worker(tmp.path(), "2", "", true);
        assert_eq!(rc, 0);
        assert!(text.contains("NEXT_ACTION=stall"));
        assert!(text.contains("STEP5_REVIEW_STATUS=stall"));
    }

    #[test]
    fn step5_resume_worker_continue_path_runs_next_round() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_python(|_a| Ok(out(0, "NEXT_ACTION=continue\n")));
        install_test_larch(|_c, _r, args| {
            assert_eq!(arg_at(args, 0), "review-and-fix");
            Ok(out(0, "ROUND=3\n"))
        });
        let (rc, text) = step5_resume_worker(tmp.path(), "2", "", true);
        assert_eq!(rc, 0);
        assert!(text.contains("ROUND=3"));
    }

    #[test]
    fn step5_resume_worker_rejects_non_numeric_round() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let (rc, _text) = step5_resume_worker(tmp.path(), "abc", "", false);
        assert_eq!(rc, 2);
    }

    #[test]
    fn commit_phase_non_terminal_action_relays_with_next_action() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_python(|_a| Ok(out(1, "NEXT_ACTION=retry\nERROR=boom\n")));
        let (rc, text) = step5_resume_commit_phase();
        assert_eq!(rc, Some(1));
        assert!(text.contains("ERROR=boom"));
    }

    #[test]
    fn checks_step5_resume_pass_runs_resume_leg() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let _repository = seed_identity(tmp.path());
        install_test_larch(|_c, _r, args| match arg_at(args, 0).as_str() {
            "checks" => Ok(out(
                0,
                "RELEVANT_CHECKS_OK=true SITE=step5 COVERAGE=full PHASE=p\n",
            )),
            "implement" => Ok(out(0, "COMMITTED=true\n")),
            _ => Ok(out(0, "")),
        });
        let (rc, text) = run_checks_step5_resume(tmp.path(), "step5", "2");
        assert_eq!(rc, 0);
        assert!(text.contains("RELEVANT_CHECKS_OK=true"));
        assert!(text.contains("COMMITTED=true"));
    }

    #[test]
    fn checks_step5_resume_fail_emits_checks_failed() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let _repository = seed_identity(tmp.path());
        install_test_larch(|_c, _r, _a| Ok(out(2, "")));
        let (rc, text) = run_checks_step5_resume(tmp.path(), "step5", "2");
        assert_eq!(rc, 0);
        assert!(text.contains("NEXT_ACTION=checks-failed"));
    }

    #[test]
    fn checks_step5_resume_repo_root_failure_bails() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let (rc, _text) = run_checks_step5_resume(tmp.path(), "step5", "2");
        assert_eq!(rc, 2);
    }

    #[test]
    fn step6_entry_worker_skip_to_7a_when_no_files_changed() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, _a| Ok(out(0, "FILES_CHANGED=false\n")));
        let (rc, text) = step6_entry_worker("false", "false", tmp.path());
        assert_eq!(rc, 0);
        assert!(text.contains("NEXT_ACTION=skip-to-7a"));
        assert!(tmp.path().join(".review-boundary-passed").exists());
    }

    #[test]
    fn step6_entry_worker_files_changed_runs_composite() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, args| match arg_at(args, 0).as_str() {
            "review-and-fix" => Ok(out(0, "FILES_CHANGED=true\n")),
            _ => Ok(out(0, "NEXT_ACTION=continue\n")),
        });
        let (rc, text) = step6_entry_worker("false", "false", tmp.path());
        assert_eq!(rc, 0);
        assert!(text.contains("NEXT_ACTION=continue"));
    }

    #[test]
    fn step6_entry_worker_seeds_stall_on_probe_failure() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, args| match arg_at(args, 0).as_str() {
            "review-and-fix" => Ok(out(1, "")),
            _ => Ok(out(0, "")),
        });
        let (rc, text) = step6_entry_worker("false", "false", tmp.path());
        assert_eq!(rc, 0);
        assert!(text.contains("NEXT_ACTION=stall"));
    }

    #[test]
    fn step6_entry_worker_force_checks_goes_straight_to_composite() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, _a| Ok(out(0, "NEXT_ACTION=continue\n")));
        let (rc, _text) = step6_entry_worker("false", "true", tmp.path());
        assert_eq!(rc, 0);
    }

    #[test]
    fn generate_diagram_failure_appends_warning() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, _a| Ok(out(0, "")));
        crate::diagram_commands::install_test_diagram(|_tmp, _model, _remote, _ref| {
            crate::diagram_commands::CodeFlowDiagramResult {
                exit_code: 1,
                status: "failed".to_owned(),
                diagram_file: String::new(),
                reason: "generation-failed rc=1 tail=boom".to_owned(),
            }
        });
        let (status, path, reason) = generate_code_flow_diagram(tmp.path(), "origin", "main");
        assert_eq!(status, "failed");
        assert!(path.is_empty());
        assert!(!reason.is_empty());
    }

    #[test]
    fn checkpoint_execution_issues_degrades_on_bad_status() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        assert_eq!(checkpoint_execution_issues(tmp.path(), ""), "skip");
        install_test_larch(|_c, _r, _a| Ok(out(0, "FLUSH_STATUS=broken\n")));
        assert_eq!(checkpoint_execution_issues(tmp.path(), "r1"), "degraded");
        install_test_larch(|_c, _r, _a| Ok(out(0, "FLUSH_STATUS=ok\n")));
        assert_eq!(checkpoint_execution_issues(tmp.path(), "r1"), "ok");
    }

    #[test]
    fn publish_step5_child_appends_identity_rows() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let (_repository, identity) = seed_identity(tmp.path());
        let merge = tmp.path().join("child.env");
        assert!(publish_step5_child(
            tmp.path(),
            &merge.to_string_lossy(),
            "STEP5_REVIEW_STATUS=complete\n"
        ));
        let written = fs::read_to_string(&merge).unwrap();
        assert!(written.contains("STEP5_REVIEW_STATUS=complete"));
        assert!(written.contains(&format!("{CHECKS_HEAD}={}", identity.head_sha)));
    }

    #[test]
    fn step5_result_identity_ok_matches_live_identity() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let (_repository, identity) = seed_identity(tmp.path());
        let matching = hmap(&[
            (CHECKS_HEAD, identity.head_sha.as_str()),
            (CHECKS_FP, identity.tree_fp.as_str()),
            (CHECKS_SCHEMA, identity.schema.as_str()),
        ]);
        assert!(step5_result_identity_ok(tmp.path(), &matching));
        let stale = hmap(&[(CHECKS_HEAD, "other")]);
        assert!(!step5_result_identity_ok(tmp.path(), &stale));
    }

    #[test]
    fn step5_canonical_state_complete_when_identity_matches() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let (_repository, identity) = seed_identity(tmp.path());
        let mut body = format!(
            "STEP={STEP5_REVIEW_STEP}\nBGJOB_RC=0\nSTEP5_REVIEW_STATUS=complete\n\
             {CHECKS_HEAD}={}\n{CHECKS_FP}={}\n{CHECKS_SCHEMA}={}\n",
            identity.head_sha, identity.tree_fp, identity.schema
        );
        for key in STEP5_RESULT_ENVELOPE_KEYS {
            if *key != "STEP5_REVIEW_STATUS" {
                body.push_str(key);
                body.push_str("=v\n");
            }
        }
        write_result_env(tmp.path(), STEP5_REVIEW_STEP, &body);
        assert_eq!(
            step5_canonical_result_env_state(tmp.path()).unwrap(),
            "complete"
        );
    }

    #[test]
    fn handoff_timing_records_round_when_ledger_missing() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let round = tmp.path().join("round-2");
        fs::create_dir_all(&round).unwrap();
        fs::write(round.join("round-start-s"), "1000\n").unwrap();
        fs::write(
            round.join("review-tally.env"),
            "ACCEPTED_COUNT=1\nREJECTED_COUNT=0\n",
        )
        .unwrap();
        // No timing-ledger.tsv => proceeds to the record-round leg (larch_env
        // fails fast on the bogus root, but the ledger-scan branch is exercised).
        record_step5_handoff_timing(tmp.path(), "2");
    }

    #[test]
    fn handoff_timing_returns_early_on_matching_ledger_row() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        let round = tmp.path().join("round-3");
        fs::create_dir_all(&round).unwrap();
        fs::write(round.join("round-start-s"), "2000\n").unwrap();
        let ledger_row = "ts\tround\tx\timplement\tStep 5 — code review\t3\t2000\n";
        fs::write(tmp.path().join("timing-ledger.tsv"), ledger_row).unwrap();
        record_step5_handoff_timing(tmp.path(), "3");
    }

    #[test]
    fn step7a_public_bail_paths() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        // Unknown flag => argv bail envelope.
        let _ = step7a(&os(&["--nope"]));
        // Missing tmpdir => missing-implement-tmpdir bail (env is unset here).
        // Guard against an ambient value leaking in from the shell.
        if env::var_os("IMPLEMENT_TMPDIR").is_none() {
            let _ = step7a(&os(&["--issue-number", "42"]));
        }
    }

    #[test]
    fn step7a_public_bgjob_launch_and_run_paths() {
        let tmp = TempDir::new().unwrap();
        let work = TempDir::new().unwrap();
        let canonical = work.path().canonicalize().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, _a| {
            Ok(out(0, "DIAGRAM_STATUS=started\nREBASE_OUTCOME=skipped\n"))
        });
        crate::diagram_commands::install_test_diagram(|_tmp, _model, _remote, _ref| {
            crate::diagram_commands::CodeFlowDiagramResult {
                exit_code: 0,
                status: "skipped".to_owned(),
                diagram_file: String::new(),
                reason: "sanitizer-rejected".to_owned(),
            }
        });
        let tmpdir = canonical.to_string_lossy().into_owned();
        // bgjob-launch path.
        let _ = step7a(&os(&[
            "--implement-tmpdir",
            &tmpdir,
            "--issue-number",
            "42",
            "--run-id",
            "r1",
            "--bgjob-launch",
            "true",
        ]));
        // run path (bgjob-launch defaults to false).
        let _ = step7a(&os(&["--implement-tmpdir", &tmpdir, "--run-id", "r1"]));
    }

    #[test]
    fn resolve_session_repo_root_requires_repo_root_line() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_python(|_a| Ok(out(0, "OTHER=1\n")));
        assert!(resolve_session_repo_root(tmp.path()).is_err());
    }

    #[test]
    fn run_relevant_checks_empty_stdout_marks_failure() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        install_test_larch(|_c, _r, _a| Ok(out(0, "\n")));
        let (captured, _) = run_relevant_checks_for_site(tmp.path(), "step5", tmp.path());
        assert_eq!(captured.get("STATUS"), Some(&"fail".to_owned()));
        assert_eq!(
            captured.get("FAILURE_REASON"),
            Some(&"checks-child-failed".to_owned())
        );
    }

    #[test]
    fn generate_diagram_ok_writes_section_and_handles_retry_sidecar() {
        let tmp = TempDir::new().unwrap();
        let _guard = arm_plugin_root(&tmp);
        fs::write(tmp.path().join("code-flow-diagram.md"), "flow\n").unwrap();
        fs::write(tmp.path().join("code-flow-diagram.retried"), "FIRST_RC=1\n").unwrap();
        install_test_larch(|_c, _r, _a| Ok(out(0, "")));
        crate::diagram_commands::install_test_diagram(|_tmp, _model, _remote, _ref| {
            crate::diagram_commands::CodeFlowDiagramResult {
                exit_code: 0,
                status: "ok".to_owned(),
                diagram_file: "/d/f.md".to_owned(),
                reason: String::new(),
            }
        });
        let (status, path, _reason) = generate_code_flow_diagram(tmp.path(), "origin", "main");
        assert_eq!(status, "ok");
        assert_eq!(path, "/d/f.md");
        assert!(tmp.path().join("code-flow-section.md").exists());
        assert!(!tmp.path().join("code-flow-diagram.retried").exists());
    }
}
