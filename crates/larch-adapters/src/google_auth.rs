//! Hardened Google Application Default Credentials composition.

use std::{
    env,
    error::Error,
    ffi::OsStr,
    fmt,
    fs::File,
    io::{self, Read},
    path::{Path, PathBuf},
};

use google_cloud_auth::credentials::{Builder, Credentials};
use serde_json::{Map, Value};
use url::Url;

const MAX_ADC_BYTES: usize = 1_048_576;
const OAUTH_TOKEN_URL: &str = "https://oauth2.googleapis.com/token";
const STS_TOKEN_URL: &str = "https://sts.googleapis.com/v1/token";
const IAM_HOST: &str = "iamcredentials.googleapis.com";
const IAM_PATH_PREFIX: &str = "/v1/projects/-/serviceAccounts/";
const IAM_PATH_SUFFIX: &str = ":generateAccessToken";
const GCE_METADATA_HOST: &str = "GCE_METADATA_HOST";

const AWS_ROLE_URLS: [&str; 2] = [
    "http://169.254.169.254/latest/meta-data/iam/security-credentials",
    "http://[fd00:ec2::254]/latest/meta-data/iam/security-credentials",
];
const AWS_REGION_URLS: [&str; 2] = [
    "http://169.254.169.254/latest/meta-data/placement/availability-zone",
    "http://[fd00:ec2::254]/latest/meta-data/placement/availability-zone",
];
const AWS_SESSION_TOKEN_URLS: [&str; 2] = [
    "http://169.254.169.254/latest/api/token",
    "http://[fd00:ec2::254]/latest/api/token",
];
const AWS_VERIFICATION_URL: &str =
    "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15";

/// Stable failure classes for Google credential construction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GoogleAuthErrorKind {
    /// A caller did not provide a bounded Google OAuth scope.
    InvalidScope,
    /// Production composition found a test-only metadata endpoint override.
    MetadataOverride,
    /// The selected ADC file could not be read.
    CredentialRead,
    /// The selected ADC file exceeded the bounded input size.
    CredentialTooLarge,
    /// The selected ADC file was not valid JSON.
    InvalidCredential,
    /// Credential configuration named an unapproved source or endpoint.
    RejectedCredential,
    /// The official Google authentication library rejected the validated ADC.
    CredentialBuild,
}

/// A credential setup failure that never retains paths or credential data.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GoogleAuthError {
    kind: GoogleAuthErrorKind,
}

impl GoogleAuthError {
    const fn new(kind: GoogleAuthErrorKind) -> Self {
        Self { kind }
    }

    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(self) -> GoogleAuthErrorKind {
        self.kind
    }
}

impl fmt::Display for GoogleAuthError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            GoogleAuthErrorKind::InvalidScope => {
                "Google credentials require at least one explicit Google OAuth scope"
            }
            GoogleAuthErrorKind::MetadataOverride => {
                "Google metadata endpoint overrides are disabled in production"
            }
            GoogleAuthErrorKind::CredentialRead => "Google ADC could not be read",
            GoogleAuthErrorKind::CredentialTooLarge => "Google ADC exceeds the size limit",
            GoogleAuthErrorKind::InvalidCredential => "Google ADC is not valid credential JSON",
            GoogleAuthErrorKind::RejectedCredential => {
                "Google ADC contains an unapproved credential source or endpoint"
            }
            GoogleAuthErrorKind::CredentialBuild => {
                "Google ADC could not be loaded by the official authentication library"
            }
        })
    }
}

impl Error for GoogleAuthError {}

/// Official Google credentials loaded through the hardened larch boundary.
#[derive(Clone)]
pub struct GoogleAdc {
    credentials: Credentials,
}

impl fmt::Debug for GoogleAdc {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("GoogleAdc { credentials: [censored] }")
    }
}

impl GoogleAdc {
    /// Load standard ADC after validating scopes, endpoint policy, and any ADC file.
    ///
    /// Call this at production composition before worker threads start. The official
    /// library keeps access-token caching and refresh internal. Larch does not expose
    /// or persist the token.
    ///
    /// # Errors
    ///
    /// Returns a typed, credential-free error when scope or credential policy fails,
    /// an ADC file cannot be inspected, or the official builder rejects the input.
    pub fn load(scopes: &[&str]) -> Result<Self, GoogleAuthError> {
        validate_scopes(scopes)?;
        reject_metadata_override(env::var_os(GCE_METADATA_HOST).as_deref())?;
        inspect_selected_adc()?;

        let credentials = Builder::default()
            .with_scopes(scopes.iter().copied())
            .build()
            .map_err(|_error| GoogleAuthError::new(GoogleAuthErrorKind::CredentialBuild))?;
        Ok(Self { credentials })
    }

    /// Borrow the official credentials for a concrete Google service adapter.
    #[must_use]
    pub const fn credentials(&self) -> &Credentials {
        &self.credentials
    }
}

fn validate_scopes(scopes: &[&str]) -> Result<(), GoogleAuthError> {
    if scopes.is_empty() || scopes.iter().any(|scope| !is_google_scope(scope)) {
        return Err(GoogleAuthError::new(GoogleAuthErrorKind::InvalidScope));
    }
    Ok(())
}

fn is_google_scope(scope: &str) -> bool {
    let Ok(url) = Url::parse(scope) else {
        return false;
    };
    let Some(name) = url.path().strip_prefix("/auth/") else {
        return false;
    };
    url.scheme() == "https"
        && url.host_str() == Some("www.googleapis.com")
        && url.username().is_empty()
        && url.password().is_none()
        && url.port().is_none()
        && url.query().is_none()
        && url.fragment().is_none()
        && !name.is_empty()
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-._/".contains(&byte))
}

const fn reject_metadata_override(value: Option<&OsStr>) -> Result<(), GoogleAuthError> {
    if value.is_some() {
        return Err(GoogleAuthError::new(GoogleAuthErrorKind::MetadataOverride));
    }
    Ok(())
}

fn inspect_selected_adc() -> Result<(), GoogleAuthError> {
    let Some((path, required)) = selected_adc_path() else {
        return Ok(());
    };
    inspect_adc_path(&path, required)
}

fn inspect_adc_path(path: &Path, required: bool) -> Result<(), GoogleAuthError> {
    let file = match File::open(path) {
        Ok(file) => file,
        Err(error) if !required && error.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(_error) => return Err(GoogleAuthError::new(GoogleAuthErrorKind::CredentialRead)),
    };
    let mut document = Vec::new();
    file.take(u64::try_from(MAX_ADC_BYTES).expect("ADC size limit should fit in u64") + 1)
        .read_to_end(&mut document)
        .map_err(|_error| GoogleAuthError::new(GoogleAuthErrorKind::CredentialRead))?;
    validate_credential_document(&document)
}

fn selected_adc_path() -> Option<(PathBuf, bool)> {
    if let Some(path) = env::var_os(larch_core::env::GOOGLE_APPLICATION_CREDENTIALS) {
        return Some((PathBuf::from(path), true));
    }
    well_known_adc_path().map(|path| (path, false))
}

#[cfg(target_os = "windows")]
fn well_known_adc_path() -> Option<PathBuf> {
    env::var_os("APPDATA")
        .map(PathBuf::from)
        .map(|root| root.join("gcloud/application_default_credentials.json"))
}

#[cfg(not(target_os = "windows"))]
fn well_known_adc_path() -> Option<PathBuf> {
    env::var_os("HOME")
        .map(PathBuf::from)
        .map(|root| root.join(".config/gcloud/application_default_credentials.json"))
}

fn validate_credential_document(document: &[u8]) -> Result<(), GoogleAuthError> {
    if document.len() > MAX_ADC_BYTES {
        return Err(GoogleAuthError::new(
            GoogleAuthErrorKind::CredentialTooLarge,
        ));
    }
    let value: Value = serde_json::from_slice(document)
        .map_err(|_error| GoogleAuthError::new(GoogleAuthErrorKind::InvalidCredential))?;
    validate_credential(&value)
}

fn validate_credential(value: &Value) -> Result<(), GoogleAuthError> {
    let object = value
        .as_object()
        .ok_or_else(|| GoogleAuthError::new(GoogleAuthErrorKind::InvalidCredential))?;
    validate_universe(object)?;
    match string_field(object, "type")? {
        "authorized_user" => validate_authorized_user(object),
        "external_account" => validate_external_account(object),
        "impersonated_service_account" => validate_impersonated_account(object),
        _ => Ok(()),
    }
}

fn validate_universe(object: &Map<String, Value>) -> Result<(), GoogleAuthError> {
    if let Some(domain) = optional_string_field(object, "universe_domain")?
        && domain != "googleapis.com"
    {
        return rejected();
    }
    Ok(())
}

fn validate_authorized_user(object: &Map<String, Value>) -> Result<(), GoogleAuthError> {
    if let Some(token_uri) = optional_string_field(object, "token_uri")?
        && token_uri != OAUTH_TOKEN_URL
    {
        return rejected();
    }
    Ok(())
}

fn validate_impersonated_account(object: &Map<String, Value>) -> Result<(), GoogleAuthError> {
    validate_impersonation_url(string_field(object, "service_account_impersonation_url")?)?;
    let source = object
        .get("source_credentials")
        .ok_or_else(|| GoogleAuthError::new(GoogleAuthErrorKind::InvalidCredential))?;
    validate_credential(source)
}

fn validate_external_account(object: &Map<String, Value>) -> Result<(), GoogleAuthError> {
    if string_field(object, "token_url")? != STS_TOKEN_URL {
        return rejected();
    }
    if let Some(url) = optional_string_field(object, "service_account_impersonation_url")? {
        validate_impersonation_url(url)?;
    }

    let source = object
        .get("credential_source")
        .and_then(Value::as_object)
        .ok_or_else(|| GoogleAuthError::new(GoogleAuthErrorKind::InvalidCredential))?;
    if source.contains_key("executable") {
        return rejected();
    }
    if let Some(environment_id) = optional_string_field(source, "environment_id")? {
        return validate_aws_source(source, environment_id);
    }
    if let Some(url) = optional_string_field(source, "url")? {
        return validate_azure_source(url);
    }
    if optional_string_field(source, "file")?.is_some_and(|path| path.trim().is_empty()) {
        return rejected();
    }
    if source.contains_key("file") {
        return Ok(());
    }
    rejected()
}

fn validate_aws_source(
    source: &Map<String, Value>,
    environment_id: &str,
) -> Result<(), GoogleAuthError> {
    if environment_id != "aws1" {
        return rejected();
    }
    validate_optional_exact(source, "url", &AWS_ROLE_URLS)?;
    validate_optional_exact(source, "region_url", &AWS_REGION_URLS)?;
    validate_optional_exact(source, "imdsv2_session_token_url", &AWS_SESSION_TOKEN_URLS)?;
    validate_optional_exact(
        source,
        "regional_cred_verification_url",
        &[AWS_VERIFICATION_URL],
    )
}

fn validate_optional_exact(
    object: &Map<String, Value>,
    field: &str,
    allowed: &[&str],
) -> Result<(), GoogleAuthError> {
    if let Some(value) = optional_string_field(object, field)?
        && !allowed.contains(&value)
    {
        return rejected();
    }
    Ok(())
}

fn validate_azure_source(value: &str) -> Result<(), GoogleAuthError> {
    let url = Url::parse(value)
        .map_err(|_error| GoogleAuthError::new(GoogleAuthErrorKind::RejectedCredential))?;
    if url.scheme() != "http"
        || url.host_str() != Some("169.254.169.254")
        || !url.username().is_empty()
        || url.password().is_some()
        || url.port().is_some()
        || url.path() != "/metadata/identity/oauth2/token"
        || url.fragment().is_some()
    {
        return rejected();
    }
    let mut api_version = None;
    let mut resource = None;
    for (key, value) in url.query_pairs() {
        match key.as_ref() {
            "api-version" if api_version.is_none() => api_version = Some(value.into_owned()),
            "resource" if resource.is_none() => resource = Some(value.into_owned()),
            _ => return rejected(),
        }
    }
    if api_version.as_deref() != Some("2018-02-01") || resource.as_deref().is_none_or(str::is_empty)
    {
        return rejected();
    }
    Ok(())
}

fn validate_impersonation_url(value: &str) -> Result<(), GoogleAuthError> {
    let url = Url::parse(value)
        .map_err(|_error| GoogleAuthError::new(GoogleAuthErrorKind::RejectedCredential))?;
    if url.scheme() != "https"
        || url.host_str() != Some(IAM_HOST)
        || !url.username().is_empty()
        || url.password().is_some()
        || url.port().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
    {
        return rejected();
    }
    let Some(principal) = url
        .path()
        .strip_prefix(IAM_PATH_PREFIX)
        .and_then(|path| path.strip_suffix(IAM_PATH_SUFFIX))
    else {
        return rejected();
    };
    let Some((account, domain)) = principal.split_once('@') else {
        return rejected();
    };
    if account.is_empty()
        || !domain.ends_with(".iam.gserviceaccount.com")
        || principal.contains('/')
        || !principal
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-._@".contains(&byte))
    {
        return rejected();
    }
    Ok(())
}

fn string_field<'a>(
    object: &'a Map<String, Value>,
    field: &str,
) -> Result<&'a str, GoogleAuthError> {
    object
        .get(field)
        .and_then(Value::as_str)
        .ok_or_else(|| GoogleAuthError::new(GoogleAuthErrorKind::InvalidCredential))
}

fn optional_string_field<'a>(
    object: &'a Map<String, Value>,
    field: &str,
) -> Result<Option<&'a str>, GoogleAuthError> {
    object.get(field).map_or(Ok(None), |value| {
        value
            .as_str()
            .map(Some)
            .ok_or_else(|| GoogleAuthError::new(GoogleAuthErrorKind::InvalidCredential))
    })
}

const fn rejected<T>() -> Result<T, GoogleAuthError> {
    Err(GoogleAuthError::new(
        GoogleAuthErrorKind::RejectedCredential,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_test_support::TestWorkspace;
    use serde_json::json;

    fn validate(value: &Value) -> Result<(), GoogleAuthError> {
        validate_credential_document(&serde_json::to_vec(value).expect("fixture should serialize"))
    }

    fn external_account(source: &Value) -> Value {
        json!({
            "type": "external_account",
            "audience": "//iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/pool/providers/provider",
            "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
            "token_url": STS_TOKEN_URL,
            "credential_source": source,
        })
    }

    #[test]
    fn scopes_must_be_explicit_google_scopes() {
        assert_eq!(
            validate_scopes(&[])
                .expect_err("empty scopes should fail")
                .kind(),
            GoogleAuthErrorKind::InvalidScope
        );
        assert_eq!(
            validate_scopes(&["cloud-platform"])
                .expect_err("short scope should fail")
                .kind(),
            GoogleAuthErrorKind::InvalidScope
        );
        assert_eq!(
            validate_scopes(&["https://www.googleapis.com/auth/read?scope=write"])
                .expect_err("scope query should fail")
                .kind(),
            GoogleAuthErrorKind::InvalidScope
        );
        validate_scopes(&["https://www.googleapis.com/auth/cloud-platform.read-only"])
            .expect("Google scope should pass");
    }

    #[test]
    fn metadata_override_is_always_rejected() {
        assert_eq!(
            reject_metadata_override(Some(OsStr::new("127.0.0.1:8080")))
                .expect_err("override should fail")
                .kind(),
            GoogleAuthErrorKind::MetadataOverride
        );
        reject_metadata_override(None).expect("absent override should pass");
    }

    #[test]
    fn adc_file_inspection_is_offline_bounded_and_fail_closed() {
        let workspace = TestWorkspace::new().expect("test workspace");
        let valid = workspace
            .write(
                "valid.json",
                serde_json::to_vec(&json!({
                    "type": "authorized_user",
                    "token_uri": OAUTH_TOKEN_URL,
                }))
                .expect("fixture should serialize"),
            )
            .expect("write valid fixture");
        inspect_adc_path(&valid, true).expect("valid ADC should pass inspection");

        let missing = workspace.path("missing.json").expect("missing path");
        inspect_adc_path(&missing, false).expect("missing well-known ADC should use metadata");
        assert_eq!(
            inspect_adc_path(&missing, true)
                .expect_err("missing explicit ADC should fail")
                .kind(),
            GoogleAuthErrorKind::CredentialRead
        );

        let oversized = workspace
            .write("oversized.json", vec![b' '; MAX_ADC_BYTES + 1])
            .expect("write oversized fixture");
        assert_eq!(
            inspect_adc_path(&oversized, true)
                .expect_err("oversized ADC should fail")
                .kind(),
            GoogleAuthErrorKind::CredentialTooLarge
        );
    }

    #[test]
    fn wrapper_debug_output_censors_official_credentials() {
        let adc = GoogleAdc {
            credentials: google_cloud_auth::credentials::anonymous::Builder::new().build(),
        };
        assert_eq!(format!("{adc:?}"), "GoogleAdc { credentials: [censored] }");
        let _credentials = adc.credentials();
    }

    #[test]
    fn authorized_user_accepts_only_the_google_token_endpoint() {
        validate(&json!({
            "type": "authorized_user",
            "client_id": "client",
            "client_secret": "secret",
            "refresh_token": "refresh",
            "token_uri": OAUTH_TOKEN_URL,
        }))
        .expect("standard endpoint should pass");
        let error = validate(&json!({
            "type": "authorized_user",
            "token_uri": "https://attacker.example/token",
        }))
        .expect_err("custom endpoint should fail");
        assert_eq!(error.kind(), GoogleAuthErrorKind::RejectedCredential);
    }

    #[test]
    fn executable_external_account_source_is_rejected() {
        let error = validate(&external_account(&json!({
            "executable": { "command": "/tmp/token" }
        })))
        .expect_err("executable source should fail");
        assert_eq!(error.kind(), GoogleAuthErrorKind::RejectedCredential);
    }

    #[test]
    fn file_external_account_source_is_accepted() {
        validate(&external_account(&json!({ "file": "/operator/token.jwt" })))
            .expect("operator-selected subject token file should pass");
        assert_eq!(
            validate(&external_account(&json!({ "file": "  " })))
                .expect_err("blank subject-token file should fail")
                .kind(),
            GoogleAuthErrorKind::RejectedCredential
        );
    }

    #[test]
    fn external_account_requires_the_google_sts_endpoint() {
        let mut value = external_account(&json!({ "file": "/operator/token.jwt" }));
        value["token_url"] = json!("https://attacker.example/token");
        assert_eq!(
            validate(&value).expect_err("custom STS should fail").kind(),
            GoogleAuthErrorKind::RejectedCredential
        );
    }

    #[test]
    fn azure_source_requires_the_documented_metadata_endpoint() {
        validate(&external_account(&json!({
            "url": "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F",
            "headers": { "Metadata": "True" }
        })))
        .expect("documented Azure endpoint should pass");
        assert_eq!(
            validate(&external_account(
                &json!({ "url": "http://127.0.0.1/token" })
            ))
            .expect_err("custom URL should fail")
            .kind(),
            GoogleAuthErrorKind::RejectedCredential
        );
    }

    #[test]
    fn aws_source_requires_documented_metadata_endpoints() {
        validate(&external_account(&json!({
            "environment_id": "aws1",
            "url": AWS_ROLE_URLS[0],
            "region_url": AWS_REGION_URLS[0],
            "imdsv2_session_token_url": AWS_SESSION_TOKEN_URLS[0],
            "regional_cred_verification_url": AWS_VERIFICATION_URL,
        })))
        .expect("documented AWS endpoints should pass");

        let error = validate(&external_account(&json!({
            "environment_id": "aws1",
            "region_url": "http://attacker.example/region",
        })))
        .expect_err("custom AWS endpoint should fail");
        assert_eq!(error.kind(), GoogleAuthErrorKind::RejectedCredential);
    }

    #[test]
    fn impersonation_url_and_nested_source_are_validated() {
        validate(&json!({
            "type": "impersonated_service_account",
            "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/target@example.iam.gserviceaccount.com:generateAccessToken",
            "source_credentials": {
                "type": "authorized_user",
                "token_uri": OAUTH_TOKEN_URL,
            }
        }))
        .expect("standard impersonation should pass");

        let error = validate(&json!({
            "type": "impersonated_service_account",
            "service_account_impersonation_url": "https://attacker.example/v1/projects/-/serviceAccounts/target@example.com:generateAccessToken",
            "source_credentials": { "type": "service_account" },
        }))
        .expect_err("custom impersonation endpoint should fail");
        assert_eq!(error.kind(), GoogleAuthErrorKind::RejectedCredential);

        let error = validate(&json!({
            "type": "impersonated_service_account",
            "service_account_impersonation_url": "https://user@iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/target@example.iam.gserviceaccount.com:generateAccessToken",
            "source_credentials": { "type": "service_account" },
        }))
        .expect_err("URL user information should fail");
        assert_eq!(error.kind(), GoogleAuthErrorKind::RejectedCredential);
    }

    #[test]
    fn custom_universe_and_oversized_documents_fail_closed() {
        assert_eq!(
            validate(&json!({
                "type": "service_account",
                "universe_domain": "attacker.example",
            }))
            .expect_err("custom universe should fail")
            .kind(),
            GoogleAuthErrorKind::RejectedCredential
        );
        assert_eq!(
            validate_credential_document(&vec![b' '; MAX_ADC_BYTES + 1])
                .expect_err("oversized input should fail")
                .kind(),
            GoogleAuthErrorKind::CredentialTooLarge
        );
    }

    #[test]
    fn malformed_and_unknown_credential_shapes_route_explicitly() {
        assert_eq!(
            validate_credential_document(b"not-json")
                .expect_err("malformed JSON should fail")
                .kind(),
            GoogleAuthErrorKind::InvalidCredential
        );
        assert_eq!(
            validate(&json!([]))
                .expect_err("non-object credentials should fail")
                .kind(),
            GoogleAuthErrorKind::InvalidCredential
        );
        assert_eq!(
            validate(&json!({ "type": 7 }))
                .expect_err("non-string type should fail")
                .kind(),
            GoogleAuthErrorKind::InvalidCredential
        );
        validate(&json!({ "type": "future_official_type" }))
            .expect("the official builder owns unknown-type rejection");
        assert_eq!(
            validate(&external_account(&json!({})))
                .expect_err("missing subject-token source should fail")
                .kind(),
            GoogleAuthErrorKind::RejectedCredential
        );
    }

    #[test]
    fn diagnostics_do_not_include_paths_or_credential_values() {
        let rendered = [
            GoogleAuthErrorKind::InvalidScope,
            GoogleAuthErrorKind::MetadataOverride,
            GoogleAuthErrorKind::CredentialRead,
            GoogleAuthErrorKind::CredentialTooLarge,
            GoogleAuthErrorKind::InvalidCredential,
            GoogleAuthErrorKind::RejectedCredential,
            GoogleAuthErrorKind::CredentialBuild,
        ]
        .map(|kind| GoogleAuthError::new(kind).to_string())
        .join(" ");
        assert!(!rendered.contains("/operator/token.jwt"));
        assert!(!rendered.contains("refresh"));
    }

    #[tokio::test]
    #[ignore = "requires LARCH_LIVE_GOOGLE_ADC=1 and least-privilege ADC"]
    async fn live_adc_returns_an_authorization_header_without_rendering_it() {
        if env::var("LARCH_LIVE_GOOGLE_ADC").as_deref() != Ok("1") {
            return;
        }
        let adc = GoogleAdc::load(&["https://www.googleapis.com/auth/cloud-platform.read-only"])
            .expect("live ADC should load");
        let headers = adc
            .credentials()
            .headers(http::Extensions::default())
            .await
            .expect("live ADC should obtain headers");
        let google_cloud_auth::credentials::CacheableResource::New { data, .. } = headers else {
            panic!("first credential lookup should return headers");
        };
        assert!(data.keys().any(|name| name.as_str() == "authorization"));
    }
}
