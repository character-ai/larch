//! Step 3 review wrapper owner: resume-state validation and writes plus the
//! bgjob parent/child that used to live in `design-step3-review.sh`.

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use clap::Subcommand;
use larch_adapters::validate_design_tmpdir;
use larch_core::{
    ChildEnvironment, ProcessOutput, cleanup_cache_sessions_root, private_atomic_write,
};
use sha2::{Digest as _, Sha256};

use crate::{
    agent_commands::AgentRawArguments,
    argparse_compat::{ParsedCommandLine, parse_required_with_help},
    implement_child_seam::delegate_larch_with_options,
};

const PROG: &str = "plan-review step3-review";
const STEP: &str = "design-step3-review";
const BUDGET_S: u32 = 21_600;
const ADAPT_TIMEOUT: Duration = Duration::from_secs(600);
const RUN_TIMEOUT: Duration = Duration::from_secs(21_600);
const ORPHAN_TIMEOUT_S: &str = "7200";
const ALLOWED_PHASES: &[&str] = &[
    "awaiting-apply",
    "awaiting-revise",
    "awaiting-post-apply",
    "awaiting-postplan-operator",
    "awaiting-continuation",
];
const VALIDATE_PROG: &str = "cli.py plan-review resume-state validate";
const VALIDATE_USAGE: &str = "usage: cli.py plan-review resume-state validate [-h] --design-tmpdir DESIGN_TMPDIR\n                                              [--starting-round STARTING_ROUND]\n                                              [--phase PHASE]\n                                              [--findings-file FINDINGS_FILE]\n                                              [--postplan-operator-continue]";
const VALIDATE_HELP: &str = "usage: cli.py plan-review resume-state validate [-h] --design-tmpdir DESIGN_TMPDIR\n                                              [--starting-round STARTING_ROUND]\n                                              [--phase PHASE]\n                                              [--findings-file FINDINGS_FILE]\n                                              [--postplan-operator-continue]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --starting-round STARTING_ROUND\n  --phase PHASE\n  --findings-file FINDINGS_FILE\n  --postplan-operator-continue\n";
const WRITE_PROG: &str = "cli.py plan-review resume-state write";
const WRITE_USAGE: &str = "usage: cli.py plan-review resume-state write [-h] --design-tmpdir DESIGN_TMPDIR\n                                            [--starting-round STARTING_ROUND]\n                                            [--phase PHASE]\n                                            [--findings-file FINDINGS_FILE]\n                                            [--postplan-operator-continue]";
const WRITE_HELP: &str = "usage: cli.py plan-review resume-state write [-h] --design-tmpdir DESIGN_TMPDIR\n                                            [--starting-round STARTING_ROUND]\n                                            [--phase PHASE]\n                                            [--findings-file FINDINGS_FILE]\n                                            [--postplan-operator-continue]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --starting-round STARTING_ROUND\n  --phase PHASE\n  --findings-file FINDINGS_FILE\n  --postplan-operator-continue\n";

/// Nested `plan-review resume-state` verbs.
#[derive(Subcommand)]
pub enum ResumeStateCommand {
    /// Validate Step 3 resume-state flags against `DESIGN_TMPDIR`.
    #[command(name = "validate", disable_help_flag = true)]
    Validate(AgentRawArguments),
    /// Persist validated Step 3 resume-state sidecars.
    #[command(name = "write", disable_help_flag = true)]
    Write(AgentRawArguments),
}

#[derive(Clone, Debug, Default)]
#[allow(clippy::struct_excessive_bools)]
struct ResumeState {
    starting_round: String,
    starting_round_seen: bool,
    phase: String,
    phase_seen: bool,
    findings_file: String,
    findings_file_seen: bool,
    postplan_operator_continue: bool,
}

impl ResumeState {
    const fn has_resume_state(&self) -> bool {
        self.phase_seen || self.findings_file_seen || self.postplan_operator_continue
    }
}

#[derive(Clone, Debug, Default)]
struct Step3ReviewArgs {
    session_env_path: String,
    claude_pid: String,
    plugin_root: String,
    design_tmpdir: String,
    public_args: Vec<OsString>,
    bgjob_child: bool,
    merge_result_env: String,
    read_result_env: bool,
    resume: ResumeState,
    issue_number: String,
    repo: String,
}

/// Dispatch `plan-review resume-state {validate,write}`.
#[must_use]
pub fn resume_state(command: ResumeStateCommand) -> ExitCode {
    match command {
        ResumeStateCommand::Validate(arguments) => resume_state_validate(&arguments.arguments),
        ResumeStateCommand::Write(arguments) => resume_state_write(&arguments.arguments),
    }
}

/// `plan-review resume-state validate` compatibility command.
#[must_use]
pub fn resume_state_validate(arguments: &[OsString]) -> ExitCode {
    match parse_resume_state(arguments, VALIDATE_PROG, VALIDATE_USAGE, VALIDATE_HELP) {
        Ok((root, mut resume)) => match validate_resume(&root, VALIDATE_PROG, &mut resume) {
            Ok(()) => ExitCode::SUCCESS,
            Err(code) => code,
        },
        Err(code) => code,
    }
}

/// `plan-review resume-state write` compatibility command.
#[must_use]
pub fn resume_state_write(arguments: &[OsString]) -> ExitCode {
    let (root, mut resume) =
        match parse_resume_state(arguments, WRITE_PROG, WRITE_USAGE, WRITE_HELP) {
            Ok(parsed) => parsed,
            Err(code) => return code,
        };
    if let Err(code) = validate_resume(&root, WRITE_PROG, &mut resume) {
        return code;
    }
    if let Err(code) = write_resume(&root, &mut resume) {
        return code;
    }
    ExitCode::SUCCESS
}

/// `plan-review step3-review` parent/child owner.
#[must_use]
pub fn step3_review(arguments: &[OsString]) -> ExitCode {
    let mut parsed = match parse_step3_review(arguments) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if let Err(code) = resolve_session_env(&mut parsed) {
        return code;
    }
    let root = match resolve_parsed_design_dir(&parsed) {
        Ok(root) => root,
        Err(code) => return code,
    };
    parsed.design_tmpdir = root.display().to_string();
    if parsed.read_result_env {
        return match nested(
            &[
                OsString::from("plan-review"),
                OsString::from("normalize-status"),
                OsString::from("--design-tmpdir"),
                root.as_os_str().into(),
                OsString::from("--read-result-env"),
            ],
            ADAPT_TIMEOUT,
            &parsed,
        ) {
            Ok(output) => forward_exit(&output),
            Err(error) => {
                eprintln!("{error}");
                ExitCode::from(1)
            }
        };
    }
    if let Err(code) = validate_resume(&root, PROG, &mut parsed.resume) {
        return code;
    }
    if parsed.resume.has_resume_state()
        && let Err(code) = write_resume(&root, &mut parsed.resume)
    {
        return code;
    }
    if parsed.bgjob_child {
        return run_child(&root, &parsed);
    }
    if root.join(".pause-requested").is_file() {
        return pause_save(&root, &parsed);
    }
    run_parent(&root, &parsed)
}

fn parse_resume_state(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    help: &str,
) -> Result<(PathBuf, ResumeState), ExitCode> {
    let parsed = parse_required_with_help(
        arguments,
        program,
        usage,
        help,
        &[
            "--design-tmpdir",
            "--starting-round",
            "--phase",
            "--findings-file",
        ],
        &["--postplan-operator-continue"],
        &["--design-tmpdir"],
    )?;
    let raw = text(&parsed, "--design-tmpdir");
    let root = resolve_design_dir(&raw, program)?;
    let resume = ResumeState {
        starting_round: text(&parsed, "--starting-round"),
        starting_round_seen: parsed.value("--starting-round").is_some(),
        phase: text(&parsed, "--phase"),
        phase_seen: parsed.value("--phase").is_some(),
        findings_file: text(&parsed, "--findings-file"),
        findings_file_seen: parsed.value("--findings-file").is_some(),
        postplan_operator_continue: parsed.flag("--postplan-operator-continue"),
    };
    if resume.starting_round_seen && !positive(&resume.starting_round) {
        return Err(usage_die(
            program,
            "--starting-round requires a non-empty positive integer",
        ));
    }
    if resume.phase_seen && resume.phase.is_empty() {
        return Err(usage_die(program, "--phase requires a value"));
    }
    if resume.findings_file_seen && resume.findings_file.is_empty() {
        return Err(usage_die(program, "--findings-file requires a value"));
    }
    Ok((root, resume))
}

fn validate_resume(root: &Path, program: &str, resume: &mut ResumeState) -> Result<(), ExitCode> {
    if !resume.has_resume_state() {
        return Ok(());
    }
    if !resume.starting_round_seen {
        return Err(usage_die(
            program,
            "resume-state flags require --starting-round",
        ));
    }
    if !positive(&resume.starting_round) {
        return Err(usage_die(
            program,
            "--starting-round requires a non-empty positive integer",
        ));
    }
    match resume.phase.as_str() {
        "" => {}
        "awaiting-vote" => {
            return Err(usage_die(
                program,
                "--phase awaiting-vote is internal and cannot be used as a resume phase",
            ));
        }
        phase if ALLOWED_PHASES.contains(&phase) => {}
        other => return Err(usage_die(program, &format!("invalid --phase: {other}"))),
    }
    let last = read_round_count(root);
    let start = resume.starting_round.parse::<u64>().unwrap_or(0);
    if start > last.saturating_add(1) {
        return Err(usage_die(
            program,
            &format!(
                "--starting-round cannot exceed last consumed review round + 1 (got: {}, last consumed: {last})",
                resume.starting_round
            ),
        ));
    }
    if resume.findings_file.is_empty() {
        return Ok(());
    }
    resume.findings_file = validate_findings_file(root, &resume.findings_file)?
        .display()
        .to_string();
    Ok(())
}

fn validate_findings_file(root: &Path, raw: &str) -> Result<PathBuf, ExitCode> {
    if !raw.starts_with('/') {
        return Err(usage_die(PROG, "--findings-file must be an absolute path"));
    }
    if raw.contains('\n') || raw.contains('\r') {
        return Err(usage_die(
            PROG,
            "--findings-file must not contain newline or carriage return",
        ));
    }
    let path = Path::new(raw);
    let metadata = fs::symlink_metadata(path)
        .map_err(|_| usage_die(PROG, "--findings-file must be a regular file"))?;
    if metadata.file_type().is_symlink() {
        return Err(usage_die(PROG, "--findings-file must not be a symlink"));
    }
    if !metadata.is_file() {
        return Err(usage_die(PROG, "--findings-file must be a regular file"));
    }
    if metadata.permissions().mode() & 0o444 == 0 {
        return Err(usage_die(PROG, "--findings-file must be readable"));
    }
    fs::File::open(path).map_err(|_| usage_die(PROG, "--findings-file must be readable"))?;
    let canon = canonical_file(path)
        .map_err(|()| usage_die(PROG, "--findings-file parent cannot be resolved"))?;
    let root = fs::canonicalize(root).map_err(|_| usage_die(PROG, "DESIGN_TMPDIR required"))?;
    if !canon.starts_with(&root) || canon == root {
        return Err(usage_die(
            PROG,
            "--findings-file must resolve under DESIGN_TMPDIR",
        ));
    }
    Ok(canon)
}

fn write_resume(root: &Path, resume: &mut ResumeState) -> Result<(), ExitCode> {
    if !resume.has_resume_state() {
        return Ok(());
    }
    if !resume.phase.is_empty() {
        let path = root.join(format!(".step3-round-{}.phase", resume.starting_round));
        write_atomic(root, &path, &format!("{}\n", resume.phase))?;
    }
    if !resume.findings_file.is_empty() {
        let findings = validate_findings_file(root, &resume.findings_file)?;
        resume.findings_file = findings.display().to_string();
        let path = root.join(format!(
            ".gate-b-per-round-approval-round-{}.env",
            resume.starting_round
        ));
        write_atomic(
            root,
            &path,
            &format!("FINDINGS_FILE={}\n", resume.findings_file),
        )?;
    }
    if resume.postplan_operator_continue {
        let path = root.join(format!(
            ".postplan-operator-continue-{}",
            resume.starting_round
        ));
        write_atomic(root, &path, "")?;
    }
    Ok(())
}

fn parse_step3_review(arguments: &[OsString]) -> Result<Step3ReviewArgs, ExitCode> {
    let (public, bgjob_child, merge_result_env) = split_adapter_suffix(arguments)?;
    let mut parsed = Step3ReviewArgs {
        bgjob_child,
        merge_result_env,
        design_tmpdir: env::var("DESIGN_TMPDIR").unwrap_or_default(),
        issue_number: env::var("ISSUE_NUMBER").unwrap_or_default(),
        repo: env::var("REPO").unwrap_or_default(),
        public_args: public.clone(),
        ..Step3ReviewArgs::default()
    };
    let mut index = 0;
    while index < public.len() {
        let Some(flag) = public[index].to_str() else {
            return Err(unknown_argument(&public[index]));
        };
        match flag {
            "--session-env-path" => {
                parsed.session_env_path = take_value(&public, &mut index, flag)?;
            }
            "--claude-pid" => parsed.claude_pid = take_value(&public, &mut index, flag)?,
            "--plugin-root" => parsed.plugin_root = take_value(&public, &mut index, flag)?,
            "--design-tmpdir" => parsed.design_tmpdir = take_value(&public, &mut index, flag)?,
            "--mode" | "--site" | "--outcome" | "--step3-review-loop-status" | "--loop-status" => {
                take_value(&public, &mut index, flag)?;
            }
            "--snapshot-original" | "--skip-validate" => index += 1,
            "--starting-round" => {
                parsed.resume.starting_round_seen = true;
                parsed.resume.starting_round = take_value(&public, &mut index, flag)?;
            }
            "--phase" => {
                parsed.resume.phase_seen = true;
                parsed.resume.phase = take_value(&public, &mut index, flag)?;
            }
            "--findings-file" => {
                parsed.resume.findings_file_seen = true;
                parsed.resume.findings_file = take_value(&public, &mut index, flag)?;
            }
            "--postplan-operator-continue" => {
                parsed.resume.postplan_operator_continue = true;
                index += 1;
            }
            "--read-result-env" => {
                parsed.read_result_env = true;
                index += 1;
            }
            "--" => break,
            other if other.starts_with('-') => return Err(unknown_argument(&public[index])),
            _ => return Err(unknown_argument(&public[index])),
        }
    }
    if parsed.resume.starting_round_seen && !positive(&parsed.resume.starting_round) {
        return Err(usage_die(
            PROG,
            "--starting-round requires a non-empty positive integer",
        ));
    }
    if parsed.resume.phase_seen && parsed.resume.phase.is_empty() {
        return Err(usage_die(PROG, "--phase requires a value"));
    }
    if parsed.resume.findings_file_seen && parsed.resume.findings_file.is_empty() {
        return Err(usage_die(PROG, "--findings-file requires a value"));
    }
    Ok(parsed)
}

fn split_adapter_suffix(arguments: &[OsString]) -> Result<(Vec<OsString>, bool, String), ExitCode> {
    let count = arguments.len();
    if count >= 3
        && arguments[count - 3] == "--bgjob-child"
        && arguments[count - 2] == "--merge-result-env"
        && !arguments[count - 1].is_empty()
    {
        let public = arguments[..count - 3].to_vec();
        if public
            .iter()
            .any(|argument| argument == "--bgjob-child" || argument == "--merge-result-env")
        {
            return Err(usage_die(
                PROG,
                "adapter child controls must be one terminal suffix",
            ));
        }
        return Ok((
            public,
            true,
            arguments[count - 1].to_string_lossy().into_owned(),
        ));
    }
    if arguments
        .iter()
        .any(|argument| argument == "--bgjob-child" || argument == "--merge-result-env")
    {
        return Err(usage_die(
            PROG,
            "adapter child controls must be one terminal suffix",
        ));
    }
    Ok((arguments.to_vec(), false, String::new()))
}

fn take_value(arguments: &[OsString], index: &mut usize, flag: &str) -> Result<String, ExitCode> {
    let value = arguments
        .get(*index + 1)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| match flag {
            "--starting-round" => usage_die(
                PROG,
                "--starting-round requires a non-empty positive integer",
            ),
            "--phase" => usage_die(PROG, "--phase requires a value"),
            "--findings-file" => usage_die(PROG, "--findings-file requires a value"),
            _ => usage_die(PROG, &format!("{flag} requires a value")),
        })?;
    *index += 2;
    Ok(value.to_string_lossy().into_owned())
}

fn unknown_argument(argument: &OsStr) -> ExitCode {
    eprintln!("{PROG}: unknown argument: {}", argument.to_string_lossy());
    ExitCode::from(2)
}

fn resolve_session_env(parsed: &mut Step3ReviewArgs) -> Result<(), ExitCode> {
    if parsed.session_env_path.is_empty() {
        return Ok(());
    }
    let mut args = vec![
        OsString::from("bgjob"),
        OsString::from("adapt"),
        OsString::from("--resolve-session-env"),
        OsString::from("--session-env-path"),
        OsString::from(&parsed.session_env_path),
    ];
    if !parsed.claude_pid.is_empty() {
        args.extend([
            OsString::from("--owner-pid"),
            OsString::from(&parsed.claude_pid),
        ]);
    }
    let Ok(output) = nested(&args, ADAPT_TIMEOUT, parsed) else {
        println!("BGJOB_ERROR=session-env-resolution-failed");
        return Err(ExitCode::from(2));
    };
    if !output.status().success() {
        if output.stdout().is_empty() {
            println!("BGJOB_ERROR=session-env-resolution-failed");
        } else {
            let _ = std::io::stdout().write_all(output.stdout());
        }
        return Err(ExitCode::from(2));
    }
    apply_export_rows(output.stdout(), parsed);
    Ok(())
}

fn apply_export_rows(bytes: &[u8], parsed: &mut Step3ReviewArgs) {
    let text = String::from_utf8_lossy(bytes);
    for line in text.lines() {
        let Some(rest) = line.trim().strip_prefix("export ") else {
            continue;
        };
        let Some((key, raw)) = rest.split_once('=') else {
            continue;
        };
        let value = unquote(raw);
        match key {
            "DESIGN_TMPDIR" => parsed.design_tmpdir = value,
            "ISSUE_NUMBER" => parsed.issue_number = value,
            "REPO" => parsed.repo = value,
            "CLAUDE_PLUGIN_ROOT" => parsed.plugin_root = value,
            _ => {}
        }
    }
}

fn unquote(value: &str) -> String {
    if value.len() >= 2 && value.starts_with('\'') && value.ends_with('\'') {
        return value[1..value.len() - 1].replace("'\\''", "'");
    }
    if value.len() >= 2 && value.starts_with('"') && value.ends_with('"') {
        return value[1..value.len() - 1].to_owned();
    }
    value.to_owned()
}

fn resolve_parsed_design_dir(parsed: &Step3ReviewArgs) -> Result<PathBuf, ExitCode> {
    let raw = if parsed.design_tmpdir.is_empty() {
        env::var("DESIGN_TMPDIR").unwrap_or_default()
    } else {
        parsed.design_tmpdir.clone()
    };
    if raw.is_empty() || !Path::new(&raw).is_dir() {
        eprintln!("/design wrapper: DESIGN_TMPDIR required");
        return Err(ExitCode::from(1));
    }
    resolve_design_dir(&raw, PROG)
}

fn resolve_design_dir(raw: &str, program: &str) -> Result<PathBuf, ExitCode> {
    let path = Path::new(raw);
    if !path.is_dir() {
        eprintln!("{program}: DESIGN_TMPDIR required");
        return Err(ExitCode::from(2));
    }
    if path.is_symlink() {
        eprintln!("{program}: design-tmpdir must not be a symlink");
        return Err(ExitCode::from(2));
    }
    if let Err(message) = validate_design_tmpdir(
        raw,
        env::var_os("TMPDIR").as_deref(),
        &cleanup_cache_sessions_root(
            env::var_os("XDG_CACHE_HOME").as_deref(),
            env::var_os("HOME").as_deref(),
        ),
    ) {
        eprintln!("{program}: {message}");
        return Err(ExitCode::from(2));
    }
    fs::canonicalize(path).map_err(|error| {
        eprintln!("{program}: {error}");
        ExitCode::from(2)
    })
}

fn run_parent(root: &Path, parsed: &Step3ReviewArgs) -> ExitCode {
    let mut args = vec![
        OsString::from("bgjob"),
        OsString::from("adapt"),
        OsString::from("--step"),
        OsString::from(STEP),
        OsString::from("--tmpdir"),
        root.as_os_str().into(),
        OsString::from("--budget-s"),
        OsString::from(BUDGET_S.to_string()),
    ];
    if !parsed.claude_pid.is_empty() {
        args.extend([
            OsString::from("--owner-pid"),
            OsString::from(&parsed.claude_pid),
        ]);
    }
    if !parsed.session_env_path.is_empty() {
        args.extend([
            OsString::from("--session-env-path"),
            OsString::from(&parsed.session_env_path),
        ]);
    }
    if parsed.resume.has_resume_state() {
        args.push(OsString::from("--replace-completed-result"));
    }
    args.extend([
        OsString::from("--clear-on-fresh"),
        root.join(".completed/step-3").into_os_string(),
        OsString::from("--input-fingerprint"),
        OsString::from(plan_fingerprint(root)),
        OsString::from("--"),
        OsString::from("plan-review"),
        OsString::from("step3-review"),
    ]);
    args.extend(parsed.public_args.iter().cloned());
    match nested(&args, ADAPT_TIMEOUT, parsed) {
        Ok(output) => forward_exit(&output),
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
    }
}

#[allow(clippy::too_many_lines)]
fn run_child(root: &Path, parsed: &Step3ReviewArgs) -> ExitCode {
    if parsed.merge_result_env.is_empty() {
        eprintln!("{PROG}: --merge-result-env is required in child mode");
        return ExitCode::from(2);
    }
    let sidecar = match quarantine_sidecar(root) {
        Ok(path) => path,
        Err(code) => return code,
    };
    let finish = |code: ExitCode| {
        if let Some(path) = &sidecar {
            let _ = fs::remove_file(path);
        }
        code
    };
    if root.join(".pause-requested").is_file() {
        let pause = pause_save(root, parsed);
        if pause != ExitCode::SUCCESS {
            return finish(pause);
        }
        if let Err(code) = write_pause_result(root, parsed) {
            return finish(code);
        }
        return finish(publish_merge(root, &parsed.merge_result_env, parsed));
    }
    if !scope_anchor_ok(root, parsed) {
        eprintln!(
            "**⚠ Step 3: plan-review-scope-anchor.txt is missing, empty, invalid, or outside DESIGN_TMPDIR; treating plan review as panel-init-failed before launch**"
        );
        let _ = nested(
            &[
                OsString::from("plan-review"),
                OsString::from("prelaunch-failure"),
                OsString::from("--design-tmpdir"),
                root.as_os_str().into(),
                OsString::from("--reason"),
                OsString::from("scope-anchor-missing"),
            ],
            ADAPT_TIMEOUT,
            parsed,
        );
        return finish(publish_merge(root, &parsed.merge_result_env, parsed));
    }
    let Ok(stdout_file) = tempfile::Builder::new()
        .prefix("larch-step3-review-stdout.")
        .tempfile()
    else {
        eprintln!(
            "**⚠ Step 3: could not allocate plan-review stdout capture; aborting plan review**"
        );
        return finish(ExitCode::from(1));
    };
    let mut run_args = vec![
        OsString::from("plan-review"),
        OsString::from("run"),
        OsString::from("--design-tmpdir"),
        root.as_os_str().into(),
        OsString::from("--mode"),
        OsString::from("loop"),
        OsString::from("--new-process-group"),
        OsString::from("--orphan-timeout-s"),
        OsString::from(ORPHAN_TIMEOUT_S),
    ];
    if !parsed.resume.starting_round.is_empty() {
        run_args.extend([
            OsString::from("--starting-round"),
            OsString::from(&parsed.resume.starting_round),
        ]);
    }
    let run = match nested(&run_args, RUN_TIMEOUT, parsed) {
        Ok(output) => output,
        Err(error) => {
            eprintln!("{error}");
            return finish(ExitCode::from(1));
        }
    };
    let stderr_log = root.join("plan-review-loop-stderr.log");
    if stderr_log.is_symlink() {
        return finish(ExitCode::from(1));
    }
    if fs::write(&stderr_log, run.stderr()).is_err() {
        return finish(ExitCode::from(1));
    }
    if fs::write(stdout_file.path(), run.stdout()).is_err() {
        return finish(ExitCode::from(1));
    }
    let loop_rc = run.status().code().unwrap_or(1);
    let _ = nested(
        &[
            OsString::from("plan-review"),
            OsString::from("normalize-status"),
            OsString::from("--design-tmpdir"),
            root.as_os_str().into(),
            OsString::from("--stdout-file"),
            stdout_file.path().as_os_str().into(),
            OsString::from("--loop-rc"),
            OsString::from(loop_rc.to_string()),
        ],
        ADAPT_TIMEOUT,
        parsed,
    );
    finish(publish_merge(root, &parsed.merge_result_env, parsed))
}

fn quarantine_sidecar(root: &Path) -> Result<Option<PathBuf>, ExitCode> {
    let path = root.join(".step3-review-result.env");
    if !path.exists() && !path.is_symlink() {
        return Ok(None);
    }
    let metadata = fs::symlink_metadata(&path).map_err(|_| ExitCode::from(1))?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(ExitCode::from(1));
    }
    let prior = root.join(format!(
        ".step3-review-result.env.prior.{}",
        std::process::id()
    ));
    fs::rename(&path, &prior).map_err(|_| ExitCode::from(1))?;
    Ok(Some(prior))
}

fn scope_anchor_ok(root: &Path, parsed: &Step3ReviewArgs) -> bool {
    nested(
        &[
            OsString::from("scope-anchor"),
            OsString::from("validate"),
            OsString::from("--mode"),
            OsString::from("design"),
            OsString::from("--design-tmpdir"),
            root.as_os_str().into(),
            OsString::from("--path"),
            root.join("plan-review-scope-anchor.txt").into_os_string(),
        ],
        ADAPT_TIMEOUT,
        parsed,
    )
    .is_ok_and(|output| output.status().success())
}

fn pause_save(root: &Path, parsed: &Step3ReviewArgs) -> ExitCode {
    let mut args = vec![
        OsString::from("design"),
        OsString::from("pause-save"),
        OsString::from("--design-tmpdir"),
        root.as_os_str().into(),
        OsString::from("--issue"),
        OsString::from(&parsed.issue_number),
    ];
    if !parsed.repo.is_empty() {
        args.extend([OsString::from("--repo"), OsString::from(&parsed.repo)]);
    }
    match nested(&args, ADAPT_TIMEOUT, parsed) {
        Ok(output) => forward_exit(&output),
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
    }
}

fn write_pause_result(root: &Path, parsed: &Step3ReviewArgs) -> Result<(), ExitCode> {
    merge_env(
        root,
        &root.join(".step3-review-result.env"),
        &[
            ("NEXT_ACTION", "pause-save"),
            ("STEP3_REVIEW_LOOP_STATUS", "pause-save"),
            ("LOOP_STATUS", "pause-save"),
            ("PAUSE_OK", "true"),
        ],
        None,
        parsed,
    )
}

fn publish_merge(root: &Path, merge_path: &str, parsed: &Step3ReviewArgs) -> ExitCode {
    match merge_env(
        root,
        Path::new(merge_path),
        &[],
        Some(root.join(".step3-review-result.env")),
        parsed,
    ) {
        Ok(()) => ExitCode::SUCCESS,
        Err(code) => code,
    }
}

fn merge_env(
    root: &Path,
    path: &Path,
    rows: &[(&str, &str)],
    source: Option<PathBuf>,
    parsed: &Step3ReviewArgs,
) -> Result<(), ExitCode> {
    let mut args = vec![
        OsString::from("bgjob"),
        OsString::from("write-merge-result-env"),
        OsString::from("--path"),
        path.as_os_str().into(),
        OsString::from("--tmpdir"),
        root.as_os_str().into(),
    ];
    for (key, value) in rows {
        args.extend([
            OsString::from("--row"),
            OsString::from(format!("{key}={value}")),
        ]);
    }
    if let Some(source) = source {
        args.extend([
            OsString::from("--source"),
            source.into_os_string(),
            OsString::from("--require-key"),
            OsString::from("NEXT_ACTION"),
            OsString::from("--require-any-key"),
            OsString::from("STEP3_REVIEW_LOOP_STATUS"),
            OsString::from("--require-any-key"),
            OsString::from("LOOP_STATUS"),
        ]);
    }
    match nested(&args, ADAPT_TIMEOUT, parsed) {
        Ok(output) if output.status().success() => Ok(()),
        Ok(output) => {
            let _ = std::io::stderr().write_all(output.stderr());
            Err(ExitCode::from(1))
        }
        Err(error) => {
            eprintln!("{error}");
            Err(ExitCode::from(1))
        }
    }
}

fn plan_fingerprint(root: &Path) -> String {
    let plan = root.join("plan.txt");
    match fs::symlink_metadata(&plan) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => fs::read(&plan)
            .map_or_else(
                |_| "compute-failed".to_owned(),
                |bytes| format!("{:x}", Sha256::digest(bytes)),
            ),
        _ => "source-absent".to_owned(),
    }
}

fn canonical_file(path: &Path) -> Result<PathBuf, ()> {
    let parent = path.parent().ok_or(())?;
    let name = path.file_name().ok_or(())?;
    Ok(fs::canonicalize(parent).map_err(|_| ())?.join(name))
}

fn read_round_count(root: &Path) -> u64 {
    let path = root.join("review-round-count.txt");
    let Ok(metadata) = fs::symlink_metadata(&path) else {
        return 0;
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return 0;
    }
    let raw = fs::read_to_string(&path).unwrap_or_default();
    let trimmed: String = raw.chars().filter(|ch| !ch.is_whitespace()).collect();
    if trimmed.is_empty() || !trimmed.bytes().all(|byte| byte.is_ascii_digit()) {
        return 0;
    }
    trimmed.parse().unwrap_or(0)
}

fn write_atomic(root: &Path, path: &Path, body: &str) -> Result<(), ExitCode> {
    if path.is_symlink() {
        eprintln!("{PROG}: refusing to write symlink {}", path.display());
        return Err(ExitCode::from(1));
    }
    private_atomic_write(path, body, root).map_err(|error| {
        eprintln!("{PROG}: {error}");
        ExitCode::from(1)
    })
}

fn nested(
    arguments: &[OsString],
    timeout: Duration,
    parsed: &Step3ReviewArgs,
) -> Result<ProcessOutput, String> {
    let mut environment = Vec::new();
    if !parsed.design_tmpdir.is_empty() {
        environment.push((
            ChildEnvironment::DesignTmpdir,
            OsString::from(&parsed.design_tmpdir),
        ));
    }
    if !parsed.plugin_root.is_empty() {
        environment.push((
            ChildEnvironment::ClaudePluginRoot,
            OsString::from(&parsed.plugin_root),
        ));
    }
    delegate_larch_with_options(arguments, &environment, timeout)
}

fn forward_exit(output: &ProcessOutput) -> ExitCode {
    let _ = std::io::stdout().write_all(output.stdout());
    let _ = std::io::stderr().write_all(output.stderr());
    ExitCode::from(u8::try_from(output.status().code().unwrap_or(1)).unwrap_or(1))
}

fn text(parsed: &ParsedCommandLine, name: &str) -> String {
    parsed
        .value(name)
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn positive(value: &str) -> bool {
    !value.is_empty()
        && value.bytes().all(|byte| byte.is_ascii_digit())
        && value.contains(|ch: char| ch != '0')
}

fn usage_die(program: &str, error: &str) -> ExitCode {
    eprintln!("{program}: {error}");
    ExitCode::from(2)
}

#[cfg(test)]
mod tests {
    use super::{
        PROG, ResumeState, canonical_file, parse_step3_review, plan_fingerprint, positive,
        read_round_count, resume_state_validate, resume_state_write, split_adapter_suffix,
        step3_review, validate_resume, write_resume,
    };
    use crate::implement_child_seam::{clear_hooks, install_larch};
    use larch_core::{ProcessOutput, ProcessStatus};
    use std::{
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        sync::{Arc, Mutex},
    };
    use tempfile::TempDir;

    fn output(code: i32, stdout: &str) -> ProcessOutput {
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

    fn snapshot_argv(seen: &Arc<Mutex<Vec<Vec<String>>>>) -> Vec<Vec<String>> {
        seen.lock().expect("lock").clone()
    }

    fn design() -> (TempDir, PathBuf) {
        let sandbox = TempDir::new().expect("sandbox");
        let root = sandbox.path().join("design");
        fs::create_dir(&root).expect("design");
        (sandbox, root)
    }

    fn step3_args(root: &Path, extra: &[&str]) -> Vec<OsString> {
        let tmpdir = root.display().to_string();
        let mut args = os(&["--design-tmpdir", &tmpdir]);
        args.extend(os(extra));
        args
    }

    struct HookGuard;
    impl Drop for HookGuard {
        fn drop(&mut self) {
            clear_hooks();
        }
    }

    fn resume(root: &Path, round: &str, phase: &str) -> ResumeState {
        let _ = root;
        ResumeState {
            starting_round: round.to_owned(),
            starting_round_seen: true,
            phase: phase.to_owned(),
            phase_seen: !phase.is_empty(),
            ..ResumeState::default()
        }
    }

    #[test]
    fn adapter_suffix_must_be_terminal() {
        let ok = split_adapter_suffix(&os(&[
            "--starting-round",
            "1",
            "--bgjob-child",
            "--merge-result-env",
            "/tmp/merge.env",
        ]))
        .expect("suffix");
        assert!(ok.1);
        assert_eq!(ok.2, "/tmp/merge.env");
        assert!(split_adapter_suffix(&os(&["--bgjob-child", "--starting-round", "1"])).is_err());
    }

    #[test]
    fn starting_round_must_be_positive() {
        assert!(!positive(""));
        assert!(!positive("0"));
        assert!(!positive("00"));
        assert!(positive("1"));
        assert!(positive("01"));
        let parsed = parse_step3_review(&os(&["--starting-round", "0"]));
        assert!(parsed.is_err());
    }

    #[test]
    fn resume_state_requires_starting_round_and_rejects_vote_phase() {
        let (_sandbox, root) = design();
        let mut state = ResumeState {
            phase: "awaiting-apply".into(),
            phase_seen: true,
            ..ResumeState::default()
        };
        assert!(validate_resume(&root, PROG, &mut state).is_err());
        state = resume(&root, "1", "awaiting-vote");
        assert!(validate_resume(&root, PROG, &mut state).is_err());
        state = resume(&root, "1", "awaiting-apply");
        assert!(validate_resume(&root, PROG, &mut state).is_ok());
        fs::write(root.join("review-round-count.txt"), "1\n").expect("count");
        state = resume(&root, "3", "awaiting-apply");
        assert!(validate_resume(&root, PROG, &mut state).is_err());
        state = resume(&root, "2", "awaiting-apply");
        assert!(validate_resume(&root, PROG, &mut state).is_ok());
    }

    #[test]
    fn findings_file_must_stay_under_design_tmpdir() {
        let (sandbox, root) = design();
        let inside = root.join("findings.md");
        fs::write(&inside, "body\n").expect("findings");
        let mut state = resume(&root, "1", "awaiting-apply");
        state.findings_file_seen = true;
        state.findings_file = inside.display().to_string();
        assert!(validate_resume(&root, PROG, &mut state).is_ok());
        write_resume(&root, &mut state).expect("write");
        assert_eq!(
            fs::read_to_string(root.join(".step3-round-1.phase")).expect("phase"),
            "awaiting-apply\n"
        );
        assert!(
            fs::read_to_string(root.join(".gate-b-per-round-approval-round-1.env"))
                .expect("approval")
                .starts_with("FINDINGS_FILE=")
        );
        let outside = sandbox.path().join("outside.md");
        fs::write(&outside, "nope\n").expect("outside");
        state.findings_file = outside.display().to_string();
        assert!(validate_resume(&root, PROG, &mut state).is_err());
        let _ = canonical_file(&inside);
    }

    #[test]
    fn resume_state_cli_writes_continue_sentinel() {
        let (_sandbox, root) = design();
        let code = resume_state_write(&os(&[
            "--design-tmpdir",
            &root.display().to_string(),
            "--starting-round",
            "1",
            "--postplan-operator-continue",
        ]));
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        assert!(root.join(".postplan-operator-continue-1").is_file());
        assert_eq!(
            resume_state_validate(&os(&[
                "--design-tmpdir",
                &root.display().to_string(),
                "--starting-round",
                "1",
                "--phase",
                "awaiting-continuation",
            ])),
            std::process::ExitCode::SUCCESS
        );
    }

    #[test]
    fn parent_launches_adapt_with_fingerprint_and_resume_replace() {
        let (_sandbox, root) = design();
        fs::write(root.join("plan.txt"), "plan body\n").expect("plan");
        fs::write(root.join("review-round-count.txt"), "1\n").expect("count");
        let seen = Arc::new(Mutex::new(Vec::<Vec<String>>::new()));
        let captured = Arc::clone(&seen);
        install_larch(move |args, _env| {
            captured.lock().expect("lock").push(
                args.iter()
                    .map(|value| value.to_string_lossy().into_owned())
                    .collect(),
            );
            Ok(output(
                0,
                "BGJOB_STATUS=STARTED STEP=design-step3-review PGID=9\n",
            ))
        });
        let _guard = HookGuard;
        let code = step3_review(&step3_args(
            &root,
            &[
                "--claude-pid",
                "123",
                "--starting-round",
                "1",
                "--phase",
                "awaiting-apply",
            ],
        ));
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        let rows = snapshot_argv(&seen);
        let adapt = rows
            .iter()
            .find(|row| row.windows(2).any(|pair| pair == ["bgjob", "adapt"]))
            .expect("adapt argv");
        assert!(adapt.contains(&"--replace-completed-result".to_owned()));
        assert!(adapt.contains(&"--clear-on-fresh".to_owned()));
        assert!(adapt.contains(&"--input-fingerprint".to_owned()));
        let fingerprint = plan_fingerprint(&root);
        assert_eq!(fingerprint.len(), 64);
        assert!(adapt.contains(&fingerprint));
        assert!(
            adapt
                .iter()
                .any(|value| value.ends_with("/.completed/step-3")
                    || value.ends_with(".completed/step-3"))
        );
    }

    #[test]
    fn child_pause_publishes_terminal_merge_envelope() {
        let (_sandbox, root) = design();
        fs::write(root.join(".pause-requested"), "").expect("pause");
        let merge = root.join("merge.env");
        fs::write(&merge, "").expect("merge");
        fs::write(root.join(".step3-review-result.env"), "NEXT_ACTION=old\n").expect("stale");
        let pause_root = root.clone();
        install_larch(move |args, _env| {
            let text: Vec<String> = args
                .iter()
                .map(|value| value.to_string_lossy().into_owned())
                .collect();
            if text.windows(2).any(|pair| pair == ["design", "pause-save"]) {
                fs::write(pause_root.join(".pause-published"), "").expect("published");
                return Ok(output(0, ""));
            }
            if text
                .windows(2)
                .any(|pair| pair == ["bgjob", "write-merge-result-env"])
            {
                let path = text
                    .windows(2)
                    .find(|pair| pair[0] == "--path")
                    .map(|pair| PathBuf::from(&pair[1]))
                    .expect("path");
                if text.iter().any(|value| value.starts_with("NEXT_ACTION=")) {
                    fs::write(
                        &path,
                        "NEXT_ACTION=pause-save\nSTEP3_REVIEW_LOOP_STATUS=pause-save\nLOOP_STATUS=pause-save\nPAUSE_OK=true\n",
                    )
                    .expect("rows");
                } else {
                    fs::write(
                        &path,
                        "NEXT_ACTION=pause-save\nSTEP3_REVIEW_LOOP_STATUS=pause-save\nLOOP_STATUS=pause-save\nPAUSE_OK=true\n",
                    )
                    .expect("copy");
                }
                return Ok(output(0, ""));
            }
            Ok(output(0, ""))
        });
        let _guard = HookGuard;
        let merge_path = merge.display().to_string();
        let code = step3_review(&step3_args(
            &root,
            &["--bgjob-child", "--merge-result-env", &merge_path],
        ));
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        assert!(root.join(".pause-published").is_file());
        let body = fs::read_to_string(&merge).expect("merge body");
        assert!(body.contains("NEXT_ACTION=pause-save\n"));
        assert!(body.contains("PAUSE_OK=true\n"));
        assert!(
            !root.join(".step3-review-result.env").is_file() || {
                // pause writer recreates the result env after quarantining the stale sidecar
                fs::read_to_string(root.join(".step3-review-result.env"))
                    .unwrap_or_default()
                    .contains("PAUSE_OK=true")
            }
        );
        assert_eq!(read_round_count(&root), 0);
    }

    #[test]
    fn child_forwards_starting_round_and_rejects_stale_merge_source() {
        let (_sandbox, root) = design();
        fs::write(root.join("plan-review-scope-anchor.txt"), "anchor\n").expect("anchor");
        fs::write(
            root.join(".step3-review-result.env"),
            "NEXT_ACTION=step3b\nSTEP3_REVIEW_LOOP_STATUS=complete\nLOOP_STATUS=complete\n",
        )
        .expect("stale");
        let merge = root.join("merge.env");
        let seen = Arc::new(Mutex::new(Vec::<Vec<String>>::new()));
        let captured = Arc::clone(&seen);
        install_larch(move |args, _env| {
            let text: Vec<String> = args
                .iter()
                .map(|value| value.to_string_lossy().into_owned())
                .collect();
            captured.lock().expect("lock").push(text.clone());
            if text
                .windows(2)
                .any(|pair| pair == ["scope-anchor", "validate"])
            {
                return Ok(output(0, "OK=true\n"));
            }
            if text.windows(2).any(|pair| pair == ["plan-review", "run"]) {
                return Ok(output(0, ""));
            }
            if text
                .windows(2)
                .any(|pair| pair == ["plan-review", "normalize-status"])
            {
                return Ok(output(0, ""));
            }
            if text
                .windows(2)
                .any(|pair| pair == ["bgjob", "write-merge-result-env"])
            {
                return Ok(output(1, ""));
            }
            Ok(output(0, ""))
        });
        let _guard = HookGuard;
        let merge_path = merge.display().to_string();
        let code = step3_review(&step3_args(
            &root,
            &[
                "--starting-round",
                "1",
                "--bgjob-child",
                "--merge-result-env",
                &merge_path,
            ],
        ));
        assert_eq!(code, std::process::ExitCode::from(1));
        let rows = snapshot_argv(&seen);
        assert!(rows.iter().any(|row| {
            row.windows(2).any(|pair| pair == ["plan-review", "run"])
                && row.windows(2).any(|pair| pair == ["--starting-round", "1"])
        }));
        assert!(!root.join(".step3-review-result.env").is_file());
    }

    #[test]
    fn wrapper_script_delegates_to_the_rust_owner() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let wrapper = fs::read_to_string(root.join("skills/design/scripts/design-step3-review.sh"))
            .expect("wrapper");
        assert!(wrapper.contains("plan-review step3-review"));
        assert!(!wrapper.contains("step3_review_validate_resume_state"));
        assert!(!wrapper.contains("Generated /design wrapper"));
    }

    #[test]
    fn missing_design_tmpdir_exits_one() {
        let code = step3_review(&os(&["--claude-pid", "1"]));
        assert_eq!(code, std::process::ExitCode::from(1));
    }

    #[test]
    fn session_env_is_resolved_before_adapt() {
        let (sandbox, root) = design();
        let session = sandbox.path().join("session-env.sh");
        fs::write(&session, "export DESIGN_TMPDIR=/unused\n").expect("session");
        let seen = Arc::new(Mutex::new(Vec::<Vec<String>>::new()));
        let captured = Arc::clone(&seen);
        install_larch(move |args, _env| {
            captured.lock().expect("lock").push(
                args.iter()
                    .map(|value| value.to_string_lossy().into_owned())
                    .collect(),
            );
            let text: Vec<String> = args
                .iter()
                .map(|value| value.to_string_lossy().into_owned())
                .collect();
            if text.iter().any(|value| value == "--resolve-session-env") {
                return Ok(output(
                    0,
                    &format!(
                        "export DESIGN_TMPDIR={}\nexport ISSUE_NUMBER=9\n",
                        root.display()
                    ),
                ));
            }
            Ok(output(
                0,
                "BGJOB_STATUS=STARTED STEP=design-step3-review PGID=9\n",
            ))
        });
        let _guard = HookGuard;
        let session_path = session.display().to_string();
        let code = step3_review(&os(&[
            "--session-env-path",
            &session_path,
            "--claude-pid",
            "123",
        ]));
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        let rows = snapshot_argv(&seen);
        assert!(rows[0].iter().any(|value| value == "--resolve-session-env"));
        assert!(rows.iter().any(|row| {
            row.windows(2).any(|pair| pair == ["bgjob", "adapt"])
                && !row.iter().any(|value| value == "--resolve-session-env")
                && !row
                    .iter()
                    .any(|value| value == "--replace-completed-result")
        }));
    }
}
