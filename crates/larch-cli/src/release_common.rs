use std::{env, process::ExitCode};

use larch_adapters::{
    FetchRequest, GitCli, GitCliPolicy, GitRef, GitRefspec, GitRemote, GixRepository,
    LsRemoteRequest, PushRequest, TokioProcessRunner,
    github::{
        OctocrabGitHubService, OctocrabReleaseTransport, ReleaseCandidatePullRequest,
        ReleaseCandidatePullRequestState, ReleaseOperations, RepoSlug,
    },
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{GitPath, ObjectId, ReleaseTag, RepositoryRead, Revision, SafeText};

use crate::{git_command_runtime::GitCommandRuntime, github_repository_resolution};

pub struct ProductionReleaseServices {
    pub(crate) runtime: LarchRuntime,
    pub(crate) cancellation: Cancellation,
    pub(crate) github: OctocrabGitHubService,
    pub(crate) repository: GixRepository,
    git_policy: GitCliPolicy,
    runner: TokioProcessRunner,
}

/// Resolve the commit GitHub recorded for a merged release PR.
///
/// A squash merge deliberately gives this commit a different identity from the
/// candidate branch head. Every authoritative release operation must therefore
/// use this value, not `head_oid`.
pub fn merged_release_commit(pull_request: &ReleaseCandidatePullRequest) -> Result<&str, String> {
    if pull_request.state != ReleaseCandidatePullRequestState::Merged {
        return Err("release candidate PR is not merged".to_owned());
    }
    pull_request
        .merge_commit_oid
        .as_deref()
        .ok_or_else(|| "merged release candidate PR has no merge commit".to_owned())
}

/// Common read-only operations required to verify a post-merge release commit.
///
/// Both staging and publication must prove their candidate against the same
/// GitHub merge record and freshly fetched default branch.
pub trait PostMergeReleaseServices {
    fn origin_repo(&self) -> Result<String, String>;
    fn fetch_main(&self) -> Result<(), String>;
    fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String>;
    fn is_ancestor(&self, ancestor: &str, descendant: &str) -> Result<bool, String>;
    fn plugin_version_at(&self, revision: &str) -> Result<String, String>;
}

impl ProductionReleaseServices {
    pub fn new() -> Result<Self, String> {
        let cwd = env::current_dir().map_err(|error| error.to_string())?;
        let repository = GixRepository::discover(&cwd).map_err(|error| error.to_string())?;
        let git = GitCommandRuntime::for_repository(&cwd)?;
        let github = git
            .runtime
            .block_on(OctocrabGitHubService::from_gh(
                &git.runner,
                &cwd,
                &git.cancellation,
            ))
            .map_err(|error| error.to_string())?;
        let GitCommandRuntime {
            runtime,
            cancellation,
            policy: git_policy,
            runner,
        } = git;
        Ok(Self {
            runtime,
            cancellation,
            github,
            repository,
            git_policy,
            runner,
        })
    }

    pub fn origin_repo(&self) -> Result<String, String> {
        match github_repository_resolution::resolve_remote_repo("origin", Some(&self.repository)) {
            github_repository_resolution::RemoteRepoResult::Ok { repo } => Ok(repo),
            _ => Err("origin repository could not be resolved".to_owned()),
        }
    }

    /// Fetch the current default branch before inspecting a post-merge commit.
    pub fn fetch_origin_main(&self) -> Result<(), String> {
        self.runtime
            .block_on(
                self.git_cli()
                    .fetch(main_fetch_request()?, &self.cancellation),
            )
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    /// Return whether an ancestor is reachable from a descendant.
    pub fn commit_is_ancestor(&self, ancestor: &str, descendant: &str) -> Result<bool, String> {
        is_ancestor(&self.repository, ancestor, descendant)
    }

    pub fn git_cli(&self) -> GitCli<'_, TokioProcessRunner> {
        GitCli::new(&self.runner, self.git_policy.clone())
    }

    pub fn object_id(&self, oid: &str) -> Result<ObjectId, String> {
        self.repository
            .resolve_revision(&larch_core::Revision::new(oid.as_bytes()))
            .map_err(|error| error.to_string())
    }

    pub fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String> {
        self.runtime
            .block_on(self.github.release_candidate_pull_request(
                &self.cancellation,
                repo.owner(),
                repo.repo(),
                number,
            ))
            .map_err(|error| error.to_string())
    }

    pub fn release_operations<T>(
        &self,
        run: impl FnOnce(ReleaseOperations<'_, OctocrabReleaseTransport<'_>>, RepoSlug) -> T,
        repo: &RepoSlug,
    ) -> T {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        run(ReleaseOperations::new(&transport), repo.clone())
    }

    /// Read `origin`'s advertised refs for the given fully qualified patterns.
    ///
    /// Returns the raw `git ls-remote` text so each caller can apply the
    /// selection its ref kind needs: tags peel, branches do not.
    ///
    /// # Errors
    /// Returns a message when the remote read fails or is not UTF-8.
    pub fn origin_refs(&self, patterns: &[String]) -> Result<String, String> {
        let patterns = patterns
            .iter()
            .map(|pattern| GitRef::new(pattern).map_err(|error| error.to_string()))
            .collect::<Result<Vec<_>, _>>()?;
        let result = self
            .runtime
            .block_on(self.git_cli().ls_remote(
                LsRemoteRequest {
                    remote: larch_adapters::GitLsRemoteTarget::Configured(origin()?),
                    patterns,
                    heads: false,
                    exit_code: false,
                },
                &self.cancellation,
            ))
            .map_err(|error| error.to_string())?;
        String::from_utf8(result.output().stdout().to_vec())
            .map_err(|_| "remote ref read returned non-UTF-8 output".to_owned())
    }

    /// Push one refspec to `origin` with no force and no lease.
    ///
    /// Git itself rejects a non-fast-forward update, so every caller inherits
    /// forward-only semantics for the destination ref.
    ///
    /// # Errors
    /// Returns a message when the refspec is unsafe or the push fails.
    pub fn push_origin_ref(&self, refspec: &str) -> Result<(), String> {
        let request = PushRequest {
            remote: larch_adapters::GitPushTarget::Configured(origin()?),
            refspecs: vec![GitRefspec::new(refspec).map_err(|error| error.to_string())?],
            force_with_lease: None,
            set_upstream: false,
            prune: false,
        };
        self.runtime
            .block_on(self.git_cli().push(request, &self.cancellation))
            .map(|_| ())
            .map_err(|error| error.to_string())
    }
}

impl PostMergeReleaseServices for ProductionReleaseServices {
    fn origin_repo(&self) -> Result<String, String> {
        Self::origin_repo(self)
    }

    fn fetch_main(&self) -> Result<(), String> {
        self.fetch_origin_main()
    }

    fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String> {
        Self::pull_request(self, repo, number)
    }

    fn is_ancestor(&self, ancestor: &str, descendant: &str) -> Result<bool, String> {
        self.commit_is_ancestor(ancestor, descendant)
    }

    fn plugin_version_at(&self, revision: &str) -> Result<String, String> {
        plugin_version_at(&self.repository, revision)
    }
}

fn origin() -> Result<GitRemote, String> {
    GitRemote::new("origin").map_err(|error| error.to_string())
}

pub fn main_fetch_request() -> Result<FetchRequest, String> {
    Ok(FetchRequest {
        remote: origin()?,
        refspec: Some(
            GitRefspec::new("refs/heads/main:refs/remotes/origin/main")
                .map_err(|error| error.to_string())?,
        ),
        quiet: true,
        no_tags: false,
        mode: larch_adapters::FetchMode::Standard,
    })
}

pub fn is_ancestor(
    repository: &GixRepository,
    ancestor: &str,
    descendant: &str,
) -> Result<bool, String> {
    let ancestor = repository
        .resolve_revision(&Revision::new(ancestor.as_bytes()))
        .map_err(|error| error.to_string())?;
    let descendant = repository
        .resolve_revision(&Revision::new(descendant.as_bytes()))
        .map_err(|error| error.to_string())?;
    repository
        .is_ancestor(&ancestor, &descendant)
        .map_err(|error| error.to_string())
}

pub fn plugin_version_at(repository: &GixRepository, oid: &str) -> Result<String, String> {
    let id = repository
        .resolve_revision(&Revision::new(oid.as_bytes()))
        .map_err(|error| error.to_string())?;
    let bytes = repository
        .blob_at_commit(&id, &GitPath::new(b".claude-plugin/plugin.json".to_vec()))
        .map_err(|error| error.to_string())?
        .ok_or_else(|| format!("plugin.json read at {oid} failed: file is missing"))?;
    let value: serde_json::Value = serde_json::from_slice(&bytes)
        .map_err(|_| format!("plugin.json at {oid} is invalid JSON"))?;
    value
        .get("version")
        .and_then(serde_json::Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| format!("plugin.json at {oid} has no version"))
}

pub fn command<S, T>(
    services: Result<S, String>,
    run: impl FnOnce(&S) -> Result<T, String>,
    success: impl FnOnce(T),
) -> ExitCode {
    match services.and_then(|services| run(&services)) {
        Ok(value) => {
            success(value);
            ExitCode::SUCCESS
        }
        Err(error) => error_exit(error),
    }
}

pub fn exit(result: Result<(), String>) -> ExitCode {
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => error_exit(error),
    }
}

fn error_exit(error: String) -> ExitCode {
    eprintln!("ERROR={}", SafeText::from_untrusted(error));
    ExitCode::FAILURE
}

pub fn release_tag(version: &str) -> Option<String> {
    let tag = format!("v{version}");
    ReleaseTag::parse(&tag).ok().map(|_| tag)
}

pub fn parse_pr(value: &str) -> Option<u64> {
    value
        .parse::<u64>()
        .ok()
        .filter(|number| *number != 0 && value.bytes().all(|byte| byte.is_ascii_digit()))
}

pub fn repo_slug(repo: &str) -> Option<RepoSlug> {
    let (owner, name) = repo.split_once('/')?;
    (!name.contains('/'))
        .then(|| RepoSlug::parse(owner, name).ok())
        .flatten()
}

pub fn semver(value: &str) -> Option<(u64, u64, u64)> {
    let mut parts = value.split('.');
    let major = parts.next()?.parse().ok()?;
    let minor = parts.next()?.parse().ok()?;
    let patch = parts.next()?.parse().ok()?;
    (parts.next().is_none()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || byte == b'.'))
    .then_some((major, minor, patch))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn command_and_exit_preserve_success_and_failure_classes() {
        let mut published = None;
        assert_eq!(
            command(
                Ok::<_, String>(7),
                |value| Ok(value + 1),
                |value| {
                    published = Some(value);
                }
            ),
            ExitCode::SUCCESS
        );
        assert_eq!(published, Some(8));

        assert_eq!(
            command::<(), _>(
                Err("service unavailable\nwith detail".to_owned()),
                |()| Ok(()),
                |()| {}
            ),
            ExitCode::FAILURE
        );
        assert_eq!(exit(Ok(())), ExitCode::SUCCESS);
        assert_eq!(exit(Err("operation failed".to_owned())), ExitCode::FAILURE);
    }

    #[test]
    fn release_identity_parsers_accept_only_the_shared_contract() {
        assert_eq!(release_tag("1.2.3"), Some("v1.2.3".to_owned()));
        assert_eq!(release_tag("01.2.3"), None);
        assert_eq!(parse_pr("42"), Some(42));
        assert_eq!(parse_pr("0"), None);
        assert_eq!(parse_pr("+42"), None);

        let repo = repo_slug("character-ai/larch").expect("repository slug");
        assert_eq!(repo.owner(), "character-ai");
        assert_eq!(repo.repo(), "larch");
        assert_eq!(repo_slug("character-ai/larch/extra"), None);

        assert_eq!(semver("1.2.3"), Some((1, 2, 3)));
        assert_eq!(semver("1.2.3.4"), None);
        assert_eq!(semver("1.2.x"), None);
    }
}
