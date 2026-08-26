//! Checked draft-release staging and validation over typed Git and GitHub ports.
//!
//! After `release stage` emits `SOURCE_COMMIT`, the release skill runs
//! `release reconcile-notes` over `baseline..SOURCE_COMMIT` so mid-run merges
//! are appended to the still-mutable draft body before validate/finish.

use std::{collections::BTreeSet, env, fs, path::Path, process::ExitCode, time::Duration};

use larch_adapters::{
    AddRequest, CommitMessage, CommitRequest, FetchMode, FetchRequest, GitCli, GitCliPolicy,
    GitRef, GitRefspec, GitRemote, GixRepository, MergeRequest, RepositoryRoot, SecureTempDir,
    TagMutationRequest, TemporaryRoot, TokioProcessRunner, WorktreePath, WorktreeRequest,
    clock::TokioClock,
    github::{
        AttestationOperations, DraftReleaseInput, OctocrabAttestationTransport,
        OctocrabReleaseTransport, ReleaseOperations, RepoSlug,
    },
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ArtifactAttestationRequest, AsyncClock, GitHubActionsService, GitHubRepositoryRef, GitPath,
    ReleaseAssetSubject, ReleaseSourceCommit, ReleaseState, ReleaseTag, RepositoryErrorKind,
    RepositoryRead, Revision, SafeText, WorkflowRun, WorkflowRunFilters, emit_kv,
    resolve_tag_object_id,
};

use crate::{
    git_command_runtime::exact_name_only_request, release_assets, release_common,
    release_plugin_runtime,
};

const ASSET_WORKFLOW: &str = "rust-release-assets.yaml";
const ASSET_RUN_REGISTRATION_TIMEOUT: Duration = Duration::from_secs(60);
const ASSET_RUN_POLL_INTERVAL: Duration = Duration::from_secs(5);
const ASSET_RUN_NOT_REGISTERED: &str = "tag-triggered asset workflow run is not registered";
const ASSET_RUN_WAIT_CANCELLED: &str = "asset workflow run registration wait cancelled";
const ORIGIN_MAIN: &str = "origin/main";

pub fn ensure_policy(repo: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| ensure_policy_with(services, repo),
        |()| {
            emit_kv("IMMUTABLE_RELEASES_ENABLED", "true");
        },
    )
}

pub fn stage(version: &str, notes_file: &Path, repo: &str, pr: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| stage_with(services, version, notes_file, repo, pr),
        |staged| {
            emit_kv("TAG", &format!("v{version}"));
            emit_kv("SOURCE_COMMIT", &staged.source_commit);
            emit_kv("RELEASE_COMMIT", &staged.release_commit);
            emit_kv("RELEASE_SOURCE_COMMIT", &staged.source_commit);
            emit_kv("DRAFT_READY", "true");
        },
    )
}

pub fn asset_run(repo: &str, tag: &str, source_commit: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| asset_run_with(services, repo, tag, source_commit),
        |run| {
            emit_kv("ASSET_RUN_ID", &run.database_id.to_string());
            emit_kv(
                "ASSET_RUN_URL",
                &format!("https://github.com/{repo}/actions/runs/{}", run.database_id),
            );
        },
    )
}

pub fn validate_draft(version: &str, repo: &str, pr: &str, source_commit: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| validate_candidate_with(services, version, repo, pr, source_commit, true),
        |_| {
            emit_kv("TAG", &format!("v{version}"));
            emit_kv("SOURCE_COMMIT", source_commit);
            emit_kv("DRAFT_ASSETS_VALID", "true");
        },
    )
}

pub fn validate_candidate_assets(
    version: &str,
    repo: &str,
    pr: &str,
    source_commit: &str,
    require_draft: bool,
) -> Result<ReleaseState, String> {
    ProductionServices::new().and_then(|services| {
        validate_candidate_with(&services, version, repo, pr, source_commit, require_draft)
    })
}

trait Services: release_common::PostMergeReleaseServices {
    fn ensure_policy(&self, repo: &RepoSlug) -> Result<(), String>;
    fn verify_policy(&self, repo: &RepoSlug) -> Result<(), String>;
    fn candidate_license(&self, oid: &str) -> Result<Vec<u8>, String>;
    fn remote_tag(&self, repo: &RepoSlug, tag: &str) -> Result<Option<String>, String>;
    fn local_tag(&self, tag: &str) -> Result<Option<String>, String>;
    fn create_local_tag(&self, tag: &str, oid: &str) -> Result<(), String>;
    fn push_tag(&self, tag: &str) -> Result<(), String>;
    /// Fetch a tag ref from origin so a remote-only commit resolves locally.
    fn fetch_tag(&self, tag: &str) -> Result<(), String>;
    /// Resolve `origin/stable`, returning `Ok(None)` when the branch is absent.
    fn resolve_origin_stable(&self) -> Result<Option<String>, String>;
    /// Build the projection commit off `source_commit` with `stable_oid` as its
    /// second parent, returning the new commit OID.
    fn build_projection_commit(
        &self,
        source_commit: &str,
        stable_oid: &str,
        version: &str,
    ) -> Result<String, String>;
    /// Return `(parents, tree)` of `oid` as hex strings.
    fn commit_parents_and_tree(&self, oid: &str) -> Result<(Vec<String>, String), String>;
    /// Return the paths that differ between `base` and `head`.
    fn changed_paths(&self, base: &str, head: &str) -> Result<Vec<String>, String>;
    /// Read the projected `plugin/.claude-plugin/plugin.json` version at `oid`.
    fn projected_plugin_version(&self, oid: &str) -> Result<String, String>;
    fn staged_release(
        &self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> Result<Option<ReleaseState>, String>;
    fn release(&self, repo: &RepoSlug, tag: &str) -> Result<Option<ReleaseState>, String>;
    fn create_draft(
        &self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, String>;
    fn update_draft(
        &self,
        repo: &RepoSlug,
        release: &ReleaseState,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, String>;
    fn workflow_runs(
        &self,
        repo: &GitHubRepositoryRef,
        filters: &WorkflowRunFilters,
    ) -> Result<Vec<WorkflowRun>, String>;
    fn wait_for_asset_run_poll(&self, duration: Duration) -> Result<(), String>;
    fn download_asset(&self, repo: &RepoSlug, asset_id: u64, size: u64) -> Result<Vec<u8>, String>;
    fn verify_artifact(&self, request: &ArtifactAttestationRequest) -> Result<(), String>;
}

type ProductionServices = release_common::ProductionReleaseServices;

impl Services for ProductionServices {
    fn ensure_policy(&self, repo: &RepoSlug) -> Result<(), String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        let enabled = self
            .runtime
            .block_on(ReleaseOperations::new(&transport).verify_repository_policy(repo))
            .map_err(|error| error.to_string())?;
        if enabled {
            Ok(())
        } else {
            Err("immutable releases are not enabled".to_owned())
        }
    }

    fn verify_policy(&self, repo: &RepoSlug) -> Result<(), String> {
        self.ensure_policy(repo)
    }

    fn candidate_license(&self, oid: &str) -> Result<Vec<u8>, String> {
        let id = self.object_id(oid)?;
        self.repository
            .blob_at_commit(&id, &GitPath::new(b"LICENSE".to_vec()))
            .map_err(|error| error.to_string())?
            .ok_or_else(|| "candidate LICENSE read failed: file is missing".to_owned())
    }

    fn remote_tag(&self, _repo: &RepoSlug, tag: &str) -> Result<Option<String>, String> {
        let direct = format!("refs/tags/{tag}");
        let peeled = format!("{direct}^{{}}");
        let output = self.origin_refs(&[direct.clone(), peeled.clone()])?;
        let mut direct_oid = None;
        let mut peeled_oid = None;
        for line in output.lines() {
            let mut fields = line.split_ascii_whitespace();
            let oid = fields.next();
            let reference = fields.next();
            if fields.next().is_some() {
                continue;
            }
            match (oid, reference) {
                (Some(oid), Some(reference)) if reference == direct => direct_oid = Some(oid),
                (Some(oid), Some(reference)) if reference == peeled => peeled_oid = Some(oid),
                _ => {}
            }
        }
        resolve_tag_object_id(direct_oid, peeled_oid)
            .map(|oid| oid.map(|value| value.as_str().to_owned()))
            .map_err(|error| error.to_string())
    }

    fn local_tag(&self, tag: &str) -> Result<Option<String>, String> {
        let revision = Revision::new(format!("{tag}^{{commit}}").into_bytes());
        match self.repository.resolve_revision(&revision) {
            Ok(oid) => Ok(Some(oid.to_hex())),
            Err(error) if error.kind() == RepositoryErrorKind::RevisionNotFound => Ok(None),
            Err(error) => Err(error.to_string()),
        }
    }

    fn create_local_tag(&self, tag: &str, oid: &str) -> Result<(), String> {
        let request = TagMutationRequest::Create {
            force: false,
            name: GitRef::new(tag).map_err(|error| error.to_string())?,
            target: Some(GitRef::new(oid).map_err(|error| error.to_string())?),
            message: None,
        };
        self.runtime
            .block_on(self.git_cli().tag_mutation(request, &self.cancellation))
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    fn push_tag(&self, tag: &str) -> Result<(), String> {
        let reference = format!("refs/tags/{tag}");
        self.push_origin_ref(&format!("{reference}:{reference}"))
    }

    fn fetch_tag(&self, tag: &str) -> Result<(), String> {
        let reference = format!("refs/tags/{tag}");
        let request = FetchRequest {
            remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
            refspec: Some(
                GitRefspec::new(format!("{reference}:{reference}"))
                    .map_err(|error| error.to_string())?,
            ),
            quiet: true,
            no_tags: true,
            mode: FetchMode::Standard,
        };
        self.runtime
            .block_on(self.git_cli().fetch(request, &self.cancellation))
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    fn resolve_origin_stable(&self) -> Result<Option<String>, String> {
        let request = FetchRequest {
            remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
            refspec: Some(
                GitRefspec::new("refs/heads/stable:refs/remotes/origin/stable")
                    .map_err(|error| error.to_string())?,
            ),
            quiet: true,
            no_tags: true,
            mode: FetchMode::Standard,
        };
        // A missing `stable` branch fails the fetch of `refs/heads/stable`; treat
        // that as an absent branch so the caller refuses rather than aborts.
        if self
            .runtime
            .block_on(self.git_cli().fetch(request, &self.cancellation))
            .is_err()
        {
            return Ok(None);
        }
        let revision = Revision::new(b"refs/remotes/origin/stable".to_vec());
        match self.repository.resolve_revision(&revision) {
            Ok(oid) => Ok(Some(oid.to_hex())),
            Err(error) if error.kind() == RepositoryErrorKind::RevisionNotFound => Ok(None),
            Err(error) => Err(error.to_string()),
        }
    }

    fn build_projection_commit(
        &self,
        source_commit: &str,
        stable_oid: &str,
        version: &str,
    ) -> Result<String, String> {
        build_projection_commit_with_git(
            self.repository_root(),
            &self.runtime,
            &self.cancellation,
            self.runner(),
            source_commit,
            stable_oid,
            version,
        )
    }

    fn commit_parents_and_tree(&self, oid: &str) -> Result<(Vec<String>, String), String> {
        release_common::commit_parents_and_tree_at(&self.repository, oid)
    }

    fn changed_paths(&self, base: &str, head: &str) -> Result<Vec<String>, String> {
        let base = GitRef::new(base).map_err(|error| error.to_string())?;
        let head = GitRef::new(head).map_err(|error| error.to_string())?;
        let result = self
            .runtime
            .block_on(self.git_cli().exact_diff(
                exact_name_only_request(Some(base), Some(head)),
                &self.cancellation,
            ))
            .map_err(|error| error.to_string())?;
        if result.truncated() {
            return Err("projection commit diff was truncated".to_owned());
        }
        Ok(String::from_utf8_lossy(result.output().stdout())
            .lines()
            .filter(|line| !line.is_empty())
            .map(ToOwned::to_owned)
            .collect())
    }

    fn projected_plugin_version(&self, oid: &str) -> Result<String, String> {
        release_common::projected_plugin_version_at(&self.repository, oid)
    }

    fn staged_release(
        &self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> Result<Option<ReleaseState>, String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(ReleaseOperations::new(&transport).release_for_staging(repo, input))
            .map_err(|error| error.to_string())
    }

    fn release(&self, repo: &RepoSlug, tag: &str) -> Result<Option<ReleaseState>, String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(ReleaseOperations::new(&transport).release_for_tag(repo, tag))
            .map_err(|error| error.to_string())
    }

    fn create_draft(
        &self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(ReleaseOperations::new(&transport).stage_draft_release(repo, input))
            .map_err(|error| error.to_string())
    }

    fn update_draft(
        &self,
        repo: &RepoSlug,
        release: &ReleaseState,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(ReleaseOperations::new(&transport).update_draft_release(repo, release, input))
            .map_err(|error| error.to_string())
    }

    fn workflow_runs(
        &self,
        repo: &GitHubRepositoryRef,
        filters: &WorkflowRunFilters,
    ) -> Result<Vec<WorkflowRun>, String> {
        self.runtime
            .block_on(
                self.github
                    .list_workflow_runs(repo, filters, &self.cancellation),
            )
            .map_err(|error| error.to_string())
    }

    fn wait_for_asset_run_poll(&self, duration: Duration) -> Result<(), String> {
        let clock = TokioClock::new();
        self.runtime.block_on(wait_for_asset_run_poll(
            &clock,
            &self.cancellation,
            duration,
        ))
    }

    fn download_asset(&self, repo: &RepoSlug, asset_id: u64, size: u64) -> Result<Vec<u8>, String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(ReleaseOperations::new(&transport).download_asset(repo, asset_id, size))
            .map_err(|error| error.to_string())
    }

    fn verify_artifact(&self, request: &ArtifactAttestationRequest) -> Result<(), String> {
        let transport = OctocrabAttestationTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(AttestationOperations::new(&transport).verify_artifact(request))
            .map(|_| ())
            .map_err(|error| error.to_string())
    }
}

fn ensure_policy_with(services: &dyn Services, repo: &str) -> Result<(), String> {
    let (repository, slug) = repositories(repo)?;
    require_origin(services, &repository)?;
    services.ensure_policy(&slug)
}

/// The two commits `release stage` produces: the merged release-PR commit and
/// the synthetic projection commit that carries `plugin/` and is tagged.
#[derive(Debug, Eq, PartialEq)]
struct StagedRelease {
    source_commit: String,
    release_commit: String,
}

fn stage_with(
    services: &dyn Services,
    version: &str,
    notes_file: &Path,
    repo: &str,
    pr: &str,
) -> Result<StagedRelease, String> {
    let tag = release_tag(version)?;
    let pr = parse_pr(pr)?;
    let (repository, slug) = repositories(repo)?;
    require_safe_file(notes_file, "notes file is missing or unsafe")?;
    require_origin(services, &repository)?;
    require_policy(services, &slug)?;
    let pull_request = services.pull_request(&slug, pr)?;
    let source_commit = release_common::merged_release_commit(&pull_request)?.to_owned();
    services.fetch_main()?;
    if !services.is_ancestor(&source_commit, ORIGIN_MAIN)? {
        return Err("merged release commit is not an ancestor of origin/main".to_owned());
    }
    if services.plugin_version_at(&source_commit)? != version {
        return Err(
            "release candidate plugin version does not match the requested version".to_owned(),
        );
    }
    let Ok(Some(stable)) = services.resolve_origin_stable() else {
        return Err("origin/stable is not resolvable".to_owned());
    };
    let projection = services.build_projection_commit(&source_commit, &stable, version)?;
    if services
        .changed_paths(&source_commit, &projection)?
        .iter()
        .any(|path| !path.starts_with("plugin/"))
    {
        return Err("projection commit changed paths outside plugin/".to_owned());
    }
    let (parents, _) = services.commit_parents_and_tree(&projection)?;
    if parents.first().map(String::as_str) != Some(source_commit.as_str()) {
        return Err("projection commit first parent is not the merged release commit".to_owned());
    }
    if services.projected_plugin_version(&projection)? != version {
        return Err(
            "projected plugin.json version does not match the requested version".to_owned(),
        );
    }
    let release_commit = stage_projection_tag(services, &slug, &tag, &source_commit, &projection)?;
    let notes = fs::read_to_string(notes_file).map_err(|error| error.to_string())?;
    let input = DraftReleaseInput {
        tag: tag.clone(),
        target_commitish: release_commit.clone(),
        body: SafeText::from_untrusted(notes).as_str().to_owned(),
    };
    let release = match services.staged_release(&slug, &input)? {
        None => services.create_draft(&slug, &input)?,
        Some(release) if release.is_mutable_draft() => {
            services.update_draft(&slug, &release, &input)?
        }
        Some(_) => return Err("staged release is not a mutable draft".to_owned()),
    };
    if release.tag() != tag || !release.is_mutable_draft() {
        return Err("staged release is not a mutable draft".to_owned());
    }
    Ok(StagedRelease {
        source_commit,
        release_commit,
    })
}

/// Tag the projection commit, idempotently accepting a structurally matching
/// existing tag. Returns the commit the tag names (the accepted remote commit
/// on an idempotent re-run, otherwise the freshly built projection).
fn stage_projection_tag(
    services: &dyn Services,
    repo: &RepoSlug,
    tag: &str,
    source_commit: &str,
    projection: &str,
) -> Result<String, String> {
    let (_, projection_tree) = services.commit_parents_and_tree(projection)?;
    if let Some(remote) = services.remote_tag(repo, tag)? {
        services.fetch_tag(tag)?;
        if !structurally_matches(services, &remote, source_commit, &projection_tree)? {
            return Err(format!(
                "remote tag {tag} points at {remote}, not a projection of {source_commit}"
            ));
        }
        return Ok(remote);
    }
    // The tag names an existing structurally matching local commit (whose OID
    // differs from a freshly rebuilt projection on any retry, since `commit
    // --amend` restamps the committer time), or the newly created projection.
    // The pushed ref, postcondition, and return value must all name that commit.
    let tagged = if let Some(local) = services.local_tag(tag)? {
        if !structurally_matches(services, &local, source_commit, &projection_tree)? {
            return Err(format!("local tag {tag} points at a different commit"));
        }
        local
    } else {
        services.create_local_tag(tag, projection)?;
        projection.to_owned()
    };
    services.push_tag(tag)?;
    if services.remote_tag(repo, tag)?.as_deref() != Some(tagged.as_str()) {
        return Err("remote tag postcondition failed".to_owned());
    }
    Ok(tagged)
}

/// A commit is a valid projection when its first parent is the merged release
/// commit and its tree equals the freshly built projection tree. The second
/// parent (the `stable` tip) is deliberately excluded so a re-run whose `stable`
/// tip advanced still accepts the prior tag.
fn structurally_matches(
    services: &dyn Services,
    commit: &str,
    source_commit: &str,
    projection_tree: &str,
) -> Result<bool, String> {
    let (parents, tree) = services.commit_parents_and_tree(commit)?;
    Ok(parents.first().map(String::as_str) == Some(source_commit) && tree == projection_tree)
}

/// Build the projection commit through the closed installed-Git adapter.
///
/// Checks out `source_commit` in a detached temporary worktree, records
/// `stable_oid` as a second parent with a `-s ours` merge (keeping the merged
/// tree), regenerates `plugin/` into the worktree, and amends the commit with
/// the projection message. The temporary worktree is always removed. Returns the
/// projection commit OID.
///
/// # Errors
/// Returns a message when any Git operation, projection generation, or cleanup
/// fails.
pub fn build_projection_commit_with_git(
    repo_root: &Path,
    runtime: &LarchRuntime,
    cancellation: &Cancellation,
    runner: &TokioProcessRunner,
    source_commit: &str,
    stable_oid: &str,
    version: &str,
) -> Result<String, String> {
    let temporary_root =
        TemporaryRoot::resolve(Some(&env::temp_dir())).map_err(|error| error.to_string())?;
    let temporary = SecureTempDir::create(&temporary_root, "larch-release-projection-")
        .map_err(|error| error.to_string())?;
    let worktree_path = temporary.path().join("worktree");
    let worktree = WorktreePath::new(worktree_path.clone()).map_err(|error| error.to_string())?;

    let root_policy =
        GitCliPolicy::new(repo_root.to_path_buf()).map_err(|error| error.to_string())?;
    let root_git = GitCli::new(runner, root_policy);

    runtime
        .block_on(root_git.worktree(
            WorktreeRequest::Add {
                branch: None,
                detach: true,
                path: worktree.clone(),
                start_point: Some(GitRef::new(source_commit).map_err(|error| error.to_string())?),
            },
            cancellation,
        ))
        .map_err(|error| error.to_string())?;

    let built = build_projection_commit_in_worktree(
        &worktree_path,
        runtime,
        cancellation,
        runner,
        stable_oid,
        version,
    );

    let removed = runtime
        .block_on(root_git.worktree(
            WorktreeRequest::Remove {
                force: true,
                path: worktree,
            },
            cancellation,
        ))
        .map(|_| ())
        .map_err(|error| {
            // The temporary directory is reclaimed on drop, but a failed removal
            // leaves the repository's worktree administrative entry behind; name
            // the path so an operator can `git worktree prune` it.
            format!(
                "failed to remove temporary projection worktree {}: {error}",
                worktree_path.display()
            )
        });

    // Surface a build failure first; otherwise a cleanup failure fails closed.
    built.and_then(|oid| removed.map(|()| oid))
}

fn build_projection_commit_in_worktree(
    worktree_path: &Path,
    runtime: &LarchRuntime,
    cancellation: &Cancellation,
    runner: &TokioProcessRunner,
    stable_oid: &str,
    version: &str,
) -> Result<String, String> {
    let policy =
        GitCliPolicy::new(worktree_path.to_path_buf()).map_err(|error| error.to_string())?;
    let git = GitCli::new(runner, policy);

    runtime
        .block_on(git.merge(
            MergeRequest::Commit {
                theirs: GitRef::new(stable_oid).map_err(|error| error.to_string())?,
                no_edit: true,
                strategy_ours: true,
            },
            cancellation,
        ))
        .map_err(|error| error.to_string())?;

    let root = RepositoryRoot::resolve(Some(worktree_path)).map_err(|error| error.to_string())?;
    release_plugin_runtime::generate_projection(&root, &worktree_path.join("plugin"))?;

    runtime
        .block_on(git.add(
            AddRequest {
                all: false,
                force: true,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: vec![
                    larch_adapters::GitPath::new("plugin").map_err(|error| error.to_string())?,
                ],
            },
            cancellation,
        ))
        .map_err(|error| error.to_string())?;

    runtime
        .block_on(git.commit(
            CommitRequest {
                message: Some(CommitMessage::Literal(
                    format!("Release v{version} plugin projection").into(),
                )),
                amend: true,
                no_edit: false,
                allow_empty: false,
                only: false,
                pathspec_from_file: None,
                pathspec_file_nul: false,
                paths: Vec::new(),
            },
            cancellation,
        ))
        .map_err(|error| error.to_string())?;

    let repository = GixRepository::open(worktree_path).map_err(|error| error.to_string())?;
    repository
        .resolve_revision(&Revision::new(b"HEAD".to_vec()))
        .map(|oid| oid.to_hex())
        .map_err(|error| error.to_string())
}

fn asset_run_with(
    services: &dyn Services,
    repo: &str,
    tag: &str,
    source_commit: &str,
) -> Result<WorkflowRun, String> {
    if !valid_tag(tag) || !release_assets::is_commit(source_commit) {
        return Err("invalid release identity".to_owned());
    }
    let (repository, _) = repositories(repo).map_err(|_| "invalid release identity".to_owned())?;
    require_origin(services, &repository)?;
    let filters = WorkflowRunFilters {
        branch: Some(tag.to_owned()),
        workflow: Some(ASSET_WORKFLOW.to_owned()),
        event: Some("push".to_owned()),
        status: None,
        commit: Some(source_commit.to_owned()),
        limit: 10,
    };
    let mut waited = Duration::ZERO;
    loop {
        if let Some(run) = services
            .workflow_runs(&repository, &filters)?
            .into_iter()
            .filter(|run| run.head_sha == source_commit)
            .max_by_key(|run| run.database_id)
        {
            return Ok(run);
        }
        if waited >= ASSET_RUN_REGISTRATION_TIMEOUT {
            return Err(ASSET_RUN_NOT_REGISTERED.to_owned());
        }
        let delay =
            ASSET_RUN_POLL_INTERVAL.min(ASSET_RUN_REGISTRATION_TIMEOUT.saturating_sub(waited));
        services.wait_for_asset_run_poll(delay)?;
        waited = waited.saturating_add(delay);
    }
}

async fn wait_for_asset_run_poll(
    clock: &impl AsyncClock,
    cancellation: &Cancellation,
    duration: Duration,
) -> Result<(), String> {
    tokio::select! {
        biased;
        () = cancellation.cancelled() => Err(ASSET_RUN_WAIT_CANCELLED.to_owned()),
        () = clock.sleep(duration) => Ok(()),
    }
}

fn validate_candidate_with(
    services: &dyn Services,
    version: &str,
    repo: &str,
    pr: &str,
    source_commit: &str,
    require_draft: bool,
) -> Result<ReleaseState, String> {
    let tag = release_tag(version)?;
    let pr = parse_pr(pr)?;
    if !release_assets::is_commit(source_commit) {
        return Err("invalid source commit".to_owned());
    }
    let (repository, slug) = repositories(repo)?;
    require_origin(services, &repository)?;
    require_policy(services, &slug)?;
    let pull_request = services.pull_request(&slug, pr)?;
    let merged_commit = release_common::merged_release_commit(&pull_request)?;
    let (parents, _) = services.commit_parents_and_tree(source_commit)?;
    if parents.first().map(String::as_str) != Some(merged_commit) {
        return Err(
            "release candidate PR merge commit changed after the tag was created".to_owned(),
        );
    }
    if services.remote_tag(&slug, &tag)?.as_deref() != Some(source_commit) {
        return Err("release tag no longer names the candidate commit".to_owned());
    }
    let release = services
        .release(&slug, &tag)?
        .ok_or_else(|| format!("release {tag} was not found"))?;
    if require_draft && !release.is_mutable_draft() {
        return Err("release must remain a mutable draft before publication".to_owned());
    }
    if !require_draft && (release.is_draft() || !release.is_immutable()) {
        return Err("published release must be immutable".to_owned());
    }
    validate_assets(services, &slug, version, &tag, source_commit, &release)?;
    Ok(release)
}

fn validate_assets(
    services: &dyn Services,
    repo: &RepoSlug,
    version: &str,
    tag: &str,
    source_commit: &str,
    release: &ReleaseState,
) -> Result<(), String> {
    let expected = release_assets::release_asset_names(version, tag, source_commit)?;
    let expected_set: BTreeSet<&str> = expected.iter().map(String::as_str).collect();
    let actual_set: BTreeSet<&str> = release
        .assets()
        .iter()
        .map(larch_core::RemoteAsset::name)
        .collect();
    if actual_set.len() != release.assets().len() || actual_set != expected_set {
        let missing: Vec<_> = expected_set.difference(&actual_set).copied().collect();
        let unexpected: Vec<_> = actual_set.difference(&expected_set).copied().collect();
        return Err(format!(
            "release asset allowlist mismatch: missing={missing:?}, unexpected={unexpected:?}"
        ));
    }
    let temporary_root =
        TemporaryRoot::resolve(Some(&env::temp_dir())).map_err(|error| error.to_string())?;
    let temporary = SecureTempDir::create(&temporary_root, "larch-release-validate-")
        .map_err(|error| error.to_string())?;
    let asset_dir = temporary.path().join("assets");
    fs::create_dir(&asset_dir).map_err(|error| error.to_string())?;
    let tag_input = ReleaseTag::parse(tag).map_err(|error| error.to_string())?;
    let commit_input =
        ReleaseSourceCommit::parse(source_commit).map_err(|error| error.to_string())?;
    let mut attestations = Vec::with_capacity(expected.len());
    for name in &expected {
        let asset = release
            .assets()
            .iter()
            .find(|asset| asset.name() == name)
            .expect("allowlist equality proves each expected asset exists");
        let bytes = services.download_asset(repo, asset.database_id(), asset.size())?;
        if bytes.len() as u64 != asset.size() {
            return Err(format!("release asset size mismatch: {name}"));
        }
        let digest = format!("sha256:{}", release_assets::sha256_bytes(&bytes));
        if digest != asset.digest().as_str() {
            return Err(format!("release asset digest mismatch: {name}"));
        }
        fs::write(asset_dir.join(name), &bytes).map_err(|error| error.to_string())?;
        let subject = ReleaseAssetSubject::new(name, &digest).map_err(|error| error.to_string())?;
        attestations.push(ArtifactAttestationRequest::new(
            subject,
            tag_input.clone(),
            commit_input.clone(),
        ));
    }
    let license_path = temporary.path().join("LICENSE");
    fs::write(&license_path, services.candidate_license(source_commit)?)
        .map_err(|error| error.to_string())?;
    release_assets::validate_downloaded_assets(
        version,
        tag,
        source_commit,
        &asset_dir,
        &license_path,
    )?;
    for request in &attestations {
        services.verify_artifact(request)?;
    }
    Ok(())
}

fn require_policy(services: &dyn Services, repo: &RepoSlug) -> Result<(), String> {
    services.verify_policy(repo)
}

fn require_origin(services: &dyn Services, repository: &GitHubRepositoryRef) -> Result<(), String> {
    let expected = format!("{}/{}", repository.owner(), repository.name());
    if services.origin_repo()? == expected {
        Ok(())
    } else {
        Err("origin repository does not match --repo".to_owned())
    }
}

fn repositories(repo: &str) -> Result<(GitHubRepositoryRef, RepoSlug), String> {
    let slug =
        release_common::repo_slug(repo).ok_or_else(|| format!("invalid repository: {repo}"))?;
    let repository = GitHubRepositoryRef::new(slug.owner(), slug.repo())
        .map_err(|_| format!("invalid repository: {repo}"))?;
    Ok((repository, slug))
}

fn release_tag(version: &str) -> Result<String, String> {
    release_common::release_tag(version).ok_or_else(|| format!("invalid semver: {version}"))
}

fn parse_pr(value: &str) -> Result<u64, String> {
    release_common::parse_pr(value).ok_or_else(|| format!("invalid PR number: {value}"))
}

fn valid_tag(value: &str) -> bool {
    ReleaseTag::parse(value).is_ok()
}

fn require_safe_file(path: &Path, message: &str) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => Ok(()),
        _ => Err(message.to_owned()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_adapters::{
        github::{ReleaseCandidatePullRequest, ReleaseCandidatePullRequestState},
        runtime::LarchRuntime,
    };
    use larch_core::{MonotonicClock, RemoteAsset};
    use larch_test_support::TestClock;
    use std::{
        cell::{Cell, RefCell},
        collections::{BTreeMap, VecDeque},
        io::Write as _,
        time::SystemTime,
    };

    const SOURCE: &str = "1111111111111111111111111111111111111111";
    const OTHER: &str = "2222222222222222222222222222222222222222";
    const STABLE: &str = "3333333333333333333333333333333333333333";
    const PROJECTION: &str = "4444444444444444444444444444444444444444";
    const PROJECTION_TREE: &str = "5555555555555555555555555555555555555555";
    const REMOTE_MATCH: &str = "7777777777777777777777777777777777777777";
    const DIGEST: &str = "sha256:2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881";

    struct FakeServices {
        origin: String,
        policy: Result<(), String>,
        fetch_result: Result<(), String>,
        ancestor: bool,
        pr: ReleaseCandidatePullRequest,
        plugin_version: String,
        origin_stable: Option<String>,
        projection_commit: String,
        projected_version: String,
        changed: Vec<String>,
        commit_meta: BTreeMap<String, (Vec<String>, String)>,
        build_calls: Cell<usize>,
        create_local_tag_calls: Cell<usize>,
        created_tag: RefCell<Option<String>>,
        remote_tag: RefCell<Option<String>>,
        local_tag: Option<String>,
        releases: RefCell<Vec<Option<ReleaseState>>>,
        created: RefCell<usize>,
        updated: RefCell<usize>,
        fetches: Cell<usize>,
        tag_pushes: Cell<usize>,
        runs: RefCell<VecDeque<Vec<WorkflowRun>>>,
        workflow_run_queries: Cell<usize>,
        clock: TestClock,
        downloads: BTreeMap<u64, Vec<u8>>,
        attestation_error: Option<String>,
    }

    impl Default for FakeServices {
        fn default() -> Self {
            Self {
                origin: "character-ai/larch".to_owned(),
                policy: Ok(()),
                fetch_result: Ok(()),
                ancestor: true,
                pr: ReleaseCandidatePullRequest {
                    state: ReleaseCandidatePullRequestState::Merged,
                    head_oid: OTHER.to_owned(),
                    merge_commit_oid: Some(SOURCE.to_owned()),
                },
                plugin_version: "1.2.3".to_owned(),
                origin_stable: Some(STABLE.to_owned()),
                projection_commit: PROJECTION.to_owned(),
                projected_version: "1.2.3".to_owned(),
                changed: vec!["plugin/.claude-plugin/plugin.json".to_owned()],
                commit_meta: BTreeMap::new(),
                build_calls: Cell::new(0),
                create_local_tag_calls: Cell::new(0),
                created_tag: RefCell::new(None),
                remote_tag: RefCell::new(Some(PROJECTION.to_owned())),
                local_tag: None,
                releases: RefCell::new(Vec::new()),
                created: RefCell::new(0),
                updated: RefCell::new(0),
                fetches: Cell::new(0),
                tag_pushes: Cell::new(0),
                runs: RefCell::new(VecDeque::from([Vec::new()])),
                workflow_run_queries: Cell::new(0),
                clock: TestClock::new(SystemTime::UNIX_EPOCH),
                downloads: BTreeMap::new(),
                attestation_error: None,
            }
        }
    }

    impl FakeServices {
        /// The `(parents, tree)` recorded for `oid`, defaulting to a projection
        /// shape whose first parent is `SOURCE` and whose tree is `PROJECTION_TREE`.
        fn meta(&self, oid: &str) -> (Vec<String>, String) {
            self.commit_meta
                .get(oid)
                .cloned()
                .unwrap_or_else(|| (vec![SOURCE.to_owned()], PROJECTION_TREE.to_owned()))
        }
    }

    impl release_common::PostMergeReleaseServices for FakeServices {
        fn origin_repo(&self) -> Result<String, String> {
            Ok(self.origin.clone())
        }
        fn fetch_main(&self) -> Result<(), String> {
            self.fetches.set(self.fetches.get() + 1);
            self.fetch_result.clone()
        }
        fn pull_request(
            &self,
            _repo: &RepoSlug,
            _number: u64,
        ) -> Result<ReleaseCandidatePullRequest, String> {
            Ok(self.pr.clone())
        }
        fn is_ancestor(&self, _ancestor: &str, _descendant: &str) -> Result<bool, String> {
            Ok(self.ancestor)
        }
        fn plugin_version_at(&self, _oid: &str) -> Result<String, String> {
            Ok(self.plugin_version.clone())
        }
    }

    impl Services for FakeServices {
        fn ensure_policy(&self, _repo: &RepoSlug) -> Result<(), String> {
            self.policy.clone()
        }
        fn verify_policy(&self, _repo: &RepoSlug) -> Result<(), String> {
            self.policy.clone()
        }
        fn candidate_license(&self, _oid: &str) -> Result<Vec<u8>, String> {
            Ok(b"license".to_vec())
        }
        fn remote_tag(&self, _repo: &RepoSlug, _tag: &str) -> Result<Option<String>, String> {
            Ok(self.remote_tag.borrow().clone())
        }
        fn local_tag(&self, _tag: &str) -> Result<Option<String>, String> {
            Ok(self.local_tag.clone())
        }
        fn create_local_tag(&self, _tag: &str, oid: &str) -> Result<(), String> {
            self.create_local_tag_calls
                .set(self.create_local_tag_calls.get() + 1);
            *self.created_tag.borrow_mut() = Some(oid.to_owned());
            Ok(())
        }
        fn push_tag(&self, _tag: &str) -> Result<(), String> {
            self.tag_pushes.set(self.tag_pushes.get() + 1);
            // Model `git push` faithfully: the remote ref becomes whatever OID the
            // local tag currently names (the just-created commit, or a pre-existing
            // local tag), never an unrelated commit.
            let pushed = self
                .created_tag
                .borrow()
                .clone()
                .or_else(|| self.local_tag.clone())
                .unwrap_or_else(|| self.projection_commit.clone());
            *self.remote_tag.borrow_mut() = Some(pushed);
            Ok(())
        }
        fn fetch_tag(&self, _tag: &str) -> Result<(), String> {
            Ok(())
        }
        fn resolve_origin_stable(&self) -> Result<Option<String>, String> {
            Ok(self.origin_stable.clone())
        }
        fn build_projection_commit(
            &self,
            _source_commit: &str,
            _stable_oid: &str,
            _version: &str,
        ) -> Result<String, String> {
            self.build_calls.set(self.build_calls.get() + 1);
            Ok(self.projection_commit.clone())
        }
        fn commit_parents_and_tree(&self, oid: &str) -> Result<(Vec<String>, String), String> {
            Ok(self.meta(oid))
        }
        fn changed_paths(&self, _base: &str, _head: &str) -> Result<Vec<String>, String> {
            Ok(self.changed.clone())
        }
        fn projected_plugin_version(&self, _oid: &str) -> Result<String, String> {
            Ok(self.projected_version.clone())
        }
        fn staged_release(
            &self,
            _repo: &RepoSlug,
            _input: &DraftReleaseInput,
        ) -> Result<Option<ReleaseState>, String> {
            if self.releases.borrow().is_empty() {
                return Ok(None);
            }
            Ok(self.releases.borrow_mut().remove(0))
        }
        fn release(&self, _repo: &RepoSlug, _tag: &str) -> Result<Option<ReleaseState>, String> {
            if self.releases.borrow().is_empty() {
                return Ok(None);
            }
            Ok(self.releases.borrow_mut().remove(0))
        }
        fn create_draft(
            &self,
            _repo: &RepoSlug,
            _input: &DraftReleaseInput,
        ) -> Result<ReleaseState, String> {
            *self.created.borrow_mut() += 1;
            Ok(draft(Vec::new()))
        }
        fn update_draft(
            &self,
            _repo: &RepoSlug,
            _release: &ReleaseState,
            _input: &DraftReleaseInput,
        ) -> Result<ReleaseState, String> {
            *self.updated.borrow_mut() += 1;
            Ok(draft(Vec::new()))
        }
        fn workflow_runs(
            &self,
            _repo: &GitHubRepositoryRef,
            _filters: &WorkflowRunFilters,
        ) -> Result<Vec<WorkflowRun>, String> {
            self.workflow_run_queries
                .set(self.workflow_run_queries.get() + 1);
            let mut runs = self.runs.borrow_mut();
            if runs.len() > 1 {
                return Ok(runs.pop_front().expect("run response queue is not empty"));
            }
            Ok(runs.front().cloned().unwrap_or_default())
        }
        fn wait_for_asset_run_poll(&self, duration: Duration) -> Result<(), String> {
            self.clock.advance(duration);
            Ok(())
        }
        fn download_asset(
            &self,
            _repo: &RepoSlug,
            asset_id: u64,
            _size: u64,
        ) -> Result<Vec<u8>, String> {
            self.downloads
                .get(&asset_id)
                .cloned()
                .ok_or_else(|| "missing download".to_owned())
        }
        fn verify_artifact(&self, _request: &ArtifactAttestationRequest) -> Result<(), String> {
            self.attestation_error.clone().map_or(Ok(()), Err)
        }
    }

    fn draft(assets: Vec<RemoteAsset>) -> ReleaseState {
        ReleaseState::new(42, "v1.2.3", true, false, assets).expect("draft")
    }

    fn run(id: u64, sha: &str) -> WorkflowRun {
        WorkflowRun {
            database_id: id,
            status: "queued".to_owned(),
            conclusion: None,
            head_sha: sha.to_owned(),
            event: "push".to_owned(),
            workflow_name: "CI".to_owned(),
            attempt: 1,
        }
    }

    fn notes() -> tempfile::NamedTempFile {
        let mut file = tempfile::NamedTempFile::new().expect("notes");
        writeln!(file, "release notes").expect("write notes");
        file
    }

    fn complete_assets() -> (Vec<RemoteAsset>, BTreeMap<u64, Vec<u8>>) {
        const TARGETS: [&str; 1] = ["aarch64-apple-darwin"];
        let root = tempfile::tempdir().expect("asset root");
        let binary = root.path().join("larch");
        fs::write(
            &binary,
            "#!/bin/sh\n[ \"$1\" = --version ] || exit 2\nprintf 'larch 1.2.3\\n'\n",
        )
        .expect("binary");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            let mut permissions = fs::metadata(&binary).expect("metadata").permissions();
            permissions.set_mode(0o755);
            fs::set_permissions(&binary, permissions).expect("permissions");
        }
        let license = root.path().join("LICENSE");
        fs::write(&license, b"license").expect("license");
        let incoming = root.path().join("incoming");
        for target in TARGETS {
            assert_eq!(
                release_assets::package_asset(&release_assets::PackageArguments {
                    version: "1.2.3".to_owned(),
                    tag: "v1.2.3".to_owned(),
                    source_commit: PROJECTION.to_owned(),
                    target: target.to_owned(),
                    binary: binary.clone(),
                    license: license.clone(),
                    output_dir: incoming.join(target),
                }),
                ExitCode::SUCCESS
            );
        }
        let output = root.path().join("release");
        assert_eq!(
            release_assets::collect_assets(&release_assets::CollectArguments {
                version: "1.2.3".to_owned(),
                tag: "v1.2.3".to_owned(),
                source_commit: PROJECTION.to_owned(),
                input_dir: incoming,
                output_dir: output.clone(),
                license,
            }),
            ExitCode::SUCCESS
        );
        let names =
            release_assets::release_asset_names("1.2.3", "v1.2.3", PROJECTION).expect("names");
        let mut downloads = BTreeMap::new();
        let assets = names
            .iter()
            .enumerate()
            .map(|(index, name)| {
                let bytes = fs::read(output.join(name)).expect("asset bytes");
                let digest = format!("sha256:{}", release_assets::sha256_bytes(&bytes));
                let id = index as u64 + 1;
                let asset = RemoteAsset::new(id, name, bytes.len() as u64, &digest, "uploaded")
                    .expect("asset metadata");
                downloads.insert(id, bytes);
                asset
            })
            .collect();
        (assets, downloads)
    }

    #[test]
    fn stage_creates_a_missing_draft_and_resumes_a_mutable_one() {
        let notes = notes();
        let create = FakeServices {
            remote_tag: RefCell::new(None),
            releases: RefCell::new(vec![None]),
            ..FakeServices::default()
        };
        let staged = stage_with(&create, "1.2.3", notes.path(), "character-ai/larch", "7")
            .expect("stage creates a draft");
        assert_eq!(staged.source_commit, SOURCE);
        assert_eq!(staged.release_commit, PROJECTION);
        assert_eq!(*create.created.borrow(), 1);
        assert_eq!(create.fetches.get(), 1);
        assert_eq!(create.create_local_tag_calls.get(), 1);
        assert_eq!(create.tag_pushes.get(), 1);

        let resume = FakeServices {
            releases: RefCell::new(vec![Some(draft(Vec::new()))]),
            ..FakeServices::default()
        };
        assert!(stage_with(&resume, "1.2.3", notes.path(), "character-ai/larch", "7").is_ok());
        assert_eq!(*resume.updated.borrow(), 1);
    }

    #[test]
    fn stage_rejects_tag_identity_and_unsafe_resume_state() {
        let notes = notes();
        let mismatch = FakeServices {
            remote_tag: RefCell::new(Some(OTHER.to_owned())),
            commit_meta: BTreeMap::from([(
                OTHER.to_owned(),
                (vec![OTHER.to_owned()], PROJECTION_TREE.to_owned()),
            )]),
            ..FakeServices::default()
        };
        assert!(
            stage_with(&mismatch, "1.2.3", notes.path(), "character-ai/larch", "7")
                .unwrap_err()
                .contains("not a projection of")
        );
        assert_eq!(mismatch.tag_pushes.get(), 0);
        let published = ReleaseState::new(42, "v1.2.3", false, true, Vec::new()).expect("release");
        let unsafe_resume = FakeServices {
            releases: RefCell::new(vec![Some(published)]),
            ..FakeServices::default()
        };
        assert_eq!(
            stage_with(
                &unsafe_resume,
                "1.2.3",
                notes.path(),
                "character-ai/larch",
                "7"
            ),
            Err("staged release is not a mutable draft".to_owned())
        );
    }

    #[test]
    fn stage_requires_the_merged_pr_commit_before_creating_a_tag() {
        let notes = notes();
        let missing_merge_commit = FakeServices {
            pr: ReleaseCandidatePullRequest {
                state: ReleaseCandidatePullRequestState::Merged,
                head_oid: SOURCE.to_owned(),
                merge_commit_oid: None,
            },
            remote_tag: RefCell::new(None),
            ..FakeServices::default()
        };

        assert!(
            stage_with(
                &missing_merge_commit,
                "1.2.3",
                notes.path(),
                "character-ai/larch",
                "7"
            )
            .unwrap_err()
            .contains("has no merge commit")
        );
        assert_eq!(*missing_merge_commit.created.borrow(), 0);
    }

    #[test]
    fn stage_fetches_and_rejects_a_merged_commit_that_is_not_on_main() {
        let notes = notes();
        let stale = FakeServices {
            ancestor: false,
            remote_tag: RefCell::new(None),
            ..FakeServices::default()
        };

        assert!(
            stage_with(&stale, "1.2.3", notes.path(), "character-ai/larch", "7")
                .unwrap_err()
                .contains("not an ancestor")
        );
        assert_eq!(stale.fetches.get(), 1);
        assert_eq!(stale.tag_pushes.get(), 0);
        assert_eq!(*stale.created.borrow(), 0);
    }

    #[test]
    fn stage_reuses_a_structurally_matching_remote_tag_without_pushing() {
        let notes = notes();
        // The remote tag is a different SHA that nonetheless shares the merged
        // first parent and the freshly built projection tree, so the re-run
        // accepts it and pushes nothing.
        let idempotent = FakeServices {
            remote_tag: RefCell::new(Some(REMOTE_MATCH.to_owned())),
            releases: RefCell::new(vec![Some(draft(Vec::new()))]),
            ..FakeServices::default()
        };
        let staged = stage_with(
            &idempotent,
            "1.2.3",
            notes.path(),
            "character-ai/larch",
            "7",
        )
        .expect("idempotent stage");
        assert_eq!(staged.source_commit, SOURCE);
        assert_eq!(staged.release_commit, REMOTE_MATCH);
        assert_eq!(idempotent.tag_pushes.get(), 0);
        assert_eq!(idempotent.create_local_tag_calls.get(), 0);
        assert_eq!(*idempotent.updated.borrow(), 1);
    }

    #[test]
    fn stage_pushes_and_reports_a_structurally_matching_local_tag() {
        let notes = notes();
        // A prior run created the local tag at a structurally matching commit but
        // never pushed it; its OID differs from a freshly rebuilt projection. The
        // re-run must push and report that existing OID, not the rebuilt one.
        let resumed = FakeServices {
            remote_tag: RefCell::new(None),
            local_tag: Some(REMOTE_MATCH.to_owned()),
            releases: RefCell::new(vec![None]),
            ..FakeServices::default()
        };
        let staged = stage_with(&resumed, "1.2.3", notes.path(), "character-ai/larch", "7")
            .expect("resumed stage");
        assert_eq!(staged.release_commit, REMOTE_MATCH);
        assert_eq!(resumed.tag_pushes.get(), 1);
        assert_eq!(resumed.create_local_tag_calls.get(), 0);
    }

    #[test]
    fn stage_refuses_when_origin_stable_is_absent() {
        let notes = notes();
        let missing_stable = FakeServices {
            origin_stable: None,
            remote_tag: RefCell::new(None),
            ..FakeServices::default()
        };
        assert_eq!(
            stage_with(
                &missing_stable,
                "1.2.3",
                notes.path(),
                "character-ai/larch",
                "7"
            ),
            Err("origin/stable is not resolvable".to_owned())
        );
        assert_eq!(missing_stable.build_calls.get(), 0);
        assert_eq!(missing_stable.tag_pushes.get(), 0);
    }

    #[test]
    fn stage_rejects_projection_drift_outside_plugin() {
        let notes = notes();
        let drift = FakeServices {
            remote_tag: RefCell::new(None),
            changed: vec!["docs/readme.md".to_owned()],
            ..FakeServices::default()
        };
        assert_eq!(
            stage_with(&drift, "1.2.3", notes.path(), "character-ai/larch", "7"),
            Err("projection commit changed paths outside plugin/".to_owned())
        );
        assert_eq!(drift.tag_pushes.get(), 0);
    }

    #[test]
    fn stage_rejects_a_projected_plugin_version_mismatch() {
        let notes = notes();
        let mismatch = FakeServices {
            remote_tag: RefCell::new(None),
            projected_version: "1.2.4".to_owned(),
            ..FakeServices::default()
        };
        assert_eq!(
            stage_with(&mismatch, "1.2.3", notes.path(), "character-ai/larch", "7"),
            Err("projected plugin.json version does not match the requested version".to_owned())
        );
        assert_eq!(mismatch.tag_pushes.get(), 0);
    }

    #[test]
    fn stage_rejects_a_projection_whose_first_parent_is_not_the_merged_commit() {
        let notes = notes();
        let mismatch = FakeServices {
            remote_tag: RefCell::new(None),
            commit_meta: BTreeMap::from([(
                PROJECTION.to_owned(),
                (vec![OTHER.to_owned()], PROJECTION_TREE.to_owned()),
            )]),
            ..FakeServices::default()
        };
        assert_eq!(
            stage_with(&mismatch, "1.2.3", notes.path(), "character-ai/larch", "7"),
            Err("projection commit first parent is not the merged release commit".to_owned())
        );
        assert_eq!(mismatch.tag_pushes.get(), 0);
    }

    #[test]
    fn build_projection_commit_with_git_shapes_the_commit_and_cleans_up() {
        use std::process::Command;

        let repo = tempfile::tempdir().expect("repository directory");
        let root = repo.path();
        let git = |arguments: &[&str]| -> String {
            let output = Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixture builds and inspects the projection commit
                .arg("-C")
                .arg(root)
                .args(arguments)
                .output()
                .expect("run git");
            assert!(
                output.status.success(),
                "git {arguments:?}: {}",
                String::from_utf8_lossy(&output.stderr)
            );
            String::from_utf8_lossy(&output.stdout).trim().to_owned()
        };
        git(&["init", "--quiet", "--initial-branch=main"]);
        git(&["config", "user.email", "test@example.invalid"]);
        git(&["config", "user.name", "Larch Test"]);
        fs::write(root.join("README"), "root\n").expect("root file");
        git(&["add", "--all"]);
        git(&["commit", "--quiet", "-m", "root"]);

        // `stable` diverges from the shared root commit.
        git(&["checkout", "--quiet", "-b", "stable"]);
        fs::write(root.join("stable-only.txt"), "stable\n").expect("stable file");
        git(&["add", "--all"]);
        git(&["commit", "--quiet", "-m", "stable change"]);
        let stable_oid = git(&["rev-parse", "stable"]);

        // `main` carries the runtime projection inputs (the merged release commit).
        git(&["checkout", "--quiet", "main"]);
        crate::release_plugin_runtime::write_runtime_inputs(root);
        git(&["add", "--all"]);
        git(&["commit", "--quiet", "-m", "runtime inputs"]);
        let source_oid = git(&["rev-parse", "main"]);

        let runtime = LarchRuntime::new().expect("runtime");
        let cancellation = Cancellation::new();
        let runner = TokioProcessRunner::default();
        let projection = build_projection_commit_with_git(
            root,
            &runtime,
            &cancellation,
            &runner,
            &source_oid,
            &stable_oid,
            "1.2.3",
        )
        .expect("projection commit");

        // Parents are exactly [merged commit, stable tip].
        let parents = git(&["rev-list", "--parents", "-n", "1", &projection]);
        let mut fields = parents.split_whitespace();
        assert_eq!(fields.next(), Some(projection.as_str()));
        assert_eq!(fields.next(), Some(source_oid.as_str()));
        assert_eq!(fields.next(), Some(stable_oid.as_str()));
        assert_eq!(fields.next(), None);

        // The tree differs from the merged tree only under plugin/.
        let changed = git(&["diff", "--name-only", &source_oid, &projection]);
        assert!(!changed.is_empty(), "expected a generated plugin/ tree");
        assert!(
            changed.lines().all(|line| line.starts_with("plugin/")),
            "projection changed paths outside plugin/: {changed}"
        );

        // The generated plugin.json is present in the projection tree.
        let plugin_json = git(&[
            "show",
            &format!("{projection}:plugin/.claude-plugin/plugin.json"),
        ]);
        assert!(
            plugin_json.contains("\"name\":\"larch\""),
            "unexpected plugin.json: {plugin_json}"
        );

        // The temporary worktree was removed on the success path.
        let worktrees = git(&["worktree", "list", "--porcelain"]);
        assert_eq!(
            worktrees.matches("worktree ").count(),
            1,
            "temporary worktree was not removed: {worktrees}"
        );
    }

    #[test]
    fn asset_run_selects_only_the_exact_commit_and_highest_run_id() {
        let services = FakeServices {
            runs: RefCell::new(VecDeque::from([vec![
                run(10, SOURCE),
                run(12, OTHER),
                run(11, SOURCE),
            ]])),
            ..FakeServices::default()
        };
        assert_eq!(
            asset_run_with(&services, "character-ai/larch", "v1.2.3", SOURCE)
                .expect("run")
                .database_id,
            11
        );
        assert_eq!(services.workflow_run_queries.get(), 1);
        assert_eq!(services.clock.now().elapsed(), Duration::ZERO);
    }

    #[test]
    fn asset_run_polls_until_the_run_is_registered() {
        let services = FakeServices {
            runs: RefCell::new(VecDeque::from([
                vec![run(12, OTHER)],
                vec![run(13, SOURCE)],
            ])),
            ..FakeServices::default()
        };
        assert_eq!(
            asset_run_with(&services, "character-ai/larch", "v1.2.3", SOURCE)
                .expect("delayed run")
                .database_id,
            13
        );
        assert_eq!(services.workflow_run_queries.get(), 2);
        assert_eq!(services.clock.now().elapsed(), ASSET_RUN_POLL_INTERVAL);
    }

    #[test]
    fn asset_run_stops_after_the_registration_timeout() {
        let services = FakeServices {
            runs: RefCell::new(VecDeque::from([vec![run(12, OTHER)]])),
            ..FakeServices::default()
        };
        assert_eq!(
            asset_run_with(&services, "character-ai/larch", "v1.2.3", SOURCE),
            Err(ASSET_RUN_NOT_REGISTERED.to_owned())
        );
        assert_eq!(services.workflow_run_queries.get(), 13);
        assert_eq!(
            services.clock.now().elapsed(),
            ASSET_RUN_REGISTRATION_TIMEOUT
        );
    }

    #[test]
    fn asset_run_poll_wait_observes_duration_and_cancellation() {
        let runtime = LarchRuntime::current_thread().expect("test runtime");
        let clock = TestClock::new(SystemTime::UNIX_EPOCH);
        let cancellation = Cancellation::new();

        assert_eq!(
            runtime.block_on(wait_for_asset_run_poll(
                &clock,
                &cancellation,
                ASSET_RUN_POLL_INTERVAL,
            )),
            Ok(())
        );
        assert_eq!(clock.now().elapsed(), ASSET_RUN_POLL_INTERVAL);

        cancellation.cancel();
        assert_eq!(
            runtime.block_on(wait_for_asset_run_poll(
                &clock,
                &cancellation,
                ASSET_RUN_POLL_INTERVAL,
            )),
            Err(ASSET_RUN_WAIT_CANCELLED.to_owned())
        );
        assert_eq!(clock.now().elapsed(), ASSET_RUN_POLL_INTERVAL);
    }

    #[test]
    fn validate_draft_rejects_merge_commit_drift_incomplete_assets_and_digest_failure() {
        let drift = FakeServices {
            pr: ReleaseCandidatePullRequest {
                state: ReleaseCandidatePullRequestState::Merged,
                head_oid: OTHER.to_owned(),
                merge_commit_oid: Some(OTHER.to_owned()),
            },
            ..FakeServices::default()
        };
        assert!(
            validate_candidate_with(&drift, "1.2.3", "character-ai/larch", "7", PROJECTION, true,)
                .unwrap_err()
                .contains("merge commit changed")
        );

        let incomplete = FakeServices {
            releases: RefCell::new(vec![Some(draft(Vec::new()))]),
            ..FakeServices::default()
        };
        assert!(
            validate_candidate_with(
                &incomplete,
                "1.2.3",
                "character-ai/larch",
                "7",
                PROJECTION,
                true,
            )
            .unwrap_err()
            .contains("allowlist mismatch")
        );

        let names = release_assets::release_asset_names("1.2.3", "v1.2.3", PROJECTION)
            .expect("asset names");
        let assets: Vec<_> = names
            .iter()
            .enumerate()
            .map(|(index, name)| {
                RemoteAsset::new(index as u64 + 1, name, 1, DIGEST, "uploaded").expect("asset")
            })
            .collect();
        let downloads = assets
            .iter()
            .map(|asset| (asset.database_id(), b"y".to_vec()))
            .collect();
        let digest = FakeServices {
            releases: RefCell::new(vec![Some(draft(assets))]),
            downloads,
            ..FakeServices::default()
        };
        assert!(
            validate_candidate_with(
                &digest,
                "1.2.3",
                "character-ai/larch",
                "7",
                PROJECTION,
                true,
            )
            .unwrap_err()
            .contains("digest mismatch")
        );

        let (assets, downloads) = complete_assets();
        let complete = FakeServices {
            releases: RefCell::new(vec![Some(draft(assets))]),
            downloads,
            ..FakeServices::default()
        };
        assert!(
            validate_candidate_with(
                &complete,
                "1.2.3",
                "character-ai/larch",
                "7",
                PROJECTION,
                true,
            )
            .is_ok()
        );
    }

    #[test]
    fn policy_and_identity_inputs_fail_closed() {
        let services = FakeServices {
            policy: Err("cancelled".to_owned()),
            ..FakeServices::default()
        };
        assert_eq!(
            ensure_policy_with(&services, "character-ai/larch"),
            Err("cancelled".to_owned())
        );
        assert_eq!(
            release_tag("01.2.3"),
            Err("invalid semver: 01.2.3".to_owned())
        );
        assert_eq!(parse_pr("0"), Err("invalid PR number: 0".to_owned()));
        assert!(!release_assets::is_commit("ABC"));
    }

    #[test]
    fn stage_and_validation_reject_stale_or_incomplete_boundaries() {
        let notes = notes();
        let wrong_origin = FakeServices {
            origin: "elsewhere/repo".to_owned(),
            ..FakeServices::default()
        };
        assert!(
            ensure_policy_with(&wrong_origin, "character-ai/larch")
                .expect_err("origin mismatch")
                .contains("does not match")
        );

        let closed = FakeServices {
            pr: ReleaseCandidatePullRequest {
                state: ReleaseCandidatePullRequestState::Closed,
                head_oid: SOURCE.to_owned(),
                merge_commit_oid: None,
            },
            ..FakeServices::default()
        };
        assert!(
            stage_with(&closed, "1.2.3", notes.path(), "character-ai/larch", "7")
                .expect_err("closed PR")
                .contains("not merged")
        );

        let wrong_version = FakeServices {
            plugin_version: "1.2.4".to_owned(),
            ..FakeServices::default()
        };
        assert!(
            stage_with(
                &wrong_version,
                "1.2.3",
                notes.path(),
                "character-ai/larch",
                "7"
            )
            .expect_err("version drift")
            .contains("does not match")
        );

        let local_mismatch = FakeServices {
            remote_tag: RefCell::new(None),
            local_tag: Some(OTHER.to_owned()),
            commit_meta: BTreeMap::from([(
                OTHER.to_owned(),
                (vec![OTHER.to_owned()], PROJECTION_TREE.to_owned()),
            )]),
            ..FakeServices::default()
        };
        assert!(
            stage_with(
                &local_mismatch,
                "1.2.3",
                notes.path(),
                "character-ai/larch",
                "7"
            )
            .expect_err("local tag mismatch")
            .contains("different commit")
        );

        assert_eq!(
            asset_run_with(
                &FakeServices::default(),
                "character-ai/larch",
                "v1.2",
                SOURCE
            ),
            Err("invalid release identity".to_owned())
        );
        assert_eq!(
            validate_candidate_with(
                &FakeServices::default(),
                "1.2.3",
                "character-ai/larch",
                "7",
                "bad",
                true,
            ),
            Err("invalid source commit".to_owned())
        );
        assert_eq!(
            validate_candidate_with(
                &FakeServices::default(),
                "1.2.3",
                "character-ai/larch",
                "7",
                PROJECTION,
                true,
            ),
            Err("release v1.2.3 was not found".to_owned())
        );
    }
}
