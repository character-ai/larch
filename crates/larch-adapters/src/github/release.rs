//! Typed GitHub release and bounded asset service operations.
//!
//! Each operation builds a path from a validated `owner/repo` slug and numeric
//! ids, never accepts a caller-supplied absolute URL or arbitrary API path, and
//! reconciles ambiguous create, upload, and publish outcomes before any retry.
//! Asset download follows an operation-specific redirect policy that stays
//! HTTPS, strips the credential across origins, rejects loops and hop overruns,
//! and bounds the streamed body by a per-asset byte cap.

use super::{GitHubCompletionError, GitHubHostError, OctocrabGitHubService, validate_approved_url};
use bytes::Bytes;
use http::header::{HeaderMap, HeaderName};
use http_body_util::combinators::BoxBody;
use http_body_util::{BodyExt, Limited};
use larch_core::{
    ASSET_MEDIA_TYPE, AssetStreamGuard, GitHubFailureInput, GitHubRateLimitInputs,
    GitHubRequestKind, GitHubRetryAction, ProcessCancellation, ReconciledMutation,
    ReleaseDataError, ReleaseState, RemoteAsset, SafeText, TagObjectId, classify_github_retry,
    reconcile_mutation, require_asset_content_type, resolve_tag_object_id, select_release_for_tag,
};
use octocrab::models::repos::{Asset, Release};
use octocrab::repos::releases::MakeLatest;
use std::{error::Error, fmt, future::Future, pin::Pin};
use url::Url;

const MAX_ASSET_REDIRECTS: usize = 5;
const API_HOST: &str = "api.github.com";

/// A validated `owner/repo` slug that is safe to interpolate into a typed path.
///
/// Validating at the boundary keeps a hostile label out of a constructed API
/// path; no operation ever accepts a caller-supplied absolute URL or raw path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepoSlug {
    owner: String,
    repo: String,
}

impl RepoSlug {
    /// Validate an `owner/repo` slug against the release-path allowlist.
    ///
    /// # Errors
    /// Returns [`GitHubHostError::InvalidUrl`] when either segment is empty or
    /// contains a character outside `[A-Za-z0-9_.-]`.
    pub fn parse(owner: &str, repo: &str) -> Result<Self, GitHubHostError> {
        if is_path_segment(owner) && is_path_segment(repo) {
            Ok(Self {
                owner: owner.to_owned(),
                repo: repo.to_owned(),
            })
        } else {
            Err(GitHubHostError::InvalidUrl)
        }
    }

    /// Render the `owner/repo` path segment.
    #[must_use]
    pub fn path(&self) -> String {
        format!("{}/{}", self.owner, self.repo)
    }

    /// Borrow the owner segment.
    #[must_use]
    pub fn owner(&self) -> &str {
        &self.owner
    }

    /// Borrow the repository segment.
    #[must_use]
    pub fn repo(&self) -> &str {
        &self.repo
    }
}

fn is_path_segment(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 100
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"_.-".contains(&byte))
}

/// A failure raised by a typed release or asset operation.
///
/// Every variant is secret-free: transport detail is redacted before storage,
/// and status codes are the only untrusted values retained.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReleaseServiceError {
    /// A release or asset value failed its core contract.
    Data(ReleaseDataError),
    /// A redirect target failed the download host policy.
    Host(GitHubHostError),
    /// The operation was cancelled or exceeded its deadline.
    Completion(GitHubCompletionError),
    /// A redirect chain revisited a URL it had already followed.
    RedirectLoop,
    /// A redirect chain exceeded the bounded hop count.
    TooManyRedirects,
    /// A download hop returned a status other than success.
    UnexpectedStatus(u16),
    /// A download body exceeded the per-asset byte cap before completing.
    AssetTooLarge,
    /// A mutation's transport outcome was ambiguous and must be reconciled.
    AmbiguousMutation,
    /// An ambiguous mutation reconciled to a lost effect that must not retry.
    MutationLost,
    /// The transport failed with an already-redacted diagnostic.
    Transport(SafeText),
}

impl fmt::Display for ReleaseServiceError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Data(error) => error.fmt(formatter),
            Self::Host(error) => error.fmt(formatter),
            Self::Completion(error) => error.fmt(formatter),
            Self::RedirectLoop => formatter.write_str("GitHub asset redirect chain looped"),
            Self::TooManyRedirects => {
                formatter.write_str("GitHub asset redirect chain exceeded the hop limit")
            }
            Self::UnexpectedStatus(status) => {
                write!(formatter, "GitHub asset download returned status {status}")
            }
            Self::AssetTooLarge => {
                formatter.write_str("GitHub asset download exceeded the per-asset byte cap")
            }
            Self::AmbiguousMutation => formatter
                .write_str("GitHub mutation outcome was ambiguous and awaits reconciliation"),
            Self::MutationLost => formatter
                .write_str("GitHub mutation could not be reconciled after an ambiguous outcome"),
            Self::Transport(detail) => write!(formatter, "GitHub transport failed: {detail}"),
        }
    }
}

impl Error for ReleaseServiceError {}

impl From<ReleaseDataError> for ReleaseServiceError {
    fn from(error: ReleaseDataError) -> Self {
        Self::Data(error)
    }
}

impl From<GitHubHostError> for ReleaseServiceError {
    fn from(error: GitHubHostError) -> Self {
        Self::Host(error)
    }
}

impl From<GitHubCompletionError> for ReleaseServiceError {
    fn from(error: GitHubCompletionError) -> Self {
        Self::Completion(error)
    }
}

/// Fields for creating one draft release for a tagged, immutable publish.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DraftReleaseInput {
    pub tag: String,
    pub target_commitish: String,
    pub body: String,
}

/// One asset upload payload bound for a staged draft release.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AssetUpload {
    pub name: String,
    pub content: Vec<u8>,
}

/// One validated download hop plus whether the credential must be stripped
/// because the origin changed, and the per-asset cap that bounds its body.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FetchRequest {
    pub url: Url,
    pub strip_authorization: bool,
    pub max_bytes: u64,
}

/// The result of a single download hop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum FetchOutcome {
    /// A redirect to the given location value.
    Redirect { location: String },
    /// A terminal body response with its advertised metadata.
    Body {
        status: u16,
        content_type: Option<String>,
        content_length: Option<u64>,
        body: Vec<u8>,
    },
}

/// Future returned by the release transport seam.
pub type ReleaseFuture<'a, T> =
    Pin<Box<dyn Future<Output = Result<T, ReleaseServiceError>> + Send + 'a>>;

/// Injectable transport seam for typed release and asset operations.
///
/// Production wiring is backed by the hardened Octocrab client; tests drive the
/// same operations and policy with loopback fixtures. Implementations never
/// expose a raw URL or an arbitrary API path to a caller.
pub trait ReleaseTransport: Send + Sync {
    /// List releases on the bounded first page for duplicate-safe selection.
    fn list_releases<'a>(&'a self, repo: &RepoSlug) -> ReleaseFuture<'a, Vec<ReleaseState>>;
    /// Read the repository's current Latest release.
    fn latest_release<'a>(&'a self, repo: &RepoSlug) -> ReleaseFuture<'a, Option<ReleaseState>>;
    /// Resolve the object id a tag points at, preferring the peeled target.
    fn resolve_tag<'a>(
        &'a self,
        repo: &RepoSlug,
        tag: &str,
    ) -> ReleaseFuture<'a, Option<TagObjectId>>;
    /// Report whether immutable releases are enabled for the repository.
    fn immutable_releases_enabled<'a>(&'a self, repo: &RepoSlug) -> ReleaseFuture<'a, bool>;
    /// Report whether merge commits are enabled for the repository.
    fn merge_commits_enabled<'a>(&'a self, repo: &RepoSlug) -> ReleaseFuture<'a, bool>;
    /// Enable merge commits through the fixed repository-settings operation.
    fn enable_merge_commits<'a>(&'a self, repo: &RepoSlug) -> ReleaseFuture<'a, ()>;
    /// Enable immutable releases through the fixed repository-settings operation.
    fn enable_immutable_releases<'a>(&'a self, repo: &RepoSlug) -> ReleaseFuture<'a, ()>;
    /// Create one draft release.
    fn create_draft_release<'a>(
        &'a self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> ReleaseFuture<'a, ReleaseState>;
    /// Update the title and body of one existing mutable draft.
    fn update_draft_release<'a>(
        &'a self,
        repo: &RepoSlug,
        release_id: u64,
        input: &DraftReleaseInput,
    ) -> ReleaseFuture<'a, ReleaseState>;
    /// Read the body of one release for exact update reconciliation.
    fn release_body<'a>(&'a self, repo: &RepoSlug, release_id: u64) -> ReleaseFuture<'a, String>;
    /// Publish a staged draft release by database id.
    fn publish_release<'a>(
        &'a self,
        repo: &RepoSlug,
        release_id: u64,
    ) -> ReleaseFuture<'a, ReleaseState>;
    /// Clear prerelease and mark one published release as Latest.
    fn promote_release<'a>(
        &'a self,
        repo: &RepoSlug,
        release_id: u64,
    ) -> ReleaseFuture<'a, ReleaseState>;
    /// Upload one asset to a staged draft release.
    fn upload_asset<'a>(
        &'a self,
        repo: &RepoSlug,
        release_id: u64,
        upload: &AssetUpload,
    ) -> ReleaseFuture<'a, RemoteAsset>;
    /// Perform one download hop without following redirects.
    fn fetch_asset_hop<'a>(&'a self, request: &FetchRequest) -> ReleaseFuture<'a, FetchOutcome>;
}

/// Validate one asset-download redirect target under the download host policy.
///
/// Unlike the same-origin API continuation policy, an asset download may leave
/// the API origin for a signed CDN. The target must stay HTTPS (no downgrade),
/// carry no embedded credentials, and the credential is stripped whenever the
/// origin changes.
///
/// # Errors
/// Rejects a malformed, non-HTTPS, or credential-bearing redirect target.
pub fn validate_download_redirect(
    current: &Url,
    location: &str,
    max_bytes: u64,
) -> Result<FetchRequest, GitHubHostError> {
    let next = current
        .join(location)
        .map_err(|_| GitHubHostError::InvalidUrl)?;
    let acceptable = next.scheme() == "https"
        && next.host_str().is_some()
        && next.username().is_empty()
        && next.password().is_none();
    if !acceptable {
        return Err(GitHubHostError::UnapprovedOrigin);
    }
    let strip_authorization = next.host_str() != Some(API_HOST);
    Ok(FetchRequest {
        url: next,
        strip_authorization,
        max_bytes,
    })
}

fn finish_download(
    status: u16,
    content_type: Option<&str>,
    content_length: Option<u64>,
    body: Vec<u8>,
    max_bytes: u64,
) -> Result<Vec<u8>, ReleaseServiceError> {
    if status != 200 {
        return Err(ReleaseServiceError::UnexpectedStatus(status));
    }
    require_asset_content_type(content_type.unwrap_or_default())?;
    let mut guard = AssetStreamGuard::new(max_bytes, content_length);
    guard.accept(body.len())?;
    guard.finish()?;
    Ok(body)
}

/// Typed release and asset service operations over an injected transport.
///
/// This layer owns release selection, ambiguous-mutation reconciliation, and
/// bounded, redirect-validated downloads. Release orchestration and the
/// immutable-publish state machine stay with their owning caller.
pub struct ReleaseOperations<'a, T: ReleaseTransport> {
    transport: &'a T,
}

impl<'a, T: ReleaseTransport> ReleaseOperations<'a, T> {
    /// Bind typed operations to a transport.
    #[must_use]
    pub const fn new(transport: &'a T) -> Self {
        Self { transport }
    }

    /// Select the single release that claims `tag`, rejecting duplicates.
    ///
    /// # Errors
    /// Fails when the transport fails or two releases share the tag.
    pub async fn release_for_tag(
        &self,
        repo: &RepoSlug,
        tag: &str,
    ) -> Result<Option<ReleaseState>, ReleaseServiceError> {
        let releases = self.transport.list_releases(repo).await?;
        Ok(select_release_for_tag(tag, releases)?)
    }

    /// Select the most recently published non-draft release.
    ///
    /// # Errors
    /// Fails when the bounded release list cannot be read.
    pub async fn newest_published_release(
        &self,
        repo: &RepoSlug,
    ) -> Result<Option<ReleaseState>, ReleaseServiceError> {
        let releases = self.transport.list_releases(repo).await?;
        Ok(releases
            .into_iter()
            .filter(|release| !release.is_draft() && release.published_at().is_some())
            .max_by(|left, right| left.published_at().cmp(&right.published_at())))
    }

    /// Read the repository's current Latest release.
    ///
    /// # Errors
    /// Fails when the owning GitHub surface cannot be read.
    pub async fn latest_release(
        &self,
        repo: &RepoSlug,
    ) -> Result<Option<ReleaseState>, ReleaseServiceError> {
        self.transport.latest_release(repo).await
    }

    /// Create a draft release, reconciling an ambiguous create before retry.
    ///
    /// # Errors
    /// Fails when the transport fails, or when an ambiguous create cannot be
    /// reconciled to a landed release.
    pub async fn stage_draft_release(
        &self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, ReleaseServiceError> {
        let state = match self.transport.create_draft_release(repo, input).await {
            Ok(state) => state,
            Err(error) if is_ambiguous_write(&error) => self.reconcile_create(repo, input).await?,
            Err(other) => return Err(other),
        };
        if state.tag() != input.tag
            || !state.is_mutable_draft()
            || self
                .transport
                .release_body(repo, state.database_id())
                .await?
                != input.body
        {
            return Err(ReleaseServiceError::MutationLost);
        }
        Ok(state)
    }

    /// Update a mutable draft and verify the exact body on both clear and
    /// ambiguous mutation outcomes.
    ///
    /// # Errors
    /// Fails when the update or its owning-surface read-back fails.
    pub async fn update_draft_release(
        &self,
        repo: &RepoSlug,
        release: &ReleaseState,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, ReleaseServiceError> {
        if !release.is_mutable_draft() {
            return Err(ReleaseServiceError::MutationLost);
        }
        let result = self
            .transport
            .update_draft_release(repo, release.database_id(), input)
            .await;
        match result {
            Ok(_) => {}
            Err(error) if is_ambiguous_write(&error) => {}
            Err(other) => return Err(other),
        }
        if self
            .transport
            .release_body(repo, release.database_id())
            .await?
            != input.body
        {
            return Err(ReleaseServiceError::MutationLost);
        }
        let observed = self
            .release_for_tag(repo, &input.tag)
            .await?
            .ok_or(ReleaseServiceError::MutationLost)?;
        if observed.database_id() != release.database_id() || !observed.is_mutable_draft() {
            return Err(ReleaseServiceError::MutationLost);
        }
        Ok(observed)
    }

    async fn reconcile_create(
        &self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> Result<ReleaseState, ReleaseServiceError> {
        let existing = self.release_for_tag(repo, &input.tag).await?;
        match reconcile_mutation(GitHubRetryAction::ReconcileMutation, existing.is_some()) {
            ReconciledMutation::AlreadyApplied => existing.ok_or(ReleaseServiceError::MutationLost),
            _ => self.transport.create_draft_release(repo, input).await,
        }
    }

    /// Publish a draft release, reconciling an ambiguous publish before retry.
    ///
    /// # Errors
    /// Fails when the transport fails, or when an ambiguous publish cannot be
    /// reconciled to a published release.
    pub async fn publish_release(
        &self,
        repo: &RepoSlug,
        release: &ReleaseState,
    ) -> Result<ReleaseState, ReleaseServiceError> {
        match self
            .transport
            .publish_release(repo, release.database_id())
            .await
        {
            Ok(state) => Ok(state),
            Err(error) if is_ambiguous_write(&error) => {
                let observed = self.release_for_tag(repo, release.tag()).await?;
                let applied = observed.as_ref().is_some_and(|state| !state.is_draft());
                match reconcile_mutation(GitHubRetryAction::ReconcileMutation, applied) {
                    ReconciledMutation::AlreadyApplied => {
                        observed.ok_or(ReleaseServiceError::MutationLost)
                    }
                    _ => {
                        self.transport
                            .publish_release(repo, release.database_id())
                            .await
                    }
                }
            }
            Err(other) => Err(other),
        }
    }

    /// Promote one published release to Latest and verify the owning surface.
    ///
    /// An ambiguous first write is retried only after Latest read-back proves
    /// the effect absent. Every success path re-reads Latest and prerelease
    /// state before returning.
    ///
    /// # Errors
    /// Fails on a definite mutation error or when read-back does not show the
    /// requested release as non-draft, non-prerelease Latest.
    pub async fn promote_release(
        &self,
        repo: &RepoSlug,
        release: &ReleaseState,
    ) -> Result<ReleaseState, ReleaseServiceError> {
        if release.is_draft() {
            return Err(ReleaseServiceError::MutationLost);
        }
        let first = self
            .transport
            .promote_release(repo, release.database_id())
            .await;
        match first {
            Ok(_) => {}
            Err(error) if is_ambiguous_write(&error) => {
                if let Some(observed) = self.promoted_state(repo, release.database_id()).await? {
                    return Ok(observed);
                }
                let retry = self
                    .transport
                    .promote_release(repo, release.database_id())
                    .await;
                if let Err(error) = retry
                    && !is_ambiguous_write(&error)
                {
                    return Err(error);
                }
            }
            Err(other) => return Err(other),
        }
        self.promoted_state(repo, release.database_id())
            .await?
            .ok_or(ReleaseServiceError::MutationLost)
    }

    async fn promoted_state(
        &self,
        repo: &RepoSlug,
        release_id: u64,
    ) -> Result<Option<ReleaseState>, ReleaseServiceError> {
        Ok(self.latest_release(repo).await?.filter(|release| {
            release.database_id() == release_id && !release.is_draft() && !release.is_prerelease()
        }))
    }

    /// Upload an asset, reconciling an ambiguous upload before retry.
    ///
    /// # Errors
    /// Fails when the transport fails, or when an ambiguous upload cannot be
    /// reconciled to a present asset.
    pub async fn upload_asset(
        &self,
        repo: &RepoSlug,
        release: &ReleaseState,
        upload: &AssetUpload,
    ) -> Result<RemoteAsset, ReleaseServiceError> {
        match self
            .transport
            .upload_asset(repo, release.database_id(), upload)
            .await
        {
            Ok(asset) => Ok(asset),
            Err(error) if is_ambiguous_write(&error) => {
                let observed = self.release_for_tag(repo, release.tag()).await?;
                let landed = observed
                    .as_ref()
                    .and_then(|state| find_asset(state, &upload.name).cloned());
                match reconcile_mutation(GitHubRetryAction::ReconcileMutation, landed.is_some()) {
                    ReconciledMutation::AlreadyApplied => {
                        landed.ok_or(ReleaseServiceError::MutationLost)
                    }
                    _ => {
                        self.transport
                            .upload_asset(repo, release.database_id(), upload)
                            .await
                    }
                }
            }
            Err(other) => Err(other),
        }
    }

    /// Resolve the object id a release tag points at.
    ///
    /// # Errors
    /// Fails when the transport fails or the id is not a Git object id.
    pub async fn tag_object_id(
        &self,
        repo: &RepoSlug,
        tag: &str,
    ) -> Result<Option<TagObjectId>, ReleaseServiceError> {
        self.transport.resolve_tag(repo, tag).await
    }

    /// Report whether immutable releases are enabled for the repository.
    ///
    /// # Errors
    /// Fails when the transport fails.
    pub async fn immutable_releases_enabled(
        &self,
        repo: &RepoSlug,
    ) -> Result<bool, ReleaseServiceError> {
        self.transport.immutable_releases_enabled(repo).await
    }

    /// Verify both repository settings required by the release state machine.
    ///
    /// # Errors
    /// Fails unless merge commits and immutable releases are both enabled.
    pub async fn verify_repository_policy(
        &self,
        repo: &RepoSlug,
    ) -> Result<bool, ReleaseServiceError> {
        let (merge_commits, immutable_releases) = self.repository_policy(repo).await?;
        Ok(merge_commits && immutable_releases)
    }

    /// Read both repository settings required by release staging.
    ///
    /// # Errors
    /// Fails when either owning read surface fails.
    pub async fn repository_policy(
        &self,
        repo: &RepoSlug,
    ) -> Result<(bool, bool), ReleaseServiceError> {
        Ok((
            self.transport.merge_commits_enabled(repo).await?,
            self.transport.immutable_releases_enabled(repo).await?,
        ))
    }

    /// Enable both required settings and verify them on the owning read surfaces.
    ///
    /// # Errors
    /// Fails on a definite mutation error or when read-back does not show both
    /// settings enabled. Ambiguous writes are reconciled by the same read-back.
    pub async fn ensure_repository_policy(
        &self,
        repo: &RepoSlug,
    ) -> Result<(), ReleaseServiceError> {
        let merge = self.transport.enable_merge_commits(repo).await;
        if let Err(error) = &merge
            && !is_ambiguous_write(error)
        {
            return merge;
        }
        let immutable = self.transport.enable_immutable_releases(repo).await;
        if let Err(error) = &immutable
            && !is_ambiguous_write(error)
        {
            return immutable;
        }
        if self.verify_repository_policy(repo).await? {
            Ok(())
        } else {
            Err(ReleaseServiceError::MutationLost)
        }
    }

    /// Download one release asset by id under the bounded, redirect-safe policy.
    ///
    /// The start URL is constructed from the validated repository and asset id,
    /// never supplied by the caller. Each hop is size-, content-type-,
    /// redirect-, origin-, and loop-bounded.
    ///
    /// # Errors
    /// Fails on a transport error, an unsafe redirect, an over-cap or truncated
    /// body, an unexpected content type, or a redirect loop or hop overrun.
    pub async fn download_asset(
        &self,
        repo: &RepoSlug,
        asset_id: u64,
        max_bytes: u64,
    ) -> Result<Vec<u8>, ReleaseServiceError> {
        let start = asset_download_url(repo, asset_id)?;
        validate_approved_url(&start)?;
        let mut current = FetchRequest {
            url: start,
            strip_authorization: false,
            max_bytes,
        };
        let mut visited = vec![current.url.as_str().to_owned()];
        for _ in 0..=MAX_ASSET_REDIRECTS {
            match self.transport.fetch_asset_hop(&current).await? {
                FetchOutcome::Redirect { location } => {
                    let next = validate_download_redirect(&current.url, &location, max_bytes)?;
                    if visited.iter().any(|seen| seen == next.url.as_str()) {
                        return Err(ReleaseServiceError::RedirectLoop);
                    }
                    visited.push(next.url.as_str().to_owned());
                    current = next;
                }
                FetchOutcome::Body {
                    status,
                    content_type,
                    content_length,
                    body,
                } => {
                    return finish_download(
                        status,
                        content_type.as_deref(),
                        content_length,
                        body,
                        max_bytes,
                    );
                }
            }
        }
        Err(ReleaseServiceError::TooManyRedirects)
    }
}

/// Find one asset by name inside a release state.
#[must_use]
pub fn find_asset<'a>(release: &'a ReleaseState, name: &str) -> Option<&'a RemoteAsset> {
    release.assets().iter().find(|asset| asset.name() == name)
}

fn asset_download_url(repo: &RepoSlug, asset_id: u64) -> Result<Url, GitHubHostError> {
    Url::parse(&format!(
        "https://{API_HOST}/repos/{}/releases/assets/{asset_id}",
        repo.path()
    ))
    .map_err(|_| GitHubHostError::InvalidUrl)
}

const fn is_ambiguous_write(error: &ReleaseServiceError) -> bool {
    matches!(
        error,
        ReleaseServiceError::AmbiguousMutation
            | ReleaseServiceError::Completion(GitHubCompletionError::DeadlineExceeded)
    )
}

type OctoResponse = http::Response<BoxBody<Bytes, octocrab::Error>>;

/// Production release transport backed by the hardened Octocrab client.
///
/// Every network exchange runs inside the shared operation guard, so a
/// cancelled or timed-out operation returns a closed completion error rather
/// than a partial result. No method accepts a caller-supplied path or URL:
/// paths are constructed from the validated repository slug and object ids.
pub struct OctocrabReleaseTransport<'a> {
    service: &'a OctocrabGitHubService,
    cancellation: &'a dyn ProcessCancellation,
}

impl<'a> OctocrabReleaseTransport<'a> {
    /// Bind the transport to a hardened service and a cancellation source.
    #[must_use]
    pub const fn new(
        service: &'a OctocrabGitHubService,
        cancellation: &'a dyn ProcessCancellation,
    ) -> Self {
        Self {
            service,
            cancellation,
        }
    }

    async fn guard<T: Send>(
        &self,
        operation: impl Future<Output = Result<T, ReleaseServiceError>> + Send,
    ) -> Result<T, ReleaseServiceError> {
        match self
            .service
            .guard_operation(self.cancellation, operation)
            .await
        {
            Ok(result) => result,
            Err(completion) => Err(ReleaseServiceError::Completion(completion)),
        }
    }

    fn transport_error(&self, error: &octocrab::Error) -> ReleaseServiceError {
        ReleaseServiceError::Transport(self.service.redact_diagnostic(error.to_string()))
    }

    fn mutation_error(&self, error: &octocrab::Error) -> ReleaseServiceError {
        let failure = match error {
            octocrab::Error::GitHub { source, .. } => {
                GitHubFailureInput::HttpStatus(source.status_code.as_u16())
            }
            _ => GitHubFailureInput::Transport,
        };
        match classify_github_retry(
            GitHubRequestKind::Mutation,
            failure,
            GitHubRateLimitInputs::NONE,
        ) {
            GitHubRetryAction::ReconcileMutation => ReleaseServiceError::AmbiguousMutation,
            _ => self.transport_error(error),
        }
    }

    async fn get_json(
        &self,
        url: String,
    ) -> Result<Option<serde_json::Value>, ReleaseServiceError> {
        let response = match self.service.client._get(url).await {
            Ok(response) => response,
            Err(octocrab::Error::GitHub { source, .. }) if source.status_code.as_u16() == 404 => {
                return Ok(None);
            }
            Err(error) => return Err(self.transport_error(&error)),
        };
        let cap = self.service.policy.limits().body_bytes();
        let body = collect_bounded(response, cap).await?;
        serde_json::from_slice(&body)
            .map(Some)
            .map_err(|error| self.transport_error_from(&error))
    }

    fn transport_error_from(
        &self,
        error: &(impl std::error::Error + ?Sized),
    ) -> ReleaseServiceError {
        ReleaseServiceError::Transport(self.service.redact_diagnostic(error.to_string()))
    }

    async fn fetch_outcome(
        &self,
        response: OctoResponse,
        max_bytes: u64,
    ) -> Result<FetchOutcome, ReleaseServiceError> {
        let status = response.status().as_u16();
        if let Some(location) = header_string(response.headers(), &http::header::LOCATION) {
            return Ok(FetchOutcome::Redirect { location });
        }
        let content_type = header_string(response.headers(), &http::header::CONTENT_TYPE);
        let content_length = header_string(response.headers(), &http::header::CONTENT_LENGTH)
            .and_then(|value| value.parse::<u64>().ok());
        if content_length.is_some_and(|length| length > max_bytes) {
            return Err(ReleaseServiceError::AssetTooLarge);
        }
        let cap = usize::try_from(max_bytes).unwrap_or(usize::MAX);
        let body = collect_bounded(response, cap).await?;
        Ok(FetchOutcome::Body {
            status,
            content_type,
            content_length,
            body,
        })
    }
}

async fn collect_bounded(
    response: OctoResponse,
    max_bytes: usize,
) -> Result<Vec<u8>, ReleaseServiceError> {
    Limited::new(response.into_body(), max_bytes)
        .collect()
        .await
        .map(|collected| collected.to_bytes().to_vec())
        .map_err(|_| ReleaseServiceError::AssetTooLarge)
}

fn header_string(headers: &HeaderMap, name: &HeaderName) -> Option<String> {
    headers
        .get(name)
        .and_then(|value| value.to_str().ok())
        .map(str::to_owned)
}

fn ref_object(value: &serde_json::Value) -> Result<(String, String), ReleaseServiceError> {
    let object = value.get("object");
    let sha = object
        .and_then(|object| object.get("sha"))
        .and_then(serde_json::Value::as_str);
    let kind = object
        .and_then(|object| object.get("type"))
        .and_then(serde_json::Value::as_str);
    match (sha, kind) {
        (Some(sha), Some(kind)) => Ok((sha.to_owned(), kind.to_owned())),
        _ => Err(ReleaseServiceError::Data(
            TagObjectId::parse("").expect_err("an empty object id is never a valid tag reference"),
        )),
    }
}

fn map_release(release: &Release) -> Result<ReleaseState, ReleaseServiceError> {
    let assets = release
        .assets
        .iter()
        .map(map_asset)
        .collect::<Result<Vec<_>, _>>()?;
    ReleaseState::new(
        release.id.into_inner(),
        &release.tag_name,
        release.draft,
        release.immutable.unwrap_or(false),
        assets,
    )
    .map(|state| {
        let published_at = release
            .published_at
            .as_ref()
            .or(release.created_at.as_ref())
            .map(ToString::to_string);
        state.with_publication(release.prerelease, published_at)
    })
    .map_err(ReleaseServiceError::Data)
}

fn map_asset(asset: &Asset) -> Result<RemoteAsset, ReleaseServiceError> {
    let size = u64::try_from(asset.size).unwrap_or(0);
    RemoteAsset::new(
        asset.id.into_inner(),
        &asset.name,
        size,
        asset.digest.as_deref().unwrap_or_default(),
        &asset.state,
    )
    .map_err(ReleaseServiceError::Data)
}

impl ReleaseTransport for OctocrabReleaseTransport<'_> {
    fn list_releases<'b>(&'b self, repo: &RepoSlug) -> ReleaseFuture<'b, Vec<ReleaseState>> {
        let owner = repo.owner().to_owned();
        let name = repo.repo().to_owned();
        Box::pin(self.guard(async move {
            let page = self
                .service
                .client
                .repos(owner, name)
                .releases()
                .list()
                .per_page(100_u8)
                .send()
                .await
                .map_err(|error| self.transport_error(&error))?;
            page.items.iter().map(map_release).collect()
        }))
    }

    fn latest_release<'b>(&'b self, repo: &RepoSlug) -> ReleaseFuture<'b, Option<ReleaseState>> {
        let url = format!("/repos/{}/releases/latest", repo.path());
        Box::pin(self.guard(async move {
            self.get_json(url)
                .await?
                .map(|value| {
                    serde_json::from_value::<Release>(value)
                        .map_err(|_| {
                            ReleaseServiceError::Transport(
                                self.service
                                    .redact_diagnostic("latest release is malformed"),
                            )
                        })
                        .and_then(|release| map_release(&release))
                })
                .transpose()
        }))
    }

    fn resolve_tag<'b>(
        &'b self,
        repo: &RepoSlug,
        tag: &str,
    ) -> ReleaseFuture<'b, Option<TagObjectId>> {
        let base = format!("https://{API_HOST}/repos/{}", repo.path());
        let tag = tag.to_owned();
        Box::pin(self.guard(async move {
            let Some(reference) = self.get_json(format!("{base}/git/ref/tags/{tag}")).await? else {
                return Ok(None);
            };
            let (sha, kind) = ref_object(&reference)?;
            let peeled = if kind == "tag" {
                match self.get_json(format!("{base}/git/tags/{sha}")).await? {
                    Some(object) => Some(ref_object(&object)?.0),
                    None => None,
                }
            } else {
                None
            };
            resolve_tag_object_id(Some(&sha), peeled.as_deref()).map_err(ReleaseServiceError::Data)
        }))
    }

    fn immutable_releases_enabled<'b>(&'b self, repo: &RepoSlug) -> ReleaseFuture<'b, bool> {
        let url = format!(
            "https://{API_HOST}/repos/{}/immutable-releases",
            repo.path()
        );
        Box::pin(self.guard(async move {
            Ok(self
                .get_json(url)
                .await?
                .as_ref()
                .and_then(|value| value.get("enabled"))
                .and_then(serde_json::Value::as_bool)
                .unwrap_or(false))
        }))
    }

    fn merge_commits_enabled<'b>(&'b self, repo: &RepoSlug) -> ReleaseFuture<'b, bool> {
        let url = format!("https://{API_HOST}/repos/{}", repo.path());
        Box::pin(self.guard(async move {
            Ok(self
                .get_json(url)
                .await?
                .as_ref()
                .and_then(|value| value.get("allow_merge_commit"))
                .and_then(serde_json::Value::as_bool)
                .unwrap_or(false))
        }))
    }

    fn enable_merge_commits<'b>(&'b self, repo: &RepoSlug) -> ReleaseFuture<'b, ()> {
        let url = format!("https://{API_HOST}/repos/{}", repo.path());
        Box::pin(self.guard(async move {
            let body = serde_json::json!({"allow_merge_commit": true});
            self.service
                .client
                .patch::<serde_json::Value, _, _>(url, Some(&body))
                .await
                .map(|_| ())
                .map_err(|error| self.mutation_error(&error))
        }))
    }

    fn enable_immutable_releases<'b>(&'b self, repo: &RepoSlug) -> ReleaseFuture<'b, ()> {
        let url = format!(
            "https://{API_HOST}/repos/{}/immutable-releases",
            repo.path()
        );
        Box::pin(self.guard(async move {
            self.service
                .client
                ._put(url, None::<&()>)
                .await
                .map(|_| ())
                .map_err(|error| self.mutation_error(&error))
        }))
    }

    fn create_draft_release<'b>(
        &'b self,
        repo: &RepoSlug,
        input: &DraftReleaseInput,
    ) -> ReleaseFuture<'b, ReleaseState> {
        let owner = repo.owner().to_owned();
        let name = repo.repo().to_owned();
        let input = input.clone();
        Box::pin(self.guard(async move {
            let release = self
                .service
                .client
                .repos(owner, name)
                .releases()
                .create(&input.tag)
                .target_commitish(&input.target_commitish)
                .body(&input.body)
                .draft(true)
                .send()
                .await
                .map_err(|error| self.mutation_error(&error))?;
            map_release(&release)
        }))
    }

    fn update_draft_release<'b>(
        &'b self,
        repo: &RepoSlug,
        release_id: u64,
        input: &DraftReleaseInput,
    ) -> ReleaseFuture<'b, ReleaseState> {
        let url = format!(
            "https://{API_HOST}/repos/{}/releases/{release_id}",
            repo.path()
        );
        let body = serde_json::json!({"name": input.tag, "body": input.body});
        Box::pin(self.guard(async move {
            self.service
                .client
                .patch::<Release, _, _>(url, Some(&body))
                .await
                .map_err(|error| self.mutation_error(&error))
                .and_then(|release| map_release(&release))
        }))
    }

    fn release_body<'b>(&'b self, repo: &RepoSlug, release_id: u64) -> ReleaseFuture<'b, String> {
        let url = format!(
            "https://{API_HOST}/repos/{}/releases/{release_id}",
            repo.path()
        );
        Box::pin(self.guard(async move {
            self.get_json(url)
                .await?
                .and_then(|value| {
                    value
                        .get("body")
                        .and_then(serde_json::Value::as_str)
                        .map(str::to_owned)
                })
                .ok_or_else(|| {
                    ReleaseServiceError::Transport(
                        self.service.redact_diagnostic("release body is missing"),
                    )
                })
        }))
    }

    fn publish_release<'b>(
        &'b self,
        repo: &RepoSlug,
        release_id: u64,
    ) -> ReleaseFuture<'b, ReleaseState> {
        let owner = repo.owner().to_owned();
        let name = repo.repo().to_owned();
        Box::pin(self.guard(async move {
            let release = self
                .service
                .client
                .repos(owner, name)
                .releases()
                .update(release_id)
                .draft(false)
                .prerelease(false)
                .make_latest(MakeLatest::False)
                .send()
                .await
                .map_err(|error| self.mutation_error(&error))?;
            map_release(&release)
        }))
    }

    fn promote_release<'b>(
        &'b self,
        repo: &RepoSlug,
        release_id: u64,
    ) -> ReleaseFuture<'b, ReleaseState> {
        let owner = repo.owner().to_owned();
        let name = repo.repo().to_owned();
        Box::pin(self.guard(async move {
            let release = self
                .service
                .client
                .repos(owner, name)
                .releases()
                .update(release_id)
                .draft(false)
                .prerelease(false)
                .make_latest(MakeLatest::True)
                .send()
                .await
                .map_err(|error| self.mutation_error(&error))?;
            map_release(&release)
        }))
    }

    fn upload_asset<'b>(
        &'b self,
        repo: &RepoSlug,
        release_id: u64,
        upload: &AssetUpload,
    ) -> ReleaseFuture<'b, RemoteAsset> {
        let owner = repo.owner().to_owned();
        let name = repo.repo().to_owned();
        let asset_name = upload.name.clone();
        let content = Bytes::from(upload.content.clone());
        Box::pin(self.guard(async move {
            let asset = self
                .service
                .client
                .repos(owner, name)
                .releases()
                .upload_asset(release_id, &asset_name, content)
                .send()
                .await
                .map_err(|error| self.mutation_error(&error))?;
            map_asset(&asset)
        }))
    }

    fn fetch_asset_hop<'b>(&'b self, request: &FetchRequest) -> ReleaseFuture<'b, FetchOutcome> {
        let url = request.url.to_string();
        let max_bytes = request.max_bytes;
        Box::pin(self.guard(async move {
            let http_request = http::Request::builder()
                .method(http::Method::GET)
                .uri(url)
                .header(http::header::ACCEPT, ASSET_MEDIA_TYPE)
                .body(())
                .map_err(|error| self.transport_error_from(&error))?;
            let response = self
                .service
                .client
                .execute(http_request)
                .await
                .map_err(|error| self.transport_error(&error))?;
            self.fetch_outcome(response, max_bytes).await
        }))
    }
}

#[cfg(test)]
mod release_tests {
    use super::*;
    use crate::runtime::LarchRuntime;
    use larch_core::ReleaseDataErrorKind;
    use std::collections::VecDeque;
    use std::sync::Mutex;

    const DIGEST: &str = "sha256:1111111111111111111111111111111111111111111111111111111111111111";
    const START: &str = "https://api.github.com/repos/o/r/releases/assets/42";
    const CDN: &str = "https://release-assets.githubusercontent.com/download/42";

    type ReleaseQueue<T> = Mutex<VecDeque<Result<T, ReleaseServiceError>>>;

    fn asset(name: &str) -> RemoteAsset {
        RemoteAsset::new(7, name, 4, DIGEST, "uploaded").expect("valid asset")
    }

    fn release(
        id: u64,
        tag: &str,
        draft: bool,
        immutable: bool,
        assets: Vec<RemoteAsset>,
    ) -> ReleaseState {
        ReleaseState::new(id, tag, draft, immutable, assets).expect("valid release")
    }

    fn published(id: u64, tag: &str, prerelease: bool, at: &str) -> ReleaseState {
        release(id, tag, false, true, Vec::new()).with_publication(prerelease, Some(at.to_owned()))
    }

    fn pop<T>(queue: &ReleaseQueue<T>) -> Option<Result<T, ReleaseServiceError>> {
        queue.lock().expect("queue lock").pop_front()
    }

    #[derive(Default)]
    struct FakeTransport {
        releases: Vec<ReleaseState>,
        tag: Option<TagObjectId>,
        immutable: bool,
        merge_commits: bool,
        release_body: String,
        list: ReleaseQueue<Vec<ReleaseState>>,
        latest: ReleaseQueue<Option<ReleaseState>>,
        create: ReleaseQueue<ReleaseState>,
        update: ReleaseQueue<ReleaseState>,
        publish: ReleaseQueue<ReleaseState>,
        promote: ReleaseQueue<ReleaseState>,
        upload: ReleaseQueue<RemoteAsset>,
        hops: ReleaseQueue<FetchOutcome>,
        list_calls: Mutex<usize>,
    }

    impl ReleaseTransport for FakeTransport {
        fn list_releases<'a>(&'a self, _repo: &RepoSlug) -> ReleaseFuture<'a, Vec<ReleaseState>> {
            *self.list_calls.lock().expect("call counter") += 1;
            let scripted = pop(&self.list);
            let fallback = self.releases.clone();
            Box::pin(async move { scripted.unwrap_or(Ok(fallback)) })
        }

        fn latest_release<'a>(
            &'a self,
            _repo: &RepoSlug,
        ) -> ReleaseFuture<'a, Option<ReleaseState>> {
            let outcome = pop(&self.latest);
            Box::pin(async move { outcome.unwrap_or(Ok(None)) })
        }

        fn resolve_tag<'a>(
            &'a self,
            _repo: &RepoSlug,
            _tag: &str,
        ) -> ReleaseFuture<'a, Option<TagObjectId>> {
            let tag = self.tag.clone();
            Box::pin(async move { Ok(tag) })
        }

        fn immutable_releases_enabled<'a>(&'a self, _repo: &RepoSlug) -> ReleaseFuture<'a, bool> {
            let value = self.immutable;
            Box::pin(async move { Ok(value) })
        }

        fn merge_commits_enabled<'a>(&'a self, _repo: &RepoSlug) -> ReleaseFuture<'a, bool> {
            let value = self.merge_commits;
            Box::pin(async move { Ok(value) })
        }

        fn enable_merge_commits<'a>(&'a self, _repo: &RepoSlug) -> ReleaseFuture<'a, ()> {
            Box::pin(async { Ok(()) })
        }

        fn enable_immutable_releases<'a>(&'a self, _repo: &RepoSlug) -> ReleaseFuture<'a, ()> {
            Box::pin(async { Ok(()) })
        }

        fn create_draft_release<'a>(
            &'a self,
            _repo: &RepoSlug,
            _input: &DraftReleaseInput,
        ) -> ReleaseFuture<'a, ReleaseState> {
            let outcome = pop(&self.create);
            Box::pin(async move { outcome.unwrap_or(Err(ReleaseServiceError::MutationLost)) })
        }

        fn update_draft_release<'a>(
            &'a self,
            _repo: &RepoSlug,
            _id: u64,
            _input: &DraftReleaseInput,
        ) -> ReleaseFuture<'a, ReleaseState> {
            let outcome = pop(&self.update);
            Box::pin(async move { outcome.unwrap_or(Err(ReleaseServiceError::MutationLost)) })
        }

        fn release_body<'a>(&'a self, _repo: &RepoSlug, _id: u64) -> ReleaseFuture<'a, String> {
            let body = self.release_body.clone();
            Box::pin(async move { Ok(body) })
        }

        fn publish_release<'a>(
            &'a self,
            _repo: &RepoSlug,
            _id: u64,
        ) -> ReleaseFuture<'a, ReleaseState> {
            let outcome = pop(&self.publish);
            Box::pin(async move { outcome.unwrap_or(Err(ReleaseServiceError::MutationLost)) })
        }

        fn promote_release<'a>(
            &'a self,
            _repo: &RepoSlug,
            _id: u64,
        ) -> ReleaseFuture<'a, ReleaseState> {
            let outcome = pop(&self.promote);
            Box::pin(async move { outcome.unwrap_or(Err(ReleaseServiceError::MutationLost)) })
        }

        fn upload_asset<'a>(
            &'a self,
            _repo: &RepoSlug,
            _id: u64,
            _upload: &AssetUpload,
        ) -> ReleaseFuture<'a, RemoteAsset> {
            let outcome = pop(&self.upload);
            Box::pin(async move { outcome.unwrap_or(Err(ReleaseServiceError::MutationLost)) })
        }

        fn fetch_asset_hop<'a>(
            &'a self,
            _request: &FetchRequest,
        ) -> ReleaseFuture<'a, FetchOutcome> {
            let outcome = pop(&self.hops);
            Box::pin(async move { outcome.unwrap_or(Err(ReleaseServiceError::TooManyRedirects)) })
        }
    }

    fn repo() -> RepoSlug {
        RepoSlug::parse("o", "r").expect("valid slug")
    }

    fn run<T>(future: impl Future<Output = T>) -> T {
        LarchRuntime::new().expect("runtime").block_on(future)
    }

    fn hops(scripted: Vec<Result<FetchOutcome, ReleaseServiceError>>) -> FakeTransport {
        FakeTransport {
            hops: Mutex::new(scripted.into()),
            ..FakeTransport::default()
        }
    }

    // These build success elements for a `Result` hop queue whose failure
    // elements are written inline as `Err(...)`, so the wrap is intentional.
    #[allow(clippy::unnecessary_wraps, reason = "queue element type is Result")]
    fn redirect(location: &str) -> Result<FetchOutcome, ReleaseServiceError> {
        Ok(FetchOutcome::Redirect {
            location: location.to_owned(),
        })
    }

    #[allow(clippy::unnecessary_wraps, reason = "queue element type is Result")]
    fn body(
        content_type: &str,
        declared: Option<u64>,
        size: usize,
    ) -> Result<FetchOutcome, ReleaseServiceError> {
        Ok(FetchOutcome::Body {
            status: 200,
            content_type: Some(content_type.to_owned()),
            content_length: declared,
            body: vec![0_u8; size],
        })
    }

    fn download(transport: &FakeTransport, max_bytes: u64) -> Result<Vec<u8>, ReleaseServiceError> {
        run(ReleaseOperations::new(transport).download_asset(&repo(), 42, max_bytes))
    }

    #[test]
    fn release_selection_covers_drafts_immutability_absence_and_duplicates() {
        let transport = FakeTransport {
            releases: vec![
                release(1, "v1", true, false, Vec::new()),
                release(2, "v2", false, true, vec![asset("larch")]),
            ],
            ..FakeTransport::default()
        };
        let operations = ReleaseOperations::new(&transport);

        let published = run(operations.release_for_tag(&repo(), "v2"))
            .expect("selection")
            .expect("present");
        assert!(published.is_immutable());
        assert_eq!(published.assets().len(), 1);

        assert!(
            run(operations.release_for_tag(&repo(), "absent"))
                .expect("selection")
                .is_none()
        );

        let duplicates = FakeTransport {
            releases: vec![
                release(1, "dup", true, false, Vec::new()),
                release(2, "dup", true, false, Vec::new()),
            ],
            ..FakeTransport::default()
        };
        assert!(matches!(
            run(ReleaseOperations::new(&duplicates).release_for_tag(&repo(), "dup")),
            Err(ReleaseServiceError::Data(error)) if error.kind() == ReleaseDataErrorKind::DuplicateReleaseTag
        ));
    }

    #[test]
    fn ambiguous_create_reconciles_to_a_landed_release_without_repeating() {
        let transport = FakeTransport {
            releases: vec![release(7, "v1", true, false, Vec::new())],
            create: Mutex::new([Err(ReleaseServiceError::AmbiguousMutation)].into()),
            release_body: "notes".to_owned(),
            ..FakeTransport::default()
        };
        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "commit".to_owned(),
            body: "notes".to_owned(),
        };

        let staged = run(ReleaseOperations::new(&transport).stage_draft_release(&repo(), &input))
            .expect("reconciled release");

        assert_eq!(staged.database_id(), 7);
        assert_eq!(*transport.list_calls.lock().expect("counter"), 1);
    }

    #[test]
    fn ambiguous_create_retries_the_idempotent_create_when_not_applied() {
        let transport = FakeTransport {
            create: Mutex::new(
                [
                    Err(ReleaseServiceError::AmbiguousMutation),
                    Ok(release(7, "v1", true, false, Vec::new())),
                ]
                .into(),
            ),
            release_body: "notes".to_owned(),
            ..FakeTransport::default()
        };
        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "commit".to_owned(),
            body: "notes".to_owned(),
        };

        let staged = run(ReleaseOperations::new(&transport).stage_draft_release(&repo(), &input))
            .expect("retried release");
        assert_eq!(staged.database_id(), 7);
    }

    #[test]
    fn policy_enablement_and_draft_update_verify_owning_surfaces() {
        let staged = release(7, "v1", true, false, Vec::new());
        let transport = FakeTransport {
            releases: vec![staged.clone()],
            immutable: true,
            merge_commits: true,
            release_body: "notes".to_owned(),
            update: Mutex::new(
                [Err(ReleaseServiceError::Completion(
                    GitHubCompletionError::DeadlineExceeded,
                ))]
                .into(),
            ),
            ..FakeTransport::default()
        };
        let operations = ReleaseOperations::new(&transport);
        assert!(run(operations.ensure_repository_policy(&repo())).is_ok());
        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "commit".to_owned(),
            body: "notes".to_owned(),
        };
        assert_eq!(
            run(operations.update_draft_release(&repo(), &staged, &input))
                .expect("reconciled update")
                .database_id(),
            7
        );
    }

    #[test]
    fn policy_and_draft_read_back_fail_closed_on_wrong_state() {
        let staged = release(7, "v1", true, false, Vec::new());
        let transport = FakeTransport {
            releases: vec![staged.clone()],
            release_body: "old notes".to_owned(),
            update: Mutex::new([Ok(staged.clone())].into()),
            ..FakeTransport::default()
        };
        let operations = ReleaseOperations::new(&transport);
        assert_eq!(
            run(operations.ensure_repository_policy(&repo())),
            Err(ReleaseServiceError::MutationLost)
        );
        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "commit".to_owned(),
            body: "notes".to_owned(),
        };
        assert_eq!(
            run(operations.update_draft_release(&repo(), &staged, &input)),
            Err(ReleaseServiceError::MutationLost)
        );
    }

    #[test]
    fn ambiguous_publish_reconciles_to_a_published_release() {
        let transport = FakeTransport {
            releases: vec![release(7, "v1", false, true, Vec::new())],
            publish: Mutex::new([Err(ReleaseServiceError::AmbiguousMutation)].into()),
            ..FakeTransport::default()
        };
        let draft = release(7, "v1", true, false, Vec::new());

        let published = run(ReleaseOperations::new(&transport).publish_release(&repo(), &draft))
            .expect("reconciled publish");
        assert!(!published.is_draft());
    }

    #[test]
    fn publication_selection_and_ambiguous_promotion_use_owning_read_back() {
        let selected = published(8, "v2", true, "2026-07-19T02:00:00+00:00");
        let transport = FakeTransport {
            releases: vec![
                published(7, "v1", false, "2026-07-19T01:00:00+00:00"),
                selected.clone(),
                release(9, "v3", true, false, Vec::new()),
            ],
            latest: Mutex::new(
                [Ok(Some(selected.clone().with_publication(
                    false,
                    selected.published_at().map(str::to_owned),
                )))]
                .into(),
            ),
            promote: Mutex::new([Err(ReleaseServiceError::AmbiguousMutation)].into()),
            ..FakeTransport::default()
        };
        let operations = ReleaseOperations::new(&transport);
        assert_eq!(
            run(operations.newest_published_release(&repo()))
                .expect("newest")
                .expect("present")
                .database_id(),
            8
        );
        assert_eq!(
            run(operations.promote_release(&repo(), &selected))
                .expect("reconciled promotion")
                .database_id(),
            8
        );
        assert!(transport.promote.lock().expect("promote queue").is_empty());
    }

    #[test]
    fn failed_promotion_never_accepts_the_prior_latest() {
        let candidate = published(8, "v2", false, "2026-07-19T02:00:00+00:00");
        let transport = FakeTransport {
            latest: Mutex::new(
                [Ok(Some(published(
                    7,
                    "v1",
                    false,
                    "2026-07-19T01:00:00+00:00",
                )))]
                .into(),
            ),
            promote: Mutex::new([Ok(candidate.clone())].into()),
            ..FakeTransport::default()
        };
        assert_eq!(
            run(ReleaseOperations::new(&transport).promote_release(&repo(), &candidate)),
            Err(ReleaseServiceError::MutationLost)
        );
    }

    #[test]
    fn ambiguous_upload_reconciles_to_a_present_asset() {
        let transport = FakeTransport {
            releases: vec![release(7, "v1", true, false, vec![asset("larch")])],
            upload: Mutex::new([Err(ReleaseServiceError::AmbiguousMutation)].into()),
            ..FakeTransport::default()
        };
        let draft = release(7, "v1", true, false, Vec::new());
        let upload = AssetUpload {
            name: "larch".to_owned(),
            content: vec![1, 2, 3, 4],
        };

        let asset = run(ReleaseOperations::new(&transport).upload_asset(&repo(), &draft, &upload))
            .expect("reconciled upload");
        assert_eq!(asset.name(), "larch");
    }

    #[test]
    fn download_follows_a_validated_cross_origin_redirect_and_streams_the_body() {
        let transport = hops(vec![
            redirect(CDN),
            body("application/octet-stream", Some(4), 4),
        ]);
        assert_eq!(download(&transport, 1024).expect("download"), vec![0_u8; 4]);
    }

    #[test]
    fn download_rejects_downgrade_loop_and_hop_overrun() {
        let downgrade = hops(vec![redirect(
            "http://release-assets.githubusercontent.com/x",
        )]);
        assert!(matches!(
            download(&downgrade, 1024),
            Err(ReleaseServiceError::Host(GitHubHostError::UnapprovedOrigin))
        ));

        let looped = hops(vec![redirect(CDN), redirect(START)]);
        assert_eq!(
            download(&looped, 1024),
            Err(ReleaseServiceError::RedirectLoop)
        );

        let overrun = hops(vec![
            redirect("https://cdn.example/1"),
            redirect("https://cdn.example/2"),
            redirect("https://cdn.example/3"),
            redirect("https://cdn.example/4"),
            redirect("https://cdn.example/5"),
            redirect("https://cdn.example/6"),
            redirect("https://cdn.example/7"),
        ]);
        assert_eq!(
            download(&overrun, 1024),
            Err(ReleaseServiceError::TooManyRedirects)
        );
    }

    #[test]
    fn download_rejects_bad_content_type_oversize_and_truncation() {
        let wrong_type = hops(vec![body("text/html", Some(4), 4)]);
        assert!(matches!(
            download(&wrong_type, 1024),
            Err(ReleaseServiceError::Data(error)) if error.kind() == ReleaseDataErrorKind::UnexpectedContentType
        ));

        let oversize = hops(vec![body("application/octet-stream", Some(10), 10)]);
        assert!(matches!(
            download(&oversize, 4),
            Err(ReleaseServiceError::Data(error)) if error.kind() == ReleaseDataErrorKind::AssetTooLarge
        ));

        let truncated = hops(vec![body("application/octet-stream", Some(10), 4)]);
        assert!(matches!(
            download(&truncated, 1024),
            Err(ReleaseServiceError::Data(error)) if error.kind() == ReleaseDataErrorKind::TruncatedAsset
        ));
    }

    #[test]
    fn download_surfaces_cancellation_timeout_and_transport_failures() {
        let cancelled = hops(vec![Err(ReleaseServiceError::Completion(
            GitHubCompletionError::Cancelled,
        ))]);
        assert_eq!(
            download(&cancelled, 1024),
            Err(ReleaseServiceError::Completion(
                GitHubCompletionError::Cancelled
            ))
        );

        let timed_out = hops(vec![Err(ReleaseServiceError::Completion(
            GitHubCompletionError::DeadlineExceeded,
        ))]);
        assert_eq!(
            download(&timed_out, 1024),
            Err(ReleaseServiceError::Completion(
                GitHubCompletionError::DeadlineExceeded
            ))
        );

        let throttled = FakeTransport {
            list: Mutex::new([Err(ReleaseServiceError::UnexpectedStatus(429))].into()),
            ..FakeTransport::default()
        };
        assert_eq!(
            run(ReleaseOperations::new(&throttled).release_for_tag(&repo(), "v1")),
            Err(ReleaseServiceError::UnexpectedStatus(429))
        );
    }

    #[test]
    fn repo_slug_rejects_hostile_segments() {
        assert!(RepoSlug::parse("o", "r").is_ok());
        assert!(RepoSlug::parse("o", "../secret").is_err());
        assert!(RepoSlug::parse("o", "a b").is_err());
        assert!(RepoSlug::parse("", "r").is_err());
    }

    #[test]
    fn download_redirect_strips_credentials_only_when_the_origin_changes() {
        let api = Url::parse(START).expect("api url");
        let same_origin = validate_download_redirect(&api, "https://api.github.com/other", 1024)
            .expect("same-origin hop");
        assert!(!same_origin.strip_authorization);

        let cross_origin = validate_download_redirect(&api, CDN, 1024).expect("cross-origin hop");
        assert!(cross_origin.strip_authorization);

        assert!(validate_download_redirect(&api, "https://user:pass@cdn.example/x", 1024).is_err());
    }

    #[test]
    fn operations_pass_through_immediate_success_tag_and_immutability() {
        let transport = FakeTransport {
            create: Mutex::new([Ok(release(7, "v1", true, false, Vec::new()))].into()),
            publish: Mutex::new([Ok(release(7, "v1", false, false, Vec::new()))].into()),
            upload: Mutex::new([Ok(asset("larch"))].into()),
            tag: Some(TagObjectId::parse("0123456789abcdef0123456789abcdef01234567").expect("oid")),
            immutable: true,
            release_body: "notes".to_owned(),
            ..FakeTransport::default()
        };
        let operations = ReleaseOperations::new(&transport);
        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "commit".to_owned(),
            body: "notes".to_owned(),
        };
        let draft = release(7, "v1", true, false, Vec::new());
        let upload = AssetUpload {
            name: "larch".to_owned(),
            content: vec![1, 2, 3, 4],
        };

        let staged =
            run(operations.stage_draft_release(&repo(), &input)).expect("immediate create");
        assert_eq!(staged.database_id(), 7);
        assert!(
            !run(operations.publish_release(&repo(), &draft))
                .expect("publish")
                .is_draft()
        );
        assert_eq!(
            run(operations.upload_asset(&repo(), &draft, &upload))
                .expect("upload")
                .name(),
            "larch"
        );
        assert!(
            run(operations.tag_object_id(&repo(), "v1"))
                .expect("tag")
                .is_some()
        );
        assert!(run(operations.immutable_releases_enabled(&repo())).expect("immutable"));
        assert_eq!(*transport.list_calls.lock().expect("counter"), 0);
    }

    #[test]
    fn service_errors_render_fixed_secret_free_messages() {
        for error in [
            ReleaseServiceError::Host(GitHubHostError::CrossOriginContinuation),
            ReleaseServiceError::Completion(GitHubCompletionError::DeadlineExceeded),
            ReleaseServiceError::RedirectLoop,
            ReleaseServiceError::TooManyRedirects,
            ReleaseServiceError::UnexpectedStatus(503),
            ReleaseServiceError::AssetTooLarge,
            ReleaseServiceError::AmbiguousMutation,
            ReleaseServiceError::MutationLost,
        ] {
            assert!(!error.to_string().is_empty());
        }
        assert_eq!(
            GitHubHostError::CrossOriginContinuation.to_string(),
            "GitHub continuation changed origin"
        );
        assert_eq!(
            GitHubCompletionError::Cancelled.to_string(),
            "GitHub operation cancelled"
        );
    }
}

#[cfg(test)]
mod transport_tests {
    use super::*;
    use crate::runtime::Cancellation;
    use octocrab::Octocrab;
    use serde_json::json;
    use std::fmt::Write as _;
    use std::io::{Read as _, Write as _};
    use std::net::TcpListener;
    use std::thread;

    const DIGEST: &str = "sha256:1111111111111111111111111111111111111111111111111111111111111111";

    /// One scripted loopback reply: status line, extra headers, and body bytes.
    struct Reply {
        status: u16,
        headers: Vec<(&'static str, String)>,
        body: Vec<u8>,
        expected_request: Option<&'static str>,
    }

    fn json_reply(status: u16, value: &serde_json::Value) -> Reply {
        Reply {
            status,
            headers: vec![("Content-Type", "application/json".to_owned())],
            body: value.to_string().into_bytes(),
            expected_request: None,
        }
    }

    fn json_reply_expecting(
        status: u16,
        value: &serde_json::Value,
        expected_request: &'static str,
    ) -> Reply {
        Reply {
            expected_request: Some(expected_request),
            ..json_reply(status, value)
        }
    }

    fn redirect_reply(location: &str) -> Reply {
        Reply {
            status: 302,
            headers: vec![("Location", location.to_owned())],
            body: Vec::new(),
            expected_request: None,
        }
    }

    fn octet_reply(bytes: Vec<u8>) -> Reply {
        Reply {
            status: 200,
            headers: vec![("Content-Type", ASSET_MEDIA_TYPE.to_owned())],
            body: bytes,
            expected_request: None,
        }
    }

    // A loopback HTTP stub that serves scripted replies in order, mirroring the
    // hardened client against a local socket the same way `github_rest` does.
    fn stub(replies: Vec<Reply>) -> (OctocrabGitHubService, String, thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind stub");
        let base = format!("http://{}/", listener.local_addr().expect("stub address"));
        let server = thread::spawn(move || {
            for reply in replies {
                let (mut socket, _) = listener.accept().expect("accept request");
                let mut request = [0_u8; 16_384];
                let read = socket.read(&mut request).expect("read request");
                assert!(read > 0, "request must not be empty");
                if let Some(expected) = reply.expected_request {
                    let request = String::from_utf8_lossy(&request[..read]);
                    assert!(
                        request.contains(expected),
                        "request did not contain {expected:?}: {request}"
                    );
                }
                let mut head = format!("HTTP/1.1 {} Stub\r\n", reply.status);
                for (name, value) in &reply.headers {
                    head.push_str(name);
                    head.push_str(": ");
                    head.push_str(value);
                    head.push_str("\r\n");
                }
                write!(
                    head,
                    "Content-Length: {}\r\nConnection: close\r\n\r\n",
                    reply.body.len()
                )
                .expect("format head");
                socket.write_all(head.as_bytes()).expect("write head");
                socket.write_all(&reply.body).expect("write body");
            }
        });
        let client = Octocrab::builder()
            .personal_token(String::from("test-token"))
            .base_uri(&base)
            .expect("base URI")
            .upload_uri(&base)
            .expect("upload URI")
            .build()
            .expect("stub client");
        (
            OctocrabGitHubService::with_test_client(client),
            base,
            server,
        )
    }

    fn asset_json(name: &str) -> serde_json::Value {
        json!({
            "url": "https://api.github.com/repos/o/r/releases/assets/42",
            "browser_download_url": "https://github.com/o/r/releases/download/v1/larch",
            "id": 42,
            "node_id": "A_42",
            "name": name,
            "state": "uploaded",
            "content_type": ASSET_MEDIA_TYPE,
            "size": 4,
            "digest": DIGEST,
            "download_count": 0,
            "created_at": "2026-07-18T00:00:00Z",
            "updated_at": "2026-07-18T00:00:00Z"
        })
    }

    fn release_json(id: u64, tag: &str, draft: bool) -> serde_json::Value {
        json!({
            "url": "https://api.github.com/repos/o/r/releases/1",
            "html_url": "https://github.com/o/r/releases/tag/v1",
            "assets_url": "https://api.github.com/repos/o/r/releases/1/assets",
            // Relative so the hardened client resolves the upload POST back to the
            // loopback stub instead of the public uploads host.
            "upload_url": "/repos/o/r/releases/1/assets{?name,label}",
            "id": id,
            "node_id": "R_1",
            "tag_name": tag,
            "target_commitish": "main",
            "draft": draft,
            "prerelease": false,
            "immutable": true,
            "created_at": "2026-07-18T00:00:00Z",
            "published_at": (!draft).then_some("2026-07-18T01:00:00Z"),
            "assets": [asset_json("larch")]
        })
    }

    fn repo() -> RepoSlug {
        RepoSlug::parse("o", "r").expect("valid slug")
    }

    #[tokio::test]
    async fn transport_maps_release_list_create_publish_and_upload() {
        serde_json::from_value::<Release>(release_json(2, "v1", false))
            .expect("release fixture should deserialize");
        // `upload_asset` first GETs the release to read its `upload_url`, then
        // POSTs the asset there, so it consumes two scripted replies.
        let (service, _base, server) = stub(vec![
            json_reply(200, &json!([release_json(1, "v1", true)])),
            json_reply(201, &release_json(2, "v1", true)),
            json_reply_expecting(
                200,
                &release_json(2, "v1", false),
                "\"make_latest\":\"false\"",
            ),
            json_reply_expecting(
                200,
                &release_json(2, "v1", false),
                "/repos/o/r/releases/latest",
            ),
            json_reply_expecting(
                200,
                &release_json(2, "v1", false),
                "\"make_latest\":\"true\"",
            ),
            json_reply(200, &release_json(2, "v1", false)),
            json_reply(201, &asset_json("larch")),
        ]);
        let cancellation = Cancellation::new();
        let transport = OctocrabReleaseTransport::new(&service, &cancellation);
        let repo = repo();

        let releases = transport.list_releases(&repo).await.expect("list releases");
        assert_eq!(releases.len(), 1);
        assert_eq!(releases[0].tag(), "v1");
        assert_eq!(releases[0].assets().len(), 1);

        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "main".to_owned(),
            body: "notes".to_owned(),
        };
        let created = transport
            .create_draft_release(&repo, &input)
            .await
            .expect("create draft");
        assert!(created.is_draft());
        assert_eq!(created.database_id(), 2);

        let published = transport
            .publish_release(&repo, created.database_id())
            .await
            .expect("publish");
        assert!(!published.is_draft());

        let latest = transport
            .latest_release(&repo)
            .await
            .expect("read Latest")
            .expect("Latest release");
        assert_eq!(latest.database_id(), published.database_id());

        let promoted = transport
            .promote_release(&repo, published.database_id())
            .await
            .expect("promote");
        assert_eq!(promoted.database_id(), published.database_id());

        let upload = AssetUpload {
            name: "larch".to_owned(),
            content: vec![1, 2, 3, 4],
        };
        let asset = transport
            .upload_asset(&repo, published.database_id(), &upload)
            .await
            .expect("upload asset");
        assert_eq!(asset.name(), "larch");

        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn transport_reads_redirect_and_terminal_body_hops() {
        let (service, base, server) = stub(vec![
            redirect_reply("https://release-assets.githubusercontent.com/x"),
            octet_reply(vec![7, 8, 9, 10]),
        ]);
        let cancellation = Cancellation::new();
        let transport = OctocrabReleaseTransport::new(&service, &cancellation);
        let request = FetchRequest {
            url: Url::parse(&format!("{base}asset")).expect("loopback url"),
            strip_authorization: false,
            max_bytes: 1024,
        };

        match transport
            .fetch_asset_hop(&request)
            .await
            .expect("redirect hop")
        {
            FetchOutcome::Redirect { location } => {
                assert_eq!(location, "https://release-assets.githubusercontent.com/x");
            }
            other @ FetchOutcome::Body { .. } => panic!("expected redirect, got {other:?}"),
        }
        match transport.fetch_asset_hop(&request).await.expect("body hop") {
            FetchOutcome::Body {
                status,
                content_type,
                body,
                ..
            } => {
                assert_eq!(status, 200);
                assert_eq!(content_type.as_deref(), Some(ASSET_MEDIA_TYPE));
                assert_eq!(body, vec![7, 8, 9, 10]);
            }
            other @ FetchOutcome::Redirect { .. } => panic!("expected body, got {other:?}"),
        }

        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn transport_reports_transport_mutation_and_cancellation_failures() {
        let (service, _base, server) = stub(vec![
            json_reply(500, &json!({"message": "boom"})),
            json_reply(500, &json!({"message": "boom"})),
        ]);
        let repo = repo();
        let cancellation = Cancellation::new();
        let transport = OctocrabReleaseTransport::new(&service, &cancellation);

        assert!(matches!(
            transport.list_releases(&repo).await,
            Err(ReleaseServiceError::Transport(_))
        ));

        let input = DraftReleaseInput {
            tag: "v1".to_owned(),
            target_commitish: "main".to_owned(),
            body: "notes".to_owned(),
        };
        assert_eq!(
            transport.create_draft_release(&repo, &input).await,
            Err(ReleaseServiceError::AmbiguousMutation)
        );

        let cancelled = Cancellation::new();
        cancelled.cancel();
        let cancelled_transport = OctocrabReleaseTransport::new(&service, &cancelled);
        assert_eq!(
            cancelled_transport.list_releases(&repo).await,
            Err(ReleaseServiceError::Completion(
                GitHubCompletionError::Cancelled
            ))
        );

        server.join().expect("stub completed");
    }

    #[test]
    fn ref_object_reads_sha_and_type_or_reports_missing() {
        let value = json!({"object": {"sha": "abcd", "type": "commit"}});
        assert_eq!(
            ref_object(&value).expect("object present"),
            ("abcd".to_owned(), "commit".to_owned())
        );
        assert!(matches!(
            ref_object(&json!({})),
            Err(ReleaseServiceError::Data(_))
        ));
    }
}
