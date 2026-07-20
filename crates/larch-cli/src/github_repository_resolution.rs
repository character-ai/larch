//! GitHub repository resolution commands: `gh remote-repo` and `gh resolve-repo`.
//!
//! Composes typed repository remotes from the gix read port with optional
//! GitHub repository metadata. Never shells out to `gh` or an untyped Git
//! subprocess.

use std::{
    env,
    io::{self, Write},
    process::ExitCode,
};

use larch_adapters::{
    GixRepository, TokioProcessRunner, github::OctocrabGitHubService, runtime::Cancellation,
    runtime::LarchRuntime,
};
use larch_core::{GitHubRepositoryRef, GitHubService, Remote, RepositoryRead};

const REMOTE_USAGE: &str = "Usage: github-remote-repo.sh <remote-name-or-url>";
const REMOTE_PARSE_ERROR: &str = "github-remote-repo.sh: cannot parse remote";
const RESOLVE_UNKNOWN: &str = "resolve-repo.sh: unknown argument:";
const RESOLVE_ERROR: &str = "ERROR=could not resolve repo (gh repo view + git remote both failed)";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RemoteRepoResult {
    Ok { repo: String },
    Usage,
    ParseFailure,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PrimaryFailureKind {
    NonZero,
    Setup,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PrimaryFailure {
    pub kind: PrimaryFailureKind,
    pub detail: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResolutionStatus {
    Valid,
    Invalid,
    Absent,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResolutionSource {
    Service,
    Origin,
    None,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RepoResolution {
    pub status: ResolutionStatus,
    pub source: ResolutionSource,
    pub candidate: String,
    pub primary_failure: Option<PrimaryFailure>,
}

impl RepoResolution {
    #[must_use]
    pub const fn repo(&self) -> Option<&str> {
        match self.status {
            ResolutionStatus::Valid => Some(self.candidate.as_str()),
            ResolutionStatus::Invalid | ResolutionStatus::Absent => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResolveRepoResult {
    Ok { repo: String },
    UnknownArgument { argument: String },
    Unresolved,
}

pub fn run_remote_repo(args: &[String]) -> ExitCode {
    let result = match args {
        [remote_or_url] => resolve_remote_repo(remote_or_url, open_cwd_repository().as_ref()),
        _ => RemoteRepoResult::Usage,
    };
    ExitCode::from(emit_remote_repo(result))
}

pub fn run_resolve_repo(args: &[String]) -> ExitCode {
    ExitCode::from(emit_resolve_repo(resolve_repo_command(args)))
}

fn emit_remote_repo(result: RemoteRepoResult) -> u8 {
    match result {
        RemoteRepoResult::Ok { repo } => {
            println!("{repo}");
            0
        }
        RemoteRepoResult::Usage => {
            let _ = writeln!(io::stderr(), "{REMOTE_USAGE}");
            2
        }
        RemoteRepoResult::ParseFailure => {
            let _ = writeln!(io::stderr(), "{REMOTE_PARSE_ERROR}");
            2
        }
    }
}

fn emit_resolve_repo(result: ResolveRepoResult) -> u8 {
    match result {
        ResolveRepoResult::Ok { repo } => {
            println!("{repo}");
            0
        }
        ResolveRepoResult::UnknownArgument { argument } => {
            let _ = writeln!(io::stderr(), "{RESOLVE_UNKNOWN} {argument}");
            1
        }
        ResolveRepoResult::Unresolved => {
            let _ = writeln!(io::stderr(), "{RESOLVE_ERROR}");
            1
        }
    }
}

fn resolve_repo_command(args: &[String]) -> ResolveRepoResult {
    if let Some(argument) = args.first() {
        return ResolveRepoResult::UnknownArgument {
            argument: argument.clone(),
        };
    }
    let repository = open_cwd_repository();
    let detailed = resolve_repo_detailed(repository.as_ref(), query_github_repository);
    detailed
        .repo()
        .map_or(ResolveRepoResult::Unresolved, |repo| {
            ResolveRepoResult::Ok {
                repo: repo.to_owned(),
            }
        })
}

/// Parse a remote name or URL into `OWNER/REPO`, matching the Python contract.
#[must_use]
pub fn resolve_remote_repo(
    remote_or_url: &str,
    repository: Option<&GixRepository>,
) -> RemoteRepoResult {
    let url = if looks_like_url(remote_or_url) {
        remote_or_url.to_owned()
    } else {
        let Some(repo) = repository else {
            return RemoteRepoResult::ParseFailure;
        };
        match remote_fetch_url(repo, remote_or_url) {
            Some(url) => url,
            None => return RemoteRepoResult::ParseFailure,
        }
    };
    parse_github_remote_url(&url).map_or(RemoteRepoResult::ParseFailure, |repo| {
        RemoteRepoResult::Ok { repo }
    })
}

/// Ambient repository discovery with service-first precedence and origin fallback.
#[must_use]
pub fn resolve_repo_detailed<F>(
    repository: Option<&GixRepository>,
    service_query: F,
) -> RepoResolution
where
    F: FnMut(&GitHubRepositoryRef) -> Result<String, PrimaryFailure>,
{
    let (origin_candidate, origin_valid) = origin_repo_candidate(repository);
    resolve_from_origin_candidate(origin_candidate, origin_valid, service_query)
}

/// Shared precedence: service metadata when reachable, else validated origin.
#[must_use]
pub fn resolve_from_origin_candidate<F>(
    origin_candidate: String,
    origin_valid: bool,
    mut service_query: F,
) -> RepoResolution
where
    F: FnMut(&GitHubRepositoryRef) -> Result<String, PrimaryFailure>,
{
    let mut primary_failure: Option<PrimaryFailure> = None;
    let mut primary_invalid = String::new();

    if origin_valid {
        if let Ok(reference) = parse_repository_ref(&origin_candidate) {
            match service_query(&reference) {
                Ok(name_with_owner) => {
                    let candidate = name_with_owner.trim().to_owned();
                    if validate_repo_slug(&candidate) {
                        return RepoResolution {
                            status: ResolutionStatus::Valid,
                            source: ResolutionSource::Service,
                            candidate,
                            primary_failure: None,
                        };
                    }
                    if !candidate.is_empty() {
                        primary_invalid = candidate;
                        primary_failure = Some(PrimaryFailure {
                            kind: PrimaryFailureKind::NonZero,
                            detail: "GitHub repository metadata returned an invalid slug"
                                .to_owned(),
                        });
                    }
                }
                Err(failure) => primary_failure = Some(failure),
            }
        }
    } else if origin_candidate.is_empty() {
        primary_failure = probe_service_setup().err();
    }

    if origin_valid && !origin_candidate.is_empty() {
        return RepoResolution {
            status: ResolutionStatus::Valid,
            source: ResolutionSource::Origin,
            candidate: origin_candidate,
            primary_failure,
        };
    }
    if !origin_candidate.is_empty() {
        return RepoResolution {
            status: ResolutionStatus::Invalid,
            source: ResolutionSource::Origin,
            candidate: origin_candidate,
            primary_failure,
        };
    }
    if !primary_invalid.is_empty() {
        return RepoResolution {
            status: ResolutionStatus::Invalid,
            source: ResolutionSource::Service,
            candidate: primary_invalid,
            primary_failure,
        };
    }
    RepoResolution {
        status: ResolutionStatus::Absent,
        source: ResolutionSource::None,
        candidate: String::new(),
        primary_failure,
    }
}

fn query_github_repository(reference: &GitHubRepositoryRef) -> Result<String, PrimaryFailure> {
    let working_directory = env::current_dir().map_err(|error| PrimaryFailure {
        kind: PrimaryFailureKind::Setup,
        detail: format!("cannot resolve current directory: {error}"),
    })?;
    let runtime = LarchRuntime::new().map_err(|error| PrimaryFailure {
        kind: PrimaryFailureKind::Setup,
        detail: format!("cannot initialize larch runtime: {error}"),
    })?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        let service = OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation)
            .await
            .map_err(|error| PrimaryFailure {
                kind: PrimaryFailureKind::Setup,
                detail: error.to_string(),
            })?;
        match service.repository(reference, &cancellation).await {
            Ok(repository) => Ok(repository.name_with_owner),
            Err(error) => Err(PrimaryFailure {
                kind: PrimaryFailureKind::NonZero,
                detail: error.to_string(),
            }),
        }
    })
}

fn probe_service_setup() -> Result<(), PrimaryFailure> {
    let working_directory = env::current_dir().map_err(|error| PrimaryFailure {
        kind: PrimaryFailureKind::Setup,
        detail: format!("cannot resolve current directory: {error}"),
    })?;
    let runtime = LarchRuntime::new().map_err(|error| PrimaryFailure {
        kind: PrimaryFailureKind::Setup,
        detail: format!("cannot initialize larch runtime: {error}"),
    })?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation)
            .await
            .map(|_| ())
            .map_err(|error| PrimaryFailure {
                kind: PrimaryFailureKind::Setup,
                detail: error.to_string(),
            })
    })
}

fn origin_repo_candidate(repository: Option<&GixRepository>) -> (String, bool) {
    let Some(repository) = repository else {
        return (String::new(), false);
    };
    let Some(url) = remote_fetch_url(repository, "origin") else {
        return (String::new(), false);
    };
    candidate_from_remote_url(&url)
}

fn candidate_from_remote_url(url: &str) -> (String, bool) {
    if let Some(parsed) = parse_github_remote_url(url)
        && validate_repo_slug(&parsed)
    {
        return (parsed, true);
    }
    let raw = raw_remote_path_candidate(url);
    if raw.is_empty() {
        (url.to_owned(), false)
    } else {
        (raw, false)
    }
}

fn remote_fetch_url(repository: &GixRepository, name: &str) -> Option<String> {
    let remotes = repository.remotes().ok()?;
    remotes
        .into_iter()
        .find(|remote| remote_name_eq(remote, name))
        .and_then(|remote| remote.fetch_url)
        .and_then(|bytes| String::from_utf8(bytes).ok())
        .map(|url| url.trim().to_owned())
        .filter(|url| !url.is_empty())
}

fn remote_name_eq(remote: &Remote, name: &str) -> bool {
    remote.name == name.as_bytes()
}

fn looks_like_url(value: &str) -> bool {
    value.contains("://") || value.contains('@')
}

/// Parse a GitHub remote URL into `OWNER/REPO`.
#[must_use]
pub fn parse_github_remote_url(url: &str) -> Option<String> {
    let normalized = normalize_remote_url(url);
    if let Some(repo) = parse_scp_github(&normalized) {
        return Some(repo);
    }
    parse_scheme_github(&normalized)
}

fn normalize_remote_url(url: &str) -> String {
    let mut text = url.trim().trim_end_matches('/').to_owned();
    if let Some(stripped) = text.strip_suffix(".git") {
        text = stripped.trim_end_matches('/').to_owned();
    }
    text
}

fn parse_scp_github(url: &str) -> Option<String> {
    let rest = url.strip_prefix("git@github.com:")?;
    split_owner_repo(rest)
}

fn parse_scheme_github(url: &str) -> Option<String> {
    let rest = url
        .strip_prefix("https://")
        .or_else(|| url.strip_prefix("http://"))
        .or_else(|| url.strip_prefix("ssh://"))
        .or_else(|| url.strip_prefix("git://"))?;
    let after_auth = match rest.split_once('@') {
        Some((_user, host_path)) => host_path,
        None => rest,
    };
    let path = after_auth.strip_prefix("github.com/")?;
    split_owner_repo(path)
}

fn split_owner_repo(path: &str) -> Option<String> {
    let (owner, repo) = path.split_once('/')?;
    if repo.contains('/') {
        return None;
    }
    if !is_slug_part(owner) || !is_slug_part(repo) {
        return None;
    }
    Some(format!("{owner}/{repo}"))
}

fn raw_remote_path_candidate(url: &str) -> String {
    let text = normalize_remote_url(url);
    if text.is_empty() {
        return String::new();
    }
    if let Some(path) = scp_path(&text) {
        return path.trim_start_matches('/').to_owned();
    }
    if let Some(path) = scheme_path(&text) {
        return path.trim_start_matches('/').to_owned();
    }
    text
}

fn scp_path(text: &str) -> Option<String> {
    let (_user_host, path) = text.split_once('@')?;
    if path.contains(' ') || !path.contains(':') {
        return None;
    }
    let (_host, path) = path.split_once(':')?;
    Some(path.to_owned())
}

fn scheme_path(text: &str) -> Option<String> {
    let rest = text
        .strip_prefix("https://")
        .or_else(|| text.strip_prefix("http://"))
        .or_else(|| text.strip_prefix("ssh://"))
        .or_else(|| text.strip_prefix("git://"))?;
    let after_auth = match rest.split_once('@') {
        Some((_user, host_path)) => host_path,
        None => rest,
    };
    let (_host, path) = after_auth.split_once('/')?;
    Some(path.to_owned())
}

/// Validate an `OWNER/REPO` slug against the Python CLI contract.
#[must_use]
pub fn validate_repo_slug(value: &str) -> bool {
    if value.is_empty() || value.contains('\n') || value.contains('\r') {
        return false;
    }
    if value.starts_with("--")
        || value.starts_with('/')
        || value.contains("../")
        || value.contains('\\')
    {
        return false;
    }
    let Some((owner, repo)) = value.split_once('/') else {
        return false;
    };
    if repo.contains('/') || owner == "." || owner == ".." || repo == "." || repo == ".." {
        return false;
    }
    is_slug_part(owner) && is_slug_part(repo)
}

fn is_slug_part(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

fn parse_repository_ref(slug: &str) -> Result<GitHubRepositoryRef, ()> {
    let (owner, name) = slug.split_once('/').ok_or(())?;
    GitHubRepositoryRef::new(owner, name).map_err(|_| ())
}

fn open_cwd_repository() -> Option<GixRepository> {
    let cwd = env::current_dir().ok()?;
    GixRepository::discover(cwd).ok()
}
