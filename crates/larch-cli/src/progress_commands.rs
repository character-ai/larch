//! `progress` breadcrumb, statusline, and installation verbs.
//!
//! Every verb keeps the exit codes and stream routing its hook, skill, and
//! launcher callers depend on. The statusline and session-reset verbs are
//! fail silent by contract: a Claude Code session must never see them fail.
//! Ambient state — environment, working directory, stdin — is read here, at
//! the composition root, and passed into the adapter layer explicitly.

use crate::argparse_compat::{
    ParsedCommandLine, parse, resolve_option, split_inline_option, write_stdout,
};
use larch_adapters::{
    phase_detail::{self, PhaseSkill, RenderRequest},
    progress_state::{self, ProgressPaths},
    statusline::{self, InstallOutcome, StatuslineEnvironment},
};
use larch_core::STATUSLINE_DISABLE_ENV;
use std::{
    env,
    ffi::OsString,
    io::Read as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

const ACTIVATE_USAGE: &str = "usage: progress activate [--repo-root REPO_ROOT] --run-id RUN_ID";
const DEACTIVATE_USAGE: &str = "usage: progress deactivate [--repo-root REPO_ROOT] --run-id RUN_ID";
const CLEAR_USAGE: &str = "usage: progress clear [--repo-root REPO_ROOT]";
const NOTE_USAGE: &str = "usage: progress note [--repo-root REPO_ROOT] [--run-id RUN_ID] --skill SKILL --step STEP text [text ...]";
const STATUSLINE_USAGE: &str = "usage: progress statusline";
const SESSION_RESET_USAGE: &str = "usage: progress session-reset";
const INSTALL_USAGE: &str = "usage: progress install-statusline [--plugin-root PLUGIN_ROOT] [--repo-root REPO_ROOT] [--notice]";
const RENDER_PHASE_DETAIL_USAGE: &str = "usage: cli.py progress render-phase-detail [-h] --rounds-root ROUNDS_ROOT\n                                           [--findings-file FINDINGS_FILE]\n                                           [--timing-ledger TIMING_LEDGER]\n                                           [--token-ledger TOKEN_LEDGER]\n                                           [--skill {implement,design}]\n                                           [--top-n TOP_N] [--no-gantt]\n                                           [--output OUTPUT]";
const RENDER_PHASE_DETAIL_HELP: &str = "usage: cli.py progress render-phase-detail [-h] --rounds-root ROUNDS_ROOT\n                                           [--findings-file FINDINGS_FILE]\n                                           [--timing-ledger TIMING_LEDGER]\n                                           [--token-ledger TOKEN_LEDGER]\n                                           [--skill {implement,design}]\n                                           [--top-n TOP_N] [--no-gantt]\n                                           [--output OUTPUT]\n\noptions:\n  -h, --help            show this help message and exit\n  --rounds-root ROUNDS_ROOT\n  --findings-file FINDINGS_FILE\n  --timing-ledger TIMING_LEDGER\n  --token-ledger TOKEN_LEDGER\n  --skill {implement,design}\n  --top-n TOP_N\n  --no-gantt\n  --output OUTPUT\n";
const WRITE_DESIGN_ROUND_META_USAGE: &str =
    "usage: cli.py progress write-design-round-meta [-h] --round-dir ROUND_DIR";
const WRITE_DESIGN_ROUND_META_HELP: &str = "usage: cli.py progress write-design-round-meta [-h] --round-dir ROUND_DIR\n\noptions:\n  -h, --help            show this help message and exit\n  --round-dir ROUND_DIR\n";
const WRITE_IMPLEMENT_ROUND_META_USAGE: &str =
    "usage: cli.py progress write-implement-round-meta [-h] --round-dir ROUND_DIR";
const WRITE_IMPLEMENT_ROUND_META_HELP: &str = "usage: cli.py progress write-implement-round-meta [-h] --round-dir ROUND_DIR\n\noptions:\n  -h, --help            show this help message and exit\n  --round-dir ROUND_DIR\n";

const LAUNCHER_RELATIVE: &str = ".cache/larch/statusline.sh";
const NOTICE_SENTINEL_RELATIVE: &str = ".cache/larch/.statusline-install-notice";
const LARCH_ENTRYPOINT_RELATIVE: &str = "scripts/larch.sh";

/// Point the clone's active-run pointer at one run.
pub fn activate(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--repo-root", "--run-id"], 0);
    if let Some(error) = parsed.error() {
        return usage_error(ACTIVATE_USAGE, "progress activate", &error);
    }
    let Some(run_id) = required_run_id(&parsed, ACTIVATE_USAGE, "progress activate") else {
        return ExitCode::from(2);
    };
    match progress_state::activate_run(&paths(&parsed), &run_id) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("progress activate failed: {message}");
            ExitCode::from(2)
        }
    }
}

/// Clear the clone's active-run pointer when the named run still owns it.
pub fn deactivate(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--repo-root", "--run-id"], 0);
    if let Some(error) = parsed.error() {
        return usage_error(DEACTIVATE_USAGE, "progress deactivate", &error);
    }
    let Some(run_id) = required_run_id(&parsed, DEACTIVATE_USAGE, "progress deactivate") else {
        return ExitCode::from(2);
    };
    let _cleared = progress_state::deactivate_run(&paths(&parsed), &run_id);
    ExitCode::SUCCESS
}

/// Clear the clone's active-run pointer regardless of its prior owner.
pub fn clear(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--repo-root"], 0);
    if let Some(error) = parsed.error() {
        return usage_error(CLEAR_USAGE, "progress clear", &error);
    }
    let _cleared = progress_state::clear_active_run(&paths(&parsed));
    ExitCode::SUCCESS
}

/// Append one breadcrumb to the active run, or to an explicitly named run.
pub fn note(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(
        arguments,
        &["--repo-root", "--run-id", "--skill", "--step"],
        usize::MAX,
    );
    if let Some(error) = parsed.error() {
        return usage_error(NOTE_USAGE, "progress note", &error);
    }
    let (Some(skill), Some(step)) = (parsed.value("--skill"), parsed.value("--step")) else {
        return usage_error(
            NOTE_USAGE,
            "progress note",
            &missing_arguments(&parsed, &["--skill", "--step"]),
        );
    };
    let mut words: Vec<String> = Vec::new();
    let mut index = 0;
    while let Some(word) = parsed.positional(index) {
        words.push(word.to_string_lossy().into_owned());
        index += 1;
    }
    if words.is_empty() {
        return usage_error(
            NOTE_USAGE,
            "progress note",
            "the following arguments are required: text",
        );
    }
    let text = words.join(" ");
    let paths = paths(&parsed);
    let skill = skill.to_string_lossy();
    let step = step.to_string_lossy();
    let _written = parsed.value("--run-id").map_or_else(
        || progress_state::append_breadcrumb(&paths, &skill, &step, &text),
        |run_id| {
            progress_state::append_breadcrumb_for_run(
                &paths,
                &run_id.to_string_lossy(),
                &skill,
                &step,
                &text,
            )
        },
    );
    ExitCode::SUCCESS
}

/// Render the larch statusline for the payload on stdin.
pub fn render_statusline(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &[], 0);
    if let Some(error) = parsed.error() {
        return usage_error(STATUSLINE_USAGE, "progress statusline", &error);
    }
    let rendered = statusline::render(&read_stdin(), &statusline_environment());
    if rendered.is_empty() {
        return ExitCode::SUCCESS;
    }
    write_stdout(&rendered)
}

/// Clear a stale active-run pointer when a fresh Claude session starts.
pub fn session_reset(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &[], 0);
    if let Some(error) = parsed.error() {
        return usage_error(SESSION_RESET_USAGE, "progress session-reset", &error);
    }
    if statusline_disabled() {
        return ExitCode::SUCCESS;
    }
    let _cleared = statusline::session_reset(&read_stdin(), &statusline_environment());
    ExitCode::SUCCESS
}

/// Idempotently install the larch statusline into clone-local settings.
pub fn install_statusline(arguments: &[OsString]) -> ExitCode {
    // `--notice` is a store-true flag, so it is removed before the value-option
    // table sees the line.
    let notice = arguments.iter().any(|argument| argument == "--notice");
    let remaining: Vec<OsString> = arguments
        .iter()
        .filter(|argument| *argument != "--notice")
        .cloned()
        .collect();
    let parsed = parse(&remaining, &["--plugin-root", "--repo-root"], 0);
    if let Some(error) = parsed.error() {
        return usage_error(INSTALL_USAGE, "progress install-statusline", &error);
    }
    if statusline_disabled() {
        return ExitCode::SUCCESS;
    }
    let repo_root = parsed
        .value("--repo-root")
        .filter(|value| !value.is_empty())
        .map_or_else(
            || larch_core::install_payload_directory(&read_stdin()).unwrap_or_default(),
            |value| value.to_string_lossy().into_owned(),
        );
    let plugin_root = parsed
        .value("--plugin-root")
        .filter(|value| !value.is_empty())
        .map(|value| value.to_string_lossy().into_owned())
        .or_else(|| env::var("CLAUDE_PLUGIN_ROOT").ok())
        .unwrap_or_default();
    if repo_root.is_empty() || plugin_root.is_empty() {
        return ExitCode::SUCCESS;
    }
    let home = home_directory();
    let plugin_root = PathBuf::from(plugin_root);
    let outcome = statusline::install(
        Path::new(&repo_root),
        &plugin_root,
        &home.join(LAUNCHER_RELATIVE),
        &plugin_root.join(LARCH_ENTRYPOINT_RELATIVE),
        Some(&home.join(".claude/settings.json")),
    );
    if notice
        && matches!(
            outcome,
            InstallOutcome::Installed {
                first_install: true
            }
        )
    {
        announce_first_install(&home.join(NOTICE_SENTINEL_RELATIVE));
    }
    ExitCode::SUCCESS
}

/// Render the historical review-phase detail report through the Rust adapter.
pub fn render_phase_detail(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        return write_stdout(RENDER_PHASE_DETAIL_HELP);
    }
    for argument in arguments {
        let argument = argument.to_string_lossy();
        let (name, explicit) = split_inline_option(&argument);
        if let (Some(option), Some(value)) = (resolve_option(name, &["--no-gantt"]), explicit) {
            return usage_error(
                RENDER_PHASE_DETAIL_USAGE,
                "cli.py progress render-phase-detail",
                &format!("argument {option}: ignored explicit argument '{value}'"),
            );
        }
    }
    let no_gantt = arguments.iter().any(|argument| {
        let argument = argument.to_string_lossy();
        let (name, explicit) = split_inline_option(&argument);
        explicit.is_none() && resolve_option(name, &["--no-gantt"]).is_some()
    });
    let remaining: Vec<OsString> = arguments
        .iter()
        .filter(|argument| {
            let argument = argument.to_string_lossy();
            let (name, explicit) = split_inline_option(&argument);
            explicit.is_some() || resolve_option(name, &["--no-gantt"]).is_none()
        })
        .cloned()
        .collect();
    let parsed = parse(
        &remaining,
        &[
            "--rounds-root",
            "--findings-file",
            "--timing-ledger",
            "--token-ledger",
            "--skill",
            "--top-n",
            "--output",
        ],
        0,
    );
    if let Some(error) = parsed.error() {
        return usage_error(
            RENDER_PHASE_DETAIL_USAGE,
            "cli.py progress render-phase-detail",
            &error,
        );
    }
    let Some(rounds_root) = parsed.value("--rounds-root") else {
        return usage_error(
            RENDER_PHASE_DETAIL_USAGE,
            "cli.py progress render-phase-detail",
            "the following arguments are required: --rounds-root",
        );
    };
    let skill_raw = parsed.value("--skill").map_or_else(
        || "implement".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    let Some(skill) = PhaseSkill::parse(&skill_raw) else {
        return usage_error(
            RENDER_PHASE_DETAIL_USAGE,
            "cli.py progress render-phase-detail",
            &format!(
                "argument --skill: invalid choice: '{skill_raw}' (choose from 'implement', 'design')"
            ),
        );
    };
    let top_n = parsed
        .value("--top-n")
        .and_then(python_nonnegative_usize)
        .unwrap_or(7);
    let path_value = |option: &str| parsed.value(option).map(PathBuf::from);
    let rounds_root = PathBuf::from(rounds_root);
    let findings = path_value("--findings-file");
    let timing = path_value("--timing-ledger");
    let tokens = path_value("--token-ledger");
    let output = phase_detail::render_phase_detail(&RenderRequest {
        rounds_root: &rounds_root,
        skill,
        timing_ledger: timing.as_deref(),
        token_ledger: tokens.as_deref(),
        findings_file: findings.as_deref(),
        top_n,
        gantt_enabled: !no_gantt,
    });
    if let Some(path) = parsed.value("--output") {
        return match phase_detail::write_render_output(Path::new(path), &output) {
            Ok(()) => ExitCode::SUCCESS,
            Err(_error) => ExitCode::FAILURE,
        };
    }
    write_stdout(&output)
}

/// Materialize `/design` review metadata through the Rust adapter.
pub fn write_design_round_meta(arguments: &[OsString]) -> ExitCode {
    write_round_meta(
        arguments,
        WRITE_DESIGN_ROUND_META_USAGE,
        WRITE_DESIGN_ROUND_META_HELP,
        "cli.py progress write-design-round-meta",
        phase_detail::write_design_round_meta,
    )
}

/// Materialize `/implement` review metadata through the Rust adapter.
pub fn write_implement_round_meta(arguments: &[OsString]) -> ExitCode {
    write_round_meta(
        arguments,
        WRITE_IMPLEMENT_ROUND_META_USAGE,
        WRITE_IMPLEMENT_ROUND_META_HELP,
        "cli.py progress write-implement-round-meta",
        phase_detail::write_implement_round_meta,
    )
}

fn write_round_meta(
    arguments: &[OsString],
    usage: &str,
    help: &str,
    program: &str,
    writer: fn(&Path) -> Result<bool, String>,
) -> ExitCode {
    if help_requested(arguments) {
        return write_stdout(help);
    }
    let parsed = parse(arguments, &["--round-dir"], 0);
    if let Some(error) = parsed.error() {
        return usage_error(usage, program, &error);
    }
    let Some(round_dir) = parsed.value("--round-dir") else {
        return usage_error(
            usage,
            program,
            "the following arguments are required: --round-dir",
        );
    };
    match writer(Path::new(round_dir)) {
        Ok(_written) => ExitCode::SUCCESS,
        Err(_error) => ExitCode::FAILURE,
    }
}

fn help_requested(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_string_lossy().as_ref(), "-h" | "--help"))
}

fn python_nonnegative_usize(value: &std::ffi::OsStr) -> Option<usize> {
    let value = value.to_string_lossy();
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then_some(value.parse::<usize>().ok())
        .flatten()
}

fn announce_first_install(sentinel: &Path) {
    if statusline::publish_notice_sentinel(sentinel) {
        println!(
            "larch: installed progress statusline (set LARCH_STATUSLINE_DISABLE=1 to opt out)"
        );
    }
}

fn paths(parsed: &ParsedCommandLine) -> ProgressPaths {
    let repo_root = parsed.value("--repo-root").map_or_else(
        || env::current_dir().unwrap_or_else(|_error| PathBuf::from(".")),
        PathBuf::from,
    );
    progress_state::progress_paths(&cache_home(), &repo_root)
}

fn cache_home() -> PathBuf {
    progress_state::progress_cache_home(
        env::var_os("LARCH_TEST_CACHE_HOME").as_deref(),
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

fn home_directory() -> PathBuf {
    env::var_os("HOME").map_or_else(|| PathBuf::from("/"), PathBuf::from)
}

fn statusline_environment() -> StatuslineEnvironment {
    StatuslineEnvironment {
        cache_home: cache_home(),
        bgjob_registry_root: env::var_os("LARCH_BGJOB_REGISTRY_ROOT")
            .filter(|value| !value.is_empty())
            .map(PathBuf::from),
        lines: env::var("LARCH_STATUSLINE_LINES").ok(),
        stale_after_s: env::var("LARCH_STATUSLINE_STALE_AFTER_S").ok(),
        hide_after_s: env::var("LARCH_STATUSLINE_HIDE_AFTER_S").ok(),
        columns: env::var("COLUMNS").ok(),
        now_override: env::var("LARCH_TEST_STATUSLINE_NOW").ok(),
    }
}

fn statusline_disabled() -> bool {
    env::var(STATUSLINE_DISABLE_ENV).as_deref() == Ok("1")
}

fn read_stdin() -> String {
    let mut buffer = Vec::new();
    let _read = std::io::stdin().lock().read_to_end(&mut buffer);
    String::from_utf8_lossy(&buffer).into_owned()
}

fn required_run_id(parsed: &ParsedCommandLine, usage: &str, program: &str) -> Option<String> {
    let run_id = parsed.value("--run-id");
    if run_id.is_none() {
        emit_usage_error(
            usage,
            program,
            "the following arguments are required: --run-id",
        );
    }
    run_id.map(|value| value.to_string_lossy().into_owned())
}

fn missing_arguments(parsed: &ParsedCommandLine, required: &[&str]) -> String {
    let missing: Vec<&str> = required
        .iter()
        .copied()
        .filter(|option| parsed.value(option).is_none())
        .collect();
    format!(
        "the following arguments are required: {}",
        missing.join(", ")
    )
}

fn emit_usage_error(usage: &str, program: &str, error: &str) {
    eprintln!("{usage}\n{program}: error: {error}");
}

fn usage_error(usage: &str, program: &str, error: &str) -> ExitCode {
    emit_usage_error(usage, program, error);
    ExitCode::from(2)
}

#[cfg(test)]
mod tests {
    use super::{missing_arguments, required_run_id};
    use crate::argparse_compat::parse;
    use std::ffi::OsString;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn a_missing_required_option_is_reported_once() {
        let parsed = parse(&arguments(&["--repo-root", "/clone"]), &["--repo-root"], 0);

        assert_eq!(
            required_run_id(&parsed, "usage: x", "x"),
            None,
            "a missing --run-id must refuse the verb"
        );
        assert_eq!(
            missing_arguments(&parsed, &["--skill", "--step"]),
            "the following arguments are required: --skill, --step"
        );
    }

    #[test]
    fn an_inline_run_id_is_accepted() {
        let parsed = parse(&arguments(&["--run-id=run-1"]), &["--run-id"], 0);

        assert_eq!(
            required_run_id(&parsed, "usage: x", "x").as_deref(),
            Some("run-1")
        );
    }
}
