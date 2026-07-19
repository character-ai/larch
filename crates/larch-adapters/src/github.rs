//! Authenticated, policy-bound GitHub transport foundation.

use http::header::HeaderName;
use larch_core::{GitHubTransportPolicy, ProcessCancellation, RuntimeRedactor, SafeText, env};
use octocrab::Octocrab;
use std::{error::Error, ffi::OsString, fmt, future::Future};
use url::Url;

const API_BASE: &str = "https://api.github.com/";
const API_VERSION_HEADER: &str = "x-github-api-version";
const API_VERSION: &str = "2022-11-28";
const ACCEPT_VALUE: &str = "application/vnd.github+json";
const USER_AGENT_VALUE: &str = "larch";

/// Reason GitHub credential setup failed before any request was attempted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubCredentialErrorKind {
    Missing,
    Empty,
    NonUnicode,
}

/// Secret-free GitHub credential setup error.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GitHubCredentialError {
    kind: GitHubCredentialErrorKind,
}

impl GitHubCredentialError {
    #[must_use]
    pub const fn kind(self) -> GitHubCredentialErrorKind {
        self.kind
    }
}

impl fmt::Display for GitHubCredentialError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            GitHubCredentialErrorKind::Missing => {
                "LARCH_GH_TOKEN is required; export a non-empty GitHub token before starting larch"
            }
            GitHubCredentialErrorKind::Empty => {
                "LARCH_GH_TOKEN must not be empty or whitespace-only"
            }
            GitHubCredentialErrorKind::NonUnicode => {
                "LARCH_GH_TOKEN must be valid Unicode environment text"
            }
        })
    }
}

impl Error for GitHubCredentialError {}

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

trait EnvironmentSource {
    fn read(&self, name: &'static str) -> Option<OsString>;
}

struct ProcessEnvironment;

impl EnvironmentSource for ProcessEnvironment {
    fn read(&self, name: &'static str) -> Option<OsString> {
        std::env::var_os(name)
    }
}

// Deliberately non-Debug: a credential must not enter derived diagnostics.
struct GitHubCredential(String);

impl GitHubCredential {
    fn load(source: &dyn EnvironmentSource) -> Result<Self, GitHubCredentialError> {
        let raw = source
            .read(env::LARCH_GH_TOKEN)
            .ok_or(GitHubCredentialError {
                kind: GitHubCredentialErrorKind::Missing,
            })?;
        let value = raw.into_string().map_err(|_| GitHubCredentialError {
            kind: GitHubCredentialErrorKind::NonUnicode,
        })?;
        if value.trim().is_empty() {
            return Err(GitHubCredentialError {
                kind: GitHubCredentialErrorKind::Empty,
            });
        }
        Ok(Self(value))
    }

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
    pub(crate) policy: GitHubTransportPolicy,
    redactor: RuntimeRedactor,
}

impl OctocrabGitHubService {
    #[cfg(test)]
    pub(crate) fn with_test_client(client: Octocrab) -> Self {
        Self {
            client,
            policy: GitHubTransportPolicy::github_com(),
            redactor: RuntimeRedactor::default(),
        }
    }

    /// Load the sole supported credential and construct one hardened client.
    ///
    /// # Errors
    /// Fails before network access when `LARCH_GH_TOKEN` is missing, blank, or
    /// invalid, or when fixed client configuration cannot be constructed.
    pub fn from_environment() -> Result<Self, GitHubClientError> {
        Self::from_source(&ProcessEnvironment)
    }

    fn from_source(source: &dyn EnvironmentSource) -> Result<Self, GitHubClientError> {
        let credential = GitHubCredential::load(source)?;
        let policy = GitHubTransportPolicy::github_com();
        let mut redactor = RuntimeRedactor::default();
        let registered = redactor.register_exact_secret(credential.expose().to_owned());
        debug_assert!(registered, "validated GitHub credential must register");
        if tokio::runtime::Handle::try_current().is_err() {
            return Err(GitHubClientError::Configuration(redactor.safe_text(
                "GitHub transport must be constructed inside the larch Tokio runtime",
            )));
        }
        let client = build_client(&credential, policy).map_err(|error| {
            GitHubClientError::Configuration(redactor.safe_text(error.to_string()))
        })?;
        Ok(Self {
            client,
            policy,
            redactor,
        })
    }

    /// Fixed request headers applied to every GitHub API request.
    #[must_use]
    pub const fn required_headers() -> [(&'static str, &'static str); 3] {
        [
            ("user-agent", USER_AGENT_VALUE),
            ("accept", ACCEPT_VALUE),
            (API_VERSION_HEADER, API_VERSION),
        ]
    }

    /// Remove the exact runtime credential and standard secret families.
    #[must_use]
    pub fn redact_diagnostic(&self, text: impl AsRef<str>) -> SafeText {
        self.redactor.safe_text(text)
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
) -> octocrab::Result<Octocrab> {
    let mut builder = Octocrab::builder()
        .personal_token(credential.expose().to_owned())
        .set_connect_timeout(Some(policy.connect_timeout()))
        .set_read_timeout(Some(policy.read_timeout()))
        .set_write_timeout(Some(policy.write_timeout()))
        .base_uri(API_BASE)?
        .upload_uri(API_BASE)?;
    for (name, value) in OctocrabGitHubService::required_headers() {
        builder = builder.add_header(HeaderName::from_static(name), value.to_owned());
    }
    builder.build()
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::{Cancellation, LarchRuntime};
    use larch_core::{GitHubResponseLimits, GitHubService};
    use std::{collections::BTreeMap, sync::Mutex};

    struct FakeEnvironment {
        values: BTreeMap<&'static str, OsString>,
        reads: Mutex<Vec<&'static str>>,
    }

    impl FakeEnvironment {
        fn new(values: impl IntoIterator<Item = (&'static str, &'static str)>) -> Self {
            Self {
                values: values
                    .into_iter()
                    .map(|(key, value)| (key, OsString::from(value)))
                    .collect(),
                reads: Mutex::new(Vec::new()),
            }
        }
    }

    impl EnvironmentSource for FakeEnvironment {
        fn read(&self, name: &'static str) -> Option<OsString> {
            self.reads.lock().expect("read log lock").push(name);
            self.values.get(name).cloned()
        }
    }

    fn configured_service(runtime: &LarchRuntime) -> OctocrabGitHubService {
        runtime.block_on(async {
            OctocrabGitHubService::from_source(&FakeEnvironment::new([(
                env::LARCH_GH_TOKEN,
                "opaque test credential",
            )]))
            .expect("fixed client should build")
        })
    }

    #[test]
    fn credential_loader_reads_only_larch_token_without_fallbacks() {
        let source = FakeEnvironment::new([
            (env::GH_TOKEN, "legacy-token"),
            (env::GITHUB_TOKEN, "actions-token"),
        ]);

        let error = GitHubCredential::load(&source)
            .err()
            .expect("fallbacks must be ignored");

        assert_eq!(error.kind(), GitHubCredentialErrorKind::Missing);
        assert_eq!(
            source.reads.into_inner().expect("read log"),
            [env::LARCH_GH_TOKEN]
        );
    }

    #[test]
    fn credential_loader_rejects_empty_and_whitespace_values() {
        for value in ["", " \t\n"] {
            let error =
                GitHubCredential::load(&FakeEnvironment::new([(env::LARCH_GH_TOKEN, value)]))
                    .err()
                    .expect("blank token must fail");
            assert_eq!(error.kind(), GitHubCredentialErrorKind::Empty);
            assert_eq!(
                error.to_string(),
                "LARCH_GH_TOKEN must not be empty or whitespace-only"
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn credential_loader_rejects_non_unicode_without_echoing_bytes() {
        use std::os::unix::ffi::OsStringExt;

        let source = FakeEnvironment {
            values: BTreeMap::from([(env::LARCH_GH_TOKEN, OsString::from_vec(vec![0xff]))]),
            reads: Mutex::new(Vec::new()),
        };
        let error = GitHubCredential::load(&source)
            .err()
            .expect("non-Unicode token must fail");

        assert_eq!(error.kind(), GitHubCredentialErrorKind::NonUnicode);
        assert_eq!(
            error.to_string(),
            "LARCH_GH_TOKEN must be valid Unicode environment text"
        );
    }

    #[test]
    fn client_construction_outside_runtime_fails_without_secret_diagnostics() {
        let error = OctocrabGitHubService::from_source(&FakeEnvironment::new([(
            env::LARCH_GH_TOKEN,
            "unusual exact secret",
        )]))
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
                ("x-github-api-version", "2022-11-28"),
            ]
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
