//! Authenticated, policy-bound GitHub transport foundation and the typed
//! pull-request, review, issue-graph, and release operations built on it.

mod attestation;
mod issue_mutation;
mod mutation_auth;
mod operations;
mod release;

pub use attestation::{
    AttestationFuture, AttestationOperations, AttestationQuery, AttestationServiceError,
    AttestationServiceErrorKind, AttestationTransport, OctocrabAttestationTransport,
};

pub use issue_mutation::{IssueCreateFailure, IssueMutationOwner};
pub use mutation_auth::{LiveMutationDecision, LiveMutationRequest, check_live_mutation_auth};
pub use operations::{
    AuditPullRequest, AuditRunsService, CompanionIssue, CreatedPullRequest, DependencyEdge,
    DependencyMutation, DependencyMutationReceipt, DependencyRef, GitHubOperationError,
    MergeStateStatus, Mergeable, PullRequest, PullRequestEdit, PullRequestMerge,
    PullRequestMergeMethod, PullRequestMergeResult, PullRequestQueueLifecycle,
    PullRequestQueueResult, PullRequestQueueState, PullRequestReviewState, PullRequestSpec,
    PullRequestState, ReleaseCandidatePullRequest, ReleaseCandidatePullRequestState,
    ReleasePlanningService, ReleasePullRequest, ReviewDecision, SubIssueEdge, SubIssueMutation,
    SubIssueMutationReceipt, SubIssueRef,
};
pub use release::{
    AssetUpload, DraftReleaseInput, FetchOutcome, FetchRequest, OctocrabReleaseTransport,
    PublicReleaseAsset, PublicReleaseDownloader, ReleaseFuture, ReleaseOperations,
    ReleaseServiceError, ReleaseTransport, RepoSlug, find_asset, validate_download_redirect,
};

use bytes::Bytes;
use chrono::{DateTime, SecondsFormat, Utc};
use http::header::{CONTENT_LENGTH, HeaderName};
use http_body_util::{BodyExt, Limited};
use larch_core::{
    ExternalProcessRunner, GitHubToken, GitHubTransportPolicy, ProcessCancellation,
    RuntimeRedactor, SafeText, acquire_github_token,
};
pub use larch_core::{
    GitHubTokenError as GitHubCredentialError, GitHubTokenErrorKind as GitHubCredentialErrorKind,
};
use octocrab::Octocrab;
use std::{error::Error, fmt, future::Future, path::Path, time::Duration};
use tokio::sync::Mutex;
use url::Url;

const API_BASE: &str = "https://api.github.com/";
const API_VERSION_HEADER: &str = "x-github-api-version";
const API_VERSION: &str = "2022-11-28";
const ACCEPT_VALUE: &str = "application/vnd.github+json";
const USER_AGENT_VALUE: &str = "larch";

/// Render a GitHub timestamp in the canonical UTC spelling used for freshness identities.
pub(crate) fn github_utc_timestamp(value: &DateTime<Utc>) -> String {
    value.to_rfc3339_opts(SecondsFormat::Secs, true)
}

/// Failure to construct the hardened GitHub service.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GitHubClientError {
    Credential(GitHubCredentialError),
    Configuration(SafeText),
}

impl fmt::Display for GitHubClientError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Credential(error) => error.fmt(formatter),
            Self::Configuration(detail) => {
                write!(formatter, "cannot configure GitHub transport: {detail}")
            }
        }
    }
}

impl Error for GitHubClientError {}

impl From<GitHubCredentialError> for GitHubClientError {
    fn from(error: GitHubCredentialError) -> Self {
        Self::Credential(error)
    }
}

/// Host or continuation policy rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubHostError {
    InvalidUrl,
    UnapprovedOrigin,
    CrossOriginContinuation,
}

impl fmt::Display for GitHubHostError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::InvalidUrl => "GitHub URL is invalid",
            Self::UnapprovedOrigin => "GitHub URL origin is not approved",
            Self::CrossOriginContinuation => "GitHub continuation changed origin",
        })
    }
}

impl Error for GitHubHostError {}

/// Why an operation wrapper completed without an API result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubCompletionError {
    Cancelled,
    DeadlineExceeded,
}

impl fmt::Display for GitHubCompletionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Cancelled => "GitHub operation cancelled",
            Self::DeadlineExceeded => "GitHub operation deadline exceeded",
        })
    }
}

impl Error for GitHubCompletionError {}

// Deliberately non-Debug: a credential must not enter derived diagnostics.
struct GitHubCredential(String);

impl From<GitHubToken> for GitHubCredential {
    fn from(token: GitHubToken) -> Self {
        Self(token.expose().to_owned())
    }
}

impl GitHubCredential {
    fn expose(&self) -> &str {
        &self.0
    }
}

/// One Octocrab client and exact-secret registry for a runtime context.
///
/// The client is intentionally private. Operation adapters in this crate add
/// typed paths and DTOs instead of exposing Octocrab, raw REST URLs, or
/// arbitrary GraphQL documents to domain callers.
pub struct OctocrabGitHubService {
    pub(crate) client: Octocrab,
    /// Client for release-asset binary downloads. It omits the
    /// `application/vnd.github+json` Accept so the per-request
    /// `application/octet-stream` Accept is honored; otherwise the GitHub
    /// asset endpoint returns asset metadata JSON instead of the binary.
    pub(crate) download_client: Octocrab,
    pub(crate) policy: GitHubTransportPolicy,
    pub(crate) api_base: Url,
    #[cfg(test)]
    pub(crate) test_log_redirect_origin: Option<url::Origin>,
    redactor: RuntimeRedactor,
    pub(crate) mutation_lock: Mutex<()>,
    #[cfg(any(test, feature = "test-support"))]
    test_continuation_base: Option<Url>,
}

impl OctocrabGitHubService {
    #[cfg(any(test, feature = "test-support"))]
    #[doc(hidden)]
    pub fn with_test_client(client: Octocrab) -> Self {
        Self {
            download_client: client.clone(),
            client,
            policy: GitHubTransportPolicy::github_com(),
            api_base: Url::parse(API_BASE).expect("fixed API base must be valid"),
            #[cfg(test)]
            test_log_redirect_origin: None,
            redactor: RuntimeRedactor::default(),
            mutation_lock: Mutex::new(()),
            #[cfg(any(test, feature = "test-support"))]
            test_continuation_base: None,
        }
    }

    /// Construct a loopback-only test client from one supplied base URL.
    #[cfg(any(test, feature = "test-support"))]
    #[doc(hidden)]
    #[must_use]
    pub fn with_test_base(base_url: &str) -> Self {
        let client = Octocrab::builder()
            .personal_token(String::from("test-token"))
            .base_uri(base_url)
            .expect("test API base URI")
            .upload_uri(base_url)
            .expect("test upload base URI")
            .build()
            .expect("test client");
        Self::with_test_client(client).with_test_continuation_base(base_url)
    }

    /// Acquire the sole supported credential from `gh` and construct one hardened client.
    ///
    /// # Errors
    /// Fails before network access when `gh` is absent or unauthenticated, its
    /// output is invalid, or fixed client configuration cannot be constructed.
    pub async fn from_gh<R: ExternalProcessRunner + ?Sized>(
        runner: &R,
        working_directory: &Path,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<Self, GitHubClientError> {
        Self::from_gh_with_policy(
            runner,
            working_directory,
            cancellation,
            GitHubTransportPolicy::github_com(),
        )
        .await
    }

    /// Acquire the sole supported credential and construct a client with one
    /// reviewed, caller-selected transport policy.
    ///
    /// Callers use this only for an explicitly documented exhaustive-history
    /// read. The client, credential acquisition, redaction, fixed origins, and
    /// request validation remain owned by this adapter.
    ///
    /// # Errors
    ///
    /// Fails before network access when `gh` is absent or unauthenticated, its
    /// output is invalid, or fixed client configuration cannot be constructed.
    pub async fn from_gh_with_policy<R: ExternalProcessRunner + ?Sized>(
        runner: &R,
        working_directory: &Path,
        cancellation: &dyn ProcessCancellation,
        policy: GitHubTransportPolicy,
    ) -> Result<Self, GitHubClientError> {
        let credential = acquire_github_token(runner, working_directory, cancellation).await?;
        let credential = GitHubCredential::from(credential);
        Self::from_credential_with_policy(&credential, policy)
    }

    fn from_credential_with_policy(
        credential: &GitHubCredential,
        policy: GitHubTransportPolicy,
    ) -> Result<Self, GitHubClientError> {
        let mut redactor = RuntimeRedactor::default();
        let registered = redactor.register_exact_secret(credential.expose().to_owned());
        debug_assert!(registered, "validated GitHub credential must register");
        if tokio::runtime::Handle::try_current().is_err() {
            return Err(GitHubClientError::Configuration(redactor.safe_text(
                "GitHub transport must be constructed inside the larch Tokio runtime",
            )));
        }
        if !octocrab_api_version_is_exact() {
            return Err(GitHubClientError::Configuration(redactor.safe_text(
                "Octocrab GitHub API version does not match larch policy",
            )));
        }
        let client = build_client(credential, policy, API_BASE, &Self::required_headers())
            .map_err(|error| {
                GitHubClientError::Configuration(redactor.safe_text(error.to_string()))
            })?;
        let download_client = build_client(credential, policy, API_BASE, &Self::download_headers())
            .map_err(|error| {
                GitHubClientError::Configuration(redactor.safe_text(error.to_string()))
            })?;
        Ok(Self {
            client,
            download_client,
            policy,
            api_base: Url::parse(API_BASE).expect("fixed API base must be valid"),
            #[cfg(test)]
            test_log_redirect_origin: None,
            redactor,
            mutation_lock: Mutex::new(()),
            #[cfg(any(test, feature = "test-support"))]
            test_continuation_base: None,
        })
    }

    #[cfg(test)]
    pub(crate) fn from_test_token(token: &str) -> Self {
        Self::from_credential_with_policy(
            &GitHubCredential(token.to_owned()),
            GitHubTransportPolicy::github_com(),
        )
        .expect("test token and active runtime must construct the client")
    }

    #[cfg(test)]
    pub(crate) fn from_test_token_with_base(
        token: &str,
        api_base: &Url,
        log_redirect_origin: url::Origin,
    ) -> Self {
        let credential = GitHubCredential(token.to_owned());
        let policy = GitHubTransportPolicy::github_com();
        let mut redactor = RuntimeRedactor::default();
        assert!(
            redactor.register_exact_secret(credential.expose().to_owned()),
            "test credential must register"
        );
        let client = build_client(
            &credential,
            policy,
            api_base.as_str(),
            &Self::required_headers(),
        )
        .expect("test API base and token must construct the client");
        let download_client = build_client(
            &credential,
            policy,
            api_base.as_str(),
            &Self::download_headers(),
        )
        .expect("test API base and token must construct the download client");
        Self {
            client,
            download_client,
            policy,
            api_base: api_base.clone(),
            test_log_redirect_origin: Some(log_redirect_origin),
            redactor,
            mutation_lock: Mutex::new(()),
            test_continuation_base: None,
        }
    }

    /// Larch-owned headers added beside Octocrab's verified API-version header.
    #[must_use]
    pub const fn required_headers() -> [(&'static str, &'static str); 2] {
        [("user-agent", USER_AGENT_VALUE), ("accept", ACCEPT_VALUE)]
    }

    /// Headers for the release-asset download client. It adds none of larch's
    /// API headers. Omitting the `application/vnd.github+json` Accept lets a
    /// per-request `application/octet-stream` Accept survive; otherwise the
    /// asset endpoint returns metadata JSON. Omitting the `user-agent` avoids a
    /// second `User-Agent` header (Octocrab already sets one): the
    /// release-assets CDN rejects a duplicate `User-Agent` with HTTP 400
    /// "invalid header name", though `api.github.com` tolerates it.
    #[must_use]
    pub const fn download_headers() -> [(&'static str, &'static str); 0] {
        []
    }

    /// Remove the exact runtime credential and standard secret families.
    #[must_use]
    pub fn redact_diagnostic(&self, text: impl AsRef<str>) -> SafeText {
        self.redactor.safe_text(text)
    }

    pub(crate) const fn client(&self) -> &Octocrab {
        &self.client
    }

    #[cfg(any(test, feature = "test-support"))]
    pub(crate) fn with_test_continuation_base(mut self, base: &str) -> Self {
        self.test_continuation_base = Some(Url::parse(base).expect("test continuation base"));
        self
    }

    /// Resolve a response-supplied pagination or redirect continuation and
    /// require it to stay on the approved starting origin.
    ///
    /// # Errors
    /// Rejects malformed, non-HTTPS, credential-bearing, unapproved, or
    /// cross-origin URLs.
    pub fn continuation_url(base: &str, continuation: &str) -> Result<Url, GitHubHostError> {
        let base = parse_approved_url(base)?;
        let next = base
            .join(continuation)
            .map_err(|_| GitHubHostError::InvalidUrl)?;
        validate_approved_url(&next)?;
        if base.origin() != next.origin() {
            return Err(GitHubHostError::CrossOriginContinuation);
        }
        Ok(next)
    }

    /// Enforce the overall deadline and cooperative cancellation around one
    /// typed operation future. Cancellation wins when both signals are ready.
    ///
    /// # Errors
    /// Returns a closed cancellation or deadline outcome.
    pub async fn guard_operation<T, F>(
        &self,
        cancellation: &dyn ProcessCancellation,
        operation: F,
    ) -> Result<T, GitHubCompletionError>
    where
        F: Future<Output = T> + Send,
        T: Send,
    {
        tokio::select! {
            biased;
            () = cancellation.cancelled() => Err(GitHubCompletionError::Cancelled),
            result = tokio::time::timeout(self.policy.overall_timeout(), operation) => {
                result.map_err(|_| GitHubCompletionError::DeadlineExceeded)
            }
        }
    }
}

fn build_client(
    credential: &GitHubCredential,
    policy: GitHubTransportPolicy,
    api_base: &str,
    headers: &[(&'static str, &'static str)],
) -> octocrab::Result<Octocrab> {
    let mut builder = Octocrab::builder()
        .personal_token(credential.expose().to_owned())
        .set_connect_timeout(Some(policy.connect_timeout()))
        .set_read_timeout(Some(policy.read_timeout()))
        .set_write_timeout(Some(policy.write_timeout()))
        .base_uri(api_base)?
        .upload_uri(api_base)?;
    for &(name, value) in headers {
        builder = builder.add_header(HeaderName::from_static(name), value.to_owned());
    }
    builder.build()
}

pub(super) fn build_public_client(api_base: &str, timeout: Duration) -> octocrab::Result<Octocrab> {
    Octocrab::builder()
        .set_connect_timeout(Some(timeout))
        .set_read_timeout(Some(timeout))
        .set_write_timeout(Some(timeout))
        .base_uri(api_base)?
        .upload_uri(api_base)?
        .build()
}

fn octocrab_api_version_is_exact() -> bool {
    let mut versions = octocrab::_SET_HEADERS_MAP
        .iter()
        .filter(|(name, _)| name.eq_ignore_ascii_case(API_VERSION_HEADER))
        .map(|(_, value)| *value);
    versions.next() == Some(API_VERSION) && versions.next().is_none()
}

fn parse_approved_url(value: &str) -> Result<Url, GitHubHostError> {
    let url = Url::parse(value).map_err(|_| GitHubHostError::InvalidUrl)?;
    validate_approved_url(&url)?;
    Ok(url)
}

fn validate_approved_url(url: &Url) -> Result<(), GitHubHostError> {
    let host = url.host_str();
    let approved_host = matches!(host, Some("api.github.com" | "github.com"));
    let approved = url.scheme() == "https"
        && approved_host
        && url.port_or_known_default() == Some(443)
        && url.username().is_empty()
        && url.password().is_none();
    if approved {
        Ok(())
    } else {
        Err(GitHubHostError::UnapprovedOrigin)
    }
}

pub(crate) fn octocrab_status(error: &octocrab::Error) -> Option<u16> {
    match error {
        octocrab::Error::GitHub { source, .. } => Some(source.status_code.as_u16()),
        _ => None,
    }
}

/// Classify an octocrab error as network-unreachable: a failure that never
/// produced an HTTP response, so the request never reached GitHub. With the
/// hyper default client, a DNS failure, connect timeout, or refused or reset
/// connection surfaces through the tower connector as `Service` or directly as
/// `Hyper`. Every `GitHub` variant carries an HTTP status, so an HTTP 4xx or
/// 5xx never qualifies, and serialization or URI faults stay classified as
/// ordinary transport failures.
pub(crate) const fn octocrab_is_unreachable(error: &octocrab::Error) -> bool {
    matches!(
        error,
        octocrab::Error::Service { .. } | octocrab::Error::Hyper { .. }
    )
}

pub(crate) type GitHubRawResponse =
    http::Response<http_body_util::combinators::BoxBody<Bytes, octocrab::Error>>;

/// Collect a GitHub response without exceeding the caller's byte bound.
pub(crate) async fn collect_bounded_response(
    response: GitHubRawResponse,
    cap: usize,
) -> Result<Vec<u8>, ()> {
    if response
        .headers()
        .get(CONTENT_LENGTH)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.parse::<usize>().ok())
        .is_some_and(|length| length > cap)
    {
        return Err(());
    }
    Limited::new(response.into_body(), cap)
        .collect()
        .await
        .map(|body| body.to_bytes().to_vec())
        .map_err(|_| ())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::{Cancellation, LarchRuntime};
    use larch_core::{GitHubResponseLimits, GitHubService};

    fn configured_service(runtime: &LarchRuntime) -> OctocrabGitHubService {
        runtime.block_on(async {
            OctocrabGitHubService::from_credential_with_policy(
                &GitHubCredential("opaque test credential".to_owned()),
                GitHubTransportPolicy::github_com(),
            )
            .expect("fixed client should build")
        })
    }

    #[test]
    fn client_construction_outside_runtime_fails_without_secret_diagnostics() {
        let error = OctocrabGitHubService::from_credential_with_policy(
            &GitHubCredential("unusual exact secret".to_owned()),
            GitHubTransportPolicy::github_com(),
        )
        .err()
        .expect("runtime-less construction must fail");

        assert!(error.to_string().contains("inside the larch Tokio runtime"));
        assert!(!error.to_string().contains("unusual exact secret"));
    }

    #[test]
    fn client_uses_fixed_headers_policy_and_exact_secret_redaction() {
        let runtime = LarchRuntime::new().expect("runtime");
        let service = configured_service(&runtime);
        assert_eq!(
            OctocrabGitHubService::required_headers(),
            [
                ("user-agent", "larch"),
                ("accept", "application/vnd.github+json"),
            ]
        );
        assert!(
            octocrab_api_version_is_exact(),
            "the pinned Octocrab request header must supply the API version exactly once"
        );
        let safe = service.redact_diagnostic(
            "Authorization: Bearer opaque test credential; body=opaque test credential",
        );
        assert_eq!(
            safe.as_str(),
            "Authorization: Bearer <REDACTED-TOKEN>; body=<REDACTED-TOKEN>"
        );
        let limits: GitHubResponseLimits = service.transport_policy().limits();
        assert_eq!(limits.body_bytes(), 2 * 1024 * 1024);
        assert_eq!(limits.pages(), 20);
    }

    #[test]
    fn explicit_history_policy_stays_inside_the_typed_client_boundary() {
        let runtime = LarchRuntime::new().expect("runtime");
        let service = runtime.block_on(async {
            OctocrabGitHubService::from_credential_with_policy(
                &GitHubCredential("opaque audit credential".to_owned()),
                GitHubTransportPolicy::migration_audit(),
            )
            .expect("fixed audit policy should build")
        });
        assert_eq!(service.transport_policy().limits().pages(), 100);
        assert_eq!(service.transport_policy().limits().items(), 10_000);
    }

    #[test]
    fn download_client_adds_no_extra_headers() {
        // The asset-download client adds none of larch's API headers. It must
        // not advertise the vnd.github+json Accept (Octocrab appends it to the
        // per-request octet-stream Accept, so the asset endpoint returns
        // metadata JSON), and it must not add a second user-agent (Octocrab
        // already sets one; a duplicate User-Agent makes the release-assets CDN
        // reject the download with HTTP 400 "invalid header name").
        assert!(OctocrabGitHubService::download_headers().is_empty());
        // The API client keeps the JSON Accept it needs.
        assert!(
            OctocrabGitHubService::required_headers()
                .iter()
                .any(|(name, value)| *name == "accept" && *value == "application/vnd.github+json")
        );
    }

    #[test]
    fn continuation_policy_rejects_unapproved_and_cross_origin_urls() {
        let relative = OctocrabGitHubService::continuation_url(
            "https://api.github.com/repos/example/repo/issues",
            "?page=2",
        )
        .expect("same-origin relative continuation");
        assert_eq!(
            relative.as_str(),
            "https://api.github.com/repos/example/repo/issues?page=2"
        );

        for continuation in [
            "https://github.com/page/2",
            "https://evil.example/page/2",
            "http://api.github.com/page/2",
            "https://user@api.github.com/page/2",
            "https://api.github.com:444/page/2",
        ] {
            assert!(
                OctocrabGitHubService::continuation_url(API_BASE, continuation).is_err(),
                "continuation {continuation}"
            );
        }
    }

    #[test]
    fn operation_guard_prioritizes_cancellation() {
        let runtime = LarchRuntime::paused_current_thread().expect("runtime");
        let service = configured_service(&runtime);
        let cancellation = Cancellation::new();
        cancellation.cancel();

        let result =
            runtime.block_on(service.guard_operation(&cancellation, std::future::pending::<()>()));

        assert_eq!(result, Err(GitHubCompletionError::Cancelled));
    }

    #[test]
    fn operation_guard_enforces_overall_deadline() {
        let runtime = LarchRuntime::paused_current_thread().expect("runtime");
        let service = configured_service(&runtime);

        let result = runtime
            .block_on(service.guard_operation(&Cancellation::new(), std::future::pending::<()>()));

        assert_eq!(result, Err(GitHubCompletionError::DeadlineExceeded));
    }
}
