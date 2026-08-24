//! One-call `/complete-umbrella` Step 0 bootstrap.
//!
//! Composes the existing lifecycle, repository, resume, session, start, Write-hook,
//! and model owners in process and emits one consolidated `KEY=value` envelope.

use crate::{
    agent_commands, github_repository_resolution, run_lifecycle_commands, session_setup_commands,
};
use clap::Args;
use larch_adapters::{
    PathIntent, TemporaryRoot, assert_no_symlink_path_or_ancestors, atomic_write_utf8,
    open_confined_read,
};
use larch_core::{
    CommentPolicy, CrStrip, DuplicateInputPolicy, DuplicatePolicy, EmptyKeyPolicy, KeyPolicy,
    KvDocument, MalformedLinePolicy, ParseOptions, WhitespacePolicy, is_valid_claude_pid, kv_text,
};
use std::{
    collections::BTreeMap,
    env,
    fmt::Write as _,
    fs,
    io::Read as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

const SKILL: &str = "complete-umbrella";
const RUN_LEAVES_STEP: &str = "complete-umbrella-leaves";
const BOOTSTRAP_COPY: &str = "complete-umbrella-bootstrap.env";
const MODEL_COPY: &str = "model.env";
const SESSION_PREFIX: &str = "claude-complete-umbrella";
const WRITE_HOOK_TOKEN: &str = "complete-umbrella";
const LIFECYCLE_KEYS: &[&str] = &[
    "RUN_ID",
    "SKILL",
    "LOG_ROOT",
    "RUN_DIR",
    "CONTEXT_FILE",
    "RUN_LOG_STORAGE",
    "RUN_LOG_STORAGE_REASON",
    "STORAGE_BASE_URI",
    "CLIENT_REPO",
    "TOOL_REPO_URI",
    "RUN_LOGS_URI",
    "STORAGE_PREFLIGHT",
    "PREFLIGHT_OK",
    "LIFECYCLE_STARTED",
];
const RESUME_KEYS: &[&str] = &[
    "RESUME_FOUND",
    "RESUME_ACTION",
    "COMPLETE_UMBRELLA_TMPDIR",
    "COMPLETE_UMBRELLA_POINTER",
    "BGJOB_STEP",
    "CURRENT_LEAF",
    "CURRENT_STEP",
    "TRANSIENT_ATTEMPT_COUNT",
    "CHILD_STATUS",
    "CHILD_FAILURE_CLASS",
    "NEXT_ACTION",
    "FAILED_STEP",
    "FAILED_LEAF",
    "FAILURE_REASON",
];
const CURRENT_STEPS: &[&str] = &["start", "select", "launch", "verify", "audit", "failed"];
const RESUME_ACTIONS: &[&str] = &["wait", "reselect", "needs-design", "failed"];

#[derive(Args)]
pub struct BootstrapArguments {
    #[arg(long)]
    issue: u64,
    #[arg(long, default_value_t = String::new())]
    lifecycle_parent_context: String,
    #[arg(long, action = clap::ArgAction::SetTrue)]
    operator_invoked: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct StageOutput {
    status: u8,
    stdout: String,
    stderr: String,
}

#[derive(Clone, Debug)]
struct Envelope {
    values: BTreeMap<String, String>,
    stdout: String,
    stderr: String,
}

struct BootstrapError {
    stage: String,
    detail: String,
    diagnostics: String,
    tmpdir: Option<PathBuf>,
}

struct OrderedRows {
    rows: Vec<(String, String)>,
}

impl OrderedRows {
    const fn new() -> Self {
        Self { rows: Vec::new() }
    }

    fn insert(&mut self, key: &str, value: String) {
        if let Some(existing) = self.rows.iter_mut().find(|(candidate, _)| candidate == key) {
            existing.1 = value;
            return;
        }
        self.rows.push((key.to_owned(), value));
    }

    fn get(&self, key: &str) -> Option<&str> {
        self.rows
            .iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.as_str())
    }

    fn render(&self) -> Result<String, String> {
        let pairs: Vec<(&str, &str)> = self
            .rows
            .iter()
            .map(|(key, value)| (key.as_str(), value.as_str()))
            .collect();
        kv_text(&pairs).map_err(|error| error.to_string())
    }
}

trait BootstrapStages {
    fn lifecycle_start(&self, repo_root: &Path, parent_context: &str) -> StageOutput;
    fn resolve_repo(&self, repo_root: &Path) -> StageOutput;
    fn resume(&self, repository: &str, issue: u64, claude_pid: u32) -> StageOutput;
    fn session_setup(&self) -> StageOutput;
    fn start(&self, repository: &str, issue: u64, tmpdir: &Path, claude_pid: u32) -> StageOutput;
    fn read_claude_model(&self) -> StageOutput;
}

struct LiveStages;

impl BootstrapStages for LiveStages {
    fn lifecycle_start(&self, repo_root: &Path, parent_context: &str) -> StageOutput {
        let context = (!parent_context.is_empty()).then_some(Path::new(parent_context));
        let (status, stdout, stderr) =
            run_lifecycle_commands::start_for_composer(repo_root, SKILL, context);
        StageOutput {
            status,
            stdout,
            stderr,
        }
    }

    fn resolve_repo(&self, repo_root: &Path) -> StageOutput {
        match github_repository_resolution::resolve_repo_from(repo_root) {
            Ok(repo) => StageOutput {
                status: 0,
                stdout: format!("{repo}\n"),
                stderr: String::new(),
            },
            Err(error) => StageOutput {
                status: 1,
                stdout: String::new(),
                stderr: format!("{error}\n"),
            },
        }
    }

    fn resume(&self, repository: &str, issue: u64, claude_pid: u32) -> StageOutput {
        captured_result(super::captured_resume(
            repository.to_owned(),
            issue,
            claude_pid,
        ))
    }

    fn session_setup(&self) -> StageOutput {
        let (status, stdout, stderr) = session_setup_commands::setup_for_composer(SESSION_PREFIX);
        StageOutput {
            status,
            stdout,
            stderr,
        }
    }

    fn start(&self, repository: &str, issue: u64, tmpdir: &Path, claude_pid: u32) -> StageOutput {
        captured_result(super::captured_start(
            repository.to_owned(),
            issue,
            tmpdir.to_path_buf(),
            claude_pid,
        ))
    }

    fn read_claude_model(&self) -> StageOutput {
        let model = agent_commands::resolve_claude_model_from_environment();
        StageOutput {
            status: 0,
            stdout: format!("CLAUDE_MODEL={model}\n"),
            stderr: String::new(),
        }
    }
}

fn captured_result(result: Result<String, String>) -> StageOutput {
    match result {
        Ok(stdout) => StageOutput {
            status: 0,
            stdout,
            stderr: String::new(),
        },
        Err(error) => StageOutput {
            status: 1,
            stdout: String::new(),
            stderr: format!("{error}\n"),
        },
    }
}

struct BootstrapResult {
    exit_code: u8,
    stdout: String,
    stderr: String,
}

/// Run `complete-umbrella bootstrap` and emit the consolidated envelope.
#[must_use]
pub fn run(arguments: &BootstrapArguments) -> ExitCode {
    let result = bootstrap(
        &LiveStages,
        arguments.issue,
        arguments.operator_invoked,
        &arguments.lifecycle_parent_context,
        &env::vars().collect::<BTreeMap<_, _>>(),
        fallback_pid(),
    );
    print!("{}", result.stdout);
    eprint!("{}", result.stderr);
    ExitCode::from(result.exit_code)
}

fn fallback_pid() -> u32 {
    std::os::unix::process::parent_id()
}

fn bootstrap(
    stages: &dyn BootstrapStages,
    issue: u64,
    operator_invoked: bool,
    lifecycle_parent_context: &str,
    environ: &BTreeMap<String, String>,
    fallback_pid: u32,
) -> BootstrapResult {
    let mut rows = OrderedRows::new();
    let mut warnings = String::new();
    let mut tmpdir = None;
    match bootstrap_inner(
        stages,
        issue,
        operator_invoked,
        lifecycle_parent_context,
        environ,
        fallback_pid,
        &mut rows,
        &mut warnings,
        &mut tmpdir,
    ) {
        Ok(stdout) => BootstrapResult {
            exit_code: 0,
            stdout,
            stderr: warnings,
        },
        Err(error) => failure_result(&mut rows, &mut warnings, &error, tmpdir.as_deref()),
    }
}

#[allow(clippy::too_many_arguments)] // Linear stages retain partial failure state.
fn bootstrap_inner(
    stages: &dyn BootstrapStages,
    issue: u64,
    operator_invoked: bool,
    lifecycle_parent_context: &str,
    environ: &BTreeMap<String, String>,
    fallback_pid: u32,
    rows: &mut OrderedRows,
    warnings: &mut String,
    tmpdir: &mut Option<PathBuf>,
) -> Result<String, BootstrapError> {
    if issue == 0 {
        return Err(stage_error(
            "arguments",
            "--issue must be a positive integer",
        ));
    }
    if !operator_invoked {
        return Err(stage_error("arguments", "--operator-invoked is required"));
    }
    let repo_root = validated_repo_root(environ)?;
    let owner_pid = validated_owner_pid(environ, fallback_pid)?;
    let lifecycle = run_stage(
        stages.lifecycle_start(&repo_root, lifecycle_parent_context),
        "lifecycle-start",
    )?;
    warnings.push_str(&lifecycle.stderr);
    validate_lifecycle(&lifecycle)?;
    for key in LIFECYCLE_KEYS {
        rows.insert(key, require_key(&lifecycle.values, key, "lifecycle-start")?);
    }

    let repository_output = run_command(stages.resolve_repo(&repo_root), "repository-resolve")?;
    warnings.push_str(&repository_output.stderr);
    let repository = validated_repository(&repository_output.stdout)?;
    rows.insert("REPO_ROOT", repo_root.display().to_string());
    rows.insert("REPO", repository.clone());
    rows.insert("UMBRELLA", issue.to_string());
    rows.insert("COMPLETE_UMBRELLA_OWNER_PID", owner_pid.to_string());

    let resume = run_stage(stages.resume(&repository, issue, owner_pid), "resume")?;
    warnings.push_str(&resume.stderr);
    let resume_found = validate_resume(&resume)?;
    rows.insert("RESUME_FOUND", resume_found.clone());
    let session = if resume_found == "true" {
        for key in RESUME_KEYS.iter().skip(1) {
            if let Some(value) = resume.values.get(*key) {
                rows.insert(key, value.clone());
            }
        }
        validated_tmpdir(
            &require_nonempty_row(rows, "COMPLETE_UMBRELLA_TMPDIR", "resume")?,
            "resume",
        )?
    } else {
        let setup = stages.session_setup();
        let envelope = parse_envelope("session-setup", &setup.stdout, &setup.stderr)?;
        if setup.status != 0 {
            let published = envelope
                .values
                .get("SESSION_TMPDIR")
                .filter(|value| !value.is_empty())
                .map(|value| validated_tmpdir(value, "session-setup"))
                .transpose()?;
            return Err(command_failure("session-setup", &setup, published));
        }
        warnings.push_str(&setup.stderr);
        let session = validated_tmpdir(
            &require_nonempty(&envelope.values, "SESSION_TMPDIR", "session-setup")?,
            "session-setup",
        )?;
        rows.insert("SESSION_TMPDIR", session.display().to_string());
        rows.insert("COMPLETE_UMBRELLA_TMPDIR", session.display().to_string());
        let start = run_stage(
            stages.start(&repository, issue, &session, owner_pid),
            "start",
        )?;
        warnings.push_str(&start.stderr);
        rows.insert("RESUME_ACTION", "reselect".to_owned());
        rows.insert("COMPLETE_UMBRELLA_TMPDIR", session.display().to_string());
        rows.insert(
            "COMPLETE_UMBRELLA_POINTER",
            validate_start(&start, issue, &session)?,
        );
        rows.insert("BGJOB_STEP", RUN_LEAVES_STEP.to_owned());
        rows.insert("CURRENT_LEAF", "0".to_owned());
        rows.insert("CURRENT_STEP", "select".to_owned());
        rows.insert("TRANSIENT_ATTEMPT_COUNT", "0".to_owned());
        session
    };
    *tmpdir = Some(session.clone());
    rows.insert("UMBRELLA_STARTED", "true".to_owned());
    rows.insert("SESSION_TMPDIR", session.display().to_string());
    let sentinel = activate_write_sentinel(environ, owner_pid)?;
    rows.insert(
        "COMPLETE_UMBRELLA_WRITE_SENTINEL",
        sentinel.display().to_string(),
    );

    let action = require_nonempty_row(rows, "RESUME_ACTION", "resume")?;
    if action == "wait" || action == "reselect" {
        let (model, model_stderr) = model_for_run(stages, &session)?;
        warnings.push_str(&model_stderr);
        rows.insert("CLAUDE_MODEL", model);
    } else {
        rows.insert("CLAUDE_MODEL", String::new());
    }
    rows.insert("BOOTSTRAP_OK", "true".to_owned());
    let stdout = render_rows(rows, "diagnostic-copy")?;
    diagnostic_copy(&session, &stdout)?;
    Ok(stdout)
}

fn run_command(output: StageOutput, stage: &str) -> Result<StageOutput, BootstrapError> {
    if output.status != 0 {
        return Err(command_failure(stage, &output, None));
    }
    Ok(output)
}

fn run_stage(output: StageOutput, stage: &str) -> Result<Envelope, BootstrapError> {
    let output = run_command(output, stage)?;
    parse_envelope(stage, &output.stdout, &output.stderr)
}

fn parse_envelope(stage: &str, stdout: &str, stderr: &str) -> Result<Envelope, BootstrapError> {
    if has_wire_break(&stdout.replace('\n', "")) {
        return Err(BootstrapError {
            stage: stage.to_owned(),
            detail: single_line("invalid line break in machine stdout"),
            diagnostics: stderr.to_owned(),
            tmpdir: None,
        });
    }
    let mut options = ParseOptions::legacy();
    options.malformed_lines = MalformedLinePolicy::Skip;
    options.key_policy = Some(KeyPolicy::Environment);
    options.empty_keys = EmptyKeyPolicy::Keep;
    options.comments = CommentPolicy::Keep;
    options.key_whitespace = WhitespacePolicy::Preserve;
    options.value_whitespace = WhitespacePolicy::Preserve;
    options.cr_strip = CrStrip::None;
    options.duplicates = DuplicateInputPolicy::Allow;
    let document = KvDocument::parse(stdout, options).map_err(|_| BootstrapError {
        stage: stage.to_owned(),
        detail: single_line("malformed non-KV stdout"),
        diagnostics: stderr.to_owned(),
        tmpdir: None,
    })?;
    let source_row_count = stdout.split('\n').filter(|line| !line.is_empty()).count();
    if document.rows().len() != source_row_count {
        return Err(BootstrapError {
            stage: stage.to_owned(),
            detail: single_line("malformed non-KV stdout"),
            diagnostics: stderr.to_owned(),
            tmpdir: None,
        });
    }
    let grouped = document.select_all();
    let duplicates: Vec<&str> = grouped
        .iter()
        .filter(|(_, values)| values.len() != 1)
        .map(|(key, _)| key.as_str())
        .collect();
    if !duplicates.is_empty() {
        return Err(BootstrapError {
            stage: stage.to_owned(),
            detail: single_line(&format!(
                "duplicate machine key(s): {}",
                duplicates.join(", ")
            )),
            diagnostics: stderr.to_owned(),
            tmpdir: None,
        });
    }
    Ok(Envelope {
        values: document.select(DuplicatePolicy::First),
        stdout: stdout.to_owned(),
        stderr: stderr.to_owned(),
    })
}

fn validate_lifecycle(envelope: &Envelope) -> Result<(), BootstrapError> {
    const STAGE: &str = "lifecycle-start";
    for key in LIFECYCLE_KEYS {
        require_key(&envelope.values, key, STAGE)?;
    }
    for key in [
        "RUN_ID",
        "LOG_ROOT",
        "RUN_DIR",
        "CONTEXT_FILE",
        "CLIENT_REPO",
    ] {
        require_nonempty(&envelope.values, key, STAGE)?;
    }
    if envelope.values.get("SKILL").map(String::as_str) != Some(SKILL) {
        return Err(stage_error(
            STAGE,
            "lifecycle start returned the wrong SKILL",
        ));
    }
    if envelope.values.get("LIFECYCLE_STARTED").map(String::as_str) != Some("true")
        || envelope.values.get("PREFLIGHT_OK").map(String::as_str) != Some("true")
    {
        return Err(stage_error(STAGE, "lifecycle start did not report success"));
    }
    let storage = envelope
        .values
        .get("RUN_LOG_STORAGE")
        .map(String::as_str)
        .unwrap_or_default();
    let preflight = envelope
        .values
        .get("STORAGE_PREFLIGHT")
        .map(String::as_str)
        .unwrap_or_default();
    if !matches!(
        (storage, preflight),
        ("enabled", "ok") | ("disabled", "skipped-disabled")
    ) {
        return Err(stage_error(
            STAGE,
            "lifecycle start returned an invalid storage state",
        ));
    }
    Ok(())
}

fn validated_repo_root(environ: &BTreeMap<String, String>) -> Result<PathBuf, BootstrapError> {
    const STAGE: &str = "repository-root";
    let project_dir = environ
        .get("CLAUDE_PROJECT_DIR")
        .cloned()
        .unwrap_or_default();
    if project_dir.is_empty() {
        return Err(stage_error(STAGE, "CLAUDE_PROJECT_DIR is required"));
    }
    require_wire_value(&project_dir, "CLAUDE_PROJECT_DIR", STAGE)?;
    let root = Path::new(&project_dir)
        .canonicalize()
        .map_err(|error| stage_error(STAGE, &error.to_string()))?;
    if !root.is_dir() {
        return Err(stage_error(STAGE, "CLAUDE_PROJECT_DIR is not a directory"));
    }
    require_wire_value(&root.display().to_string(), "REPO_ROOT", STAGE)?;
    Ok(root)
}

fn validated_owner_pid(
    environ: &BTreeMap<String, String>,
    fallback_pid: u32,
) -> Result<u32, BootstrapError> {
    let raw = environ
        .get("LARCH_CLAUDE_PID")
        .filter(|value| !value.is_empty())
        .cloned()
        .or_else(|| {
            environ
                .get("CLAUDE_PID")
                .filter(|value| !value.is_empty())
                .cloned()
        })
        .unwrap_or_else(|| fallback_pid.to_string());
    if !is_valid_claude_pid(&raw) {
        return Err(stage_error("owner-pid", "invalid CLAUDE_PID"));
    }
    raw.parse()
        .map_err(|_| stage_error("owner-pid", "invalid CLAUDE_PID"))
}

fn validated_repository(stdout: &str) -> Result<String, BootstrapError> {
    let repository = stdout.strip_suffix('\n').unwrap_or(stdout).to_owned();
    require_wire_value(&repository, "REPO", "repository-resolve")?;
    if !github_repository_resolution::validate_repo_slug(&repository) {
        return Err(stage_error(
            "repository-resolve",
            "repository must use exact OWNER/REPO syntax",
        ));
    }
    Ok(repository)
}

fn validated_tmpdir(raw: &str, stage: &str) -> Result<PathBuf, BootstrapError> {
    require_wire_value(raw, "SESSION_TMPDIR", stage)?;
    let path = PathBuf::from(raw);
    if !path.is_absolute() {
        return Err(stage_error(stage, "session tmpdir must be absolute"));
    }
    TemporaryRoot::resolve(Some(&path)).map_err(|error| stage_error(stage, &error.to_string()))?;
    Ok(path)
}

fn validate_pointer(raw: &str, stage: &str) -> Result<String, BootstrapError> {
    require_wire_value(raw, "COMPLETE_UMBRELLA_POINTER", stage)?;
    let path = PathBuf::from(raw);
    if !path.is_absolute() {
        return Err(stage_error(stage, "run pointer must be absolute"));
    }
    assert_no_symlink_path_or_ancestors(&path)
        .map_err(|error| stage_error(stage, &format!("run pointer is unavailable: {error}")))?;
    let metadata = path
        .symlink_metadata()
        .map_err(|error| stage_error(stage, &format!("run pointer is unavailable: {error}")))?;
    if !metadata.is_file() {
        return Err(stage_error(stage, "run pointer is not a regular file"));
    }
    Ok(raw.to_owned())
}

fn validate_resume(envelope: &Envelope) -> Result<String, BootstrapError> {
    const STAGE: &str = "resume";
    let found = require_key(&envelope.values, "RESUME_FOUND", STAGE)?;
    if found == "false" {
        return Ok(found);
    }
    if found != "true" {
        return Err(stage_error(STAGE, "invalid RESUME_FOUND"));
    }
    let action = require_key(&envelope.values, "RESUME_ACTION", STAGE)?;
    if !RESUME_ACTIONS.contains(&action.as_str()) {
        return Err(stage_error(STAGE, "invalid RESUME_ACTION"));
    }
    validated_tmpdir(
        &require_nonempty(&envelope.values, "COMPLETE_UMBRELLA_TMPDIR", STAGE)?,
        STAGE,
    )?;
    validate_pointer(
        &require_nonempty(&envelope.values, "COMPLETE_UMBRELLA_POINTER", STAGE)?,
        STAGE,
    )?;
    if require_key(&envelope.values, "BGJOB_STEP", STAGE)? != RUN_LEAVES_STEP {
        return Err(stage_error(STAGE, "invalid BGJOB_STEP"));
    }
    let current_step = require_key(&envelope.values, "CURRENT_STEP", STAGE)?;
    if !CURRENT_STEPS.contains(&current_step.as_str()) {
        return Err(stage_error(STAGE, "invalid CURRENT_STEP"));
    }
    require_uint(
        &require_key(&envelope.values, "CURRENT_LEAF", STAGE)?,
        "CURRENT_LEAF",
        STAGE,
    )?;
    require_uint(
        &require_key(&envelope.values, "TRANSIENT_ATTEMPT_COUNT", STAGE)?,
        "TRANSIENT_ATTEMPT_COUNT",
        STAGE,
    )?;
    if action == "needs-design" || action == "failed" {
        let expected_next = if action == "needs-design" {
            "needs-design"
        } else {
            "failed"
        };
        if require_key(&envelope.values, "NEXT_ACTION", STAGE)? != expected_next {
            return Err(stage_error(STAGE, "invalid NEXT_ACTION"));
        }
        require_nonempty(&envelope.values, "FAILED_STEP", STAGE)?;
        require_uint(
            &require_key(&envelope.values, "FAILED_LEAF", STAGE)?,
            "FAILED_LEAF",
            STAGE,
        )?;
        require_nonempty(&envelope.values, "FAILURE_REASON", STAGE)?;
    }
    Ok(found)
}

fn validate_start(
    envelope: &Envelope,
    issue: u64,
    tmpdir: &Path,
) -> Result<String, BootstrapError> {
    const STAGE: &str = "start";
    if require_key(&envelope.values, "UMBRELLA_STARTED", STAGE)? != "true" {
        return Err(stage_error(
            STAGE,
            "start did not report UMBRELLA_STARTED=true",
        ));
    }
    let started_issue = require_uint(
        &require_key(&envelope.values, "UMBRELLA_ISSUE", STAGE)?,
        "UMBRELLA_ISSUE",
        STAGE,
    )?;
    if started_issue != issue {
        return Err(stage_error(
            STAGE,
            "start returned the wrong umbrella issue",
        ));
    }
    let started_tmpdir = validated_tmpdir(
        &require_nonempty(&envelope.values, "COMPLETE_UMBRELLA_TMPDIR", STAGE)?,
        STAGE,
    )?;
    if !same_existing_dir(&started_tmpdir, tmpdir) {
        return Err(stage_error(
            STAGE,
            "start returned a different session tmpdir",
        ));
    }
    validate_pointer(
        &require_nonempty(&envelope.values, "COMPLETE_UMBRELLA_POINTER", STAGE)?,
        STAGE,
    )
}

fn activate_write_sentinel(
    environ: &BTreeMap<String, String>,
    owner_pid: u32,
) -> Result<PathBuf, BootstrapError> {
    const STAGE: &str = "write-hook";
    let xdg = environ
        .get("XDG_CACHE_HOME")
        .filter(|value| !value.is_empty());
    let home = environ.get("HOME").filter(|value| !value.is_empty());
    let cache_home = if let Some(value) = xdg {
        require_wire_value(value, "XDG_CACHE_HOME", STAGE)?;
        PathBuf::from(value)
    } else if let Some(value) = home {
        require_wire_value(value, "HOME", STAGE)?;
        Path::new(value).join(".cache")
    } else {
        return Err(stage_error(STAGE, "XDG_CACHE_HOME and HOME are unset"));
    };
    let sentinel = session_setup_commands::activate_named_write_sentinel_in(
        &cache_home,
        WRITE_HOOK_TOKEN,
        owner_pid,
    )
    .map_err(|error| stage_error(STAGE, &error))?;
    require_wire_value(
        &sentinel.display().to_string(),
        "COMPLETE_UMBRELLA_WRITE_SENTINEL",
        STAGE,
    )?;
    Ok(sentinel)
}

fn model_for_run(
    stages: &dyn BootstrapStages,
    tmpdir: &Path,
) -> Result<(String, String), BootstrapError> {
    let model_path = tmpdir.join(MODEL_COPY);
    if model_present(&model_path, tmpdir)? {
        let text = read_model_copy(&model_path, tmpdir)?;
        return Ok((validated_model(&text, "model-read")?, String::new()));
    }
    let envelope = run_stage(stages.read_claude_model(), "model-resolve")?;
    let model =
        validated_model(&envelope.stdout, "model-resolve").map_err(|error| BootstrapError {
            stage: error.stage,
            detail: error.detail,
            diagnostics: envelope.stderr.clone(),
            tmpdir: None,
        })?;
    write_session_file(tmpdir, &model_path, &envelope.stdout, "model-copy")?;
    Ok((model, envelope.stderr))
}

fn model_present(path: &Path, tmpdir: &Path) -> Result<bool, BootstrapError> {
    if !path.exists() {
        return Ok(false);
    }
    let root = temporary_root(tmpdir, "model-read")?;
    root.confine(
        path.strip_prefix(tmpdir)
            .map_err(|_| stage_error("model-read", "model copy escapes the session tmpdir"))?,
        PathIntent::Read,
    )
    .map_err(|error| stage_error("model-read", &error.to_string()))?;
    let metadata = path
        .symlink_metadata()
        .map_err(|error| stage_error("model-read", &error.to_string()))?;
    Ok(metadata.is_file())
}

fn read_model_copy(path: &Path, tmpdir: &Path) -> Result<String, BootstrapError> {
    const STAGE: &str = "model-read";
    let root = temporary_root(tmpdir, STAGE)?;
    let confined = root
        .confine(
            path.strip_prefix(tmpdir)
                .map_err(|_| stage_error(STAGE, "model copy escapes the session tmpdir"))?,
            PathIntent::Read,
        )
        .map_err(|error| stage_error(STAGE, &error.to_string()))?;
    let mut file =
        open_confined_read(&confined).map_err(|error| stage_error(STAGE, &error.to_string()))?;
    let mut text = String::new();
    file.read_to_string(&mut text)
        .map_err(|error| stage_error(STAGE, &error.to_string()))?;
    if text.contains('\r') {
        return Err(stage_error(
            STAGE,
            "carriage return not allowed in model copy",
        ));
    }
    Ok(text)
}

fn validated_model(text: &str, stage: &str) -> Result<String, BootstrapError> {
    let envelope = parse_envelope(stage, text, "")?;
    let model = require_nonempty(&envelope.values, "CLAUDE_MODEL", stage)?;
    if model == "unknown" || model.chars().any(char::is_whitespace) {
        return Err(stage_error(stage, "invalid CLAUDE_MODEL"));
    }
    Ok(model)
}

fn diagnostic_copy(tmpdir: &Path, text: &str) -> Result<(), BootstrapError> {
    write_session_file(
        tmpdir,
        &tmpdir.join(BOOTSTRAP_COPY),
        text,
        "diagnostic-copy",
    )
}

fn write_session_file(
    tmpdir: &Path,
    path: &Path,
    text: &str,
    stage: &str,
) -> Result<(), BootstrapError> {
    let root = temporary_root(tmpdir, stage)?;
    let confined = root
        .confine(
            path.strip_prefix(tmpdir)
                .map_err(|_| stage_error(stage, "session copy escapes the session tmpdir"))?,
            PathIntent::Write,
        )
        .map_err(|error| stage_error(stage, &error.to_string()))?;
    atomic_write_utf8(&confined, text, 0o600)
        .map_err(|error| stage_error(stage, &error.to_string()))
}

fn temporary_root(tmpdir: &Path, stage: &str) -> Result<TemporaryRoot, BootstrapError> {
    TemporaryRoot::resolve(Some(tmpdir)).map_err(|error| stage_error(stage, &error.to_string()))
}

fn failure_result(
    rows: &mut OrderedRows,
    warnings: &mut String,
    error: &BootstrapError,
    tmpdir: Option<&Path>,
) -> BootstrapResult {
    let diagnostic_tmpdir = tmpdir.or(error.tmpdir.as_deref());
    if let Some(published) = &error.tmpdir {
        if rows.get("SESSION_TMPDIR").is_none() {
            rows.insert("SESSION_TMPDIR", published.display().to_string());
        }
        if rows.get("COMPLETE_UMBRELLA_TMPDIR").is_none() {
            rows.insert("COMPLETE_UMBRELLA_TMPDIR", published.display().to_string());
        }
    }
    rows.insert("BOOTSTRAP_OK", "false".to_owned());
    rows.insert("BOOTSTRAP_STAGE", error.stage.clone());
    rows.insert("BOOTSTRAP_ERROR", error.detail.clone());
    let stdout = render_rows(rows, "diagnostic-copy").unwrap_or_else(|_| {
        format!(
            "BOOTSTRAP_OK=false\nBOOTSTRAP_STAGE={}\nBOOTSTRAP_ERROR={}\n",
            error.stage, error.detail
        )
    });
    if let Some(path) = diagnostic_tmpdir
        && error.stage != "diagnostic-copy"
        && let Err(copy_error) = diagnostic_copy(path, &stdout)
    {
        let _ = writeln!(
            warnings,
            "complete-umbrella bootstrap diagnostic copy failed: {}",
            copy_error.detail
        );
    }
    warnings.push_str(&error.diagnostics);
    let _ = writeln!(
        warnings,
        "ERROR: complete-umbrella bootstrap failed at stage={}: {}",
        error.stage, error.detail
    );
    BootstrapResult {
        exit_code: 1,
        stdout,
        stderr: warnings.clone(),
    }
}

fn render_rows(rows: &OrderedRows, stage: &str) -> Result<String, BootstrapError> {
    rows.render().map_err(|error| stage_error(stage, &error))
}

fn command_failure(stage: &str, output: &StageOutput, tmpdir: Option<PathBuf>) -> BootstrapError {
    let detail = if !output.stderr.is_empty() {
        output.stderr.as_str()
    } else if !output.stdout.is_empty() {
        output.stdout.as_str()
    } else {
        "command exited 1"
    };
    BootstrapError {
        stage: stage.to_owned(),
        detail: single_line(detail),
        diagnostics: output.stderr.clone(),
        tmpdir,
    }
}

fn require_key(
    values: &BTreeMap<String, String>,
    key: &str,
    stage: &str,
) -> Result<String, BootstrapError> {
    values
        .get(key)
        .cloned()
        .ok_or_else(|| stage_error(stage, &format!("missing {key}")))
}

fn require_nonempty(
    values: &BTreeMap<String, String>,
    key: &str,
    stage: &str,
) -> Result<String, BootstrapError> {
    let value = require_key(values, key, stage)?;
    if value.is_empty() {
        return Err(stage_error(stage, &format!("empty {key}")));
    }
    Ok(value)
}

fn require_nonempty_row(
    rows: &OrderedRows,
    key: &str,
    stage: &str,
) -> Result<String, BootstrapError> {
    let value = rows
        .get(key)
        .ok_or_else(|| stage_error(stage, &format!("missing {key}")))?;
    if value.is_empty() {
        return Err(stage_error(stage, &format!("empty {key}")));
    }
    Ok(value.to_owned())
}

fn require_uint(value: &str, key: &str, stage: &str) -> Result<u64, BootstrapError> {
    if !value.is_ascii() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(stage_error(stage, &format!("invalid {key}")));
    }
    value
        .parse()
        .map_err(|_| stage_error(stage, &format!("invalid {key}")))
}

fn require_wire_value(value: &str, key: &str, stage: &str) -> Result<(), BootstrapError> {
    if has_wire_break(value) {
        return Err(stage_error(stage, &format!("invalid line break in {key}")));
    }
    Ok(())
}

fn same_existing_dir(left: &Path, right: &Path) -> bool {
    match (fs::canonicalize(left), fs::canonicalize(right)) {
        (Ok(first), Ok(second)) => first == second,
        _ => left == right,
    }
}

fn has_wire_break(value: &str) -> bool {
    value.chars().any(|character| {
        matches!(
            character,
            '\0' | '\n'
                | '\r'
                | '\u{0b}'
                | '\u{0c}'
                | '\u{1c}'
                | '\u{1d}'
                | '\u{1e}'
                | '\u{85}'
                | '\u{2028}'
                | '\u{2029}'
        )
    })
}

fn single_line(value: &str) -> String {
    let sanitized: String = value
        .chars()
        .map(|character| {
            if has_wire_break(&character.to_string()) {
                ' '
            } else {
                character
            }
        })
        .collect();
    let collapsed = sanitized.split_whitespace().collect::<Vec<_>>().join(" ");
    let truncated: String = collapsed.chars().take(500).collect();
    if truncated.is_empty() {
        "stage failed".to_owned()
    } else {
        truncated
    }
}

fn stage_error(stage: &str, detail: &str) -> BootstrapError {
    BootstrapError {
        stage: stage.to_owned(),
        detail: single_line(detail),
        diagnostics: String::new(),
        tmpdir: None,
    }
}

#[cfg(test)]
mod tests {
    use super::{BootstrapStages, StageOutput, bootstrap};
    use std::{
        cell::{Cell, RefCell},
        collections::BTreeMap,
        fs,
        os::unix::fs::PermissionsExt as _,
        path::{Path, PathBuf},
    };
    use tempfile::TempDir;

    struct ScriptedStages {
        responses: Vec<StageOutput>,
        index: Cell<usize>,
        calls: RefCell<Vec<String>>,
    }

    impl ScriptedStages {
        fn new(responses: Vec<StageOutput>) -> Self {
            Self {
                responses,
                index: Cell::new(0),
                calls: RefCell::new(Vec::new()),
            }
        }

        fn next(&self, name: &str) -> StageOutput {
            self.calls.borrow_mut().push(name.to_owned());
            let index = self.index.get();
            self.index.set(index + 1);
            self.responses.get(index).cloned().unwrap_or(StageOutput {
                status: 1,
                stdout: String::new(),
                stderr: "no scripted response\n".to_owned(),
            })
        }
    }

    impl BootstrapStages for ScriptedStages {
        fn lifecycle_start(&self, _repo_root: &Path, _parent_context: &str) -> StageOutput {
            self.next("lifecycle-start")
        }

        fn resolve_repo(&self, _repo_root: &Path) -> StageOutput {
            self.next("repository-resolve")
        }

        fn resume(&self, _repository: &str, _issue: u64, _claude_pid: u32) -> StageOutput {
            self.next("resume")
        }

        fn session_setup(&self) -> StageOutput {
            self.next("session-setup")
        }

        fn start(
            &self,
            _repository: &str,
            _issue: u64,
            _tmpdir: &Path,
            _claude_pid: u32,
        ) -> StageOutput {
            self.next("start")
        }

        fn read_claude_model(&self) -> StageOutput {
            self.next("model-resolve")
        }
    }

    fn ok(stdout: &str) -> StageOutput {
        StageOutput {
            status: 0,
            stdout: stdout.to_owned(),
            stderr: String::new(),
        }
    }

    fn failed(stderr: &str) -> StageOutput {
        StageOutput {
            status: 1,
            stdout: String::new(),
            stderr: stderr.to_owned(),
        }
    }

    fn lifecycle() -> String {
        "RUN_ID=run-8651\nSKILL=complete-umbrella\nLOG_ROOT=/tmp/larch-log\n\
         RUN_DIR=/tmp/larch-run\nCONTEXT_FILE=/tmp/larch-context.json\n\
         RUN_LOG_STORAGE=disabled\nRUN_LOG_STORAGE_REASON=config-file-missing\n\
         STORAGE_BASE_URI=\nCLIENT_REPO=larch\nTOOL_REPO_URI=\nRUN_LOGS_URI=\n\
         STORAGE_PREFLIGHT=skipped-disabled\nPREFLIGHT_OK=true\nLIFECYCLE_STARTED=true\n"
            .to_owned()
    }

    struct Fixture {
        _root: TempDir,
        repo: PathBuf,
        home: PathBuf,
        session: PathBuf,
        pointer: PathBuf,
        environ: BTreeMap<String, String>,
    }

    fn fixture() -> Fixture {
        let root = TempDir::new().expect("tempdir");
        let repo = root.path().join("repo");
        let home = root.path().join("home");
        let session = root.path().join("session");
        fs::create_dir(&repo).expect("repo");
        fs::create_dir(&home).expect("home");
        fs::create_dir(&session).expect("session");
        let pointer = home.join(".cache/larch/sessions/pointer.env");
        fs::create_dir_all(pointer.parent().expect("pointer parent")).expect("pointer dir");
        fs::write(&pointer, "pointer\n").expect("pointer");
        let mut environ = BTreeMap::new();
        environ.insert("CLAUDE_PROJECT_DIR".to_owned(), repo.display().to_string());
        environ.insert("HOME".to_owned(), home.display().to_string());
        environ.insert("LARCH_CLAUDE_PID".to_owned(), "4242".to_owned());
        Fixture {
            _root: root,
            repo,
            home,
            session,
            pointer,
            environ,
        }
    }

    fn fresh_responses(session: &Path, pointer: &Path) -> Vec<StageOutput> {
        vec![
            ok(&lifecycle()),
            ok("character-ai/larch\n"),
            ok("RESUME_FOUND=false\n"),
            ok(&format!(
                "SESSION_TMPDIR={}\nSESSION_ID=test-session\n",
                session.display()
            )),
            ok(&format!(
                "UMBRELLA_STARTED=true\nUMBRELLA_ISSUE=8651\nCOMPLETE_UMBRELLA_TMPDIR={}\nCOMPLETE_UMBRELLA_POINTER={}\n",
                session.display(),
                pointer.display()
            )),
            ok("CLAUDE_MODEL=claude-opus-4-8\n"),
        ]
    }

    #[test]
    fn fresh_bootstrap_emits_one_validated_block_and_internal_copies() {
        let fixture = fixture();
        let stages = ScriptedStages::new(fresh_responses(&fixture.session, &fixture.pointer));
        let result = bootstrap(
            &stages,
            8651,
            true,
            "/tmp/parent-context.json",
            &fixture.environ,
            999,
        );
        assert_eq!(result.exit_code, 0);
        assert_eq!(result.stderr, "");
        assert_eq!(result.stdout.matches("BOOTSTRAP_OK=true\n").count(), 1);
        for row in [
            "REPO=character-ai/larch\n",
            "UMBRELLA_STARTED=true\n",
            &format!("SESSION_TMPDIR={}\n", fixture.session.display()),
            &format!("COMPLETE_UMBRELLA_TMPDIR={}\n", fixture.session.display()),
            "RESUME_ACTION=reselect\n",
            "CLAUDE_MODEL=claude-opus-4-8\n",
        ] {
            assert!(result.stdout.contains(row), "missing {row}");
        }
        assert_eq!(
            fs::read_to_string(fixture.session.join("complete-umbrella-bootstrap.env")).unwrap(),
            result.stdout
        );
        assert_eq!(
            fs::read_to_string(fixture.session.join("model.env")).unwrap(),
            "CLAUDE_MODEL=claude-opus-4-8\n"
        );
        let sentinel = result
            .stdout
            .lines()
            .find_map(|line| line.strip_prefix("COMPLETE_UMBRELLA_WRITE_SENTINEL="))
            .map(PathBuf::from)
            .expect("sentinel");
        assert!(sentinel.is_file());
        assert_eq!(
            sentinel.metadata().unwrap().permissions().mode() & 0o777,
            0o600
        );
        assert_eq!(
            stages.calls.borrow().as_slice(),
            [
                "lifecycle-start",
                "repository-resolve",
                "resume",
                "session-setup",
                "start",
                "model-resolve",
            ]
        );
        let _ = fixture.repo;
        let _ = fixture.home;
    }

    #[test]
    fn resume_reuses_the_existing_tmpdir_and_pinned_model() {
        let fixture = fixture();
        fs::write(
            fixture.session.join("model.env"),
            "CLAUDE_MODEL=claude-sonnet-4-6\n",
        )
        .unwrap();
        let stages = ScriptedStages::new(vec![
            ok(&lifecycle()),
            ok("character-ai/larch\n"),
            ok(&format!(
                "RESUME_FOUND=true\nRESUME_ACTION=wait\nCOMPLETE_UMBRELLA_TMPDIR={}\n\
                 COMPLETE_UMBRELLA_POINTER={}\nBGJOB_STEP=complete-umbrella-leaves\n\
                 CURRENT_LEAF=8653\nCURRENT_STEP=launch\nTRANSIENT_ATTEMPT_COUNT=2\n",
                fixture.session.display(),
                fixture.pointer.display()
            )),
        ]);
        let result = bootstrap(&stages, 8651, true, "", &fixture.environ, 999);
        assert_eq!(result.exit_code, 0);
        assert!(result.stdout.contains("RESUME_ACTION=wait\n"));
        assert!(result.stdout.contains("CLAUDE_MODEL=claude-sonnet-4-6\n"));
        assert_eq!(stages.calls.borrow().len(), 3);
    }

    #[test]
    fn terminal_resume_skips_model_resolution() {
        let fixture = fixture();
        let stages = ScriptedStages::new(vec![
            ok(&lifecycle()),
            ok("character-ai/larch\n"),
            ok(&format!(
                "RESUME_FOUND=true\nRESUME_ACTION=needs-design\nCOMPLETE_UMBRELLA_TMPDIR={}\n\
                 COMPLETE_UMBRELLA_POINTER={}\nBGJOB_STEP=complete-umbrella-leaves\n\
                 CURRENT_LEAF=8653\nCURRENT_STEP=failed\nTRANSIENT_ATTEMPT_COUNT=0\n\
                 NEXT_ACTION=needs-design\nFAILED_STEP=run-child\nFAILED_LEAF=8653\n\
                 FAILURE_REASON=plan is malformed\n",
                fixture.session.display(),
                fixture.pointer.display()
            )),
        ]);
        let result = bootstrap(&stages, 8651, true, "", &fixture.environ, 999);
        assert_eq!(result.exit_code, 0);
        assert!(result.stdout.contains("CLAUDE_MODEL=\n"));
        assert!(result.stdout.contains("NEXT_ACTION=needs-design\n"));
        assert_eq!(stages.calls.borrow().len(), 3);
    }

    #[test]
    fn every_command_failure_names_its_stage() {
        let cases = [
            (0, "lifecycle-start"),
            (1, "repository-resolve"),
            (2, "resume"),
            (3, "session-setup"),
            (4, "start"),
            (5, "model-resolve"),
        ];
        for (failed_index, expected_stage) in cases {
            let fixture = fixture();
            let mut responses = fresh_responses(&fixture.session, &fixture.pointer);
            responses[failed_index] = failed("backend unavailable\n");
            let stages = ScriptedStages::new(responses);
            let result = bootstrap(&stages, 8651, true, "", &fixture.environ, 999);
            assert_eq!(result.exit_code, 1, "{expected_stage}");
            assert!(
                result
                    .stdout
                    .contains(&format!("BOOTSTRAP_STAGE={expected_stage}\n")),
                "{expected_stage}"
            );
            assert!(
                result
                    .stderr
                    .contains(&format!("failed at stage={expected_stage}")),
                "{expected_stage}"
            );
            assert!(result.stdout.contains("BOOTSTRAP_OK=false\n"));
            if failed_index > 0 {
                assert!(result.stdout.contains("LIFECYCLE_STARTED=true\n"));
            }
            if expected_stage == "start" {
                assert!(
                    result
                        .stdout
                        .contains(&format!("SESSION_TMPDIR={}\n", fixture.session.display()))
                );
                assert!(result.stdout.contains(&format!(
                    "COMPLETE_UMBRELLA_TMPDIR={}\n",
                    fixture.session.display()
                )));
            }
        }
    }

    #[test]
    fn stage_stdout_rejects_non_kv_noise() {
        let fixture = fixture();
        let stages = ScriptedStages::new(vec![ok(&format!("{}unexpected prose\n", lifecycle()))]);
        let result = bootstrap(&stages, 8651, true, "", &fixture.environ, 999);
        assert_eq!(result.exit_code, 1);
        assert!(result.stdout.contains("BOOTSTRAP_STAGE=lifecycle-start\n"));
        assert!(
            result
                .stdout
                .contains("BOOTSTRAP_ERROR=malformed non-KV stdout\n")
        );
        assert!(stages.calls.borrow().as_slice() == ["lifecycle-start"]);
    }

    #[test]
    fn repository_root_rejects_wire_line_breaks() {
        let root = TempDir::new().expect("tempdir");
        let repo = root.path().join("repo\nFORGED=true");
        let home = root.path().join("home");
        fs::create_dir(&repo).unwrap();
        fs::create_dir(&home).unwrap();
        let mut environ = BTreeMap::new();
        environ.insert("CLAUDE_PROJECT_DIR".to_owned(), repo.display().to_string());
        environ.insert("HOME".to_owned(), home.display().to_string());
        environ.insert("LARCH_CLAUDE_PID".to_owned(), "4242".to_owned());
        let stages = ScriptedStages::new(Vec::new());
        let result = bootstrap(&stages, 8651, true, "", &environ, 999);
        assert_eq!(result.exit_code, 1);
        assert!(result.stdout.contains("BOOTSTRAP_STAGE=repository-root\n"));
        assert!(!result.stdout.contains("\nFORGED=true\n"));
        assert!(stages.calls.borrow().is_empty());
    }

    #[test]
    fn oversized_owner_pid_fails_at_its_validation_stage() {
        let fixture = fixture();
        let mut environ = fixture.environ.clone();
        environ.insert("LARCH_CLAUDE_PID".to_owned(), "9".repeat(5_000));
        let stages = ScriptedStages::new(Vec::new());
        let result = bootstrap(&stages, 8651, true, "", &environ, 999);
        assert_eq!(result.exit_code, 1);
        assert!(result.stdout.contains("BOOTSTRAP_STAGE=owner-pid\n"));
        assert!(
            result
                .stdout
                .contains("BOOTSTRAP_ERROR=invalid CLAUDE_PID\n")
        );
        assert!(stages.calls.borrow().is_empty());
    }

    #[test]
    fn failed_session_setup_preserves_its_published_tmpdir() {
        let fixture = fixture();
        let stages = ScriptedStages::new(vec![
            ok(&lifecycle()),
            ok("character-ai/larch\n"),
            ok("RESUME_FOUND=false\n"),
            StageOutput {
                status: 1,
                stdout: format!(
                    "SESSION_TMPDIR={}\nSESSION_ID=test-session\n",
                    fixture.session.display()
                ),
                stderr: "session environment write failed\n".to_owned(),
            },
        ]);
        let result = bootstrap(&stages, 8651, true, "", &fixture.environ, 999);
        assert_eq!(result.exit_code, 1);
        assert!(result.stdout.contains("BOOTSTRAP_STAGE=session-setup\n"));
        assert!(
            result
                .stdout
                .contains(&format!("SESSION_TMPDIR={}\n", fixture.session.display()))
        );
        assert!(result.stdout.contains(&format!(
            "COMPLETE_UMBRELLA_TMPDIR={}\n",
            fixture.session.display()
        )));
        assert_eq!(
            fs::read_to_string(fixture.session.join("complete-umbrella-bootstrap.env")).unwrap(),
            result.stdout
        );
    }

    #[test]
    fn write_hook_failure_is_named_and_keeps_the_session() {
        let fixture = fixture();
        let mut environ = fixture.environ.clone();
        environ.remove("HOME");
        let mut responses = fresh_responses(&fixture.session, &fixture.pointer);
        responses.pop();
        let stages = ScriptedStages::new(responses);
        let result = bootstrap(&stages, 8651, true, "", &environ, 999);
        assert_eq!(result.exit_code, 1);
        assert!(result.stdout.contains("BOOTSTRAP_STAGE=write-hook\n"));
        assert!(fixture.session.is_dir());
        assert!(
            fixture
                .session
                .join("complete-umbrella-bootstrap.env")
                .is_file()
        );
    }

    #[test]
    fn invalid_existing_model_fails_closed_without_resolving_again() {
        let fixture = fixture();
        fs::write(fixture.session.join("model.env"), "CLAUDE_MODEL=unknown\n").unwrap();
        let stages = ScriptedStages::new(vec![
            ok(&lifecycle()),
            ok("character-ai/larch\n"),
            ok(&format!(
                "RESUME_FOUND=true\nRESUME_ACTION=reselect\nCOMPLETE_UMBRELLA_TMPDIR={}\n\
                 COMPLETE_UMBRELLA_POINTER={}\nBGJOB_STEP=complete-umbrella-leaves\n\
                 CURRENT_LEAF=0\nCURRENT_STEP=select\nTRANSIENT_ATTEMPT_COUNT=0\n",
                fixture.session.display(),
                fixture.pointer.display()
            )),
        ]);
        let result = bootstrap(&stages, 8651, true, "", &fixture.environ, 999);
        assert_eq!(result.exit_code, 1);
        assert!(result.stdout.contains("BOOTSTRAP_STAGE=model-read\n"));
        assert_eq!(stages.calls.borrow().len(), 3);
    }
}
