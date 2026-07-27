//! Checked draft-release staging and validation over typed Git and GitHub ports.

use std::{collections::BTreeSet, env, fs, path::Path, process::ExitCode, time::Duration};

use larch_adapters::{
    GitRef, GitRefspec, GitRemote, GixRepository, LsRemoteRequest, PushRequest, SecureTempDir,
    TagMutationRequest, TemporaryRoot,
    clock::TokioClock,
    github::{
        AttestationOperations, DraftReleaseInput, OctocrabAttestationTransport,
        OctocrabReleaseTransport, ReleaseCandidatePullRequest, ReleaseCandidatePullRequestState,
        ReleaseOperations, RepoSlug,
    },
    runtime::Cancellation,
};
use larch_core::{
    ArtifactAttestationRequest, AsyncClock, GitHubActionsService, GitHubRepositoryRef, GitPath,
    ReleaseAssetSubject, ReleaseSourceCommit, ReleaseState, ReleaseTag, RepositoryErrorKind,
    RepositoryRead, Revision, SafeText, WorkflowRun, WorkflowRunFilters, emit_kv,
    resolve_tag_object_id,
};

use crate::{release_assets, release_common};

const ASSET_WORKFLOW: &str = "rust-release-assets.yaml";
const ASSET_RUN_REGISTRATION_TIMEOUT: Duration = Duration::from_secs(60);
const ASSET_RUN_POLL_INTERVAL: Duration = Duration::from_secs(5);
const ASSET_RUN_NOT_REGISTERED: &str = "tag-triggered asset workflow run is not registered";
const ASSET_RUN_WAIT_CANCELLED: &str = "asset workflow run registration wait cancelled";

pub fn ensure_policy(repo: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| ensure_policy_with(services, repo),
        |()| {
            emit_kv("MERGE_COMMITS_ENABLED", "true");
            emit_kv("IMMUTABLE_RELEASES_ENABLED", "true");
        },
    )
}

pub fn stage(version: &str, notes_file: &Path, repo: &str, pr: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| stage_with(services, version, notes_file, repo, pr),
        |source_commit| {
            emit_kv("TAG", &format!("v{version}"));
            emit_kv("SOURCE_COMMIT", &source_commit);
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

trait Services {
    fn origin_repo(&self) -> Result<String, String>;
    fn ensure_policy(&self, repo: &RepoSlug) -> Result<(), String>;
    fn verify_policy(&self, repo: &RepoSlug) -> Result<(), String>;
    fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String>;
    fn plugin_version_at(&self, oid: &str) -> Result<String, String>;
    fn candidate_license(&self, oid: &str) -> Result<Vec<u8>, String>;
    fn remote_tag(&self, repo: &RepoSlug, tag: &str) -> Result<Option<String>, String>;
    fn local_tag(&self, tag: &str) -> Result<Option<String>, String>;
    fn create_local_tag(&self, tag: &str, oid: &str) -> Result<(), String>;
    fn push_tag(&self, tag: &str) -> Result<(), String>;
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
    fn origin_repo(&self) -> Result<String, String> {
        self.origin_repo()
    }

    fn ensure_policy(&self, repo: &RepoSlug) -> Result<(), String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(ReleaseOperations::new(&transport).ensure_repository_policy(repo))
            .map_err(|error| error.to_string())
    }

    fn verify_policy(&self, repo: &RepoSlug) -> Result<(), String> {
        let transport = OctocrabReleaseTransport::new(&self.github, &self.cancellation);
        let (merge_commits, immutable_releases) = self
            .runtime
            .block_on(ReleaseOperations::new(&transport).repository_policy(repo))
            .map_err(|error| error.to_string())?;
        if !merge_commits {
            return Err("repository merge commits are not enabled".to_owned());
        }
        if !immutable_releases {
            return Err("immutable releases are not enabled".to_owned());
        }
        Ok(())
    }

    fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String> {
        self.pull_request(repo, number)
    }

    fn plugin_version_at(&self, oid: &str) -> Result<String, String> {
        plugin_version_at(&self.repository, oid)
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
        let result = self
            .runtime
            .block_on(self.git_cli().ls_remote(
                LsRemoteRequest {
                    remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
                    patterns: vec![
                        GitRef::new(&direct).map_err(|error| error.to_string())?,
                        GitRef::new(&peeled).map_err(|error| error.to_string())?,
                    ],
                    heads: false,
                    exit_code: false,
                },
                &self.cancellation,
            ))
            .map_err(|error| error.to_string())?;
        let output = String::from_utf8(result.output().stdout().to_vec())
            .map_err(|_| "remote tag read returned non-UTF-8 output".to_owned())?;
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
        let request = PushRequest {
            remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
            refspec: GitRefspec::new(format!("{reference}:{reference}"))
                .map_err(|error| error.to_string())?,
            force_with_lease: None,
            set_upstream: false,
        };
        self.runtime
            .block_on(self.git_cli().push(request, &self.cancellation))
            .map(|_| ())
            .map_err(|error| error.to_string())
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

fn ensure_policy_with(services: &dyn Services, repo: &str) -> Result<(), String> {
    let (repository, slug) = repositories(repo)?;
    require_origin(services, &repository)?;
    services.ensure_policy(&slug)?;
    services.verify_policy(&slug)
}

fn stage_with(
    services: &dyn Services,
    version: &str,
    notes_file: &Path,
    repo: &str,
    pr: &str,
) -> Result<String, String> {
    let tag = release_tag(version)?;
    let pr = parse_pr(pr)?;
    let (repository, slug) = repositories(repo)?;
    require_safe_file(notes_file, "notes file is missing or unsafe")?;
    require_origin(services, &repository)?;
    require_policy(services, &slug)?;
    let pull_request = services.pull_request(&slug, pr)?;
    if pull_request.state != ReleaseCandidatePullRequestState::Open {
        return Err("release candidate PR must be open while staging".to_owned());
    }
    let source_commit = pull_request.head_oid;
    if services.plugin_version_at(&source_commit)? != version {
        return Err(
            "release candidate plugin version does not match the requested version".to_owned(),
        );
    }
    stage_tag(services, &slug, &tag, &source_commit)?;
    let notes = fs::read_to_string(notes_file).map_err(|error| error.to_string())?;
    let input = DraftReleaseInput {
        tag: tag.clone(),
        target_commitish: source_commit.clone(),
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
    Ok(source_commit)
}

fn stage_tag(
    services: &dyn Services,
    repo: &RepoSlug,
    tag: &str,
    source_commit: &str,
) -> Result<(), String> {
    match services.remote_tag(repo, tag)? {
        Some(remote) if remote != source_commit => {
            return Err(format!(
                "remote tag {tag} points at {remote}, not {source_commit}"
            ));
        }
        Some(_) => {}
        None => {
            match services.local_tag(tag)? {
                Some(local) if local != source_commit => {
                    return Err(format!("local tag {tag} points at a different commit"));
                }
                Some(_) => {}
                None => services.create_local_tag(tag, source_commit)?,
            }
            services.push_tag(tag)?;
        }
    }
    if services.remote_tag(repo, tag)?.as_deref() != Some(source_commit) {
        return Err("remote tag postcondition failed".to_owned());
    }
    Ok(())
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
    if services.pull_request(&slug, pr)?.head_oid != source_commit {
        return Err("release candidate PR head changed after the tag was created".to_owned());
    }
    if services.remote_tag(&slug, &tag)?.as_deref() != Some(source_commit) {
        return Err("release tag no longer names the candidate commit".to_owned());
    }
    let release = services
        .release(&slug, &tag)?
        .ok_or_else(|| format!("release {tag} was not found"))?;
    if require_draft && !release.is_mutable_draft() {
        return Err("release must remain a mutable draft before merge".to_owned());
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
    use larch_adapters::runtime::LarchRuntime;
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
    const DIGEST: &str = "sha256:2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881";

    struct FakeServices {
        origin: String,
        policy: Result<(), String>,
        pr: ReleaseCandidatePullRequest,
        plugin_version: String,
        remote_tag: RefCell<Option<String>>,
        local_tag: Option<String>,
        releases: RefCell<Vec<Option<ReleaseState>>>,
        created: RefCell<usize>,
        updated: RefCell<usize>,
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
                pr: ReleaseCandidatePullRequest {
                    state: ReleaseCandidatePullRequestState::Open,
                    head_oid: SOURCE.to_owned(),
                },
                plugin_version: "1.2.3".to_owned(),
                remote_tag: RefCell::new(Some(SOURCE.to_owned())),
                local_tag: None,
                releases: RefCell::new(Vec::new()),
                created: RefCell::new(0),
                updated: RefCell::new(0),
                runs: RefCell::new(VecDeque::from([Vec::new()])),
                workflow_run_queries: Cell::new(0),
                clock: TestClock::new(SystemTime::UNIX_EPOCH),
                downloads: BTreeMap::new(),
                attestation_error: None,
            }
        }
    }

    impl Services for FakeServices {
        fn origin_repo(&self) -> Result<String, String> {
            Ok(self.origin.clone())
        }
        fn ensure_policy(&self, _repo: &RepoSlug) -> Result<(), String> {
            Ok(())
        }
        fn verify_policy(&self, _repo: &RepoSlug) -> Result<(), String> {
            self.policy.clone()
        }
        fn pull_request(
            &self,
            _repo: &RepoSlug,
            _number: u64,
        ) -> Result<ReleaseCandidatePullRequest, String> {
            Ok(self.pr.clone())
        }
        fn plugin_version_at(&self, _oid: &str) -> Result<String, String> {
            Ok(self.plugin_version.clone())
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
        fn create_local_tag(&self, _tag: &str, _oid: &str) -> Result<(), String> {
            Ok(())
        }
        fn push_tag(&self, _tag: &str) -> Result<(), String> {
            *self.remote_tag.borrow_mut() = Some(SOURCE.to_owned());
            Ok(())
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
                    source_commit: SOURCE.to_owned(),
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
                source_commit: SOURCE.to_owned(),
                input_dir: incoming,
                output_dir: output.clone(),
                license,
            }),
            ExitCode::SUCCESS
        );
        let names = release_assets::release_asset_names("1.2.3", "v1.2.3", SOURCE).expect("names");
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
        assert_eq!(
            stage_with(&create, "1.2.3", notes.path(), "character-ai/larch", "7"),
            Ok(SOURCE.to_owned())
        );
        assert_eq!(*create.created.borrow(), 1);

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
            ..FakeServices::default()
        };
        assert!(
            stage_with(&mismatch, "1.2.3", notes.path(), "character-ai/larch", "7")
                .unwrap_err()
                .contains("not 111111")
        );
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
    fn validate_draft_rejects_head_drift_incomplete_assets_and_digest_failure() {
        let drift = FakeServices {
            pr: ReleaseCandidatePullRequest {
                state: ReleaseCandidatePullRequestState::Open,
                head_oid: OTHER.to_owned(),
            },
            ..FakeServices::default()
        };
        assert!(
            validate_candidate_with(&drift, "1.2.3", "character-ai/larch", "7", SOURCE, true)
                .unwrap_err()
                .contains("PR head changed")
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
                SOURCE,
                true,
            )
            .unwrap_err()
            .contains("allowlist mismatch")
        );

        let names =
            release_assets::release_asset_names("1.2.3", "v1.2.3", SOURCE).expect("asset names");
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
            validate_candidate_with(&digest, "1.2.3", "character-ai/larch", "7", SOURCE, true,)
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
            validate_candidate_with(&complete, "1.2.3", "character-ai/larch", "7", SOURCE, true,)
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
            },
            ..FakeServices::default()
        };
        assert!(
            stage_with(&closed, "1.2.3", notes.path(), "character-ai/larch", "7")
                .expect_err("closed PR")
                .contains("must be open")
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
                SOURCE,
                true,
            ),
            Err("release v1.2.3 was not found".to_owned())
        );
    }
}
