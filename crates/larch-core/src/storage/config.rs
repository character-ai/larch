//! Storage configuration resolution, URI parsing, and derived tool identity.
//!
//! Port of Python `larch.report.storage_config`, config resolution and
//! URI/identity only. Git remote discovery and provider preflight (network,
//! process spawn) stay out of `larch-core` and live in `larch-adapters` /
//! `larch-cli`.

use std::{
    collections::HashMap,
    error::Error,
    fmt::{self, Write as _},
    fs,
    path::Path,
    sync::LazyLock,
};

use regex::Regex;
use sha2::{Digest, Sha256};

/// Repository-relative path to the optional storage configuration file.
pub const STORAGE_CONFIG_RELPATH: &str = "tools-config.toml";
/// The fixed tool namespace segment shared by every larch storage root.
pub const LARCH_TOOL_NAME: &str = "larch";
/// The sole recognized key inside the `[larch]` configuration table.
pub const STORAGE_BASE_URI_FIELD: &str = "storage_base_uri";
/// The child data namespace used for published run-log archives.
pub const RUN_LOGS_DATA_TYPE: &str = "run-logs";
/// Accepted object-storage URI schemes, in Python declaration order.
pub const STORAGE_URI_SCHEMES: [&str; 3] = ["gs", "r2", "s3"];
/// Legacy, no-longer-supported base-URI override name.
pub const ENV_LARCH_LOGS_URI: &str = crate::config::env::LARCH_LOGS_URI;
/// Base object-storage URI override name.
pub const ENV_LARCH_STORAGE_BASE_URI: &str = crate::config::env::LARCH_STORAGE_BASE_URI;
/// Cloudflare R2 account identifier override name.
pub const ENV_LARCH_R2_ACCOUNT_ID: &str = crate::config::env::LARCH_R2_ACCOUNT_ID;
/// Cloudflare R2 endpoint override name.
pub const ENV_LARCH_R2_ENDPOINT: &str = crate::config::env::LARCH_R2_ENDPOINT;
/// Domain separator binding the local disabled-storage namespace to this schema version.
pub const LOCAL_NAMESPACE_DOMAIN: &[u8] = b"larch-run-log-local-namespace-v1\0";

const ASCII_CONTROL_CHARACTER_MAX: u32 = 32;
const ASCII_DELETE: u32 = 127;

static CLIENT_REPO_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?$")
        .expect("static client-repo regex must compile")
});
static SCP_REMOTE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?:[A-Za-z0-9._-]+@)?[^/:@\s]+:[^:\s]+$")
        .expect("static scp remote regex must compile")
});

/// The repository's storage configuration or identity is invalid.
///
/// The message is always a fixed guidance string; it never carries raw
/// credentials, secrets, or the untrusted URI/remote text that triggered it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StorageConfigurationError(String);

impl StorageConfigurationError {
    #[must_use]
    pub fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for StorageConfigurationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for StorageConfigurationError {}

/// The configured tool and repository prefix cannot be listed.
///
/// Preflight execution (provider transport) stays in adapters; this type is
/// the credential-free failure they report through.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StoragePreflightError(String);

impl StoragePreflightError {
    #[must_use]
    pub fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for StoragePreflightError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for StoragePreflightError {}

/// Validated provider, bucket, and optional base prefix.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StorageBase {
    pub scheme: String,
    pub bucket: String,
    pub prefix: String,
}

impl StorageBase {
    /// Construct a base with no prefix.
    #[must_use]
    pub fn new(scheme: impl Into<String>, bucket: impl Into<String>) -> Self {
        Self {
            scheme: scheme.into(),
            bucket: bucket.into(),
            prefix: String::new(),
        }
    }

    /// Construct a base with an explicit prefix.
    #[must_use]
    pub fn with_prefix(
        scheme: impl Into<String>,
        bucket: impl Into<String>,
        prefix: impl Into<String>,
    ) -> Self {
        Self {
            scheme: scheme.into(),
            bucket: bucket.into(),
            prefix: prefix.into(),
        }
    }

    /// Return the canonical configured base URI.
    #[must_use]
    pub fn uri(&self) -> String {
        if self.prefix.is_empty() {
            format!("{}://{}", self.scheme, self.bucket)
        } else {
            format!("{}://{}/{}", self.scheme, self.bucket, self.prefix)
        }
    }

    /// Return the provider bucket root.
    #[must_use]
    pub fn bucket_uri(&self) -> String {
        format!("{}://{}", self.scheme, self.bucket)
    }
}

/// The fixed larch namespace for one Git-origin-derived repository.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ToolRepositoryStorage {
    pub base: StorageBase,
    pub client_repo: String,
}

impl ToolRepositoryStorage {
    #[must_use]
    pub fn new(base: StorageBase, client_repo: impl Into<String>) -> Self {
        Self {
            base,
            client_repo: client_repo.into(),
        }
    }

    #[must_use]
    pub fn scheme(&self) -> &str {
        &self.base.scheme
    }

    #[must_use]
    pub fn bucket(&self) -> &str {
        &self.base.bucket
    }

    #[must_use]
    pub fn prefix(&self) -> String {
        let mut parts: Vec<&str> = Vec::with_capacity(3);
        if !self.base.prefix.is_empty() {
            parts.push(&self.base.prefix);
        }
        parts.push(LARCH_TOOL_NAME);
        parts.push(&self.client_repo);
        parts.join("/")
    }

    /// Return the canonical tool and client-repository root.
    #[must_use]
    pub fn uri(&self) -> String {
        format!(
            "{}://{}/{}",
            self.base.scheme,
            self.base.bucket,
            self.prefix()
        )
    }

    /// Bind local mutable state to the complete canonical remote origin.
    #[must_use]
    pub fn storage_origin_id(&self) -> String {
        hex_lower(&Sha256::digest(self.uri().as_bytes()))
    }

    /// Return one validated child data namespace.
    ///
    /// # Errors
    ///
    /// Returns [`StorageConfigurationError`] when `data_type` is empty, `.`,
    /// `..`, contains a path separator, or contains whitespace or control
    /// characters.
    pub fn data_uri(&self, data_type: &str) -> Result<String, StorageConfigurationError> {
        let child = validated_path_component(data_type, "data type")?;
        Ok(format!("{}/{child}/", self.uri()))
    }

    /// Return the deterministic remote root for run archives.
    ///
    /// # Panics
    ///
    /// Never panics: [`RUN_LOGS_DATA_TYPE`] is a fixed, valid path component.
    #[must_use]
    pub fn run_logs_uri(&self) -> String {
        self.data_uri(RUN_LOGS_DATA_TYPE)
            .expect("RUN_LOGS_DATA_TYPE is a fixed valid path component")
    }
}

/// Pinned enabled or disabled run-log publication mode.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RunLogStorageMode {
    Enabled,
    Disabled,
}

impl RunLogStorageMode {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Enabled => "enabled",
            Self::Disabled => "disabled",
        }
    }
}

impl fmt::Display for RunLogStorageMode {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// Why run-log storage resolved to its pinned mode, matching Python's
/// `RunLogStorageReason` literal values exactly.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RunLogStorageReason {
    EnvironmentOverride,
    RepositoryConfig,
    InjectedStorage,
    ConfigFileMissing,
    LarchTableMissing,
    StorageBaseUriOmitted,
}

impl RunLogStorageReason {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EnvironmentOverride => "environment-override",
            Self::RepositoryConfig => "repository-config",
            Self::InjectedStorage => "injected-storage",
            Self::ConfigFileMissing => "config-file-missing",
            Self::LarchTableMissing => "larch-table-missing",
            Self::StorageBaseUriOmitted => "storage-base-uri-omitted",
        }
    }

    /// Return whether this reason is only valid for enabled storage.
    #[must_use]
    pub const fn is_enabled_reason(self) -> bool {
        matches!(
            self,
            Self::EnvironmentOverride | Self::RepositoryConfig | Self::InjectedStorage
        )
    }
}

impl fmt::Display for RunLogStorageReason {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// Pinned enabled or disabled run-log publication state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunLogStorageResolution {
    mode: RunLogStorageMode,
    reason: RunLogStorageReason,
    storage: Option<ToolRepositoryStorage>,
    client_repo: String,
    local_namespace_id: Option<String>,
}

impl RunLogStorageResolution {
    /// Construct a resolution, validating internal consistency.
    ///
    /// # Errors
    ///
    /// Returns [`StorageConfigurationError`] when the reason does not match
    /// the mode, the storage presence does not match the mode, the local
    /// namespace ID presence does not match the mode, or the storage's
    /// `client_repo` disagrees with `client_repo`.
    pub fn new(
        mode: RunLogStorageMode,
        reason: RunLogStorageReason,
        storage: Option<ToolRepositoryStorage>,
        client_repo: impl Into<String>,
        local_namespace_id: Option<String>,
    ) -> Result<Self, StorageConfigurationError> {
        let client_repo = client_repo.into();
        let enabled = matches!(mode, RunLogStorageMode::Enabled);
        let valid_reason = reason.is_enabled_reason() == enabled;
        let storage_matches_client_repo = storage
            .as_ref()
            .is_none_or(|storage| storage.client_repo == client_repo);
        if !valid_reason
            || enabled != storage.is_some()
            || enabled == local_namespace_id.is_some()
            || !storage_matches_client_repo
        {
            return Err(StorageConfigurationError::new(
                "inconsistent run-log storage resolution",
            ));
        }
        Ok(Self {
            mode,
            reason,
            storage,
            client_repo,
            local_namespace_id,
        })
    }

    #[must_use]
    pub const fn mode(&self) -> RunLogStorageMode {
        self.mode
    }

    #[must_use]
    pub const fn reason(&self) -> RunLogStorageReason {
        self.reason
    }

    #[must_use]
    pub const fn storage(&self) -> Option<&ToolRepositoryStorage> {
        self.storage.as_ref()
    }

    #[must_use]
    pub fn client_repo(&self) -> &str {
        &self.client_repo
    }

    #[must_use]
    pub fn local_namespace_id(&self) -> Option<&str> {
        self.local_namespace_id.as_deref()
    }
}

/// Require enabled storage or fail with actionable configuration guidance.
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when `resolution` is disabled.
pub fn require_enabled_storage(
    resolution: &RunLogStorageResolution,
) -> Result<ToolRepositoryStorage, StorageConfigurationError> {
    resolution.storage().cloned().ok_or_else(|| {
        StorageConfigurationError::new(
            "run-log storage is disabled; configure [larch].storage_base_uri or set \
             LARCH_STORAGE_BASE_URI",
        )
    })
}

/// Wrap test- or caller-pinned provider storage in an enabled resolution.
///
/// # Panics
///
/// Never panics: an enabled resolution built from `storage`'s own
/// `client_repo` is always internally consistent.
#[must_use]
pub fn injected_storage_resolution(storage: ToolRepositoryStorage) -> RunLogStorageResolution {
    let client_repo = storage.client_repo.clone();
    RunLogStorageResolution::new(
        RunLogStorageMode::Enabled,
        RunLogStorageReason::InjectedStorage,
        Some(storage),
        client_repo,
        None,
    )
    .expect("injected storage resolution is always internally consistent")
}

/// Validate the closed lowercase client-repository slug.
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when `value` does not match the
/// lowercase repository-slug grammar.
pub fn validate_client_repo(value: &str) -> Result<String, StorageConfigurationError> {
    if !CLIENT_REPO_PATTERN.is_match(value) || value == "." || value == ".." {
        return Err(StorageConfigurationError::new(
            "Git remote.origin.url did not yield a valid lowercase repository slug; set \
             remote.origin.url to a standard HTTPS, SSH, or SCP-like repository URL",
        ));
    }
    Ok(value.to_string())
}

/// Extract the final path component of a Git remote without ever returning
/// the remote text (which may carry credentials) in an error message.
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when `remote` is missing, malformed,
/// credential-bearing, decorated with a port/query/fragment, or ambiguous.
pub fn repository_leaf_from_remote(remote: &str) -> Result<String, StorageConfigurationError> {
    if remote.is_empty()
        || remote != remote.trim()
        || remote.chars().any(|character| {
            (character as u32) < ASCII_CONTROL_CHARACTER_MAX || (character as u32) == ASCII_DELETE
        })
    {
        return Err(StorageConfigurationError::new(
            "remote.origin.url is missing or malformed; set it to a standard HTTPS, SSH, or \
             SCP-like repository URL",
        ));
    }

    let path: &str = if remote.contains("://") {
        let split = split_uri(remote).ok_or_else(unsupported_remote_syntax_error)?;
        let (password_present, username_present, has_port) =
            netloc_credential_signals(split.netloc);
        let unsupported_shape = !matches!(split.scheme.as_str(), "https" | "ssh")
            || split.netloc.is_empty()
            || !split.path.starts_with('/');
        let credential_bearing = password_present || (split.scheme == "https" && username_present);
        let decorated = has_port
            || split.query.is_some_and(|value| !value.is_empty())
            || split.fragment.is_some_and(|value| !value.is_empty());
        if unsupported_shape || credential_bearing || decorated {
            return Err(unsupported_remote_syntax_error());
        }
        split.path
    } else {
        if !SCP_REMOTE_PATTERN.is_match(remote) {
            return Err(StorageConfigurationError::new(
                "remote.origin.url uses unsupported or ambiguous syntax; set a standard HTTPS, \
                 SSH, or SCP-like repository URL",
            ));
        }
        // The pattern requires exactly one unescaped ':' outside user/host; take the
        // remainder after the first ':' that follows an optional `user@host` prefix.
        scp_path(remote)
    };

    let trimmed = path.trim_start_matches('/');
    let segments: Vec<&str> = trimmed.split('/').collect();
    if path.ends_with('/')
        || path.contains("//")
        || segments
            .iter()
            .any(|segment| segment.is_empty() || *segment == "." || *segment == "..")
    {
        return Err(StorageConfigurationError::new(
            "remote.origin.url has an ambiguous repository path; set a standard repository URL",
        ));
    }
    let leaf = segments.last().copied().unwrap_or("");
    let leaf = leaf.strip_suffix(".git").unwrap_or(leaf);
    validate_client_repo(&leaf.to_ascii_lowercase())
}

fn unsupported_remote_syntax_error() -> StorageConfigurationError {
    StorageConfigurationError::new(
        "remote.origin.url uses unsupported or credential-bearing syntax; set a credential-free \
         standard HTTPS or SSH repository URL",
    )
}

/// Return the `path` group of the SCP-like remote grammar
/// `[user@]host:path`, matching `_SCP_REMOTE_RE` in the Python port.
fn scp_path(remote: &str) -> &str {
    let after_at = remote.rfind('@').map_or(remote, |idx| &remote[idx + 1..]);
    let colon = after_at.find(':').expect("SCP pattern guarantees a colon");
    &after_at[colon + 1..]
}

/// Rehydrate a canonical persisted tool-repository URI.
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when the scheme, bucket, or prefix
/// are invalid, the namespace does not end in `.../larch/<client_repo>`, the
/// derived `client_repo` disagrees with `expected_client_repo`, or the
/// reconstructed URI is not byte-identical to `raw_uri`.
pub fn parse_tool_repository_uri(
    raw_uri: &str,
    expected_client_repo: Option<&str>,
) -> Result<ToolRepositoryStorage, StorageConfigurationError> {
    let split = split_uri(raw_uri).ok_or_else(|| {
        StorageConfigurationError::new("persisted tool repository URI has an invalid scheme")
    })?;
    if !STORAGE_URI_SCHEMES.contains(&split.scheme.as_str()) {
        return Err(StorageConfigurationError::new(
            "persisted tool repository URI has an invalid scheme",
        ));
    }
    let bucket = validated_bucket(split.netloc)?;
    let prefix = validated_prefix(split.path)?;
    let parts: Vec<&str> = prefix.split('/').collect();
    if parts.len() < 2 || parts[parts.len() - 2] != LARCH_TOOL_NAME {
        return Err(StorageConfigurationError::new(
            "persisted tool repository URI has an invalid namespace",
        ));
    }
    let client_repo = validate_client_repo(parts[parts.len() - 1])?;
    if expected_client_repo.is_some_and(|expected| expected != client_repo) {
        return Err(StorageConfigurationError::new(
            "persisted tool repository identity changed",
        ));
    }
    let base_prefix = parts[..parts.len() - 2].join("/");
    let storage = ToolRepositoryStorage::new(
        StorageBase::with_prefix(split.scheme, bucket, base_prefix),
        client_repo,
    );
    if storage.uri() != raw_uri {
        return Err(StorageConfigurationError::new(
            "persisted tool repository URI is not canonical",
        ));
    }
    Ok(storage)
}

/// Validate a base URI without adding the tool or repository namespace.
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when the URI is empty, has
/// surrounding whitespace, uses an unsupported scheme, carries credentials,
/// a port, a query, or a fragment, or has an unsafe bucket or prefix.
pub fn parse_storage_base_uri(raw_uri: &str) -> Result<StorageBase, StorageConfigurationError> {
    if raw_uri.is_empty() || raw_uri != raw_uri.trim() {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri must be a non-empty URI without surrounding whitespace",
        ));
    }
    let split = split_uri(raw_uri).ok_or_else(unsupported_scheme_error)?;
    if !STORAGE_URI_SCHEMES.contains(&split.scheme.as_str())
        || !raw_uri.starts_with(&format!("{}://", split.scheme))
    {
        return Err(unsupported_scheme_error());
    }
    if split.query.is_some_and(|value| !value.is_empty())
        || split.fragment.is_some_and(|value| !value.is_empty())
    {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri must not contain a query or fragment",
        ));
    }
    Ok(StorageBase::with_prefix(
        split.scheme,
        validated_bucket(split.netloc)?,
        validated_prefix(split.path)?,
    ))
}

fn unsupported_scheme_error() -> StorageConfigurationError {
    let accepted = STORAGE_URI_SCHEMES
        .iter()
        .map(|scheme| format!("{scheme}://"))
        .collect::<Vec<_>>()
        .join(", ");
    StorageConfigurationError::new(format!(
        "[larch].storage_base_uri must use one of: {accepted}"
    ))
}

fn validated_bucket(netloc: &str) -> Result<String, StorageConfigurationError> {
    if netloc.contains('@') {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri must not contain credentials",
        ));
    }
    let unsafe_bucket = netloc.is_empty()
        || netloc.contains(':')
        || netloc.contains('\\')
        || netloc.chars().any(|character| {
            character.is_whitespace()
                || (character as u32) < ASCII_CONTROL_CHARACTER_MAX
                || (character as u32) == ASCII_DELETE
        });
    if unsafe_bucket {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri must contain a plain bucket name without a port",
        ));
    }
    Ok(netloc.to_string())
}

fn validated_prefix(path: &str) -> Result<String, StorageConfigurationError> {
    if path.is_empty() {
        return Ok(String::new());
    }
    if !path.starts_with('/') || path.ends_with('/') {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri must not have a trailing slash",
        ));
    }
    let segments: Vec<&str> = path[1..].split('/').collect();
    if segments
        .iter()
        .any(|segment| segment.is_empty() || *segment == "." || *segment == "..")
    {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri prefix must not contain empty, '.' or '..' segments",
        ));
    }
    if segments.iter().any(|segment| {
        segment.contains('\\')
            || segment.chars().any(|character| {
                character.is_whitespace()
                    || (character as u32) < ASCII_CONTROL_CHARACTER_MAX
                    || (character as u32) == ASCII_DELETE
            })
    }) {
        return Err(StorageConfigurationError::new(
            "[larch].storage_base_uri prefix must not contain whitespace or control characters",
        ));
    }
    Ok(segments.join("/"))
}

fn validated_path_component(value: &str, label: &str) -> Result<String, StorageConfigurationError> {
    let invalid = value.is_empty()
        || value == "."
        || value == ".."
        || value.contains('/')
        || value.contains('\\')
        || value.chars().any(|character| {
            character.is_whitespace()
                || (character as u32) < ASCII_CONTROL_CHARACTER_MAX
                || (character as u32) == ASCII_DELETE
        });
    if invalid {
        return Err(StorageConfigurationError::new(format!("invalid {label}")));
    }
    Ok(value.to_string())
}

/// A minimal `scheme://netloc/path?query#fragment` split, matching the
/// fields of Python's `urllib.parse.urlsplit` that this module consumes.
struct SplitUri<'a> {
    scheme: String,
    netloc: &'a str,
    path: &'a str,
    query: Option<&'a str>,
    fragment: Option<&'a str>,
}

/// Split `raw` at its first `"://"`, matching `urlsplit`'s netloc, path,
/// query, and fragment extraction order for that shape. Returns `None` when
/// `raw` has no `"://"` delimiter.
fn split_uri(raw: &str) -> Option<SplitUri<'_>> {
    let scheme_end = raw.find("://")?;
    let scheme = raw[..scheme_end].to_ascii_lowercase();
    let rest = &raw[scheme_end + 3..];
    let delimiter = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    let netloc = &rest[..delimiter];
    let remainder = &rest[delimiter..];
    let (before_fragment, fragment) = remainder.find('#').map_or((remainder, None), |idx| {
        (&remainder[..idx], Some(&remainder[idx + 1..]))
    });
    let (path, query) = before_fragment
        .find('?')
        .map_or((before_fragment, None), |idx| {
            (&before_fragment[..idx], Some(&before_fragment[idx + 1..]))
        });
    Some(SplitUri {
        scheme,
        netloc,
        path,
        query,
        fragment,
    })
}

/// Return `(password_present, username_present, port_present)` for a netloc,
/// matching the credential and port signals `_repository_leaf` reads from
/// `urlsplit`'s `username` / `password` / `port` properties. A password
/// counts as present once `userinfo` contains `:`, even with nothing after
/// it, matching Python's `partition(':')` semantics.
fn netloc_credential_signals(netloc: &str) -> (bool, bool, bool) {
    let (userinfo, hostinfo) = netloc.rfind('@').map_or((None, netloc), |idx| {
        (Some(&netloc[..idx]), &netloc[idx + 1..])
    });
    let (username_present, password_present) =
        userinfo.map_or((false, false), |info| (true, info.contains(':')));
    let port_present = hostinfo
        .find(':')
        .is_some_and(|idx| !hostinfo[idx + 1..].is_empty());
    (password_present, username_present, port_present)
}

fn repository_label(repo_root: &Path) -> String {
    repo_root
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .filter(|name| !name.is_empty())
        .unwrap_or_else(|| repo_root.display().to_string())
}

fn load_repository_config(
    repo_root: &Path,
) -> Result<Option<toml::Table>, StorageConfigurationError> {
    let config_path = repo_root.join(STORAGE_CONFIG_RELPATH);
    let repo_label = repository_label(repo_root);
    let Ok(metadata) = fs::symlink_metadata(&config_path) else {
        return Ok(None);
    };
    if metadata.file_type().is_symlink() {
        return Err(StorageConfigurationError::new(format!(
            "{STORAGE_CONFIG_RELPATH}: refusing symlink in Git repository {repo_label}"
        )));
    }
    if !metadata.is_file() {
        return Err(StorageConfigurationError::new(format!(
            "{STORAGE_CONFIG_RELPATH}: must be a regular file in Git repository {repo_label}"
        )));
    }
    let raw = fs::read_to_string(&config_path).map_err(|_| {
        StorageConfigurationError::new(format!(
            "{STORAGE_CONFIG_RELPATH}: cannot read configuration in Git repository {repo_label}; \
             add readable [larch] with storage_base_uri"
        ))
    })?;
    raw.parse::<toml::Table>().map(Some).map_err(|_| {
        StorageConfigurationError::new(format!(
            "{STORAGE_CONFIG_RELPATH}: malformed TOML in Git repository {repo_label}"
        ))
    })
}

fn configured_storage_base(
    repo_root: &Path,
    environ: &HashMap<String, String>,
) -> Result<(Option<StorageBase>, RunLogStorageReason), StorageConfigurationError> {
    if environ
        .get(ENV_LARCH_LOGS_URI)
        .is_some_and(|value| !value.is_empty())
    {
        return Err(StorageConfigurationError::new(format!(
            "{ENV_LARCH_LOGS_URI} is no longer supported; remove it and use \
             {ENV_LARCH_STORAGE_BASE_URI} for a base-only override"
        )));
    }

    let raw_data = load_repository_config(repo_root)?;
    let repo_label = repository_label(repo_root);
    // `disabled_reason` is only observed when `configured_base` stays `None`;
    // the placeholder in the "table found, string present" arm mirrors the
    // unused Python assignment in the same branch.
    let (configured_base, disabled_reason) = match raw_data {
        None => (None, RunLogStorageReason::ConfigFileMissing),
        Some(raw) => match raw.get(LARCH_TOOL_NAME) {
            None => (None, RunLogStorageReason::LarchTableMissing),
            Some(toml::Value::Table(larch_table)) => {
                let has_unknown_keys = larch_table
                    .keys()
                    .any(|key| key.as_str() != STORAGE_BASE_URI_FIELD);
                if has_unknown_keys {
                    return Err(StorageConfigurationError::new(format!(
                        "{STORAGE_CONFIG_RELPATH}: [larch] must contain only \
                         {STORAGE_BASE_URI_FIELD}"
                    )));
                }
                match larch_table.get(STORAGE_BASE_URI_FIELD) {
                    None => (None, RunLogStorageReason::StorageBaseUriOmitted),
                    Some(toml::Value::String(configured)) => (
                        Some(parse_storage_base_uri(configured)?),
                        RunLogStorageReason::StorageBaseUriOmitted,
                    ),
                    Some(_) => {
                        return Err(StorageConfigurationError::new(format!(
                            "{STORAGE_CONFIG_RELPATH}: [larch].{STORAGE_BASE_URI_FIELD} must be \
                             a string"
                        )));
                    }
                }
            }
            Some(_) => {
                return Err(StorageConfigurationError::new(format!(
                    "{STORAGE_CONFIG_RELPATH}: [larch] must be a table in Git repository \
                     {repo_label}"
                )));
            }
        },
    };

    if let Some(override_value) = environ
        .get(ENV_LARCH_STORAGE_BASE_URI)
        .filter(|value| !value.is_empty())
    {
        return Ok((
            Some(parse_storage_base_uri(override_value)?),
            RunLogStorageReason::EnvironmentOverride,
        ));
    }
    if let Some(base) = configured_base {
        return Ok((Some(base), RunLogStorageReason::RepositoryConfig));
    }
    Ok((None, disabled_reason))
}

/// Bind disabled staging to one validated absolute repository root.
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when `repo_root` is not absolute,
/// cannot be resolved, or does not name a directory.
pub fn local_namespace_id(repo_root: &Path) -> Result<String, StorageConfigurationError> {
    if !repo_root.is_absolute() {
        return Err(StorageConfigurationError::new(
            "repository root must be absolute before resolving run-log storage",
        ));
    }
    let resolved = fs::canonicalize(repo_root).map_err(|_| {
        StorageConfigurationError::new(
            "repository root could not be resolved before run-log staging",
        )
    })?;
    if !resolved.is_dir() {
        return Err(StorageConfigurationError::new(
            "repository root must be a directory before run-log staging",
        ));
    }
    let mut hasher = Sha256::new();
    hasher.update(LOCAL_NAMESPACE_DOMAIN);
    hasher.update(resolved.as_os_str().as_encoded_bytes());
    Ok(hex_lower(&hasher.finalize()))
}

/// Resolve publication once while preserving strict present-config validation.
///
/// `origin_url` is the caller-supplied local `remote.origin.url` (Git
/// identity discovery is an adapter concern, not this crate's).
///
/// # Errors
///
/// Returns [`StorageConfigurationError`] when the repository configuration
/// is present but invalid, the legacy `LARCH_LOGS_URI` override is set, or
/// `origin_url` does not yield a valid client-repository slug.
#[allow(clippy::implicit_hasher)] // Caller-supplied environment snapshots always use the default hasher.
pub fn resolve_run_log_storage(
    repo_root: &Path,
    environ: &HashMap<String, String>,
    origin_url: &str,
) -> Result<RunLogStorageResolution, StorageConfigurationError> {
    let (base, reason) = configured_storage_base(repo_root, environ)?;
    let client_repo = repository_leaf_from_remote(origin_url)?;
    match base {
        None => RunLogStorageResolution::new(
            RunLogStorageMode::Disabled,
            reason,
            None,
            client_repo,
            Some(local_namespace_id(repo_root)?),
        ),
        Some(base) => {
            let storage = ToolRepositoryStorage::new(base, client_repo.clone());
            RunLogStorageResolution::new(
                RunLogStorageMode::Enabled,
                reason,
                Some(storage),
                client_repo,
                None,
            )
        }
    }
}

/// Render the exact `KEY=value` success envelope emitted by the Python
/// `storage_preflight_main` on success (adapters own the preflight call
/// itself; this only formats the already-resolved outcome).
#[must_use]
pub fn format_preflight_stdout(resolution: &RunLogStorageResolution) -> String {
    let storage = resolution.storage();
    let mut output = String::new();
    let _ = writeln!(output, "RUN_LOG_STORAGE={}", resolution.mode());
    let _ = writeln!(output, "RUN_LOG_STORAGE_REASON={}", resolution.reason());
    let _ = writeln!(
        output,
        "STORAGE_BASE_URI={}",
        storage
            .map(|repository| repository.base.uri())
            .unwrap_or_default()
    );
    let _ = writeln!(output, "CLIENT_REPO={}", resolution.client_repo());
    let _ = writeln!(
        output,
        "TOOL_REPO_URI={}",
        storage.map(ToolRepositoryStorage::uri).unwrap_or_default()
    );
    let _ = writeln!(
        output,
        "RUN_LOGS_URI={}",
        storage
            .map(ToolRepositoryStorage::run_logs_uri)
            .unwrap_or_default()
    );
    let _ = writeln!(
        output,
        "STORAGE_PREFLIGHT={}",
        if storage.is_some() {
            "ok"
        } else {
            "skipped-disabled"
        }
    );
    output.push_str("PREFLIGHT_OK=true\n");
    output
}

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::{
        RunLogStorageMode, RunLogStorageReason, StorageBase, ToolRepositoryStorage,
        format_preflight_stdout, injected_storage_resolution, parse_storage_base_uri,
        repository_leaf_from_remote, resolve_run_log_storage, validate_client_repo,
    };
    use std::collections::HashMap;
    use tempfile::tempdir;

    fn write_config(repo_root: &std::path::Path, contents: &str) {
        std::fs::write(repo_root.join("tools-config.toml"), contents)
            .expect("write fixture config");
    }

    #[test]
    fn storage_base_uri_parses_scheme_bucket_and_prefix() {
        let cases = [
            ("s3://zhupanov", "s3", "zhupanov", ""),
            (
                "s3://company-data/prod/tools",
                "s3",
                "company-data",
                "prod/tools",
            ),
            ("gs://character-tool-logs", "gs", "character-tool-logs", ""),
            ("r2://archive-bucket/base", "r2", "archive-bucket", "base"),
        ];
        for (uri, scheme, bucket, prefix) in cases {
            let base = parse_storage_base_uri(uri).unwrap_or_else(|error| panic!("{uri}: {error}"));
            assert_eq!(base.scheme, scheme, "{uri}");
            assert_eq!(base.bucket, bucket, "{uri}");
            assert_eq!(base.prefix, prefix, "{uri}");
            assert_eq!(base.uri(), uri, "{uri}");
        }
    }

    #[test]
    fn storage_base_uri_rejects_unsafe_shapes() {
        let cases = [
            ("https://bucket", "must use one of"),
            ("S3://bucket", "must use one of"),
            ("s3://key:secret@bucket", "must not contain credentials"),
            ("s3://bucket:443", "without a port"),
            ("s3://bucket/a/../prefix", "must not contain empty"),
            ("s3://bucket/a//prefix", "must not contain empty"),
            ("s3://bucket/prefix/", "trailing slash"),
            ("s3://bucket/prefix?query=1", "query or fragment"),
            ("s3://bucket/prefix#fragment", "query or fragment"),
            (r"s3://bucket\\other/prefix", "plain bucket name"),
            (
                r"s3://bucket/base\\prefix",
                "whitespace or control characters",
            ),
            (" s3://bucket", "surrounding whitespace"),
            ("", "surrounding whitespace"),
        ];
        for (uri, expected_substring) in cases {
            let error = parse_storage_base_uri(uri).expect_err(uri);
            assert!(
                error.to_string().contains(expected_substring),
                "{uri}: {error}"
            );
        }
    }

    #[test]
    fn tool_repository_storage_derives_uri_and_run_logs_uri() {
        let storage = ToolRepositoryStorage::new(
            StorageBase::with_prefix("s3", "company-data", "prod/tools"),
            "service-a",
        );
        assert_eq!(
            storage.uri(),
            "s3://company-data/prod/tools/larch/service-a"
        );
        assert_eq!(
            storage.run_logs_uri(),
            "s3://company-data/prod/tools/larch/service-a/run-logs/"
        );
        assert_eq!(storage.storage_origin_id().len(), 64);
    }

    #[test]
    fn git_origin_derivation_supports_standard_syntax() {
        let cases = [
            (
                "https://github.com/character-ai/Agent-Lint.git",
                "agent-lint",
            ),
            ("ssh://git@github.com/character-ai/larch.git", "larch"),
            ("git@github.com:character-ai/larch.git", "larch"),
            ("github.com:character-ai/service_a", "service_a"),
        ];
        for (origin, expected) in cases {
            assert_eq!(
                repository_leaf_from_remote(origin)
                    .unwrap_or_else(|error| panic!("{origin}: {error}")),
                expected,
                "{origin}"
            );
        }
    }

    #[test]
    fn git_origin_derivation_rejects_unsafe_or_ambiguous_values_without_leaking_secrets() {
        let cases = [
            "https://user:secret@example.com/org/repo.git",
            "https://example.com:443/org/repo.git",
            "ssh://example.com:notaport/org/repo.git",
            "file:///tmp/repo.git",
            "git@github.com:org/../repo.git",
            "git@github.com:org/-repo.git",
            "git@github.com:org/repo-.git",
            "ambiguous",
            "",
        ];
        for origin in cases {
            let error = repository_leaf_from_remote(origin).expect_err(origin);
            assert!(!error.to_string().contains("secret"), "{origin}: {error}");
        }
    }

    #[test]
    fn client_repo_validation_requires_lowercase_closed_slug() {
        assert_eq!(validate_client_repo("larch").unwrap(), "larch");
        for rejected in ["Larch", "-larch", "larch-", "", ".", ".."] {
            assert!(validate_client_repo(rejected).is_err(), "{rejected}");
        }
    }

    #[test]
    fn optional_configuration_has_distinct_disabled_reasons() {
        let cases: [(Option<&str>, RunLogStorageReason); 3] = [
            (None, RunLogStorageReason::ConfigFileMissing),
            (
                Some("[sre]\nvalue = 1\n"),
                RunLogStorageReason::LarchTableMissing,
            ),
            (
                Some("[larch]\n"),
                RunLogStorageReason::StorageBaseUriOmitted,
            ),
        ];
        for (config_text, expected_reason) in cases {
            let dir = tempdir().expect("tempdir");
            if let Some(text) = config_text {
                write_config(dir.path(), text);
            }
            let resolution =
                resolve_run_log_storage(dir.path(), &HashMap::new(), "git@github.com:org/repo.git")
                    .unwrap_or_else(|error| panic!("{error}"));
            assert_eq!(resolution.mode(), RunLogStorageMode::Disabled);
            assert_eq!(resolution.reason(), expected_reason);
            assert!(resolution.storage().is_none());
            assert_eq!(
                resolution.local_namespace_id().expect("namespace").len(),
                64
            );
        }
    }

    #[test]
    fn present_invalid_value_and_legacy_override_fail_closed() {
        for configured in ["", " ", "https://bucket"] {
            let dir = tempdir().expect("tempdir");
            write_config(
                dir.path(),
                &format!("[larch]\nstorage_base_uri = \"{configured}\"\n"),
            );
            assert!(
                resolve_run_log_storage(dir.path(), &HashMap::new(), "git@github.com:org/repo.git")
                    .is_err(),
                "{configured:?}"
            );
        }
        let dir = tempdir().expect("tempdir");
        write_config(dir.path(), "[larch\n");
        let mut environ = HashMap::new();
        environ.insert(
            super::ENV_LARCH_STORAGE_BASE_URI.to_string(),
            "s3://override".to_string(),
        );
        let error = resolve_run_log_storage(dir.path(), &environ, "git@github.com:org/repo.git")
            .expect_err("malformed TOML must not be masked");
        assert!(error.to_string().contains("malformed TOML"));

        let dir = tempdir().expect("tempdir");
        write_config(
            dir.path(),
            "[larch]\nstorage_base_uri = \"s3://zhupanov\"\n",
        );
        let mut environ = HashMap::new();
        environ.insert(
            super::ENV_LARCH_LOGS_URI.to_string(),
            "s3://old/root".to_string(),
        );
        let error = resolve_run_log_storage(dir.path(), &environ, "git@github.com:org/repo.git")
            .expect_err("legacy override must be rejected");
        assert!(error.to_string().contains("LARCH_LOGS_URI"));
    }

    #[test]
    fn non_regular_or_symlinked_config_is_rejected() {
        let dir = tempdir().expect("tempdir");
        std::fs::create_dir(dir.path().join("tools-config.toml")).expect("mkdir");
        let error =
            resolve_run_log_storage(dir.path(), &HashMap::new(), "git@github.com:org/repo.git")
                .expect_err("directory must be refused");
        assert!(error.to_string().contains("regular file"));

        #[cfg(unix)]
        {
            let dir = tempdir().expect("tempdir");
            let target = dir.path().join("actual.toml");
            std::fs::write(&target, "[larch]\nstorage_base_uri = \"s3://bucket\"\n")
                .expect("write symlink target");
            std::os::unix::fs::symlink(&target, dir.path().join("tools-config.toml"))
                .expect("create symlink");
            let error =
                resolve_run_log_storage(dir.path(), &HashMap::new(), "git@github.com:org/repo.git")
                    .expect_err("symlink must be refused");
            assert!(error.to_string().contains("refusing symlink"));
        }
    }

    #[test]
    fn preflight_envelope_matches_enabled_and_disabled_contracts() {
        let storage = ToolRepositoryStorage::new(
            StorageBase::with_prefix("s3", "company-data", "prod/tools"),
            "service-a",
        );
        let enabled = injected_storage_resolution(storage);
        assert_eq!(
            format_preflight_stdout(&enabled),
            "RUN_LOG_STORAGE=enabled\n\
             RUN_LOG_STORAGE_REASON=injected-storage\n\
             STORAGE_BASE_URI=s3://company-data/prod/tools\n\
             CLIENT_REPO=service-a\n\
             TOOL_REPO_URI=s3://company-data/prod/tools/larch/service-a\n\
             RUN_LOGS_URI=s3://company-data/prod/tools/larch/service-a/run-logs/\n\
             STORAGE_PREFLIGHT=ok\n\
             PREFLIGHT_OK=true\n"
        );

        let disabled = super::RunLogStorageResolution::new(
            RunLogStorageMode::Disabled,
            RunLogStorageReason::ConfigFileMissing,
            None,
            "service-a",
            Some("a".repeat(64)),
        )
        .expect("disabled resolution is consistent");
        assert_eq!(
            format_preflight_stdout(&disabled),
            "RUN_LOG_STORAGE=disabled\n\
             RUN_LOG_STORAGE_REASON=config-file-missing\n\
             STORAGE_BASE_URI=\n\
             CLIENT_REPO=service-a\n\
             TOOL_REPO_URI=\n\
             RUN_LOGS_URI=\n\
             STORAGE_PREFLIGHT=skipped-disabled\n\
             PREFLIGHT_OK=true\n"
        );
    }
}
