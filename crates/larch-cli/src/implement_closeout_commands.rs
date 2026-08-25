//! Rust owners for the `/implement` Step 16 and Step 17 closeout checkpoints.
//!
//! The four compatibility commands keep the retired Python owner's forgiving
//! closeout behavior: rejected-finding replay and Slack notification are best
//! effort, Step 17 protects a prior summary while refreshing it, and the
//! combined command always hands control to Step 18 after recording failures.
//! Sibling Rust verbs remain child processes through the verified
//! `scripts/larch.sh` bootstrap so their output can be captured in the same
//! wire files as before the cutover.

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    assert_no_symlink_path_or_ancestors, remove_optional_file, write_confined_file,
};
use larch_core::{
    ChildEnvironment, LARCH_SLACK_WEBHOOK_URL, ProcessOutput, implement::first_kv_value,
};

use crate::{
    argparse_compat::{ParsedCommandLine, parse_required_with_help},
    design_step1_commands::append_failure_args,
    implement_child_seam::resolve_plugin_root,
    implement_dispatch_commands::run_verified_larch_env_in,
};

const SUMMARY_BEGIN: &str = "---LARCH-SUMMARY-FINAL-BEGIN---";
const SUMMARY_END: &str = "---LARCH-SUMMARY-FINAL-END---";

const STEP16_PROG: &str = "cli.py implement step-16";
const STEP16_USAGE: &str =
    "usage: cli.py implement step-16 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]";
const STEP16_HELP: &str = "usage: cli.py implement step-16 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR";

const STEP16_16A_PROG: &str = "cli.py implement step-16-16a";
const STEP16_16A_USAGE: &str =
    "usage: cli.py implement step-16-16a [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]";
const STEP16_16A_HELP: &str = "usage: cli.py implement step-16-16a [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR";

const STEP16_17_PROG: &str = "cli.py implement step-16-17";
const STEP16_17_USAGE: &str =
    "usage: cli.py implement step-16-17 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]";
const STEP16_17_HELP: &str = "usage: cli.py implement step-16-17 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR";

const STEP17_PROG: &str = "cli.py implement step-17";
const STEP17_USAGE: &str = "usage: cli.py implement step-17 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                [--no-print-stdout]";
const STEP17_HELP: &str = "usage: cli.py implement step-17 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                [--no-print-stdout]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --no-print-stdout";

const INTERNAL_ERROR: i32 = 1;

struct CloseoutContext {
    tmpdir: PathBuf,
    plugin_root: PathBuf,
    working_directory: PathBuf,
    child_environment: Vec<(ChildEnvironment, OsString)>,
}

impl CloseoutContext {
    fn run(&self, arguments: impl IntoIterator<Item = OsString>) -> Result<ProcessOutput, String> {
        self.run_with_environment(arguments, &[])
    }

    fn run_with_environment(
        &self,
        arguments: impl IntoIterator<Item = OsString>,
        extra_environment: &[(ChildEnvironment, OsString)],
    ) -> Result<ProcessOutput, String> {
        let arguments: Vec<OsString> = arguments.into_iter().collect();
        let mut environment = self.child_environment.clone();
        environment.extend_from_slice(extra_environment);
        run_verified_larch_env_in(
            &self.working_directory,
            &self.plugin_root,
            &arguments,
            &environment,
        )
    }
}

fn parse(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    help: &str,
    flags: &[&'static str],
) -> Result<ParsedCommandLine, ExitCode> {
    parse_required_with_help(
        arguments,
        program,
        usage,
        help,
        &["--implement-tmpdir"],
        flags,
        &[],
    )
}

fn resolve_tmpdir(parsed: &ParsedCommandLine) -> Result<PathBuf, ExitCode> {
    let raw = parsed
        .value("--implement-tmpdir")
        .filter(|value| !value.is_empty())
        .map(OsStr::to_owned)
        .or_else(|| env::var_os("IMPLEMENT_TMPDIR").filter(|value| !value.is_empty()));
    let Some(raw) = raw else {
        eprintln!("IMPLEMENT_TMPDIR required");
        return Err(ExitCode::from(2));
    };
    Ok(PathBuf::from(raw))
}

fn context(parsed: &ParsedCommandLine) -> Result<CloseoutContext, ExitCode> {
    let tmpdir = resolve_tmpdir(parsed)?;
    let plugin_root = closeout_plugin_root(&tmpdir).map_err(|_error| {
        eprintln!(
            "**❌ /implement closeout: cannot resolve CLAUDE_PLUGIN_ROOT/scripts/larch.sh.**"
        );
        ExitCode::from(2)
    })?;
    let entrypoint = plugin_root.join("scripts/larch.sh");
    if !entrypoint.is_file()
        || entrypoint.is_symlink()
        || assert_no_symlink_path_or_ancestors(&entrypoint).is_err()
    {
        eprintln!(
            "**❌ /implement closeout: cannot resolve CLAUDE_PLUGIN_ROOT/scripts/larch.sh.**"
        );
        return Err(ExitCode::from(2));
    }
    let working_directory = env::current_dir().unwrap_or_else(|_| plugin_root.clone());
    Ok(CloseoutContext {
        child_environment: closeout_child_environment(&tmpdir),
        tmpdir,
        plugin_root,
        working_directory,
    })
}

fn read_key(path: &Path, key: &str, default: &str) -> String {
    let value = if assert_no_symlink_path_or_ancestors(path).is_ok() {
        fs::read(path)
            .ok()
            .and_then(|bytes| first_kv_value(&String::from_utf8_lossy(&bytes), key))
            .unwrap_or_else(|| default.to_owned())
    } else {
        default.to_owned()
    };
    let value = value.trim();
    if value.is_empty() {
        default.to_owned()
    } else {
        value.to_owned()
    }
}

fn closeout_plugin_root(tmpdir: &Path) -> Result<PathBuf, String> {
    if env::var_os("CLAUDE_PLUGIN_ROOT").is_some_and(|value| !value.is_empty()) {
        return resolve_plugin_root();
    }
    let recorded = read_key(&tmpdir.join("plugin-root.env"), "CLAUDE_PLUGIN_ROOT", "");
    let recorded = if recorded.is_empty() {
        read_key(
            &tmpdir.join("session-env.sh"),
            "LARCH_CLAUDE_PLUGIN_ROOT",
            "",
        )
    } else {
        recorded
    };
    if recorded.is_empty() {
        return resolve_plugin_root();
    }
    let root = PathBuf::from(recorded);
    if !root.is_absolute() {
        return Err("recorded plugin root is not absolute".to_owned());
    }
    let root = fs::canonicalize(root).map_err(|error| error.to_string())?;
    if !root.is_dir() {
        return Err("recorded plugin root is not a directory".to_owned());
    }
    Ok(root)
}

fn closeout_child_environment(tmpdir: &Path) -> Vec<(ChildEnvironment, OsString)> {
    let session = tmpdir.join("session-env.sh");
    let mut environment = vec![(
        ChildEnvironment::ImplementTmpdir,
        tmpdir.as_os_str().to_owned(),
    )];
    environment.extend(
        [
            (
                "LARCH_TOKEN_SESSION_ID",
                ChildEnvironment::LarchTokenSessionId,
            ),
            (
                "LARCH_CLAUDE_SOURCE_FILE",
                ChildEnvironment::LarchClaudeSourceFile,
            ),
            ("LARCH_TIMING_LEDGER", ChildEnvironment::LarchTimingLedger),
        ]
        .into_iter()
        .map(|(key, child_key)| {
            let inherited = env::var(key).unwrap_or_default();
            (
                child_key,
                OsString::from(read_key(&session, key, &inherited)),
            )
        }),
    );
    environment
}

fn child_code(output: &ProcessOutput) -> i32 {
    output
        .status()
        .code()
        .unwrap_or_else(|| i32::from(!output.status().success()))
}

fn combined_output(output: &ProcessOutput) -> String {
    let bytes = [output.stdout(), output.stderr()].concat();
    String::from_utf8_lossy(&bytes).into_owned()
}

fn write_text(path: &Path, text: &str) -> Result<(), String> {
    write_confined_file(path, text, 0o600, "implement closeout file")
}

fn touch(path: &Path) -> Result<(), String> {
    write_text(path, "")
}

fn regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_file())
}

fn summary_nonempty(tmpdir: &Path) -> bool {
    fs::symlink_metadata(tmpdir.join("summary-final.md"))
        .is_ok_and(|metadata| metadata.file_type().is_file() && metadata.len() > 0)
}

fn print_summary_markers(tmpdir: &Path, sentinel: &str) -> i32 {
    let summary = tmpdir.join("summary-final.md");
    if assert_no_symlink_path_or_ancestors(&summary).is_err() {
        eprintln!("closeout: cannot read summary-final.md");
        return 1;
    }
    let Ok(data) = fs::read(&summary) else {
        eprintln!("closeout: cannot read summary-final.md");
        return 1;
    };
    let mut body = String::from_utf8_lossy(&data).into_owned();
    if !data.is_empty() && !data.ends_with(b"\n") {
        body.push('\n');
    }
    let rendered = format!("{SUMMARY_BEGIN}\n{body}{SUMMARY_END}\n");
    if std::io::stdout().write_all(rendered.as_bytes()).is_err() {
        eprintln!("closeout: cannot emit summary markers");
        return 1;
    }
    if touch(&tmpdir.join(sentinel)).is_err() {
        eprintln!("closeout: cannot emit summary markers");
        return 1;
    }
    0
}

fn append_failure(
    context: &CloseoutContext,
    site: &str,
    tool: &str,
    exit_code: i32,
    category: &str,
    output_file: &Path,
) {
    if !regular_file(output_file) {
        let _ignored = write_text(output_file, "");
    }
    let arguments = append_failure_args(
        context
            .tmpdir
            .join("execution-issues.md")
            .display()
            .to_string(),
        site,
        tool,
        &exit_code.to_string(),
        category,
        output_file,
    )
    .into_iter()
    .map(OsString::from);
    let _ignored = context.run(arguments);
}

fn execute_step16(context: &CloseoutContext) -> Result<(), String> {
    let inherited_run_id = env::var("RUN_ID").unwrap_or_default();
    let session_run_id = read_key(
        &context.tmpdir.join("session-env.sh"),
        "LARCH_RUN_ID",
        &inherited_run_id,
    );
    let run_id = if session_run_id.is_empty() {
        [
            ("ship-pr-state.sh", "RUN_ID"),
            ("finalize-state.sh", "RUN_ID"),
        ]
        .into_iter()
        .find_map(|(file, key)| {
            let value = read_key(&context.tmpdir.join(file), key, "");
            (!value.is_empty()).then_some(value)
        })
        .unwrap_or_default()
    } else {
        session_run_id
    };
    let _timing = context.run([
        "timing".into(),
        "telemetry-mark".into(),
        "--implement-tmpdir".into(),
        context.tmpdir.as_os_str().to_owned(),
        "--label".into(),
        "Step 16 — rejected findings".into(),
    ])?;
    let _rejected = context.run([
        "review-and-fix".into(),
        "write-rejected".into(),
        "--implement-tmpdir".into(),
        context.tmpdir.as_os_str().to_owned(),
        "--run-id".into(),
        run_id.into(),
        "--log-root".into(),
        context.tmpdir.join("larch-logs").into_os_string(),
    ])?;
    Ok(())
}

fn record_step16_failure(context: &CloseoutContext) {
    let log = context.tmpdir.join("step16-write-rejected.failure.log");
    let _ignored = write_text(&log, "");
    append_failure(
        context,
        "Step 16 — rejected findings",
        "scripts/larch.sh implement step-16",
        INTERNAL_ERROR,
        "Tool Failures",
        &log,
    );
}

fn execute_slack(context: &CloseoutContext) -> Result<(), String> {
    let log = context.tmpdir.join("step16a-slack-issue-announce.log");
    let _ignored = write_text(&log, "");
    let webhook_environment = env::var_os(LARCH_SLACK_WEBHOOK_URL)
        .filter(|value| !value.is_empty())
        .map(|value| vec![(ChildEnvironment::LarchSlackWebhookUrl, value)])
        .unwrap_or_default();
    let output = context.run_with_environment(
        [
            "slack".into(),
            "issue-announce".into(),
            "--implement-tmpdir".into(),
            context.tmpdir.as_os_str().to_owned(),
            "--best-effort".into(),
        ],
        &webhook_environment,
    )?;
    let body = combined_output(&output);
    let logged = write_text(&log, &body).is_ok();
    let slack_text = if logged {
        body
    } else {
        fs::read_to_string(&log).unwrap_or_default()
    };
    if slack_text.contains("STATUS=failed") {
        append_failure(
            context,
            "Step 16a — notify",
            "scripts/larch.sh slack issue-announce",
            child_code(&output),
            "Warnings",
            &log,
        );
    }
    Ok(())
}

fn remove_backup(path: &Path) -> Result<(), String> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error.to_string()),
    };
    if !metadata.file_type().is_file() {
        return Err(format!("refusing non-regular backup: {}", path.display()));
    }
    assert_no_symlink_path_or_ancestors(path)?;
    remove_optional_file(path).map_err(|error| error.to_string())
}

fn backup_summary(summary: &Path, backup: &Path) -> Result<bool, String> {
    if !regular_file(summary) {
        return Ok(false);
    }
    assert_no_symlink_path_or_ancestors(summary)?;
    remove_backup(backup)?;
    assert_no_symlink_path_or_ancestors(backup)?;
    fs::rename(summary, backup).map_err(|error| error.to_string())?;
    Ok(true)
}

fn restore_summary(summary: &Path, backup: &Path) {
    if !regular_file(backup) {
        return;
    }
    if assert_no_symlink_path_or_ancestors(summary).is_err()
        || assert_no_symlink_path_or_ancestors(backup).is_err()
    {
        return;
    }
    let _ignored = fs::rename(backup, summary);
}

fn final_report(context: &CloseoutContext, print_stdout: bool) -> Result<ProcessOutput, String> {
    let mut arguments = vec![
        "final-report".into(),
        "write".into(),
        "--implement-tmpdir".into(),
        context.tmpdir.as_os_str().to_owned(),
    ];
    if print_stdout {
        arguments.push("--print-stdout".into());
    }
    let cost_overrides = crate::final_report_commands::cost_overrides_from_environment();
    if cost_overrides != "{}" {
        arguments.extend(["--cost-overrides-json".into(), cost_overrides.into()]);
    }
    let environment = [
        (
            ChildEnvironment::ClaudeCodeEffortLevel,
            env::var_os("CLAUDE_CODE_EFFORT_LEVEL").unwrap_or_default(),
        ),
        (
            ChildEnvironment::ClaudeEffort,
            env::var_os("CLAUDE_EFFORT").unwrap_or_default(),
        ),
        (
            ChildEnvironment::LarchExecIssueAssessmentModel,
            env::var_os("LARCH_EXEC_ISSUE_ASSESSMENT_MODEL").unwrap_or_default(),
        ),
    ];
    context.run_with_environment(arguments, &environment)
}

fn execute_step17(context: &CloseoutContext, no_print_stdout: bool) -> Result<i32, String> {
    let _timing = context.run([
        "timing".into(),
        "telemetry-mark".into(),
        "--implement-tmpdir".into(),
        context.tmpdir.as_os_str().to_owned(),
        "--label".into(),
        "Step 17 — final report".into(),
    ])?;
    let summary = context.tmpdir.join("summary-final.md");
    let log = context.tmpdir.join("step17-write-final-report.failure.log");
    let _ignored = write_text(&log, "");

    if no_print_stdout {
        let backup = context.tmpdir.join(".summary-final.pre-step17.bak");
        let had_backup = match backup_summary(&summary, &backup) {
            Ok(had_backup) => had_backup,
            Err(_error) => {
                eprintln!("closeout: cannot backup summary-final.md before Step 17 write");
                return Ok(2);
            }
        };
        let output = final_report(context, false)?;
        let code = child_code(&output);
        let _logged = write_text(&log, &combined_output(&output));
        if code == 0 {
            if had_backup {
                remove_backup(&backup)?;
            }
            return Ok(0);
        }
        append_failure(
            context,
            "Step 17 — final report",
            "scripts/larch.sh final-report write",
            code,
            "Tool Failures",
            &log,
        );
        if summary_nonempty(&context.tmpdir) {
            if had_backup {
                remove_backup(&backup)?;
            }
            return Ok(0);
        }
        if had_backup {
            restore_summary(&summary, &backup);
        }
        return Ok(code);
    }

    let output = final_report(context, true)?;
    let code = child_code(&output);
    let body = combined_output(&output);
    let logged = write_text(&log, &body).is_ok();
    if code == 0 {
        if logged {
            let _ignored = std::io::stdout().write_all(body.as_bytes());
        }
        if summary_nonempty(&context.tmpdir) {
            let _ignored = touch(&context.tmpdir.join(".step17-printed"));
        }
    } else {
        append_failure(
            context,
            "Step 17 — final report",
            "scripts/larch.sh final-report write",
            code,
            "Tool Failures",
            &log,
        );
    }
    Ok(code)
}

fn exit_code(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

/// Run the standalone Step 16 rejected-findings checkpoint.
pub fn step_16(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(arguments, STEP16_PROG, STEP16_USAGE, STEP16_HELP, &[]) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let context = match context(&parsed) {
        Ok(context) => context,
        Err(code) => return code,
    };
    match execute_step16(&context) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("closeout: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Run Step 16 and the best-effort Step 16a Slack announcement.
pub fn step_16_16a(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(
        arguments,
        STEP16_16A_PROG,
        STEP16_16A_USAGE,
        STEP16_16A_HELP,
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let context = match context(&parsed) {
        Ok(context) => context,
        Err(code) => return code,
    };
    if execute_step16(&context).is_err() {
        record_step16_failure(&context);
    }
    if let Err(error) = execute_slack(&context) {
        eprintln!("closeout: {error}");
        return ExitCode::FAILURE;
    }
    let _ignored = touch(&context.tmpdir.join(".step16-16a-done"));
    ExitCode::SUCCESS
}

/// Run the standalone Step 17 final-report checkpoint.
pub fn step_17(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(
        arguments,
        STEP17_PROG,
        STEP17_USAGE,
        STEP17_HELP,
        &["--no-print-stdout"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let context = match context(&parsed) {
        Ok(context) => context,
        Err(code) => return code,
    };
    match execute_step17(&context, parsed.flag("--no-print-stdout")) {
        Ok(code) => exit_code(code),
        Err(error) => {
            eprintln!("closeout: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Run Steps 16, 16a, and 17 while preserving the terminal handoff contract.
pub fn step_16_17(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(
        arguments,
        STEP16_17_PROG,
        STEP16_17_USAGE,
        STEP16_17_HELP,
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let context = match context(&parsed) {
        Ok(context) => context,
        Err(code) => return code,
    };
    if execute_step16(&context).is_err() {
        record_step16_failure(&context);
    }
    if let Err(error) = execute_slack(&context) {
        eprintln!("closeout: {error}");
        return ExitCode::FAILURE;
    }
    let _ignored = touch(&context.tmpdir.join(".step16-16a-done"));

    let step17_log = context.tmpdir.join("step17-write-final-report.failure.log");
    let step17_rc = match execute_step17(&context, true) {
        Ok(code) => code,
        Err(_error) => {
            let _ignored = write_text(&step17_log, "");
            append_failure(
                &context,
                "Step 17 — final report",
                "scripts/larch.sh implement step-17",
                INTERNAL_ERROR,
                "Tool Failures",
                &step17_log,
            );
            INTERNAL_ERROR
        }
    };
    if step17_rc == 0 && summary_nonempty(&context.tmpdir) {
        if print_summary_markers(&context.tmpdir, ".step17-printed") != 0 {
            eprintln!("closeout: failed to emit summary markers");
        }
    } else if !summary_nonempty(&context.tmpdir) {
        eprintln!(
            "closeout: Step 17 final report render failed (rc={step17_rc}); no summary body written. Step 18b will report the cause."
        );
    }
    ExitCode::SUCCESS
}
