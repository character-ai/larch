//! Rust owner for `/set-up-forked-open-source-repo` repository setup (#8798).

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::{self, IsTerminal as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

#[cfg(unix)]
use std::os::unix::ffi::OsStringExt as _;

use larch_adapters::{
    BranchMutationRequest, CloneRequest, ConfigMutationRequest, FetchMode, FetchRequest, GitCli,
    GitCliError, GitCliPolicy, GitCliResult, GitConfigKey, GitLsRemoteTarget,
    GitPath as GitCliPath, GitPushTarget, GitRef, GitRefspec, GitRemote, GitUrl, GixRepository,
    LsRemoteRequest, MergeRequest, PushRequest, RemoteMutationRequest, SubmoduleRequest,
    TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ConfigKey, GitHubOperationErrorKind, GitHubRepository, GitHubRepositoryRef, GitHubService as _,
    Head, ObjectId, RemoteClassification, RemoteDescription, RepositoryRead as _, Revision,
    SafeText, StatusOptions, classify_fork_remotes, normalize_github_url,
};

use crate::{git_commands::transient_git, github_service::with_github_service};

const HOST: &str = "github.com";
const MAIN_REF: &str = "refs/heads/main";
const ORIGIN_MAIN_REF: &str = "refs/remotes/origin/main";
const DISABLED_PUSH_URL: &str = "larch-disabled://upstream-push-disabled";
const USAGE: &str =
    "Usage: setup --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]";

#[derive(Clone, Debug, Eq, PartialEq)]
struct SetupOptions {
    upstream: String,
    fork: String,
    mirror_confirmed: bool,
    init_submodules: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RemoteSnapshot {
    remotes: Vec<RemoteDescription>,
    values: Vec<(String, Vec<OsString>)>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct RepositoryUrlOverrides {
    upstream_https: Option<OsString>,
    fork_https: Option<OsString>,
    fork_ssh: Option<OsString>,
}

impl RepositoryUrlOverrides {
    fn from_environment() -> Self {
        Self::from_reader(
            env::var_os("LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE").as_deref() == Some(OsStr::new("1")),
            nonempty_environment,
        )
    }

    fn from_reader(enabled: bool, mut read: impl FnMut(&str) -> Option<OsString>) -> Self {
        if !enabled {
            return Self::default();
        }
        Self {
            upstream_https: read("LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_HTTPS"),
            fork_https: read("LARCH_FORKED_REPO_URL_OVERRIDE_FORK_HTTPS"),
            fork_ssh: read("LARCH_FORKED_REPO_URL_OVERRIDE_FORK_SSH"),
        }
    }
}

struct SetupContext {
    options: SetupOptions,
    root: PathBuf,
    urls: RepositoryUrlOverrides,
    classification: Option<RemoteClassification>,
    snapshot: Option<RemoteSnapshot>,
    remote_undo: Vec<RemoteMutationRequest>,
    remote_phase_active: bool,
    lock_guard: Option<SetupLock>,
}

struct SetupLock {
    directory: PathBuf,
    holder: PathBuf,
    owner: String,
}

impl SetupLock {
    fn acquire(common_dir: &Path) -> Result<Self, String> {
        let common_dir = fs::canonicalize(common_dir)
            .map_err(|error| format!("cannot resolve Git common directory: {error}"))?;
        let directory = common_dir.join("larch-fork-setup.lock.d");
        if fs::create_dir(&directory).is_err() {
            let holder = read_lock_holder(&directory.join("holder"));
            return Err(format!(
                "another setup-forked-open-source-repo run is in progress (lock={}, holder={holder})",
                directory.display()
            ));
        }
        let holder = directory.join("holder");
        let owner = std::process::id().to_string();
        if let Err(error) = fs::write(&holder, format!("{owner}\n")) {
            let _ = fs::remove_dir(&directory);
            return Err(format!("cannot record fork setup lock holder: {error}"));
        }
        Ok(Self {
            directory,
            holder,
            owner,
        })
    }
}

impl Drop for SetupLock {
    fn drop(&mut self) {
        let holder_owned = fs::symlink_metadata(&self.holder).is_ok_and(|metadata| {
            metadata.is_file()
                && !metadata.file_type().is_symlink()
                && fs::read_to_string(&self.holder).is_ok_and(|value| value.trim() == self.owner)
        });
        let directory_owned = fs::symlink_metadata(&self.directory)
            .is_ok_and(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink());
        if holder_owned && directory_owned {
            let _ = fs::remove_file(&self.holder);
            let _ = fs::remove_dir(&self.directory);
        }
    }
}

struct GitEffects {
    runtime: LarchRuntime,
    runner: TokioProcessRunner,
    cancellation: Cancellation,
}

macro_rules! git_effect_method {
    ($name:ident, $method:ident, $request:ty) => {
        fn $name(&self, cwd: &Path, request: $request) -> Result<GitCliResult, GitCliError> {
            let cli = GitCli::new(&self.runner, GitCliPolicy::new(cwd.to_path_buf())?);
            self.runtime
                .block_on(cli.$method(request, &self.cancellation))
        }
    };
}

impl GitEffects {
    fn new() -> Result<Self, String> {
        Ok(Self {
            runtime: LarchRuntime::new()
                .map_err(|error| format!("cannot initialize larch runtime: {error}"))?,
            runner: TokioProcessRunner::default(),
            cancellation: Cancellation::new(),
        })
    }

    git_effect_method!(fetch, fetch, FetchRequest);
    git_effect_method!(remote_mutation, remote_mutation, RemoteMutationRequest);
    git_effect_method!(config_mutation, config_mutation, ConfigMutationRequest);
    git_effect_method!(branch_mutation, branch_mutation, BranchMutationRequest);
    git_effect_method!(merge, merge, MergeRequest);
    git_effect_method!(submodule, submodule, SubmoduleRequest);
    git_effect_method!(clone_repository, clone_repository, CloneRequest);
    git_effect_method!(push, push, PushRequest);
    git_effect_method!(ls_remote, ls_remote, LsRemoteRequest);
}

enum ParseOutcome {
    Options(SetupOptions),
    Exit(ExitCode),
}

enum RepositoryLookup {
    Found(GitHubRepository),
    Missing,
}

/// Run the legacy-compatible `forked-repo setup` command.
#[must_use]
pub fn setup(arguments: &[OsString]) -> ExitCode {
    let options = match parse_arguments(arguments) {
        ParseOutcome::Options(options) => options,
        ParseOutcome::Exit(code) => return code,
    };
    let cwd = match env::current_dir() {
        Ok(cwd) => cwd,
        Err(error) => {
            eprintln!("ERROR: cannot resolve current directory: {error}");
            return ExitCode::FAILURE;
        }
    };
    setup_from(options, &cwd)
}

fn setup_from(options: SetupOptions, cwd: &Path) -> ExitCode {
    let root = match repository_root(cwd) {
        Ok(root) => root,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    let effects = match GitEffects::new() {
        Ok(effects) => effects,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    let mut context = SetupContext {
        options,
        root,
        urls: RepositoryUrlOverrides::from_environment(),
        classification: None,
        snapshot: None,
        remote_undo: Vec::new(),
        remote_phase_active: false,
        lock_guard: None,
    };
    let result = run_setup(&mut context, &effects);
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ERROR: {error}");
            rollback_remotes_if_active(&mut context, &effects);
            ExitCode::FAILURE
        }
    }
}

fn run_setup(context: &mut SetupContext, effects: &GitEffects) -> Result<(), String> {
    phase_preflight(context, effects)?;
    if !phase_github(context, effects)? {
        return Ok(());
    }
    phase_remotes(context, effects)?;
    phase_submodules(context, effects)?;
    phase_verify(context)?;
    Ok(())
}

fn parse_arguments(arguments: &[OsString]) -> ParseOutcome {
    let mut upstream = None;
    let mut fork = None;
    let mut mirror_confirmed = false;
    let mut init_submodules = false;
    let mut index = 0_usize;
    while index < arguments.len() {
        let argument = &arguments[index];
        match argument.to_str() {
            Some("--upstream" | "--fork") => {
                let option = argument.to_string_lossy();
                let Some(value) = arguments.get(index + 1) else {
                    eprintln!("ERROR: {option} requires a value");
                    return ParseOutcome::Exit(ExitCode::FAILURE);
                };
                let Some(value) = value.to_str() else {
                    eprintln!("ERROR: {option} must have owner/repo shape");
                    return ParseOutcome::Exit(ExitCode::FAILURE);
                };
                if option == "--upstream" {
                    upstream = Some(value.to_owned());
                } else {
                    fork = Some(value.to_owned());
                }
                index += 2;
            }
            Some("--mirror-confirmed") => {
                mirror_confirmed = true;
                index += 1;
            }
            Some("--init-submodules") => {
                init_submodules = true;
                index += 1;
            }
            Some("-h" | "--help") => {
                eprintln!("{USAGE}");
                return ParseOutcome::Exit(ExitCode::SUCCESS);
            }
            _ => {
                eprintln!("{USAGE}");
                eprintln!("ERROR: unknown argument: {}", argument.to_string_lossy());
                return ParseOutcome::Exit(ExitCode::FAILURE);
            }
        }
    }
    let Some(upstream) = upstream else {
        eprintln!("ERROR: missing --upstream");
        return ParseOutcome::Exit(ExitCode::FAILURE);
    };
    let Some(fork) = fork else {
        eprintln!("ERROR: missing --fork");
        return ParseOutcome::Exit(ExitCode::FAILURE);
    };
    if !owner_repo_shape(&upstream) {
        eprintln!("ERROR: --upstream must have owner/repo shape");
        return ParseOutcome::Exit(ExitCode::FAILURE);
    }
    if !owner_repo_shape(&fork) {
        eprintln!("ERROR: --fork must have owner/repo shape");
        return ParseOutcome::Exit(ExitCode::FAILURE);
    }
    ParseOutcome::Options(SetupOptions {
        upstream,
        fork,
        mirror_confirmed,
        init_submodules,
    })
}

fn owner_repo_shape(value: &str) -> bool {
    value.split_once('/').is_some_and(|(owner, repository)| {
        !repository.contains('/')
            && [owner, repository].into_iter().all(|part| {
                !part.is_empty()
                    && part.bytes().all(|byte| {
                        byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-')
                    })
            })
    })
}

fn repository_root(cwd: &Path) -> Result<PathBuf, String> {
    let repository = GixRepository::discover(cwd)
        .map_err(|_| "not inside a Git working repository".to_owned())?;
    let location = repository.location();
    location
        .work_dir
        .as_ref()
        .ok_or_else(|| "not inside a Git working repository".to_owned())
        .and_then(|path| path_from_git_bytes(path.as_bytes()))
}

fn phase_preflight(context: &mut SetupContext, effects: &GitEffects) -> Result<(), String> {
    let repository = open_repository(&context.root)?;
    let location = repository.location();
    let common_dir = path_from_git_bytes(location.common_dir.as_bytes())?;
    context.lock_guard = Some(SetupLock::acquire(&common_dir)?);
    let main =
        resolve(&repository, MAIN_REF).map_err(|_| "local refs/heads/main is absent".to_owned())?;
    match repository.head().map_err(text_error)? {
        Head::Symbolic { name, .. } if matches!(name.as_bytes(), b"main" | b"refs/heads/main") => {}
        _ => return Err("current checkout must be main".to_owned()),
    }
    let remotes = remote_descriptions(&repository)?;
    if let Some(origin) = remotes.iter().find(|remote| remote.name == "origin") {
        if origin.urls.len() > 1 {
            return Err("multiple remote.origin.url entries; refuse early".to_owned());
        }
        let url = origin.urls.first().map_or("", String::as_str);
        let Some(parsed) = normalize_github_url(url) else {
            return Err(format!(
                "origin remote URL '{}' is not a recognized GitHub-compatible URL; refusing to fetch",
                SafeText::from_untrusted(url)
            ));
        };
        if parsed.host != HOST {
            return Err(format!(
                "origin remote URL '{}' is not hosted on github.com; refusing to fetch",
                SafeText::from_untrusted(url)
            ));
        }
    }
    if !all_worktrees_clean(&repository)? {
        return Err("working tree is dirty; commit or stash before running".to_owned());
    }
    if !no_operation_in_progress(&repository)? {
        return Err("git operation in progress; resolve it before running".to_owned());
    }
    if remotes.iter().any(|remote| remote.name == "origin") {
        let classification = classify_fork_remotes(
            &remotes,
            &context.options.upstream,
            &context.options.fork,
            HOST,
        );
        if classification == RemoteClassification::Ambiguous {
            return Err(
                "ambiguous remote state; refusing to call GitHub before remotes are resolved"
                    .to_owned(),
            );
        }
        context.classification = Some(classification);
        effects
            .fetch(
                &context.root,
                FetchRequest {
                    remote: git_remote("origin")?,
                    refspec: None,
                    quiet: false,
                    no_tags: false,
                    mode: FetchMode::Standard,
                },
            )
            .map_err(git_error_detail)?;
        let repository = open_repository(&context.root)?;
        let origin_main = resolve(&repository, ORIGIN_MAIN_REF)
            .map_err(|_| "origin/main is absent after fetch".to_owned())?;
        if !repository
            .is_ancestor(&main, &origin_main)
            .map_err(text_error)?
        {
            if repository
                .is_ancestor(&origin_main, &main)
                .map_err(text_error)?
            {
                return Err(
                    "local main is ahead of origin/main; push or reset manually before running"
                        .to_owned(),
                );
            }
            return Err("local main and origin/main have diverged".to_owned());
        }
    }
    Ok(())
}

fn phase_github(context: &SetupContext, effects: &GitEffects) -> Result<bool, String> {
    let fork = repository_ref(&context.options.fork)?;
    let lookup = with_github_service(async |service, cancellation| {
        match service.repository(&fork, cancellation).await {
            Ok(repository) => Ok(RepositoryLookup::Found(repository)),
            Err(error) if error.kind() == GitHubOperationErrorKind::NotFound => {
                Ok(RepositoryLookup::Missing)
            }
            Err(error) => Err(error.to_string()),
        }
    })
    .map_err(|error| {
        format!(
            "GitHub authentication or repository lookup failed: {}",
            error.into_detail()
        )
    })?;
    handle_repository_lookup(context, effects, lookup)
}

fn handle_repository_lookup(
    context: &SetupContext,
    effects: &GitEffects,
    lookup: RepositoryLookup,
) -> Result<bool, String> {
    let repository = match lookup {
        RepositoryLookup::Found(repository) => repository,
        RepositoryLookup::Missing => {
            eprintln!(
                "Fork {} was not found. Create it at https://github.com/{}/fork, then rerun this skill.",
                context.options.fork, context.options.upstream
            );
            println!("SETUP_FORKED_REPO_RESULT=fork_missing");
            return Ok(false);
        }
    };
    let actual_parent = repository.parent.as_ref().map_or_else(
        || "<none>".to_owned(),
        |parent| format!("{}/{}", parent.owner(), parent.name()),
    );
    if !actual_parent.eq_ignore_ascii_case(&context.options.upstream) {
        return Err(format!(
            "fork parent mismatch: expected {}, got {actual_parent}",
            context.options.upstream
        ));
    }
    sync_fork(context, effects)
}

fn sync_fork(context: &SetupContext, effects: &GitEffects) -> Result<bool, String> {
    let upstream_https = context.upstream_https()?;
    let fork_https = context.fork_https()?;
    let upstream_sha = remote_main_sha(effects, &context.root, &upstream_https)?;
    let fork_sha = remote_main_sha(effects, &context.root, &fork_https)?;
    let Some(upstream_sha) = upstream_sha else {
        return Err("upstream has no refs/heads/main".to_owned());
    };
    let Some(fork_sha) = fork_sha else {
        return Err("fork has no refs/heads/main".to_owned());
    };
    if upstream_sha == fork_sha {
        println!("SETUP_FORKED_REPO_RESULT=mirror_skipped_in_sync");
        return Ok(true);
    }
    eprintln!(
        "Fork main differs from upstream main: upstream={upstream_sha} fork={fork_sha}. Confirming will overwrite fork branches/tags to match upstream."
    );
    if !context.options.mirror_confirmed {
        if !io::stdin().is_terminal() {
            return Err("mirror divergence detected; rerun with --mirror-confirmed".to_owned());
        }
        eprintln!("Mirror-sync fork now? [y/N] ");
        let mut reply = String::new();
        io::stdin()
            .read_line(&mut reply)
            .map_err(|error| format!("cannot read mirror confirmation: {error}"))?;
        if !matches!(reply.trim().to_ascii_lowercase().as_str(), "y" | "yes") {
            return Err("mirror sync declined".to_owned());
        }
    }
    if remote_main_sha(effects, &context.root, &upstream_https)?.as_deref()
        != Some(upstream_sha.as_str())
        || remote_main_sha(effects, &context.root, &fork_https)?.as_deref()
            != Some(fork_sha.as_str())
    {
        return Err("remote moved during confirmation; rerun".to_owned());
    }
    let repository = open_repository(&context.root)?;
    if !all_worktrees_clean(&repository)? || !no_operation_in_progress(&repository)? {
        return Err("working tree became dirty before mirror push".to_owned());
    }
    let temporary = tempfile::Builder::new()
        .prefix("larch-forked-mirror.")
        .tempdir()
        .map_err(|error| format!("cannot create mirror staging directory: {error}"))?;
    effects
        .clone_repository(
            temporary.path(),
            CloneRequest {
                url: upstream_https,
                directory: Some(GitCliPath::new("upstream.git").map_err(text_error)?),
                mirror: true,
            },
        )
        .map_err(git_error_detail)?;
    let mirror = temporary.path().join("upstream.git");
    let pushed_sha = resolve(&open_repository(&mirror)?, MAIN_REF)
        .map_err(|_| "mirror clone has no refs/heads/main".to_owned())?
        .to_hex();
    let fork_ssh = context.fork_ssh()?;
    transient_git(|| {
        effects.push(
            &mirror,
            PushRequest {
                remote: GitPushTarget::Url(fork_ssh.clone()),
                refspecs: vec![
                    GitRefspec::new("+refs/heads/*:refs/heads/*")?,
                    GitRefspec::new("+refs/tags/*:refs/tags/*")?,
                ],
                force_with_lease: None,
                set_upstream: false,
                prune: true,
            },
        )
    })
    .map_err(|_| "mirror push to fork failed".to_owned())?;
    let post_sha = remote_main_sha(effects, &context.root, &fork_https)?;
    if post_sha.as_deref() != Some(pushed_sha.as_str()) {
        return Err(format!(
            "fork refs/heads/main did not match what was pushed (expected {pushed_sha}, got {})",
            post_sha.as_deref().unwrap_or("<none>")
        ));
    }
    println!("SETUP_FORKED_REPO_RESULT=mirror_synced");
    Ok(true)
}

fn phase_remotes(context: &mut SetupContext, effects: &GitEffects) -> Result<(), String> {
    let repository = open_repository(&context.root)?;
    context.snapshot = Some(snapshot_remote_state(&repository)?);
    context.remote_phase_active = true;
    let remotes = remote_descriptions(&repository)?;
    let classification = context.classification.clone().unwrap_or_else(|| {
        classify_fork_remotes(
            &remotes,
            &context.options.upstream,
            &context.options.fork,
            HOST,
        )
    });
    match classification {
        RemoteClassification::AlreadyConfigured => {}
        state @ (RemoteClassification::OriginUpstreamOnly
        | RemoteClassification::OriginUpstreamNamedFork(_)) => {
            rename_remote(context, effects, "origin", "upstream")?;
            reject_injection("after-rename-origin-upstream")?;
            match state {
                RemoteClassification::OriginUpstreamOnly => {
                    let fork_url = context.fork_ssh()?;
                    add_remote(context, effects, "origin", fork_url)?;
                }
                RemoteClassification::OriginUpstreamNamedFork(named) => {
                    rename_remote(context, effects, &named, "origin")?;
                }
                _ => unreachable!("pattern limits the state"),
            }
        }
        RemoteClassification::Ambiguous => {
            return Err("ambiguous remote state; refusing to mutate.".to_owned());
        }
    }
    let upstream_push = config_key("remote.upstream.pushurl")?;
    let _ = effects.config_mutation(
        &context.root,
        ConfigMutationRequest::UnsetAll {
            key: upstream_push.clone(),
        },
    );
    effects
        .config_mutation(
            &context.root,
            ConfigMutationRequest::Add {
                key: upstream_push,
                value: OsString::from(DISABLED_PUSH_URL),
            },
        )
        .map_err(git_error_detail)?;
    let _ = effects.config_mutation(
        &context.root,
        ConfigMutationRequest::UnsetAll {
            key: config_key("remote.origin.pushurl")?,
        },
    );
    if injection_is("fetch") || injection_is("rollback") {
        return Err("injected failure".to_owned());
    }
    effects
        .fetch(
            &context.root,
            FetchRequest {
                remote: git_remote("origin")?,
                refspec: None,
                quiet: false,
                no_tags: false,
                mode: FetchMode::PruneTags,
            },
        )
        .map_err(git_error_detail)?;
    effects
        .branch_mutation(
            &context.root,
            BranchMutationRequest::SetUpstream {
                name: git_ref("main")?,
                upstream: git_ref("origin/main")?,
            },
        )
        .map_err(git_error_detail)?;
    let repository = open_repository(&context.root)?;
    if !all_worktrees_clean(&repository)? {
        return Err("working tree became dirty before fast-forward".to_owned());
    }
    let main = resolve(&repository, MAIN_REF).map_err(text_error)?;
    let origin_main = resolve(&repository, ORIGIN_MAIN_REF).map_err(text_error)?;
    if !repository
        .is_ancestor(&origin_main, &main)
        .map_err(text_error)?
    {
        effects
            .merge(
                &context.root,
                MergeRequest::FastForward {
                    target: git_ref("origin/main")?,
                },
            )
            .map_err(git_error_detail)?;
    }
    Ok(())
}

fn phase_submodules(context: &SetupContext, effects: &GitEffects) -> Result<(), String> {
    if !context.options.init_submodules || !context.root.join(".gitmodules").is_file() {
        return Ok(());
    }
    transient_git(|| {
        effects.submodule(
            &context.root,
            SubmoduleRequest::Update {
                init: true,
                recursive: true,
            },
        )
    })
    .map(drop)
    .map_err(|_| "git submodule update --init --recursive failed".to_owned())
}

fn phase_verify(context: &mut SetupContext) -> Result<(), String> {
    if injection_is("in-verify") {
        return Err("injected failure".to_owned());
    }
    let repository = open_repository(&context.root)?;
    let remotes = remote_descriptions(&repository)?;
    let origin = remotes.iter().find(|remote| remote.name == "origin");
    let upstream = remotes.iter().find(|remote| remote.name == "upstream");
    let fork_aliases = [context.fork_https()?, context.fork_ssh()?];
    let upstream_aliases = [context.upstream_https()?];
    if remotes.len() != 2
        || origin.is_none_or(|remote| !remote_matches(remote, &context.options.fork, &fork_aliases))
        || upstream.is_none_or(|remote| {
            !remote_matches(remote, &context.options.upstream, &upstream_aliases)
        })
    {
        return Err("final origin/upstream configuration is invalid".to_owned());
    }
    if origin.is_none_or(|remote| !remote.push_urls.is_empty())
        || upstream.is_none_or(|remote| remote.push_urls != [DISABLED_PUSH_URL])
    {
        return Err("final remote push protection is invalid".to_owned());
    }
    eprintln!();
    eprintln!("Final remotes:");
    for remote in remotes {
        if let Some(fetch) = remote.urls.first() {
            eprintln!("{}\t{fetch} (fetch)", remote.name);
            let push = remote.push_urls.first().unwrap_or(fetch);
            eprintln!("{}\t{push} (push)", remote.name);
        }
    }
    eprintln!();
    eprintln!("Disabled upstream push sentinel:");
    for value in config_text_values(&repository, "remote.upstream.pushurl")? {
        eprintln!("remote.upstream.pushurl {value}");
    }
    if config_text_values(&repository, "branch.main.remote")?
        .last()
        .map(String::as_str)
        != Some("origin")
    {
        return Err("branch.main.remote is not origin".to_owned());
    }
    if config_text_values(&repository, "branch.main.merge")?
        .last()
        .map(String::as_str)
        != Some(MAIN_REF)
    {
        return Err("branch.main.merge is not refs/heads/main".to_owned());
    }
    eprintln!();
    eprintln!(
        "Fork workflow: branch off origin/main, push topic branches to origin, and open PRs from {}:<branch> to {}:main.",
        context.options.fork, context.options.upstream
    );
    println!("SETUP_FORKED_REPO_RESULT=ok");
    context.remote_phase_active = false;
    Ok(())
}

impl SetupContext {
    fn upstream_https(&self) -> Result<GitUrl, String> {
        Self::url(
            self.urls.upstream_https.as_deref(),
            format!("https://{HOST}/{}.git", self.options.upstream),
        )
    }

    fn fork_https(&self) -> Result<GitUrl, String> {
        Self::url(
            self.urls.fork_https.as_deref(),
            format!("https://{HOST}/{}.git", self.options.fork),
        )
    }

    fn fork_ssh(&self) -> Result<GitUrl, String> {
        Self::url(
            self.urls.fork_ssh.as_deref(),
            format!("git@{HOST}:{}.git", self.options.fork),
        )
    }

    fn url(override_value: Option<&OsStr>, fallback: String) -> Result<GitUrl, String> {
        GitUrl::new(override_value.map_or_else(|| fallback.into(), ToOwned::to_owned))
            .map_err(text_error)
    }
}

fn nonempty_environment(name: &str) -> Option<OsString> {
    env::var_os(name).filter(|value| !value.is_empty())
}

fn remote_main_sha(
    effects: &GitEffects,
    cwd: &Path,
    remote: &GitUrl,
) -> Result<Option<String>, String> {
    let reference = git_ref(MAIN_REF)?;
    let result = transient_git(|| {
        effects.ls_remote(
            cwd,
            LsRemoteRequest {
                remote: GitLsRemoteTarget::Url(remote.clone()),
                patterns: vec![reference.clone()],
                heads: false,
                exit_code: false,
            },
        )
    });
    let Ok(result) = result else {
        return Ok(None);
    };
    if result.truncated() {
        return Ok(None);
    }
    let output = String::from_utf8_lossy(result.output().stdout());
    Ok(output.lines().find_map(|line| {
        let mut fields = line.split_whitespace();
        let sha = fields.next()?;
        let reference = fields.next()?;
        (reference == MAIN_REF
            && fields.next().is_none()
            && matches!(sha.len(), 40 | 64)
            && sha.bytes().all(|byte| byte.is_ascii_hexdigit()))
        .then(|| sha.to_ascii_lowercase())
    }))
}

fn all_worktrees_clean(repository: &GixRepository) -> Result<bool, String> {
    for worktree in repository.worktrees().map_err(text_error)? {
        let path = path_from_git_bytes(worktree.path.as_bytes())?;
        if !path.is_dir() {
            continue;
        }
        let status = open_repository(&path)?
            .status(&StatusOptions::default())
            .map_err(text_error)?;
        if status.is_dirty() {
            eprintln!(
                "ERROR: working tree '{}' is dirty; commit or stash before running",
                path.display()
            );
            return Ok(false);
        }
    }
    Ok(true)
}

fn no_operation_in_progress(repository: &GixRepository) -> Result<bool, String> {
    for worktree in repository.worktrees().map_err(text_error)? {
        let path = path_from_git_bytes(worktree.path.as_bytes())?;
        if !path.is_dir() {
            continue;
        }
        let git_dir = path_from_git_bytes(worktree.git_dir.as_bytes())?;
        for sentinel in [
            "MERGE_HEAD",
            "REBASE_HEAD",
            "rebase-apply",
            "rebase-merge",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
        ] {
            if git_dir.join(sentinel).exists() {
                eprintln!(
                    "ERROR: git operation in progress in '{}' ({sentinel}); resolve it before running",
                    path.display()
                );
                return Ok(false);
            }
        }
    }
    Ok(true)
}

fn remote_descriptions(repository: &GixRepository) -> Result<Vec<RemoteDescription>, String> {
    let mut descriptions = Vec::new();
    for remote in repository.remotes().map_err(text_error)? {
        let name = String::from_utf8(remote.name)
            .map_err(|_| "remote name is not valid UTF-8".to_owned())?;
        descriptions.push(RemoteDescription {
            urls: config_text_values(repository, &format!("remote.{name}.url"))?,
            push_urls: config_text_values(repository, &format!("remote.{name}.pushurl"))?,
            name,
        });
    }
    descriptions.sort_by(|left, right| left.name.cmp(&right.name));
    Ok(descriptions)
}

fn remote_matches(remote: &RemoteDescription, repository: &str, aliases: &[GitUrl]) -> bool {
    let [url] = remote.urls.as_slice() else {
        return false;
    };
    normalize_github_url(url).is_some_and(|parsed| {
        parsed.host == HOST && parsed.repository.eq_ignore_ascii_case(repository)
    }) || aliases
        .iter()
        .any(|alias| alias.as_os_str() == OsStr::new(url))
}

fn config_text_values(repository: &GixRepository, key: &str) -> Result<Vec<String>, String> {
    raw_config_values(repository, key)?
        .into_iter()
        .filter(|value| !value.is_empty())
        .map(|value| {
            value
                .into_string()
                .map_err(|_| format!("Git configuration value for {key} is not valid UTF-8"))
        })
        .collect()
}

fn raw_config_values(repository: &GixRepository, key: &str) -> Result<Vec<OsString>, String> {
    repository
        .config_values(&ConfigKey::new(key).map_err(text_error)?)
        .map_err(text_error)?
        .into_iter()
        .map(|value| os_string_from_git_bytes(&value.value, "Git configuration value"))
        .collect()
}

fn snapshot_remote_state(repository: &GixRepository) -> Result<RemoteSnapshot, String> {
    let remotes = remote_descriptions(repository)?;
    let mut values = Vec::new();
    for remote in &remotes {
        let key = format!("remote.{}.pushurl", remote.name);
        values.push((key.clone(), raw_config_values(repository, &key)?));
    }
    for key in ["branch.main.remote", "branch.main.merge"] {
        values.push((key.to_owned(), raw_config_values(repository, key)?));
    }
    Ok(RemoteSnapshot { remotes, values })
}

fn rollback_remotes_if_active(context: &mut SetupContext, effects: &GitEffects) {
    if !context.remote_phase_active {
        return;
    }
    context.remote_phase_active = false;
    let Some(snapshot) = context.snapshot.clone() else {
        return;
    };
    eprintln!("ERROR: remote rewrite failed; attempting rollback");
    if injection_is("rollback") {
        eprintln!("RECOVERY_REPORT rollback_failed=true reason=injected-rollback-failure");
        eprintln!("RECOVERY_REPORT rollback_failed=true reason=restore-remote-state-failed");
        return;
    }
    let mut restored = true;
    while let Some(undo) = context.remote_undo.pop() {
        if effects.remote_mutation(&context.root, undo).is_err() {
            restored = false;
        }
    }
    restored &= restore_remote_state(&context.root, &snapshot, effects).unwrap_or(false);
    if !restored {
        eprintln!("RECOVERY_REPORT rollback_failed=true reason=git-config-restore-failed");
        eprintln!("RECOVERY_REPORT rollback_failed=true reason=restore-remote-state-failed");
    }
}

fn restore_remote_state(
    root: &Path,
    snapshot: &RemoteSnapshot,
    effects: &GitEffects,
) -> Result<bool, String> {
    let mut ok = true;
    for (key, values) in &snapshot.values {
        let _ = effects.config_mutation(
            root,
            ConfigMutationRequest::UnsetAll {
                key: config_key(key)?,
            },
        );
        for value in values {
            if effects
                .config_mutation(
                    root,
                    ConfigMutationRequest::Add {
                        key: config_key(key)?,
                        value: value.clone(),
                    },
                )
                .is_err()
            {
                ok = false;
            }
        }
    }
    Ok(ok && snapshot_remote_state(&open_repository(root)?)? == *snapshot)
}

fn add_remote(
    context: &mut SetupContext,
    effects: &GitEffects,
    name: &str,
    url: GitUrl,
) -> Result<(), String> {
    effects
        .remote_mutation(
            &context.root,
            RemoteMutationRequest::Add {
                name: git_remote(name)?,
                url,
            },
        )
        .map_err(git_error_detail)?;
    context.remote_undo.push(RemoteMutationRequest::Remove {
        name: git_remote(name)?,
    });
    Ok(())
}

fn rename_remote(
    context: &mut SetupContext,
    effects: &GitEffects,
    from: &str,
    to: &str,
) -> Result<(), String> {
    effects
        .remote_mutation(
            &context.root,
            RemoteMutationRequest::Rename {
                from: git_remote(from)?,
                to: git_remote(to)?,
            },
        )
        .map_err(git_error_detail)?;
    context.remote_undo.push(RemoteMutationRequest::Rename {
        from: git_remote(to)?,
        to: git_remote(from)?,
    });
    Ok(())
}

fn injection_is(value: &str) -> bool {
    env::var_os("LARCH_FORKED_REPO_INJECT_FAILURE").as_deref() == Some(OsStr::new(value))
}

fn reject_injection(value: &str) -> Result<(), String> {
    (!injection_is(value))
        .then_some(())
        .ok_or_else(|| "injected failure".to_owned())
}

fn repository_ref(value: &str) -> Result<GitHubRepositoryRef, String> {
    let (owner, name) = value
        .split_once('/')
        .ok_or_else(|| "repository must have owner/repo shape".to_owned())?;
    GitHubRepositoryRef::new(owner, name).map_err(|error| error.to_string())
}

fn open_repository(path: &Path) -> Result<GixRepository, String> {
    GixRepository::open(path).map_err(text_error)
}

fn resolve(
    repository: &GixRepository,
    revision: &str,
) -> Result<ObjectId, larch_core::RepositoryError> {
    repository.resolve_revision(&Revision::new(revision.as_bytes()))
}

fn git_remote(value: &str) -> Result<GitRemote, String> {
    GitRemote::new(value).map_err(text_error)
}

fn git_ref(value: &str) -> Result<GitRef, String> {
    GitRef::new(value).map_err(text_error)
}

fn config_key(value: &str) -> Result<GitConfigKey, String> {
    GitConfigKey::new(value).map_err(text_error)
}

fn git_error_detail(error: GitCliError) -> String {
    let fallback = error.to_string();
    if let GitCliError::Failed(result) = error {
        let detail = result.safe_stderr();
        if !detail.as_str().trim().is_empty() {
            return detail.as_str().trim().to_owned();
        }
    }
    fallback
}

fn text_error(error: impl std::fmt::Display) -> String {
    error.to_string()
}

fn read_lock_holder(path: &Path) -> String {
    let regular = fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink());
    if !regular {
        return "unknown".to_owned();
    }
    fs::read_to_string(path)
        .ok()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "unknown".to_owned())
}

#[cfg(unix)]
fn os_string_from_git_bytes(bytes: &[u8], label: &str) -> Result<OsString, String> {
    if bytes.contains(&0) {
        return Err(format!("{label} contains NUL"));
    }
    Ok(OsString::from_vec(bytes.to_vec()))
}

#[cfg(not(unix))]
fn os_string_from_git_bytes(bytes: &[u8], label: &str) -> Result<OsString, String> {
    String::from_utf8(bytes.to_vec())
        .map(Into::into)
        .map_err(|_| format!("{label} is not valid UTF-8"))
}

fn path_from_git_bytes(bytes: &[u8]) -> Result<PathBuf, String> {
    os_string_from_git_bytes(bytes, "Git repository path").map(PathBuf::from)
}

#[cfg(test)]
mod tests {
    use std::{ffi::OsString, fmt::Debug};

    use larch_core::RemoteClassification;
    use larch_test_support::{GitFixture, GitRepository};

    use super::*;

    fn checked_git_os(repository: &GitRepository, arguments: &[OsString]) -> Vec<u8> {
        let output = repository.git(arguments).expect("run installed Git");
        assert!(
            output.success(),
            "Git failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        output.stdout
    }

    fn checked_git(repository: &GitRepository, arguments: &[&str]) -> Vec<u8> {
        checked_git_os(repository, &os_arguments(arguments))
    }

    fn os_arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn fixture(kind: GitFixture) -> GitRepository {
        GitRepository::builder(kind).build().expect("Git fixture")
    }

    fn assert_error<T: Debug>(result: Result<T, String>, expected: &str) {
        let error = result.expect_err("operation must fail");
        assert!(error.contains(expected), "unexpected error: {error}");
    }

    fn setup_options() -> SetupOptions {
        SetupOptions {
            upstream: "upstream/repo".to_owned(),
            fork: "fork/repo".to_owned(),
            mirror_confirmed: false,
            init_submodules: false,
        }
    }

    fn clone_bare(repository: &GitRepository, destination: &Path) {
        checked_git_os(
            repository,
            &[
                OsString::from("clone"),
                OsString::from("--quiet"),
                OsString::from("--bare"),
                repository.root().as_os_str().to_owned(),
                destination.as_os_str().to_owned(),
            ],
        );
    }

    fn add_remote(repository: &GitRepository, name: &str, url: &Path) {
        checked_git_os(
            repository,
            &[
                "remote".into(),
                "add".into(),
                name.into(),
                url.as_os_str().to_owned(),
            ],
        );
    }

    fn context(root: &Path, upstream: &Path, fork: &Path, mirror_confirmed: bool) -> SetupContext {
        SetupContext {
            options: SetupOptions {
                mirror_confirmed,
                ..setup_options()
            },
            root: root.to_path_buf(),
            urls: RepositoryUrlOverrides {
                upstream_https: Some(upstream.as_os_str().to_owned()),
                fork_https: Some(fork.as_os_str().to_owned()),
                fork_ssh: Some(fork.as_os_str().to_owned()),
            },
            classification: Some(RemoteClassification::OriginUpstreamOnly),
            snapshot: None,
            remote_undo: Vec::new(),
            remote_phase_active: false,
            lock_guard: None,
        }
    }

    fn github_repository(parent: Option<&str>) -> GitHubRepository {
        GitHubRepository {
            id: 1,
            name_with_owner: "fork/repo".to_owned(),
            url: "https://github.com/fork/repo".to_owned(),
            default_branch: "main".to_owned(),
            private: false,
            parent: parent.map(|value| repository_ref(value).expect("repository parent")),
        }
    }

    fn local_fork_fixture(diverged: bool) -> (GitRepository, PathBuf, PathBuf) {
        let repository = fixture(GitFixture::Refs);
        let fork = repository.workspace_root().join("fork.git");
        clone_bare(&repository, &fork);
        if diverged {
            repository
                .write("tracked.txt", b"upstream change\n")
                .expect("write upstream change");
            checked_git(&repository, &["add", "--", "tracked.txt"]);
            checked_git(&repository, &["commit", "--quiet", "-m", "upstream change"]);
        }
        let upstream = repository.workspace_root().join("upstream.git");
        clone_bare(&repository, &upstream);
        add_remote(&repository, "origin", &upstream);
        (repository, upstream, fork)
    }

    #[test]
    fn parser_and_small_validators_cover_the_frozen_contract() {
        let valid = os_arguments(&[
            "--upstream",
            "upstream/repo",
            "--fork",
            "fork/repo",
            "--mirror-confirmed",
            "--init-submodules",
        ]);
        let ParseOutcome::Options(options) = parse_arguments(&valid) else {
            panic!("valid options must parse");
        };
        assert_eq!(
            options,
            SetupOptions {
                upstream: "upstream/repo".to_owned(),
                fork: "fork/repo".to_owned(),
                mirror_confirmed: true,
                init_submodules: true,
            }
        );

        for (arguments, expected) in [
            (vec![], ExitCode::FAILURE),
            (os_arguments(&["--upstream"]), ExitCode::FAILURE),
            (os_arguments(&["--upstream", "up/repo"]), ExitCode::FAILURE),
            (
                os_arguments(&["--upstream", "bad", "--fork", "fork/repo"]),
                ExitCode::FAILURE,
            ),
            (
                os_arguments(&["--upstream", "up/repo", "--fork", "bad"]),
                ExitCode::FAILURE,
            ),
            (os_arguments(&["--unknown"]), ExitCode::FAILURE),
            (os_arguments(&["--help"]), ExitCode::SUCCESS),
        ] {
            let ParseOutcome::Exit(actual) = parse_arguments(&arguments) else {
                panic!("invalid options must exit");
            };
            assert_eq!(actual, expected);
        }

        assert!(owner_repo_shape("owner/repo"));
        for invalid in ["", "/repo", "owner/", "a/b/c", "owner/re po"] {
            assert!(
                !owner_repo_shape(invalid),
                "unexpected valid slug: {invalid}"
            );
        }
        assert!(repository_ref("owner/repo").is_ok());
        assert!(repository_ref("missing-slash").is_err());
        assert!(git_remote("origin").is_ok());
        assert!(git_remote("--bad").is_err());
        assert!(git_ref("refs/heads/main").is_ok());
        assert!(git_ref("bad ref").is_err());
        assert!(config_key("remote.origin.url").is_ok());
        assert!(config_key("invalid").is_err());
        assert!(path_from_git_bytes(b"/tmp/repository").is_ok());
        assert!(path_from_git_bytes(b"bad\0path").is_err());
    }

    #[test]
    #[cfg(unix)]
    fn parser_rejects_non_utf8_option_values() {
        use std::os::unix::ffi::OsStringExt as _;

        let arguments = vec![
            OsString::from("--upstream"),
            OsString::from_vec(vec![0xff]),
            OsString::from("--fork"),
            OsString::from("fork/repo"),
        ];
        assert!(matches!(
            parse_arguments(&arguments),
            ParseOutcome::Exit(code) if code == ExitCode::FAILURE
        ));
    }

    #[test]
    fn preflight_covers_clean_fetch_lock_and_refusal_paths() {
        let (repository, upstream, _) = local_fork_fixture(false);
        checked_git(
            &repository,
            &[
                "remote",
                "set-url",
                "origin",
                "https://github.com/upstream/repo.git",
            ],
        );
        let rewrite_key = format!("url.{}.insteadOf", upstream.display());
        checked_git_os(
            &repository,
            &[
                OsString::from("config"),
                OsString::from(rewrite_key),
                OsString::from("https://github.com/upstream/repo.git"),
            ],
        );
        let mut setup = context(repository.root(), &upstream, &upstream, false);
        let effects = GitEffects::new().expect("Git effects");
        phase_preflight(&mut setup, &effects).expect("clean preflight");
        assert_eq!(
            setup.classification,
            Some(RemoteClassification::OriginUpstreamOnly)
        );
        let common_dir = path_from_git_bytes(
            open_repository(repository.root())
                .expect("repository")
                .location()
                .common_dir
                .as_bytes(),
        )
        .expect("common directory");
        assert!(SetupLock::acquire(&common_dir).is_err());
        drop(setup.lock_guard.take());
        let reacquired = SetupLock::acquire(&common_dir).expect("released lock");
        drop(reacquired);

        let detached = fixture(GitFixture::Detached);
        let mut detached_setup = context(detached.root(), &upstream, &upstream, false);
        assert!(phase_preflight(&mut detached_setup, &effects).is_err());

        let unborn = fixture(GitFixture::Unborn);
        let mut unborn_setup = context(unborn.root(), &upstream, &upstream, false);
        assert!(phase_preflight(&mut unborn_setup, &effects).is_err());

        let invalid = fixture(GitFixture::Refs);
        checked_git(
            &invalid,
            &["remote", "add", "origin", "https://example.com/up/repo.git"],
        );
        let mut invalid_setup = context(invalid.root(), &upstream, &upstream, false);
        assert_error(
            phase_preflight(&mut invalid_setup, &effects),
            "not hosted on github.com",
        );

        let unrecognized = fixture(GitFixture::Refs);
        checked_git(&unrecognized, &["remote", "add", "origin", "not-a-url"]);
        let mut unrecognized_setup = context(unrecognized.root(), &upstream, &upstream, false);
        assert_error(
            phase_preflight(&mut unrecognized_setup, &effects),
            "not a recognized GitHub-compatible URL",
        );

        let duplicate = fixture(GitFixture::Refs);
        checked_git(
            &duplicate,
            &[
                "remote",
                "add",
                "origin",
                "https://github.com/upstream/repo.git",
            ],
        );
        checked_git(
            &duplicate,
            &[
                "config",
                "--add",
                "remote.origin.url",
                "git@github.com:upstream/repo.git",
            ],
        );
        let mut duplicate_setup = context(duplicate.root(), &upstream, &upstream, false);
        assert_error(
            phase_preflight(&mut duplicate_setup, &effects),
            "multiple remote.origin.url",
        );
    }

    #[test]
    fn local_mirror_rewrite_and_final_verification_cover_the_transaction() {
        let (repository, upstream, fork) = local_fork_fixture(true);
        let effects = GitEffects::new().expect("Git effects");
        let mut setup = context(repository.root(), &upstream, &fork, false);

        assert!(
            !handle_repository_lookup(&setup, &effects, RepositoryLookup::Missing)
                .expect("missing fork result")
        );
        assert_error(
            handle_repository_lookup(
                &setup,
                &effects,
                RepositoryLookup::Found(github_repository(None)),
            ),
            "fork parent mismatch",
        );
        assert_error(
            handle_repository_lookup(
                &setup,
                &effects,
                RepositoryLookup::Found(github_repository(Some("upstream/repo"))),
            ),
            "--mirror-confirmed",
        );

        setup.options.mirror_confirmed = true;
        assert!(
            handle_repository_lookup(
                &setup,
                &effects,
                RepositoryLookup::Found(github_repository(Some("upstream/repo"))),
            )
            .expect("confirmed mirror")
        );
        assert!(sync_fork(&setup, &effects).expect("already synchronized"));

        phase_remotes(&mut setup, &effects).expect("remote rewrite");
        phase_submodules(&setup, &effects).expect("submodule skip");
        phase_verify(&mut setup).expect("final verification");
        assert!(!setup.remote_phase_active);

        let final_repository = open_repository(repository.root()).expect("final repository");
        assert_eq!(
            config_text_values(&final_repository, "remote.upstream.pushurl").expect("push URL"),
            [DISABLED_PUSH_URL]
        );
        assert_eq!(
            remote_main_sha(
                &effects,
                repository.root(),
                &setup.fork_https().expect("fork URL")
            )
            .expect("fork main"),
            remote_main_sha(
                &effects,
                repository.root(),
                &setup.upstream_https().expect("upstream URL"),
            )
            .expect("upstream main")
        );
    }

    #[test]
    fn rollback_restores_the_exact_remote_snapshot() {
        let (repository, upstream, fork) = local_fork_fixture(false);
        let effects = GitEffects::new().expect("Git effects");
        let original =
            snapshot_remote_state(&open_repository(repository.root()).expect("initial repository"))
                .expect("initial snapshot");
        let mut setup = context(repository.root(), &upstream, &fork, false);
        phase_remotes(&mut setup, &effects).expect("remote rewrite");
        assert!(setup.remote_phase_active);
        rollback_remotes_if_active(&mut setup, &effects);
        assert!(!setup.remote_phase_active);
        assert_eq!(
            snapshot_remote_state(
                &open_repository(repository.root()).expect("restored repository")
            )
            .expect("restored snapshot"),
            original
        );
        rollback_remotes_if_active(&mut setup, &effects);
    }

    #[test]
    fn worktree_operation_remote_and_verification_refusals_are_explicit() {
        let dirty = fixture(GitFixture::Changes);
        let dirty_repository = open_repository(dirty.root()).expect("dirty repository");
        assert!(!all_worktrees_clean(&dirty_repository).expect("dirty status"));

        let clean = fixture(GitFixture::Refs);
        let clean_repository = open_repository(clean.root()).expect("clean repository");
        assert!(all_worktrees_clean(&clean_repository).expect("clean status"));
        assert!(no_operation_in_progress(&clean_repository).expect("no operation"));
        fs::write(clean.root().join(".git/MERGE_HEAD"), b"in progress\n")
            .expect("operation sentinel");
        assert!(!no_operation_in_progress(&clean_repository).expect("operation status"));

        let (repository, upstream, fork) = local_fork_fixture(false);
        let effects = GitEffects::new().expect("Git effects");
        let mut setup = context(repository.root(), &upstream, &fork, false);
        phase_remotes(&mut setup, &effects).expect("remote rewrite");
        checked_git(
            &repository,
            &["config", "--add", "remote.origin.pushurl", "blocked"],
        );
        assert!(phase_verify(&mut setup).is_err());
        checked_git(
            &repository,
            &["config", "--unset-all", "remote.origin.pushurl"],
        );
        checked_git(
            &repository,
            &[
                "remote",
                "add",
                "extra",
                "https://github.com/extra/repo.git",
            ],
        );
        assert!(phase_verify(&mut setup).is_err());
        checked_git(&repository, &["remote", "remove", "extra"]);
        checked_git(&repository, &["config", "branch.main.remote", "upstream"]);
        assert!(phase_verify(&mut setup).is_err());
        checked_git(&repository, &["config", "branch.main.remote", "origin"]);
        checked_git(
            &repository,
            &["config", "branch.main.merge", "refs/heads/other"],
        );
        assert!(phase_verify(&mut setup).is_err());
    }

    #[test]
    fn url_and_lock_helpers_cover_canonical_override_and_unknown_values() {
        let overrides = RepositoryUrlOverrides::from_reader(true, |name| Some(name.into()));
        assert_eq!(
            overrides.upstream_https.as_deref(),
            Some(OsStr::new("LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_HTTPS"))
        );
        assert_eq!(
            RepositoryUrlOverrides::from_reader(false, |_| Some("ignored".into())),
            RepositoryUrlOverrides::default()
        );
        let root = Path::new("/tmp/repository");
        let canonical = SetupContext {
            options: SetupOptions {
                upstream: "up/repo".to_owned(),
                fork: "fork/repo".to_owned(),
                mirror_confirmed: false,
                init_submodules: false,
            },
            root: root.to_path_buf(),
            urls: RepositoryUrlOverrides::default(),
            classification: None,
            snapshot: None,
            remote_undo: Vec::new(),
            remote_phase_active: false,
            lock_guard: None,
        };
        assert_eq!(
            canonical
                .upstream_https()
                .expect("canonical upstream")
                .as_os_str(),
            OsStr::new("https://github.com/up/repo.git")
        );
        assert_eq!(
            canonical.fork_ssh().expect("canonical fork").as_os_str(),
            OsStr::new("git@github.com:fork/repo.git")
        );
        assert!(SetupContext::url(Some(OsStr::new("")), "fallback".to_owned()).is_err());

        let temporary = tempfile::tempdir().expect("temporary directory");
        let holder = temporary.path().join("holder");
        assert_eq!(read_lock_holder(&holder), "unknown");
        fs::write(&holder, "\n").expect("empty holder");
        assert_eq!(read_lock_holder(&holder), "unknown");
        fs::write(&holder, "owner\n").expect("owned holder");
        assert_eq!(read_lock_holder(&holder), "owner");
    }

    #[test]
    fn setup_and_sync_refusal_branches_are_covered() {
        let effects = GitEffects::new().expect("Git effects");
        let (repository, upstream, fork) = local_fork_fixture(false);
        assert_eq!(
            setup_from(setup_options(), repository.root().join("missing").as_path()),
            ExitCode::FAILURE
        );
        let detached = fixture(GitFixture::Detached);
        assert_eq!(
            setup_from(setup_options(), detached.root()),
            ExitCode::FAILURE
        );

        let empty = repository.workspace_root().join("empty.git");
        checked_git_os(
            &repository,
            &[
                OsString::from("init"),
                OsString::from("--quiet"),
                OsString::from("--bare"),
                empty.as_os_str().to_owned(),
            ],
        );
        let missing_upstream = context(repository.root(), &empty, &fork, false);
        assert_error(sync_fork(&missing_upstream, &effects), "upstream has no");
        let missing_fork = context(repository.root(), &upstream, &empty, false);
        assert_error(sync_fork(&missing_fork, &effects), "fork has no");
    }

    #[test]
    fn additional_preflight_remote_and_submodule_branches_are_covered() {
        let effects = GitEffects::new().expect("Git effects");
        let (repository, upstream, fork) = local_fork_fixture(false);

        let ambiguous = fixture(GitFixture::Refs);
        checked_git(
            &ambiguous,
            &[
                "remote",
                "add",
                "origin",
                "https://github.com/upstream/repo.git",
            ],
        );
        checked_git(
            &ambiguous,
            &[
                "remote",
                "add",
                "extra",
                "https://github.com/other/repo.git",
            ],
        );
        let mut ambiguous_setup = context(ambiguous.root(), &upstream, &fork, false);
        assert_error(
            phase_preflight(&mut ambiguous_setup, &effects),
            "ambiguous remote state",
        );

        let dirty = fixture(GitFixture::Changes);
        let mut dirty_setup = context(dirty.root(), &upstream, &fork, false);
        assert_error(
            phase_preflight(&mut dirty_setup, &effects),
            "working tree is dirty",
        );
        let operation = fixture(GitFixture::Refs);
        fs::write(operation.root().join(".git/MERGE_HEAD"), b"in progress\n")
            .expect("operation sentinel");
        let mut operation_setup = context(operation.root(), &upstream, &fork, false);
        assert_error(
            phase_preflight(&mut operation_setup, &effects),
            "operation in progress",
        );

        let mut ambiguous_phase = context(repository.root(), &upstream, &fork, false);
        ambiguous_phase.classification = Some(RemoteClassification::Ambiguous);
        assert!(phase_remotes(&mut ambiguous_phase, &effects).is_err());

        add_remote(&repository, "mine", &fork);
        let mut named_phase = context(repository.root(), &upstream, &fork, false);
        named_phase.classification = Some(RemoteClassification::OriginUpstreamNamedFork(
            "mine".to_owned(),
        ));
        phase_remotes(&mut named_phase, &effects).expect("named fork rewrite");

        let mut rollback_without_snapshot = context(repository.root(), &upstream, &fork, false);
        rollback_without_snapshot.remote_phase_active = true;
        rollback_remotes_if_active(&mut rollback_without_snapshot, &effects);

        let multi = RemoteDescription {
            name: "origin".to_owned(),
            urls: vec!["one".to_owned(), "two".to_owned()],
            push_urls: Vec::new(),
        };
        assert!(!remote_matches(
            &multi,
            "fork/repo",
            &[GitUrl::new("one").expect("alias")]
        ));

        let missing_remote_error = effects
            .fetch(
                repository.root(),
                FetchRequest {
                    remote: git_remote("missing").expect("remote"),
                    refspec: None,
                    quiet: false,
                    no_tags: false,
                    mode: FetchMode::Standard,
                },
            )
            .expect_err("missing remote must fail");
        assert!(!git_error_detail(missing_remote_error).is_empty());
        let input_error = GitCliPolicy::new("relative").expect_err("relative policy");
        assert!(!git_error_detail(input_error).is_empty());

        let submodule = fixture(GitFixture::Submodule);
        let mut submodule_setup = context(submodule.root(), &upstream, &fork, false);
        submodule_setup.options.init_submodules = true;
        phase_submodules(&submodule_setup, &effects).expect("submodule update");
    }
}
