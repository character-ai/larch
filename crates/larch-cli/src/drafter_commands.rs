//! Drafter, negotiation-round, and Codex exec launchers.
//!
//! These four commands all sit on the shared vendor launch lifecycle in
//! `larch-core` and the shared in-process launcher in [`crate::external_agent`].
//! What differs per command is the artifact family it publishes afterwards: the
//! drafters publish a plan plus a status file, the negotiation round publishes a
//! response file, and the Codex exec launcher promotes the inner sentinel and
//! records outer-launcher metadata for the collector.

use std::{
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::{Mutex, PoisonError},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use clap::{Args, Subcommand};
use larch_adapters::{
    CodexHomeContext, ConfinedPath, PathIntent, TemporaryRoot, atomic_write_utf8_in,
    ensure_directory_chain,
    git::GixRepository,
    read_kv_raw, read_optional_utf8_lossy,
    vendor_diagnostics::{
        parse_codex_usage_file, write_failed_agent_stderr_tail, write_failure_diag,
    },
};
use larch_core::{
    AuthVerdict, CLAUDE_DESCRIPTOR, CODEX_DESCRIPTOR, CODEX_DRAFTER_TRUSTED_INSTRUCTIONS,
    CURSOR_DESCRIPTOR, ChildEnvironment, CodexEnvAuth, CodexModelRole, DIALECTIC_RAW_PENDING_FILE,
    DrafterDialectic, DrafterDirtyTree, DrafterParse, DrafterScout, DrafterStatus,
    DrafterTimeoutError, LauncherArtifact, LauncherArtifactKind, LauncherArtifactPaths,
    MAX_DRAFTER_TIMEOUT_SECONDS, ModelTool, RepositoryRead, SyncLauncherHooks, VendorLaunchRequest,
    VendorLaunchStatus, VendorProcessResult, VendorProgram, codex_env_auth_from_key,
    drafter_model_allowed, drafter_path_text_allowed, drafter_token_raw_label, emit_kv,
    env as env_names, is_quota_failure, outcome_exit_code, parse_claude_envelope,
    parse_drafter_output, render_drafter_dirty_tree, render_drafter_status,
    render_preflight_bundle, resolve_model_args, run_ready_launch, validate_drafter_timeout,
};

use crate::external_agent::{
    BareVendorOutput, BareVendorRun, ExternalAgentLaunch, ExternalAgentRouting,
    cursor_preflight_verdict, hold_vendor_startup_lock, run_bare_vendor,
    run_external_agent_with_auth_retries,
};
use crate::python_verb::plugin_root_directory;
use crate::runtime_entrypoint::run_verified_larch_with_timeout;
use crate::scout_commands::filter_manifest_paths;

/// Vendor label used by every launcher in this module that drives Codex.
const CODEX_TOOL: &str = "codex";
/// Vendor label used by the Claude drafter.
const CLAUDE_TOOL: &str = "claude";
/// Ceiling on one negotiation round.
///
/// The retired Python round imposed no launcher deadline and relied entirely on
/// the caller's tool timeout, which leaves a hung vendor running forever. This
/// reuses the ceiling the rest of the vendor surface already applies, so a
/// normal round is unaffected and only a hung vendor is reaped.
const NEGOTIATION_TIMEOUT_SECONDS: u64 = MAX_DRAFTER_TIMEOUT_SECONDS;
/// Exit code the process layer reports for a deadline-exceeded vendor.
const EXIT_TIMEOUT: i32 = 124;
/// Interval between policy-watch samples while a vendor runs.
const POLL_INTERVAL: Duration = Duration::from_secs(10);
/// Bound on the still-Python design helpers this module delegates to.
const DESIGN_VERB_TIMEOUT: Duration = Duration::from_secs(120);
/// The one Claude ledger alias that prices as its non-`[1m]` base model.
const CLAUDE_SONNET_1M_ALIAS: &str = "claude-sonnet-4-6[1m]";
/// Base model the `[1m]` Sonnet alias records as.
const CLAUDE_SONNET_BASE: &str = "claude-sonnet-4-6";

/// Drafter and vendor-exec launchers exposed under the `agent` domain.
#[derive(Subcommand)]
pub enum DrafterCommand {
    /// Draft a plan with Codex and publish the Step 2b drafter artifacts.
    #[command(name = "launch-codex-drafter")]
    LaunchCodexDrafter(CodexDrafterArguments),
    /// Draft a plan with Claude and publish the Step 2b drafter artifacts.
    #[command(name = "launch-claude-drafter")]
    LaunchClaudeDrafter(ClaudeDrafterArguments),
    /// Run one reviewer negotiation round against Codex or Cursor.
    #[command(name = "run-negotiation-round")]
    RunNegotiationRound(NegotiationArguments),
    /// Run one Codex exec launch and publish its collector metadata.
    #[command(name = "launch-codex-exec")]
    LaunchCodexExec(CodexExecArguments),
}

/// Arguments for `agent launch-codex-drafter`.
#[derive(Args)]
pub struct CodexDrafterArguments {
    #[arg(long = "prompt-file")]
    prompt_file: String,
    #[arg(long = "output-file")]
    output_file: String,
    #[arg(long)]
    timeout: String,
    #[arg(long = "design-tmpdir")]
    design_tmpdir: String,
    #[arg(long = "repo-root")]
    repo_root: String,
    #[arg(long = "timing-task-kind", default_value = "codex-plan-draft")]
    timing_task_kind: String,
    #[arg(long = "baseline-porcelain", default_value = "")]
    baseline_porcelain: String,
}

/// Arguments for `agent launch-claude-drafter`.
#[derive(Args)]
pub struct ClaudeDrafterArguments {
    #[arg(long)]
    model: String,
    #[arg(long = "prompt-file")]
    prompt_file: String,
    #[arg(long = "output-file")]
    output_file: String,
    #[arg(long)]
    timeout: String,
    #[arg(long = "design-tmpdir")]
    design_tmpdir: String,
    #[arg(long = "repo-root")]
    repo_root: String,
    #[arg(long = "timing-task-kind", default_value = "claude-plan-draft")]
    timing_task_kind: String,
    #[arg(long = "baseline-porcelain", default_value = "")]
    baseline_porcelain: String,
}

/// Arguments for `agent run-negotiation-round`.
#[derive(Args)]
pub struct NegotiationArguments {
    #[arg(long)]
    tool: String,
    #[arg(long = "prompt-file")]
    prompt_file: String,
    #[arg(long)]
    output: String,
    #[arg(long)]
    workspace: String,
}

/// Arguments for `agent launch-codex-exec`.
#[derive(Args)]
pub struct CodexExecArguments {
    #[arg(long)]
    output: String,
    #[arg(long)]
    timeout: String,
    #[arg(long, conflicts_with = "prompt_file")]
    prompt: Option<String>,
    #[arg(long = "prompt-file", required_unless_present = "prompt")]
    prompt_file: Option<String>,
    #[arg(long)]
    workdir: Option<String>,
    #[arg(long = "add-dir")]
    add_dir: Vec<String>,
    #[arg(long, value_parser = ["workspace-write", "read-only"], default_value = "workspace-write")]
    sandbox: String,
    #[arg(long = "with-effort")]
    with_effort: bool,
    #[arg(long = "model-role", value_parser = ["default", "fix"], default_value = "default")]
    model_role: String,
    #[arg(long = "usage-label", default_value = "codex_exec")]
    usage_label: String,
    #[arg(long = "timing-task-kind", default_value = "codex-exec")]
    timing_task_kind: String,
    #[arg(long = "trusted-instructions-file", default_value = "")]
    trusted_instructions_file: String,
}

/// Run one drafter-family command and return its process exit status.
pub fn run(command: DrafterCommand) -> ExitCode {
    let code = match command {
        DrafterCommand::LaunchCodexDrafter(arguments) => launch_codex_drafter(&arguments),
        DrafterCommand::LaunchClaudeDrafter(arguments) => launch_claude_drafter(&arguments),
        DrafterCommand::RunNegotiationRound(arguments) => run_negotiation_round(&arguments),
        DrafterCommand::LaunchCodexExec(arguments) => launch_codex_exec(&arguments),
    };
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

// ---------------------------------------------------------------------------
// Shared drafter scaffolding
// ---------------------------------------------------------------------------

/// Canonical, containment-checked inputs shared by both drafter launchers.
struct DrafterPaths {
    prompt: PathBuf,
    design: PathBuf,
    repo: PathBuf,
    output: PathBuf,
    baseline: Option<PathBuf>,
}

/// Publication surface for one drafter run.
struct DrafterSession {
    paths: DrafterPaths,
    artifacts: LauncherArtifactPaths,
    design_root: TemporaryRoot,
    output_root: TemporaryRoot,
    pid: u32,
}

impl DrafterSession {
    fn design_file(&self, name: &str) -> PathBuf {
        self.paths.design.join(name)
    }

    fn scratch(&self, stem: &str) -> PathBuf {
        self.design_file(&format!("{stem}.{}", self.pid))
    }

    fn write_status(&self, status: &DrafterStatus<'_>) {
        // The status file is the drafter's whole machine-readable result, so a
        // failure to publish it must be visible rather than silently dropped.
        if let Err(error) = atomic_write_utf8_in(
            &self.output_root,
            &self.paths.output,
            &render_drafter_status(status),
            true,
            0o600,
        ) {
            eprintln!("agent drafter: could not write the status file: {error}");
        }
    }

    fn write_done(&self, exit_code: i32) {
        let _ignored = atomic_write_utf8_in(
            &self.output_root,
            &self.artifacts.path(LauncherArtifactKind::Done),
            &format!("{exit_code}\n"),
            true,
            0o600,
        );
    }

    fn write_output_artifact(&self, kind: LauncherArtifactKind, text: &str) {
        let _ignored = atomic_write_utf8_in(
            &self.output_root,
            &self.artifacts.path(kind),
            text,
            true,
            0o600,
        );
    }

    fn remove_output_artifact(&self, kind: LauncherArtifactKind) {
        remove_confined(&self.output_root, &self.artifacts.path(kind));
    }
}

fn canonical_existing_file(raw: &str, reject_dotdot: bool) -> Option<PathBuf> {
    if reject_dotdot && !drafter_path_text_allowed(raw) {
        return None;
    }
    let path = PathBuf::from(raw);
    let metadata = fs::symlink_metadata(&path).ok()?;
    if !metadata.is_file() {
        return None;
    }
    let parent = fs::canonicalize(path.parent()?).ok()?;
    Some(parent.join(path.file_name()?))
}

fn canonical_existing_dir(raw: &str, reject_dotdot: bool) -> Option<PathBuf> {
    if reject_dotdot && !drafter_path_text_allowed(raw) {
        return None;
    }
    let path = PathBuf::from(raw);
    let metadata = fs::symlink_metadata(&path).ok()?;
    if !metadata.is_dir() {
        return None;
    }
    fs::canonicalize(&path).ok()
}

fn canonical_output(raw: &str, reject_dotdot: bool) -> Option<PathBuf> {
    if reject_dotdot && !drafter_path_text_allowed(raw) {
        return None;
    }
    let path = PathBuf::from(raw);
    if fs::symlink_metadata(&path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return None;
    }
    let parent = fs::canonicalize(path.parent()?).ok()?;
    Some(parent.join(path.file_name()?))
}

fn under(path: &Path, root: &Path) -> bool {
    path.starts_with(root)
}

fn remove_confined(root: &TemporaryRoot, path: &Path) {
    if fs::symlink_metadata(path).is_err() {
        return;
    }
    if let Ok(confined) = root.confine(path, PathIntent::Cleanup) {
        let _ignored = fs::remove_file(confined.path());
    }
}

fn read_text(path: &Path) -> String {
    read_optional_utf8_lossy(path)
        .unwrap_or_default()
        .unwrap_or_default()
}

fn is_non_empty_file(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

fn unix_seconds() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |elapsed| i64::try_from(elapsed.as_secs()).unwrap_or(0))
}

fn environment_map() -> std::collections::BTreeMap<String, String> {
    env::vars().collect()
}

/// Resolve the Codex env-auth decision from the caller's environment.
fn codex_auth() -> CodexEnvAuth {
    codex_env_auth_from_key(env::var(env_names::OPENAI_API_KEY).ok().as_deref())
}

// ---------------------------------------------------------------------------
// Still-Python design helpers
// ---------------------------------------------------------------------------

/// Record one vendor task's wall-clock through the still-Python timing writer.
fn record_vendor_timing(
    vendor: &str,
    task_kind: &str,
    start: i64,
    end: i64,
    output: &Path,
    exit_code: i32,
) {
    crate::timing_commands::record_vendor_timing(
        vendor,
        task_kind,
        start,
        end,
        output,
        exit_code,
        if exit_code == 0 { "complete" } else { "signal" },
    );
}

/// Filter a scout candidate manifest through the in-process Rust scout owner.
///
/// Returns whether the filtered manifest was published, plus the fail reason.
fn filter_drafter_scout(
    session: &DrafterSession,
    candidate: &Path,
    filtered: &Path,
) -> (bool, &'static str) {
    let final_manifest = session.design_file("scout-plan-manifest.json");
    if !is_non_empty_file(candidate) {
        return (false, "absent");
    }
    // The retired sibling ran as a subprocess whose WARN stream this caller
    // discarded, so the in-process seam keeps the warnings unpublished.
    let outcome = filter_manifest_paths(candidate, filtered, 1, "plan-review");
    let usable = outcome.status != "parse-failed"
        && is_non_empty_file(filtered)
        && serde_json::from_str::<serde_json::Value>(&read_text(filtered))
            .ok()
            .and_then(|value| value.get("archetypes").cloned())
            .is_some_and(|archetypes| archetypes.is_array());
    if usable && fs::rename(filtered, &final_manifest).is_ok() {
        return (true, "");
    }
    remove_confined(&session.design_root, filtered);
    remove_confined(&session.design_root, &final_manifest);
    (false, "filter_failed")
}

/// Validate a raw dialectic block through the Rust-owned candidate command.
///
/// Returns the normalized compact payload, or an empty payload plus the wire
/// fail reason when the block is not a usable candidate set.
fn validate_dialectic(session: &DrafterSession, raw: &str) -> (String, &'static str) {
    let content_file = session.scratch("dialectic-candidate.json");
    let Ok(confined) = session
        .design_root
        .confine(&content_file, PathIntent::Write)
    else {
        return (String::new(), "invalid_dialectic_json");
    };
    if fs::write(confined.path(), raw).is_err() {
        return (String::new(), "invalid_dialectic_json");
    }
    let verb = run_verified_larch_with_timeout(
        &[
            OsString::from("design"),
            OsString::from("dialectic-validate-candidates"),
            OsString::from("--content-file"),
            content_file.as_os_str().to_os_string(),
        ],
        DESIGN_VERB_TIMEOUT,
    );
    remove_confined(&session.design_root, &content_file);
    let Ok(output) = verb else {
        return (String::new(), "invalid_dialectic_json");
    };
    let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
    if !output.status().success() {
        return (String::new(), "invalid_dialectic_json");
    }
    // The verb prints `DIALECTIC_CANDIDATES_VALID=true` and then the normalized
    // compact payload on its own line.
    let payload = stdout
        .lines()
        .find(|line| line.starts_with('{'))
        .unwrap_or_default();
    if payload.is_empty() {
        return (String::new(), "invalid_dialectic_json");
    }
    (format!("{payload}\n"), "")
}

/// Persist the raw dialectic payload for the next design step.
fn write_dialectic_pending(session: &DrafterSession, payload: &str) -> bool {
    if payload.is_empty() {
        return false;
    }
    let path = session.design_file(DIALECTIC_RAW_PENDING_FILE);
    atomic_write_utf8_in(&session.design_root, &path, payload, true, 0o600).is_ok()
}

// ---------------------------------------------------------------------------
// Shared drafter publication
// ---------------------------------------------------------------------------

/// Outcome of publishing one parsed drafter response.
struct PublishedDraft {
    scout_written: bool,
    scout_fail_reason: String,
    dialectic_parsed: bool,
    dialectic_fail_reason: String,
    dialectic_pending_written: bool,
}

fn publish_draft(session: &DrafterSession, parsed: &DrafterParse) -> PublishedDraft {
    let mut scout_written = false;
    let mut scout_fail_reason = parsed.scout.fail_reason().to_owned();
    if let DrafterScout::Manifest(manifest) = &parsed.scout {
        let candidate = session.scratch("scout-plan-manifest.json.candidate");
        let filtered = session.scratch("scout-plan-manifest.json.filtered");
        if atomic_write_utf8_in(&session.design_root, &candidate, manifest, true, 0o600).is_ok() {
            let (written, reason) = filter_drafter_scout(session, &candidate, &filtered);
            scout_written = written;
            reason.clone_into(&mut scout_fail_reason);
        } else {
            "filter_failed".clone_into(&mut scout_fail_reason);
        }
        remove_confined(&session.design_root, &candidate);
    }

    let (dialectic_payload, dialectic_fail_reason) = match &parsed.dialectic {
        DrafterDialectic::Absent => (String::new(), String::new()),
        DrafterDialectic::Invalid(reason) => (String::new(), (*reason).to_owned()),
        DrafterDialectic::Candidate(raw) => {
            let (payload, reason) = validate_dialectic(session, raw);
            (payload, reason.to_owned())
        }
    };
    let dialectic_parsed = !dialectic_payload.is_empty();
    let dialectic_pending_written = write_dialectic_pending(session, &dialectic_payload);

    let _published = atomic_write_utf8_in(
        &session.design_root,
        &session.design_file("plan.txt"),
        &parsed.plan_body,
        true,
        0o600,
    );
    match &parsed.summary {
        Some(summary) => {
            let _published = atomic_write_utf8_in(
                &session.design_root,
                &session.design_file("plan-summary.md"),
                summary,
                true,
                0o600,
            );
        }
        None => remove_confined(
            &session.design_root,
            &session.design_file("plan-summary.md"),
        ),
    }
    PublishedDraft {
        scout_written,
        scout_fail_reason,
        dialectic_parsed,
        dialectic_fail_reason,
        dialectic_pending_written,
    }
}

fn success_status<'a>(parsed: &DrafterParse, published: &'a PublishedDraft) -> DrafterStatus<'a> {
    DrafterStatus {
        status: "OK",
        plan_written: true,
        plan_lines: parsed.plan_lines,
        diff_lines: parsed.diff_lines,
        summary_written: parsed.summary.is_some(),
        scout_written: published.scout_written,
        scout_fail_reason: if published.scout_written {
            ""
        } else {
            &published.scout_fail_reason
        },
        dialectic_parsed: published.dialectic_parsed,
        dialectic_raw_pending_written: published.dialectic_pending_written,
        dialectic_fail_reason: if published.dialectic_parsed {
            ""
        } else {
            &published.dialectic_fail_reason
        },
        launched: true,
        reason: "",
    }
}

/// Publish the drafter dirty-tree sidecar from the live working tree.
fn write_dirty_tree_sidecar(session: &DrafterSession, launched: bool, tool: &str) {
    let evidence = if launched {
        let porcelain = git_status_porcelain(&session.paths.repo);
        let baseline = session
            .paths
            .baseline
            .as_deref()
            .filter(|path| path.is_file())
            .map(read_text);
        render_drafter_dirty_tree(DrafterDirtyTree::Launched {
            tool,
            porcelain: porcelain.as_deref(),
            baseline: baseline.as_deref(),
        })
    } else {
        render_drafter_dirty_tree(DrafterDirtyTree::NotLaunched)
    };
    session.write_output_artifact(LauncherArtifactKind::DirtyTree, &evidence);
}

fn git_status_porcelain(repo: &Path) -> Option<String> {
    crate::repository_porcelain(repo)
}

/// Remove the pid-scoped scratch files this run may have left in the design tmpdir.
fn clean_drafter_scratch(session: &DrafterSession, stems: &[&str]) {
    for stem in stems {
        remove_confined(&session.design_root, &session.scratch(stem));
    }
}

// ---------------------------------------------------------------------------
// Codex usage and quota sidecars
// ---------------------------------------------------------------------------

/// Ensure the events stream exists, then mirror any quota signature it carries.
fn mirror_codex_quota(root: &TemporaryRoot, events: &Path, sidecar: &Path) {
    if !is_non_empty_file(events) {
        let _written = atomic_write_utf8_in(root, events, "{}\n", true, 0o600);
    }
    let text = read_text(events);
    if is_quota_failure(Some(&LauncherArtifact::present(text))) {
        append_confined(
            root,
            sidecar,
            "codex-quota: usage limit / quota reported on the codex exec --json events stream\n",
        );
    }
}

/// Where one launch's Codex token usage is published.
enum CodexUsageSink<'a> {
    /// Write a launcher-local token record the collector picks up.
    TokenRecord(&'a Path),
    /// Append straight to the shared token ledger.
    Ledger,
}

/// Publish one launch's Codex token usage, or explain why it could not be read.
fn record_codex_usage(
    root: &TemporaryRoot,
    events: &Path,
    sidecar: &Path,
    sink: &CodexUsageSink<'_>,
    label: &str,
    model: &str,
) {
    let totals = match parse_codex_usage_file(events) {
        Ok(totals) => totals,
        Err(error) => {
            append_confined(
                root,
                sidecar,
                &format!("agent parse-codex-usage: {error}\n"),
            );
            return;
        }
    };
    match sink {
        CodexUsageSink::TokenRecord(token_record) => {
            let model_line = if model.is_empty() {
                String::new()
            } else {
                format!("MODEL={model}\n")
            };
            let record = format!(
                "TOOL=codex\n{model_line}INPUT={}\nOUTPUT={}\nCACHE_READ={}\nTOTAL={}\nRAW={label}\n",
                totals.uncached_input_tokens(),
                totals.output_tokens(),
                totals.cached_input_tokens(),
                totals.total_tokens(),
            );
            let _written = atomic_write_utf8_in(root, token_record, &record, true, 0o600);
        }
        CodexUsageSink::Ledger => {
            crate::launcher_support::record_codex_vendor_usage(&totals, label, model);
        }
    }
}

fn append_confined(root: &TemporaryRoot, path: &Path, text: &str) {
    let existing = read_text(path);
    let _written = atomic_write_utf8_in(root, path, &format!("{existing}{text}"), true, 0o600);
}

// ---------------------------------------------------------------------------
// agent launch-codex-drafter
// ---------------------------------------------------------------------------

/// Which drafter launcher is resolving its arguments.
///
/// The two launchers differ in argument hygiene and in the order they report a
/// rejection, and both are observable contracts their callers branch on.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DrafterDialect {
    /// Reports the prompt first and accepts `..` in a path argument.
    Codex,
    /// Screens every path for control characters and `..`, and reports the
    /// design tmpdir first.
    Claude,
}

impl DrafterDialect {
    const fn rejects_dotdot(self) -> bool {
        matches!(self, Self::Claude)
    }
}

/// Resolve and containment-check the shared drafter inputs.
fn resolve_drafter_session(
    prog: &str,
    inputs: &DrafterArguments<'_>,
    dialect: DrafterDialect,
) -> Result<DrafterSession, i32> {
    let strict = dialect.rejects_dotdot();
    let invalid = |message: String| -> i32 {
        eprintln!("{prog}: {message}");
        2
    };
    let resolve_prompt = || {
        canonical_existing_file(inputs.prompt_file, strict).ok_or_else(|| {
            invalid(if strict {
                "invalid --prompt-file".to_owned()
            } else {
                format!(
                    "--prompt-file not found or is a symlink: {}",
                    inputs.prompt_file
                )
            })
        })
    };
    let resolve_design = || {
        canonical_existing_dir(inputs.design_tmpdir, strict).ok_or_else(|| {
            invalid(if strict {
                "invalid --design-tmpdir".to_owned()
            } else {
                format!(
                    "--design-tmpdir not found or is a symlink: {}",
                    inputs.design_tmpdir
                )
            })
        })
    };
    let resolve_repo = || {
        canonical_existing_dir(inputs.repo_root, strict).ok_or_else(|| {
            invalid(if strict {
                "invalid --repo-root".to_owned()
            } else {
                format!(
                    "--repo-root not found or is a symlink: {}",
                    inputs.repo_root
                )
            })
        })
    };
    let (prompt, design, repo) = match dialect {
        DrafterDialect::Codex => {
            let prompt = resolve_prompt()?;
            let design = resolve_design()?;
            (prompt, design, resolve_repo()?)
        }
        DrafterDialect::Claude => {
            let design = resolve_design()?;
            let repo = resolve_repo()?;
            (resolve_prompt()?, design, repo)
        }
    };
    let output = canonical_output(inputs.output_file, strict)
        .ok_or_else(|| invalid("invalid --output-file".to_owned()))?;
    if !under(&output, &design) {
        return Err(invalid("--output-file outside design tmpdir".to_owned()));
    }
    let baseline = if inputs.baseline_porcelain.is_empty() {
        None
    } else {
        Some(
            canonical_existing_file(inputs.baseline_porcelain, strict)
                .filter(|path| under(path, &design))
                .ok_or_else(|| {
                    invalid(if strict {
                        "invalid --baseline-porcelain".to_owned()
                    } else {
                        "--baseline-porcelain outside design tmpdir or invalid".to_owned()
                    })
                })?,
        )
    };
    let design_root = TemporaryRoot::resolve(Some(&design))
        .map_err(|error| invalid(format!("unusable --design-tmpdir: {error}")))?;
    let output_root = TemporaryRoot::resolve(output.parent())
        .map_err(|error| invalid(format!("unusable --output-file parent: {error}")))?;
    Ok(DrafterSession {
        artifacts: LauncherArtifactPaths::new(output.clone()),
        paths: DrafterPaths {
            prompt,
            design,
            repo,
            output,
            baseline,
        },
        design_root,
        output_root,
        pid: std::process::id(),
    })
}

/// The path arguments both drafter launchers accept.
struct DrafterArguments<'a> {
    prompt_file: &'a str,
    output_file: &'a str,
    design_tmpdir: &'a str,
    repo_root: &'a str,
    baseline_porcelain: &'a str,
}

/// Validate the shared drafter argument grammar before any filesystem work.
fn check_drafter_arguments(prog: &str, timeout: &str, timing_task_kind: &str) -> Result<(), i32> {
    match validate_drafter_timeout(timeout) {
        Ok(_seconds) => {}
        Err(DrafterTimeoutError::NotPositive) => {
            eprintln!("{prog}: --timeout must be a positive integer");
            return Err(2);
        }
        Err(DrafterTimeoutError::TooLarge) => {
            eprintln!("{prog}: --timeout must be <= 1800");
            return Err(2);
        }
    }
    if timing_task_kind.is_empty() || timing_task_kind.starts_with("--") {
        eprintln!("{prog}: --timing-task-kind must be a non-empty, non-flag-like value");
        return Err(2);
    }
    Ok(())
}

/// Scratch stems the drafter launchers create and remove inside the design tmpdir.
const CODEX_DRAFTER_SCRATCH: [&str; 6] = [
    "step2b-codex-raw.txt",
    "plan.txt.tmp",
    "plan-summary.md.tmp",
    "scout-plan-manifest.json.candidate",
    "scout-plan-manifest.json.filtered",
    "step2b-codex-trusted-instructions.txt",
];

fn launch_codex_drafter(arguments: &CodexDrafterArguments) -> i32 {
    let prog = "agent launch-codex-drafter";
    if let Err(code) =
        check_drafter_arguments(prog, &arguments.timeout, &arguments.timing_task_kind)
    {
        return code;
    }
    let session = match resolve_drafter_session(
        prog,
        &DrafterArguments {
            prompt_file: &arguments.prompt_file,
            output_file: &arguments.output_file,
            design_tmpdir: &arguments.design_tmpdir,
            repo_root: &arguments.repo_root,
            baseline_porcelain: &arguments.baseline_porcelain,
        },
        DrafterDialect::Codex,
    ) {
        Ok(session) => session,
        Err(code) => return code,
    };
    for kind in [
        LauncherArtifactKind::StderrTail,
        LauncherArtifactKind::FailureDiag,
        LauncherArtifactKind::TokenRecord,
    ] {
        session.remove_output_artifact(kind);
    }
    session.write_status(&DrafterStatus::prelaunch("prelaunch"));
    let mut launched = false;
    let code = run_codex_drafter_body(prog, arguments, &session, &mut launched);
    write_dirty_tree_sidecar(&session, launched, CODEX_TOOL);
    clean_drafter_scratch(&session, &CODEX_DRAFTER_SCRATCH);
    code
}

fn run_codex_drafter_body(
    prog: &str,
    arguments: &CodexDrafterArguments,
    session: &DrafterSession,
    launched: &mut bool,
) -> i32 {
    if !under(&session.paths.prompt, &session.paths.design)
        && !under(&session.paths.prompt, &session.paths.repo)
    {
        eprintln!("{prog}: --prompt-file outside allowed roots");
        return 2;
    }
    let raw = session.scratch("step2b-codex-raw.txt");
    let trusted = session.scratch("step2b-codex-trusted-instructions.txt");
    clean_drafter_scratch(session, &CODEX_DRAFTER_SCRATCH);
    if atomic_write_utf8_in(
        &session.design_root,
        &trusted,
        CODEX_DRAFTER_TRUSTED_INSTRUCTIONS,
        true,
        0o600,
    )
    .is_err()
    {
        eprintln!("{prog}: could not stage the trusted Codex instructions");
        return 2;
    }
    *launched = true;
    let launcher_exit = run_codex_drafter_vendor(prog, arguments, session, &raw, &trusted);
    let raw_artifacts = LauncherArtifactPaths::new(raw.clone());
    let token_source = raw_artifacts.path(LauncherArtifactKind::TokenRecord);
    if is_non_empty_file(&token_source) {
        session.write_output_artifact(LauncherArtifactKind::TokenRecord, &read_text(&token_source));
    }
    if launcher_exit != 0 {
        return finish_failed_codex_draft(session, &raw_artifacts, launcher_exit);
    }
    if !is_non_empty_file(&raw) {
        session.write_output_artifact(LauncherArtifactKind::FailureDiag, "CODEX_EMPTY_OUTPUT\n");
        session.write_status(&DrafterStatus::launched_failure(
            "ERROR",
            "CODEX_EMPTY_OUTPUT",
        ));
        session.write_done(1);
        emit_kv("STATUS", "ERROR");
        emit_kv("OUTPUT_FILE", &session.paths.output.display().to_string());
        return 1;
    }
    let parsed = match parse_drafter_output(&read_text(&raw)) {
        Ok(parsed) => parsed,
        Err(error) => {
            session.write_output_artifact(
                LauncherArtifactKind::FailureDiag,
                &format!("DELIMITER_EXTRACTION_INVALID\n{error}\n"),
            );
            session.write_status(&DrafterStatus::launched_failure(
                "ERROR",
                "DELIMITER_EXTRACTION_INVALID",
            ));
            session.write_done(99);
            emit_kv("STATUS", "ERROR");
            emit_kv("OUTPUT_FILE", &session.paths.output.display().to_string());
            return 99;
        }
    };
    let published = publish_draft(session, &parsed);
    for kind in [
        LauncherArtifactKind::Stderr,
        LauncherArtifactKind::StderrTail,
        LauncherArtifactKind::FailureDiag,
    ] {
        session.remove_output_artifact(kind);
    }
    session.write_status(&success_status(&parsed, &published));
    session.write_done(0);
    emit_kv("STATUS", "OK");
    emit_kv("OUTPUT_FILE", &session.paths.output.display().to_string());
    let token_record = session.artifacts.path(LauncherArtifactKind::TokenRecord);
    if token_record.is_file() {
        emit_kv("TOKEN_RECORD", &token_record.display().to_string());
    } else {
        emit_kv("TOKEN_RECORD_MISSING", "true");
    }
    emit_draft_result_keys(&published);
    0
}

fn emit_draft_result_keys(published: &PublishedDraft) {
    emit_kv("SCOUT_WRITTEN", &published.scout_written.to_string());
    emit_kv(
        "DIALECTIC_CANDIDATES_PARSED",
        &published.dialectic_parsed.to_string(),
    );
    emit_kv(
        "DIALECTIC_RAW_PENDING_WRITTEN",
        &published.dialectic_pending_written.to_string(),
    );
    if !published.dialectic_parsed && !published.dialectic_fail_reason.is_empty() {
        emit_kv(
            "DIALECTIC_CANDIDATES_FAIL_REASON",
            &published.dialectic_fail_reason,
        );
    }
    if !published.scout_written && !published.scout_fail_reason.is_empty() {
        emit_kv("SCOUT_FAIL_REASON", &published.scout_fail_reason);
    }
}

fn finish_failed_codex_draft(
    session: &DrafterSession,
    raw_artifacts: &LauncherArtifactPaths,
    launcher_exit: i32,
) -> i32 {
    session.write_output_artifact(LauncherArtifactKind::FailureDiag, "CODEX_EXEC_FAILED\n");
    session.write_status(&DrafterStatus::launched_failure(
        "ERROR",
        "CODEX_EXEC_FAILED",
    ));
    let raw_sidecar = raw_artifacts.path(LauncherArtifactKind::Sidecar);
    let source = if is_non_empty_file(&raw_sidecar) {
        raw_sidecar
    } else {
        session.artifacts.path(LauncherArtifactKind::Stderr)
    };
    if is_non_empty_file(&source) {
        let _written = write_failed_agent_stderr_tail(
            &session.output_root,
            &source,
            &session.artifacts,
            None,
            None,
        );
    }
    session.write_done(launcher_exit);
    emit_kv("STATUS", "ERROR");
    emit_kv("OUTPUT_FILE", &session.paths.output.display().to_string());
    let token_record = session.artifacts.path(LauncherArtifactKind::TokenRecord);
    emit_kv(
        "TOKEN_RECORD",
        &if token_record.is_file() {
            token_record.display().to_string()
        } else {
            String::new()
        },
    );
    launcher_exit
}

/// Run the Codex drafter vendor inside a private Codex home.
fn run_codex_drafter_vendor(
    prog: &str,
    arguments: &CodexDrafterArguments,
    session: &DrafterSession,
    raw: &Path,
    trusted: &Path,
) -> i32 {
    let model_args = match resolve_model_args(
        ModelTool::Codex,
        false,
        "",
        CodexModelRole::Default,
        &environment_map(),
    ) {
        Ok(resolved) => resolved.argv().to_vec(),
        Err(error) => {
            eprintln!("{prog}: model args failed: {error}");
            return 1;
        }
    };
    let home = match PrivateCodexHome::create(Some(trusted)) {
        Ok(home) => home,
        Err(refusal) => {
            write_preflight_refusal(
                &session.design_root,
                raw,
                &arguments.timeout,
                refusal.exit_code,
                &refusal.reason,
            );
            return 1;
        }
    };
    let raw_artifacts = LauncherArtifactPaths::new(raw.to_path_buf());
    let events = raw_artifacts.path(LauncherArtifactKind::Events);
    let sidecar = raw_artifacts.path(LauncherArtifactKind::Sidecar);
    let token_record = raw_artifacts.path(LauncherArtifactKind::TokenRecord);
    let stderr_path = session.artifacts.path(LauncherArtifactKind::Stderr);
    let request = VendorLaunchRequest {
        workdir: session.paths.repo.display().to_string(),
        output: raw.display().to_string(),
        prompt: read_text(&session.paths.prompt),
        model_args,
        add_dirs: vec![session.paths.repo.display().to_string()],
        timing_task_kind: arguments.timing_task_kind.clone(),
        codex_env_auth: codex_auth(),
        ..VendorLaunchRequest::new(String::new(), String::new(), String::new())
    };
    let started = Mutex::new(unix_seconds());
    let execute = |argv: &[String]| -> VendorProcessResult {
        set_started(&started);
        VendorProcessResult::new(run_codex_vendor(&CodexVendorLaunch {
            output: raw,
            timeout_seconds: &arguments.timeout,
            argv,
            workdir: &session.paths.repo,
            home: home.path(),
            stdout: &events,
            stderr: &stderr_path,
        }))
    };
    let mirror = |_result: &VendorProcessResult| {
        mirror_codex_quota(&session.design_root, &events, &sidecar);
    };
    let timing = |result: &VendorProcessResult| {
        record_vendor_timing(
            CODEX_TOOL,
            &arguments.timing_task_kind,
            started_at(&started),
            unix_seconds(),
            raw,
            result.exit_code,
        );
    };
    let usage = |model: &str| {
        record_codex_usage(
            &session.design_root,
            &events,
            &sidecar,
            &CodexUsageSink::TokenRecord(&token_record),
            "codex_plan_draft",
            model,
        );
    };
    let mut hooks = SyncLauncherHooks::new(&execute);
    hooks.mirror_quota = Some(&mirror);
    hooks.record_timing = Some(&timing);
    hooks.record_usage = Some(&usage);
    match run_ready_launch(&CODEX_DESCRIPTOR, "read-only", &request, &hooks) {
        Ok(outcome) => outcome_exit_code(&outcome, 1),
        Err(error) => {
            eprintln!("{prog}: {error}");
            1
        }
    }
}

fn set_started(cell: &Mutex<i64>) {
    *cell.lock().unwrap_or_else(PoisonError::into_inner) = unix_seconds();
}

fn started_at(cell: &Mutex<i64>) -> i64 {
    *cell.lock().unwrap_or_else(PoisonError::into_inner)
}

// ---------------------------------------------------------------------------
// Private Codex home and preflight refusals
// ---------------------------------------------------------------------------

/// Why a private Codex home could not be published.
struct CodexHomeRefusal {
    exit_code: i32,
    reason: String,
}

/// An owned private Codex home that is removed when this value drops.
struct PrivateCodexHome {
    context: CodexHomeContext,
}

impl PrivateCodexHome {
    /// Create and populate a private Codex home below the system temporary root.
    fn create(trusted: Option<&Path>) -> Result<Self, CodexHomeRefusal> {
        let temporary_root =
            TemporaryRoot::resolve(Some(&env::temp_dir())).map_err(|error| CodexHomeRefusal {
                exit_code: 1,
                reason: format!("codex auth setup failed: {error}"),
            })?;
        let user_home = home_directory().ok_or_else(|| CodexHomeRefusal {
            exit_code: 1,
            reason: "codex auth setup failed: HOME is unset".to_owned(),
        })?;
        let context = CodexHomeContext::create(&temporary_root, &user_home, trusted, codex_auth())
            .map_err(|error| CodexHomeRefusal {
                exit_code: error.exit_code(),
                reason: error.to_string(),
            })?;
        Ok(Self { context })
    }

    fn path(&self) -> &Path {
        self.context.path()
    }
}

fn home_directory() -> Option<PathBuf> {
    env::var_os("HOME")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

/// Publish the launcher artifact family for a refusal that ran no vendor.
fn write_preflight_refusal(
    root: &TemporaryRoot,
    output: &Path,
    timeout: &str,
    launcher_exit: i32,
    failure_reason: &str,
) {
    let bundle = render_preflight_bundle(
        CODEX_TOOL,
        timeout,
        output,
        failure_reason,
        false,
        launcher_exit,
    );
    let artifacts = LauncherArtifactPaths::new(output.to_path_buf());
    let writes = [
        (output.to_path_buf(), bundle.output.as_str()),
        (
            artifacts.path(LauncherArtifactKind::Diag),
            bundle.diag.as_str(),
        ),
        (
            artifacts.path(LauncherArtifactKind::Meta),
            bundle.meta.as_str(),
        ),
        (
            artifacts.path(LauncherArtifactKind::Done),
            bundle.done.as_str(),
        ),
    ];
    for (path, text) in writes {
        let _written = atomic_write_utf8_in(root, &path, text, true, 0o600);
    }
    emit_kv("LAUNCHER_EXIT", &launcher_exit.to_string());
    crate::launcher_support::emit_launcher_failure_envelope(
        &crate::launcher_support::LauncherFailureEnvelope {
            launcher_exit,
            tool: VendorProgram::Codex,
            auth_verdict: AuthVerdict::Unclassified,
            binary_present: true,
            sidecar: bundle.diag.clone(),
            output: bundle.output.clone(),
            fallback_reason: failure_reason,
            output_label: &output.display().to_string(),
        },
    );
}

// ---------------------------------------------------------------------------
// Codex vendor execution through the shared in-process launcher
// ---------------------------------------------------------------------------

/// One Codex vendor invocation routed through the shared launcher.
struct CodexVendorLaunch<'a> {
    output: &'a Path,
    timeout_seconds: &'a str,
    argv: &'a [String],
    workdir: &'a Path,
    home: &'a Path,
    stdout: &'a Path,
    stderr: &'a Path,
}

fn run_codex_vendor(launch: &CodexVendorLaunch<'_>) -> i32 {
    let timeout_seconds = launch.timeout_seconds.parse::<u64>().unwrap_or(0);
    let request = ExternalAgentLaunch {
        tool: CODEX_TOOL.to_owned(),
        output: launch.output.display().to_string(),
        timeout_seconds,
        command: launch.argv.to_vec(),
        program: VendorProgram::Codex,
        routing: ExternalAgentRouting::Streams {
            stdout: Some(launch.stdout.to_path_buf()),
            stderr: Some(launch.stderr.to_path_buf()),
        },
        stderr_sink: None,
        working_directory: Some(launch.workdir.to_path_buf()),
        environment: vec![(
            ChildEnvironment::CodexHome,
            launch.home.as_os_str().to_owned(),
        )],
        sentinel_suffix: LauncherArtifactKind::InnerDone.suffix(),
        poll_interval: POLL_INTERVAL,
        stdin: None,
        stall_watch: None,
    };
    match run_external_agent_with_auth_retries(&request) {
        Ok(outcome) => outcome.exit_code,
        Err(error) => {
            eprintln!("agent codex launch: {error}");
            1
        }
    }
}

// ---------------------------------------------------------------------------
// agent launch-claude-drafter
// ---------------------------------------------------------------------------

/// Scratch stems the Claude drafter creates inside the design tmpdir.
const CLAUDE_DRAFTER_SCRATCH: [&str; 4] = [
    "plan.txt.tmp",
    "plan-summary.md.tmp",
    "scout-plan-manifest.json.candidate",
    "scout-plan-manifest.json.filtered",
];

fn launch_claude_drafter(arguments: &ClaudeDrafterArguments) -> i32 {
    let prog = "agent launch-claude-drafter";
    if !drafter_model_allowed(&arguments.model) {
        eprintln!("{prog}: --model must be a single non-empty token");
        return 2;
    }
    let path_values = [
        arguments.prompt_file.as_str(),
        arguments.output_file.as_str(),
        arguments.design_tmpdir.as_str(),
        arguments.repo_root.as_str(),
        arguments.baseline_porcelain.as_str(),
    ];
    if path_values
        .iter()
        .any(|value| !value.is_empty() && !drafter_path_text_allowed(value))
    {
        eprintln!("{prog}: paths must not contain control characters or '..'");
        return 2;
    }
    if let Err(code) =
        check_drafter_arguments(prog, &arguments.timeout, &arguments.timing_task_kind)
    {
        return code;
    }
    let session = match resolve_drafter_session(
        prog,
        &DrafterArguments {
            prompt_file: &arguments.prompt_file,
            output_file: &arguments.output_file,
            design_tmpdir: &arguments.design_tmpdir,
            repo_root: &arguments.repo_root,
            baseline_porcelain: &arguments.baseline_porcelain,
        },
        DrafterDialect::Claude,
    ) {
        Ok(session) => session,
        Err(code) => return code,
    };
    for kind in [
        LauncherArtifactKind::StderrTail,
        LauncherArtifactKind::FailureDiag,
    ] {
        session.remove_output_artifact(kind);
    }
    remove_confined(&session.output_root, &claude_json_path(&session));
    remove_confined(&session.output_root, &claude_result_path(&session));
    session.write_status(&DrafterStatus::prelaunch("prelaunch"));

    let start = unix_seconds();
    let mut launched = false;
    let mut status = "ERROR";
    let exit_code = run_claude_drafter_body(prog, arguments, &session, &mut launched, &mut status);
    let end = unix_seconds();
    write_dirty_tree_sidecar(&session, launched, CLAUDE_TOOL);
    record_vendor_timing(
        CLAUDE_TOOL,
        &arguments.timing_task_kind,
        start,
        end,
        &session.paths.output,
        exit_code,
    );
    emit_kv("STATUS", status);
    emit_kv("OUTPUT_FILE", &session.paths.output.display().to_string());
    emit_kv("ELAPSED", &(end - start).max(0).to_string());
    let published = read_text(&session.paths.output);
    emit_kv(
        "SCOUT_WRITTEN",
        &published.contains("SCOUT_WRITTEN=true").to_string(),
    );
    emit_kv(
        "DIALECTIC_CANDIDATES_PARSED",
        &published
            .contains("DIALECTIC_CANDIDATES_PARSED=true")
            .to_string(),
    );
    emit_kv(
        "DIALECTIC_RAW_PENDING_WRITTEN",
        &published
            .contains("DIALECTIC_RAW_PENDING_WRITTEN=true")
            .to_string(),
    );
    clean_drafter_scratch(&session, &CLAUDE_DRAFTER_SCRATCH);
    remove_confined(&session.output_root, &claude_json_path(&session));
    remove_confined(&session.output_root, &claude_result_path(&session));
    exit_code
}

fn claude_json_path(session: &DrafterSession) -> PathBuf {
    suffixed(&session.paths.output, &format!(".json.{}", session.pid))
}

fn claude_result_path(session: &DrafterSession) -> PathBuf {
    suffixed(&session.paths.output, &format!(".extract.{}", session.pid))
}

fn suffixed(path: &Path, suffix: &str) -> PathBuf {
    let mut rendered = path.as_os_str().to_owned();
    rendered.push(suffix);
    PathBuf::from(rendered)
}

fn run_claude_drafter_body(
    prog: &str,
    arguments: &ClaudeDrafterArguments,
    session: &DrafterSession,
    launched: &mut bool,
    status: &mut &'static str,
) -> i32 {
    let Some(plugin_root) = plugin_root_directory() else {
        session.write_status(&DrafterStatus::prelaunch("plugin root unresolved"));
        eprintln!("{prog}: cannot resolve the plugin root");
        return 2;
    };
    if !under(&session.paths.prompt, &session.paths.design)
        && !under(&session.paths.prompt, &plugin_root)
    {
        session.write_status(&DrafterStatus::prelaunch(
            "--prompt-file outside allowed roots",
        ));
        eprintln!("{prog}: --prompt-file outside allowed roots");
        return 2;
    }
    let json_tmp = claude_json_path(session);
    let result_tmp = claude_result_path(session);
    let request = VendorLaunchRequest {
        workdir: session.paths.repo.display().to_string(),
        output: session.paths.output.display().to_string(),
        model: arguments.model.clone(),
        timing_task_kind: arguments.timing_task_kind.clone(),
        ..VendorLaunchRequest::new(String::new(), String::new(), String::new())
    };
    let Ok(argv) = CLAUDE_DESCRIPTOR.build_argv("drafter-read", &request) else {
        session.write_status(&DrafterStatus::launched_failure(
            "ERROR",
            "CLAUDE_ARGV_INVALID",
        ));
        eprintln!("{prog}: cannot build the Claude drafter argv");
        return 2;
    };
    session.write_output_artifact(
        LauncherArtifactKind::Meta,
        &format!(
            "OUTER_LAUNCHER=claude-drafter\nTIMEOUT={}\nTOOL=claude\nCMD_JSON={}\n",
            arguments.timeout,
            serde_json::to_string(&argv.full_argv()).unwrap_or_else(|_error| "[]".to_owned()),
        ),
    );
    *launched = true;
    let timeout_seconds = arguments.timeout.parse::<u64>().unwrap_or(0);
    let execute = |argv: &[String]| -> VendorProcessResult {
        VendorProcessResult::new(run_claude_drafter_vendor(
            session,
            argv,
            timeout_seconds,
            &json_tmp,
        ))
    };
    let hooks = SyncLauncherHooks::new(&execute);
    let launched_exit = match run_ready_launch(&CLAUDE_DESCRIPTOR, "drafter-read", &request, &hooks)
    {
        Ok(outcome) => outcome_exit_code(&outcome, 127),
        Err(error) => {
            eprintln!("{prog}: {error}");
            127
        }
    };
    let mut exit_code = record_claude_launch_outcome(
        arguments,
        session,
        &ClaudeDraftFiles {
            json_tmp: &json_tmp,
            result_tmp: &result_tmp,
        },
        launched_exit,
        status,
    );
    if exit_code == 0 {
        exit_code = publish_claude_draft(session, &result_tmp, status);
    }
    finish_claude_draft(session, exit_code);
    exit_code
}

/// Scratch files one Claude drafter launch reads and writes.
struct ClaudeDraftFiles<'a> {
    json_tmp: &'a Path,
    result_tmp: &'a Path,
}

/// Publish the status file for one Claude launch and extract its result text.
fn record_claude_launch_outcome(
    arguments: &ClaudeDrafterArguments,
    session: &DrafterSession,
    files: &ClaudeDraftFiles<'_>,
    launched_exit: i32,
    status: &mut &'static str,
) -> i32 {
    if launched_exit == EXIT_TIMEOUT {
        *status = "TIMEOUT";
        session.write_status(&DrafterStatus::launched_failure("TIMEOUT", "TIMEOUT"));
        return launched_exit;
    }
    if launched_exit != 0 {
        session.write_status(&DrafterStatus::launched_failure(
            "ERROR",
            "CLAUDE_EXIT_NONZERO",
        ));
        return launched_exit;
    }
    let envelope = parse_claude_envelope(&read_text(files.json_tmp));
    if envelope.text.is_empty() {
        session.write_output_artifact(
            LauncherArtifactKind::FailureDiag,
            "CLAUDE_JSON_RESULT_INVALID\n",
        );
        append_confined(
            &session.output_root,
            &session.artifacts.path(LauncherArtifactKind::Stderr),
            &format!(
                "claude JSON envelope parse failed: {}\n",
                envelope.status.as_str()
            ),
        );
        session.write_status(&DrafterStatus::launched_failure(
            "ERROR",
            "CLAUDE_JSON_RESULT_INVALID",
        ));
        return 99;
    }
    let _written = atomic_write_utf8_in(
        &session.output_root,
        files.result_tmp,
        &envelope.text,
        true,
        0o600,
    );
    record_claude_sub_usage(
        &envelope.raw,
        drafter_token_raw_label(&arguments.timing_task_kind),
        &arguments.model,
    );
    0
}

fn publish_claude_draft(
    session: &DrafterSession,
    result_tmp: &Path,
    status: &mut &'static str,
) -> i32 {
    match parse_drafter_output(&read_text(result_tmp)) {
        Ok(parsed) => {
            let published = publish_draft(session, &parsed);
            session.write_status(&success_status(&parsed, &published));
            *status = "OK";
            0
        }
        Err(error) => {
            session.write_output_artifact(
                LauncherArtifactKind::FailureDiag,
                &format!("DELIMITER_EXTRACTION_INVALID\n{error}\n"),
            );
            session.write_status(&DrafterStatus::launched_failure(
                "ERROR",
                "DELIMITER_EXTRACTION_INVALID",
            ));
            99
        }
    }
}

fn finish_claude_draft(session: &DrafterSession, exit_code: i32) {
    let stderr_file = session.artifacts.path(LauncherArtifactKind::Stderr);
    if exit_code == 0 {
        for kind in [
            LauncherArtifactKind::StderrTail,
            LauncherArtifactKind::FailureDiag,
        ] {
            session.remove_output_artifact(kind);
        }
    } else {
        if is_non_empty_file(&stderr_file) {
            let _written = write_failed_agent_stderr_tail(
                &session.output_root,
                &stderr_file,
                &session.artifacts,
                None,
                None,
            );
        }
        if !is_non_empty_file(&session.artifacts.path(LauncherArtifactKind::FailureDiag)) {
            let _written = write_failure_diag(
                &session.output_root,
                &session.artifacts,
                Some(&stderr_file),
                None,
                None,
            );
        }
    }
    session.write_done(exit_code);
}

/// Run the Claude drafter with the prompt file on the child's standard input.
///
/// The drafter owns its own artifacts — a status file, an `OUTER_LAUNCHER` meta
/// record, and a completion sentinel it writes after extraction — so the vendor
/// runs bare rather than through the artifact-publishing launcher, which would
/// overwrite that meta record with a generic one.
fn run_claude_drafter_vendor(
    session: &DrafterSession,
    argv: &[String],
    timeout_seconds: u64,
    json_tmp: &Path,
) -> i32 {
    let stderr_path = session.artifacts.path(LauncherArtifactKind::Stderr);
    let files = claude_drafter_files(session, json_tmp, &stderr_path);
    let (stdin, stdout, stderr) = match files {
        Ok(files) => files,
        Err(error) => {
            append_confined(
                &session.output_root,
                &stderr_path,
                &format!("Failed to launch child: {error}\n"),
            );
            return 127;
        }
    };
    let run = BareVendorRun {
        program: VendorProgram::Claude,
        argv,
        working_directory: &session.paths.repo,
        environment: Vec::new(),
        stdin: Some(stdin),
        output: BareVendorOutput::Streams {
            stdout: Some(stdout),
            stderr: Some(stderr),
        },
        timeout_seconds,
    };
    match run_bare_vendor(&run) {
        Ok(exit_code) => exit_code,
        Err((exit_code, message)) => {
            append_confined(
                &session.output_root,
                &stderr_path,
                &format!("Failed to launch child: {message}\n"),
            );
            exit_code
        }
    }
}

/// Confine the Claude drafter's prompt, envelope, and stderr files.
fn claude_drafter_files(
    session: &DrafterSession,
    json_tmp: &Path,
    stderr_path: &Path,
) -> Result<(ConfinedPath, ConfinedPath, ConfinedPath), String> {
    let confine = |path: &Path| {
        session
            .output_root
            .confine(path, PathIntent::Write)
            .map_err(|error| error.to_string())
    };
    Ok((
        confined_stdin(&session.paths.prompt)?,
        confine(json_tmp)?,
        confine(stderr_path)?,
    ))
}

/// Confine one existing prompt file for use as a child's standard input.
fn confined_stdin(prompt: &Path) -> Result<ConfinedPath, String> {
    let parent = prompt
        .parent()
        .ok_or_else(|| "prompt file has no parent directory".to_owned())?;
    let root = TemporaryRoot::resolve(Some(parent)).map_err(|error| error.to_string())?;
    root.confine(prompt, PathIntent::Read)
        .map_err(|error| error.to_string())
}

/// Record one Claude subprocess's token usage through the still-Python ledger.
fn record_claude_sub_usage(raw_envelope: &str, label: &str, model: &str) {
    let Some(usage) = serde_json::from_str::<serde_json::Value>(raw_envelope)
        .ok()
        .and_then(|value| value.get("usage").cloned())
    else {
        return;
    };
    let read = |primary: &str, alternate: &str| -> i64 {
        usage
            .get(primary)
            .or_else(|| usage.get(alternate))
            .and_then(serde_json::Value::as_i64)
            .unwrap_or(0)
    };
    let input = read("input_tokens", "inputTokens");
    let output = read("output_tokens", "outputTokens");
    let cache_read = read("cache_read_input_tokens", "cacheReadTokens");
    let cache_create = read("cache_creation_input_tokens", "cacheWriteTokens");
    let total = input + output + cache_read + cache_create;
    let ledger_model = if model == CLAUDE_SONNET_1M_ALIAS {
        CLAUDE_SONNET_BASE
    } else {
        model
    };
    crate::token_commands::record_vendor_best_effort([
        OsString::from("claude_sub"),
        OsString::from(format!("input={input}")),
        OsString::from(format!("output={output}")),
        OsString::from(format!("cache_read={cache_read}")),
        OsString::from(format!("cache_create={cache_create}")),
        OsString::from(format!("total={total}")),
        OsString::from(format!("raw={label}")),
        OsString::from(format!("model={ledger_model}")),
    ]);
}

// ---------------------------------------------------------------------------
// agent run-negotiation-round
// ---------------------------------------------------------------------------

fn run_negotiation_round(arguments: &NegotiationArguments) -> i32 {
    let prog = "agent run-negotiation-round";
    if arguments.tool != CODEX_TOOL && arguments.tool != "cursor" {
        eprintln!(
            "{prog}: ERROR: --tool must be 'codex' or 'cursor' (got: {})",
            arguments.tool
        );
        return 1;
    }
    let prompt = PathBuf::from(&arguments.prompt_file);
    let output = PathBuf::from(&arguments.output);
    let workspace = PathBuf::from(&arguments.workspace);
    if !prompt.is_file() {
        eprintln!("{prog}: ERROR: prompt file not found: {}", prompt.display());
        return 1;
    }
    let Some(parent) = output.parent() else {
        eprintln!("{prog}: ERROR: --output has no parent directory");
        return 1;
    };
    if ensure_directory_chain(parent).is_err() {
        eprintln!("{prog}: ERROR: cannot create the output directory");
        return 1;
    }
    let Ok(output_root) = TemporaryRoot::resolve(Some(parent)) else {
        eprintln!("{prog}: ERROR: unusable output directory");
        return 1;
    };
    remove_confined(&output_root, &output);
    if arguments.tool == CODEX_TOOL {
        run_codex_negotiation(prog, &prompt, &output, &output_root, &workspace)
    } else {
        run_cursor_negotiation(prog, &prompt, &output, &output_root, &workspace)
    }
}

/// Strip one trailing `.txt` so the Codex sidecars sit beside the response.
fn negotiation_base(output: &Path) -> PathBuf {
    output
        .to_str()
        .and_then(|text| text.strip_suffix(".txt"))
        .map_or_else(|| output.to_path_buf(), PathBuf::from)
}

fn run_codex_negotiation(
    prog: &str,
    prompt: &Path,
    output: &Path,
    output_root: &TemporaryRoot,
    workspace: &Path,
) -> i32 {
    let base = negotiation_base(output);
    let events = suffixed(&base, ".events.jsonl");
    let sidecar = suffixed(&base, ".sidecar");
    remove_confined(output_root, &events);
    remove_confined(output_root, &sidecar);
    let model_args = match resolve_model_args(
        ModelTool::Codex,
        false,
        "",
        CodexModelRole::Default,
        &environment_map(),
    ) {
        Ok(resolved) => resolved.argv().to_vec(),
        Err(error) => {
            eprintln!("{prog}: model args failed: {error}");
            return 1;
        }
    };
    let home = PrivateCodexHome::create(None);
    let request = VendorLaunchRequest {
        workdir: workspace.display().to_string(),
        output: output.display().to_string(),
        model_args,
        prompt_via_stdin: true,
        timing_task_kind: "codex_negotiation".to_owned(),
        codex_env_auth: codex_auth(),
        ..VendorLaunchRequest::new(String::new(), String::new(), String::new())
    };
    let refusal = home.as_ref().err();
    let preflight = || -> bool {
        refusal.is_none_or(|error| {
            if !error.reason.is_empty() {
                let _written = atomic_write_utf8_in(
                    output_root,
                    &sidecar,
                    &format!("{}\n", error.reason),
                    true,
                    0o600,
                );
            }
            false
        })
    };
    let execute = |argv: &[String]| -> VendorProcessResult {
        let Ok(home) = home.as_ref() else {
            return VendorProcessResult::new(1);
        };
        VendorProcessResult::new(run_codex_negotiation_vendor(&CodexNegotiationLaunch {
            prompt,
            events: &events,
            sidecar: &sidecar,
            workspace,
            home: home.path(),
            argv,
            output_root,
        }))
    };
    let mirror = |result: &VendorProcessResult| {
        if result.exit_code != 0 {
            mirror_codex_quota(output_root, &events, &sidecar);
        }
    };
    let usage = |_model: &str| {
        record_codex_usage(
            output_root,
            &events,
            &sidecar,
            &CodexUsageSink::Ledger,
            "codex_negotiation",
            "",
        );
    };
    let promote = |_result: &VendorProcessResult| {
        emit_kv("RESPONSE_FILE", &output.display().to_string());
    };
    let mut hooks = SyncLauncherHooks::new(&execute);
    hooks.preflight = Some(&preflight);
    hooks.mirror_quota = Some(&mirror);
    hooks.record_usage = Some(&usage);
    hooks.promote_completion = Some(&promote);
    match run_ready_launch(&CODEX_DESCRIPTOR, "workspace-write", &request, &hooks) {
        Ok(outcome) if outcome.status == VendorLaunchStatus::PreflightRefused => {
            emit_kv("RESPONSE_FILE", &output.display().to_string());
            2
        }
        Ok(outcome) if outcome_exit_code(&outcome, 0) != 0 => 2,
        Ok(_outcome) => 0,
        Err(error) => {
            eprintln!("{prog}: {error}");
            2
        }
    }
}

/// One Codex negotiation invocation routed through the shared launcher.
struct CodexNegotiationLaunch<'a> {
    prompt: &'a Path,
    events: &'a Path,
    sidecar: &'a Path,
    workspace: &'a Path,
    home: &'a Path,
    argv: &'a [String],
    output_root: &'a TemporaryRoot,
}

fn run_codex_negotiation_vendor(launch: &CodexNegotiationLaunch<'_>) -> i32 {
    let files = match negotiation_files(
        launch.output_root,
        launch.prompt,
        launch.events,
        launch.sidecar,
    ) {
        Ok(files) => files,
        Err(error) => {
            append_confined(
                launch.output_root,
                launch.sidecar,
                &format!("Failed to launch child: {error}\n"),
            );
            return 127;
        }
    };
    let _release = hold_vendor_startup_lock(VendorProgram::Codex);
    let run = BareVendorRun {
        program: VendorProgram::Codex,
        argv: launch.argv,
        working_directory: launch.workspace,
        environment: vec![(
            ChildEnvironment::CodexHome,
            launch.home.as_os_str().to_owned(),
        )],
        stdin: files.stdin,
        output: BareVendorOutput::Streams {
            stdout: files.stdout,
            stderr: files.stderr,
        },
        timeout_seconds: NEGOTIATION_TIMEOUT_SECONDS,
    };
    match run_bare_vendor(&run) {
        Ok(exit_code) => exit_code,
        Err((exit_code, message)) => {
            append_confined(
                launch.output_root,
                launch.sidecar,
                &format!("Failed to launch child: {message}\n"),
            );
            exit_code
        }
    }
}

/// The negotiation round's own stream files, confined below its output root.
struct NegotiationFiles {
    stdin: Option<ConfinedPath>,
    stdout: Option<ConfinedPath>,
    stderr: Option<ConfinedPath>,
}

fn negotiation_files(
    root: &TemporaryRoot,
    prompt: &Path,
    stdout: &Path,
    stderr: &Path,
) -> Result<NegotiationFiles, String> {
    let confine = |path: &Path| {
        root.confine(path, PathIntent::Write)
            .map_err(|error| error.to_string())
    };
    Ok(NegotiationFiles {
        stdin: Some(confined_stdin(prompt)?),
        stdout: Some(confine(stdout)?),
        stderr: Some(confine(stderr)?),
    })
}

fn run_cursor_negotiation(
    prog: &str,
    prompt: &Path,
    output: &Path,
    output_root: &TemporaryRoot,
    workspace: &Path,
) -> i32 {
    let model_args = match resolve_model_args(
        ModelTool::Cursor,
        false,
        "",
        CodexModelRole::Default,
        &environment_map(),
    ) {
        Ok(resolved) => resolved.argv().to_vec(),
        Err(error) => {
            eprintln!("{prog}: model args failed: {error}");
            return 1;
        }
    };
    let request = VendorLaunchRequest {
        workdir: workspace.display().to_string(),
        output: output.display().to_string(),
        prompt: format!(
            " /max-mode on. Prompt: Read the negotiation prompt from {} and respond to it.",
            prompt.display()
        ),
        model_args,
        timing_task_kind: "cursor_negotiation".to_owned(),
        ..VendorLaunchRequest::new(String::new(), String::new(), String::new())
    };
    let preflight = || cursor_negotiation_preflight();
    let execute = |argv: &[String]| -> VendorProcessResult {
        VendorProcessResult::new(run_cursor_negotiation_vendor(
            argv,
            output,
            output_root,
            workspace,
        ))
    };
    let promote = |_result: &VendorProcessResult| {
        emit_kv("RESPONSE_FILE", &output.display().to_string());
    };
    let mut hooks = SyncLauncherHooks::new(&execute);
    hooks.preflight = Some(&preflight);
    hooks.promote_completion = Some(&promote);
    match run_ready_launch(&CURSOR_DESCRIPTOR, "negotiation-write", &request, &hooks) {
        Ok(outcome) if outcome.status == VendorLaunchStatus::PreflightRefused => {
            emit_kv("RESPONSE_FILE", &output.display().to_string());
            3
        }
        Ok(outcome) if outcome_exit_code(&outcome, 0) != 0 => 2,
        Ok(_outcome) => 0,
        Err(error) => {
            eprintln!("{prog}: {error}");
            2
        }
    }
}

/// Prove Cursor can authenticate before the negotiation round launches.
///
/// Returning `false` refuses the launch before any vendor work, which the
/// caller reports as the documented Cursor preflight exit code.
fn cursor_negotiation_preflight() -> bool {
    let verdict = cursor_preflight_verdict("agent run-negotiation-round");
    if !verdict.ok {
        eprintln!("{}", verdict.message);
    }
    verdict.ok
}

fn run_cursor_negotiation_vendor(
    argv: &[String],
    output: &Path,
    output_root: &TemporaryRoot,
    workspace: &Path,
) -> i32 {
    let Ok(response) = output_root.confine(output, PathIntent::Write) else {
        eprintln!("agent run-negotiation-round: unusable --output path");
        return 1;
    };
    let _release = hold_vendor_startup_lock(VendorProgram::Cursor);
    let run = BareVendorRun {
        program: VendorProgram::Cursor,
        argv,
        working_directory: workspace,
        environment: Vec::new(),
        stdin: None,
        // Cursor's diagnostics belong in the response file the caller reads,
        // interleaved with its answer rather than overwriting it.
        output: BareVendorOutput::Combined(response),
        timeout_seconds: NEGOTIATION_TIMEOUT_SECONDS,
    };
    match run_bare_vendor(&run) {
        Ok(exit_code) => exit_code,
        Err((exit_code, message)) => {
            let _written = atomic_write_utf8_in(
                output_root,
                output,
                &format!("Failed to launch child: {message}\n"),
                true,
                0o600,
            );
            exit_code
        }
    }
}

// ---------------------------------------------------------------------------
// agent launch-codex-exec
// ---------------------------------------------------------------------------

fn launch_codex_exec(arguments: &CodexExecArguments) -> i32 {
    let prog = "agent launch-codex-exec";
    if !is_positive_integer(&arguments.timeout) {
        eprintln!("{prog}: --timeout must be a positive integer");
        return 2;
    }
    let output = PathBuf::from(&arguments.output);
    if !output.is_absolute() {
        return 2;
    }
    if !crate::valid_meta_path(output.as_os_str()) {
        eprintln!("ERROR: --output contains unsupported characters");
        return 2;
    }
    let workdir = arguments
        .workdir
        .as_deref()
        .map_or_else(resolve_review_codex_workdir, PathBuf::from);
    if !workdir.is_dir() {
        eprintln!(
            "{prog}: --workdir is not a directory: {}",
            workdir.display()
        );
        return 2;
    }
    let prompt = match (&arguments.prompt, &arguments.prompt_file) {
        (Some(prompt), _) => prompt.clone(),
        (None, Some(file)) => read_text(Path::new(file)),
        (None, None) => {
            eprintln!("{prog}: --prompt or --prompt-file is required");
            return 2;
        }
    };
    let Some(parent) = output.parent() else {
        eprintln!("{prog}: --output has no parent directory");
        return 2;
    };
    if ensure_directory_chain(parent).is_err() {
        eprintln!("{prog}: cannot create the output directory");
        return 2;
    }
    let Ok(output_root) = TemporaryRoot::resolve(Some(parent)) else {
        eprintln!("{prog}: unusable output directory");
        return 2;
    };
    let artifacts = LauncherArtifactPaths::new(output.clone());
    let prompt_sidecar = artifacts.path(LauncherArtifactKind::Prompt);
    let _written = atomic_write_utf8_in(&output_root, &prompt_sidecar, &prompt, true, 0o600);
    let add_dirs = if arguments.add_dir.is_empty() {
        vec![workdir.display().to_string()]
    } else {
        arguments.add_dir.clone()
    };
    let launcher_exit = run_codex_exec_launch(
        arguments,
        &CodexExecContext {
            output: &output,
            output_root: &output_root,
            artifacts: &artifacts,
            workdir: &workdir,
            prompt: &prompt,
            add_dirs: &add_dirs,
        },
    );
    emit_kv("LAUNCHER_EXIT", &launcher_exit.to_string());
    emit_kv("OUTPUT", &output.display().to_string());
    0
}

/// Resolved surroundings for one Codex exec launch.
struct CodexExecContext<'a> {
    output: &'a Path,
    output_root: &'a TemporaryRoot,
    artifacts: &'a LauncherArtifactPaths,
    workdir: &'a Path,
    prompt: &'a str,
    add_dirs: &'a [String],
}

fn run_codex_exec_launch(arguments: &CodexExecArguments, context: &CodexExecContext<'_>) -> i32 {
    let trusted = (!arguments.trusted_instructions_file.is_empty())
        .then(|| PathBuf::from(&arguments.trusted_instructions_file));
    let home = match PrivateCodexHome::create(trusted.as_deref()) {
        Ok(home) => home,
        Err(refusal) => {
            write_preflight_refusal(
                context.output_root,
                context.output,
                &arguments.timeout,
                refusal.exit_code,
                &refusal.reason,
            );
            return 0;
        }
    };
    let Some(model_args) = codex_exec_model_args(arguments, context) else {
        return 0;
    };
    let events = context.artifacts.path(LauncherArtifactKind::Events);
    let sidecar = context.artifacts.path(LauncherArtifactKind::Sidecar);
    let token_record = context.artifacts.path(LauncherArtifactKind::TokenRecord);
    let request = VendorLaunchRequest {
        workdir: context.workdir.display().to_string(),
        output: context.output.display().to_string(),
        prompt: context.prompt.to_owned(),
        model_args,
        add_dirs: context.add_dirs.to_vec(),
        timing_task_kind: arguments.timing_task_kind.clone(),
        codex_env_auth: codex_auth(),
        ..VendorLaunchRequest::new(String::new(), String::new(), String::new())
    };
    let started = Mutex::new(unix_seconds());
    let execute = |argv: &[String]| -> VendorProcessResult {
        set_started(&started);
        VendorProcessResult::new(run_codex_vendor(&CodexVendorLaunch {
            output: context.output,
            timeout_seconds: &arguments.timeout,
            argv,
            workdir: context.workdir,
            home: home.path(),
            stdout: &events,
            stderr: &sidecar,
        }))
    };
    let mirror = |_result: &VendorProcessResult| {
        mirror_codex_quota(context.output_root, &events, &sidecar);
    };
    let timing = |result: &VendorProcessResult| {
        record_vendor_timing(
            CODEX_TOOL,
            &arguments.timing_task_kind,
            started_at(&started),
            unix_seconds(),
            context.output,
            result.exit_code,
        );
    };
    let usage = |model: &str| {
        record_codex_usage(
            context.output_root,
            &events,
            &sidecar,
            &CodexUsageSink::TokenRecord(&token_record),
            &arguments.usage_label,
            model,
        );
    };
    let promote = |_result: &VendorProcessResult| {
        promote_codex_exec(arguments, context);
    };
    let mut hooks = SyncLauncherHooks::new(&execute);
    hooks.mirror_quota = Some(&mirror);
    hooks.record_timing = Some(&timing);
    hooks.record_usage = Some(&usage);
    hooks.promote_completion = Some(&promote);
    match run_ready_launch(&CODEX_DESCRIPTOR, &arguments.sandbox, &request, &hooks) {
        Ok(outcome) => outcome_exit_code(&outcome, 0),
        Err(error) => {
            eprintln!("agent launch-codex-exec: {error}");
            0
        }
    }
}

/// Resolve Codex model argv, publishing a refusal bundle when it cannot resolve.
fn codex_exec_model_args(
    arguments: &CodexExecArguments,
    context: &CodexExecContext<'_>,
) -> Option<Vec<String>> {
    let codex_role = if arguments.model_role == "fix" {
        CodexModelRole::Fix
    } else {
        CodexModelRole::Default
    };
    match resolve_model_args(
        ModelTool::Codex,
        arguments.with_effort,
        "",
        codex_role,
        &environment_map(),
    ) {
        Ok(resolved) => Some(resolved.argv().to_vec()),
        Err(error) => {
            write_preflight_refusal(
                context.output_root,
                context.output,
                &arguments.timeout,
                1,
                &format!("model args failed: {error}"),
            );
            None
        }
    }
}

/// Record the outer-launcher metadata the collector reads, then publish `.done`.
fn promote_codex_exec(arguments: &CodexExecArguments, context: &CodexExecContext<'_>) {
    let meta = context.artifacts.path(LauncherArtifactKind::Meta);
    let record = format!(
        "OUTER_LAUNCHER=agent launch-codex-exec\nOUTER_LAUNCHER_PROMPT_FILE={}\nOUTER_LAUNCHER_WORKDIR={}\nOUTER_LAUNCHER_KIND=codex-exec\nOUTER_LAUNCHER_SANDBOX={}\nOUTER_LAUNCHER_WITH_EFFORT={}\nOUTER_LAUNCHER_MODEL_ROLE={}\nOUTER_LAUNCHER_USAGE_LABEL={}\nOUTER_LAUNCHER_TIMING_KIND={}\nOUTER_LAUNCHER_ADD_DIRS_JSON={}\n",
        context
            .artifacts
            .path(LauncherArtifactKind::Prompt)
            .display(),
        context.workdir.display(),
        arguments.sandbox,
        arguments.with_effort,
        arguments.model_role,
        arguments.usage_label,
        arguments.timing_task_kind,
        serde_json::to_string(context.add_dirs).unwrap_or_else(|_error| "[]".to_owned()),
    );
    append_confined(context.output_root, &meta, &record);
    let inner = context.artifacts.path(LauncherArtifactKind::InnerDone);
    if inner.is_file() {
        let _promoted = fs::rename(&inner, context.artifacts.path(LauncherArtifactKind::Done));
    }
}

fn is_positive_integer(value: &str) -> bool {
    !value.is_empty()
        && value.bytes().all(|byte| byte.is_ascii_digit())
        && value.parse::<u64>().is_ok_and(|parsed| parsed > 0)
}

// ---------------------------------------------------------------------------
// Codex exec workdir resolution
// ---------------------------------------------------------------------------

/// Resolve the repository the review Codex lane should run inside.
///
/// The declared project directory wins, then the current directory, then a
/// keepalive clone recorded by an active session. Each candidate is accepted
/// only when it resolves to a Git work tree.
fn resolve_review_codex_workdir() -> PathBuf {
    let cwd = env::current_dir().unwrap_or_else(|_error| PathBuf::from("."));
    let declared = env::var_os("CLAUDE_PROJECT_DIR").map(PathBuf::from);
    if let Some(toplevel) = declared.as_deref().and_then(git_toplevel) {
        return toplevel;
    }
    if let Some(toplevel) = git_toplevel(&cwd) {
        return toplevel;
    }
    keepalive_clone_path(&cwd)
        .as_deref()
        .and_then(git_toplevel)
        .unwrap_or(cwd)
}

fn git_toplevel(path: &Path) -> Option<PathBuf> {
    let repository = GixRepository::discover(path).ok()?;
    let work_dir = repository.location().work_dir?;
    let rendered = PathBuf::from(String::from_utf8_lossy(work_dir.as_bytes()).into_owned());
    fs::canonicalize(rendered).ok()
}

/// Read `CLONE_PATH` from the nearest `.larch-keepalive` record.
fn keepalive_clone_path(start: &Path) -> Option<PathBuf> {
    for name in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "SESSION_TMPDIR"] {
        let Some(tmpdir) = env::var_os(name).filter(|value| !value.is_empty()) else {
            continue;
        };
        if let Some(clone) = clone_path_in(&PathBuf::from(tmpdir).join(".larch-keepalive")) {
            return Some(clone);
        }
    }
    let mut current = start.to_path_buf();
    loop {
        if let Some(clone) = clone_path_in(&current.join(".larch-keepalive")) {
            return Some(clone);
        }
        match current.parent() {
            Some(parent) if parent != current => current = parent.to_path_buf(),
            _ => return None,
        }
    }
}

fn clone_path_in(keepalive: &Path) -> Option<PathBuf> {
    let pairs: Vec<(String, String)> = read_kv_raw(keepalive).ok()?;
    let value = pairs
        .iter()
        .find(|(key, _value)| key == "CLONE_PATH")
        .map(|(_key, value)| value.trim())
        .unwrap_or_default();
    (!value.is_empty()).then(|| PathBuf::from(value))
}
