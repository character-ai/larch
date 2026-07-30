//! Immutable release publication, recovery, and Latest promotion.

use std::process::ExitCode;

use larch_adapters::{
    FetchRequest, GitRefspec, GitRemote, GixRepository,
    github::{
        AttestationOperations, OctocrabAttestationTransport, ReleaseCandidatePullRequest,
        ReleaseCandidatePullRequestState, RepoSlug,
    },
};
use larch_core::{
    ImmutableReleaseAttestationRequest, ReleaseAssetSubject, ReleaseSourceCommit, ReleaseState,
    ReleaseTag, RepositoryRead, Revision, emit_kv,
};

use crate::{release_common, release_stage};

const ORIGIN_MAIN: &str = "origin/main";

/// The branch that `.claude-plugin/marketplace.json` pins the installed plugin
/// projection to with its `git-subdir` `ref` field.
///
/// A release version is an alias for exactly one commit: everything an install
/// places on disk for that version, plugin content and executable alike, comes
/// from the commit this branch names. `release finish` fast-forwards it to the
/// tagged commit only after immutable publication, attestation verification, and
/// Latest promotion all succeed, so a pinned install can never fetch content for
/// a version whose verified binary does not exist yet.
///
/// Three surfaces share this token and change together: the descriptor's `ref`
/// field, this constant, and `RELEASE_PIN_REF` in `scripts/larch.sh`.
/// `marketplace_descriptor_pins_the_release_ref` pins the first two.
///
/// Not `release`: Git refs are paths, so `refs/heads/release` and the
/// `release/v<version>` candidate branch `/release` Step 5 creates cannot
/// coexist. `pin_ref_cannot_collide_with_release_candidate_branches` pins that.
pub const RELEASE_PIN_REF: &str = "stable";

pub fn finish(version: &str, repo: &str, pr: &str, source_commit: &str) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| finish_with(services, version, repo, pr, source_commit),
        |action| {
            emit_kv("RELEASE_ACTION", action);
            emit_kv("SOURCE_COMMIT", source_commit);
            emit_kv("TAG", &format!("v{version}"));
            emit_kv("VERSION", version);
            emit_kv("IMMUTABLE_RELEASE_VALID", "true");
            emit_kv("LATEST", "true");
            emit_kv("RELEASE_PIN_REF", RELEASE_PIN_REF);
            emit_kv("RELEASE_PIN_OID", source_commit);
        },
    )
}

pub fn promote(version: &str, repo: Option<&str>) -> ExitCode {
    release_common::command(
        ProductionServices::new(),
        |services| promote_with(services, version, repo),
        |outcome| println!("{}", outcome.message()),
    )
}

pub fn promote_latest(repo: &str, dry_run: bool) -> ExitCode {
    if release_common::repo_slug(repo).is_none() {
        return exit(Err(format!("Invalid --repo value: {repo}")));
    }
    let result = ProductionServices::new()
        .and_then(|services| promote_latest_with(&services, repo, dry_run));
    exit(result)
}

fn promote_latest_with(services: &dyn Services, repo: &str, dry_run: bool) -> Result<(), String> {
    let plan = latest_plan(services, repo)?;
    emit_kv("RELEASE_REPO", repo);
    emit_kv("RELEASE_TAG", plan.release.tag());
    emit_kv(
        "RELEASE_PUBLISHED_AT",
        plan.release.published_at().unwrap_or_default(),
    );
    emit_kv(
        "RELEASE_WAS_PRERELEASE",
        boolean(plan.release.is_prerelease()),
    );
    emit_kv("RELEASE_WAS_LATEST", boolean(plan.was_latest));
    if dry_run {
        emit_kv("DRY_RUN", "true");
        return Ok(());
    }
    apply_latest_plan(services, &plan)
}

fn exit(result: Result<(), String>) -> ExitCode {
    release_common::exit(result)
}

trait Services {
    fn origin_repo(&self) -> Result<String, String>;
    fn fetch_main(&self) -> Result<(), String>;
    fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String>;
    fn is_ancestor(&self, ancestor: &str, descendant: &str) -> Result<bool, String>;
    fn plugin_version_at(&self, revision: &str) -> Result<String, String>;
    fn release(&self, repo: &RepoSlug, tag: &str) -> Result<Option<ReleaseState>, String>;
    fn validate_assets(
        &self,
        version: &str,
        repo: &str,
        pr: &str,
        source_commit: &str,
        require_draft: bool,
    ) -> Result<ReleaseState, String>;
    fn publish(&self, repo: &RepoSlug, release: &ReleaseState) -> Result<ReleaseState, String>;
    fn verify_release(&self, release: &ReleaseState, source_commit: &str) -> Result<(), String>;
    fn latest(&self, repo: &RepoSlug) -> Result<Option<ReleaseState>, String>;
    fn newest_published(&self, repo: &RepoSlug) -> Result<Option<ReleaseState>, String>;
    fn promote(&self, repo: &RepoSlug, release: &ReleaseState) -> Result<ReleaseState, String>;
    fn remote_branch_commit(&self, branch: &str) -> Result<Option<String>, String>;
    fn fast_forward_remote_branch(&self, branch: &str, commit: &str) -> Result<(), String>;
}

type ProductionServices = release_common::ProductionReleaseServices;

impl Services for ProductionServices {
    fn origin_repo(&self) -> Result<String, String> {
        self.origin_repo()
    }

    fn fetch_main(&self) -> Result<(), String> {
        self.runtime
            .block_on(
                self.git_cli()
                    .fetch(main_fetch_request()?, &self.cancellation),
            )
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    fn pull_request(
        &self,
        repo: &RepoSlug,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, String> {
        self.pull_request(repo, number)
    }

    fn is_ancestor(&self, ancestor: &str, descendant: &str) -> Result<bool, String> {
        is_ancestor(&self.repository, ancestor, descendant)
    }

    fn plugin_version_at(&self, revision: &str) -> Result<String, String> {
        release_stage::plugin_version_at(&self.repository, revision)
    }

    fn release(&self, repo: &RepoSlug, tag: &str) -> Result<Option<ReleaseState>, String> {
        self.release_operations(
            |operations, repo| {
                self.runtime
                    .block_on(operations.release_for_tag(&repo, tag))
            },
            repo,
        )
        .map_err(|error| error.to_string())
    }

    fn validate_assets(
        &self,
        version: &str,
        repo: &str,
        pr: &str,
        source_commit: &str,
        require_draft: bool,
    ) -> Result<ReleaseState, String> {
        release_stage::validate_candidate_assets(version, repo, pr, source_commit, require_draft)
    }

    fn publish(&self, repo: &RepoSlug, release: &ReleaseState) -> Result<ReleaseState, String> {
        self.release_operations(
            |operations, repo| {
                self.runtime
                    .block_on(operations.publish_release(&repo, release))
            },
            repo,
        )
        .map_err(|error| error.to_string())
    }

    fn verify_release(&self, release: &ReleaseState, source_commit: &str) -> Result<(), String> {
        let request = immutable_release_request(release, source_commit)?;
        let transport = OctocrabAttestationTransport::new(&self.github, &self.cancellation);
        self.runtime
            .block_on(AttestationOperations::new(&transport).verify_immutable_release(&request))
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    fn latest(&self, repo: &RepoSlug) -> Result<Option<ReleaseState>, String> {
        self.release_operations(
            |operations, repo| self.runtime.block_on(operations.latest_release(&repo)),
            repo,
        )
        .map_err(|error| error.to_string())
    }

    fn newest_published(&self, repo: &RepoSlug) -> Result<Option<ReleaseState>, String> {
        self.release_operations(
            |operations, repo| {
                self.runtime
                    .block_on(operations.newest_published_release(&repo))
            },
            repo,
        )
        .map_err(|error| error.to_string())
    }

    fn promote(&self, repo: &RepoSlug, release: &ReleaseState) -> Result<ReleaseState, String> {
        self.release_operations(
            |operations, repo| {
                self.runtime
                    .block_on(operations.promote_release(&repo, release))
            },
            repo,
        )
        .map_err(|error| error.to_string())
    }

    fn remote_branch_commit(&self, branch: &str) -> Result<Option<String>, String> {
        let reference = branch_reference(branch);
        let output = self.origin_refs(std::slice::from_ref(&reference))?;
        sole_remote_commit(&output, &reference)
    }

    fn fast_forward_remote_branch(&self, branch: &str, commit: &str) -> Result<(), String> {
        self.push_origin_ref(&format!("{commit}:{}", branch_reference(branch)))
    }
}

fn branch_reference(branch: &str) -> String {
    format!("refs/heads/{branch}")
}

/// Select the commit `git ls-remote` reported for exactly one reference.
///
/// A branch has no peeled form, so a second row for the same name means the
/// remote answered ambiguously and the caller must not act on either value.
fn sole_remote_commit(output: &str, reference: &str) -> Result<Option<String>, String> {
    let mut commit: Option<&str> = None;
    for line in output.lines() {
        let mut fields = line.split_ascii_whitespace();
        let (Some(oid), Some(name), None) = (fields.next(), fields.next(), fields.next()) else {
            continue;
        };
        if name != reference {
            continue;
        }
        if commit.is_some() {
            return Err(format!("remote reported {reference} more than once"));
        }
        commit = Some(oid);
    }
    commit
        .map(|oid| {
            ReleaseSourceCommit::parse(oid)
                .map(|parsed| parsed.as_str().to_owned())
                .map_err(|_| format!("remote reported an invalid commit for {reference}"))
        })
        .transpose()
}

fn main_fetch_request() -> Result<FetchRequest, String> {
    Ok(FetchRequest {
        remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
        refspec: Some(GitRefspec::new("main").map_err(|error| error.to_string())?),
        quiet: true,
    })
}

fn is_ancestor(
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

fn immutable_release_request(
    release: &ReleaseState,
    source_commit: &str,
) -> Result<ImmutableReleaseAttestationRequest, String> {
    let tag = ReleaseTag::parse(release.tag()).map_err(|error| error.to_string())?;
    let source_commit =
        ReleaseSourceCommit::parse(source_commit).map_err(|error| error.to_string())?;
    let assets = release
        .assets()
        .iter()
        .map(|asset| ReleaseAssetSubject::new(asset.name(), asset.digest().as_str()))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;
    ImmutableReleaseAttestationRequest::new(tag, source_commit, assets)
        .map_err(|error| error.to_string())
}

fn finish_with(
    services: &dyn Services,
    version: &str,
    repo: &str,
    pr: &str,
    source_commit: &str,
) -> Result<&'static str, String> {
    let tag = finish_release_tag(version)?;
    let pr_number = parse_pr(pr)?;
    ReleaseSourceCommit::parse(source_commit).map_err(|_| "invalid source commit".to_owned())?;
    let slug = finish_repository(repo)?;
    if services.origin_repo()? != repo {
        return Err("origin repository does not match --repo".to_owned());
    }
    services.fetch_main()?;
    let pull_request = services.pull_request(&slug, pr_number)?;
    if pull_request.state != ReleaseCandidatePullRequestState::Merged
        || pull_request.head_oid != source_commit
    {
        return Err("release candidate PR is not merged at the tagged commit".to_owned());
    }
    if !services.is_ancestor(source_commit, ORIGIN_MAIN)? {
        return Err("tagged release candidate is not an ancestor of origin/main".to_owned());
    }
    if services.plugin_version_at(source_commit)? != version {
        return Err("plugin version at the release tag does not match".to_owned());
    }
    if services.plugin_version_at(ORIGIN_MAIN)? != version {
        return Err("plugin version on origin/main does not match the release tag".to_owned());
    }
    let release = services
        .release(&slug, &tag)?
        .ok_or_else(|| "staged release is missing".to_owned())?;
    let action = if release.is_draft() {
        let validated = services.validate_assets(version, repo, pr, source_commit, true)?;
        require_same_release(&release, &validated)?;
        let published = services.publish(&slug, &release)?;
        require_same_release(&release, &published)?;
        "publish"
    } else {
        if !release.is_immutable() {
            return Err("published release must be immutable".to_owned());
        }
        "resume-published"
    };
    let published = services.validate_assets(version, repo, pr, source_commit, false)?;
    require_same_release(&release, &published)?;
    services.verify_release(&published, source_commit)?;
    let latest = services.latest(&slug)?;
    let promotion_needed = latest.as_ref().is_none_or(|latest| {
        latest.database_id() != published.database_id() || latest.is_prerelease()
    });
    if promotion_needed {
        let promoted = services.promote(&slug, &published)?;
        require_same_release(&published, &promoted)?;
    }
    let latest = services
        .latest(&slug)?
        .ok_or_else(|| "Latest release promotion postcondition failed".to_owned())?;
    if latest.database_id() != published.database_id()
        || latest.is_draft()
        || latest.is_prerelease()
    {
        return Err("Latest release promotion postcondition failed".to_owned());
    }
    advance_release_pin(services, source_commit)?;
    Ok(action)
}

/// Fast-forward the marketplace-pinned branch to the verified tagged commit.
///
/// This runs last on purpose. Until it succeeds, a pinned install keeps fetching
/// the previous release's plugin content, which pairs with the previous binary;
/// once it succeeds, both sides of the new install come from `source_commit`. A
/// failure here fails `release finish`, because a published release whose pin
/// never advanced is invisible to every installer.
fn advance_release_pin(services: &dyn Services, source_commit: &str) -> Result<(), String> {
    if services.remote_branch_commit(RELEASE_PIN_REF)?.as_deref() != Some(source_commit) {
        services.fast_forward_remote_branch(RELEASE_PIN_REF, source_commit)?;
    }
    let observed = services
        .remote_branch_commit(RELEASE_PIN_REF)?
        .ok_or_else(|| format!("release pin refs/heads/{RELEASE_PIN_REF} is missing after push"))?;
    if observed == source_commit {
        Ok(())
    } else {
        Err(format!(
            "release pin refs/heads/{RELEASE_PIN_REF} is at {observed}, not the tagged commit"
        ))
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PromoteOutcome {
    tag: String,
    was_latest: bool,
    cleared_prerelease: bool,
}

impl PromoteOutcome {
    fn message(&self) -> String {
        match (self.was_latest, self.cleared_prerelease) {
            (true, true) => format!(
                "{} is already the latest release; cleared pre-release flag.",
                self.tag
            ),
            (true, false) => format!("{} is already the latest release.", self.tag),
            (false, _) => format!("Promoted {} to latest release.", self.tag),
        }
    }
}

fn promote_with(
    services: &dyn Services,
    version: &str,
    repo: Option<&str>,
) -> Result<PromoteOutcome, String> {
    let tag = release_tag(version)?;
    let repo = repo
        .map(str::to_owned)
        .map_or_else(|| services.origin_repo(), Ok)?;
    let slug = repository(&repo)?;
    let release = services
        .release(&slug, &tag)?
        .ok_or_else(|| format!("release {tag} not found."))?;
    require_publishable(&release)?;
    let was_latest = services
        .latest(&slug)?
        .is_some_and(|latest| latest.database_id() == release.database_id());
    let cleared_prerelease = release.is_prerelease();
    if !was_latest || cleared_prerelease {
        let promoted = services.promote(&slug, &release)?;
        require_same_release(&release, &promoted)?;
    }
    Ok(PromoteOutcome {
        tag,
        was_latest,
        cleared_prerelease,
    })
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct LatestPlan {
    repo: RepoSlug,
    release: ReleaseState,
    was_latest: bool,
}

fn latest_plan(services: &dyn Services, repo: &str) -> Result<LatestPlan, String> {
    let slug = repository(repo)?;
    let release = services
        .newest_published(&slug)?
        .ok_or_else(|| format!("No non-draft releases found for {repo}"))?;
    let was_latest = services
        .latest(&slug)?
        .is_some_and(|latest| latest.database_id() == release.database_id());
    Ok(LatestPlan {
        repo: slug,
        release,
        was_latest,
    })
}

fn apply_latest_plan(services: &dyn Services, plan: &LatestPlan) -> Result<(), String> {
    if !plan.release.is_prerelease() && plan.was_latest {
        emit_kv("RELEASE_ALREADY_LATEST", "true");
        return Ok(());
    }
    emit_kv("RELEASE_ALREADY_LATEST", "false");
    require_publishable(&plan.release)?;
    let promoted = services.promote(&plan.repo, &plan.release)?;
    emit_kv("RELEASE_IS_PRERELEASE", boolean(promoted.is_prerelease()));
    emit_kv("RELEASE_IS_LATEST", "true");
    require_same_release(&plan.release, &promoted)
}

fn require_publishable(release: &ReleaseState) -> Result<(), String> {
    if release.is_draft() || !release.is_immutable() {
        Err("release must be published and immutable before Latest promotion".to_owned())
    } else {
        Ok(())
    }
}

fn require_same_release(expected: &ReleaseState, observed: &ReleaseState) -> Result<(), String> {
    if expected.database_id() == observed.database_id() && expected.tag() == observed.tag() {
        Ok(())
    } else {
        Err("release identity changed during publication".to_owned())
    }
}

fn release_tag(version: &str) -> Result<String, String> {
    release_common::release_tag(version)
        .ok_or_else(|| format!("invalid semver format: {version} (expected X.Y.Z)"))
}

fn finish_release_tag(version: &str) -> Result<String, String> {
    release_common::release_tag(version).ok_or_else(|| format!("invalid semver: {version}"))
}

fn repository(repo: &str) -> Result<RepoSlug, String> {
    release_common::repo_slug(repo).ok_or_else(|| format!("invalid --repo value: {repo}"))
}

fn finish_repository(repo: &str) -> Result<RepoSlug, String> {
    release_common::repo_slug(repo).ok_or_else(|| format!("invalid repository: {repo}"))
}

fn parse_pr(value: &str) -> Result<u64, String> {
    release_common::parse_pr(value).ok_or_else(|| format!("invalid PR number: {value}"))
}

const fn boolean(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_core::RemoteAsset;
    use std::cell::RefCell;

    const SOURCE: &str = "1111111111111111111111111111111111111111";
    const DIGEST: &str = "sha256:2222222222222222222222222222222222222222222222222222222222222222";
    const PRIOR_PIN: &str = "3333333333333333333333333333333333333333";

    struct FakeServices {
        origin: String,
        pr: ReleaseCandidatePullRequest,
        ancestor: bool,
        source_version: String,
        main_version: String,
        release: RefCell<ReleaseState>,
        latest: RefCell<Option<ReleaseState>>,
        newest: Option<ReleaseState>,
        release_missing: bool,
        failure: Option<&'static str>,
        events: RefCell<Vec<&'static str>>,
        pin: RefCell<Option<String>>,
    }

    impl Default for FakeServices {
        fn default() -> Self {
            let release = state(7, true, false, false, "v1.2.3");
            Self {
                origin: "character-ai/larch".to_owned(),
                pr: ReleaseCandidatePullRequest {
                    state: ReleaseCandidatePullRequestState::Merged,
                    head_oid: SOURCE.to_owned(),
                },
                ancestor: true,
                source_version: "1.2.3".to_owned(),
                main_version: "1.2.3".to_owned(),
                release: RefCell::new(release.clone()),
                latest: RefCell::new(Some(state(6, false, true, false, "v1.2.2"))),
                newest: Some(release),
                release_missing: false,
                failure: None,
                events: RefCell::new(Vec::new()),
                pin: RefCell::new(Some(PRIOR_PIN.to_owned())),
            }
        }
    }

    impl Services for FakeServices {
        fn origin_repo(&self) -> Result<String, String> {
            Ok(self.origin.clone())
        }
        fn fetch_main(&self) -> Result<(), String> {
            self.events.borrow_mut().push("fetch");
            Ok(())
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
        fn plugin_version_at(&self, revision: &str) -> Result<String, String> {
            Ok(if revision == ORIGIN_MAIN {
                self.main_version.clone()
            } else {
                self.source_version.clone()
            })
        }
        fn release(&self, _repo: &RepoSlug, _tag: &str) -> Result<Option<ReleaseState>, String> {
            Ok((!self.release_missing).then(|| self.release.borrow().clone()))
        }
        fn validate_assets(
            &self,
            _version: &str,
            _repo: &str,
            _pr: &str,
            _source_commit: &str,
            require_draft: bool,
        ) -> Result<ReleaseState, String> {
            self.events.borrow_mut().push(if require_draft {
                "validate-draft"
            } else {
                "validate-published"
            });
            if self.failure == Some("validate") {
                return Err("asset validation failed".to_owned());
            }
            let release = self.release.borrow().clone();
            if require_draft && !release.is_mutable_draft() {
                return Err("release must remain a mutable draft before merge".to_owned());
            }
            if !require_draft && (release.is_draft() || !release.is_immutable()) {
                return Err("published release must be immutable".to_owned());
            }
            Ok(release)
        }
        fn publish(
            &self,
            _repo: &RepoSlug,
            release: &ReleaseState,
        ) -> Result<ReleaseState, String> {
            self.events.borrow_mut().push("publish");
            if self.failure == Some("publish-identity") {
                return Ok(state(8, false, true, false, release.tag()));
            }
            let published = state(release.database_id(), false, true, false, release.tag());
            *self.release.borrow_mut() = published.clone();
            Ok(published)
        }
        fn verify_release(
            &self,
            _release: &ReleaseState,
            _source_commit: &str,
        ) -> Result<(), String> {
            self.events.borrow_mut().push("verify-attestation");
            if self.failure == Some("attestation") {
                Err("attestation failed".to_owned())
            } else {
                Ok(())
            }
        }
        fn latest(&self, _repo: &RepoSlug) -> Result<Option<ReleaseState>, String> {
            Ok(self.latest.borrow().clone())
        }
        fn newest_published(&self, _repo: &RepoSlug) -> Result<Option<ReleaseState>, String> {
            Ok(self.newest.clone())
        }
        fn promote(
            &self,
            _repo: &RepoSlug,
            release: &ReleaseState,
        ) -> Result<ReleaseState, String> {
            self.events.borrow_mut().push("promote");
            if self.failure == Some("promote") {
                return Err("promotion failed".to_owned());
            }
            let promoted = state(release.database_id(), false, true, false, release.tag());
            if self.failure != Some("postcondition") {
                *self.latest.borrow_mut() = Some(promoted.clone());
            }
            Ok(promoted)
        }
        fn remote_branch_commit(&self, _branch: &str) -> Result<Option<String>, String> {
            self.events.borrow_mut().push("read-pin");
            if self.failure == Some("pin-read") {
                return Err("remote branch read failed".to_owned());
            }
            Ok(self.pin.borrow().clone())
        }
        fn fast_forward_remote_branch(&self, _branch: &str, commit: &str) -> Result<(), String> {
            self.events.borrow_mut().push("advance-pin");
            match self.failure {
                Some("pin-push") => Err("non-fast-forward pin update rejected".to_owned()),
                // A push that reports success but leaves the branch elsewhere is
                // exactly what the re-read after the mutation exists to catch.
                Some("pin-silent-noop") => Ok(()),
                _ => {
                    *self.pin.borrow_mut() = Some(commit.to_owned());
                    Ok(())
                }
            }
        }
    }

    fn state(id: u64, draft: bool, immutable: bool, prerelease: bool, tag: &str) -> ReleaseState {
        let asset = RemoteAsset::new(id, "larch.tar.gz", 1, DIGEST, "uploaded").expect("asset");
        ReleaseState::new(id, tag, draft, immutable, vec![asset])
            .expect("release")
            .with_publication(prerelease, Some("2026-07-19T01:00:00Z".to_owned()))
    }

    fn finish(services: &FakeServices) -> Result<&'static str, String> {
        finish_with(services, "1.2.3", "character-ai/larch", "7", SOURCE)
    }

    #[test]
    fn finish_publishes_only_after_validation_and_promotes_after_attestation() {
        let services = FakeServices::default();
        assert_eq!(finish(&services), Ok("publish"));
        assert_eq!(
            services.events.borrow().as_slice(),
            [
                "fetch",
                "validate-draft",
                "publish",
                "validate-published",
                "verify-attestation",
                "promote",
                "read-pin",
                "advance-pin",
                "read-pin",
            ]
        );
        assert_eq!(services.pin.borrow().as_deref(), Some(SOURCE));
    }

    #[test]
    fn pin_advances_only_after_publication_verification_and_promotion_succeed() {
        for failure in ["validate", "attestation", "promote", "postcondition"] {
            let services = FakeServices {
                failure: Some(failure),
                ..FakeServices::default()
            };
            assert!(finish(&services).is_err(), "{failure} must fail closed");
            assert!(
                !services.events.borrow().contains(&"advance-pin"),
                "{failure} must not advance the release pin"
            );
            assert_eq!(services.pin.borrow().as_deref(), Some(PRIOR_PIN));
        }
    }

    #[test]
    fn pin_advance_is_idempotent_and_creates_a_missing_pin() {
        let already_pinned = FakeServices {
            pin: RefCell::new(Some(SOURCE.to_owned())),
            ..FakeServices::default()
        };
        assert_eq!(finish(&already_pinned), Ok("publish"));
        assert!(!already_pinned.events.borrow().contains(&"advance-pin"));

        let unborn = FakeServices {
            pin: RefCell::new(None),
            ..FakeServices::default()
        };
        assert_eq!(finish(&unborn), Ok("publish"));
        assert_eq!(unborn.pin.borrow().as_deref(), Some(SOURCE));
    }

    #[test]
    fn pin_failures_fail_the_release_instead_of_reporting_a_pinned_install() {
        let rejected = FakeServices {
            failure: Some("pin-push"),
            ..FakeServices::default()
        };
        assert!(
            finish(&rejected)
                .unwrap_err()
                .contains("non-fast-forward pin update rejected")
        );

        let unreadable = FakeServices {
            failure: Some("pin-read"),
            ..FakeServices::default()
        };
        assert!(
            finish(&unreadable)
                .unwrap_err()
                .contains("remote branch read failed")
        );

        // The re-read, not the push's own exit status, decides the outcome.
        let silent = FakeServices {
            failure: Some("pin-silent-noop"),
            ..FakeServices::default()
        };
        let error = finish(&silent).unwrap_err();
        assert!(error.contains(RELEASE_PIN_REF) && error.contains(PRIOR_PIN));

        let vanished = FakeServices {
            failure: Some("pin-silent-noop"),
            pin: RefCell::new(None),
            ..FakeServices::default()
        };
        assert!(
            finish(&vanished)
                .unwrap_err()
                .contains("missing after push")
        );
    }

    #[test]
    fn sole_remote_commit_rejects_ambiguous_and_malformed_remote_answers() {
        let reference = format!("refs/heads/{RELEASE_PIN_REF}");
        assert_eq!(sole_remote_commit("", &reference), Ok(None));
        assert_eq!(
            sole_remote_commit(&format!("{SOURCE}\t{reference}\n"), &reference),
            Ok(Some(SOURCE.to_owned()))
        );
        // A prefix match such as refs/heads/release-notes must not be selected.
        assert_eq!(
            sole_remote_commit(&format!("{SOURCE}\t{reference}-notes\n"), &reference),
            Ok(None)
        );
        assert!(
            sole_remote_commit(
                &format!("{SOURCE}\t{reference}\n{PRIOR_PIN}\t{reference}\n"),
                &reference
            )
            .unwrap_err()
            .contains("more than once")
        );
        assert!(
            sole_remote_commit(&format!("not-a-commit\t{reference}\n"), &reference)
                .unwrap_err()
                .contains("invalid commit")
        );
    }

    #[test]
    fn marketplace_descriptor_pins_the_release_ref() {
        let descriptor = std::fs::read_to_string(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../../.claude-plugin/marketplace.json"),
        )
        .expect("marketplace descriptor");
        let value: serde_json::Value =
            serde_json::from_str(&descriptor).expect("descriptor is valid JSON");
        let source = value["plugins"]
            .as_array()
            .expect("plugins array")
            .iter()
            .find(|plugin| plugin["name"] == "larch")
            .map(|plugin| plugin["source"].clone())
            .expect("larch plugin entry");
        assert_eq!(source["source"], "git-subdir");
        assert_eq!(source["path"], "plugin");
        assert_eq!(
            source["ref"], RELEASE_PIN_REF,
            "the descriptor must pin installed plugin content to the release branch"
        );
    }

    #[test]
    fn published_recovery_never_republishes() {
        let published = state(7, false, true, false, "v1.2.3");
        let services = FakeServices {
            release: RefCell::new(published.clone()),
            latest: RefCell::new(Some(published)),
            ..FakeServices::default()
        };
        assert_eq!(finish(&services), Ok("resume-published"));
        assert!(!services.events.borrow().contains(&"publish"));
        assert!(!services.events.borrow().contains(&"promote"));
    }

    #[test]
    fn published_recovery_clears_prerelease_even_when_candidate_is_latest() {
        let published = state(7, false, true, true, "v1.2.3");
        let services = FakeServices {
            release: RefCell::new(published.clone()),
            latest: RefCell::new(Some(published)),
            ..FakeServices::default()
        };
        assert_eq!(finish(&services), Ok("resume-published"));
        assert!(!services.events.borrow().contains(&"publish"));
        assert!(services.events.borrow().contains(&"promote"));
        assert!(!services.latest.borrow().as_ref().unwrap().is_prerelease());
    }

    #[test]
    fn finish_rejects_ancestry_version_and_mutability_drift() {
        let ancestry = FakeServices {
            ancestor: false,
            ..FakeServices::default()
        };
        assert!(finish(&ancestry).unwrap_err().contains("not an ancestor"));

        let version = FakeServices {
            main_version: "1.2.4".to_owned(),
            ..FakeServices::default()
        };
        assert!(finish(&version).unwrap_err().contains("origin/main"));

        let mutable = FakeServices {
            release: RefCell::new(state(7, false, false, false, "v1.2.3")),
            ..FakeServices::default()
        };
        assert!(finish(&mutable).unwrap_err().contains("must be immutable"));
    }

    #[test]
    fn failed_attestation_or_promotion_keeps_the_prior_latest() {
        for failure in ["attestation", "promote"] {
            let services = FakeServices {
                failure: Some(failure),
                ..FakeServices::default()
            };
            assert!(finish(&services).is_err());
            assert_eq!(
                services.latest.borrow().as_ref().map(ReleaseState::tag),
                Some("v1.2.2")
            );
        }
    }

    #[test]
    fn promotion_commands_are_idempotent_and_select_newest_publication() {
        let published = state(7, false, true, true, "v1.2.3");
        let services = FakeServices {
            release: RefCell::new(published.clone()),
            newest: Some(published),
            ..FakeServices::default()
        };
        let outcome = promote_with(&services, "1.2.3", Some("character-ai/larch"))
            .expect("specific promotion");
        assert!(!outcome.was_latest);
        assert!(outcome.cleared_prerelease);
        let plan = latest_plan(&services, "character-ai/larch").expect("plan");
        assert!(apply_latest_plan(&services, &plan).is_ok());
    }

    #[test]
    fn identity_inputs_fail_closed() {
        let services = FakeServices::default();
        assert!(promote_with(&services, "1.2", Some("character-ai/larch")).is_err());
        assert!(promote_with(&services, "1.2.3", Some("bad/repo/extra")).is_err());
        assert!(finish_with(&services, "1.2.3", "character-ai/larch", "0", SOURCE).is_err());
        assert!(finish_with(&services, "1.2.3", "character-ai/larch", "7", "bad",).is_err());
    }

    #[test]
    fn finish_rejects_each_prepublication_boundary() {
        let wrong_origin = FakeServices {
            origin: "someone/else".to_owned(),
            ..FakeServices::default()
        };
        assert_eq!(
            finish(&wrong_origin),
            Err("origin repository does not match --repo".to_owned())
        );
        let open_pr = FakeServices {
            pr: ReleaseCandidatePullRequest {
                state: ReleaseCandidatePullRequestState::Open,
                head_oid: SOURCE.to_owned(),
            },
            ..FakeServices::default()
        };
        assert!(finish(&open_pr).unwrap_err().contains("not merged"));
        let missing = FakeServices {
            release_missing: true,
            ..FakeServices::default()
        };
        assert_eq!(
            finish(&missing),
            Err("staged release is missing".to_owned())
        );
    }

    #[test]
    fn publication_identity_and_latest_postconditions_fail_closed() {
        let publish_identity = FakeServices {
            failure: Some("publish-identity"),
            ..FakeServices::default()
        };
        assert!(
            finish(&publish_identity)
                .unwrap_err()
                .contains("identity changed")
        );
        let postcondition = FakeServices {
            failure: Some("postcondition"),
            ..FakeServices::default()
        };
        assert!(
            finish(&postcondition)
                .unwrap_err()
                .contains("postcondition failed")
        );
    }

    #[test]
    fn promotion_validation_and_messages_cover_all_outcomes() {
        let missing = FakeServices {
            release_missing: true,
            ..FakeServices::default()
        };
        assert!(
            promote_with(&missing, "1.2.3", None)
                .unwrap_err()
                .contains("not found")
        );
        let draft = FakeServices::default();
        assert!(
            promote_with(&draft, "1.2.3", None)
                .unwrap_err()
                .contains("published and immutable")
        );
        let already_latest = PromoteOutcome {
            tag: "v1.2.3".to_owned(),
            was_latest: true,
            cleared_prerelease: false,
        };
        assert!(already_latest.message().contains("already the latest"));
        assert!(
            PromoteOutcome {
                cleared_prerelease: true,
                ..already_latest.clone()
            }
            .message()
            .contains("cleared pre-release")
        );
        assert!(
            PromoteOutcome {
                was_latest: false,
                ..already_latest
            }
            .message()
            .contains("Promoted")
        );
    }

    #[test]
    fn latest_promotion_supports_dry_run_idempotency_and_empty_repositories() {
        let published = state(7, false, true, false, "v1.2.3");
        let services = FakeServices {
            release: RefCell::new(published.clone()),
            newest: Some(published),
            ..FakeServices::default()
        };
        assert!(promote_latest_with(&services, "character-ai/larch", true).is_ok());
        assert!(!services.events.borrow().contains(&"promote"));
        assert!(promote_latest_with(&services, "character-ai/larch", false).is_ok());
        assert!(services.events.borrow().contains(&"promote"));
        let published = state(7, false, true, false, "v1.2.3");
        let already_latest = FakeServices {
            release: RefCell::new(published.clone()),
            latest: RefCell::new(Some(published.clone())),
            newest: Some(published),
            ..FakeServices::default()
        };
        assert!(promote_latest_with(&already_latest, "character-ai/larch", false).is_ok());
        assert!(!already_latest.events.borrow().contains(&"promote"));
        let empty = FakeServices {
            newest: None,
            ..FakeServices::default()
        };
        assert!(
            latest_plan(&empty, "character-ai/larch")
                .unwrap_err()
                .contains("No non-draft releases")
        );
    }

    #[test]
    fn production_request_inputs_are_fixed_and_locally_verifiable() {
        let request = main_fetch_request().expect("fixed fetch request");
        assert!(request.quiet);
        let repository = GixRepository::discover(std::env::current_dir().expect("cwd"))
            .expect("test runs in repository");
        assert_eq!(is_ancestor(&repository, "HEAD", "HEAD"), Ok(true));
        assert!(is_ancestor(&repository, "missing", "HEAD").is_err());
        let release = state(7, false, true, false, "v1.2.3");
        assert!(immutable_release_request(&release, SOURCE).is_ok());
        assert!(immutable_release_request(&release, "bad").is_err());
    }
}
