//! `push rebase` and `push checkpoint-probe`, migrated from `larch.git.push`
//! and `larch.git.rebase`. The Rust runtime is the sole rebase orchestrator for
//! these two commands: it composes the #7758 main-sync, #7757 phantom-probe,
//! #7759 conflict controls, and #7760 push behavior with no Python bridge.

use std::{
    env,
    fmt::Write as _,
    io::{self, Write as _},
    path::PathBuf,
    process::ExitCode,
    thread,
    time::Duration,
};

use larch_adapters::{
    FetchRequest, ForceWithLease, GitCli, GitCliError, GitCliPolicy, GitCliResult, GitPath, GitRef,
    GitRefspec, GitRemote, GixRepository, LsRemoteRequest, PushRequest, RebaseRequest, RmRequest,
    TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ConfigKey, ObjectId, RepositoryRead, RepositoryStatus, Revision, StatusOptions, emit_kv,
};

use crate::git_commands::is_transient_net;
use crate::push_network::current_branch;

const DEFAULT_REMOTE: &str = "origin";
const FORKED_REMOTE: &str = "upstream";
const DEFAULT_REF: &str = "main";
const REBASE_FAILED_EXIT: i32 = 3;
const CHECKPOINT_ITERATION_CAP: usize = 50;
const PUSH_MAX_ATTEMPTS: u32 = 3;
const TRANSIENT_ATTEMPTS: u32 = 3;
const TRIVIAL_CONFLICT_PREFIX: &str = "larch-logs/";

// ---------------------------------------------------------------------------
// Command entrypoints
// ---------------------------------------------------------------------------

/// `push rebase`: parity port of `larch.git.push.rebase_main`.
pub fn rebase(args: &[String]) -> ExitCode {
    let Ok(options) = parse_rebase_args(args) else {
        return ExitCode::from(3);
    };
    let git = match Git::new() {
        Ok(git) => git,
        Err(message) => {
            emit_kv("REBASE_ERROR", &single_line(&message));
            return ExitCode::from(3);
        }
    };
    let result = rebase_push(&git, &options);
    if result.skipped_already_pushed {
        emit_kv("SKIPPED_ALREADY_PUSHED", "true");
    }
    if result.skipped_already_fresh {
        emit_kv("SKIPPED_ALREADY_FRESH", "true");
    }
    if !result.conflict_files.is_empty() {
        emit_kv("CONFLICT_FILES", &single_line(&result.conflict_files));
    }
    if !result.rebase_error.is_empty() {
        emit_kv("REBASE_ERROR", &single_line(&result.rebase_error));
    }
    if !result.push_error.is_empty() {
        emit_kv("PUSH_ERROR", &single_line(&result.push_error));
    }
    ExitCode::from(u8::try_from(result.exit_code).unwrap_or(1))
}

/// `push checkpoint-probe`: parity port of `larch.git.push.checkpoint_probe_main`.
pub fn checkpoint_probe(args: &[String]) -> ExitCode {
    let Ok(parsed) = parse_checkpoint_args(args) else {
        return ExitCode::from(2);
    };
    let _ = writeln!(
        io::stderr(),
        "→ rebase-probe: {} {}",
        parsed.step_prefix,
        parsed.short_name
    );
    let base_remote = parsed.base_remote.clone().unwrap_or_else(|| {
        if parsed.forked_target {
            FORKED_REMOTE.to_owned()
        } else {
            DEFAULT_REMOTE.to_owned()
        }
    });
    let base_ref = parsed
        .base_ref
        .clone()
        .unwrap_or_else(|| DEFAULT_REF.to_owned());

    let output = match Git::new() {
        Ok(git) => checkpoint_probe_run(&git, &parsed.step_prefix, &base_remote, &base_ref),
        Err(message) => checkpoint_output(&RebasePushResult::error(
            REBASE_FAILED_EXIT,
            single_line(&message),
        )),
    };
    print!("{}", render_checkpoint(&output));
    ExitCode::from(u8::try_from(output.exit_code).unwrap_or(1))
}

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

// The four bools mirror the four `push rebase` flag switches one-for-one.
#[allow(clippy::struct_excessive_bools)]
struct RebaseOptions {
    continue_mode: bool,
    no_push: bool,
    skip_if_pushed: bool,
    keep_on_conflict: bool,
    base_remote: String,
    base_ref: String,
}

fn parse_rebase_args(args: &[String]) -> Result<RebaseOptions, ()> {
    let mut options = RebaseOptions {
        continue_mode: false,
        no_push: false,
        skip_if_pushed: false,
        keep_on_conflict: false,
        base_remote: DEFAULT_REMOTE.to_owned(),
        base_ref: DEFAULT_REF.to_owned(),
    };
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--continue" => options.continue_mode = true,
            "--no-push" => options.no_push = true,
            "--skip-if-pushed" => options.skip_if_pushed = true,
            "--keep-on-conflict" => options.keep_on_conflict = true,
            "--base-remote" => {
                options
                    .base_remote
                    .clone_from(args.get(index + 1).ok_or(())?);
                index += 2;
                continue;
            }
            "--base-ref" => {
                options.base_ref.clone_from(args.get(index + 1).ok_or(())?);
                index += 2;
                continue;
            }
            _ => return Err(()),
        }
        index += 1;
    }
    Ok(options)
}

struct CheckpointArgs {
    step_prefix: String,
    short_name: String,
    base_remote: Option<String>,
    base_ref: Option<String>,
    forked_target: bool,
}

fn parse_checkpoint_args(args: &[String]) -> Result<CheckpointArgs, ()> {
    let mut positionals: Vec<String> = Vec::new();
    let mut base_remote = None;
    let mut base_ref = None;
    let mut forked_target = None;
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--base-remote" => {
                base_remote = Some(args.get(index + 1).ok_or(())?.clone());
                index += 2;
                continue;
            }
            "--base-ref" => {
                base_ref = Some(args.get(index + 1).ok_or(())?.clone());
                index += 2;
                continue;
            }
            "--forked-target" => {
                let value = args.get(index + 1).ok_or(())?;
                forked_target = Some(match value.as_str() {
                    "true" => true,
                    "false" => false,
                    _ => return Err(()),
                });
                index += 2;
                continue;
            }
            flag if flag.starts_with("--") => return Err(()),
            _ => positionals.push(args[index].clone()),
        }
        index += 1;
    }
    if positionals.len() != 2 {
        return Err(());
    }
    Ok(CheckpointArgs {
        step_prefix: positionals[0].clone(),
        short_name: positionals[1].clone(),
        base_remote,
        base_ref,
        forked_target: forked_target.unwrap_or(false),
    })
}

// ---------------------------------------------------------------------------
// rebase_push: parity port of larch.git.rebase.rebase_push
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, Default)]
struct RebasePushResult {
    exit_code: i32,
    skipped_already_pushed: bool,
    skipped_already_fresh: bool,
    conflict_files: String,
    rebase_error: String,
    push_error: String,
}

impl RebasePushResult {
    fn code(exit_code: i32) -> Self {
        Self {
            exit_code,
            ..Self::default()
        }
    }

    fn error(exit_code: i32, rebase_error: impl Into<String>) -> Self {
        Self {
            exit_code,
            rebase_error: rebase_error.into(),
            ..Self::default()
        }
    }

    fn conflict(conflict_files: impl Into<String>) -> Self {
        Self {
            exit_code: 1,
            conflict_files: conflict_files.into(),
            ..Self::default()
        }
    }
}

// One cohesive state machine mirroring `larch.git.rebase.rebase_push`; splitting
// it would fragment the flag-precedence contract this parity port must preserve.
#[allow(clippy::too_many_lines)]
fn rebase_push(git: &Git, options: &RebaseOptions) -> RebasePushResult {
    if let Some(message) = validate_base_remote_ref(&options.base_remote, &options.base_ref) {
        return RebasePushResult::error(3, message);
    }
    if options.skip_if_pushed && !options.no_push {
        return RebasePushResult::error(3, "--skip-if-pushed is only valid with --no-push");
    }
    if options.skip_if_pushed && options.continue_mode {
        return RebasePushResult::error(3, "--skip-if-pushed cannot be used with --continue");
    }
    if options.keep_on_conflict && !options.no_push {
        return RebasePushResult::error(3, "--keep-on-conflict is only valid with --no-push");
    }
    if options.continue_mode && options.no_push && !options.keep_on_conflict {
        return RebasePushResult::error(
            3,
            "--continue --no-push requires --keep-on-conflict to safely handle nested conflicts",
        );
    }

    if options.skip_if_pushed
        && let Some(branch) = current_branch()
    {
        let probe = transient_retry(|| git.ls_remote_ref(DEFAULT_REMOTE, &branch));
        if probe.ok && !probe.stdout.trim().is_empty() {
            return RebasePushResult {
                exit_code: 0,
                skipped_already_pushed: true,
                ..RebasePushResult::default()
            };
        }
    }

    let base_target = format!("{}/{}", options.base_remote, options.base_ref);
    let rebase_outcome = if options.continue_mode {
        if !rebase_in_progress() {
            return RebasePushResult::error(3, "--continue called but no rebase is in progress");
        }
        git.rebase_continue()
    } else {
        if current_branch().is_none() {
            return RebasePushResult::error(3, "Not on a branch (detached HEAD)");
        }
        let fetch = transient_retry(|| git.fetch(&options.base_remote, &options.base_ref));
        if options.no_push && !fetch.ok {
            return RebasePushResult::error(
                3,
                format!(
                    "git fetch {} {} failed (network/auth issue)",
                    options.base_remote, options.base_ref
                ),
            );
        }
        if options.no_push && is_ancestor(&base_target, "HEAD") {
            return RebasePushResult {
                exit_code: 0,
                skipped_already_fresh: true,
                ..RebasePushResult::default()
            };
        }
        git.rebase_start(&base_target)
    };

    if !rebase_outcome.ok {
        let conflicts = unmerged_paths().join(",");
        if !conflicts.is_empty() {
            if options.no_push && !options.keep_on_conflict {
                git.rebase_abort();
            }
            return RebasePushResult::conflict(conflicts);
        }
        let detail = replace_newlines(&format!(
            "{}{}",
            rebase_outcome.stdout, rebase_outcome.stderr
        ));
        if !options.continue_mode {
            git.rebase_abort();
        }
        return RebasePushResult::error(3, detail);
    }

    if options.no_push {
        return RebasePushResult::code(0);
    }

    let Some(branch) = current_branch() else {
        return RebasePushResult {
            exit_code: 2,
            push_error: "Not on a branch (detached HEAD) before push".to_owned(),
            ..RebasePushResult::default()
        };
    };
    let push_remote = resolve_branch_push_remote(&branch);
    let _ = transient_retry(|| git.fetch(&push_remote, &branch));
    let mut expected_oid = resolve_hex(&format!("{push_remote}/{branch}")).unwrap_or_default();
    if expected_oid.is_empty() {
        let probe = transient_retry(|| git.ls_remote_ref(&push_remote, &branch));
        if probe.ok
            && let Some(first) = probe.stdout.split_whitespace().next()
        {
            first.clone_into(&mut expected_oid);
        }
    }
    let (pushed, push_error) =
        rebase_push_force_with_lease(git, &push_remote, &branch, &expected_oid);
    if pushed {
        return RebasePushResult::code(0);
    }
    RebasePushResult {
        exit_code: 2,
        push_error,
        ..RebasePushResult::default()
    }
}

/// Three-attempt force-with-lease loop, parity with `_rebase_push_force_with_lease`.
fn rebase_push_force_with_lease(
    git: &Git,
    push_remote: &str,
    branch: &str,
    expected_oid: &str,
) -> (bool, String) {
    let mut last_output = String::new();
    for attempt in 1..=PUSH_MAX_ATTEMPTS {
        if current_branch().is_none() {
            return (
                false,
                format!("Not on a branch (detached HEAD) before push attempt {attempt}"),
            );
        }
        let push = transient_retry(|| git.force_push_with_lease(push_remote, branch, expected_oid));
        if push.ok {
            return (true, String::new());
        }
        last_output = replace_newlines(&format!("{}{}", push.stdout, push.stderr));
        let _ = transient_retry(|| git.fetch(push_remote, branch));
        let local = resolve_hex("HEAD");
        let remote = resolve_hex(&format!("{push_remote}/{branch}"));
        if let (Some(local), Some(remote)) = (local, remote)
            && local == remote
        {
            return (true, String::new());
        }
        if attempt < PUSH_MAX_ATTEMPTS {
            thread::sleep(Duration::from_secs(1u64 << (attempt - 1)));
        }
    }
    (false, last_output)
}

// ---------------------------------------------------------------------------
// checkpoint_probe: parity port of larch.git.push.checkpoint_probe
// ---------------------------------------------------------------------------

struct CheckpointOutput {
    exit_code: i32,
    routing: Vec<(String, String)>,
    advisory: Vec<String>,
}

fn checkpoint_probe_run(
    git: &Git,
    step_prefix: &str,
    base_remote: &str,
    base_ref: &str,
) -> CheckpointOutput {
    let result = checkpoint_rebase_result(git, base_remote, base_ref);
    let mut output = checkpoint_output(&result);
    if output.exit_code == 0 {
        output.advisory =
            crate::phantom_probe_lines(&format!("{step_prefix}-post-rebase"), None, false);
    }
    output
}

/// Build the routing rows, mirroring `checkpoint_probe`'s ordered dict.
fn checkpoint_output(result: &RebasePushResult) -> CheckpointOutput {
    let mut routing: Vec<(String, String)> =
        vec![("REBASE_RC".to_owned(), result.exit_code.to_string())];
    if result.skipped_already_pushed {
        routing.push(("SKIPPED_ALREADY_PUSHED".to_owned(), "true".to_owned()));
    }
    if result.skipped_already_fresh {
        routing.push(("SKIPPED_ALREADY_FRESH".to_owned(), "true".to_owned()));
    }
    let (outcome, route) = match result.exit_code {
        0 => {
            let outcome = if result.skipped_already_pushed || result.skipped_already_fresh {
                "skipped"
            } else {
                "ok"
            };
            (outcome, "continue")
        }
        1 => ("conflict", "conflict"),
        _ => ("failed", "bail"),
    };
    routing.push(("REBASE_OUTCOME".to_owned(), outcome.to_owned()));
    routing.push(("ROUTE".to_owned(), route.to_owned()));
    if result.exit_code == 1 || !result.conflict_files.is_empty() {
        routing.push(("CONFLICT_FILES".to_owned(), conflict_files_csv(result)));
    }
    if !result.rebase_error.is_empty() {
        routing.push((
            "REBASE_ERROR".to_owned(),
            collapse_whitespace(&result.rebase_error),
        ));
    } else if result.exit_code != 0 && result.exit_code != 1 {
        let error = if result.exit_code == REBASE_FAILED_EXIT {
            "rebase-failed".to_owned()
        } else {
            format!("unexpected-rc-{}", result.exit_code)
        };
        routing.push(("REBASE_ERROR".to_owned(), error));
    }
    routing.push((
        "CHECKPOINT_NEXT".to_owned(),
        if result.exit_code == 0 {
            "continue".to_owned()
        } else {
            "load-routing".to_owned()
        },
    ));
    CheckpointOutput {
        exit_code: result.exit_code,
        routing,
        advisory: Vec::new(),
    }
}

fn render_checkpoint(output: &CheckpointOutput) -> String {
    let mut rendered = String::new();
    for (key, value) in &output.routing {
        let _ = writeln!(rendered, "{key}={value}");
    }
    for line in &output.advisory {
        let _ = writeln!(rendered, "{line}");
    }
    rendered
}

/// Parity port of `_checkpoint_rebase_result`: rebase with the trivial-conflict
/// (larch-logs/) auto-resolution pre-pass and empty-continue recovery.
fn checkpoint_rebase_result(git: &Git, base_remote: &str, base_ref: &str) -> RebasePushResult {
    let options = RebaseOptions {
        continue_mode: false,
        no_push: true,
        skip_if_pushed: true,
        keep_on_conflict: true,
        base_remote: base_remote.to_owned(),
        base_ref: base_ref.to_owned(),
    };
    let mut result = rebase_push(git, &options);
    if result.exit_code != 1 {
        return result;
    }

    for _ in 0..CHECKPOINT_ITERATION_CAP {
        let conflict_csv = conflict_files_csv(&result);
        if conflict_csv.is_empty() {
            return RebasePushResult::conflict("");
        }
        let (trivial, nontrivial): (Vec<String>, Vec<String>) = split_conflict_csv(&conflict_csv)
            .into_iter()
            .partition(|path| is_trivial_conflict_file(path));
        if trivial.is_empty() {
            return RebasePushResult::conflict(conflict_csv);
        }
        for path in &trivial {
            if !resolve_trivial_conflict_file(git, path) {
                return RebasePushResult::conflict(current_unmerged_conflict_files());
            }
        }
        if !nontrivial.is_empty() {
            let current = current_unmerged_conflict_files();
            let files = if current.is_empty() {
                nontrivial.join(",")
            } else {
                current
            };
            return RebasePushResult::conflict(files);
        }
        result = continue_checkpoint_rebase(git);
        if result.exit_code == REBASE_FAILED_EXIT {
            match handle_empty_continue_rc3(git, &result) {
                None => return result,
                Some(handled) => result = handled,
            }
        }
        if result.exit_code != 1 {
            return result;
        }
    }
    let _ = writeln!(
        io::stderr(),
        "WARN rebase-probe: trivial conflict pre-pass hit iteration cap; surfacing current conflicts"
    );
    RebasePushResult::conflict(current_unmerged_conflict_files())
}

fn continue_checkpoint_rebase(git: &Git) -> RebasePushResult {
    rebase_push(
        git,
        &RebaseOptions {
            continue_mode: true,
            no_push: true,
            skip_if_pushed: false,
            keep_on_conflict: true,
            base_remote: DEFAULT_REMOTE.to_owned(),
            base_ref: DEFAULT_REF.to_owned(),
        },
    )
}

fn handle_empty_continue_rc3(git: &Git, initial: &RebasePushResult) -> Option<RebasePushResult> {
    let mut result = initial.clone();
    loop {
        let unmerged = current_unmerged_conflict_files();
        if !unmerged.is_empty() {
            return Some(RebasePushResult::conflict(unmerged));
        }
        if !is_empty_or_already_applied(&result.rebase_error) {
            return None;
        }
        if !git.rebase_skip().ok {
            let _ = writeln!(
                io::stderr(),
                "WARN rebase-probe: git rebase --skip failed after empty continue"
            );
            return None;
        }
        if !rebase_in_progress() {
            return Some(RebasePushResult::code(0));
        }
        result = continue_checkpoint_rebase(git);
        if result.exit_code != REBASE_FAILED_EXIT {
            return Some(result);
        }
    }
}

fn resolve_trivial_conflict_file(git: &Git, path: &str) -> bool {
    if !git.checkout_ours(path).ok {
        if !conflict_upstream_deleted(path) {
            warn_trivial(path);
            return false;
        }
        if !git.rm_path(path).ok {
            warn_trivial(path);
            return false;
        }
        return true;
    }
    if !git.add_path(path).ok {
        let _ = writeln!(
            io::stderr(),
            "WARN rebase-probe: failed to stage trivial conflict {path}"
        );
        return false;
    }
    true
}

fn warn_trivial(path: &str) {
    let _ = writeln!(
        io::stderr(),
        "WARN rebase-probe: failed to resolve trivial conflict {path}"
    );
}

fn is_trivial_conflict_file(path: &str) -> bool {
    path.starts_with(TRIVIAL_CONFLICT_PREFIX)
}

fn split_conflict_csv(value: &str) -> Vec<String> {
    value
        .split(',')
        .filter(|item| !item.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn conflict_files_csv(result: &RebasePushResult) -> String {
    if !result.conflict_files.is_empty() {
        return result.conflict_files.clone();
    }
    current_unmerged_conflict_files()
}

fn current_unmerged_conflict_files() -> String {
    unmerged_paths().join(",")
}

/// Render conflict paths with the legacy lossy ordering and deduplication contract.
pub fn sorted_lossy_unmerged_paths(status: &RepositoryStatus) -> Vec<String> {
    let mut paths: Vec<String> = status
        .unmerged
        .iter()
        .map(|entry| String::from_utf8_lossy(entry.path.as_bytes()).into_owned())
        .collect();
    paths.sort();
    paths.dedup();
    paths
}

fn is_empty_or_already_applied(text: &str) -> bool {
    let lowered = text.to_ascii_lowercase();
    lowered.contains("nothing to commit")
        || lowered.contains("no changes")
        || lowered.contains("all merge conflicts were fixed")
}

// ---------------------------------------------------------------------------
// Git operation facade (typed GitCli wrappers returning CommandResult-shaped rows)
// ---------------------------------------------------------------------------

struct GitOutcome {
    ok: bool,
    stdout: String,
    stderr: String,
}

impl GitOutcome {
    fn input_error(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            stdout: String::new(),
            stderr: message.into(),
        }
    }
}

fn outcome_of(result: Result<GitCliResult, GitCliError>) -> GitOutcome {
    match result {
        Ok(value) => GitOutcome {
            ok: true,
            stdout: String::from_utf8_lossy(value.output().stdout()).into_owned(),
            stderr: String::from_utf8_lossy(value.output().stderr()).into_owned(),
        },
        Err(GitCliError::Failed(value)) => GitOutcome {
            ok: false,
            stdout: String::from_utf8_lossy(value.output().stdout()).into_owned(),
            stderr: String::from_utf8_lossy(value.output().stderr()).into_owned(),
        },
        Err(other) => GitOutcome::input_error(other.to_string()),
    }
}

struct Git {
    runtime: LarchRuntime,
    runner: TokioProcessRunner,
    policy: GitCliPolicy,
}

impl Git {
    fn new() -> Result<Self, String> {
        let cwd = env::current_dir().map_err(|error| error.to_string())?;
        let policy = GitCliPolicy::new(cwd).map_err(|error| error.to_string())?;
        let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
        Ok(Self {
            runtime,
            runner: TokioProcessRunner::default(),
            policy,
        })
    }

    fn cli(&self) -> GitCli<'_, TokioProcessRunner> {
        GitCli::new(&self.runner, self.policy.clone())
    }

    fn fetch(&self, remote: &str, reference: &str) -> GitOutcome {
        let remote = match GitRemote::new(remote) {
            Ok(remote) => remote,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let refspec = match GitRefspec::new(reference) {
            Ok(refspec) => refspec,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let request = FetchRequest {
            remote,
            refspec: Some(refspec),
            quiet: true,
            no_tags: false,
            mode: larch_adapters::FetchMode::Standard,
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().fetch(request, &Cancellation::new())),
        )
    }

    fn rebase_start(&self, upstream: &str) -> GitOutcome {
        let upstream = match GitRef::new(upstream) {
            Ok(upstream) => upstream,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let request = RebaseRequest::Start {
            onto: None,
            upstream,
            branch: None,
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().rebase(request, &Cancellation::new())),
        )
    }

    fn rebase_continue(&self) -> GitOutcome {
        outcome_of(
            self.runtime.block_on(
                self.cli()
                    .rebase(RebaseRequest::Continue, &Cancellation::new()),
            ),
        )
    }

    fn rebase_skip(&self) -> GitOutcome {
        outcome_of(
            self.runtime
                .block_on(self.cli().rebase(RebaseRequest::Skip, &Cancellation::new())),
        )
    }

    fn rebase_abort(&self) {
        let _ = self.runtime.block_on(
            self.cli()
                .rebase(RebaseRequest::Abort, &Cancellation::new()),
        );
    }

    fn ls_remote_ref(&self, remote: &str, branch: &str) -> GitOutcome {
        let remote = match GitRemote::new(remote) {
            Ok(remote) => remote,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let pattern = match GitRef::new(format!("refs/heads/{branch}")) {
            Ok(pattern) => pattern,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let request = LsRemoteRequest {
            remote: larch_adapters::GitLsRemoteTarget::Configured(remote),
            patterns: vec![pattern],
            heads: true,
            exit_code: false,
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().ls_remote(request, &Cancellation::new())),
        )
    }

    fn force_push_with_lease(&self, remote: &str, branch: &str, expected_oid: &str) -> GitOutcome {
        let remote = match GitRemote::new(remote) {
            Ok(remote) => remote,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let destination = format!("refs/heads/{branch}");
        let refspec = match GitRefspec::new(format!("HEAD:{destination}")) {
            Ok(refspec) => refspec,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let reference = match GitRef::new(destination) {
            Ok(reference) => reference,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let force_with_lease = if expected_oid.is_empty() {
            ForceWithLease::ExpectingAbsent { reference }
        } else {
            match GitRef::new(expected_oid) {
                Ok(oid) => ForceWithLease::Expecting { reference, oid },
                Err(error) => return GitOutcome::input_error(error.to_string()),
            }
        };
        let request = PushRequest {
            remote: larch_adapters::GitPushTarget::Configured(remote),
            refspecs: vec![refspec],
            force_with_lease: Some(force_with_lease),
            set_upstream: false,
            prune: false,
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().push(request, &Cancellation::new())),
        )
    }

    fn checkout_ours(&self, path: &str) -> GitOutcome {
        use larch_adapters::CheckoutRequest;
        let git_path = match GitPath::new(path) {
            Ok(git_path) => git_path,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let request = CheckoutRequest::Paths {
            ours: true,
            theirs: false,
            paths: vec![git_path],
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().checkout(request, &Cancellation::new())),
        )
    }

    fn add_path(&self, path: &str) -> GitOutcome {
        use larch_adapters::AddRequest;
        let git_path = match GitPath::new(path) {
            Ok(git_path) => git_path,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let request = AddRequest {
            all: false,
            force: false,
            pathspec_from_file: None,
            pathspec_file_nul: false,
            paths: vec![git_path],
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().add(request, &Cancellation::new())),
        )
    }

    fn rm_path(&self, path: &str) -> GitOutcome {
        let git_path = match GitPath::new(path) {
            Ok(git_path) => git_path,
            Err(error) => return GitOutcome::input_error(error.to_string()),
        };
        let request = RmRequest {
            force: true,
            paths: vec![git_path],
        };
        outcome_of(
            self.runtime
                .block_on(self.cli().rm(request, &Cancellation::new())),
        )
    }
}

/// Retry a git operation while its combined output matches a transient-network
/// signature, mirroring the Python `with_transient_retry` bounded loop.
fn transient_retry(mut attempt: impl FnMut() -> GitOutcome) -> GitOutcome {
    let mut outcome = attempt();
    let mut tries = 1;
    while !outcome.ok
        && tries < TRANSIENT_ATTEMPTS
        && is_transient_net(&format!("{}{}", outcome.stdout, outcome.stderr))
    {
        thread::sleep(Duration::from_millis(200 * u64::from(tries)));
        outcome = attempt();
        tries += 1;
    }
    outcome
}

// ---------------------------------------------------------------------------
// Repository reads (gitoxide)
// ---------------------------------------------------------------------------

fn open_repository() -> Option<GixRepository> {
    let cwd = env::current_dir().ok()?;
    GixRepository::discover(cwd).ok()
}

fn resolve_optional(repository: &GixRepository, revision: &str) -> Option<ObjectId> {
    repository
        .resolve_revision(&Revision::new(revision.as_bytes()))
        .ok()
}

fn resolve_hex(revision: &str) -> Option<String> {
    let repository = open_repository()?;
    let object = resolve_optional(&repository, revision)?;
    Some(object.to_hex())
}

fn is_ancestor(ancestor_revision: &str, descendant_revision: &str) -> bool {
    let Some(repository) = open_repository() else {
        return false;
    };
    let Some(ancestor) = resolve_optional(&repository, ancestor_revision) else {
        return false;
    };
    let Some(descendant) = resolve_optional(&repository, descendant_revision) else {
        return false;
    };
    repository
        .is_ancestor(&ancestor, &descendant)
        .unwrap_or(false)
}

fn unmerged_paths() -> Vec<String> {
    let Some(repository) = open_repository() else {
        return Vec::new();
    };
    let Ok(status) = repository.local_status(&StatusOptions::default()) else {
        return Vec::new();
    };
    sorted_lossy_unmerged_paths(&status)
}

fn conflict_upstream_deleted(path: &str) -> bool {
    let Some(repository) = open_repository() else {
        return false;
    };
    let Ok(status) = repository.local_status(&StatusOptions::default()) else {
        return false;
    };
    status
        .unmerged
        .iter()
        .find(|entry| entry.path.as_bytes() == path.as_bytes())
        .is_some_and(|entry| !entry.stages.iter().any(|stage| stage.stage == 2))
}

fn rebase_in_progress() -> bool {
    let Some(repository) = open_repository() else {
        return false;
    };
    let git_dir = repository.location().git_dir;
    let mut base = PathBuf::from(String::from_utf8_lossy(git_dir.as_bytes()).into_owned());
    if base.is_relative()
        && let Ok(cwd) = env::current_dir()
    {
        base = cwd.join(base);
    }
    base.join("rebase-merge").is_dir() || base.join("rebase-apply").is_dir()
}

fn resolve_branch_push_remote(branch: &str) -> String {
    let Some(repository) = open_repository() else {
        return DEFAULT_REMOTE.to_owned();
    };
    for key in [
        format!("branch.{branch}.pushRemote"),
        format!("branch.{branch}.remote"),
    ] {
        let Ok(config_key) = ConfigKey::new(key) else {
            continue;
        };
        let Ok(values) = repository.config_values(&config_key) else {
            continue;
        };
        if let Some(value) = values.first() {
            let candidate = String::from_utf8_lossy(&value.value).trim().to_owned();
            if !candidate.is_empty() && is_git_ref_label(&candidate) {
                return candidate;
            }
        }
    }
    DEFAULT_REMOTE.to_owned()
}

// ---------------------------------------------------------------------------
// Text helpers
// ---------------------------------------------------------------------------

fn validate_base_remote_ref(base_remote: &str, base_ref: &str) -> Option<String> {
    if !is_git_ref_label(base_remote) {
        return Some("base_remote contains unsupported characters".to_owned());
    }
    if !is_git_ref_label(base_ref) {
        return Some("base_ref contains unsupported characters".to_owned());
    }
    None
}

fn is_git_ref_label(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'/' | b'-'))
}

/// `text.replace("\n", " ")` plus a `\r` fold so the value is safe for `emit_kv`.
fn replace_newlines(text: &str) -> String {
    text.replace(['\n', '\r'], " ").trim().to_owned()
}

/// `" ".join(text.split())`: collapse every whitespace run to a single space.
fn collapse_whitespace(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Guard `emit_kv` inputs against newlines while preserving Python's single-lining.
fn single_line(text: &str) -> String {
    text.replace(['\n', '\r'], " ")
}

#[cfg(test)]
mod tests {
    use larch_core::{ConflictKind, GitPath, RepositoryStatus, UnmergedEntry};

    use super::sorted_lossy_unmerged_paths;

    #[test]
    fn lossy_unmerged_paths_preserve_legacy_sort_and_deduplication() {
        let unmerged = [b"zeta".as_slice(), b"alpha".as_slice(), &[0xff], &[0xfe]]
            .into_iter()
            .map(|path| UnmergedEntry {
                path: GitPath::new(path),
                kind: ConflictKind::BothModified,
                stages: Vec::new(),
            })
            .collect();
        let status = RepositoryStatus {
            unmerged,
            ..RepositoryStatus::default()
        };

        assert_eq!(
            sorted_lossy_unmerged_paths(&status),
            vec!["alpha", "zeta", "�"]
        );
    }
}
