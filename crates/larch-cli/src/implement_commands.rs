//! `/implement` clone tagging, coder-scout normalization, and Step 0 bootstrap.
//!
//! These four verbs are the composition layer between the `/implement` skill
//! wrappers and the already-owned `admission`, `agent`, `bootstrap`, and
//! `run-log` commands. They read ambient session files, assemble one child
//! command line, and forward that child's contract unchanged, so each policy
//! stays with the command that owns it.
//!
//! `scripts/larch.sh` validates and exports `CLAUDE_PLUGIN_ROOT` before it
//! execs this binary, so the retired Python owner's `plugin-root.env`
//! rehydration has no remaining work to do here.

use std::{
    env,
    ffi::OsString,
    fs,
    io::Write as _,
    os::unix::ffi::OsStrExt as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_core::{ChildEnvironment, ProcessOutput, binary_on_path, emit_kv, shell_quote};

use crate::{
    argparse_compat::{
        ParsedCommandLine, choice_error, parse_with_flags, usage_error, write_stdout,
    },
    oos_commands::atomic_write,
    python_verb::run_python_verb,
    runtime_entrypoint::{run_verified_larch, run_verified_larch_with_environment},
    tracking_issue_commands::adoption_sentinel_identity,
};

/// Bytes a clone tag may carry verbatim; every other byte becomes `_`.
const CLONE_TAG_ALLOWED: &[u8] =
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
/// Byte ceiling the retired owner applied after translation.
const CLONE_TAG_MAX_BYTES: usize = 32;
/// Difficulty tiers `--difficulty` accepts, alongside the empty default.
const DIFFICULTY_VALUES: [&str; 3] = ["TRIVIAL", "MODERATE", "HARD"];
/// Empty dynamic-archetype manifest written whenever normalization refuses.
const EMPTY_SCOUT_MANIFEST: &str = "{\"archetypes\":[]}\n";
/// Deadline for the still-Python `scout filter-manifest` sibling.
const SCOUT_FILTER_TIMEOUT: Duration = Duration::from_secs(120);

const HELP_FLAGS: [&str; 2] = ["-h", "--help"];

const CLONE_TAG_PROGRAM: &str = "cli.py implement clone-tag";
const CLONE_TAG_USAGE: &str = "usage: cli.py implement clone-tag [-h]";
const CLONE_TAG_HELP: &str = concat!(
    "usage: cli.py implement clone-tag [-h]\n",
    "\n",
    "options:\n",
    "  -h, --help  show this help message and exit\n",
);

const SCOUT_PROGRAM: &str = "cli.py implement normalize-coder-scout";
const SCOUT_OPTIONS: [&str; 3] = ["--tmpdir", "--input", "--producer"];
const SCOUT_PRODUCERS: [&str; 3] = ["external", "main-agent", "subagent"];
const SCOUT_USAGE: &str = concat!(
    "usage: cli.py implement normalize-coder-scout [-h] [--tmpdir TMPDIR] [--input INPUT]\n",
    "                                             [--producer {external,main-agent,subagent}]",
);
const SCOUT_HELP: &str = concat!(
    "usage: cli.py implement normalize-coder-scout [-h] [--tmpdir TMPDIR] [--input INPUT]\n",
    "                                             [--producer {external,main-agent,subagent}]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --tmpdir TMPDIR\n",
    "  --input INPUT\n",
    "  --producer {external,main-agent,subagent}\n",
);

const DEGRADED_GATE_PROGRAM: &str = "cli.py implement step-0-degraded-gate";
const DEGRADED_GATE_USAGE: &str = "usage: cli.py implement step-0-degraded-gate [-h]";
const DEGRADED_GATE_HELP: &str = concat!(
    "usage: cli.py implement step-0-degraded-gate [-h]\n",
    "\n",
    "options:\n",
    "  -h, --help  show this help message and exit\n",
);

const BOOTSTRAP_PROGRAM: &str = "cli.py implement step-0-bootstrap";
/// Boolean-valued options `step-0-bootstrap` validates after `argparse`.
const BOOTSTRAP_BOOLEAN_FLAGS: [&str; 9] = [
    "--force-requested",
    "--self-review-requested",
    "--self-implement-requested",
    "--forked-target",
    "--merge-requested",
    "--draft-requested",
    "--no-admin-fallback",
    "--no-logs-commit",
    "--non-interactive",
];
const BOOTSTRAP_OPTIONS: [&str; 19] = [
    "--mode",
    "--issue-number",
    "--preflight-tmpdir",
    "--coder",
    "--force-requested",
    "--self-review-requested",
    "--self-implement-requested",
    "--forked-target",
    "--merge-requested",
    "--draft-requested",
    "--no-admin-fallback",
    "--no-logs-commit",
    "--upstream-repo",
    "--run-id",
    "--caller-env",
    "--session-env",
    "--non-interactive",
    "--difficulty",
    "--lifecycle-parent-context",
];
const BOOTSTRAP_USAGE: &str = concat!(
    "usage: cli.py implement step-0-bootstrap [-h] --mode {initial,resume}\n",
    "                                        [--issue-number ISSUE_NUMBER]\n",
    "                                        [--preflight-tmpdir PREFLIGHT_TMPDIR]\n",
    "                                        [--coder CODER]",
);
const BOOTSTRAP_HELP: &str = concat!(
    "usage: cli.py implement step-0-bootstrap [-h] --mode {initial,resume}\n",
    "                                        [--issue-number ISSUE_NUMBER]\n",
    "                                        [--preflight-tmpdir PREFLIGHT_TMPDIR]\n",
    "                                        [--coder CODER]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --mode {initial,resume}\n",
);

/// Emit this clone's tag and the implement tmpdir prefix derived from it.
pub fn clone_tag(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &[], &HELP_FLAGS, 0);
    if let Some(refusal) =
        help_or_refusal(&parsed, CLONE_TAG_PROGRAM, CLONE_TAG_USAGE, CLONE_TAG_HELP)
    {
        return refusal;
    }
    let tag = derive_clone_tag_full();
    let prefix = format!("claude-implement-{tag}-");
    print_line(&format!("CLONE_TAG_FULL={}", shell_quote(&tag)));
    print_line(&format!(
        "EXPECTED_TMPDIR_BASENAME_PREFIX={}",
        shell_quote(&prefix)
    ));
    ExitCode::SUCCESS
}

/// Normalize a coder-produced dynamic-archetype manifest for Step 5.
pub fn normalize_coder_scout(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &SCOUT_OPTIONS, &HELP_FLAGS, 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        return write_stdout(SCOUT_HELP);
    }
    if let Some(error) = parsed.value_error() {
        return usage_error(SCOUT_USAGE, SCOUT_PROGRAM, error, 2);
    }
    if let Some(error) = choice_error(
        arguments,
        &SCOUT_OPTIONS,
        &[("--producer", &SCOUT_PRODUCERS)],
    ) {
        return usage_error(SCOUT_USAGE, SCOUT_PROGRAM, &error, 2);
    }
    if let Some(error) = parsed.error() {
        return usage_error(SCOUT_USAGE, SCOUT_PROGRAM, &error, 2);
    }
    let producer = option_value(&parsed, "--producer");
    let producer = if producer.is_empty() {
        "external".to_owned()
    } else {
        producer
    };
    let raw_tmpdir = option_or_env(&parsed, "--tmpdir", "IMPLEMENT_TMPDIR");
    if raw_tmpdir.is_empty() {
        eprintln!(
            "implement normalize-coder-scout: --tmpdir is required or IMPLEMENT_TMPDIR must be set"
        );
        return ExitCode::from(2);
    }
    let tmpdir = PathBuf::from(&raw_tmpdir);
    if !tmpdir.is_dir() {
        eprintln!(
            "implement normalize-coder-scout: --tmpdir not a directory: {}",
            tmpdir.display()
        );
        return ExitCode::from(2);
    }
    let input = resolve_tmpdir_path(
        &tmpdir,
        &option_value(&parsed, "--input"),
        "scout-coder-manifest.raw.json",
    );
    let status = normalize_scout_manifest(&tmpdir, &input, &producer);
    emit_kv("SCOUT_CODER_STATUS", &status);
    emit_kv(
        "SCOUT_CODER_MANIFEST",
        &tmpdir.join("scout-coder-manifest.json").to_string_lossy(),
    );
    ExitCode::SUCCESS
}

/// Probe the vendor reviewers, then forward the shared degraded-tools gate.
pub fn step0_degraded_gate(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &[], &HELP_FLAGS, 0);
    if let Some(refusal) = help_or_refusal(
        &parsed,
        DEGRADED_GATE_PROGRAM,
        DEGRADED_GATE_USAGE,
        DEGRADED_GATE_HELP,
    ) {
        return refusal;
    }
    let Some(implement_tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    let session = implement_tmpdir.join("session-env.sh");
    let codex_binary_found = read_kv_first(&session, "CODEX_BINARY_FOUND");
    let cursor_binary_found = read_kv_first(&session, "CURSOR_BINARY_FOUND");
    let mut check = vec![OsString::from("agent"), OsString::from("check-reviewers")];
    if !on_path("codex") {
        check.push(OsString::from("--skip-codex-probe"));
    }
    if !on_path("cursor") {
        check.push(OsString::from("--skip-cursor-probe"));
    }
    // The retired owner probed twice: a cold vendor CLI can fail its first
    // authentication handshake and succeed immediately afterwards.
    let mut probe = run_verified_larch(&check);
    if !probe.as_ref().is_ok_and(|output| output.status().success()) {
        probe = run_verified_larch(&check);
    }
    let probed = probe.map_or_else(|_error| String::new(), |output| stdout_text(&output));
    forward_verified_larch(&[
        OsString::from("agent"),
        OsString::from("degraded-tools-gate"),
        OsString::from("--skill"),
        OsString::from("implement"),
        OsString::from("--codex-present"),
        OsString::from(kv_value(&probed, "CODEX_PRESENT")),
        OsString::from("--cursor-present"),
        OsString::from(kv_value(&probed, "CURSOR_PRESENT")),
        OsString::from("--codex-binary-found"),
        OsString::from(codex_binary_found),
        OsString::from("--cursor-binary-found"),
        OsString::from(cursor_binary_found),
    ])
}

/// Validate the Step 0 flags, rehydrate a resume, and start the run lifecycle.
pub fn step0_bootstrap(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &BOOTSTRAP_OPTIONS, &HELP_FLAGS, 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        return write_stdout(BOOTSTRAP_HELP);
    }
    if let Some(error) = parsed.value_error() {
        return usage_error(BOOTSTRAP_USAGE, BOOTSTRAP_PROGRAM, error, 2);
    }
    if let Some(error) = choice_error(
        arguments,
        &BOOTSTRAP_OPTIONS,
        &[("--mode", &["initial", "resume"])],
    ) {
        return usage_error(BOOTSTRAP_USAGE, BOOTSTRAP_PROGRAM, &error, 2);
    }
    if parsed.value("--mode").is_none() {
        return usage_error(
            BOOTSTRAP_USAGE,
            BOOTSTRAP_PROGRAM,
            "the following arguments are required: --mode",
            2,
        );
    }
    if let Some(error) = parsed.error() {
        return usage_error(BOOTSTRAP_USAGE, BOOTSTRAP_PROGRAM, &error, 2);
    }
    let mut request = match BootstrapRequest::parse(&parsed) {
        Ok(request) => request,
        Err(code) => return code,
    };
    let implement_tmpdir = env::var("IMPLEMENT_TMPDIR")
        .ok()
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);
    if request.mode == "resume" {
        let Some(tmpdir) = implement_tmpdir.as_deref() else {
            eprintln!("bootstrap invoke: --mode resume requires exported IMPLEMENT_TMPDIR");
            return ExitCode::from(2);
        };
        request.apply_resume_rehydration(tmpdir);
    }
    if request.forked_target == "true"
        && request.upstream_repo.is_empty()
        && let Some(code) = request.apply_fork_env()
    {
        return code;
    }
    let environment = session_child_environment(implement_tmpdir.as_deref());
    if let Some(tmpdir) = implement_tmpdir.as_deref()
        && !request.preflight_tmpdir.is_empty()
        && let Err(message) = write_atomic(
            &tmpdir.join("preflight-tmpdir.env"),
            &format!("PREFLIGHT_TMPDIR={}\n", request.preflight_tmpdir),
        )
    {
        eprintln!("step-0-bootstrap: {message}");
        return ExitCode::from(2);
    }
    if request.non_interactive.is_empty() {
        request.non_interactive = resolve_non_interactive(&environment);
    }
    let Ok(result) = run_verified_larch_with_environment(&request.invoke_arguments(), &environment)
    else {
        eprintln!("step-0-bootstrap: could not start bootstrap invoke");
        return ExitCode::from(1);
    };
    let mut stdout = stdout_text(&result);
    let mut stderr = String::from_utf8_lossy(result.stderr()).into_owned();
    let mut code = exit_code_of(&result);
    if code == 0
        && kv_value(&stdout, "REPO_UNAVAILABLE") != "true"
        && request.no_logs_commit != "true"
    {
        let invoked = stdout.clone();
        code = request.start_run_lifecycle(&invoked, &environment, &mut stdout, &mut stderr);
    }
    write_streams(&stdout, &stderr);
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

/// Every Step 0 flag after `argparse` validation and resume rehydration.
struct BootstrapRequest {
    mode: String,
    issue_number: String,
    preflight_tmpdir: String,
    coder: String,
    force_requested: String,
    self_review_requested: String,
    self_implement_requested: String,
    forked_target: String,
    merge_requested: String,
    draft_requested: String,
    no_admin_fallback: String,
    no_logs_commit: String,
    upstream_repo: String,
    run_id: String,
    caller_env: String,
    session_env: String,
    non_interactive: String,
    difficulty: String,
    lifecycle_parent_context: String,
}

impl BootstrapRequest {
    fn parse(parsed: &ParsedCommandLine) -> Result<Self, ExitCode> {
        let request = Self {
            mode: option_value(parsed, "--mode"),
            issue_number: option_value(parsed, "--issue-number"),
            preflight_tmpdir: option_value(parsed, "--preflight-tmpdir"),
            coder: option_value(parsed, "--coder"),
            force_requested: option_value(parsed, "--force-requested"),
            self_review_requested: option_value(parsed, "--self-review-requested"),
            self_implement_requested: option_value(parsed, "--self-implement-requested"),
            forked_target: option_value(parsed, "--forked-target"),
            merge_requested: option_value(parsed, "--merge-requested"),
            draft_requested: option_value(parsed, "--draft-requested"),
            no_admin_fallback: option_value(parsed, "--no-admin-fallback"),
            no_logs_commit: option_value(parsed, "--no-logs-commit"),
            upstream_repo: option_value(parsed, "--upstream-repo"),
            run_id: option_value(parsed, "--run-id"),
            caller_env: option_value(parsed, "--caller-env"),
            session_env: option_value(parsed, "--session-env"),
            non_interactive: option_value(parsed, "--non-interactive"),
            difficulty: option_value(parsed, "--difficulty"),
            lifecycle_parent_context: option_value(parsed, "--lifecycle-parent-context"),
        };
        for flag in BOOTSTRAP_BOOLEAN_FLAGS {
            let supplied = option_value(parsed, flag);
            if !supplied.is_empty() && supplied != "true" && supplied != "false" {
                return Err(die_argv(&format!("{flag} must be true or false")));
            }
        }
        if !request.difficulty.is_empty()
            && !DIFFICULTY_VALUES.contains(&request.difficulty.as_str())
        {
            return Err(die_argv("--difficulty must be TRIVIAL, MODERATE, or HARD"));
        }
        Ok(request)
    }

    /// Fill each absent optional flag from its own durable resume artifact.
    fn apply_resume_rehydration(&mut self, tmpdir: &Path) {
        let session = tmpdir.join("session-env.sh");
        let run_flags = tmpdir.join("run-flags.sh");
        let seed = tmpdir.join("ship-seed-input.env");
        if self.preflight_tmpdir.is_empty() {
            let file = tmpdir.join("preflight-tmpdir.env");
            if file.is_file() {
                self.preflight_tmpdir = read_kv_first(&file, "PREFLIGHT_TMPDIR");
            }
        }
        if self.forked_target.is_empty() {
            let value = read_kv_or(&session, "FORKED_TARGET", "false");
            if value == "true" || value == "false" {
                self.forked_target = value;
            }
        }
        adopt_boolean(&mut self.force_requested, &run_flags, "FORCE_REQUESTED");
        adopt_boolean(
            &mut self.self_review_requested,
            &run_flags,
            "SELF_REVIEW_REQUESTED",
        );
        adopt_boolean(
            &mut self.self_implement_requested,
            &run_flags,
            "SELF_IMPLEMENT_REQUESTED",
        );
        adopt_seed(&mut self.merge_requested, &seed, "MERGE");
        adopt_seed(&mut self.draft_requested, &seed, "DRAFT");
        adopt_seed(&mut self.no_admin_fallback, &seed, "NO_ADMIN_FALLBACK");
        adopt_seed(&mut self.no_logs_commit, &seed, "NO_LOGS_COMMIT");
        if self.issue_number.is_empty() {
            let (sentinel_issue, sentinel_run_id) =
                sentinel_identity(&tmpdir.join("parent-issue.md"));
            let issue = first_nonempty(&sentinel_issue, &read_kv_first(&session, "ISSUE_NUMBER"));
            if !issue.is_empty() {
                self.issue_number = issue;
            }
            if self.run_id.is_empty() {
                let run_id = first_nonempty(&sentinel_run_id, &read_kv_first(&session, "RUN_ID"));
                if !run_id.is_empty() {
                    self.run_id = run_id;
                }
            }
        }
        if self.run_id.is_empty() {
            self.run_id = read_kv_first(&session, "RUN_ID");
        }
    }

    /// Adopt the fork identity a `--forked` run needs, echoing its envelope.
    ///
    /// `FORK_REPO` and `FORK_OWNER` reach the operator through the echoed
    /// stdout: the reviewed child-environment allowlist carries neither, and
    /// no composed child reads them.
    fn apply_fork_env(&mut self) -> Option<ExitCode> {
        let Ok(result) =
            run_verified_larch(&[OsString::from("admission"), OsString::from("fork-env")])
        else {
            eprintln!("step-0-bootstrap: could not start admission fork-env");
            return Some(ExitCode::from(1));
        };
        let stdout = stdout_text(&result);
        if !result.status().success() {
            write_streams(&stdout, &String::from_utf8_lossy(result.stderr()));
            return Some(ExitCode::from(
                u8::try_from(exit_code_of(&result)).unwrap_or(1),
            ));
        }
        let caller_env = kv_value(&stdout, "CALLER_ENV_PATH");
        if !caller_env.is_empty() {
            self.caller_env = caller_env;
        }
        let upstream = kv_value(&stdout, "UPSTREAM_REPO");
        if !upstream.is_empty() {
            self.upstream_repo = upstream;
        }
        let forked = kv_value(&stdout, "FORKED_TARGET");
        if forked == "true" || forked == "false" {
            self.forked_target = forked;
        }
        let mut echoed = stdout;
        if !echoed.is_empty() && !echoed.ends_with('\n') {
            echoed.push('\n');
        }
        write_streams(&echoed, "");
        None
    }

    /// Assemble the `bootstrap invoke` line the retired owner composed.
    fn invoke_arguments(&self) -> Vec<OsString> {
        let issue = if self.issue_number.is_empty() {
            env::var("ISSUE_NUMBER").unwrap_or_default()
        } else {
            self.issue_number.clone()
        };
        let boolean = |value: &str| {
            if value.is_empty() {
                "false".to_owned()
            } else {
                value.to_owned()
            }
        };
        let caller_env = if self.caller_env.is_empty() {
            self.session_env.clone()
        } else {
            self.caller_env.clone()
        };
        [
            "bootstrap",
            "invoke",
            "--mode",
            &self.mode,
            "--issue-number",
            &issue,
            "--preflight-tmpdir",
            &self.preflight_tmpdir,
            "--coder",
            &self.coder,
            "--force-requested",
            &boolean(&self.force_requested),
            "--self-review-requested",
            &boolean(&self.self_review_requested),
            "--self-implement-requested",
            &boolean(&self.self_implement_requested),
            "--forked-target",
            &boolean(&self.forked_target),
            "--merge-requested",
            &boolean(&self.merge_requested),
            "--draft-requested",
            &boolean(&self.draft_requested),
            "--no-admin-fallback",
            &boolean(&self.no_admin_fallback),
            "--no-logs-commit",
            &boolean(&self.no_logs_commit),
            "--upstream-repo",
            &self.upstream_repo,
            "--run-id",
            &self.run_id,
            "--caller-env",
            &caller_env,
            "--non-interactive",
            &self.non_interactive,
            "--difficulty",
            &self.difficulty,
        ]
        .into_iter()
        .map(OsString::from)
        .collect()
    }

    /// Adopt the run-log lifecycle, failing closed on an invalid storage state.
    fn start_run_lifecycle(
        &self,
        invoke_stdout: &str,
        environment: &[(ChildEnvironment, OsString)],
        stdout: &mut String,
        stderr: &mut String,
    ) -> i32 {
        let run_id = first_nonempty(&kv_value(invoke_stdout, "RUN_ID"), &self.run_id);
        let issue = first_nonempty(&kv_value(invoke_stdout, "ISSUE_NUMBER"), &self.issue_number);
        let log_root =
            PathBuf::from(kv_value(invoke_stdout, "IMPLEMENT_TMPDIR")).join("larch-logs");
        let repo_root = env::current_dir().unwrap_or_default();
        let mut arguments: Vec<OsString> = [
            "run-log",
            "lifecycle-start",
            "--repo-root",
            &repo_root.to_string_lossy(),
            "--skill",
            "implement",
            "--run-id",
            &run_id,
            "--log-root",
            &log_root.to_string_lossy(),
            "--issue",
            &issue,
            "--adopt-existing",
        ]
        .into_iter()
        .map(OsString::from)
        .collect();
        if !self.lifecycle_parent_context.is_empty() {
            arguments.push(OsString::from("--lifecycle-parent-context"));
            arguments.push(OsString::from(self.lifecycle_parent_context.clone()));
        }
        let Ok(lifecycle) = run_verified_larch_with_environment(&arguments, environment) else {
            stderr.push_str("step-0-bootstrap: could not start run-log lifecycle-start\n");
            return 1;
        };
        let lifecycle_stdout = stdout_text(&lifecycle);
        stdout.push_str(&lifecycle_stdout);
        stderr.push_str(&String::from_utf8_lossy(lifecycle.stderr()));
        let code = exit_code_of(&lifecycle);
        if code != 0 {
            return code;
        }
        let storage = kv_value(&lifecycle_stdout, "RUN_LOG_STORAGE");
        let preflight = kv_value(&lifecycle_stdout, "STORAGE_PREFLIGHT");
        let storage_ok = (storage == "enabled" && preflight == "ok")
            || (storage == "disabled" && preflight == "skipped-disabled");
        if kv_value(&lifecycle_stdout, "LIFECYCLE_STARTED") != "true" || !storage_ok {
            stderr
                .push_str("step-0-bootstrap: lifecycle start returned an invalid storage state\n");
            return 1;
        }
        0
    }
}

/// Publish the session identity every composed child must observe.
///
/// The retired owner exported these into its own environment; the reviewed
/// child-environment allowlist carries them explicitly instead.
fn session_child_environment(tmpdir: Option<&Path>) -> Vec<(ChildEnvironment, OsString)> {
    let mut rows = Vec::new();
    if let Some(tmpdir) = tmpdir {
        let session = tmpdir.join("session-env.sh");
        for (key, name) in [
            (
                ChildEnvironment::LarchTokenSessionId,
                "LARCH_TOKEN_SESSION_ID",
            ),
            (
                ChildEnvironment::LarchClaudeSourceFile,
                "LARCH_CLAUDE_SOURCE_FILE",
            ),
            (ChildEnvironment::LarchTimingLedger, "LARCH_TIMING_LEDGER"),
        ] {
            if env::var_os(name).is_none_or(|value| value.is_empty()) {
                let value = read_kv_first(&session, name);
                if !value.is_empty() {
                    rows.push((key, OsString::from(value)));
                }
            }
        }
    }
    rows.push((
        ChildEnvironment::LarchClaudePid,
        OsString::from(claude_pid()),
    ));
    rows
}

/// Resolve the non-interactive default the retired owner delegated.
fn resolve_non_interactive(environment: &[(ChildEnvironment, OsString)]) -> String {
    let arguments = [
        OsString::from("bootstrap"),
        OsString::from("resolve-non-interactive"),
    ];
    let resolved = run_verified_larch_with_environment(&arguments, environment)
        .map_or_else(|_error| String::new(), |output| stdout_text(&output));
    if resolved.trim() == "true" {
        "true".to_owned()
    } else {
        "false".to_owned()
    }
}

/// Refuse one Step 0 argument line the way the retired owner did.
fn die_argv(message: &str) -> ExitCode {
    eprintln!("step-0-bootstrap: {message}");
    ExitCode::from(2)
}

/// Serve `--help`, then the `argparse` value and surplus-argument refusals.
fn help_or_refusal(
    parsed: &ParsedCommandLine,
    program: &str,
    usage: &str,
    help: &str,
) -> Option<ExitCode> {
    if parsed.flag("-h") || parsed.flag("--help") {
        return Some(write_stdout(help));
    }
    if let Some(error) = parsed.value_error() {
        return Some(usage_error(usage, program, error, 2));
    }
    parsed
        .error()
        .map(|error| usage_error(usage, program, &error, 2))
}

/// Return one option's supplied value, or the empty `argparse` default.
fn option_value(parsed: &ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option)
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

/// Return the supplied option, falling back to one environment variable.
fn option_or_env(parsed: &ParsedCommandLine, option: &str, variable: &str) -> String {
    let supplied = option_value(parsed, option);
    if supplied.is_empty() {
        env::var(variable).unwrap_or_default()
    } else {
        supplied
    }
}

/// Resolve the required implement tmpdir, refusing an unset environment.
fn tmpdir_from_env() -> Option<PathBuf> {
    let raw = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    if raw.is_empty() {
        eprintln!("IMPLEMENT_TMPDIR required");
        return None;
    }
    Some(PathBuf::from(raw))
}

/// Confine one caller-supplied artifact path beneath the implement tmpdir.
fn resolve_tmpdir_path(tmpdir: &Path, raw: &str, default_relative: &str) -> PathBuf {
    if raw.is_empty() {
        return tmpdir.join(default_relative);
    }
    let candidate = Path::new(raw);
    if candidate.is_absolute() && !candidate.starts_with(tmpdir) {
        let mut components = candidate.components();
        let _root = components.next();
        return tmpdir.join(components.as_path());
    }
    tmpdir.join(candidate)
}

/// Filter a coder manifest to Step 5's dynamic-archetype budget.
fn normalize_scout_manifest(tmpdir: &Path, input: &Path, producer: &str) -> String {
    let manifest = tmpdir.join("scout-coder-manifest.json");
    let marker = tmpdir.join("step2-external-scout-eligible.txt");
    let filtered = tmpdir.join(format!(
        "scout-coder-manifest.filtered.{}.json",
        std::process::id()
    ));
    let mut status = "missing-or-invalid";
    if let Some(raw_count) = archetype_count(input) {
        // `scout filter-manifest` remains Python-owned, so the budget rule it
        // enforces keeps its single owner.
        let filter = run_python_verb(
            [
                OsString::from("scout"),
                OsString::from("filter-manifest"),
                input.as_os_str().to_owned(),
                filtered.as_os_str().to_owned(),
                OsString::from("--max-archetypes"),
                OsString::from("1"),
                OsString::from("--mode"),
                OsString::from("review"),
            ],
            SCOUT_FILTER_TIMEOUT,
        );
        let filtered_count = archetype_count(&filtered);
        let filter_status = filter.as_ref().map_or_else(
            |_error| String::new(),
            |output| kv_value(&stdout_text(output), "SCOUT_STATUS"),
        );
        let filter_ok = filter
            .as_ref()
            .is_ok_and(|output| output.status().success())
            && (filter_status == "ok" || filter_status == "empty")
            && filtered_count.is_some();
        if filter_ok
            && (raw_count == 0 || filtered_count.unwrap_or(0) > 0)
            && fs::rename(&filtered, &manifest).is_ok()
        {
            status = "ok";
        } else {
            let _written = write_atomic(&manifest, EMPTY_SCOUT_MANIFEST);
        }
    } else {
        let _written = write_atomic(&manifest, EMPTY_SCOUT_MANIFEST);
    }
    let _removed = fs::remove_file(&filtered);
    if status == "ok" {
        let _written = write_atomic(&marker, "eligible\n");
    } else {
        let _removed = fs::remove_file(&marker);
        warn_invalid_coder_scout(producer);
    }
    let _written = write_atomic(
        &tmpdir.join("step2-scout-coder-status.env"),
        &format!(
            "SCOUT_CODER_STATUS={status}\nSCOUT_CODER_MANIFEST={}\nSCOUT_CODER_PRODUCER={producer}\n",
            manifest.display()
        ),
    );
    status.to_owned()
}

/// Warn once that Step 5 will fall back to the static reviewer panel.
fn warn_invalid_coder_scout(producer: &str) {
    let label = match producer {
        "main-agent" => "main agent",
        "subagent" => "Claude subagent",
        _other => "external coder",
    };
    eprintln!(
        "**⚠ implement Step 2: {label} dynamic-archetype manifest missing or invalid; Step 5 will use static reviewers only.**"
    );
}

/// Count a manifest's declared archetypes, or report an unusable manifest.
fn archetype_count(path: &Path) -> Option<usize> {
    let text = fs::read_to_string(path).ok()?;
    let parsed: serde_json::Value = serde_json::from_str(&text).ok()?;
    parsed
        .get("archetypes")
        .and_then(serde_json::Value::as_array)
        .map(Vec::len)
}

/// Derive this clone's tag from `CLONE_TAG`, or from the logical `PWD`.
fn derive_clone_tag_full() -> String {
    let declared = env::var("CLONE_TAG").unwrap_or_default();
    if !declared.is_empty() {
        return declared;
    }
    let pwd = env::var_os("PWD").unwrap_or_default();
    let mut translated: Vec<u8> = pwd_basename(pwd.as_bytes())
        .iter()
        .map(|byte| {
            if CLONE_TAG_ALLOWED.contains(byte) {
                *byte
            } else {
                b'_'
            }
        })
        .collect();
    translated.truncate(CLONE_TAG_MAX_BYTES);
    if translated.is_empty() {
        return "_".to_owned();
    }
    String::from_utf8(translated).unwrap_or_else(|_error| "_".to_owned())
}

/// Match `basename "$PWD"` byte behavior on the logical path string.
fn pwd_basename(pwd: &[u8]) -> Vec<u8> {
    if pwd.is_empty() || pwd == b"/" {
        return b"/".to_vec();
    }
    let Some(last) = pwd.iter().rposition(|byte| *byte != b'/') else {
        return b"/".to_vec();
    };
    let trimmed = &pwd[..=last];
    trimmed
        .rsplit(|byte| *byte == b'/')
        .next()
        .unwrap_or(trimmed)
        .to_vec()
}

/// Read this run's Claude PID, defaulting to the parent that launched us.
fn claude_pid() -> String {
    let declared = env::var("LARCH_CLAUDE_PID").unwrap_or_default();
    if !declared.is_empty() {
        return declared;
    }
    std::os::unix::process::parent_id().to_string()
}

/// Adopt one boolean run flag when the command line left it unset.
fn adopt_boolean(slot: &mut String, path: &Path, key: &str) {
    if slot == "true" || slot == "false" {
        return;
    }
    let value = read_kv_first(path, key);
    if value == "true" || value == "false" {
        *slot = value;
    }
}

/// Adopt one ship-seed flag, defaulting an absent row to `false`.
fn adopt_seed(slot: &mut String, path: &Path, key: &str) {
    if !slot.is_empty() {
        return;
    }
    let value = read_kv_first(path, key);
    *slot = if value.is_empty() {
        "false".to_owned()
    } else {
        value
    };
}

/// Read the adopted issue and run identity one resumed sentinel carries.
fn sentinel_identity(sentinel: &Path) -> (String, String) {
    if !sentinel.is_file() {
        return (String::new(), String::new());
    }
    adoption_sentinel_identity(sentinel)
        .map_or_else(Default::default, |(issue, run_id, _adopted)| {
            (issue, run_id)
        })
}

/// Return the first non-empty candidate, matching the retired owner's helper.
fn first_nonempty(first: &str, second: &str) -> String {
    if first.is_empty() {
        second.to_owned()
    } else {
        first.to_owned()
    }
}

/// Read the first `KEY=value` row from one optional file.
pub fn read_kv_first(path: &Path, key: &str) -> String {
    read_kv_or(path, key, "")
}

/// Read the first `KEY=value` row, or `default` when the row is absent.
pub fn read_kv_or(path: &Path, key: &str, default: &str) -> String {
    if !path.is_file() {
        return default.to_owned();
    }
    let Ok(bytes) = fs::read(path) else {
        return default.to_owned();
    };
    let text = String::from_utf8_lossy(&bytes);
    let prefix = format!("{key}=");
    let lines: Vec<&str> = text.split('\n').collect();
    let last = lines.len().saturating_sub(1);
    for (index, line) in lines.iter().enumerate() {
        // The wire format accepts CRLF, so a CR before the final LF is framing.
        let line = if index < last {
            line.strip_suffix('\r').unwrap_or(line)
        } else {
            line
        };
        if let Some(value) = line.strip_prefix(&prefix) {
            return value.to_owned();
        }
    }
    default.to_owned()
}

/// Read one `KEY=value` row from a captured `KEY=value` stream.
///
/// First duplicate wins, matching the retired bootstrap `_parse_kv(...,
/// first_wins=True)` contract used by Step 0 composition.
pub fn kv_value(text: &str, key: &str) -> String {
    let prefix = format!("{key}=");
    text.lines()
        .find_map(|line| line.strip_prefix(&prefix))
        .unwrap_or_default()
        .to_owned()
}

/// Report whether one vendor binary is reachable on `PATH`.
fn on_path(binary: &str) -> bool {
    binary_on_path(binary, env::var("PATH").ok().as_deref())
}

/// Run one already-owned command and forward its complete contract.
fn forward_verified_larch(arguments: &[OsString]) -> ExitCode {
    let Ok(result) = run_verified_larch(arguments) else {
        eprintln!("step-0-degraded-gate: could not start the degraded-tools gate");
        return ExitCode::from(1);
    };
    write_streams(
        &stdout_text(&result),
        &String::from_utf8_lossy(result.stderr()),
    );
    ExitCode::from(u8::try_from(exit_code_of(&result)).unwrap_or(1))
}

fn stdout_text(output: &ProcessOutput) -> String {
    String::from_utf8_lossy(output.stdout()).into_owned()
}

fn exit_code_of(output: &ProcessOutput) -> i32 {
    output.status().code().unwrap_or(1)
}

/// Forward a captured child's streams in the retired owner's order.
pub fn write_streams(stdout: &str, stderr: &str) {
    if !stdout.is_empty() {
        let mut handle = std::io::stdout().lock();
        let _written = handle.write_all(stdout.as_bytes());
        let _flushed = handle.flush();
    }
    if !stderr.is_empty() {
        let mut handle = std::io::stderr().lock();
        let _written = handle.write_all(stderr.as_bytes());
        let _flushed = handle.flush();
    }
}

/// Print one exact line, bypassing the `KEY=value` newline assertions.
fn print_line(line: &str) {
    let mut handle = std::io::stdout().lock();
    let _written = handle.write_all(line.as_bytes());
    let _newline = handle.write_all(b"\n");
}

/// Publish exact text through the shared same-directory temporary file writer.
pub fn write_atomic(path: &Path, text: &str) -> Result<(), String> {
    if let Some(parent) = path.parent()
        && let Err(error) = fs::create_dir_all(parent)
    {
        return Err(format!("cannot create {}: {error}", parent.display()));
    }
    atomic_write(path, text).map_err(|error| format!("cannot publish {}: {error}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::{kv_value, pwd_basename, read_kv_or, resolve_tmpdir_path};
    use std::path::{Path, PathBuf};

    #[test]
    fn pwd_basename_matches_the_bash_boundary() {
        assert_eq!(pwd_basename(b""), b"/".to_vec());
        assert_eq!(pwd_basename(b"/"), b"/".to_vec());
        assert_eq!(pwd_basename(b"///"), b"/".to_vec());
        assert_eq!(pwd_basename(b"/a/b/"), b"b".to_vec());
        assert_eq!(pwd_basename(b"larch1"), b"larch1".to_vec());
    }

    #[test]
    fn an_absolute_input_is_confined_beneath_the_tmpdir() {
        let tmpdir = Path::new("/tmp/implement");

        assert_eq!(
            resolve_tmpdir_path(tmpdir, "", "raw.json"),
            tmpdir.join("raw.json")
        );
        assert_eq!(
            resolve_tmpdir_path(tmpdir, "/etc/passwd", "raw.json"),
            tmpdir.join("etc/passwd")
        );
        assert_eq!(
            resolve_tmpdir_path(tmpdir, "/tmp/implement/inner.json", "raw.json"),
            PathBuf::from("/tmp/implement/inner.json")
        );
        assert_eq!(
            resolve_tmpdir_path(tmpdir, "nested/raw.json", "raw.json"),
            tmpdir.join("nested/raw.json")
        );
    }

    #[test]
    fn kv_readers_take_the_first_row() {
        assert_eq!(kv_value("A=1\nA=2\n", "A"), "1");
        assert_eq!(kv_value("A=1\n", "B"), "");
        assert_eq!(
            read_kv_or(Path::new("/nonexistent-kv"), "A", "fallback"),
            "fallback"
        );
    }
}
