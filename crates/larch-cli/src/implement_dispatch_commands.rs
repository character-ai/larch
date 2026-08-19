//! Rust owners for `implement recovery-paths` and `implement run-step-checks`.

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::{GixRepository, SystemProcessIdentityHost};
use larch_core::{
    CHECKS_TERMINAL_ACTIONS, ChildEnvironment, CommentPolicy, DuplicateInputPolicy,
    DuplicatePolicy, ExternalProgram, KvDocument, LarchProgram, ParseOptions, ProcessOutput,
    ProcessStatus, RecoveryPorcelainInputs, StatusOptions, bgjob_dir, child_liveness,
    compute_recovery_paths, daemon_liveness, ensure_under,
    implement::{
        ChecksIdentityError, ChecksInputIdentity, classify_completed_result, classify_live_seed,
        identities_match, session_repo_root,
    },
    log_paths, owner_pid_candidate, private_atomic_write, read_for, resolve_run_id,
    resolve_step_and_budget, resolve_tmpdir_path, result_env_path, validate_merge_result_env,
    write_bytes_atomic,
};

use crate::{
    argparse_compat::{ParsedCommandLine, choice_error, parse_required_with_help, usage_error},
    checks_identity_commands::{live_identity, validate_repo_root},
    child_process::{bounded_request_in, run_bounded},
    implement_child_seam::resolve_plugin_root,
    python_verb::{publish_session_environment, run_python_verb},
};

const RECOVERY_PROG: &str = "cli.py implement recovery-paths";
const RECOVERY_USAGE: &str = "usage: cli.py implement recovery-paths [-h] --repo-root REPO_ROOT\n                                       [--tmpdir TMPDIR]\n                                       [--capture-postlaunch]\n                                       [--prelaunch-porcelain PRELAUNCH_PORCELAIN]\n                                       [--postlaunch-porcelain POSTLAUNCH_PORCELAIN]\n                                       [--prelaunch-digests PRELAUNCH_DIGESTS]\n                                       [--out-file OUT_FILE]\n";
const RECOVERY_HELP: &str = "usage: cli.py implement recovery-paths [-h] --repo-root REPO_ROOT\n                                       [--tmpdir TMPDIR]\n                                       [--capture-postlaunch]\n                                       [--prelaunch-porcelain PRELAUNCH_PORCELAIN]\n                                       [--postlaunch-porcelain POSTLAUNCH_PORCELAIN]\n                                       [--prelaunch-digests PRELAUNCH_DIGESTS]\n                                       [--out-file OUT_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --tmpdir TMPDIR\n  --capture-postlaunch\n  --prelaunch-porcelain PRELAUNCH_PORCELAIN\n  --postlaunch-porcelain POSTLAUNCH_PORCELAIN\n  --prelaunch-digests PRELAUNCH_DIGESTS\n  --out-file OUT_FILE\n";
const STEP_PROG: &str = "cli.py implement run-step-checks";
const STEP_USAGE: &str = "usage: cli.py implement run-step-checks [-h] --site SITE\n                                        [--commit-site COMMIT_SITE]\n                                        [--forked-target {true,false}]\n                                        [--rebase-checkpoint-4r]\n                                        [--bgjob-child]\n                                        [--merge-result-env MERGE_RESULT_ENV]\n                                        [--repo-root REPO_ROOT]\n                                        [--launch-head LAUNCH_HEAD]\n                                        [--launch-fp LAUNCH_FP]\n                                        [--launch-schema LAUNCH_SCHEMA]\n";
const STEP_HELP: &str = "usage: cli.py implement run-step-checks [-h] --site SITE\n                                        [--commit-site COMMIT_SITE]\n                                        [--forked-target {true,false}]\n                                        [--rebase-checkpoint-4r]\n                                        [--bgjob-child]\n                                        [--merge-result-env MERGE_RESULT_ENV]\n                                        [--repo-root REPO_ROOT]\n                                        [--launch-head LAUNCH_HEAD]\n                                        [--launch-fp LAUNCH_FP]\n                                        [--launch-schema LAUNCH_SCHEMA]\n\noptions:\n  -h, --help            show this help message and exit\n  --site SITE\n  --commit-site COMMIT_SITE\n  --forked-target {true,false}\n  --rebase-checkpoint-4r\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n  --repo-root REPO_ROOT\n  --launch-head LAUNCH_HEAD\n  --launch-fp LAUNCH_FP\n  --launch-schema LAUNCH_SCHEMA\n";

const PYTHON_TIMEOUT: Duration = Duration::from_secs(600);
const ADAPT_TIMEOUT: Duration = Duration::from_secs(600);
const ADAPT_GRACE: Duration = Duration::from_secs(5);
const ADAPT_OUTPUT_LIMIT: usize = 256 * 1024;
const CHECKS_HEAD: &str = "CHECKS_INPUT_HEAD_SHA";
const CHECKS_FP: &str = "CHECKS_INPUT_TREE_FP";
const CHECKS_SCHEMA: &str = "CHECKS_INPUT_FP_SCHEMA";
const IDENTITY_FAILED: &str = "identity-integrity-failed";

#[cfg(test)]
type PythonHook =
    std::sync::Arc<dyn Fn(&[OsString]) -> Result<ProcessOutput, String> + Send + Sync>;
#[cfg(test)]
type LarchHook = std::sync::Arc<
    dyn Fn(&Path, &Path, &[OsString]) -> Result<ProcessOutput, String> + Send + Sync,
>;

#[cfg(test)]
std::thread_local! {
    static TEST_PYTHON: std::cell::RefCell<Option<PythonHook>> = const { std::cell::RefCell::new(None) };
    static TEST_LARCH: std::cell::RefCell<Option<LarchHook>> = const { std::cell::RefCell::new(None) };
}

pub fn delegate_python(
    arguments: impl IntoIterator<Item = OsString>,
) -> Result<ProcessOutput, String> {
    let args: Vec<OsString> = arguments.into_iter().collect();
    #[cfg(test)]
    if let Some(hook) = TEST_PYTHON.with(|slot| slot.borrow().clone()) {
        return hook(&args);
    }
    run_python_verb(args, PYTHON_TIMEOUT)
}

pub fn delegate_verified_larch(
    cwd: &Path,
    root: &Path,
    args: &[OsString],
) -> Result<ProcessOutput, String> {
    #[cfg(test)]
    if let Some(hook) = TEST_LARCH.with(|slot| slot.borrow().clone()) {
        return hook(cwd, root, args);
    }
    run_verified_larch_in(cwd, root, args)
}

/// Answer every `delegate_python` call from `hook` for this thread (test only).
#[cfg(test)]
pub fn install_test_python(
    hook: impl Fn(&[OsString]) -> Result<ProcessOutput, String> + Send + Sync + 'static,
) {
    TEST_PYTHON.with(|slot| *slot.borrow_mut() = Some(std::sync::Arc::new(hook)));
}

/// Answer every `delegate_verified_larch` call from `hook` for this thread (test only).
#[cfg(test)]
pub fn install_test_larch(
    hook: impl Fn(&Path, &Path, &[OsString]) -> Result<ProcessOutput, String> + Send + Sync + 'static,
) {
    TEST_LARCH.with(|slot| *slot.borrow_mut() = Some(std::sync::Arc::new(hook)));
}

/// Restore both dispatch seams and the child seam for this thread (test only).
#[cfg(test)]
pub fn clear_test_hooks() {
    TEST_PYTHON.with(|slot| *slot.borrow_mut() = None);
    TEST_LARCH.with(|slot| *slot.borrow_mut() = None);
    crate::implement_child_seam::clear_hooks();
}

/// `implement recovery-paths` compatibility command.
pub fn recovery_paths(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        RECOVERY_PROG,
        RECOVERY_USAGE,
        RECOVERY_HELP,
        &[
            "--repo-root",
            "--tmpdir",
            "--prelaunch-porcelain",
            "--postlaunch-porcelain",
            "--prelaunch-digests",
            "--out-file",
        ],
        &["--capture-postlaunch"],
        &["--repo-root"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let repo_root = PathBuf::from(parsed.value("--repo-root").unwrap_or_default());
    let raw_tmpdir = parsed
        .value("--tmpdir")
        .map(|v| v.to_string_lossy().into_owned())
        .filter(|v| !v.is_empty())
        .or_else(|| env::var("IMPLEMENT_TMPDIR").ok().filter(|v| !v.is_empty()));
    let Some(raw_tmpdir) = raw_tmpdir else {
        eprintln!("implement recovery-paths: --tmpdir is required or IMPLEMENT_TMPDIR must be set");
        return ExitCode::from(2);
    };
    let tmpdir = PathBuf::from(raw_tmpdir);
    if parsed.flag("--capture-postlaunch") {
        let rc = capture_postlaunch_porcelain(&repo_root, &tmpdir);
        if rc != 0 {
            return ExitCode::from(rc);
        }
    }
    let porcelain = RecoveryPorcelainInputs {
        prelaunch_porcelain: resolve_tmpdir_path(
            &tmpdir,
            &opt_string(parsed.value("--prelaunch-porcelain")),
            "step2-prelaunch-porcelain.nul",
        ),
        postlaunch_porcelain: resolve_tmpdir_path(
            &tmpdir,
            &opt_string(parsed.value("--postlaunch-porcelain")),
            "step2-postlaunch-porcelain.nul",
        ),
        prelaunch_digests: resolve_tmpdir_path(
            &tmpdir,
            &opt_string(parsed.value("--prelaunch-digests")),
            "step2-prelaunch-content-digests.txt",
        ),
    };
    let out_file = resolve_tmpdir_path(
        &tmpdir,
        &opt_string(parsed.value("--out-file")),
        "step2-recovery-paths.nul",
    );
    match compute_recovery_paths(&repo_root, &tmpdir, &porcelain, &out_file) {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::from(1),
        Err(error) => {
            eprintln!("implement recovery-paths: {error}");
            ExitCode::from(2)
        }
    }
}

/// `implement run-step-checks` compatibility command.
pub fn run_step_checks(arguments: &[OsString]) -> ExitCode {
    if let Some(error) = choice_error(
        arguments,
        &[
            "--site",
            "--commit-site",
            "--forked-target",
            "--merge-result-env",
            "--repo-root",
            "--launch-head",
            "--launch-fp",
            "--launch-schema",
            "--rebase-checkpoint-4r",
            "--bgjob-child",
            "-h",
            "--help",
        ],
        &[("--forked-target", &["true", "false"])],
    ) {
        return usage_error(STEP_USAGE, STEP_PROG, &error, 2);
    }
    let parsed = match parse_required_with_help(
        arguments,
        STEP_PROG,
        STEP_USAGE,
        STEP_HELP,
        &[
            "--site",
            "--commit-site",
            "--forked-target",
            "--merge-result-env",
            "--repo-root",
            "--launch-head",
            "--launch-fp",
            "--launch-schema",
        ],
        &["--rebase-checkpoint-4r", "--bgjob-child"],
        &["--site"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let forked = {
        let raw = opt_string(parsed.value("--forked-target"));
        if raw.is_empty() {
            "false".to_owned()
        } else {
            raw
        }
    };
    let Ok(tmpdir) = tmpdir_from_env() else {
        return ExitCode::from(2);
    };
    rehydrate_session(&tmpdir);
    let site = opt_string(parsed.value("--site"));
    let (step, budget_s) = resolve_step_and_budget(&site);
    let commit_site = opt_string(parsed.value("--commit-site"));
    let rebase = parsed.flag("--rebase-checkpoint-4r");
    if parsed.flag("--bgjob-child") {
        return run_child(
            &tmpdir,
            &step,
            &site,
            &commit_site,
            &forked,
            rebase,
            &opt_string(parsed.value("--merge-result-env")),
            &opt_string(parsed.value("--repo-root")),
            &opt_string(parsed.value("--launch-head")),
            &opt_string(parsed.value("--launch-fp")),
            &opt_string(parsed.value("--launch-schema")),
        )
        .unwrap_or_else(|_| ExitCode::from(2));
    }
    match run_parent(
        &tmpdir,
        &step,
        budget_s,
        &site,
        &commit_site,
        &forked,
        rebase,
    ) {
        Ok(code) => code,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(2)
        }
    }
}

fn run_parent(
    tmpdir: &Path,
    step: &str,
    budget_s: u32,
    site: &str,
    commit_site: &str,
    forked: &str,
    rebase: bool,
) -> Result<ExitCode, String> {
    let identity = checks_launch_identity(tmpdir)?;
    let merge_raw = tmpdir.join("bgjob").join(format!("{step}.merge.env"));
    let merge_env = safe_merge_env(tmpdir, &merge_raw)?;
    prepare_checks_rejoin(tmpdir, step, &merge_env, &identity)?;
    let mut public: Vec<OsString> = vec!["--site".into(), site.into()];
    if !commit_site.is_empty() {
        public.extend(["--commit-site".into(), commit_site.into()]);
    }
    public.extend(["--forked-target".into(), forked.into()]);
    if rebase {
        public.push("--rebase-checkpoint-4r".into());
    }
    public.extend([
        "--repo-root".into(),
        identity.repo_root.clone().into(),
        "--launch-head".into(),
        identity.head_sha.clone().into(),
        "--launch-fp".into(),
        identity.tree_fp.clone().into(),
        "--launch-schema".into(),
        identity.schema.clone().into(),
    ]);
    run_bgjob_adapt(
        tmpdir,
        step,
        budget_s,
        "run-step-checks",
        &merge_env,
        &identity.as_rows(),
        &public,
        Some(&identity.repo_root),
        false,
    )
}

/// Launch the shared `bgjob adapt` wrapper for a step's verified larch verb.
///
/// Builds the canonical `bgjob adapt ... -- larch.sh implement <verb> <args>`
/// argv, delegates through the verified bootstrap, forwards captured output, and
/// returns the child's exit code as an [`ExitCode`].
#[allow(clippy::too_many_arguments)]
pub fn run_bgjob_adapt(
    tmpdir: &Path,
    step: &str,
    budget_s: u32,
    verb: &str,
    merge_env: &Path,
    initial_merge_rows: &[(String, String)],
    public_args: &[OsString],
    repo_root: Option<&Path>,
    replace_completed_result: bool,
) -> Result<ExitCode, String> {
    let root = resolve_plugin_root()?;
    let entry = root.join("scripts").join("larch.sh");
    let clone = env::current_dir().map_err(|e| e.to_string())?;
    let run_id = resolve_run_id("", tmpdir, &clone);
    let (log_dir, _, _) = log_paths(tmpdir, None, step).map_err(|e| e.to_string())?;
    let owner_pid = owner_pid_string();
    let mut argv: Vec<OsString> = vec![
        "bgjob".into(),
        "adapt".into(),
        "--step".into(),
        step.into(),
        "--tmpdir".into(),
        tmpdir.as_os_str().into(),
        "--run-id".into(),
        run_id.into(),
        "--budget-s".into(),
        budget_s.to_string().into(),
        "--log-dir".into(),
        log_dir.into(),
    ];
    if !owner_pid.is_empty() {
        argv.extend(["--owner-pid".into(), owner_pid.into()]);
    }
    argv.extend(["--merge-result-env".into(), merge_env.as_os_str().into()]);
    for (key, value) in initial_merge_rows {
        argv.extend([
            "--initial-merge-row".into(),
            format!("{key}={value}").into(),
        ]);
    }
    if replace_completed_result {
        argv.push("--replace-completed-result".into());
    }
    argv.extend([
        "--".into(),
        entry.into_os_string(),
        "implement".into(),
        verb.into(),
    ]);
    argv.extend(public_args.iter().cloned());
    let cwd = repo_root.unwrap_or(&clone);
    let output = delegate_verified_larch(cwd, &root, &argv)?;
    forward_output(&output);
    Ok(ExitCode::from(
        u8::try_from(output.status().code().unwrap_or(1)).unwrap_or(1),
    ))
}

#[allow(clippy::too_many_arguments)]
fn run_child(
    tmpdir: &Path,
    step: &str,
    site: &str,
    commit_site: &str,
    forked: &str,
    rebase: bool,
    merge_raw: &str,
    repo_root: &str,
    launch_head: &str,
    launch_fp: &str,
    launch_schema: &str,
) -> Result<ExitCode, String> {
    let merge_env = safe_merge_env(tmpdir, Path::new(merge_raw))?;
    if repo_root.is_empty()
        || launch_head.is_empty()
        || launch_fp.is_empty()
        || launch_schema.is_empty()
    {
        return Err("launch identity args required in child mode".into());
    }
    let launch = LaunchIdentity {
        head_sha: launch_head.to_owned(),
        tree_fp: launch_fp.to_owned(),
        schema: launch_schema.to_owned(),
        repo_root: PathBuf::from(repo_root),
    };
    publish_child_session(&launch, tmpdir);
    publish_identity_child(
        tmpdir,
        step,
        &merge_env,
        &launch,
        !commit_site.is_empty(),
        || run_step_checks_worker(site, commit_site, forked, rebase, tmpdir, &launch.repo_root),
    )
}

/// Publish the child's repo-root and tmpdir into the verified session env.
pub fn publish_child_session(launch: &LaunchIdentity, tmpdir: &Path) {
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
}

pub fn publish_identity_child(
    tmpdir: &Path,
    step: &str,
    merge_env: &Path,
    launch: &LaunchIdentity,
    allow_post_mutation: bool,
    worker: impl FnOnce() -> Result<(i32, String), String>,
) -> Result<ExitCode, String> {
    if validate_child_identity(launch).is_err() {
        publish_rows(
            tmpdir,
            merge_env,
            &integrity_rows(step, "pre-checks-identity-mismatch"),
        )?;
        return Ok(ExitCode::from(1));
    }
    let (rc, output) = worker()?;
    let final_identity = if allow_post_mutation && terminal_action_in_output(&output) {
        compute_identity(&launch.repo_root)?
    } else if validate_child_identity(launch).is_ok() {
        launch.clone()
    } else {
        publish_rows(
            tmpdir,
            merge_env,
            &integrity_rows(step, "pre-publish-identity-mismatch"),
        )?;
        return Ok(ExitCode::from(1));
    };
    let mut merged = output.clone();
    if !merged.is_empty() && !merged.ends_with('\n') {
        merged.push('\n');
    }
    merged.push_str(&format_rows(&final_identity.as_rows()));
    publish_rows(tmpdir, merge_env, &merged)?;
    print!("{output}");
    let _ = std::io::stdout().flush();
    Ok(ExitCode::from(u8::try_from(rc).unwrap_or(1)))
}

fn run_step_checks_worker(
    site: &str,
    commit_site: &str,
    forked: &str,
    rebase: bool,
    tmpdir: &Path,
    repo_root: &Path,
) -> Result<(i32, String), String> {
    let output = if commit_site.is_empty() {
        delegate_python([
            OsString::from("checks"),
            OsString::from("run-relevant"),
            OsString::from("--site"),
            OsString::from(site),
            OsString::from("--tmpdir"),
            tmpdir.as_os_str().to_owned(),
            OsString::from("--repo-root"),
            repo_root.as_os_str().to_owned(),
        ])?
    } else {
        let mut args = vec![
            OsString::from("implement"),
            OsString::from("checks-commit-route"),
            OsString::from("--checks-site"),
            OsString::from(site),
            OsString::from("--commit-site"),
            OsString::from(commit_site),
        ];
        if rebase {
            args.push(OsString::from("--rebase-checkpoint-4r"));
        }
        args.extend([OsString::from("--forked-target"), OsString::from(forked)]);
        delegate_python(args)?
    };
    let text = String::from_utf8_lossy(output.stdout()).into_owned();
    if !output.stderr().is_empty() {
        let _ = std::io::stderr().write_all(output.stderr());
    }
    Ok((output.status().code().unwrap_or(1), text))
}

#[derive(Clone)]
pub struct LaunchIdentity {
    pub head_sha: String,
    pub tree_fp: String,
    pub schema: String,
    pub repo_root: PathBuf,
}

impl LaunchIdentity {
    pub fn as_rows(&self) -> Vec<(String, String)> {
        vec![
            (CHECKS_HEAD.to_owned(), self.head_sha.clone()),
            (CHECKS_FP.to_owned(), self.tree_fp.clone()),
            (CHECKS_SCHEMA.to_owned(), self.schema.clone()),
        ]
    }
}

/// Resolve `REPO_ROOT` for a tmpdir in the shape the retired verb printed.
///
/// The Rust owner of `implement checks-result-identity` is now in process, so
/// this composes it directly and keeps the captured-output shape its callers
/// already branch on.
#[must_use]
pub fn resolve_repo_root_output(tmpdir: &Path) -> ProcessOutput {
    let resolved = session_repo_root(tmpdir).and_then(|raw| validate_repo_root(Path::new(&raw)));
    match resolved {
        Ok(root) => identity_stdout(&format!("REPO_ROOT={}\n", root.display())),
        Err(error) => identity_stderr(&error),
    }
}

fn identity_stdout(text: &str) -> ProcessOutput {
    ProcessOutput::new(
        ProcessStatus::new(true, Some(0)),
        text.as_bytes().to_vec(),
        Vec::new(),
        false,
        false,
    )
}

fn identity_stderr(error: &ChecksIdentityError) -> ProcessOutput {
    ProcessOutput::new(
        ProcessStatus::new(false, Some(2)),
        Vec::new(),
        format!("ERROR={error}\n").into_bytes(),
        false,
        false,
    )
}

pub fn checks_launch_identity(tmpdir: &Path) -> Result<LaunchIdentity, String> {
    let resolve = resolve_repo_root_output(tmpdir);
    if !resolve.status().success() {
        return Err(stderr_or_stdout(&resolve));
    }
    let resolve_text = String::from_utf8_lossy(resolve.stdout()).into_owned();
    let repo_root = kv_value(&resolve_text, "REPO_ROOT")
        .ok_or_else(|| "REPO_ROOT missing from resolve-repo-root".to_owned())?;
    compute_identity(Path::new(&repo_root))
}

fn compute_identity(repo_root: &Path) -> Result<LaunchIdentity, String> {
    let identity = live_identity(repo_root).map_err(|error| error.to_string())?;
    Ok(LaunchIdentity {
        head_sha: identity.head_sha,
        tree_fp: identity.tree_fingerprint,
        schema: identity.fingerprint_schema,
        repo_root: identity.repo_root,
    })
}

fn validate_child_identity(launch: &LaunchIdentity) -> Result<(), String> {
    let root = validate_repo_root(&launch.repo_root).map_err(|error| error.to_string())?;
    let current = live_identity(&root).map_err(|error| error.to_string())?;
    let expected = ChecksInputIdentity {
        head_sha: launch.head_sha.clone(),
        tree_fingerprint: launch.tree_fp.clone(),
        fingerprint_schema: launch.schema.clone(),
        repo_root: root,
    };
    if identities_match(&current, &expected) {
        Ok(())
    } else {
        Err("checks input identity drifted from launch seed".to_owned())
    }
}

pub fn prepare_checks_rejoin(
    tmpdir: &Path,
    step: &str,
    merge_env: &Path,
    identity: &LaunchIdentity,
) -> Result<(), String> {
    let result_env = result_env_path(tmpdir, step).map_err(|e| e.to_string())?;
    let host = SystemProcessIdentityHost::new();
    let live = read_for(tmpdir, step, None)
        .ok()
        .and_then(|(_, entry)| entry)
        .filter(|entry| daemon_liveness(&host, entry).live || child_liveness(&host, entry).live);
    if live.is_some() {
        let (seed, _) = classify_seed(identity, merge_env)?;
        if seed != "matching" {
            return Err(format!("live checks job identity mismatch: {seed}"));
        }
        let (completed, _) = classify_completed(identity, &result_env, step)?;
        // Live jobs: clear only stale/incomplete/unsafe completed residue; never
        // fail closed on an unsafe prior result while the daemon is still live.
        if completed != "matching" && completed != "absent" {
            unlink_safe(&result_env, tmpdir)?;
        }
        return Ok(());
    }
    let (completed, reason) = classify_completed(identity, &result_env, step)?;
    if completed == "matching" {
        return Ok(());
    }
    if completed == "unsafe" {
        return Err(if reason.is_empty() {
            "unsafe checks result env".into()
        } else {
            reason
        });
    }
    unlink_safe(&result_env, tmpdir)?;
    unlink_safe(merge_env, tmpdir)?;
    Ok(())
}

fn classify_completed(
    identity: &LaunchIdentity,
    result_env: &Path,
    step: &str,
) -> Result<(String, String), String> {
    let live = live_identity(&identity.repo_root).map_err(|error| error.to_string())?;
    let classified = classify_completed_result(result_env, step, &live, CHECKS_TERMINAL_ACTIONS);
    Ok((classified.state.to_owned(), classified.reason))
}

fn classify_seed(identity: &LaunchIdentity, merge_env: &Path) -> Result<(String, String), String> {
    let live = live_identity(&identity.repo_root).map_err(|error| error.to_string())?;
    let classified = classify_live_seed(merge_env, &live);
    Ok((classified.state.to_owned(), classified.reason))
}

pub fn safe_merge_env(tmpdir: &Path, raw: &Path) -> Result<PathBuf, String> {
    if let Ok(root) = bgjob_dir(tmpdir)
        && raw
            .parent()
            .is_some_and(|parent| fs::canonicalize(parent).ok() == fs::canonicalize(&root).ok())
    {
        let _ = fs::create_dir_all(&root);
    }
    validate_merge_result_env(raw, tmpdir).map_err(|e| e.to_string())
}

/// Reject a symlink or non-regular file before it is read or unlinked.
pub fn ensure_safe_regular_file(path: &Path) -> Result<(), String> {
    if let Ok(meta) = fs::symlink_metadata(path)
        && (meta.file_type().is_symlink() || !meta.is_file())
    {
        return Err("unsafe result file".into());
    }
    Ok(())
}

pub fn unlink_safe(path: &Path, root: &Path) -> Result<(), String> {
    ensure_safe_regular_file(path)?;
    let _ = ensure_under(path, root, "result file").map_err(|e| e.to_string())?;
    let _ = fs::remove_file(path);
    if path.exists() || path.is_symlink() {
        return Err("result file clear failed".into());
    }
    Ok(())
}

pub fn publish_rows(tmpdir: &Path, merge_env: &Path, text: &str) -> Result<(), String> {
    if !stdout_is_merge_rows(text) {
        return Err("child output is not a KV stream".into());
    }
    let safe = safe_merge_env(tmpdir, merge_env)?;
    let body = if text.is_empty() || text.ends_with('\n') {
        text.to_owned()
    } else {
        format!("{text}\n")
    };
    private_atomic_write(&safe, &body, tmpdir).map_err(|e| e.to_string())
}

fn stdout_is_merge_rows(text: &str) -> bool {
    let mut options = ParseOptions::environment();
    options.duplicates = DuplicateInputPolicy::Allow;
    options.comments = CommentPolicy::Keep;
    KvDocument::parse(text, options).is_ok()
}

fn terminal_action_in_output(text: &str) -> bool {
    let Ok(document) = KvDocument::parse(text, ParseOptions::legacy()) else {
        return false;
    };
    document
        .select_all()
        .get("NEXT_ACTION")
        .into_iter()
        .flatten()
        .any(|value| CHECKS_TERMINAL_ACTIONS.contains(&value.as_str()))
}

fn integrity_rows(step: &str, reason: &str) -> String {
    format_rows(&[
        ("STEP".into(), step.into()),
        ("BGJOB_RC".into(), "1".into()),
        ("NEXT_ACTION".into(), IDENTITY_FAILED.into()),
        ("FAILURE_REASON".into(), reason.replace(['\n', '\r'], " ")),
    ])
}

pub fn format_rows(rows: &[(String, String)]) -> String {
    let mut out = String::new();
    for (key, value) in rows {
        out.push_str(key);
        out.push('=');
        out.push_str(value);
        out.push('\n');
    }
    out
}

fn capture_postlaunch_porcelain(repo_root: &Path, tmpdir: &Path) -> u8 {
    let out = tmpdir.join("step2-postlaunch-porcelain.nul");
    let Ok(repository) = GixRepository::open(repo_root) else {
        return 1;
    };
    let Ok(status) = repository.local_status(&StatusOptions {
        include_untracked: true,
        ..StatusOptions::default()
    }) else {
        return 1;
    };
    let mut data = Vec::new();
    // Mirror git porcelain -z: XY + space + path + NUL (+ rename source for R/C).
    let mut rows = std::collections::BTreeMap::<Vec<u8>, [u8; 2]>::new();
    for change in status.tree_to_index.entries() {
        rows.entry(change.path.as_bytes().to_vec())
            .or_insert([b' ', b' '])[0] = status_byte(change.kind);
    }
    for change in status.index_to_worktree.entries() {
        rows.entry(change.path.as_bytes().to_vec())
            .or_insert([b' ', b' '])[1] = status_byte(change.kind);
    }
    for path in &status.untracked {
        rows.insert(path.as_bytes().to_vec(), [b'?', b'?']);
    }
    for (path, code) in rows {
        data.extend_from_slice(&code);
        data.push(b' ');
        data.extend_from_slice(&path);
        data.push(0);
    }
    if write_bytes_atomic(&out, &data).is_err() {
        return 1;
    }
    0
}

const fn status_byte(kind: larch_core::ChangeKind) -> u8 {
    match kind {
        larch_core::ChangeKind::Added => b'A',
        larch_core::ChangeKind::Deleted => b'D',
        larch_core::ChangeKind::Modified | larch_core::ChangeKind::SubmoduleModified => b'M',
        larch_core::ChangeKind::TypeChanged => b'T',
        larch_core::ChangeKind::Renamed => b'R',
        larch_core::ChangeKind::Copied => b'C',
    }
}

pub fn rehydrate_session(tmpdir: &Path) {
    let mut rows = Vec::new();
    if env::var_os("CLAUDE_PLUGIN_ROOT").is_none()
        && let Some(root) = session_key(tmpdir, "plugin-root.env", "CLAUDE_PLUGIN_ROOT")
            .or_else(|| session_key(tmpdir, "session-env.sh", "LARCH_CLAUDE_PLUGIN_ROOT"))
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
            && let Some(value) = session_key(tmpdir, "session-env.sh", env_key)
        {
            rows.push((child_key, OsString::from(value)));
        }
    }
    rows.push((ChildEnvironment::ImplementTmpdir, tmpdir.as_os_str().into()));
    publish_session_environment(rows);
}

fn session_key(tmpdir: &Path, file: &str, key: &str) -> Option<String> {
    let text = fs::read_to_string(tmpdir.join(file)).ok()?;
    for line in text.lines() {
        let line = line.trim_start_matches("export ").trim();
        if let Some(rest) = line.strip_prefix(&format!("{key}=")) {
            return Some(rest.trim().trim_matches(['\'', '"']).to_owned());
        }
    }
    None
}

pub fn tmpdir_from_env() -> Result<PathBuf, ()> {
    let raw = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    if raw.is_empty() {
        eprintln!("IMPLEMENT_TMPDIR required");
        return Err(());
    }
    Ok(PathBuf::from(raw))
}

/// Parse one compatibility command and rehydrate its required implement tmpdir.
pub fn parse_command_with_tmpdir(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    help: &str,
    options: &[&'static str],
    flags: &[&'static str],
    required: &[&str],
) -> Result<(ParsedCommandLine, PathBuf), ExitCode> {
    let parsed =
        parse_required_with_help(arguments, program, usage, help, options, flags, required)?;
    let tmpdir = tmpdir_from_env().map_err(|()| ExitCode::from(2))?;
    rehydrate_session(&tmpdir);
    Ok((parsed, tmpdir))
}

pub fn owner_pid_string() -> String {
    env::var("LARCH_CLAUDE_PID")
        .ok()
        .filter(|v| !v.is_empty())
        .or_else(|| owner_pid_candidate("").filter(|v| !v.is_empty()))
        .unwrap_or_else(|| {
            #[cfg(unix)]
            {
                nix::unistd::getppid().as_raw().to_string()
            }
            #[cfg(not(unix))]
            {
                String::new()
            }
        })
}

fn run_verified_larch_in(
    cwd: &Path,
    root: &Path,
    args: &[OsString],
) -> Result<ProcessOutput, String> {
    run_verified_larch_env_in(cwd, root, args, &[])
}

/// Run a verified larch verb with the standard child env plus caller extras.
pub fn run_verified_larch_env_in(
    cwd: &Path,
    root: &Path,
    args: &[OsString],
    extra: &[(ChildEnvironment, OsString)],
) -> Result<ProcessOutput, String> {
    let program = LarchProgram::bootstrap(root)
        .map_err(|error| format!("could not select verified larch entrypoint: {error}"))?;
    let mut request = bounded_request_in(
        ExternalProgram::Larch(program),
        args.iter().cloned(),
        cwd,
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

pub fn forward_output(output: &ProcessOutput) {
    let _ = std::io::stdout().write_all(output.stdout());
    let _ = std::io::stdout().flush();
    if !output.stderr().is_empty() {
        let _ = std::io::stderr().write_all(output.stderr());
    }
}

pub fn opt_string(value: Option<&OsStr>) -> String {
    value
        .map(|v| v.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn kv_value(text: &str, key: &str) -> Option<String> {
    let document = KvDocument::parse(text, ParseOptions::legacy()).ok()?;
    document
        .select(DuplicatePolicy::First)
        .get(key)
        .filter(|value| !value.is_empty())
        .cloned()
}

fn stderr_or_stdout(output: &ProcessOutput) -> String {
    let err = String::from_utf8_lossy(output.stderr());
    if err.trim().is_empty() {
        String::from_utf8_lossy(output.stdout()).into_owned()
    } else {
        err.into_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        CHECKS_FP, CHECKS_HEAD, CHECKS_SCHEMA, IDENTITY_FAILED, LaunchIdentity, TEST_LARCH,
        TEST_PYTHON, format_rows, integrity_rows, kv_value, opt_string, prepare_checks_rejoin,
        publish_identity_child, publish_rows, run_child, run_parent, run_step_checks,
        safe_merge_env, session_key, status_byte, stdout_is_merge_rows, terminal_action_in_output,
        unlink_safe,
    };
    use larch_core::{ChangeKind, ProcessOutput, ProcessStatus};
    use larch_test_support::{GitFixture, GitRepository};
    use std::{
        ffi::{OsStr, OsString},
        fs,
        path::{Path, PathBuf},
        sync::Arc,
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

    fn install_python(
        hook: impl Fn(&[OsString]) -> Result<ProcessOutput, String> + Send + Sync + 'static,
    ) {
        TEST_PYTHON.with(|slot| {
            *slot.borrow_mut() = Some(Arc::new(hook));
        });
    }

    fn install_larch(
        hook: impl Fn(&Path, &Path, &[OsString]) -> Result<ProcessOutput, String>
        + Send
        + Sync
        + 'static,
    ) {
        TEST_LARCH.with(|slot| {
            *slot.borrow_mut() = Some(Arc::new(hook));
        });
    }

    fn clear_hooks() {
        TEST_PYTHON.with(|slot| *slot.borrow_mut() = None);
        TEST_LARCH.with(|slot| *slot.borrow_mut() = None);
        crate::implement_child_seam::clear_hooks();
    }

    fn identity(repo: &Path) -> LaunchIdentity {
        LaunchIdentity {
            head_sha: "abc123".into(),
            tree_fp: "fp1".into(),
            schema: "v1".into(),
            repo_root: repo.to_path_buf(),
        }
    }

    /// The identity verbs are in process now, so these tests need real Git.
    fn git_repository() -> GitRepository {
        GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("git fixture")
    }

    fn live(repo: &Path) -> LaunchIdentity {
        super::compute_identity(repo).expect("live identity")
    }

    fn matching_result_rows(identity: &LaunchIdentity, step: &str) -> String {
        format!(
            "BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP={step}\n{CHECKS_HEAD}={}\n{CHECKS_FP}={}\n{CHECKS_SCHEMA}={}\n",
            identity.head_sha, identity.tree_fp, identity.schema
        )
    }

    fn args_contain(args: &[OsString], needle: &str) -> bool {
        args.iter().any(|arg| arg == needle)
    }

    #[test]
    fn merge_rows_accept_environment_keys_and_reject_noise() {
        assert!(stdout_is_merge_rows("STEP=step3\nBGJOB_RC=0\n"));
        assert!(stdout_is_merge_rows("A=1\nA=2\n"));
        assert!(!stdout_is_merge_rows("not a kv line\n"));
        assert!(!stdout_is_merge_rows("bad-key=1\n"));
    }

    #[test]
    fn terminal_action_detects_known_next_actions() {
        assert!(terminal_action_in_output("NEXT_ACTION=continue\n"));
        assert!(terminal_action_in_output("NEXT_ACTION=stall\n"));
        assert!(!terminal_action_in_output("NEXT_ACTION=unknown\n"));
        assert!(!terminal_action_in_output("STEP=only\n"));
    }

    #[test]
    fn integrity_rows_sanitize_newlines() {
        let rows = integrity_rows("implement-step3-checks", "bad\nreason\rhere");
        assert!(rows.contains("STEP=implement-step3-checks\n"));
        assert!(rows.contains(&format!("NEXT_ACTION={IDENTITY_FAILED}\n")));
        assert!(rows.contains("FAILURE_REASON=bad reason here\n"));
        assert!(!rows.contains('\r'));
    }

    #[test]
    fn format_rows_emits_trailing_newlines() {
        assert_eq!(
            format_rows(&[("A".into(), "1".into()), ("B".into(), "2".into())]),
            "A=1\nB=2\n"
        );
    }

    #[test]
    fn status_byte_covers_change_kinds() {
        assert_eq!(status_byte(ChangeKind::Added), b'A');
        assert_eq!(status_byte(ChangeKind::Deleted), b'D');
        assert_eq!(status_byte(ChangeKind::Modified), b'M');
        assert_eq!(status_byte(ChangeKind::SubmoduleModified), b'M');
        assert_eq!(status_byte(ChangeKind::TypeChanged), b'T');
        assert_eq!(status_byte(ChangeKind::Renamed), b'R');
        assert_eq!(status_byte(ChangeKind::Copied), b'C');
    }

    #[test]
    fn kv_value_reads_first_nonempty() {
        assert_eq!(
            kv_value("FOO=kept\nFOO=later\n", "FOO").as_deref(),
            Some("kept")
        );
        assert_eq!(kv_value("FOO=\n", "FOO"), None);
        assert_eq!(kv_value("BAR=1\n", "FOO"), None);
    }

    #[test]
    fn opt_string_defaults_empty() {
        assert_eq!(opt_string(None), "");
        assert_eq!(opt_string(Some(OsStr::new("x"))), "x");
    }

    #[test]
    fn session_key_parses_export_and_plain_assignments() {
        let root = TempDir::new().expect("temp");
        let path = root.path().join("session-env.sh");
        fs::write(
            &path,
            "export CLAUDE_PLUGIN_ROOT='/plugins/larch'\nLARCH_TOKEN_SESSION_ID=\"abc\"\n",
        )
        .expect("write");
        assert_eq!(
            session_key(root.path(), "session-env.sh", "CLAUDE_PLUGIN_ROOT").as_deref(),
            Some("/plugins/larch")
        );
        assert_eq!(
            session_key(root.path(), "session-env.sh", "LARCH_TOKEN_SESSION_ID").as_deref(),
            Some("abc")
        );
        assert_eq!(session_key(root.path(), "session-env.sh", "MISSING"), None);
    }

    #[test]
    fn publish_rows_and_unlink_round_trip() {
        let root = TempDir::new().expect("temp");
        let merge = root.path().join("merge.env");
        publish_rows(root.path(), &merge, "STEP=step3\nBGJOB_RC=0").expect("publish");
        assert_eq!(
            fs::read_to_string(&merge).expect("read"),
            "STEP=step3\nBGJOB_RC=0\n"
        );
        unlink_safe(&merge, root.path()).expect("unlink");
        assert!(!merge.exists());
    }

    #[test]
    fn publish_rows_rejects_non_kv() {
        let root = TempDir::new().expect("temp");
        let merge = root.path().join("merge.env");
        let err = publish_rows(root.path(), &merge, "not-kv").expect_err("reject");
        assert!(err.contains("KV stream"));
    }

    #[test]
    fn launch_identity_rows_and_safe_merge_env() {
        let root = TempDir::new().expect("temp");
        let id = identity(root.path());
        let rows = id.as_rows();
        assert_eq!(rows[0].0, CHECKS_HEAD);
        assert_eq!(rows[1].0, CHECKS_FP);
        assert_eq!(rows[2].0, CHECKS_SCHEMA);
        let merge = root.path().join("bgjob").join("step.merge.env");
        let safe = safe_merge_env(root.path(), &merge).expect("safe");
        assert_eq!(
            safe.file_name().and_then(|name| name.to_str()),
            Some("step.merge.env")
        );
    }

    #[test]
    fn prepare_checks_rejoin_absent_clears_merge_and_result() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(tmp.join("bgjob")).expect("bgjob");
        let merge = tmp.join("bgjob").join("implement-step3-checks.merge.env");
        fs::write(&merge, "X=1\n").expect("merge");
        let result = tmp.join("bgjob").join("implement-step3-checks.result.env");
        fs::write(&result, "Y=1\n").expect("result");
        prepare_checks_rejoin(
            &tmp,
            "implement-step3-checks",
            &merge,
            &live(repository.root()),
        )
        .expect("rejoin");
        assert!(!merge.exists());
        assert!(!result.exists());
        clear_hooks();
    }

    #[test]
    fn prepare_checks_rejoin_matching_keeps_artifacts() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(tmp.join("bgjob")).expect("bgjob");
        let merge = tmp.join("bgjob").join("implement-step3-checks.merge.env");
        fs::write(&merge, "X=1\n").expect("merge");
        let launch = live(repository.root());
        let result = tmp.join("bgjob").join("implement-step3-checks.result.env");
        fs::write(
            &result,
            matching_result_rows(&launch, "implement-step3-checks"),
        )
        .expect("result");
        prepare_checks_rejoin(&tmp, "implement-step3-checks", &merge, &launch).expect("rejoin");
        assert!(merge.exists());
        assert!(result.exists());
        clear_hooks();
    }

    #[cfg(unix)]
    #[test]
    fn prepare_checks_rejoin_unsafe_fails() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(tmp.join("bgjob")).expect("bgjob");
        let merge = tmp.join("bgjob").join("implement-step3-checks.merge.env");
        let result = tmp.join("bgjob").join("implement-step3-checks.result.env");
        std::os::unix::fs::symlink(root.path().join("elsewhere"), &result).expect("symlink");
        let err = prepare_checks_rejoin(
            &tmp,
            "implement-step3-checks",
            &merge,
            &live(repository.root()),
        )
        .expect_err("unsafe");
        assert!(err.contains("non-regular-result-env"), "{err}");
        clear_hooks();
    }

    #[test]
    fn publish_identity_child_publishes_worker_rows() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(&tmp).expect("tmp");
        let merge = tmp.join("merge.env");
        let launch = live(repository.root());
        let code = publish_identity_child(
            &tmp,
            "implement-step3-checks",
            &merge,
            &launch,
            false,
            || {
                Ok((
                    0,
                    "NEXT_ACTION=continue\nSTEP=implement-step3-checks\n".into(),
                ))
            },
        )
        .expect("publish");
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        let body = fs::read_to_string(&merge).expect("merge");
        assert!(body.contains("NEXT_ACTION=continue"));
        assert!(body.contains(CHECKS_HEAD));
        clear_hooks();
    }

    #[test]
    fn publish_identity_child_pre_checks_mismatch_writes_integrity() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(&tmp).expect("tmp");
        let merge = tmp.join("merge.env");
        let code = publish_identity_child(
            &tmp,
            "implement-step3-checks",
            &merge,
            &identity(root.path()),
            false,
            || panic!("worker must not run"),
        )
        .expect("publish");
        assert_eq!(code, std::process::ExitCode::from(1));
        let body = fs::read_to_string(&merge).expect("merge");
        assert!(body.contains(IDENTITY_FAILED));
        clear_hooks();
    }

    #[test]
    fn run_child_drives_checks_run_relevant() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(tmp.join("bgjob")).expect("bgjob");
        let merge = tmp.join("bgjob").join("child.merge.env");
        let launch = live(repository.root());
        install_python(|args| {
            if args_contain(args, "run-relevant") {
                Ok(output(0, "NEXT_ACTION=continue\n"))
            } else {
                Err(format!("unexpected args: {args:?}"))
            }
        });
        let code = run_child(
            &tmp,
            "implement-step3-checks",
            "step3",
            "",
            "false",
            false,
            merge.to_str().expect("utf8"),
            launch.repo_root.to_str().expect("utf8"),
            &launch.head_sha,
            &launch.tree_fp,
            &launch.schema,
        )
        .expect("child");
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        clear_hooks();
    }

    #[test]
    fn run_child_commit_route_passes_rebase_flag() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(tmp.join("bgjob")).expect("bgjob");
        let merge = tmp.join("bgjob").join("child.merge.env");
        let launch = live(repository.root());
        install_python(|args| {
            if args_contain(args, "checks-commit-route") {
                assert!(args_contain(args, "--rebase-checkpoint-4r"));
                Ok(output(0, "NEXT_ACTION=continue\n"))
            } else {
                Err(format!("unexpected args: {args:?}"))
            }
        });
        let code = run_child(
            &tmp,
            "implement-step3-checks",
            "step3",
            "commit-site",
            "true",
            true,
            merge.to_str().expect("utf8"),
            launch.repo_root.to_str().expect("utf8"),
            &launch.head_sha,
            &launch.tree_fp,
            &launch.schema,
        )
        .expect("child");
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        let body = fs::read_to_string(&merge).expect("merge");
        assert!(body.contains(&format!("{CHECKS_FP}={}", launch.tree_fp)));
        clear_hooks();
    }

    #[test]
    fn run_parent_adapts_bgjob_with_launch_identity() {
        clear_hooks();
        let repository = git_repository();
        let root = TempDir::new().expect("temp");
        let tmp = root.path().join("tmp");
        fs::create_dir_all(tmp.join("bgjob")).expect("bgjob");
        fs::write(
            tmp.join("session-env.sh"),
            format!("REPO_ROOT={}\n", repository.root().display()),
        )
        .expect("session env");
        let plugin = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        crate::implement_child_seam::declare_plugin_root(&plugin);
        install_larch(|_cwd, _root, args| {
            assert!(args_contain(args, "bgjob"));
            assert!(args_contain(args, "adapt"));
            assert!(args_contain(args, "run-step-checks"));
            Ok(output(0, "NEXT_ACTION=continue\n"))
        });
        let code = run_parent(
            &tmp,
            "implement-step3-checks",
            10,
            "step3",
            "commit-a",
            "false",
            true,
        )
        .expect("parent");
        assert_eq!(code, std::process::ExitCode::SUCCESS);
        clear_hooks();
    }

    #[test]
    fn run_step_checks_invalid_forked_target_exits_two() {
        let code = run_step_checks(&[
            OsString::from("--site"),
            OsString::from("step3"),
            OsString::from("--forked-target"),
            OsString::from("maybe"),
        ]);
        assert_eq!(code, std::process::ExitCode::from(2));
    }
}
