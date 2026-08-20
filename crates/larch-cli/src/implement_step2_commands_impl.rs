// Included by `implement_step2_commands.rs`; not a standalone module.
//
// Holds the Step 2 orchestrator body, its git probes, and the shared
// `run-dispatch` helpers so the entry points above stay readable.

// ---------------------------------------------------------------------------
// run-dispatch support
// ---------------------------------------------------------------------------

/// The exclusive per-tmpdir dispatch lock.
///
/// One dispatch per session tmpdir: a second launcher would race the same
/// manifest and porcelain baselines. The lock is advisory and released when the
/// descriptor closes, so a killed dispatcher does not strand it.
struct DispatchLock {
    #[cfg(unix)]
    _held: nix::fcntl::Flock<fs::File>,
}

impl DispatchLock {
    fn acquire(path: &Path) -> Option<Self> {
        let file = match fs::File::create(path) {
            Ok(file) => file,
            Err(error) => {
                eprintln!("implement run-dispatch: failed to acquire dispatch lock: {error}");
                return None;
            }
        };
        #[cfg(unix)]
        {
            match nix::fcntl::Flock::lock(file, nix::fcntl::FlockArg::LockExclusiveNonblock) {
                Ok(held) => Some(Self { _held: held }),
                Err((_file, nix::errno::Errno::EAGAIN)) => {
                    eprintln!(
                        "implement run-dispatch: another dispatch is already running in this tmpdir"
                    );
                    None
                }
                Err((_file, error)) => {
                    eprintln!("implement run-dispatch: failed to acquire dispatch lock: {error}");
                    None
                }
            }
        }
        #[cfg(not(unix))]
        {
            drop(file);
            Some(Self {})
        }
    }
}

/// The validated `run-dispatch` command line plus the child it will run.
struct RunDispatchRequest {
    tmpdir: PathBuf,
    plugin_root: PathBuf,
    coder: String,
    answers: String,
    codex_binary_found: String,
    cursor_binary_found: String,
    /// The bgjob envelope path, empty when this is not a bgjob leg.
    merge_result_env: String,
    child: Vec<OsString>,
}

/// Parse and validate the `run-dispatch` command line.
///
/// Every refusal here exits `2`: no dispatch has started, so there is no Step 2
/// contract to route a bail through.
#[allow(clippy::too_many_lines)]
fn parse_run_dispatch(arguments: &[OsString]) -> Result<RunDispatchRequest, ExitCode> {
    if let Some(error) = choice_error(
        arguments,
        &RUN_OPTIONS,
        &[("--difficulty", &DIFFICULTY_CHOICES)],
    ) {
        return Err(usage_error(RUN_USAGE, RUN_PROG, &error, 2));
    }
    let parsed = parse_required_with_help(
        arguments,
        RUN_PROG,
        RUN_USAGE,
        RUN_HELP,
        &[
            "--implement-tmpdir",
            "--coder",
            "--answers",
            "--difficulty",
            "--merge-result-env",
        ],
        &["--bgjob-child"],
        &["--coder"],
    )?;
    let coder = text(parsed.value("--coder"));
    let answers = text(parsed.value("--answers"));
    let merge_result_env = text(parsed.value("--merge-result-env"));
    if parsed.flag("--bgjob-child") == merge_result_env.is_empty() {
        eprintln!(
            "implement run-dispatch: --bgjob-child and --merge-result-env must be supplied together"
        );
        return Err(ExitCode::from(2));
    }
    let raw_tmpdir = text(parsed.value("--implement-tmpdir"));
    let raw_tmpdir = if raw_tmpdir.is_empty() {
        env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
    } else {
        raw_tmpdir
    };
    if raw_tmpdir.is_empty() {
        eprintln!(
            "implement run-dispatch: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set"
        );
        return Err(ExitCode::from(2));
    }
    let tmp_arg = PathBuf::from(&raw_tmpdir);
    if !tmp_arg.is_dir() {
        eprintln!(
            "implement run-dispatch: --implement-tmpdir not a directory: {}",
            tmp_arg.display()
        );
        return Err(ExitCode::from(2));
    }
    let tmpdir = tmp_arg.canonicalize().unwrap_or(tmp_arg);
    let session_env = tmpdir.join("session-env.sh");
    let feature_file = tmpdir.join("feature-description.txt");
    let plan_file = tmpdir.join("plan.txt");
    for (path, message) in [
        (&session_env, "session-env not readable"),
        (&feature_file, "feature file not found"),
        (&plan_file, "plan file not found at conventional path"),
    ] {
        if !path.is_file() {
            eprintln!(
                "implement run-dispatch: {message}: {path}",
                path = path.display()
            );
            return Err(ExitCode::from(2));
        }
    }
    if !answers.is_empty() && !Path::new(&answers).is_file() {
        eprintln!("implement run-dispatch: --answers path does not exist: {answers}");
        return Err(ExitCode::from(2));
    }
    let plugin_root = resolve_run_dispatch_plugin_root(&session_env);
    if !plugin_root.is_dir() {
        eprintln!(
            "implement run-dispatch: plugin root not a directory: {}",
            plugin_root.display()
        );
        return Err(ExitCode::from(2));
    }
    let cursor_binary_found = binary_available(&session_env, "CURSOR_BINARY_FOUND", "cursor");
    let codex_binary_found = binary_available(&session_env, "CODEX_BINARY_FOUND", "codex");
    let requested_difficulty = text(parsed.value("--difficulty"));
    let difficulty = if requested_difficulty.is_empty() {
        resolve_step2_effective_difficulty(&tmpdir)
    } else {
        requested_difficulty
    };
    let mut child: Vec<OsString> = vec![
        "implement".into(),
        "step2-dispatch".into(),
        "--tmpdir".into(),
        tmpdir.as_os_str().into(),
        "--plan-file".into(),
        plan_file.as_os_str().into(),
        "--feature-file".into(),
        feature_file.as_os_str().into(),
        "--coder".into(),
        coder.as_str().into(),
        "--cursor-binary-found".into(),
        cursor_binary_found.as_str().into(),
        "--codex-binary-found".into(),
        codex_binary_found.as_str().into(),
    ];
    if !difficulty.is_empty() {
        child.extend(["--difficulty".into(), difficulty.as_str().into()]);
    }
    if !answers.is_empty() {
        child.extend(["--answers".into(), answers.as_str().into()]);
    }
    Ok(RunDispatchRequest {
        tmpdir,
        plugin_root,
        coder,
        answers,
        codex_binary_found,
        cursor_binary_found,
        merge_result_env,
        child,
    })
}

/// Resolve the plugin root `run-dispatch` composes its child from.
fn resolve_run_dispatch_plugin_root(session_env: &Path) -> PathBuf {
    if let Some(root) = env::var_os("CLAUDE_PLUGIN_ROOT").filter(|value| !value.is_empty()) {
        return PathBuf::from(root);
    }
    let recorded = read_kv_first(session_env, "LARCH_CLAUDE_PLUGIN_ROOT");
    if !recorded.is_empty() {
        return PathBuf::from(recorded);
    }
    resolve_plugin_root().unwrap_or_else(|_| PathBuf::from("."))
}

/// Whether an external coder binary is usable, preferring the session's record.
fn binary_available(session_env: &Path, key: &str, binary: &str) -> String {
    match read_kv_first(session_env, key).as_str() {
        "true" => "true".to_owned(),
        "false" => "false".to_owned(),
        _ => crate::implement_commands::on_path(binary).to_string(),
    }
}

/// Step 2 difficulty, with the operator override ahead of the design prior.
fn resolve_step2_effective_difficulty(tmpdir: &Path) -> String {
    let override_tier = normalize_tier(
        &read_kv_first(&tmpdir.join("run-flags.sh"), "DIFFICULTY_OVERRIDE"),
        "",
    );
    if !override_tier.is_empty() {
        return override_tier;
    }
    normalize_tier(
        &read_kv_first(&tmpdir.join("difficulty-prior.env"), "DESIGN_DIFFICULTY"),
        "",
    )
}

/// Charge this run's Step 2 token and timing budgets exactly once.
///
/// Returns whether the sentinel may be written: a failed mark must not be
/// recorded as charged, or the budget silently disappears from the ledger.
fn mark_step2_telemetry(
    tmpdir: &Path,
    plugin_root: &Path,
    coder: &str,
    codex_binary_found: &str,
    cursor_binary_found: &str,
) -> bool {
    if tmpdir.join(".step2-telemetry-marked").is_file() {
        return true;
    }
    if step2_token_mark_eligible(coder, codex_binary_found, cursor_binary_found) {
        let argv: Vec<OsString> = vec![
            "token".into(),
            "mark".into(),
            IMPLEMENT_STEP2_LABEL.into(),
        ];
        match delegate_verified_larch(tmpdir, plugin_root, &argv) {
            Ok(output) if output.status().code() == Some(0) => {}
            _ => return false,
        }
    }
    let argv: Vec<OsString> = vec![
        "timing".into(),
        "mark".into(),
        IMPLEMENT_STEP2_LABEL.into(),
    ];
    let extra = [
        (ChildEnvironment::DesignTmpdir, OsString::new()),
        (
            ChildEnvironment::LarchTimingSkill,
            OsString::from("implement"),
        ),
    ];
    matches!(
        crate::implement_dispatch_commands::run_verified_larch_env_in(
            tmpdir,
            plugin_root,
            &argv,
            &extra,
        ),
        Ok(output) if output.status().code() == Some(0)
    )
}

fn write_step2_telemetry_sentinel(tmpdir: &Path) {
    let _written = write_atomic(&tmpdir.join(".step2-telemetry-marked"), "true\n");
}

/// Republish the child's stdout as this leg's bgjob result envelope.
///
/// The adapter pre-creates the path; it is validated again here because the
/// child must never write an arbitrary caller-named path while it owns a live
/// dispatch.
fn publish_bgjob_envelope(tmpdir: &Path, path: &Path, text: &str) -> bool {
    let Ok(merge_env) = larch_core::validate_merge_result_env(path, tmpdir) else {
        return false;
    };
    write_bytes_atomic(&merge_env, text.as_bytes()).is_ok()
}

/// Clear the ship-seed keys that name an external dispatch's committed result.
fn clear_external_dispatch_seed(tmpdir: &Path) {
    let path = tmpdir.join("ship-seed-input.env");
    let existing = fs::read_to_string(&path).unwrap_or_default();
    let mut lines: Vec<String> = existing.lines().map(str::to_owned).collect();
    for key in ["MANIFEST_PATH", "DISPATCHER_COMMITTED"] {
        let prefix = format!("{key}=");
        match lines.iter().position(|line| line.starts_with(&prefix)) {
            Some(index) => lines[index] = prefix,
            None => lines.push(prefix),
        }
    }
    let mut text = lines.join("\n");
    if !text.is_empty() {
        text.push('\n');
    }
    let _written = write_atomic(&path, &text);
}

fn discover_repo_root() -> Option<PathBuf> {
    use std::os::unix::ffi::OsStringExt as _;

    let cwd = env::current_dir().ok()?;
    let work_dir = GixRepository::discover(&cwd).ok()?.location().work_dir?;
    let bytes = work_dir.as_bytes().to_vec();
    (!bytes.contains(&0)).then(|| PathBuf::from(OsString::from_vec(bytes)))
}

// ---------------------------------------------------------------------------
// git probes
// ---------------------------------------------------------------------------

/// One porcelain snapshot of the working tree.
#[derive(Default)]
struct WorkingTree {
    /// Paths differing between HEAD and the index.
    staged: Vec<String>,
    /// Paths differing between the index and the working tree.
    unstaged: Vec<String>,
    /// Untracked, non-ignored paths.
    untracked: Vec<String>,
    /// Whether any entry reports a modified submodule.
    submodule_modified: bool,
}

impl WorkingTree {
    /// Every path `git diff --name-only HEAD` would report.
    fn tracked_changes(&self) -> Vec<String> {
        let mut paths = self.staged.clone();
        paths.extend(self.unstaged.iter().cloned());
        paths.sort_unstable();
        paths.dedup();
        paths
    }

    /// Every path `git status --porcelain` would report.
    const fn dirty(&self) -> bool {
        !self.staged.is_empty() || !self.unstaged.is_empty() || !self.untracked.is_empty()
    }

    /// Every path any porcelain row names, including untracked entries.
    fn all_paths(&self) -> Vec<String> {
        let mut paths = self.tracked_changes();
        paths.extend(self.untracked.iter().cloned());
        paths.sort_unstable();
        paths.dedup();
        paths
    }
}

/// Snapshot the working tree, or `None` when the probe itself failed.
///
/// A failed probe is never reported as a clean tree: callers fail closed on it.
fn working_tree(repo_root: &Path) -> Option<WorkingTree> {
    let status = crate::implement_dispatch_commands::untracked_local_status(repo_root)?;
    let mut tree = WorkingTree::default();
    for change in status.tree_to_index.entries() {
        tree.staged
            .push(String::from_utf8_lossy(change.path.as_bytes()).into_owned());
        tree.submodule_modified |= change.kind == ChangeKind::SubmoduleModified;
    }
    for change in status.index_to_worktree.entries() {
        tree.unstaged
            .push(String::from_utf8_lossy(change.path.as_bytes()).into_owned());
        tree.submodule_modified |= change.kind == ChangeKind::SubmoduleModified;
    }
    for path in &status.untracked {
        tree.untracked
            .push(String::from_utf8_lossy(path.as_bytes()).into_owned());
    }
    Some(tree)
}

/// The full HEAD commit, or empty when HEAD names no commit.
fn head_sha(repo_root: &Path) -> String {
    let Ok(repository) = GixRepository::open(repo_root) else {
        return String::new();
    };
    repository
        .resolve_revision(&Revision::new(b"HEAD".to_vec()))
        .map(|object| object.to_hex())
        .unwrap_or_default()
}

/// The checked-out branch, or empty for a detached HEAD.
fn symbolic_branch(repo_root: &Path) -> String {
    let Ok(repository) = GixRepository::open(repo_root) else {
        return String::new();
    };
    let Ok(head) = repository.head() else {
        return String::new();
    };
    match head {
        Head::Symbolic { name, .. } | Head::Unborn { name } => {
            let raw = name.as_bytes();
            let stripped = raw.strip_prefix(b"refs/heads/").unwrap_or(raw);
            String::from_utf8_lossy(stripped).into_owned()
        }
        Head::Detached { .. } => String::new(),
    }
}

/// The checked-out branch, or `HEAD` for a detached HEAD.
fn abbrev_ref(repo_root: &Path) -> String {
    let branch = symbolic_branch(repo_root);
    if branch.is_empty() {
        "HEAD".to_owned()
    } else {
        branch
    }
}

/// Every submodule path declared at or below the repository root.
///
/// Reads the declaring `.gitmodules` files rather than running a submodule
/// walk: only the declared paths matter here, and an unfetched submodule still
/// has to be protected from a coder's edits.
fn submodule_roots(repo_root: &Path) -> Vec<String> {
    let mut roots = Vec::new();
    collect_submodule_roots(repo_root, "", &mut roots, 0);
    roots.sort_unstable();
    roots.dedup();
    roots
}

/// Recursion bound for nested `.gitmodules` discovery.
const SUBMODULE_DEPTH_LIMIT: usize = 8;

fn collect_submodule_roots(root: &Path, prefix: &str, roots: &mut Vec<String>, depth: usize) {
    if depth > SUBMODULE_DEPTH_LIMIT {
        return;
    }
    let text = fs::read_to_string(root.join(".gitmodules")).unwrap_or_default();
    for line in text.lines() {
        let trimmed = line.trim();
        let Some(rest) = trimmed.strip_prefix("path") else {
            continue;
        };
        let Some(index) = rest.find('=') else {
            continue;
        };
        let value = rest[index + 1..].trim().trim_matches('/');
        if value.is_empty() || value.contains("..") || value.starts_with('/') {
            continue;
        }
        let joined = if prefix.is_empty() {
            value.to_owned()
        } else {
            format!("{prefix}/{value}")
        };
        roots.push(joined.clone());
        collect_submodule_roots(&root.join(value), &joined, roots, depth + 1);
    }
}

/// `git submodule status --recursive` output, for the dirty-prefix check.
fn submodule_status_text(repo_root: &Path) -> String {
    let mut text = String::new();
    let tree = working_tree(repo_root);
    let dirty_submodule = tree.as_ref().is_some_and(|tree| tree.submodule_modified);
    for root in submodule_roots(repo_root) {
        let marker = if dirty_submodule { '+' } else { ' ' };
        text.push(marker);
        text.push_str("0000000 ");
        text.push_str(&root);
        text.push('\n');
    }
    text
}

/// Stage every change and commit the message file, retrying once.
///
/// The single retry mirrors the retired owner: a concurrent index writer can
/// lose one `add`/`commit` pair, and the second attempt runs against the same
/// baselined tree.
fn commit_all(repo_root: &Path, message_file: &Path) -> Result<(), String> {
    let runtime = crate::git_command_runtime::GitCommandRuntime::for_repository(repo_root)?;
    let message = GitFilePath::new(message_file.as_os_str().to_owned())
        .map_err(|error| error.to_string())?;
    let mut last_error = String::new();
    for _attempt in 0..2 {
        let git = runtime.git_cli();
        let add = runtime.runtime.block_on(git.add(
            AddRequest {
                all: true,
                force: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            },
            &runtime.cancellation,
        ));
        if let Err(error) = add {
            return Err(git_failure_text(&error, "git add failed"));
        }
        let commit = runtime.runtime.block_on(git.commit(
            CommitRequest {
                message: Some(CommitMessage::File(message.clone())),
                amend: false,
                no_edit: false,
                allow_empty: false,
                only: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            },
            &runtime.cancellation,
        ));
        match commit {
            Ok(_result) => return Ok(()),
            Err(error) => last_error = git_failure_text(&error, "git commit failed"),
        }
    }
    Err(last_error)
}

fn git_failure_text(error: &larch_adapters::GitCliError, fallback: &str) -> String {
    let text = match error {
        larch_adapters::GitCliError::Failed(result) => {
            String::from_utf8_lossy(result.output().stderr()).into_owned()
        }
        other => other.to_string(),
    };
    if text.trim().is_empty() {
        fallback.to_owned()
    } else {
        text
    }
}

// ---------------------------------------------------------------------------
// step2-dispatch request
// ---------------------------------------------------------------------------

/// The validated `step2-dispatch` command line.
struct Step2Request {
    tmpdir: PathBuf,
    plan_file: PathBuf,
    feature_file: PathBuf,
    coder: String,
    cursor_present: String,
    codex_binary_found: String,
    cursor_binary_found: String,
    answers: String,
    completion_retry: bool,
    difficulty: String,
}

/// Parse and validate the `step2-dispatch` command line.
///
/// Every refusal here is a usage failure, so it exits `2` rather than routing a
/// bail: no dispatch state exists yet to bail from.
#[allow(clippy::too_many_lines)]
fn step2_dispatch_argv(arguments: &[OsString]) -> Result<Step2Request, ExitCode> {
    if let Some(error) = choice_error(
        arguments,
        &STEP2_OPTIONS,
        &[("--difficulty", &DIFFICULTY_CHOICES)],
    ) {
        return Err(usage_error(STEP2_USAGE, STEP2_PROG, &error, 2));
    }
    let parsed = parse_required_with_help(
        arguments,
        STEP2_PROG,
        STEP2_USAGE,
        STEP2_HELP,
        &[
            "--tmpdir",
            "--plan-file",
            "--feature-file",
            "--coder",
            "--codex-available",
            "--cursor-present",
            "--codex-present",
            "--cursor-available",
            "--codex-binary-found",
            "--cursor-binary-found",
            "--answers",
            "--difficulty",
        ],
        &["--completion-retry"],
        &["--tmpdir", "--plan-file", "--feature-file"],
    )?;
    let mut coder = text(parsed.value("--coder"));
    let codex_available = text(parsed.value("--codex-available"));
    if !coder.is_empty() && !codex_available.is_empty() {
        eprintln!(
            "implement step2-dispatch: --coder and --codex-available are mutually exclusive"
        );
        return Err(ExitCode::from(2));
    }
    if !codex_available.is_empty() {
        match codex_available.as_str() {
            "true" => {
                eprintln!(
                    "implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder codex instead"
                );
                coder.clear();
                coder.push_str("codex");
            }
            "false" => {
                eprintln!(
                    "implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder claude instead"
                );
                coder.clear();
                coder.push_str("claude");
            }
            other => {
                eprintln!(
                    "implement step2-dispatch: --codex-available must be 'true' or 'false', got: {other}"
                );
                return Err(ExitCode::from(2));
            }
        }
    }
    if coder.is_empty() {
        eprintln!("implement step2-dispatch: --coder is required");
        return Err(ExitCode::from(2));
    }
    if !SAFE_CODERS.contains(&coder.as_str()) {
        eprintln!(
            "implement step2-dispatch: --coder must be one of {{claude,codex,cursor}}, got: {coder}"
        );
        return Err(ExitCode::from(2));
    }
    for flag in [
        "--codex-present",
        "--cursor-present",
        "--cursor-available",
        "--codex-binary-found",
        "--cursor-binary-found",
    ] {
        let value = text(parsed.value(flag));
        if !value.is_empty() && value != "true" && value != "false" {
            eprintln!(
                "implement step2-dispatch: {flag} must be 'true', 'false', or empty, got: {value}"
            );
            return Err(ExitCode::from(2));
        }
    }
    let raw_tmpdir = text(parsed.value("--tmpdir"));
    let raw_tmpdir = if raw_tmpdir.is_empty() {
        env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
    } else {
        raw_tmpdir
    };
    let tmpdir_raw = PathBuf::from(&raw_tmpdir);
    if !tmpdir_raw.is_dir() {
        eprintln!(
            "implement step2-dispatch: --tmpdir not a directory: {}",
            tmpdir_raw.display()
        );
        return Err(ExitCode::from(2));
    }
    let tmpdir = tmpdir_raw.canonicalize().unwrap_or(tmpdir_raw);
    let difficulty = {
        let requested = text(parsed.value("--difficulty"));
        if requested.is_empty() {
            resolve_step2_effective_difficulty(&tmpdir)
        } else {
            requested
        }
    };
    publish_step2_child_environment(&tmpdir);
    let plan_file = PathBuf::from(text(parsed.value("--plan-file")));
    let feature_file = PathBuf::from(text(parsed.value("--feature-file")));
    for (path, flag) in [(&plan_file, "--plan-file"), (&feature_file, "--feature-file")] {
        if !path.is_file() {
            eprintln!(
                "implement step2-dispatch: {flag} not found: {}",
                path.display()
            );
            return Err(ExitCode::from(2));
        }
    }
    Ok(Step2Request {
        tmpdir,
        plan_file,
        feature_file,
        coder,
        cursor_present: text(parsed.value("--cursor-present")),
        codex_binary_found: text(parsed.value("--codex-binary-found")),
        cursor_binary_found: text(parsed.value("--cursor-binary-found")),
        answers: text(parsed.value("--answers")),
        completion_retry: parsed.flag("--completion-retry"),
        difficulty,
    })
}

/// Session identity rows every child of this dispatch inherits.
///
/// The workspace forbids mutating this process's own environment, so the rows
/// travel explicitly instead: published for delegated Python verbs and passed
/// to each verified `larch` child.
static STEP2_CHILD_ENVIRONMENT: Mutex<Vec<(ChildEnvironment, OsString)>> = Mutex::new(Vec::new());

/// Resolve this dispatch's session identity and publish it to every child path.
fn publish_step2_child_environment(tmpdir: &Path) {
    let mut rows = vec![(ChildEnvironment::ImplementTmpdir, tmpdir.as_os_str().into())];
    let session_id = fs::read_to_string(tmpdir.join("session-id")).unwrap_or_default();
    let session_id = session_id.trim();
    if !session_id.is_empty() {
        rows.push((
            ChildEnvironment::LarchTokenSessionId,
            OsString::from(session_id),
        ));
    }
    let claude_source = tmpdir.join("claude-source.env");
    if claude_source.is_file() {
        rows.push((
            ChildEnvironment::LarchClaudeSourceFile,
            claude_source.into_os_string(),
        ));
    }
    publish_session_environment(rows.clone());
    *STEP2_CHILD_ENVIRONMENT
        .lock()
        .unwrap_or_else(PoisonError::into_inner) = rows;
}

/// Run one already-owned `larch` verb with this dispatch's session identity.
fn state_larch(state: &DispatchState, argv: &[OsString]) -> Result<ProcessOutput, String> {
    let rows = STEP2_CHILD_ENVIRONMENT
        .lock()
        .unwrap_or_else(PoisonError::into_inner)
        .clone();
    run_verified_larch_env_in(&state.repo_root, &state.plugin_root, argv, &rows)
}

// ---------------------------------------------------------------------------
// step2-dispatch orchestrator
// ---------------------------------------------------------------------------

/// Build the dispatch workspace layout for one coder.
fn dispatch_state(
    request: &Step2Request,
    repo_root: &Path,
    plugin_root: &Path,
) -> Result<DispatchState, String> {
    let tool = request.coder.clone();
    let tmpdir = &request.tmpdir;
    // Codex writes its manifest under a per-tool directory so a Claude fallback
    // in the same tmpdir cannot read the abandoned Codex attempt as its own.
    let artifact_dir = if tool == "codex" {
        let out_dir = tmpdir.join("codex-step2-out");
        fs::create_dir_all(&out_dir).map_err(|error| error.to_string())?;
        out_dir
    } else {
        tmpdir.clone()
    };
    let manifest_path = artifact_dir.join("manifest.json");
    let qa_pending_path = artifact_dir.join("qa-pending.json");
    let transcript = artifact_dir.join(format!("{tool}-impl-transcript.txt"));
    let launch_scout = artifact_dir.join("scout-coder-manifest.json");
    Ok(DispatchState {
        repo_root: repo_root.to_path_buf(),
        tmpdir: tmpdir.clone(),
        plan_file: request.plan_file.clone(),
        feature_file: request.feature_file.clone(),
        coder: tool.clone(),
        cursor_present: if request.cursor_present.is_empty() {
            "false".to_owned()
        } else {
            request.cursor_present.clone()
        },
        cursor_binary_found: request.cursor_binary_found.clone(),
        codex_binary_found: request.codex_binary_found.clone(),
        answers_file: (!request.answers.is_empty()).then(|| PathBuf::from(&request.answers)),
        plugin_root: plugin_root.to_path_buf(),
        tool_tag: tool.clone(),
        manifest_path,
        manifest_raw_path: tmpdir.join("manifest-raw.json"),
        qa_pending_path,
        transcript_path: transcript,
        sidecar_log: tmpdir.join(format!("{tool}-impl.log")),
        scout_coder_manifest: tmpdir.join("scout-coder-manifest.json"),
        launch_scout_manifest: launch_scout,
        external_scout_marker: tmpdir.join("step2-external-scout-eligible.txt"),
        baseline_file: tmpdir.join("step2-baseline.txt"),
        prelaunch_porcelain: tmpdir.join("step2-prelaunch-porcelain.nul"),
        postlaunch_porcelain: tmpdir.join("step2-postlaunch-porcelain.nul"),
        prelaunch_digests: tmpdir.join("step2-prelaunch-content-digests.txt"),
        prelaunch_index_flag: tmpdir.join("step2-prelaunch-index.env"),
        recovery_paths_file: tmpdir.join("step2-recovery-paths.nul"),
        resume_count_file: tmpdir.join(format!("{tool}-resume-count.txt")),
        completion_retry_state_file: tmpdir.join("step2-completion-retry-state.env"),
        completion_retry_feedback_file: tmpdir.join("step2-completion-retry.md"),
        spawn_branch_file: tmpdir.join("step2-spawn-branch.txt"),
        spawn_coder_file: tmpdir.join("step2-spawn-coder.txt"),
        runtime_failure_token: format!("{tool}-runtime-failure"),
        bailed_no_reason_token: format!("{tool}-bailed-no-reason"),
        requires_head_unchanged: tool == "cursor",
        nonzero_exit_warn_token: if tool == "codex" {
            "WARN_CODEX_NONZERO_EXIT".to_owned()
        } else {
            String::new()
        },
        difficulty: request.difficulty.clone(),
        baseline_sha: String::new(),
        spawn_branch: String::new(),
        scout_status: String::new(),
    })
}

/// Emit the `bailed` contract for one refusal reason.
fn emit_bailed(state: &DispatchState, reason: &str, manifest: bool) -> ExitCode {
    emit_kv("STATUS", "bailed");
    emit_kv("REASON", reason);
    emit_kv("TOOL", &state.tool_tag);
    if manifest {
        emit_kv("MANIFEST", &state.manifest_path.display().to_string());
    }
    emit_dispatch_artifact_rows(state);
    emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden");
    ExitCode::SUCCESS
}

/// Emit the transcript and sidecar rows, each only when it holds output.
fn emit_dispatch_artifact_rows(state: &DispatchState) {
    if nonempty_file(&state.transcript_path) {
        emit_kv("TRANSCRIPT", &state.transcript_path.display().to_string());
    }
    if nonempty_file(&state.sidecar_log) {
        emit_kv("SIDECAR_LOG", &state.sidecar_log.display().to_string());
    }
}

fn nonempty_file(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

/// Emit the Claude-fallback contract and reset the external dispatch state.
fn emit_claude_fallback(tmpdir: &Path, repo_root: Option<&Path>, reason: &str, tool: &str) {
    ensure_step2_baseline(tmpdir, repo_root);
    clear_external_scout_state(tmpdir);
    emit_kv("STATUS", "claude_fallback");
    if !reason.is_empty() {
        emit_kv("REASON", reason);
    }
    if !tool.is_empty() {
        emit_kv("TOOL", tool);
    }
    emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "allowed");
}

fn clear_external_scout_state(tmpdir: &Path) {
    for path in clear_external_scout_paths(tmpdir) {
        let _removed = fs::remove_file(path);
    }
}

/// Record the commit the external coder started from, once.
fn ensure_step2_baseline(tmpdir: &Path, repo_root: Option<&Path>) {
    let baseline = tmpdir.join("step2-baseline.txt");
    if baseline.is_file() {
        return;
    }
    let sha = repo_root.map_or_else(
        || {
            env::current_dir()
                .ok()
                .map_or_else(String::new, |cwd| head_sha(&cwd))
        },
        head_sha,
    );
    if !sha.is_empty() {
        let _written = write_atomic(&baseline, &format!("{sha}\n"));
    }
}

/// Run the whole Step 2 orchestration for one validated request.
#[allow(clippy::too_many_lines)]
fn run_step2_dispatch(request: &Step2Request) -> ExitCode {
    let tmpdir = &request.tmpdir;
    let repo_root = discover_repo_root();
    if let Some(root) = repo_root.as_deref() {
        let _written = write_atomic(
            &tmpdir.join("repo-root.txt"),
            &format!("{}\n", root.display()),
        );
    }
    if request.coder == "claude" {
        emit_claude_fallback(tmpdir, repo_root.as_deref(), "", "");
        return ExitCode::SUCCESS;
    }
    let session_env = tmpdir.join("session-env.sh");
    let cursor_binary_found = if request.cursor_binary_found.is_empty() {
        binary_available(&session_env, "CURSOR_BINARY_FOUND", "cursor")
    } else {
        request.cursor_binary_found.clone()
    };
    let codex_binary_found = if request.codex_binary_found.is_empty() {
        binary_available(&session_env, "CODEX_BINARY_FOUND", "codex")
    } else {
        request.codex_binary_found.clone()
    };
    let missing_binary = (request.coder == "cursor" && cursor_binary_found != "true")
        || (request.coder == "codex" && codex_binary_found != "true");
    if missing_binary {
        emit_claude_fallback(tmpdir, repo_root.as_deref(), "", "");
        return ExitCode::SUCCESS;
    }
    let plugin_root = env::var_os("CLAUDE_PLUGIN_ROOT")
        .filter(|value| !value.is_empty())
        .or_else(|| env::var_os("LARCH_CLAUDE_PLUGIN_ROOT").filter(|value| !value.is_empty()))
        .map(PathBuf::from)
        .or_else(|| resolve_plugin_root().ok())
        .unwrap_or_else(|| PathBuf::from("."));
    let plugin_root = plugin_root.canonicalize().unwrap_or(plugin_root);
    let Some(repo_root) = repo_root else {
        eprintln!(
            "implement step2-dispatch: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)"
        );
        return ExitCode::from(2);
    };
    let mut resolved = Step2Request {
        codex_binary_found,
        cursor_binary_found,
        ..clone_request(request)
    };
    let mut state = match dispatch_state(&resolved, &repo_root, &plugin_root) {
        Ok(state) => state,
        Err(detail) => {
            eprintln!("implement step2-dispatch: {detail}");
            return ExitCode::from(2);
        }
    };
    let Ok(retry_state) = read_completion_retry_state(&state) else {
        return emit_bailed(&state, COMPLETION_RETRY_STATE_INVALID, false);
    };
    if resolved.completion_retry {
        let Some(retry) = retry_state.as_ref() else {
            return emit_bailed(&state, COMPLETION_RETRY_STATE_INVALID, false);
        };
        if !state.completion_retry_feedback_file.is_file() {
            return emit_bailed(&state, COMPLETION_RETRY_STATE_INVALID, false);
        }
        match compute_plan_coverage(&state, false) {
            Ok(coverage) if coverage.fingerprint == retry.fingerprint => {}
            Ok(_stale) => return emit_bailed(&state, COMPLETION_RETRY_STATE_STALE, false),
            Err(_failed) => return emit_bailed(&state, COMPLETION_RETRY_STATE_STALE, false),
        }
    }
    append_architectural_knowledge_warnings(&state);
    let prompt_path = external_implementer_prompt_path(&plugin_root, &state.tool_tag);
    if !prompt_path.is_file() {
        eprintln!(
            "implement step2-dispatch: external implementer prompt missing: {}",
            prompt_path.display()
        );
        return ExitCode::from(2);
    }
    if let Some(bail) = adopt_spawn_identity(&mut state) {
        return emit_bailed(&state, &bail, false);
    }
    match resume_count(&state) {
        Err(bail) => return emit_bailed(&state, &bail, false),
        Ok(count) if count > RESUME_CAP => {
            return emit_bailed(&state, "qa-loop-exceeded", false);
        }
        Ok(_within_cap) => {}
    }
    if !resolved.completion_retry && prior_attempt_unfinalized(&state) {
        return emit_bailed(&state, PRIOR_ATTEMPT_REASON, false);
    }
    for path in [
        &state.manifest_path,
        &state.manifest_raw_path,
        &state.qa_pending_path,
        &state.transcript_path,
        &state.sidecar_log,
        &state.launch_scout_manifest,
    ] {
        let _removed = fs::remove_file(path);
    }
    clear_external_scout_state(tmpdir);
    if let Some(bail) = migration_governance_gate(&state) {
        return emit_bailed(&state, &bail, false);
    }
    write_prelaunch_baseline(&state);
    dispatch_launch_and_route(&mut resolved, &mut state)
}

fn clone_request(request: &Step2Request) -> Step2Request {
    Step2Request {
        tmpdir: request.tmpdir.clone(),
        plan_file: request.plan_file.clone(),
        feature_file: request.feature_file.clone(),
        coder: request.coder.clone(),
        cursor_present: request.cursor_present.clone(),
        codex_binary_found: request.codex_binary_found.clone(),
        cursor_binary_found: request.cursor_binary_found.clone(),
        answers: request.answers.clone(),
        completion_retry: request.completion_retry,
        difficulty: request.difficulty.clone(),
    }
}

fn external_implementer_prompt_path(plugin_root: &Path, tool_tag: &str) -> PathBuf {
    plugin_root
        .join("skills")
        .join("implement")
        .join("prompts")
        .join(format!("{tool_tag}-implementer.md"))
}

/// Adopt or verify the coder, baseline commit, and branch this tmpdir belongs to.
///
/// Returns a bail reason when the session is being reused by a different coder,
/// or when an issue-anchored run is sitting on a branch it must not commit to.
fn adopt_spawn_identity(state: &mut DispatchState) -> Option<String> {
    if state.spawn_coder_file.is_file() {
        let recorded = fs::read_to_string(&state.spawn_coder_file).unwrap_or_default();
        if recorded.trim() != state.coder {
            return Some("coder-mismatch-tmpdir-reuse".to_owned());
        }
    } else {
        let _written = write_atomic(&state.spawn_coder_file, &format!("{}\n", state.coder));
    }
    if !state.baseline_file.is_file() {
        let _written = write_atomic(
            &state.baseline_file,
            &format!("{}\n", head_sha(&state.repo_root)),
        );
    }
    state.baseline_sha.clear();
    state
        .baseline_sha
        .push_str(fs::read_to_string(&state.baseline_file).unwrap_or_default().trim());
    if !state.spawn_branch_file.is_file() {
        let _written = write_atomic(
            &state.spawn_branch_file,
            &format!("{}\n", symbolic_branch(&state.repo_root)),
        );
    }
    state.spawn_branch.clear();
    state.spawn_branch.push_str(
        fs::read_to_string(&state.spawn_branch_file)
            .unwrap_or_default()
            .trim(),
    );
    let session_env = state.tmpdir.join("session-env.sh");
    let parent_issue = state.tmpdir.join("parent-issue.md");
    let issue_from_parent = if parent_issue.is_file() {
        read_kv_first(&parent_issue, "ISSUE_NUMBER")
    } else {
        String::new()
    };
    let forked_target = if session_env.is_file() {
        let value = read_kv_first(&session_env, "FORKED_TARGET");
        if value.is_empty() { "false".to_owned() } else { value }
    } else {
        "false".to_owned()
    };
    let issue_anchored = !issue_from_parent.is_empty() || session_env.is_file();
    if forked_target != "true" && issue_anchored {
        if state.spawn_branch.is_empty() || state.spawn_branch == "HEAD" {
            return Some("detached-head-prohibited".to_owned());
        }
        if state.spawn_branch == "main" || state.spawn_branch == "master" {
            return Some("main-branch-prohibited".to_owned());
        }
    }
    None
}

/// The needs-QA resume count, charging this run's answers file when present.
fn resume_count(state: &DispatchState) -> Result<u32, String> {
    let mut count = 0_u32;
    if state.resume_count_file.is_file() {
        let raw = fs::read_to_string(&state.resume_count_file).unwrap_or_default();
        let raw = raw.trim();
        match raw.parse::<u32>() {
            Ok(parsed) if raw.bytes().all(|byte| byte.is_ascii_digit()) => count = parsed,
            _ => return Err("manifest-schema-invalid".to_owned()),
        }
    }
    if let Some(answers) = state.answers_file.clone() {
        if !answers.is_file() {
            eprintln!(
                "implement step2-dispatch: --answers given but path does not exist: {}",
                answers.display()
            );
            return Err("qa-answers-missing".to_owned());
        }
        count += 1;
        let _written = write_atomic(&state.resume_count_file, &format!("{count}\n"));
    }
    Ok(count)
}

/// Detect stranded edits from an interrupted prior external dispatch.
///
/// A normal Q/A redispatch shares the original prelaunch snapshot, so only a
/// content delta against that snapshot is unsafe: a second launch must not
/// claim another implementer's changes as pre-existing work.
fn prior_attempt_unfinalized(state: &DispatchState) -> bool {
    if state.answers_file.is_some()
        || !state.prelaunch_porcelain.is_file()
        || !state.prelaunch_digests.is_file()
    {
        return false;
    }
    if capture_postlaunch_porcelain(&state.repo_root, &state.tmpdir) != 0 {
        return true;
    }
    attribute_recovery_paths(state).unwrap_or(true)
}

/// Attribute the current working-tree delta against the prelaunch snapshot.
///
/// Writes the attributable paths to this dispatch's recovery-paths file and
/// reports whether every observed edit was attributable.
fn attribute_recovery_paths(state: &DispatchState) -> std::io::Result<bool> {
    larch_core::compute_recovery_paths(
        &state.repo_root,
        &state.tmpdir,
        &larch_core::RecoveryPorcelainInputs {
            prelaunch_porcelain: state.prelaunch_porcelain.clone(),
            postlaunch_porcelain: state.postlaunch_porcelain.clone(),
            prelaunch_digests: state.prelaunch_digests.clone(),
        },
        &state.recovery_paths_file,
    )
}

/// Snapshot the pre-launch working tree so a later recovery can attribute edits.
fn write_prelaunch_baseline(state: &DispatchState) {
    if state.answers_file.is_some() || state.prelaunch_porcelain.exists() {
        return;
    }
    if capture_prelaunch_porcelain(&state.repo_root, &state.tmpdir) != 0 {
        eprintln!("implement step2-dispatch: prelaunch porcelain capture failed");
    }
}

/// Record every unusable architectural knowledge file as a run warning.
fn append_architectural_knowledge_warnings(state: &DispatchState) {
    for kind in [ArchitecturalKind::Invariants, ArchitecturalKind::Guidelines] {
        let knowledge = read_architectural_knowledge(&state.repo_root, kind);
        if knowledge.status == ArchitecturalStatus::Invalid && !knowledge.warning.is_empty() {
            append_warning(
                state,
                &format!(
                    "Step 2 architectural knowledge omitted: {}",
                    knowledge.warning
                ),
            );
        }
    }
}

/// Whether this run must acknowledge architectural knowledge.
///
/// Prefers the launcher's own snapshot so both sides of one run agree even when
/// the repository changes mid-dispatch.
fn architectural_knowledge_required(state: &DispatchState) -> bool {
    let snapshot = state.tmpdir.join(ARCH_KNOWLEDGE_SNAPSHOT);
    if snapshot.is_file() {
        match read_kv_first(&snapshot, "ARCHITECTURAL_KNOWLEDGE_REQUIRED").as_str() {
            "true" => return true,
            "false" => return false,
            _other => {}
        }
    }
    [ArchitecturalKind::Invariants, ArchitecturalKind::Guidelines]
        .into_iter()
        .any(|kind| {
            read_architectural_knowledge(&state.repo_root, kind).status
                == ArchitecturalStatus::Present
        })
}

/// Append one operator warning to this run's execution issues.
fn append_warning(state: &DispatchState, entry: &str) {
    let bullet = larch_core::implement::warning_bullet(entry);
    let argv: Vec<OsString> = vec![
        "run-log".into(),
        "append-entry".into(),
        "--log".into(),
        state.tmpdir.join("execution-issues.md").into_os_string(),
        "--category".into(),
        "Warnings".into(),
        "--entry".into(),
        bullet.into(),
    ];
    let _forwarded = state_larch(state, &argv);
}

/// Consume the still-Python migration-governance verdict for this run's issue.
fn migration_governance_gate(state: &DispatchState) -> Option<String> {
    let session_env = state.tmpdir.join("session-env.sh");
    let parent_issue = state.tmpdir.join("parent-issue.md");
    let mut issue = if session_env.is_file() {
        read_kv_first(&session_env, "ISSUE_NUMBER")
    } else {
        String::new()
    };
    if issue.is_empty() && parent_issue.is_file() {
        issue = read_kv_first(&parent_issue, "ISSUE_NUMBER");
    }
    let repo_slug = if session_env.is_file() {
        read_kv_first(&session_env, "REPO")
    } else {
        String::new()
    };
    if issue.is_empty() || repo_slug.is_empty() {
        return None;
    }
    let forked_target = read_kv_first(&session_env, "FORKED_TARGET");
    let base_remote = if forked_target == "true" {
        "upstream"
    } else {
        "origin"
    };
    let Ok(base_target_sha) = crate::implement_bootstrap_continuation::resolve_revision_sha(
        &state.repo_root,
        &format!("{base_remote}/main"),
    ) else {
        eprintln!(
            "implement step2-dispatch: migration governance read failed: cannot resolve {base_remote}/main"
        );
        return Some("migration-governance-read-failed".to_owned());
    };
    let Some(body) = read_issue_body(&issue, &repo_slug) else {
        eprintln!(
            "implement step2-dispatch: migration governance read failed: issue-body-read-failed"
        );
        return Some("migration-governance-read-failed".to_owned());
    };
    let body_file = state.tmpdir.join("step2-governance-body.md");
    if write_atomic(&body_file, &body).is_err() {
        eprintln!(
            "implement step2-dispatch: migration governance read failed: cannot write governance body"
        );
        return Some("migration-governance-read-failed".to_owned());
    }
    let argv = governance_gate_argv(
        &issue,
        &repo_slug,
        &body_file,
        &state.repo_root,
        &base_target_sha,
    );
    let Ok(output) = delegate_python(argv) else {
        eprintln!(
            "implement step2-dispatch: migration governance read failed: cannot start issue governance-gate"
        );
        return Some("migration-governance-read-failed".to_owned());
    };
    let envelope = String::from_utf8_lossy(output.stdout()).into_owned();
    // Route on the published verdict, not on the exit code: a nonzero exit is
    // also how the gate reports a *refusal*, which is a different outcome from
    // a failed read.
    match kv_value(&envelope, "GOVERNANCE_OK").as_str() {
        "true" => None,
        "false" => {
            let reasons = kv_value(
                &String::from_utf8_lossy(output.stderr()),
                "GOVERNANCE_REASONS",
            );
            let tokens = if reasons.is_empty() {
                "unknown".to_owned()
            } else {
                reasons
            };
            eprintln!(
                "**❌ implement step2-dispatch: migration governance blocked: `{tokens}`.**"
            );
            Some("migration-governance-stale".to_owned())
        }
        _absent => {
            eprintln!(
                "implement step2-dispatch: migration governance read failed: no verdict envelope"
            );
            Some("migration-governance-read-failed".to_owned())
        }
    }
}

/// Read one issue body through the typed GitHub adapter.
fn read_issue_body(issue: &str, repo_slug: &str) -> Option<String> {
    let number = issue.parse::<u64>().ok()?;
    let (owner, name) = repo_slug.split_once('/')?;
    let reference = GitHubRepositoryRef::new(owner, name).ok()?;
    crate::github_service::with_github_service(async |service, cancellation| {
        service
            .issue(&reference, number, cancellation)
            .await
            .map(|issue| issue.body)
            .map_err(|error| error.to_string())
    })
    .ok()
}

include!("implement_step2_commands_route.rs");
