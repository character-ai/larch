//! Rust owner for `/design` Step 3 entry, Gate B, and Step 4 tail (#8931).
//!
//! Owns `design step3-entry`, `design gate-b`, and `design step4-tail`. Child
//! verbs (`plan-review`, `plan-block`, `scope-anchor`, `design driver`,
//! `bgjob`, `timing`) stay behind the verified `scripts/larch.sh` entrypoint.

use std::{
    ffi::OsString,
    fs,
    io::Write as IoWrite,
    path::{Path, PathBuf},
    process::{Command, ExitCode, Stdio},
};

use serde_json::Value;
use sha2::{Digest as _, Sha256};

use crate::design_step0_commands::{
    ChildOutcome, Env, LiveStep0Runner, Step0Runner, WrapperNs, entrypoint, env_get, exit_from_i32,
    load_source_env_allowed, load_wrapper_env, require_plugin_root, utf8_arguments,
};
use crate::design_step2b_commands::{print_text, resolve_design_tmpdir, touch};

const STEP3_ENTRY_PROGRAM: &str = "design-step3-entry.sh";
const GATE_B_PROGRAM: &str = "design-step35.sh";
const STEP4_TAIL_PROGRAM: &str = "design-step3b-tail.sh";
const STEP4_TAIL_STEP: &str = "design-step4-tail";
const STEP4_TAIL_BUDGET_S: &str = "900";
const REJECTED_BEGIN: &str = "---LARCH-REJECTED-BEGIN---";
const REJECTED_END: &str = "---LARCH-REJECTED-END---";
const REJECTED_FALLBACK_HEADING: &str = "## Considered Plan Review Suggestions (Not Adopted)";
const REJECTED_FALLBACK_BODY: &str = "These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.";
const SUMMARY_FAILED_JUDGE_PANEL: &str = "SUMMARY_OUTCOME=failed-judge-panel";
const STEP3_ENTRY_SOURCE_KEYS: [&str; 2] = ["POSITIONAL_KIND", "POSITIONAL_VALUE"];
const COMPLETE_LOOP_STATUSES: [&str; 3] = [
    "complete",
    "zero-findings-degraded-panel",
    "main-agent-vote-required",
];
const APPLY_LOOP_STATUSES: [&str; 3] = [
    "main-agent-apply-required",
    "per-round-approval-required",
    "postplan-operator-required",
];

struct VerbResult {
    code: ExitCode,
    stdout: String,
    stderr: String,
}

impl VerbResult {
    fn fail(code: u8, stderr: impl Into<String>) -> Self {
        Self {
            code: ExitCode::from(code),
            stdout: String::new(),
            stderr: stderr.into(),
        }
    }

    fn from_code(code: i32) -> Self {
        Self {
            code: exit_from_i32(code),
            stdout: String::new(),
            stderr: String::new(),
        }
    }
}

fn emit(out: &mut String, line: &str) {
    out.push_str(line);
    out.push('\n');
}

fn push_child(out: &mut VerbResult, child: &ChildOutcome) {
    out.stdout.push_str(&child.stdout);
    out.stderr.push_str(&child.stderr);
}

fn publish(result: &VerbResult) -> ExitCode {
    print_text(&result.stdout);
    eprint!("{}", result.stderr);
    result.code
}

#[cfg(test)]
trait Step3Seam {
    fn larch(&self, args: &[String], env: &[(String, String)]) -> ChildOutcome;
}

#[cfg(test)]
thread_local! {
    static TEST_SEAM: std::cell::RefCell<Option<std::rc::Rc<dyn Step3Seam>>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(test)]
fn current_seam() -> Option<std::rc::Rc<dyn Step3Seam>> {
    TEST_SEAM.with(|cell| cell.borrow().clone())
}

fn owned_child_argv(args: &[&str], env: &[(&str, &str)]) -> (Vec<String>, Vec<(String, String)>) {
    (
        args.iter().map(|value| (*value).to_string()).collect(),
        env.iter()
            .map(|(key, value)| ((*key).to_string(), (*value).to_string()))
            .collect(),
    )
}

fn run_larch(
    plugin_root: &Path,
    args: &[&str],
    env: &[(&str, &str)],
    runner: &dyn Step0Runner,
) -> ChildOutcome {
    let (owned, owned_env) = owned_child_argv(args, env);
    #[cfg(test)]
    if let Some(seam) = current_seam() {
        return seam.larch(&owned, &owned_env);
    }
    runner.run(plugin_root, &owned, &owned_env, false)
}

fn bytes_to_string(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

fn outcome_from_output(output: &std::process::Output) -> ChildOutcome {
    ChildOutcome {
        code: output.status.code().unwrap_or(1),
        stdout: bytes_to_string(&output.stdout),
        stderr: bytes_to_string(&output.stderr),
    }
}

fn run_larch_stdin(
    plugin_root: &Path,
    args: &[&str],
    stdin: &str,
    env: &[(&str, &str)],
) -> ChildOutcome {
    let (owned, owned_env) = owned_child_argv(args, env);
    #[cfg(test)]
    if let Some(seam) = current_seam() {
        return seam.larch(&owned, &owned_env);
    }
    let mut command = Command::new(entrypoint(plugin_root)); // lint-subprocess-via-runner: ok design Step 4 FINALIZE stdin is the same LiveStep0Runner larch.sh seam
    command.args(&owned);
    command.env("CLAUDE_PLUGIN_ROOT", plugin_root);
    for (key, value) in &owned_env {
        command.env(key, value);
    }
    command.stdin(Stdio::piped());
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());
    match command.spawn() {
        Ok(mut child) => {
            if let Some(mut handle) = child.stdin.take() {
                let _ = handle.write_all(stdin.as_bytes());
            }
            match child.wait_with_output() {
                Ok(output) => outcome_from_output(&output),
                Err(_error) => ChildOutcome {
                    code: 1,
                    stdout: String::new(),
                    stderr: String::new(),
                },
            }
        }
        Err(_error) => ChildOutcome {
            code: 1,
            stdout: String::new(),
            stderr: String::new(),
        },
    }
}

#[cfg(test)]
fn flag_value<'a>(argv: &'a [String], name: &str) -> Option<&'a str> {
    argv.windows(2)
        .find(|pair| pair[0] == name)
        .map(|pair| pair[1].as_str())
}

fn take_value<'a>(
    argv: &'a [String],
    index: &mut usize,
    program: &str,
) -> Result<&'a str, VerbResult> {
    let token = argv[*index].as_str();
    let Some(value) = argv.get(*index + 1) else {
        return Err(VerbResult::fail(
            2,
            format!("{program}: {token} requires a value\n"),
        ));
    };
    *index += 2;
    Ok(value.as_str())
}

fn unknown_arg(program: &str, token: &str) -> VerbResult {
    VerbResult::fail(2, format!("{program}: unknown argument: {token}\n"))
}

struct Step3EntryArgs {
    session_env_path: String,
    claude_pid: String,
    reentry: bool,
}

fn parse_step3_entry(argv: &[String]) -> Result<Step3EntryArgs, VerbResult> {
    let mut parsed = Step3EntryArgs {
        session_env_path: String::new(),
        claude_pid: String::new(),
        reentry: false,
    };
    let mut index = 0;
    while index < argv.len() {
        match argv[index].as_str() {
            "--session-env-path" => {
                take_value(argv, &mut index, STEP3_ENTRY_PROGRAM)?
                    .clone_into(&mut parsed.session_env_path);
            }
            "--claude-pid" => {
                take_value(argv, &mut index, STEP3_ENTRY_PROGRAM)?
                    .clone_into(&mut parsed.claude_pid);
            }
            "--reentry" => {
                parsed.reentry = true;
                index += 1;
            }
            other => return Err(unknown_arg(STEP3_ENTRY_PROGRAM, other)),
        }
    }
    Ok(parsed)
}

struct GateBArgs {
    session_env_path: String,
    claude_pid: String,
    plugin_root: String,
    loop_status: String,
    review_loop_status: String,
}

fn parse_gate_b(argv: &[String]) -> Result<GateBArgs, VerbResult> {
    let mut parsed = GateBArgs {
        session_env_path: String::new(),
        claude_pid: String::new(),
        plugin_root: std::env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default(),
        loop_status: std::env::var("LOOP_STATUS").unwrap_or_default(),
        review_loop_status: std::env::var("STEP3_REVIEW_LOOP_STATUS").unwrap_or_default(),
    };
    let mut index = 0;
    while index < argv.len() {
        match argv[index].as_str() {
            "--" => break,
            "--snapshot-original" | "--skip-validate" => index += 1,
            "--session-env-path" => {
                take_value(argv, &mut index, GATE_B_PROGRAM)?
                    .clone_into(&mut parsed.session_env_path);
            }
            "--claude-pid" => {
                take_value(argv, &mut index, GATE_B_PROGRAM)?.clone_into(&mut parsed.claude_pid);
            }
            "--plugin-root" => {
                take_value(argv, &mut index, GATE_B_PROGRAM)?.clone_into(&mut parsed.plugin_root);
            }
            "--step3-review-loop-status" => {
                take_value(argv, &mut index, GATE_B_PROGRAM)?
                    .clone_into(&mut parsed.review_loop_status);
            }
            "--loop-status" => {
                take_value(argv, &mut index, GATE_B_PROGRAM)?.clone_into(&mut parsed.loop_status);
            }
            "--mode" | "--site" | "--outcome" => {
                let _ = take_value(argv, &mut index, GATE_B_PROGRAM)?;
            }
            other => return Err(unknown_arg(GATE_B_PROGRAM, other)),
        }
    }
    Ok(parsed)
}

struct Step4TailArgs {
    session_env_path: String,
    claude_pid: String,
    child: bool,
    merge_result_env: PathBuf,
    core: Vec<String>,
}

fn parse_child_suffix(arguments: &[OsString]) -> Result<(bool, PathBuf, &[OsString]), VerbResult> {
    let len = arguments.len();
    let suffix = len
        .checked_sub(3)
        .and_then(|start| arguments.get(start..))
        .filter(|tail| {
            tail.len() == 3
                && tail[0] == "--bgjob-child"
                && tail[1] == "--merge-result-env"
                && !tail[2].is_empty()
        });
    let child_suffix = suffix.is_some();
    let misplaced = arguments.iter().enumerate().any(|(index, arg)| {
        matches!(
            arg.as_os_str().to_str(),
            Some("--bgjob-child" | "--merge-result-env")
        ) && !(child_suffix && index >= len.saturating_sub(3) && index < len.saturating_sub(1))
    });
    if misplaced {
        return Err(VerbResult::fail(
            2,
            format!("{STEP4_TAIL_PROGRAM}: adapter child controls must be one terminal suffix\n"),
        ));
    }
    Ok(suffix.map_or((false, PathBuf::new(), arguments), |tail| {
        (true, PathBuf::from(&tail[2]), &arguments[..len - 3])
    }))
}

fn parse_step4_tail(argv: &[String]) -> Result<(String, String, String), VerbResult> {
    let mut session_env_path = String::new();
    let mut claude_pid = String::new();
    let mut plugin_root = std::env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default();
    let mut index = 0;
    while index < argv.len() {
        match argv[index].as_str() {
            "--" => break,
            "--snapshot-original" | "--skip-validate" => index += 1,
            "--session-env-path" => {
                take_value(argv, &mut index, STEP4_TAIL_PROGRAM)?.clone_into(&mut session_env_path);
            }
            "--claude-pid" => {
                take_value(argv, &mut index, STEP4_TAIL_PROGRAM)?.clone_into(&mut claude_pid);
            }
            "--plugin-root" => {
                take_value(argv, &mut index, STEP4_TAIL_PROGRAM)?.clone_into(&mut plugin_root);
            }
            "--mode" | "--site" | "--outcome" | "--step3-review-loop-status" | "--loop-status" => {
                let _ = take_value(argv, &mut index, STEP4_TAIL_PROGRAM)?;
            }
            other => return Err(unknown_arg(STEP4_TAIL_PROGRAM, other)),
        }
    }
    Ok((session_env_path, claude_pid, plugin_root))
}

fn wrapper_env(session_env_path: &str, claude_pid: &str, plugin_root: &str) -> Env {
    let ns = WrapperNs {
        session_env_path: session_env_path.to_owned(),
        claude_pid: claude_pid.to_owned(),
        plugin_root: if plugin_root.is_empty() {
            std::env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default()
        } else {
            plugin_root.to_owned()
        },
        ..WrapperNs::default()
    };
    let mut env = load_wrapper_env(&ns);
    for (key, value) in
        load_source_env_allowed(session_env_path, claude_pid, &STEP3_ENTRY_SOURCE_KEYS)
    {
        let _ = env.insert(key, value);
    }
    env
}

fn require_plugin(env: &Env) -> Result<PathBuf, VerbResult> {
    require_plugin_root(env_get(env, "CLAUDE_PLUGIN_ROOT", "")).map_err(result_from_exit)
}

const fn result_from_exit(code: ExitCode) -> VerbResult {
    VerbResult {
        code,
        stdout: String::new(),
        stderr: String::new(),
    }
}

fn validate_tmpdir(raw: &str, missing: &str, program: &str) -> Result<PathBuf, VerbResult> {
    if raw.is_empty() {
        return Err(VerbResult::fail(1, format!("{missing}\n")));
    }
    let path = PathBuf::from(raw);
    if !path.is_dir() {
        return Err(VerbResult::fail(
            1,
            format!("{program}: DESIGN_TMPDIR required\n"),
        ));
    }
    Ok(resolve_design_tmpdir(raw))
}

fn json_bool(path: &Path, key: &str) -> bool {
    if !path.is_file() || path.is_symlink() {
        return false;
    }
    fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .and_then(|value| value.get(key).and_then(Value::as_bool))
        .unwrap_or(false)
}

fn nonempty_regular(path: &Path) -> bool {
    path.is_file() && !path.is_symlink() && fs::metadata(path).is_ok_and(|meta| meta.len() > 0)
}

fn sha256_file(path: &Path) -> String {
    match fs::read(path) {
        Ok(bytes) => {
            let digest = format!("{:x}", Sha256::digest(bytes));
            if digest.is_empty() {
                "compute-failed".to_owned()
            } else {
                digest
            }
        }
        Err(_error) => "compute-failed".to_owned(),
    }
}

fn input_fingerprint(design: &Path) -> String {
    let sidecar = design.join(".step3-review-result.env");
    if sidecar.is_file() && !sidecar.is_symlink() {
        sha256_file(&sidecar)
    } else {
        "source-absent".to_owned()
    }
}

fn panel_init_failed(
    plugin_root: &Path,
    design: &Path,
    reason: &str,
    stderr: &str,
    runner: &dyn Step0Runner,
) -> VerbResult {
    let design_text = design.display().to_string();
    let child = run_larch(
        plugin_root,
        &[
            "plan-review",
            "prelaunch-failure",
            "--design-tmpdir",
            &design_text,
            "--reason",
            reason,
        ],
        &[],
        runner,
    );
    let mut out = VerbResult {
        code: ExitCode::from(1),
        stdout: child.stdout,
        stderr: format!("{stderr}{}", child.stderr),
    };
    emit(&mut out.stdout, SUMMARY_FAILED_JUDGE_PANEL);
    out
}

fn pause_save(
    plugin_root: &Path,
    design: &Path,
    issue: &str,
    repo: &str,
    runner: &dyn Step0Runner,
) -> ChildOutcome {
    let design_text = design.display().to_string();
    let mut args = vec![
        "design",
        "pause-save",
        "--design-tmpdir",
        design_text.as_str(),
        "--issue",
        issue,
    ];
    if !repo.is_empty() {
        args.extend(["--repo", repo]);
    }
    run_larch(plugin_root, &args, &[], runner)
}

fn timing_mark(plugin_root: &Path, label: &str, runner: &dyn Step0Runner) {
    let _ = run_larch(
        plugin_root,
        &["timing", "mark", label],
        &[("LARCH_TIMING_SKILL", "design")],
        runner,
    );
}

#[allow(clippy::too_many_lines)] // One Bash scope-anchor assembly, ported branch for branch.
fn write_scope_anchor(
    plugin_root: &Path,
    design: &Path,
    env: &Env,
    runner: &dyn Step0Runner,
) -> Result<(), VerbResult> {
    let design_text = design.display().to_string();
    let stripped = design.join(".plan-review-scope-stripped.txt");
    let issue_body = design.join("issue-body.txt");
    let had_issue_body = nonempty_regular(&issue_body);
    if had_issue_body {
        let issue_text = issue_body.display().to_string();
        let stripped_text = stripped.display().to_string();
        let child = run_larch(
            plugin_root,
            &[
                "plan-block",
                "strip-body",
                "--file",
                &issue_text,
                "--output",
                &stripped_text,
            ],
            &[],
            runner,
        );
        if child.code != 0 {
            let _ = fs::remove_file(&stripped);
            return Err(panel_init_failed(
                plugin_root,
                design,
                "strip-body-failure",
                "**⚠ Step 3: failed to strip prior larch:plan block from issue body; aborting before reviewer launch**\n",
                runner,
            ));
        }
    } else {
        let _ = fs::write(&stripped, "");
    }
    let mut body = String::new();
    let title = env_get(env, "ISSUE_TITLE", "");
    if !title.is_empty() {
        body.push('#');
        body.push(' ');
        body.push_str(title);
        body.push('\n');
        body.push('\n');
    }
    let stripped_text = fs::read_to_string(&stripped).unwrap_or_default();
    let _ = fs::remove_file(&stripped);
    if nonempty_after_strip(&stripped_text) {
        body.push_str(&stripped_text);
        if !stripped_text.ends_with('\n') {
            body.push('\n');
        }
    } else if !had_issue_body {
        let feature = design.join("feature-description.txt");
        if nonempty_regular(&feature) {
            let fd_stripped = design.join(".plan-review-scope-fd-stripped.txt");
            let feature_text = feature.display().to_string();
            let fd_text = fd_stripped.display().to_string();
            let child = run_larch(
                plugin_root,
                &[
                    "plan-block",
                    "strip-body",
                    "--file",
                    &feature_text,
                    "--output",
                    &fd_text,
                ],
                &[],
                runner,
            );
            if child.code == 0
                && nonempty_regular(&fd_stripped)
                && let Ok(text) = fs::read_to_string(&fd_stripped)
            {
                body.push_str(&text);
                if !text.ends_with('\n') {
                    body.push('\n');
                }
            }
            let _ = fs::remove_file(&fd_stripped);
        } else if env_get(env, "POSITIONAL_KIND", "") == "verbal" {
            let value = env_get(env, "POSITIONAL_VALUE", "");
            if !value.is_empty() {
                body.push_str(value);
                body.push('\n');
            }
        }
    }
    let outline = design.join("design-outline.md");
    if nonempty_regular(&outline) && design.join(".outline-approved").is_file() {
        body.push('\n');
        body.push_str("## Approved direction (outline)\n\n");
        if let Ok(text) = fs::read_to_string(&outline) {
            body.push_str(&text);
        }
    }
    let anchor = design.join("plan-review-scope-anchor.txt");
    if body.trim().is_empty() {
        let _ = fs::remove_file(&anchor);
        return Err(panel_init_failed(
            plugin_root,
            design,
            "scope-anchor-empty",
            "**⚠ Step 3: plan-review-scope-anchor.txt would be empty; aborting before reviewer launch**\n",
            runner,
        ));
    }
    if fs::write(&anchor, &body).is_err() {
        let _ = fs::remove_file(&anchor);
        return Err(panel_init_failed(
            plugin_root,
            design,
            "scope-staging-file-failure",
            "**⚠ Step 3: could not allocate plan-review scope anchor staging file; aborting before reviewer launch**\n",
            runner,
        ));
    }
    let anchor_text = anchor.display().to_string();
    let child = run_larch(
        plugin_root,
        &[
            "scope-anchor",
            "validate",
            "--mode",
            "design",
            "--design-tmpdir",
            &design_text,
            "--path",
            &anchor_text,
        ],
        &[],
        runner,
    );
    if child.code != 0 {
        return Err(panel_init_failed(
            plugin_root,
            design,
            "scope-anchor-validation-failure",
            "**⚠ Step 3: plan-review-scope-anchor.txt failed validation; aborting before reviewer launch**\n",
            runner,
        ));
    }
    Ok(())
}

const fn nonempty_after_strip(text: &str) -> bool {
    !text.is_empty()
}

fn step3_entry_with(arguments: &[OsString], runner: &dyn Step0Runner) -> VerbResult {
    let argv = utf8_arguments(arguments);
    let parsed = match parse_step3_entry(&argv) {
        Ok(parsed) => parsed,
        Err(error) => return error,
    };
    let env = wrapper_env(&parsed.session_env_path, &parsed.claude_pid, "");
    let plugin_root = match require_plugin(&env) {
        Ok(path) => path,
        Err(error) => return error,
    };
    let raw = env_get(&env, "DESIGN_TMPDIR", "");
    if raw.is_empty() {
        return VerbResult::fail(1, "/design Step 3 entry: DESIGN_TMPDIR required\n");
    }
    let validate = run_larch(
        &plugin_root,
        &["session", "validate-design-tmpdir", raw],
        &[],
        runner,
    );
    if validate.code != 0 {
        let mut out = VerbResult::from_code(2);
        push_child(&mut out, &validate);
        if out.code == ExitCode::SUCCESS {
            out.code = ExitCode::from(2);
        }
        return out;
    }
    let design = resolve_design_tmpdir(raw);
    if parsed.reentry {
        touch(&design.join(".step3-reentry"));
        let _ = fs::remove_file(design.join("oos-aggregate-pool.md"));
    }
    let _ = fs::remove_file(design.join(".pause-save-complete"));
    let design_text = design.display().to_string();
    let state = run_larch(
        &plugin_root,
        &[
            "plan-review",
            "step3-entry-state",
            "--session-env-path",
            &parsed.session_env_path,
            "--claude-pid",
            &parsed.claude_pid,
        ],
        &[],
        runner,
    );
    let mut out = VerbResult::from_code(state.code);
    push_child(&mut out, &state);
    if state.code != 0 {
        return out;
    }
    if design.join(".pause-save-complete").is_file() {
        return out;
    }
    let snapshot = run_larch(
        &plugin_root,
        &[
            "plan-review",
            "snapshot-pre-review",
            "--design-tmpdir",
            &design_text,
        ],
        &[],
        runner,
    );
    if snapshot.code != 0 {
        return panel_init_failed(
            &plugin_root,
            &design,
            "snapshot-pre-review-failure",
            "**⚠ Step 3: failed to snapshot plan.txt before reviewer launch**\n",
            runner,
        );
    }
    if let Err(error) = write_scope_anchor(&plugin_root, &design, &env, runner) {
        return error;
    }
    let preview = run_larch(
        &plugin_root,
        &[
            "plan-review",
            "step3-entry-preview",
            "--session-env-path",
            &parsed.session_env_path,
            "--claude-pid",
            &parsed.claude_pid,
        ],
        &[],
        runner,
    );
    push_child(&mut out, &preview);
    out.code = exit_from_i32(preview.code);
    out
}

/// Combined `/design` Step 3 entry: state reset, scope-anchor, preview.
pub fn step3_entry(arguments: &[OsString]) -> ExitCode {
    publish(&step3_entry_with(arguments, &LiveStep0Runner))
}

fn gate_b_with(arguments: &[OsString], runner: &dyn Step0Runner) -> VerbResult {
    let argv = utf8_arguments(arguments);
    let parsed = match parse_gate_b(&argv) {
        Ok(parsed) => parsed,
        Err(error) => return error,
    };
    let env = wrapper_env(
        &parsed.session_env_path,
        &parsed.claude_pid,
        &parsed.plugin_root,
    );
    let plugin_root = match require_plugin(&env) {
        Ok(path) => path,
        Err(error) => return error,
    };
    let design = match validate_tmpdir(
        env_get(&env, "DESIGN_TMPDIR", ""),
        "/design wrapper: DESIGN_TMPDIR required",
        GATE_B_PROGRAM,
    ) {
        Ok(path) => path,
        Err(error) => return error,
    };
    let _ = fs::create_dir_all(design.join(".completed"));
    let mut out = VerbResult::from_code(0);
    match parsed.review_loop_status.as_str() {
        "postplan-failed" => {
            emit(
                &mut out.stdout,
                "⏩ 3.5: Gate B — aborted (STEP3_REVIEW_LOOP_STATUS=postplan-failed)",
            );
        }
        status if APPLY_LOOP_STATUSES.contains(&status) => {
            touch(&design.join(".completed/step-3"));
        }
        "" => {
            if COMPLETE_LOOP_STATUSES.contains(&parsed.loop_status.as_str()) {
                touch(&design.join(".completed/step-3"));
            } else {
                let review = if parsed.review_loop_status.is_empty() {
                    "unset"
                } else {
                    parsed.review_loop_status.as_str()
                };
                let loop_status = if parsed.loop_status.is_empty() {
                    "unset"
                } else {
                    parsed.loop_status.as_str()
                };
                emit(
                    &mut out.stdout,
                    &format!(
                        "⏩ 3.5: Gate B — skipped (STEP3_REVIEW_LOOP_STATUS={review}, LOOP_STATUS={loop_status})"
                    ),
                );
            }
        }
        status => {
            emit(
                &mut out.stdout,
                &format!("⏩ 3.5: Gate B — skipped (loop envelope {status})"),
            );
        }
    }
    if design.join(".pause-requested").is_file() {
        let pause = pause_save(
            &plugin_root,
            &design,
            env_get(&env, "ISSUE_NUMBER", ""),
            env_get(&env, "REPO", ""),
            runner,
        );
        push_child(&mut out, &pause);
        out.code = exit_from_i32(pause.code);
        return out;
    }
    timing_mark(&plugin_root, "design Step 3.5 — gate B", runner);
    let approve = json_bool(&design.join("run-params.json"), "approve_requested");
    emit(
        &mut out.stdout,
        &format!(
            "APPROVE_REQUESTED={}",
            if approve { "true" } else { "false" }
        ),
    );
    out
}

/// Gate B completion marker and `APPROVE_REQUESTED=` row.
pub fn gate_b(arguments: &[OsString]) -> ExitCode {
    publish(&gate_b_with(arguments, &LiveStep0Runner))
}

fn resolve_session(
    plugin_root: &Path,
    session_env_path: &str,
    claude_pid: &str,
    runner: &dyn Step0Runner,
) -> Result<Env, VerbResult> {
    if session_env_path.is_empty() {
        return Ok(wrapper_env(
            "",
            claude_pid,
            &plugin_root.display().to_string(),
        ));
    }
    let mut args = vec![
        "bgjob",
        "adapt",
        "--resolve-session-env",
        "--session-env-path",
        session_env_path,
    ];
    if !claude_pid.is_empty() {
        args.extend(["--owner-pid", claude_pid]);
    }
    let child = run_larch(plugin_root, &args, &[], runner);
    if child.code != 0 {
        let stdout = if child.stdout.is_empty() {
            "BGJOB_ERROR=session-env-resolution-failed\n".to_owned()
        } else {
            child.stdout
        };
        return Err(VerbResult {
            code: ExitCode::from(2),
            stdout,
            stderr: child.stderr,
        });
    }
    Ok(wrapper_env(
        session_env_path,
        claude_pid,
        &plugin_root.display().to_string(),
    ))
}

fn publish_step4_result(
    plugin_root: &Path,
    design: &Path,
    merge_env: &Path,
    status: &str,
    skip_gatec: bool,
    runner: &dyn Step0Runner,
) -> ChildOutcome {
    let merge_text = merge_env.display().to_string();
    let design_text = design.display().to_string();
    let skip = if skip_gatec { "true" } else { "false" };
    let rejected = design.join("gatec-rejected-findings-framed.md");
    let preview = design.join("gatec-preview.md");
    let rejected_text = rejected.display().to_string();
    let preview_text = preview.display().to_string();
    let digest = design.join("dialectic-clarifier-digest.md");
    let digest_row = format!("DIALECTIC_GATEC_DIGEST_PATH={}", digest.display());
    let status_row = format!("STEP4_STATUS={status}");
    let skip_row = format!("SKIP_APPROVE_REQUESTED_GATEC={skip}");
    let begin_row = format!("REJECTED_FINDINGS_BEGIN={REJECTED_BEGIN}");
    let end_row = format!("REJECTED_FINDINGS_END={REJECTED_END}");
    let body_row = format!("REJECTED_FINDINGS_BODY_PATH={rejected_text}");
    let preview_row = format!("GATEC_PREVIEW_PATH={preview_text}");
    let mut args = vec![
        "bgjob",
        "write-merge-result-env",
        "--path",
        merge_text.as_str(),
        "--tmpdir",
        design_text.as_str(),
        "--row",
        status_row.as_str(),
        "--row",
        skip_row.as_str(),
        "--row",
        begin_row.as_str(),
        "--row",
        end_row.as_str(),
        "--row",
        body_row.as_str(),
        "--row",
        preview_row.as_str(),
    ];
    if digest.is_file() && !digest.is_symlink() {
        args.extend(["--row", digest_row.as_str()]);
    }
    run_larch(plugin_root, &args, &[], runner)
}

fn write_rejected_body(
    plugin_root: &Path,
    design: &Path,
    runner: &dyn Step0Runner,
) -> Result<(), i32> {
    let mut body = String::new();
    emit(&mut body, REJECTED_BEGIN);
    let rejected = design.join("rejected-findings.md");
    if nonempty_regular(&rejected) {
        let design_text = design.display().to_string();
        let framed = run_larch(
            plugin_root,
            &[
                "plan-review",
                "emit-rejected",
                "--design-tmpdir",
                &design_text,
                "--report-framing",
            ],
            &[],
            runner,
        );
        if framed.code == 0 {
            body.push_str(&framed.stdout);
        } else {
            emit(&mut body, REJECTED_FALLBACK_HEADING);
            body.push('\n');
            emit(&mut body, REJECTED_FALLBACK_BODY);
            body.push('\n');
            let fallback = run_larch(
                plugin_root,
                &[
                    "plan-review",
                    "emit-rejected",
                    "--design-tmpdir",
                    &design_text,
                ],
                &[],
                runner,
            );
            body.push_str(&fallback.stdout);
        }
    }
    emit(&mut body, REJECTED_END);
    fs::write(design.join("gatec-rejected-findings-framed.md"), body).map_err(|_error| 1)
}

#[allow(clippy::too_many_lines)] // One Bash Step 4 child, ported branch for branch.
fn step4_tail_child(
    plugin_root: &Path,
    design: &Path,
    env: &Env,
    merge_env: &Path,
    runner: &dyn Step0Runner,
) -> VerbResult {
    let mut skip_gatec = false;
    if design.join(".pause-requested").is_file() {
        let pause = pause_save(
            plugin_root,
            design,
            env_get(env, "ISSUE_NUMBER", ""),
            env_get(env, "REPO", ""),
            runner,
        );
        let mut out = VerbResult::from_code(pause.code);
        push_child(&mut out, &pause);
        if pause.code != 0 {
            return out;
        }
        let published = publish_step4_result(
            plugin_root,
            design,
            merge_env,
            "pause-save",
            skip_gatec,
            runner,
        );
        push_child(&mut out, &published);
        out.code = exit_from_i32(published.code);
        return out;
    }
    timing_mark(plugin_root, "design Step 4 — rejected findings", runner);
    let mut out = VerbResult::from_code(0);
    if !design.join(".completed/finalize").is_file() {
        let design_text = design.display().to_string();
        let finalize = run_larch_stdin(
            plugin_root,
            &["design", "driver", "--design-tmpdir", &design_text],
            "ACTION=FINALIZE\n",
            &[],
        );
        push_child(&mut out, &finalize);
        if finalize.code != 0 {
            out.code = exit_from_i32(finalize.code);
            emit(
                &mut out.stdout,
                "**⚠ FINALIZE failed; repair the missing artifact before Step 5.**",
            );
            return out;
        }
    }
    if write_rejected_body(plugin_root, design, runner).is_err() {
        return VerbResult::from_code(1);
    }
    if design.join(".pause-requested").is_file() {
        let pause = pause_save(
            plugin_root,
            design,
            env_get(env, "ISSUE_NUMBER", ""),
            env_get(env, "REPO", ""),
            runner,
        );
        push_child(&mut out, &pause);
        if pause.code != 0 {
            out.code = exit_from_i32(pause.code);
            return out;
        }
        let published = publish_step4_result(
            plugin_root,
            design,
            merge_env,
            "pause-save",
            skip_gatec,
            runner,
        );
        push_child(&mut out, &published);
        out.code = exit_from_i32(published.code);
        return out;
    }
    timing_mark(plugin_root, "design Step 4b — gate C", runner);
    skip_gatec = json_bool(&design.join("run-params.json"), "skip_approve_requested");
    let design_text = design.display().to_string();
    let dialectic = run_larch(
        plugin_root,
        &["design", "dialectic-gatec", "--design-tmpdir", &design_text],
        &[],
        runner,
    );
    push_child(&mut out, &dialectic);
    if dialectic.code != 0 {
        out.code = exit_from_i32(dialectic.code);
        return out;
    }
    let _ = fs::create_dir_all(design.join(".completed"));
    touch(&design.join(".completed/dialectic-gatec-terminal"));
    let preview = run_larch(
        plugin_root,
        &[
            "plan-review",
            "preview",
            "--design-tmpdir",
            &design_text,
            "--variant",
            "gatec",
        ],
        &[],
        runner,
    );
    if preview.code != 0 {
        push_child(&mut out, &preview);
        out.code = exit_from_i32(preview.code);
        return out;
    }
    if fs::write(design.join("gatec-preview.md"), &preview.stdout).is_err() {
        return VerbResult::from_code(1);
    }
    if design.join(".pause-save-complete").is_file() {
        let published = publish_step4_result(
            plugin_root,
            design,
            merge_env,
            "pause-save",
            skip_gatec,
            runner,
        );
        push_child(&mut out, &published);
        out.code = exit_from_i32(published.code);
        return out;
    }
    let _ = fs::create_dir_all(design.join(".completed"));
    touch(&design.join(".completed/step-4"));
    let published = publish_step4_result(
        plugin_root,
        design,
        merge_env,
        "complete",
        skip_gatec,
        runner,
    );
    push_child(&mut out, &published);
    out.code = exit_from_i32(published.code);
    out
}

fn step4_tail_launch(
    plugin_root: &Path,
    design: &Path,
    env: &Env,
    parsed: &Step4TailArgs,
    runner: &dyn Step0Runner,
) -> VerbResult {
    let _ = fs::remove_file(design.join(".pause-save-complete"));
    if design.join(".pause-requested").is_file() {
        let pause = pause_save(
            plugin_root,
            design,
            env_get(env, "ISSUE_NUMBER", ""),
            env_get(env, "REPO", ""),
            runner,
        );
        let mut out = VerbResult::from_code(pause.code);
        push_child(&mut out, &pause);
        return out;
    }
    let fingerprint = input_fingerprint(design);
    let design_text = design.display().to_string();
    let entry = entrypoint(plugin_root);
    let entry_text = entry.display().to_string();
    let mut args = vec![
        "bgjob".to_owned(),
        "adapt".to_owned(),
        "--step".to_owned(),
        STEP4_TAIL_STEP.to_owned(),
        "--tmpdir".to_owned(),
        design_text,
        "--budget-s".to_owned(),
        STEP4_TAIL_BUDGET_S.to_owned(),
    ];
    if !parsed.claude_pid.is_empty() {
        args.extend(["--owner-pid".to_owned(), parsed.claude_pid.clone()]);
    }
    if !parsed.session_env_path.is_empty() {
        args.extend([
            "--session-env-path".to_owned(),
            parsed.session_env_path.clone(),
        ]);
    }
    args.extend([
        "--input-fingerprint".to_owned(),
        fingerprint,
        "--".to_owned(),
        entry_text,
        "design".to_owned(),
        "step4-tail".to_owned(),
    ]);
    args.extend(parsed.core.iter().cloned());
    let owned: Vec<&str> = args.iter().map(String::as_str).collect();
    let child = run_larch(plugin_root, &owned, &[], runner);
    let mut out = VerbResult::from_code(child.code);
    push_child(&mut out, &child);
    out
}

fn step4_tail_with(arguments: &[OsString], runner: &dyn Step0Runner) -> VerbResult {
    let (child, merge_result_env, core_os) = match parse_child_suffix(arguments) {
        Ok(parsed) => parsed,
        Err(error) => return error,
    };
    let core = utf8_arguments(core_os);
    let (session_env_path, claude_pid, plugin_root_flag) = match parse_step4_tail(&core) {
        Ok(parsed) => parsed,
        Err(error) => return error,
    };
    let plugin_root_value = if plugin_root_flag.is_empty() {
        std::env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default()
    } else {
        plugin_root_flag
    };
    let plugin_root = match require_plugin_root(&plugin_root_value) {
        Ok(path) => path,
        Err(exit) => return result_from_exit(exit),
    };
    let env = match resolve_session(&plugin_root, &session_env_path, &claude_pid, runner) {
        Ok(env) => env,
        Err(error) => return error,
    };
    let raw = env_get(&env, "DESIGN_TMPDIR", "");
    let design = match validate_tmpdir(
        raw,
        "design-step3b-tail.sh: DESIGN_TMPDIR required",
        STEP4_TAIL_PROGRAM,
    ) {
        Ok(path) => path,
        Err(error) => return error,
    };
    let validate = run_larch(
        &plugin_root,
        &[
            "session",
            "validate-design-tmpdir",
            &design.display().to_string(),
        ],
        &[],
        runner,
    );
    if validate.code != 0 {
        let mut out = VerbResult::from_code(2);
        push_child(&mut out, &validate);
        return out;
    }
    let parsed = Step4TailArgs {
        session_env_path,
        claude_pid,
        child,
        merge_result_env,
        core,
    };
    if parsed.child {
        step4_tail_child(
            &plugin_root,
            &design,
            &env,
            &parsed.merge_result_env,
            runner,
        )
    } else {
        step4_tail_launch(&plugin_root, &design, &env, &parsed, runner)
    }
}

/// Step 4 rejected-findings / Gate C preview tail, including bgjob adapt launch.
pub fn step4_tail(arguments: &[OsString]) -> ExitCode {
    publish(&step4_tail_with(arguments, &LiveStep0Runner))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::{Path, PathBuf};

    struct FakeSeam {
        design: PathBuf,
        last_adapt: std::rc::Rc<std::sync::Mutex<Vec<String>>>,
    }

    impl FakeSeam {
        fn new(design: &Path) -> Self {
            Self {
                design: design.to_path_buf(),
                last_adapt: std::rc::Rc::new(std::sync::Mutex::new(Vec::new())),
            }
        }

        fn ok() -> ChildOutcome {
            ChildOutcome {
                code: 0,
                stdout: String::new(),
                stderr: String::new(),
            }
        }

        fn strip(source: &Path, dest: &Path) {
            let text = fs::read_to_string(source).unwrap_or_default();
            let mut out = String::new();
            let mut inside = false;
            for line in text.lines() {
                if line == "<!-- larch:plan:start -->" {
                    inside = true;
                    continue;
                }
                if line == "<!-- larch:plan:end -->" {
                    inside = false;
                    continue;
                }
                if !inside {
                    out.push_str(line);
                    out.push('\n');
                }
            }
            let _ = fs::write(dest, out);
        }
    }

    impl Step3Seam for FakeSeam {
        #[allow(clippy::too_many_lines)] // Offline larch.sh dispatch table for the three verbs.
        fn larch(&self, args: &[String], _env: &[(String, String)]) -> ChildOutcome {
            let head = (
                args.first().map(String::as_str),
                args.get(1).map(String::as_str),
            );
            match head {
                (Some("session"), Some("validate-design-tmpdir"))
                | (Some("plan-review"), Some("step3-entry-state" | "step3-entry-preview"))
                | (Some("design"), Some("dialectic-gatec"))
                | (Some("timing"), Some("mark"))
                | (Some("scope-anchor"), Some("validate")) => Self::ok(),
                (Some("plan-review"), Some("snapshot-pre-review")) => {
                    let _ = fs::copy(
                        self.design.join("plan.txt"),
                        self.design.join("plan-before-review.txt"),
                    );
                    ChildOutcome {
                        code: 0,
                        stdout: "SNAPSHOT_PRE_REVIEW_STATUS=ok\n".to_owned(),
                        stderr: String::new(),
                    }
                }
                (Some("plan-block"), Some("strip-body")) => {
                    let file = flag_value(args, "--file").unwrap_or("");
                    let output = flag_value(args, "--output").unwrap_or("");
                    Self::strip(Path::new(file), Path::new(output));
                    Self::ok()
                }
                (Some("plan-review"), Some("prelaunch-failure")) => ChildOutcome {
                    code: 0,
                    stdout: "STEP3_REVIEW_LOOP_STATUS=panel-init-failed\n".to_owned(),
                    stderr: String::new(),
                },
                (Some("design"), Some("pause-save")) => {
                    let _ = fs::write(self.design.join(".pause-save-complete"), "");
                    Self::ok()
                }
                (Some("design"), Some("driver")) => {
                    touch(&self.design.join(".completed/finalize"));
                    Self::ok()
                }
                (Some("plan-review"), Some("emit-rejected")) => ChildOutcome {
                    code: 0,
                    stdout: "rejected body\n".to_owned(),
                    stderr: String::new(),
                },
                (Some("plan-review"), Some("preview")) => ChildOutcome {
                    code: 0,
                    stdout: "preview\n".to_owned(),
                    stderr: String::new(),
                },
                (Some("bgjob"), Some("write-merge-result-env")) => {
                    let path = flag_value(args, "--path").unwrap_or("");
                    let mut body = String::new();
                    let mut index = 0;
                    while index < args.len() {
                        if args[index] == "--row" {
                            if let Some(row) = args.get(index + 1) {
                                body.push_str(row);
                                body.push('\n');
                            }
                            index += 2;
                        } else {
                            index += 1;
                        }
                    }
                    let _ = fs::create_dir_all(
                        Path::new(path).parent().unwrap_or_else(|| Path::new(".")),
                    );
                    let _ = fs::write(path, body);
                    ChildOutcome {
                        code: 0,
                        stdout: String::new(),
                        stderr: String::new(),
                    }
                }
                (Some("bgjob"), Some("adapt")) => {
                    if args.iter().any(|arg| arg == "--resolve-session-env") {
                        let path = flag_value(args, "--session-env-path").unwrap_or("");
                        return ChildOutcome {
                            code: 0,
                            stdout: fs::read_to_string(path).unwrap_or_default(),
                            stderr: String::new(),
                        };
                    }
                    if let Ok(mut last) = self.last_adapt.lock() {
                        *last = args.to_vec();
                    }
                    ChildOutcome {
                        code: 0,
                        stdout: "BGJOB_STATUS=STARTED STEP=design-step4-tail PGID=12345\n"
                            .to_owned(),
                        stderr: String::new(),
                    }
                }
                _ => ChildOutcome {
                    code: 2,
                    stdout: String::new(),
                    stderr: format!("unexpected larch command: {args:?}\n"),
                },
            }
        }
    }

    struct SeamGuard;

    impl SeamGuard {
        fn install(seam: FakeSeam) -> Self {
            TEST_SEAM.with(|cell| *cell.borrow_mut() = Some(std::rc::Rc::new(seam)));
            Self
        }
    }

    impl Drop for SeamGuard {
        fn drop(&mut self) {
            TEST_SEAM.with(|cell| *cell.borrow_mut() = None);
        }
    }

    fn design_dir() -> (tempfile::TempDir, PathBuf) {
        let temp = tempfile::TempDir::new().expect("tempdir");
        let design = temp.path().join("design");
        fs::create_dir_all(design.join(".completed")).expect("design dir");
        (temp, design)
    }

    fn source_env(design: &Path, extra: &[(&str, &str)]) -> PathBuf {
        let path = design.join("session-env.sh");
        let mut text = format!(
            "DESIGN_TMPDIR={}\nCLAUDE_PLUGIN_ROOT={}\nISSUE_NUMBER=9\n",
            design.display(),
            std::env::current_dir()
                .unwrap_or_else(|_| PathBuf::from("/tmp"))
                .display(),
        );
        for (key, value) in extra {
            text.push_str(key);
            text.push('=');
            text.push_str(value);
            text.push('\n');
        }
        fs::write(&path, text).expect("session env");
        path
    }

    fn plugin_root() -> String {
        std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("/tmp"))
            .display()
            .to_string()
    }

    fn step3_args(env: &Path) -> Vec<OsString> {
        vec!["--session-env-path".into(), env.as_os_str().into()]
    }

    fn entry_args(env: &Path) -> Vec<OsString> {
        vec![
            "--session-env-path".into(),
            env.as_os_str().into(),
            "--plugin-root".into(),
            plugin_root().into(),
        ]
    }

    #[test]
    fn step3_entry_writes_scope_anchor_from_stripped_issue_body() {
        let (_temp, design) = design_dir();
        fs::write(design.join("plan.txt"), "plan body\n").unwrap();
        fs::write(design.join(".step3-entry-plan-printed"), "").unwrap();
        fs::write(
            design.join("issue-body.txt"),
            "Feature request text\n<!-- larch:plan:start -->\nold plan\n<!-- larch:plan:end -->\n",
        )
        .unwrap();
        let env = source_env(&design, &[]);
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let result = step3_entry_with(&step3_args(&env), &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        let anchor = fs::read_to_string(design.join("plan-review-scope-anchor.txt")).unwrap();
        assert!(anchor.contains("Feature request text"));
        assert!(!anchor.contains("old plan"));
    }

    #[test]
    fn step3_reentry_resets_stale_oos_aggregate_pool() {
        let (_temp, design) = design_dir();
        fs::write(design.join("plan.txt"), "plan body\n").unwrap();
        fs::write(
            design.join("oos-aggregate-pool.md"),
            "stale aggregate pool\n",
        )
        .unwrap();
        fs::write(design.join("issue-body.txt"), "Feature request text\n").unwrap();
        let env = source_env(&design, &[]);
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let mut args = step3_args(&env);
        args.push("--reentry".into());
        let result = step3_entry_with(&args, &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        assert!(!design.join("oos-aggregate-pool.md").exists());
        assert!(design.join(".step3-reentry").is_file());
    }

    #[test]
    fn step3_entry_aborts_empty_stripped_body_without_feature_description_fallback() {
        let (_temp, design) = design_dir();
        fs::write(design.join("plan.txt"), "plan body\n").unwrap();
        fs::write(
            design.join("issue-body.txt"),
            "<!-- larch:plan:start -->\nold plan only\n<!-- larch:plan:end -->\n",
        )
        .unwrap();
        fs::write(
            design.join("feature-description.txt"),
            "raw feature-description with plan\n",
        )
        .unwrap();
        let env = source_env(&design, &[]);
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let result = step3_entry_with(&step3_args(&env), &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::from(1));
        assert!(result.stdout.contains(SUMMARY_FAILED_JUDGE_PANEL));
        assert!(
            result
                .stdout
                .contains("STEP3_REVIEW_LOOP_STATUS=panel-init-failed")
        );
        if let Ok(anchor) = fs::read_to_string(design.join("plan-review-scope-anchor.txt")) {
            assert!(!anchor.contains("raw feature-description"));
        }
    }

    #[test]
    fn step3_entry_rejects_plugin_root_flag() {
        let result = step3_entry_with(&["--plugin-root".into(), "/tmp".into()], &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::from(2));
        assert!(result.stderr.contains("unknown argument: --plugin-root"));
    }

    #[test]
    fn gate_b_writes_step3_and_approve_requested() {
        let (_temp, design) = design_dir();
        fs::write(
            design.join("run-params.json"),
            "{\"approve_requested\":true}\n",
        )
        .unwrap();
        let env = source_env(&design, &[]);
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let mut args = entry_args(&env);
        args.extend([
            "--step3-review-loop-status".into(),
            "main-agent-apply-required".into(),
        ]);
        let result = gate_b_with(&args, &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        assert!(design.join(".completed/step-3").is_file());
        assert!(result.stdout.contains("APPROVE_REQUESTED=true"));
    }

    #[test]
    fn gate_b_skips_unknown_loop_status() {
        let (_temp, design) = design_dir();
        fs::write(design.join("run-params.json"), "{}\n").unwrap();
        let env = source_env(&design, &[]);
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let mut args = entry_args(&env);
        args.extend([
            "--step3-review-loop-status".into(),
            "".into(),
            "--loop-status".into(),
            "mystery".into(),
        ]);
        let result = gate_b_with(&args, &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        assert!(!design.join(".completed/step-3").exists());
        assert!(result.stdout.contains(
            "⏩ 3.5: Gate B — skipped (STEP3_REVIEW_LOOP_STATUS=unset, LOOP_STATUS=mystery)"
        ));
        assert!(result.stdout.contains("APPROVE_REQUESTED=false"));
    }

    #[test]
    fn step4_tail_child_publishes_complete_envelope() {
        let (_temp, design) = design_dir();
        fs::write(design.join(".completed/finalize"), "").unwrap();
        fs::write(
            design.join("run-params.json"),
            "{\"skip_approve_requested\":false}\n",
        )
        .unwrap();
        fs::write(design.join("dialectic-clarifier-digest.md"), "digest\n").unwrap();
        let env = source_env(&design, &[]);
        let merge = design.join("merge.env");
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let mut args = entry_args(&env);
        args.extend([
            "--bgjob-child".into(),
            "--merge-result-env".into(),
            merge.as_os_str().into(),
        ]);
        let result = step4_tail_with(&args, &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        let body = fs::read_to_string(&merge).unwrap();
        assert!(body.contains("STEP4_STATUS=complete"));
        assert!(body.contains("SKIP_APPROVE_REQUESTED_GATEC=false"));
        assert!(body.contains(&format!("REJECTED_FINDINGS_BEGIN={REJECTED_BEGIN}")));
        assert!(body.contains(&format!("REJECTED_FINDINGS_END={REJECTED_END}")));
        assert!(
            body.contains("REJECTED_FINDINGS_BODY_PATH=")
                && body.contains("gatec-rejected-findings-framed.md")
        );
        assert!(body.contains("GATEC_PREVIEW_PATH=") && body.contains("gatec-preview.md"));
        assert!(
            body.contains("DIALECTIC_GATEC_DIGEST_PATH=")
                && body.contains("dialectic-clarifier-digest.md")
        );
        assert!(design.join(".completed/step-4").is_file());
    }

    #[test]
    fn step4_tail_pause_race_publishes_pause_save() {
        let (_temp, design) = design_dir();
        fs::write(design.join(".completed/finalize"), "").unwrap();
        fs::write(design.join("run-params.json"), "{}\n").unwrap();
        fs::write(design.join(".pause-requested"), "").unwrap();
        let env = source_env(&design, &[]);
        let merge = design.join("merge.env");
        let _guard = SeamGuard::install(FakeSeam::new(&design));
        let mut args = entry_args(&env);
        args.extend([
            "--bgjob-child".into(),
            "--merge-result-env".into(),
            merge.as_os_str().into(),
        ]);
        let result = step4_tail_with(&args, &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        let body = fs::read_to_string(&merge).unwrap();
        assert!(body.contains("STEP4_STATUS=pause-save"));
    }

    #[test]
    fn step4_tail_launcher_passes_fingerprint_and_step() {
        let (_temp, design) = design_dir();
        fs::write(
            design.join(".step3-review-result.env"),
            "LOOP_STATUS=complete\n",
        )
        .unwrap();
        let env = source_env(&design, &[]);
        let seam = FakeSeam::new(&design);
        let last_adapt = seam.last_adapt.clone();
        let expected = sha256_file(&design.join(".step3-review-result.env"));
        let _guard = SeamGuard::install(seam);
        let result = step4_tail_with(&entry_args(&env), &LiveStep0Runner);
        assert_eq!(result.code, ExitCode::SUCCESS);
        assert!(
            result
                .stdout
                .contains("BGJOB_STATUS=STARTED STEP=design-step4-tail PGID=12345")
        );
        let adapt = last_adapt.lock().expect("adapt argv").clone();
        assert!(
            adapt
                .windows(2)
                .any(|pair| pair[0] == "--step" && pair[1] == STEP4_TAIL_STEP)
        );
        assert!(
            adapt
                .windows(2)
                .any(|pair| pair[0] == "--budget-s" && pair[1] == STEP4_TAIL_BUDGET_S)
        );
        assert!(
            adapt
                .windows(2)
                .any(|pair| { pair[0] == "--input-fingerprint" && pair[1] == expected })
        );
        assert!(
            adapt
                .windows(2)
                .any(|pair| pair[0] == "design" && pair[1] == "step4-tail")
        );
    }

    #[test]
    fn step4_tail_rejects_child_controls_in_the_middle() {
        let result = step4_tail_with(
            &[
                "--bgjob-child".into(),
                "--session-env-path".into(),
                "x".into(),
                "--merge-result-env".into(),
                "y".into(),
            ],
            &LiveStep0Runner,
        );
        assert_eq!(result.code, ExitCode::from(2));
        assert!(
            result
                .stderr
                .contains("adapter child controls must be one terminal suffix")
        );
    }
}
