//! Stage and verify merge-group artifacts for trusted main cache publication.

use regex::Regex;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::LazyLock,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

#[cfg(unix)]
use std::os::unix::fs::{MetadataExt, OpenOptionsExt, PermissionsExt};

static CACHE_CLASS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[a-z][a-z0-9-]{0,63}$").expect("cache class regex"));
static CACHE_KEY_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,511}$").expect("cache key regex"));
static ARTIFACT_NAME_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^main-cache-[a-z][a-z0-9-]{0,63}-candidate$").expect("artifact name regex")
});
static PRODUCER_REF_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^refs/heads/gh-readonly-queue/main/[A-Za-z0-9._/-]+$").expect("producer ref regex")
});
static SHA256_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[0-9a-f]{64}$").expect("sha256 regex"));
static SOURCE_NAME_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$").expect("source name regex"));
static SOURCE_SHA_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$").expect("source sha regex"));

const MANIFEST_FILENAME: &str = "manifest.json";
const PAYLOAD_DIRECTORY: &str = "payload";
const SCHEMA_VERSION: u64 = 2;
const HASH_CHUNK_BYTES: usize = 1024 * 1024;
const MAX_MANIFEST_BYTES: u64 = 32 * 1024 * 1024;
const MAX_FILE_MODE: u32 = 0o777;
const MAX_MTIME_NS: i64 = i64::MAX;

/// A cache-publication candidate does not meet its integrity contract.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateError {
    message: String,
}

impl CandidateError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl std::fmt::Display for CandidateError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for CandidateError {}

/// One named regular file or directory included in a candidate payload.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateSource {
    pub name: String,
    pub path: PathBuf,
}

/// A content-addressed regular file inside a staged payload.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateMember {
    pub mode: u32,
    pub mtime_ns: i64,
    pub path: String,
    pub sha256: String,
    pub size: u64,
}

/// Inputs that bind a staged artifact to one cache class and producer.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateRequest {
    pub artifact_name: String,
    pub cache_class: String,
    pub cache_key: String,
    pub candidate_dir: PathBuf,
    pub maximum_bytes: u64,
    pub producer_event: String,
    pub producer_job: String,
    pub producer_ref: String,
    pub source_sha: String,
    pub sources: Vec<CandidateSource>,
    pub tool_versions: BTreeMap<String, String>,
}

/// The publisher's exact identity and tool-version contract for a candidate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateContract {
    pub artifact_name: String,
    pub cache_class: String,
    pub cache_key: String,
    pub maximum_bytes: u64,
    pub producer_job: String,
    pub source_sha: String,
    pub expected_tool_versions: BTreeMap<String, String>,
}

/// Metadata proven before a publisher may save the payload to a cache.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedCandidate {
    pub artifact_name: String,
    pub artifact_sha256: String,
    pub cache_class: String,
    pub cache_key: String,
    pub key_input_digest: String,
    pub members: Vec<CandidateMember>,
    pub maximum_bytes: u64,
    pub producer_event: String,
    pub producer_job: String,
    pub producer_ref: String,
    pub source_sha: String,
    pub total_bytes: u64,
    pub tool_versions: BTreeMap<String, String>,
}

/// Copy and manifest a regular-file candidate without granting save authority.
///
/// # Errors
///
/// Returns [`CandidateError`] when the request is invalid or staging fails.
pub fn stage_candidate(request: &CandidateRequest) -> Result<VerifiedCandidate, CandidateError> {
    validate_stage_request(request)?;
    let tool_versions = validated_tool_versions(
        &Value::Object(map_from_versions(&request.tool_versions)),
        "candidate tool versions",
    )?;
    create_empty_directory(&request.candidate_dir, "candidate directory")?;
    let payload = request.candidate_dir.join(PAYLOAD_DIRECTORY);
    create_empty_directory(&payload, "candidate payload")?;
    for source in &request.sources {
        copy_source(
            &source.path,
            &payload.join(&source.name),
            &format!("candidate source {}", source.name),
        )?;
    }

    let members = collect_members(&payload)?;
    let total_bytes = members.iter().map(|member| member.size).sum::<u64>();
    if request.maximum_bytes > 0 && total_bytes > request.maximum_bytes {
        return Err(CandidateError::new(format!(
            "candidate exceeds its maximum size: {total_bytes} > {}",
            request.maximum_bytes
        )));
    }

    let mut manifest = BTreeMap::new();
    manifest.insert(
        "artifact_name".to_owned(),
        Value::String(request.artifact_name.clone()),
    );
    manifest.insert(
        "artifact_sha256".to_owned(),
        Value::String(artifact_sha256(&members)),
    );
    manifest.insert(
        "cache_class".to_owned(),
        Value::String(request.cache_class.clone()),
    );
    manifest.insert(
        "cache_key".to_owned(),
        Value::String(request.cache_key.clone()),
    );
    manifest.insert(
        "key_input_digest".to_owned(),
        Value::String(sha256_text(&request.cache_key)),
    );
    manifest.insert(
        "maximum_bytes".to_owned(),
        Value::Number(request.maximum_bytes.into()),
    );
    manifest.insert(
        "members".to_owned(),
        Value::Array(members.iter().map(member_json).collect()),
    );
    manifest.insert(
        "producer_event".to_owned(),
        Value::String(request.producer_event.clone()),
    );
    manifest.insert(
        "producer_job".to_owned(),
        Value::String(request.producer_job.clone()),
    );
    manifest.insert(
        "producer_ref".to_owned(),
        Value::String(request.producer_ref.clone()),
    );
    manifest.insert(
        "schema_version".to_owned(),
        Value::Number(SCHEMA_VERSION.into()),
    );
    manifest.insert(
        "source_sha".to_owned(),
        Value::String(request.source_sha.clone()),
    );
    manifest.insert("total_bytes".to_owned(), Value::Number(total_bytes.into()));
    manifest.insert(
        "tool_versions".to_owned(),
        Value::Object(map_from_versions(&tool_versions)),
    );
    write_manifest(
        &request.candidate_dir.join(MANIFEST_FILENAME),
        &manifest.into_iter().collect(),
    )?;
    verify_candidate(
        &request.candidate_dir,
        &CandidateContract {
            artifact_name: request.artifact_name.clone(),
            cache_class: request.cache_class.clone(),
            cache_key: request.cache_key.clone(),
            maximum_bytes: request.maximum_bytes,
            producer_job: request.producer_job.clone(),
            source_sha: request.source_sha.clone(),
            expected_tool_versions: tool_versions,
        },
    )
}

/// Verify an untrusted merge-group artifact before it reaches a cache.
///
/// # Errors
///
/// Returns [`CandidateError`] when the candidate fails its integrity contract.
pub fn verify_candidate(
    candidate_dir: &Path,
    contract: &CandidateContract,
) -> Result<VerifiedCandidate, CandidateError> {
    let expected_versions = validate_contract(contract)?;
    require_regular_directory(candidate_dir, "candidate directory")?;
    verify_candidate_root(candidate_dir)?;
    let manifest = read_manifest(&candidate_dir.join(MANIFEST_FILENAME))?;
    require_manifest_shape(&manifest)?;
    let verified = parse_verified_manifest(&manifest)?;
    require_manifest_contract(&verified, contract, &expected_versions)?;
    let actual_members = collect_members(&candidate_dir.join(PAYLOAD_DIRECTORY))?;
    if !members_match_content(&actual_members, &verified.members) {
        return Err(CandidateError::new(
            "candidate payload members do not match its manifest",
        ));
    }
    let total_bytes = verified
        .members
        .iter()
        .map(|member| member.size)
        .sum::<u64>();
    if total_bytes != verified.total_bytes {
        return Err(CandidateError::new(
            "candidate payload size does not match its manifest",
        ));
    }
    if contract.maximum_bytes > 0 && total_bytes > contract.maximum_bytes {
        return Err(CandidateError::new(
            "candidate payload exceeds its size bound",
        ));
    }
    Ok(verified)
}

/// Validate an artifact, then copy its payload to a new publication directory.
///
/// # Errors
///
/// Returns [`CandidateError`] when verification or promotion fails.
pub fn promote_candidate(
    candidate_dir: &Path,
    output_dir: &Path,
    contract: &CandidateContract,
) -> Result<VerifiedCandidate, CandidateError> {
    let verified = verify_candidate(candidate_dir, contract)?;
    create_empty_directory(output_dir, "publication directory")?;
    copy_payload_contents(&candidate_dir.join(PAYLOAD_DIRECTORY), output_dir)?;
    reject_tree_symlinks(output_dir)?;
    restore_member_metadata(output_dir, &verified.members)?;
    reject_tree_symlinks(output_dir)?;
    Ok(verified)
}

/// Parse a `NAME=PATH` candidate source argument.
///
/// # Errors
///
/// Returns [`CandidateError`] when the grammar or name is invalid.
pub fn parse_source(arg: &str) -> Result<CandidateSource, CandidateError> {
    let Some((name, raw_path)) = arg.split_once('=') else {
        return Err(CandidateError::new("candidate source must use NAME=PATH"));
    };
    if raw_path.is_empty() {
        return Err(CandidateError::new("candidate source must use NAME=PATH"));
    }
    if !SOURCE_NAME_RE.is_match(name) {
        return Err(CandidateError::new("candidate source name is invalid"));
    }
    Ok(CandidateSource {
        name: name.to_owned(),
        path: PathBuf::from(raw_path),
    })
}

/// Parse a non-negative decimal maximum-bytes argument.
///
/// # Errors
///
/// Returns [`CandidateError`] when the value is not a non-negative integer.
pub fn parse_maximum_bytes(value: &str) -> Result<u64, CandidateError> {
    if !value.chars().all(|ch| ch.is_ascii_digit()) {
        return Err(CandidateError::new("maximum bytes is invalid"));
    }
    value
        .parse::<u64>()
        .map_err(|_| CandidateError::new("maximum bytes is invalid"))
}

/// Parse repeated `NAME=VALUE` tool-version arguments into a sorted map.
///
/// # Errors
///
/// Returns [`CandidateError`] when any entry is malformed or duplicated.
pub fn parse_tool_versions(tokens: &[String]) -> Result<BTreeMap<String, String>, CandidateError> {
    let mut tool_versions = BTreeMap::new();
    for token in tokens {
        let Some((name, version)) = token.split_once('=') else {
            return Err(CandidateError::new(
                "candidate tool version must use NAME=VALUE",
            ));
        };
        if !SOURCE_NAME_RE.is_match(name) || version.is_empty() {
            return Err(CandidateError::new(
                "candidate tool version must use NAME=VALUE",
            ));
        }
        if version.contains('\n') || version.contains('\r') {
            return Err(CandidateError::new("candidate tool version is invalid"));
        }
        if tool_versions.contains_key(name) {
            return Err(CandidateError::new(
                "candidate tool version names must be unique",
            ));
        }
        tool_versions.insert(name.to_owned(), version.to_owned());
    }
    Ok(tool_versions)
}

fn validate_stage_request(request: &CandidateRequest) -> Result<(), CandidateError> {
    require_artifact_name(&request.artifact_name)?;
    require_cache_class(&request.cache_class)?;
    require_cache_key(&request.cache_key)?;
    require_producer_job(&request.producer_job)?;
    require_source_sha(&request.source_sha)?;
    if request.producer_event != "merge_group" {
        return Err(CandidateError::new(
            "candidate producer event must be merge_group",
        ));
    }
    if !PRODUCER_REF_RE.is_match(&request.producer_ref) {
        return Err(CandidateError::new(
            "candidate producer ref must be a merge-queue ref",
        ));
    }
    if request.sources.is_empty() {
        return Err(CandidateError::new("candidate has no payload sources"));
    }
    let mut names = request
        .sources
        .iter()
        .map(|source| source.name.as_str())
        .collect::<Vec<_>>();
    let before = names.len();
    names.sort_unstable();
    names.dedup();
    if names.len() != before {
        return Err(CandidateError::new("candidate source names must be unique"));
    }
    let _ = validated_tool_versions(
        &Value::Object(map_from_versions(&request.tool_versions)),
        "candidate tool versions",
    )?;
    Ok(())
}

fn validate_contract(
    contract: &CandidateContract,
) -> Result<BTreeMap<String, String>, CandidateError> {
    require_artifact_name(&contract.artifact_name)?;
    require_cache_class(&contract.cache_class)?;
    require_cache_key(&contract.cache_key)?;
    require_producer_job(&contract.producer_job)?;
    require_source_sha(&contract.source_sha)?;
    validated_tool_versions(
        &Value::Object(map_from_versions(&contract.expected_tool_versions)),
        "expected candidate tool versions",
    )
}

fn valid_member_path(path: &str) -> bool {
    let Some(rest) = path.strip_prefix("payload/") else {
        return false;
    };
    if rest.is_empty() {
        return false;
    }
    for component in rest.split('/') {
        if component.is_empty() || component == "." || component == ".." {
            return false;
        }
        if component.chars().any(|ch| {
            matches!(
                ch,
                '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|' | '\0'..='\x1f' | '\x7f'
            )
        }) {
            return false;
        }
    }
    true
}

fn require_artifact_name(value: &str) -> Result<(), CandidateError> {
    if ARTIFACT_NAME_RE.is_match(value) {
        Ok(())
    } else {
        Err(CandidateError::new("candidate artifact name is invalid"))
    }
}

fn require_cache_class(value: &str) -> Result<(), CandidateError> {
    if CACHE_CLASS_RE.is_match(value) {
        Ok(())
    } else {
        Err(CandidateError::new("cache class is invalid"))
    }
}

fn require_cache_key(value: &str) -> Result<(), CandidateError> {
    if CACHE_KEY_RE.is_match(value) {
        Ok(())
    } else {
        Err(CandidateError::new("cache key is invalid"))
    }
}

fn require_producer_job(value: &str) -> Result<(), CandidateError> {
    if value.is_empty() || value.contains('\n') || value.contains('\r') {
        Err(CandidateError::new("producer job is invalid"))
    } else {
        Ok(())
    }
}

fn require_source_sha(value: &str) -> Result<(), CandidateError> {
    if SOURCE_SHA_RE.is_match(value) {
        Ok(())
    } else {
        Err(CandidateError::new("source SHA is invalid"))
    }
}

fn require_sha256(value: &str, label: &str) -> Result<(), CandidateError> {
    if SHA256_RE.is_match(value) {
        Ok(())
    } else {
        Err(CandidateError::new(format!("{label} is invalid")))
    }
}

fn create_empty_directory(path: &Path, label: &str) -> Result<(), CandidateError> {
    let Some(parent) = path.parent() else {
        return Err(CandidateError::new(format!("could not create {label}")));
    };
    require_regular_directory(parent, &format!("{label} parent"))?;
    if path.exists() || path.is_symlink() {
        return Err(CandidateError::new(format!("{label} already exists")));
    }
    fs::create_dir(path).map_err(|_| CandidateError::new(format!("could not create {label}")))?;
    #[cfg(unix)]
    {
        let permissions = fs::Permissions::from_mode(0o755);
        fs::set_permissions(path, permissions)
            .map_err(|_| CandidateError::new(format!("could not create {label}")))?;
    }
    Ok(())
}

fn copy_source(source: &Path, destination: &Path, label: &str) -> Result<(), CandidateError> {
    let source_status = lstat(source, label)?;
    if source_status.file_type().is_symlink() {
        return Err(CandidateError::new(format!("{label} is a symlink")));
    }
    if source_status.is_file() {
        return copy_regular_file(source, destination, label);
    }
    if !source_status.is_dir() {
        return Err(CandidateError::new(format!(
            "{label} is not a regular file or directory"
        )));
    }
    copy_directory(source, destination, label)
}

fn copy_directory(source: &Path, destination: &Path, label: &str) -> Result<(), CandidateError> {
    let mode = {
        #[cfg(unix)]
        {
            lstat(source, label)?.mode() & 0o777
        }
        #[cfg(not(unix))]
        {
            let _ = label;
            0o755
        }
    };
    fs::create_dir(destination)
        .map_err(|_| CandidateError::new(format!("could not create {label} destination")))?;
    #[cfg(unix)]
    {
        fs::set_permissions(destination, fs::Permissions::from_mode(mode))
            .map_err(|_| CandidateError::new(format!("could not create {label} destination")))?;
    }
    #[cfg(not(unix))]
    let _ = mode;
    let mut children = fs::read_dir(source)
        .map_err(|_| CandidateError::new(format!("{label} is unavailable")))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| CandidateError::new(format!("{label} is unavailable")))?;
    children.sort_by_key(fs::DirEntry::file_name);
    for child in children {
        copy_source(&child.path(), &destination.join(child.file_name()), label)?;
    }
    Ok(())
}

fn copy_payload_contents(source: &Path, destination: &Path) -> Result<(), CandidateError> {
    require_regular_directory(source, "verified candidate payload")?;
    let mut children = fs::read_dir(source)
        .map_err(|_| CandidateError::new("verified candidate payload is unavailable"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| CandidateError::new("verified candidate payload is unavailable"))?;
    children.sort_by_key(fs::DirEntry::file_name);
    for child in children {
        copy_source(
            &child.path(),
            &destination.join(child.file_name()),
            "verified candidate payload",
        )?;
    }
    Ok(())
}

fn copy_regular_file(source: &Path, destination: &Path, label: &str) -> Result<(), CandidateError> {
    let status = lstat(source, label)?;
    if status.file_type().is_symlink() || !status.is_file() {
        return Err(CandidateError::new(format!(
            "{label} is not a regular file"
        )));
    }
    fs::copy(source, destination)
        .map_err(|_| CandidateError::new(format!("could not copy {label}")))?;
    Ok(())
}

fn collect_members(payload: &Path) -> Result<Vec<CandidateMember>, CandidateError> {
    require_regular_directory(payload, "candidate payload")?;
    reject_tree_symlinks(payload)?;
    let payload_parent = payload
        .parent()
        .ok_or_else(|| CandidateError::new("candidate payload is unavailable"))?;
    let mut members = Vec::new();
    for path in walk_regular_files(payload)? {
        let relative = path
            .strip_prefix(payload_parent)
            .map_err(|_| CandidateError::new("candidate payload path is invalid"))?
            .to_string_lossy()
            .replace('\\', "/");
        if !valid_member_path(&relative) {
            return Err(CandidateError::new("candidate payload path is invalid"));
        }
        let status = lstat(&path, "candidate payload member")?;
        let mtime_ns = validated_mtime_ns(mtime_ns_from_metadata(&status)?)?;
        members.push(CandidateMember {
            mode: file_mode(&status),
            mtime_ns,
            path: relative,
            sha256: sha256_file(&path)?,
            size: status.len(),
        });
    }
    members.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(members)
}

fn walk_regular_files(directory: &Path) -> Result<Vec<PathBuf>, CandidateError> {
    let mut files = Vec::new();
    let mut children = fs::read_dir(directory)
        .map_err(|_| CandidateError::new("candidate payload entry is unavailable"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| CandidateError::new("candidate payload entry is unavailable"))?;
    children.sort_by_key(fs::DirEntry::file_name);
    for child in children {
        let path = child.path();
        let status = lstat(&path, "candidate payload entry")?;
        if status.file_type().is_symlink() {
            return Err(CandidateError::new("candidate payload contains a symlink"));
        }
        if status.is_file() {
            files.push(path);
            continue;
        }
        if status.is_dir() {
            files.extend(walk_regular_files(&path)?);
            continue;
        }
        return Err(CandidateError::new(
            "candidate payload contains a non-regular entry",
        ));
    }
    Ok(files)
}

fn reject_tree_symlinks(directory: &Path) -> Result<(), CandidateError> {
    let _ = walk_regular_files(directory)?;
    Ok(())
}

fn verify_candidate_root(directory: &Path) -> Result<(), CandidateError> {
    reject_tree_symlinks(directory)?;
    let children = fs::read_dir(directory)
        .map_err(|_| CandidateError::new("candidate directory is unavailable"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| CandidateError::new("candidate directory is unavailable"))?;
    for child in children {
        let name = child.file_name();
        let name = name.to_string_lossy();
        if name == MANIFEST_FILENAME {
            let status = lstat(&child.path(), "candidate directory")?;
            if status.file_type().is_symlink() || !status.is_file() {
                return Err(CandidateError::new(
                    "candidate directory manifest is not a regular file",
                ));
            }
            continue;
        }
        if name == PAYLOAD_DIRECTORY {
            continue;
        }
        return Err(CandidateError::new(
            "candidate directory contains an unexpected entry",
        ));
    }
    Ok(())
}

fn write_manifest(path: &Path, manifest: &Map<String, Value>) -> Result<(), CandidateError> {
    let encoded = serde_json::to_string(&Value::Object(manifest.clone()))
        .map_err(|_| CandidateError::new("could not write candidate manifest"))?;
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    let mut file = options
        .open(path)
        .map_err(|_| CandidateError::new("could not write candidate manifest"))?;
    file.write_all(encoded.as_bytes())
        .and_then(|()| file.write_all(b"\n"))
        .map_err(|_| CandidateError::new("could not write candidate manifest"))
}

fn read_manifest(path: &Path) -> Result<Map<String, Value>, CandidateError> {
    let status = lstat(path, "candidate manifest")?;
    if status.file_type().is_symlink() || !status.is_file() {
        return Err(CandidateError::new(
            "candidate manifest is not a regular file",
        ));
    }
    if status.len() > MAX_MANIFEST_BYTES {
        return Err(CandidateError::new(
            "candidate manifest exceeds its size limit",
        ));
    }
    let raw = fs::read_to_string(path)
        .map_err(|_| CandidateError::new("candidate manifest is unreadable"))?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|_| CandidateError::new("candidate manifest is unreadable"))?;
    match parsed {
        Value::Object(map) => Ok(map),
        _ => Err(CandidateError::new("candidate manifest is not an object")),
    }
}

fn require_manifest_shape(manifest: &Map<String, Value>) -> Result<(), CandidateError> {
    let required = [
        "artifact_name",
        "artifact_sha256",
        "cache_class",
        "cache_key",
        "key_input_digest",
        "maximum_bytes",
        "members",
        "producer_event",
        "producer_job",
        "producer_ref",
        "schema_version",
        "source_sha",
        "total_bytes",
        "tool_versions",
    ];
    if manifest.len() != required.len() || required.iter().any(|key| !manifest.contains_key(*key)) {
        return Err(CandidateError::new(
            "candidate manifest has an unexpected schema",
        ));
    }
    match manifest.get("schema_version") {
        Some(Value::Number(number)) if number.as_u64() == Some(SCHEMA_VERSION) => {}
        _ => {
            return Err(CandidateError::new(
                "candidate manifest has an unsupported schema version",
            ));
        }
    }
    let _ = parse_manifest_tool_versions(manifest)?;
    Ok(())
}

fn require_manifest_string(
    manifest: &Map<String, Value>,
    key: &str,
) -> Result<String, CandidateError> {
    match manifest.get(key) {
        Some(Value::String(value)) => Ok(value.clone()),
        _ => Err(CandidateError::new(format!(
            "candidate manifest {key} is invalid"
        ))),
    }
}

fn require_manifest_u64(manifest: &Map<String, Value>, key: &str) -> Result<u64, CandidateError> {
    match manifest.get(key) {
        Some(Value::Number(number)) => number
            .as_u64()
            .ok_or_else(|| CandidateError::new(format!("candidate manifest {key} is invalid"))),
        _ => Err(CandidateError::new(format!(
            "candidate manifest {key} is invalid"
        ))),
    }
}

fn parse_verified_manifest(
    manifest: &Map<String, Value>,
) -> Result<VerifiedCandidate, CandidateError> {
    let artifact_name = require_manifest_string(manifest, "artifact_name")?;
    let artifact_digest = require_manifest_string(manifest, "artifact_sha256")?;
    let cache_class = require_manifest_string(manifest, "cache_class")?;
    let cache_key = require_manifest_string(manifest, "cache_key")?;
    let key_input_digest = require_manifest_string(manifest, "key_input_digest")?;
    let producer_event = require_manifest_string(manifest, "producer_event")?;
    let producer_job = require_manifest_string(manifest, "producer_job")?;
    let producer_ref = require_manifest_string(manifest, "producer_ref")?;
    let source_sha = require_manifest_string(manifest, "source_sha")?;
    let maximum_bytes = require_manifest_u64(manifest, "maximum_bytes")?;
    let total_bytes = require_manifest_u64(manifest, "total_bytes")?;
    require_artifact_name(&artifact_name)?;
    require_sha256(&artifact_digest, "candidate artifact digest")?;
    require_cache_class(&cache_class)?;
    require_cache_key(&cache_key)?;
    require_sha256(&key_input_digest, "candidate key-input digest")?;
    if key_input_digest != sha256_text(&cache_key) {
        return Err(CandidateError::new(
            "candidate cache key identity does not match",
        ));
    }
    require_source_sha(&source_sha)?;
    let members = parse_members(manifest)?;
    if artifact_sha256(&members) != artifact_digest {
        return Err(CandidateError::new(
            "candidate artifact digest does not match its manifest",
        ));
    }
    Ok(VerifiedCandidate {
        artifact_name,
        artifact_sha256: artifact_digest,
        cache_class,
        cache_key,
        key_input_digest,
        members,
        maximum_bytes,
        producer_event,
        producer_job,
        producer_ref,
        source_sha,
        total_bytes,
        tool_versions: parse_manifest_tool_versions(manifest)?,
    })
}

fn require_manifest_contract(
    verified: &VerifiedCandidate,
    contract: &CandidateContract,
    expected_versions: &BTreeMap<String, String>,
) -> Result<(), CandidateError> {
    if verified.artifact_name != contract.artifact_name {
        return Err(CandidateError::new(
            "candidate artifact name does not match",
        ));
    }
    if verified.cache_class != contract.cache_class {
        return Err(CandidateError::new(
            "candidate cache class does not match the requested cache class",
        ));
    }
    if verified.cache_key != contract.cache_key {
        return Err(CandidateError::new(
            "candidate cache key identity does not match",
        ));
    }
    if verified.producer_event != "merge_group" {
        return Err(CandidateError::new(
            "candidate producer event is not merge_group",
        ));
    }
    if verified.producer_job != contract.producer_job {
        return Err(CandidateError::new("candidate producer job does not match"));
    }
    if !PRODUCER_REF_RE.is_match(&verified.producer_ref) {
        return Err(CandidateError::new(
            "candidate producer ref is not a merge-queue ref",
        ));
    }
    if verified.source_sha != contract.source_sha {
        return Err(CandidateError::new(
            "candidate source SHA does not match the publisher SHA",
        ));
    }
    if verified.maximum_bytes != contract.maximum_bytes {
        return Err(CandidateError::new(
            "candidate size bound does not match the publisher contract",
        ));
    }
    if &verified.tool_versions != expected_versions {
        return Err(CandidateError::new(
            "candidate tool versions do not match the publisher contract",
        ));
    }
    Ok(())
}

fn parse_members(manifest: &Map<String, Value>) -> Result<Vec<CandidateMember>, CandidateError> {
    let Some(Value::Array(raw_members)) = manifest.get("members") else {
        return Err(CandidateError::new(
            "candidate manifest members are invalid",
        ));
    };
    if raw_members.is_empty() {
        return Err(CandidateError::new(
            "candidate manifest members are invalid",
        ));
    }
    let mut members = Vec::new();
    for raw_member_value in raw_members {
        let Value::Object(raw_member) = raw_member_value else {
            return Err(CandidateError::new(
                "candidate manifest member has an unexpected schema",
            ));
        };
        let expected = ["mode", "mtime_ns", "path", "sha256", "size"];
        if raw_member.len() != expected.len()
            || expected.iter().any(|key| !raw_member.contains_key(*key))
        {
            return Err(CandidateError::new(
                "candidate manifest member has an unexpected schema",
            ));
        }
        let mode = match raw_member.get("mode") {
            Some(Value::Number(number)) => number
                .as_u64()
                .filter(|value| *value <= u64::from(MAX_FILE_MODE))
                .and_then(|value| u32::try_from(value).ok()),
            _ => None,
        }
        .ok_or_else(|| CandidateError::new("candidate manifest member mode is invalid"))?;
        let path = match raw_member.get("path") {
            Some(Value::String(value)) if valid_member_path(value) => value.clone(),
            _ => {
                return Err(CandidateError::new(
                    "candidate manifest member path is invalid",
                ));
            }
        };
        let sha256 = match raw_member.get("sha256") {
            Some(Value::String(value)) => value.clone(),
            _ => {
                return Err(CandidateError::new(
                    "candidate manifest member checksum is invalid",
                ));
            }
        };
        require_sha256(&sha256, "candidate member checksum")?;
        let size = match raw_member.get("size") {
            Some(Value::Number(number)) => number.as_u64(),
            _ => None,
        }
        .ok_or_else(|| CandidateError::new("candidate manifest member size is invalid"))?;
        let mtime_ns = match raw_member.get("mtime_ns") {
            Some(Value::Number(number)) => number.as_i64().ok_or_else(|| {
                CandidateError::new("candidate manifest member mtime_ns is invalid")
            }),
            _ => Err(CandidateError::new(
                "candidate manifest member mtime_ns is invalid",
            )),
        }?;
        members.push(CandidateMember {
            mode,
            mtime_ns: validated_mtime_ns(mtime_ns)?,
            path,
            sha256,
            size,
        });
    }
    let paths = members
        .iter()
        .map(|member| member.path.as_str())
        .collect::<Vec<_>>();
    let mut sorted = paths.clone();
    sorted.sort_unstable();
    let mut unique = sorted.clone();
    unique.dedup();
    if paths != sorted || unique.len() != paths.len() {
        return Err(CandidateError::new(
            "candidate manifest member paths are not unique and sorted",
        ));
    }
    Ok(members)
}

fn members_match_content(actual: &[CandidateMember], expected: &[CandidateMember]) -> bool {
    actual
        .iter()
        .map(|member| (&member.path, &member.sha256, member.size))
        .eq(expected
            .iter()
            .map(|member| (&member.path, &member.sha256, member.size)))
}

fn validated_mtime_ns(value: i64) -> Result<i64, CandidateError> {
    if (0..=MAX_MTIME_NS).contains(&value) {
        Ok(value)
    } else {
        Err(CandidateError::new(
            "candidate manifest member mtime_ns is invalid",
        ))
    }
}

fn restore_member_metadata(
    output_dir: &Path,
    members: &[CandidateMember],
) -> Result<(), CandidateError> {
    for member in members {
        let relative = Path::new(&member.path)
            .strip_prefix(PAYLOAD_DIRECTORY)
            .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        let path = output_dir.join(relative);
        let before = lstat(&path, "promoted candidate member")?;
        if before.file_type().is_symlink() || !before.is_file() {
            return Err(CandidateError::new(
                "promoted candidate member is not a regular file",
            ));
        }
        let before_identity = file_identity(&before);
        let mut options = OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            options.custom_flags(libc_o_nofollow());
        }
        let file = options
            .open(&path)
            .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        let opened = file
            .metadata()
            .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        let current = lstat(&path, "promoted candidate member")?;
        if !opened.is_file()
            || current.file_type().is_symlink()
            || !current.is_file()
            || file_identity(&opened) != before_identity
            || file_identity(&current) != file_identity(&opened)
        {
            return Err(CandidateError::new(
                "promoted candidate member changed while opening",
            ));
        }
        set_mode_and_mtime(&file, &path, member.mode, member.mtime_ns)?;
        let restored = file
            .metadata()
            .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        let visible = lstat(&path, "promoted candidate member")?;
        if file_mode(&restored) != member.mode
            || mtime_ns_from_metadata(&restored)? != member.mtime_ns
            || visible.file_type().is_symlink()
            || !visible.is_file()
            || file_identity(&visible) != file_identity(&restored)
            || file_mode(&visible) != member.mode
            || mtime_ns_from_metadata(&visible)? != member.mtime_ns
        {
            return Err(CandidateError::new(
                "candidate member metadata was not restored exactly",
            ));
        }
    }
    Ok(())
}

fn parse_manifest_tool_versions(
    manifest: &Map<String, Value>,
) -> Result<BTreeMap<String, String>, CandidateError> {
    let raw = manifest
        .get("tool_versions")
        .cloned()
        .unwrap_or(Value::Null);
    validated_tool_versions(&raw, "candidate manifest tool versions")
}

fn validated_tool_versions(
    raw_tool_versions: &Value,
    label: &str,
) -> Result<BTreeMap<String, String>, CandidateError> {
    let Value::Object(raw_versions) = raw_tool_versions else {
        return Err(CandidateError::new(format!("{label} are invalid")));
    };
    if raw_versions.is_empty() {
        return Err(CandidateError::new(format!("{label} are invalid")));
    }
    let mut tool_versions = BTreeMap::new();
    for (raw_name, raw_version) in raw_versions {
        if !SOURCE_NAME_RE.is_match(raw_name) {
            return Err(CandidateError::new(format!("{label} name is invalid")));
        }
        let Value::String(version) = raw_version else {
            return Err(CandidateError::new(format!("{label} value is invalid")));
        };
        if version.is_empty() || version.contains('\n') || version.contains('\r') {
            return Err(CandidateError::new(format!("{label} value is invalid")));
        }
        tool_versions.insert(raw_name.clone(), version.clone());
    }
    let keys = tool_versions.keys().cloned().collect::<Vec<_>>();
    let mut sorted = keys.clone();
    sorted.sort();
    if keys != sorted {
        return Err(CandidateError::new(format!("{label} are not sorted")));
    }
    Ok(tool_versions)
}

fn require_regular_directory(path: &Path, label: &str) -> Result<(), CandidateError> {
    let status = lstat(path, label)?;
    if status.file_type().is_symlink() || !status.is_dir() {
        return Err(CandidateError::new(format!(
            "{label} is not a regular directory"
        )));
    }
    Ok(())
}

fn lstat(path: &Path, label: &str) -> Result<fs::Metadata, CandidateError> {
    fs::symlink_metadata(path).map_err(|_| CandidateError::new(format!("{label} is unavailable")))
}

fn sha256_file(path: &Path) -> Result<String, CandidateError> {
    let mut file = File::open(path)
        .map_err(|_| CandidateError::new("candidate payload member is unreadable"))?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0_u8; HASH_CHUNK_BYTES];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|_| CandidateError::new("candidate payload member is unreadable"))?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn sha256_text(value: &str) -> String {
    format!("{:x}", Sha256::digest(value.as_bytes()))
}

fn member_json(member: &CandidateMember) -> Value {
    Value::Object(
        [
            ("mode", Value::Number(member.mode.into())),
            ("mtime_ns", Value::Number(member.mtime_ns.into())),
            ("path", Value::String(member.path.clone())),
            ("sha256", Value::String(member.sha256.clone())),
            ("size", Value::Number(member.size.into())),
        ]
        .into_iter()
        .map(|(key, value)| (key.to_owned(), value))
        .collect(),
    )
}

fn artifact_sha256(members: &[CandidateMember]) -> String {
    let payload = members.iter().map(member_json).collect::<Vec<_>>();
    let encoded = serde_json::to_string(&payload).expect("artifact digest payload serializes");
    sha256_text(&encoded)
}

fn map_from_versions(versions: &BTreeMap<String, String>) -> Map<String, Value> {
    versions
        .iter()
        .map(|(key, value)| (key.clone(), Value::String(value.clone())))
        .collect()
}

fn file_mode(metadata: &fs::Metadata) -> u32 {
    #[cfg(unix)]
    {
        metadata.mode() & 0o777
    }
    #[cfg(not(unix))]
    {
        if metadata.permissions().readonly() {
            0o444
        } else {
            0o644
        }
    }
}

fn mtime_ns_from_metadata(metadata: &fs::Metadata) -> Result<i64, CandidateError> {
    #[cfg(unix)]
    {
        let seconds = metadata.mtime();
        let nanos = metadata.mtime_nsec();
        seconds
            .checked_mul(1_000_000_000)
            .and_then(|value| value.checked_add(nanos))
            .ok_or_else(|| CandidateError::new("candidate manifest member mtime_ns is invalid"))
    }
    #[cfg(not(unix))]
    {
        let modified = metadata
            .modified()
            .map_err(|_| CandidateError::new("candidate manifest member mtime_ns is invalid"))?;
        let duration = modified
            .duration_since(UNIX_EPOCH)
            .map_err(|_| CandidateError::new("candidate manifest member mtime_ns is invalid"))?;
        i64::try_from(duration.as_nanos())
            .map_err(|_| CandidateError::new("candidate manifest member mtime_ns is invalid"))
    }
}

#[cfg(unix)]
fn file_identity(metadata: &fs::Metadata) -> (u64, u64) {
    (metadata.dev(), metadata.ino())
}

fn set_mode_and_mtime(
    file: &File,
    path: &Path,
    mode: u32,
    mtime_ns: i64,
) -> Result<(), CandidateError> {
    #[cfg(unix)]
    {
        let permissions = fs::Permissions::from_mode(mode);
        fs::set_permissions(path, permissions)
            .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        let seconds = mtime_ns / 1_000_000_000;
        let nanos = u32::try_from(mtime_ns % 1_000_000_000)
            .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        let modified = UNIX_EPOCH
            .checked_add(Duration::new(
                u64::try_from(seconds).map_err(|_| {
                    CandidateError::new("could not restore candidate member metadata")
                })?,
                nanos,
            ))
            .ok_or_else(|| CandidateError::new("could not restore candidate member metadata"))?;
        let atime = file
            .metadata()
            .and_then(|metadata| metadata.accessed())
            .unwrap_or_else(|_| SystemTime::now());
        file.set_times(
            fs::FileTimes::new()
                .set_accessed(atime)
                .set_modified(modified),
        )
        .map_err(|_| CandidateError::new("could not restore candidate member metadata"))?;
        Ok(())
    }
    #[cfg(not(unix))]
    {
        let _ = (file, path, mode, mtime_ns);
        Err(CandidateError::new(
            "could not restore candidate member metadata",
        ))
    }
}

#[cfg(unix)]
const fn libc_o_nofollow() -> i32 {
    libc::O_NOFOLLOW
}

#[cfg(unix)]
mod libc {
    pub use nix::libc::O_NOFOLLOW;
}

#[cfg(test)]
mod tests {
    use super::{
        CandidateContract, CandidateRequest, CandidateSource, MAX_MANIFEST_BYTES, SCHEMA_VERSION,
        parse_maximum_bytes, parse_source, parse_tool_versions, promote_candidate, read_manifest,
        stage_candidate, valid_member_path, verify_candidate,
    };
    use serde_json::{Map, Value};
    use std::{
        collections::BTreeMap,
        fs,
        path::{Path, PathBuf},
        time::{Duration, UNIX_EPOCH},
    };

    #[cfg(unix)]
    use std::os::unix::fs::{MetadataExt, PermissionsExt};

    const PRODUCER_REF: &str = "refs/heads/gh-readonly-queue/main/pr-8362-0123456789abcdef";
    const SOURCE_SHA: &str = "0123456789abcdef0123456789abcdef01234567";
    const SOURCE_MTIME_NS: i64 = 1_700_000_000_123_456_789;
    const TRANSPORT_MTIME_NS: i64 = 1_700_000_100_987_654_321;

    fn set_mtime(path: &Path, mtime_ns: i64) {
        let modified = UNIX_EPOCH
            + Duration::new(
                u64::try_from(mtime_ns / 1_000_000_000).expect("seconds"),
                u32::try_from(mtime_ns % 1_000_000_000).expect("nanos"),
            );
        fs::File::options()
            .write(true)
            .open(path)
            .expect("open")
            .set_times(fs::FileTimes::new().set_modified(modified))
            .expect("mtime");
    }

    fn make_request(root: &Path, dir: &str) -> CandidateRequest {
        let source = root.join("source");
        fs::create_dir_all(source.join(".fingerprint")).expect("tree");
        let dependency = source.join(".fingerprint/dependency.json");
        fs::write(&dependency, "dependency\n").expect("dep");
        set_mtime(&dependency, SOURCE_MTIME_NS);
        let executable = source.join("larch");
        fs::write(&executable, b"#!/bin/sh\nprintf larch\n").expect("exe");
        #[cfg(unix)]
        fs::set_permissions(&executable, fs::Permissions::from_mode(0o755)).expect("chmod");
        set_mtime(&executable, SOURCE_MTIME_NS + 1);
        CandidateRequest {
            artifact_name: "main-cache-coverage-target-candidate".into(),
            cache_class: "coverage-target".into(),
            cache_key: "coverage-target-deps-v2-Linux-X64-identity".into(),
            candidate_dir: root.join(dir),
            maximum_bytes: 1024 * 1024,
            producer_event: "merge_group".into(),
            producer_job: "rust-full".into(),
            producer_ref: PRODUCER_REF.into(),
            source_sha: SOURCE_SHA.into(),
            sources: vec![CandidateSource {
                name: "llvm-cov-target".into(),
                path: source,
            }],
            tool_versions: BTreeMap::from([
                ("cargo-llvm-cov".into(), "cargo-llvm-cov 0.8.7".into()),
                ("rustc".into(), "rustc test".into()),
            ]),
        }
    }

    fn contract(request: &CandidateRequest) -> CandidateContract {
        CandidateContract {
            artifact_name: request.artifact_name.clone(),
            cache_class: request.cache_class.clone(),
            cache_key: request.cache_key.clone(),
            maximum_bytes: request.maximum_bytes,
            producer_job: request.producer_job.clone(),
            source_sha: request.source_sha.clone(),
            expected_tool_versions: request.tool_versions.clone(),
        }
    }

    fn rewrite_manifest(candidate_dir: &Path, edit: impl FnOnce(&mut Map<String, Value>)) {
        let path = candidate_dir.join("manifest.json");
        let mut manifest = read_manifest(&path).expect("manifest");
        edit(&mut manifest);
        fs::write(&path, format!("{}\n", Value::Object(manifest))).expect("rewrite");
    }

    #[test]
    fn parsers_accept_valid_cli_shapes_and_reject_malformed_ones() {
        let source = parse_source("llvm-cov-target=/tmp/target").expect("source");
        assert_eq!(source.name, "llvm-cov-target");
        assert_eq!(source.path, PathBuf::from("/tmp/target"));
        assert!(parse_source("bad").is_err());
        assert!(parse_source("=missing-name").is_err());
        assert!(parse_source("bad name=/tmp").is_err());
        assert_eq!(parse_maximum_bytes("0").expect("zero"), 0);
        assert_eq!(parse_maximum_bytes("42").expect("bytes"), 42);
        assert!(parse_maximum_bytes("-1").is_err());
        assert!(parse_maximum_bytes("1a").is_err());
        let versions = parse_tool_versions(&[
            "rustc=rustc test".into(),
            "cargo-llvm-cov=cargo-llvm-cov 0.8.7".into(),
        ])
        .expect("versions");
        assert_eq!(versions.len(), 2);
        assert!(parse_tool_versions(&["rustc".into()]).is_err());
        assert!(parse_tool_versions(&["rustc=".into()]).is_err());
        assert!(parse_tool_versions(&["rustc=line\nbreak".into()]).is_err());
        assert!(parse_tool_versions(&["rustc=a".into(), "rustc=b".into()]).is_err());
        assert!(!valid_member_path("payload/../escape"));
        assert!(!valid_member_path("payload/registry/../../escape"));
        assert!(!valid_member_path("payload/registry/control\nname"));
        assert!(!valid_member_path(r"payload/registry\\escape"));
        assert!(valid_member_path(
            "payload/registry/cache/index.crates.io-1949cf8c6b5b557f/wasip2-1.0.4+wasi-0.2.12.crate"
        ));
    }

    #[test]
    fn stage_promote_restores_mtime_and_mode_after_transport_drift() {
        let root = tempfile::tempdir().expect("tempdir");
        let request = make_request(root.path(), "candidate");
        let staged = stage_candidate(&request).expect("stage");
        let verified =
            verify_candidate(&request.candidate_dir, &contract(&request)).expect("verify");
        assert_eq!(verified.total_bytes, staged.total_bytes);
        assert_eq!(staged.cache_class, "coverage-target");
        assert_eq!(staged.artifact_name, "main-cache-coverage-target-candidate");
        let manifest =
            read_manifest(&request.candidate_dir.join("manifest.json")).expect("manifest");
        assert_eq!(
            manifest.get("schema_version").and_then(Value::as_u64),
            Some(SCHEMA_VERSION)
        );
        assert_eq!(
            manifest.get("cache_key").and_then(Value::as_str),
            Some("coverage-target-deps-v2-Linux-X64-identity")
        );
        let dependency = request
            .candidate_dir
            .join("payload/llvm-cov-target/.fingerprint/dependency.json");
        let executable = request.candidate_dir.join("payload/llvm-cov-target/larch");
        let expected_mtime = staged
            .members
            .iter()
            .find(|member| member.path.ends_with("dependency.json"))
            .expect("dependency member")
            .mtime_ns;
        set_mtime(&dependency, TRANSPORT_MTIME_NS);
        set_mtime(&executable, TRANSPORT_MTIME_NS);
        #[cfg(unix)]
        fs::set_permissions(&executable, fs::Permissions::from_mode(0o644)).expect("chmod");
        let promoted = promote_candidate(
            &request.candidate_dir,
            &root.path().join("promoted"),
            &contract(&request),
        )
        .expect("promote");
        assert_eq!(promoted.total_bytes, staged.total_bytes);
        #[cfg(unix)]
        {
            let meta = root
                .path()
                .join("promoted/llvm-cov-target/.fingerprint/dependency.json")
                .metadata()
                .expect("meta");
            assert_eq!(
                meta.mtime() * 1_000_000_000 + meta.mtime_nsec(),
                expected_mtime
            );
            let exe = root
                .path()
                .join("promoted/llvm-cov-target/larch")
                .metadata()
                .expect("exe meta");
            assert_ne!(exe.mode() & 0o111, 0);
        }
    }

    #[test]
    fn cargo_inputs_accept_safe_path_punctuation_and_omit_empty_git_dir() {
        let root = tempfile::tempdir().expect("tempdir");
        let registry = root.path().join("registry");
        for relative in [
            "cache/index.crates.io-1949cf8c6b5b557f/wasip2-1.0.4+wasi-0.2.12.crate",
            "index/index.crates.io-1949cf8c6b5b557f/.cache/nu/-a/nu-ansi-term",
            "src/index.crates.io-1949cf8c6b5b557f/example-1.0.0/generated/_impls.rs",
            "src/index.crates.io-1949cf8c6b5b557f/example-1.0.0/Rust Project Developers (#) [@]~",
        ] {
            let path = registry.join(relative);
            fs::create_dir_all(path.parent().expect("parent")).expect("parents");
            fs::write(&path, "cache payload\n").expect("write");
        }
        let git = root.path().join("git");
        fs::create_dir_all(&git).expect("git");
        let request = CandidateRequest {
            artifact_name: "main-cache-cargo-inputs-candidate".into(),
            cache_class: "cargo-inputs".into(),
            cache_key: "cargo-inputs-v2-Linux-X64-identity".into(),
            candidate_dir: root.path().join("candidate"),
            maximum_bytes: 1024 * 1024,
            producer_event: "merge_group".into(),
            producer_job: "rust-lint".into(),
            producer_ref: PRODUCER_REF.into(),
            source_sha: SOURCE_SHA.into(),
            sources: vec![
                CandidateSource {
                    name: "registry".into(),
                    path: registry,
                },
                CandidateSource {
                    name: "git".into(),
                    path: git,
                },
            ],
            tool_versions: BTreeMap::from([
                ("cargo".into(), "cargo test".into()),
                ("rustc".into(), "rustc test".into()),
            ]),
        };
        stage_candidate(&request).expect("stage");
        fs::remove_dir(request.candidate_dir.join("payload/git")).expect("omit empty git");
        promote_candidate(
            &request.candidate_dir,
            &root.path().join("promoted"),
            &contract(&request),
        )
        .expect("promote");
        assert!(
            root.path()
                .join("promoted/registry/cache/index.crates.io-1949cf8c6b5b557f/wasip2-1.0.4+wasi-0.2.12.crate")
                .is_file()
        );
        assert!(!root.path().join("promoted/git").exists());
    }

    #[test]
    fn members_are_lexically_sorted_across_files_and_directories() {
        let root = tempfile::tempdir().expect("tempdir");
        let source = root.path().join("source");
        let nested = source.join("async-std/docs/src/concepts");
        fs::create_dir_all(&nested).expect("nested");
        fs::write(
            source.join("async-std/docs/src/concepts.md"),
            "root documentation\n",
        )
        .expect("root doc");
        fs::write(nested.join("async-read-write.md"), "nested documentation\n")
            .expect("nested doc");
        let request = CandidateRequest {
            artifact_name: "main-cache-cargo-inputs-candidate".into(),
            cache_class: "cargo-inputs".into(),
            cache_key: "cargo-inputs-v2-Linux-X64-identity".into(),
            candidate_dir: root.path().join("candidate"),
            maximum_bytes: 1024 * 1024,
            producer_event: "merge_group".into(),
            producer_job: "rust-lint".into(),
            producer_ref: PRODUCER_REF.into(),
            source_sha: SOURCE_SHA.into(),
            sources: vec![CandidateSource {
                name: "registry".into(),
                path: source,
            }],
            tool_versions: BTreeMap::from([
                ("cargo".into(), "cargo test".into()),
                ("rustc".into(), "rustc test".into()),
            ]),
        };
        let staged = stage_candidate(&request).expect("stage");
        let paths: Vec<_> = staged
            .members
            .iter()
            .map(|member| member.path.as_str())
            .collect();
        assert_eq!(
            paths,
            [
                "payload/registry/async-std/docs/src/concepts.md",
                "payload/registry/async-std/docs/src/concepts/async-read-write.md",
            ]
        );
    }

    #[test]
    fn stage_rejects_invalid_provenance_symlinks_duplicates_and_oversize() {
        let root = tempfile::tempdir().expect("tempdir");
        let mut bad_event = make_request(root.path(), "bad-event");
        bad_event.producer_event = "pull_request".into();
        assert!(
            stage_candidate(&bad_event)
                .expect_err("event")
                .to_string()
                .contains("producer event")
        );
        let mut bad_ref = make_request(root.path(), "bad-ref");
        bad_ref.producer_ref = "refs/heads/main".into();
        assert!(
            stage_candidate(&bad_ref)
                .expect_err("ref")
                .to_string()
                .contains("producer ref")
        );
        let mut multiline = make_request(root.path(), "multiline");
        multiline.tool_versions = BTreeMap::from([(
            "cargo-nextest".into(),
            "cargo-nextest 0.9.137\nrelease: 0.9.137".into(),
        )]);
        assert!(stage_candidate(&multiline).is_err());

        #[cfg(unix)]
        {
            let link_root = root.path().join("symlink");
            fs::create_dir_all(link_root.join("source")).expect("source");
            fs::write(link_root.join("target"), "target\n").expect("target");
            std::os::unix::fs::symlink(link_root.join("target"), link_root.join("source/link"))
                .expect("symlink");
            let mut request = make_request(&link_root, "candidate");
            request.sources[0].path = link_root.join("source");
            request.maximum_bytes = 0;
            assert!(
                stage_candidate(&request)
                    .expect_err("symlink")
                    .to_string()
                    .contains("symlink")
            );
        }

        let existing = make_request(root.path(), "existing");
        stage_candidate(&existing).expect("first stage");
        assert!(
            stage_candidate(&existing)
                .expect_err("duplicate")
                .to_string()
                .contains("already exists")
        );

        let mut oversize = make_request(root.path(), "oversize");
        oversize.maximum_bytes = 1;
        assert!(
            stage_candidate(&oversize)
                .expect_err("oversize")
                .to_string()
                .contains("exceeds its maximum size")
        );

        let huge = root.path().join("huge.json");
        let huge_len = usize::try_from(MAX_MANIFEST_BYTES)
            .expect("manifest bound fits usize")
            .saturating_add(1);
        fs::write(&huge, "x".repeat(huge_len)).expect("write");
        assert!(read_manifest(&huge).is_err());
    }

    #[test]
    fn promote_rejects_tampering_and_contract_mismatches() {
        let root = tempfile::tempdir().expect("tempdir");

        let altered = make_request(root.path(), "altered");
        stage_candidate(&altered).expect("stage");
        fs::write(
            altered.candidate_dir.join("payload/llvm-cov-target/larch"),
            b"altered",
        )
        .expect("alter");
        assert!(
            promote_candidate(
                &altered.candidate_dir,
                &root.path().join("out-altered"),
                &contract(&altered),
            )
            .expect_err("members")
            .to_string()
            .contains("members do not match")
        );

        let missing = make_request(root.path(), "missing");
        stage_candidate(&missing).expect("stage");
        fs::remove_file(
            missing
                .candidate_dir
                .join("payload/llvm-cov-target/.fingerprint/dependency.json"),
        )
        .expect("remove");
        assert!(
            promote_candidate(
                &missing.candidate_dir,
                &root.path().join("out-missing"),
                &contract(&missing),
            )
            .is_err()
        );

        let empty = make_request(root.path(), "empty-manifest");
        stage_candidate(&empty).expect("stage");
        fs::write(empty.candidate_dir.join("manifest.json"), "{}\n").expect("empty");
        assert!(
            promote_candidate(
                &empty.candidate_dir,
                &root.path().join("out-empty"),
                &contract(&empty),
            )
            .expect_err("schema")
            .to_string()
            .contains("unexpected schema")
        );

        let identity = make_request(root.path(), "identity");
        stage_candidate(&identity).expect("stage");
        let mut wrong_name = contract(&identity);
        wrong_name.artifact_name = "main-cache-rust-policy-candidate".into();
        assert!(
            promote_candidate(
                &identity.candidate_dir,
                &root.path().join("out-name"),
                &wrong_name,
            )
            .expect_err("name")
            .to_string()
            .contains("artifact name")
        );
        let mut wrong_key = contract(&identity);
        wrong_key.cache_key = "coverage-target-deps-v2-Linux-X64-other".into();
        assert!(
            promote_candidate(
                &identity.candidate_dir,
                &root.path().join("out-key"),
                &wrong_key,
            )
            .expect_err("key")
            .to_string()
            .contains("cache key")
        );
        let mut wrong_sha = contract(&identity);
        wrong_sha.source_sha = "fedcba9876543210fedcba9876543210fedcba98".into();
        assert!(
            promote_candidate(
                &identity.candidate_dir,
                &root.path().join("out-sha"),
                &wrong_sha,
            )
            .expect_err("sha")
            .to_string()
            .contains("source SHA")
        );
        let mut wrong_tools = contract(&identity);
        wrong_tools.expected_tool_versions =
            BTreeMap::from([("cargo-llvm-cov".into(), "cargo-llvm-cov 0.8.8".into())]);
        assert!(
            promote_candidate(
                &identity.candidate_dir,
                &root.path().join("out-tools"),
                &wrong_tools,
            )
            .expect_err("tools")
            .to_string()
            .contains("tool versions")
        );
    }

    #[test]
    fn promote_rejects_digest_mtime_and_schema_tampering() {
        let root = tempfile::tempdir().expect("tempdir");

        for field in ["artifact_sha256", "key_input_digest"] {
            let request = make_request(root.path(), &format!("digest-{field}"));
            stage_candidate(&request).expect("stage");
            rewrite_manifest(&request.candidate_dir, |manifest| {
                manifest.insert(field.to_owned(), Value::String("0".repeat(64)));
            });
            let err = promote_candidate(
                &request.candidate_dir,
                &root.path().join(format!("out-{field}")),
                &contract(&request),
            )
            .expect_err("digest");
            let message = err.to_string();
            assert!(
                message.contains("artifact digest") || message.contains("cache key identity"),
                "{message}"
            );
        }

        let mtime = make_request(root.path(), "mtime");
        stage_candidate(&mtime).expect("stage");
        rewrite_manifest(&mtime.candidate_dir, |manifest| {
            let members = manifest
                .get_mut("members")
                .and_then(Value::as_array_mut)
                .expect("members");
            let member = members[0].as_object_mut().expect("member");
            let current = member
                .get("mtime_ns")
                .and_then(Value::as_i64)
                .expect("mtime");
            member.insert("mtime_ns".into(), Value::from(current + 1));
        });
        assert!(
            promote_candidate(
                &mtime.candidate_dir,
                &root.path().join("out-mtime"),
                &contract(&mtime),
            )
            .expect_err("mtime digest")
            .to_string()
            .contains("artifact digest")
        );

        for bad in [
            Value::Null,
            Value::String("1700000000123456789".into()),
            Value::Bool(true),
            Value::from(-1),
        ] {
            let request = make_request(root.path(), &format!("bad-mtime-{bad}"));
            stage_candidate(&request).expect("stage");
            rewrite_manifest(&request.candidate_dir, |manifest| {
                let members = manifest
                    .get_mut("members")
                    .and_then(Value::as_array_mut)
                    .expect("members");
                members[0]
                    .as_object_mut()
                    .expect("member")
                    .insert("mtime_ns".into(), bad.clone());
            });
            assert!(
                promote_candidate(
                    &request.candidate_dir,
                    &root.path().join(format!("out-bad-mtime-{bad}")),
                    &contract(&request),
                )
                .expect_err("mtime")
                .to_string()
                .contains("mtime_ns is invalid")
            );
        }

        let legacy = make_request(root.path(), "legacy");
        stage_candidate(&legacy).expect("stage");
        rewrite_manifest(&legacy.candidate_dir, |manifest| {
            manifest.insert("schema_version".into(), Value::from(1));
        });
        assert!(
            promote_candidate(
                &legacy.candidate_dir,
                &root.path().join("out-legacy"),
                &contract(&legacy),
            )
            .expect_err("schema")
            .to_string()
            .contains("unsupported schema version")
        );
    }
}
