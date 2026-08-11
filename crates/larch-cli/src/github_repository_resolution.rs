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

use crate::github_service::{ServiceFailure, with_github_service};
use larch_adapters::GixRepository;
use larch_core::{
    GitHubIssueState, GitHubLabel, GitHubLabelCreate, GitHubRepositoryRef, GitHubService, Remote,
    RepositoryRead, SafeText,
};
use serde::Serialize;

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

/// Read one upstream agnix issue without exposing an arbitrary `gh` command.
pub fn agnix_issue(repository: &GitHubRepositoryRef, issue: u64) -> ExitCode {
    if issue == 0 {
        eprintln!("ERROR=issue number must be positive");
        return ExitCode::FAILURE;
    }
    let result = with_github_service(async |service, cancellation| {
        let issue = service
            .issue(repository, issue, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        let payload = AgnixIssuePayload {
            body: SafeText::from_untrusted(&issue.body).to_string(),
            state: match issue.state {
                GitHubIssueState::Open => "OPEN",
                GitHubIssueState::Closed => "CLOSED",
                GitHubIssueState::All => return Err("GitHub issue state is invalid".to_owned()),
            }
            .to_owned(),
            title: SafeText::from_untrusted(&issue.title).to_string(),
            url: SafeText::from_untrusted(&issue.url).to_string(),
        };
        serde_json::to_string(&payload).map_err(|_| "cannot serialize GitHub issue".to_owned())
    });
    match result {
        Ok(payload) => {
            println!("{payload}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR={}", SafeText::diagnostic(error.into_detail()));
            ExitCode::FAILURE
        }
    }
}

/// Idempotently provision the one optional agnix fork label.
pub fn agnix_ensure_label(repository: &GitHubRepositoryRef) -> ExitCode {
    let result = with_github_service(async |service, cancellation| {
        let labels = service
            .list_labels(repository, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        let Some(request) = agnix_label_request(repository, &labels) else {
            return Ok("PRESENT");
        };
        match service.create_label(&request, cancellation).await {
            Ok(_) => Ok("CREATED"),
            Err(create_error) => {
                let labels = service
                    .list_labels(repository, cancellation)
                    .await
                    .map_err(|_| create_error.to_string())?;
                if agnix_label_request(repository, &labels).is_none() {
                    Ok("PRESENT")
                } else {
                    Err(create_error.to_string())
                }
            }
        }
    });
    match result {
        Ok(status) => {
            println!("LABEL_STATUS={status}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR={}", SafeText::diagnostic(error.into_detail()));
            ExitCode::FAILURE
        }
    }
}

fn agnix_label_request(
    repository: &GitHubRepositoryRef,
    labels: &[GitHubLabel],
) -> Option<GitHubLabelCreate> {
    if labels
        .iter()
        .any(|label| label.name.eq_ignore_ascii_case("skip-changelog"))
    {
        None
    } else {
        Some(GitHubLabelCreate {
            repo: repository.clone(),
            name: "skip-changelog".to_owned(),
            color: "ededed".to_owned(),
            description: "PR does not require a CHANGELOG entry".to_owned(),
        })
    }
}

#[derive(Serialize)]
struct AgnixIssuePayload {
    body: String,
    state: String,
    title: String,
    url: String,
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

/// Resolve the ambient `OWNER/REPO` for the current working directory.
///
/// Same precedence as `gh resolve-repo`: GitHub repository metadata when the
/// service is reachable, else the validated `origin` remote. Returns `None`
/// when neither answers, so callers can report their own refusal.
#[must_use]
pub fn ambient_repo() -> Option<String> {
    let repository = open_cwd_repository();
    resolve_repo_detailed(repository.as_ref(), query_github_repository)
        .repo()
        .map(str::to_owned)
}

/// Resolve one configured remote of the current checkout to its `OWNER/REPO`.
///
/// Returns `None` when the checkout has no such remote or its URL does not name
/// a GitHub repository, which callers report as "no match" rather than as a
/// failure.
#[must_use]
pub fn remote_slug(remote: &str) -> Option<String> {
    match resolve_remote_repo(remote, open_cwd_repository().as_ref()) {
        RemoteRepoResult::Ok { repo } => Some(repo),
        RemoteRepoResult::Usage | RemoteRepoResult::ParseFailure => None,
    }
}

/// Return the fetch URL configured for one remote in `repository`.
#[must_use]
pub fn repository_remote_fetch_url(repository: &GixRepository, remote: &str) -> Option<String> {
    remote_fetch_url(repository, remote)
}

/// Parse an `OWNER/REPO` slug into a validated repository reference.
///
/// # Errors
/// Returns `()` for a slug without a separator or with an invalid component.
pub fn repository_ref(slug: &str) -> Result<GitHubRepositoryRef, ()> {
    parse_repository_ref(slug)
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

impl From<ServiceFailure> for PrimaryFailure {
    /// A client that could not be built is a setup failure; anything the built
    /// client refused is the service's own non-zero answer.
    fn from(failure: ServiceFailure) -> Self {
        let kind = match failure {
            ServiceFailure::Setup(_) => PrimaryFailureKind::Setup,
            ServiceFailure::Operation(_) => PrimaryFailureKind::NonZero,
        };
        Self {
            kind,
            detail: failure.into_detail(),
        }
    }
}

fn query_github_repository(reference: &GitHubRepositoryRef) -> Result<String, PrimaryFailure> {
    with_github_service(async |service, cancellation| {
        service
            .repository(reference, cancellation)
            .await
            .map(|repository| repository.name_with_owner)
            .map_err(|error| error.to_string())
    })
    .map_err(PrimaryFailure::from)
}

fn probe_service_setup() -> Result<(), PrimaryFailure> {
    with_github_service(async |_service, _cancellation| Ok(())).map_err(PrimaryFailure::from)
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

#[cfg(test)]
mod tests {
    use super::agnix_label_request;
    use larch_core::{GitHubLabel, GitHubRepositoryRef};

    #[test]
    fn absent_agnix_label_builds_the_exact_typed_create_request() {
        let repository = GitHubRepositoryRef::new("agent-sh", "agnix").expect("repository");
        let request = agnix_label_request(&repository, &[]).expect("missing label request");

        assert_eq!(request.repo, repository);
        assert_eq!(request.name, "skip-changelog");
        assert_eq!(request.color, "ededed");
        assert_eq!(request.description, "PR does not require a CHANGELOG entry");
    }

    #[test]
    fn existing_agnix_label_is_idempotent_even_when_case_differs() {
        let repository = GitHubRepositoryRef::new("agent-sh", "agnix").expect("repository");
        let labels = [GitHubLabel {
            id: 1,
            name: "Skip-Changelog".to_owned(),
            color: "ededed".to_owned(),
            description: String::new(),
        }];

        assert!(agnix_label_request(&repository, &labels).is_none());
    }
}
