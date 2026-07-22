//! Deterministic release archive construction and fail-closed validation.

use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
    fs,
    io::Write,
    os::unix::fs::MetadataExt,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

use flate2::{Compression, GzBuilder, read::GzDecoder};
use larch_adapters::{
    PathIntent, TemporaryRoot, TokioProcessRunner, atomic_write_bytes, atomic_write_utf8,
    github::{AttestationOperations, OctocrabAttestationTransport, OctocrabGitHubService},
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ArtifactAttestationRequest, ReleaseAssetSubject, ReleaseSourceCommit, ReleaseTag, emit_kv,
};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

const SCHEMA_VERSION: u64 = 1;
const FRAGMENT_SCHEMA_VERSION: u64 = 1;
const BINARY_PATH: &str = "larch";
const LICENSE_PATH: &str = "LICENSE";
const GZIP_HEADER: [u8; 10] = [0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff];
const TAR_BLOCK: usize = 512;
const MAX_ARCHIVE_BYTES: u64 = 256 * 1024 * 1024;

const TARGETS: [&str; 1] = ["aarch64-apple-darwin"];

#[derive(Clone, Debug, Eq, PartialEq)]
struct PlatformContract {
    kind: String,
    version: String,
}

fn target_contracts() -> [(&'static str, PlatformContract); 1] {
    [(
        "aarch64-apple-darwin",
        PlatformContract {
            kind: "macos".to_owned(),
            version: "11.0".to_owned(),
        },
    )]
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ReleaseIdentity {
    version: String,
    tag: String,
    source_commit: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct AssetRecord {
    target: String,
    archive: String,
    byte_size: u64,
    sha256: String,
    binary_path: String,
    minimum_os_or_libc: PlatformContract,
}

#[derive(Debug)]
struct AssetError(String);

impl AssetError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl std::fmt::Display for AssetError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

pub struct CandidateArguments {
    pub repo_root: PathBuf,
    pub tag: String,
    pub source_commit: String,
}

pub struct PackageArguments {
    pub version: String,
    pub tag: String,
    pub source_commit: String,
    pub target: String,
    pub binary: PathBuf,
    pub license: PathBuf,
    pub output_dir: PathBuf,
}

pub struct CollectArguments {
    pub version: String,
    pub tag: String,
    pub source_commit: String,
    pub input_dir: PathBuf,
    pub output_dir: PathBuf,
    pub license: PathBuf,
}

pub struct ValidateArguments {
    pub version: String,
    pub tag: String,
    pub source_commit: String,
    pub asset_dir: PathBuf,
    pub license: PathBuf,
    pub verify_attestations: bool,
}

pub fn asset_candidate(arguments: &CandidateArguments) -> ExitCode {
    match validate_candidate(
        &arguments.repo_root,
        &arguments.tag,
        &arguments.source_commit,
    ) {
        Ok(identity) => {
            emit_kv("VERSION", &identity.version);
            emit_kv("SOURCE_COMMIT", &identity.source_commit);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

pub fn package_asset(arguments: &PackageArguments) -> ExitCode {
    match package_asset_inner(arguments) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => fail(&error),
    }
}

pub fn collect_assets(arguments: &CollectArguments) -> ExitCode {
    match collect_assets_inner(arguments) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => fail(&error),
    }
}

pub fn validate_assets(arguments: &ValidateArguments) -> ExitCode {
    match validate_assets_inner(arguments) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => fail(&error),
    }
}

pub fn release_asset_names(
    version: &str,
    tag: &str,
    source_commit: &str,
) -> Result<Vec<String>, String> {
    identity(version, tag, source_commit)
        .map(|identity| expected_asset_names(&identity))
        .map_err(|error| error.to_string())
}

pub fn validate_downloaded_assets(
    version: &str,
    tag: &str,
    source_commit: &str,
    asset_dir: &Path,
    license: &Path,
) -> Result<(), String> {
    let identity = identity(version, tag, source_commit).map_err(|error| error.to_string())?;
    validate_assets_at(asset_dir, license, &identity).map_err(|error| error.to_string())
}

#[must_use]
pub fn sha256_bytes(data: &[u8]) -> String {
    sha256_hex(data)
}

fn fail(error: &AssetError) -> ExitCode {
    eprintln!("ERROR={error}");
    ExitCode::FAILURE
}

fn identity(version: &str, tag: &str, source_commit: &str) -> Result<ReleaseIdentity, AssetError> {
    if !is_semver(version) {
        return Err(AssetError::new(format!(
            "invalid plugin version: {version}"
        )));
    }
    let expected_tag = format!("v{version}");
    if tag != expected_tag {
        return Err(AssetError::new(format!(
            "tag {tag} does not match plugin version {version}"
        )));
    }
    if !is_commit(source_commit) {
        return Err(AssetError::new(
            "source commit must be a lowercase 40-character Git object ID",
        ));
    }
    Ok(ReleaseIdentity {
        version: version.to_owned(),
        tag: tag.to_owned(),
        source_commit: source_commit.to_owned(),
    })
}

fn validate_candidate(
    repo_root: &Path,
    tag: &str,
    source_commit: &str,
) -> Result<ReleaseIdentity, AssetError> {
    let root = repo_root
        .canonicalize()
        .map_err(|error| AssetError::new(format!("repo root is not readable: {error}")))?;
    let plugin = object(
        load_json(&root.join(".claude-plugin/plugin.json"))?,
        "plugin manifest",
    )?;
    let plugin_version = string_field(&plugin, "version", "plugin manifest")?;
    let cargo_text = fs::read_to_string(root.join("Cargo.toml")).map_err(|error| {
        AssetError::new(format!(
            "Cargo.toml has no valid workspace package version: {error}"
        ))
    })?;
    let cargo: Value = toml::from_str(&cargo_text).map_err(|error| {
        AssetError::new(format!(
            "Cargo.toml has no valid workspace package version: {error}"
        ))
    })?;
    let cargo_version = cargo
        .get("workspace")
        .and_then(|value| value.get("package"))
        .and_then(|value| value.get("version"))
        .and_then(Value::as_str)
        .ok_or_else(|| AssetError::new("Cargo.toml has no valid workspace package version"))?;
    if cargo_version != plugin_version {
        return Err(AssetError::new(format!(
            "Cargo workspace version {cargo_version} does not match plugin version {plugin_version}"
        )));
    }
    identity(plugin_version, tag, source_commit)
}

fn package_asset_inner(arguments: &PackageArguments) -> Result<(), AssetError> {
    let identity = identity(&arguments.version, &arguments.tag, &arguments.source_commit)?;
    let contract = target_contract(&arguments.target)?;
    let binary = arguments
        .binary
        .canonicalize()
        .map_err(|error| AssetError::new(format!("release executable is not readable: {error}")))?;
    let license = arguments
        .license
        .canonicalize()
        .map_err(|error| AssetError::new(format!("license is not readable: {error}")))?;
    check_binary_version(&binary, &identity.version)?;
    let _ = require_regular(&license, "license", true)?;
    let binary_data = fs::read(&binary)
        .map_err(|error| AssetError::new(format!("release executable is not readable: {error}")))?;
    let license_text = fs::read(&license)
        .map_err(|error| AssetError::new(format!("license is not readable: {error}")))?;
    let archive_data = deterministic_archive(&binary_data, &license_text)?;
    let output = ensure_output_root(&arguments.output_dir)?;
    let archive_name = archive_name(&identity, &arguments.target);
    write_bytes(&output, &archive_name, &archive_data)?;
    validate_archive(&output.path().join(&archive_name), &license_text)?;
    let record = AssetRecord {
        target: arguments.target.clone(),
        archive: archive_name,
        byte_size: archive_data.len() as u64,
        sha256: sha256_hex(&archive_data),
        binary_path: BINARY_PATH.to_owned(),
        minimum_os_or_libc: contract,
    };
    let fragment = fragment_json(&identity, &record);
    let fragment_name = fragment_name(&identity, &arguments.target);
    write_utf8(&output, &fragment_name, &fragment)?;
    Ok(())
}

fn collect_assets_inner(arguments: &CollectArguments) -> Result<(), AssetError> {
    let identity = identity(&arguments.version, &arguments.tag, &arguments.source_commit)?;
    let discovered = discover_recursive(&arguments.input_dir)?;
    let expected = expected_input_names(&identity);
    let actual: BTreeSet<String> = discovered.keys().cloned().collect();
    if actual != expected {
        return Err(AssetError::new(format!(
            "input asset set mismatch: missing={:?}, unexpected={:?}",
            sorted_diff(&expected, &actual),
            sorted_diff(&actual, &expected)
        )));
    }
    let _ = require_regular(&arguments.license, "license", true)?;
    let license_text = fs::read(&arguments.license)
        .map_err(|error| AssetError::new(format!("license is not readable: {error}")))?;
    let output_names = expected_output_names(&identity);
    if arguments.output_dir.exists() {
        let metadata = fs::symlink_metadata(&arguments.output_dir).map_err(|error| {
            AssetError::new(format!(
                "asset output root must be a real directory: {error}"
            ))
        })?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(AssetError::new(
                "asset output root must be a real directory",
            ));
        }
        let stale: BTreeSet<String> = fs::read_dir(&arguments.output_dir)
            .map_err(|error| {
                AssetError::new(format!(
                    "asset output root must be a real directory: {error}"
                ))
            })?
            .filter_map(Result::ok)
            .map(|entry| entry.file_name().to_string_lossy().into_owned())
            .filter(|name| !output_names.contains(name))
            .collect();
        if !stale.is_empty() {
            return Err(AssetError::new(format!(
                "asset output contains unexpected entries: {:?}",
                stale.into_iter().collect::<Vec<_>>()
            )));
        }
    }
    fs::create_dir_all(&arguments.output_dir).map_err(|error| {
        AssetError::new(format!(
            "asset output root must be a real directory: {error}"
        ))
    })?;
    let output = ensure_output_root(&arguments.output_dir)?;
    let mut records = Vec::with_capacity(TARGETS.len());
    for target in TARGETS {
        let record = fragment_record(
            &discovered[&fragment_name(&identity, target)],
            &identity,
            target,
        )?;
        let archive_input = &discovered[&record.archive];
        verify_record_file(&record, archive_input, &license_text)?;
        let archive_bytes = fs::read(archive_input)
            .map_err(|error| AssetError::new(format!("archive is not readable: {error}")))?;
        write_bytes(&output, &record.archive, &archive_bytes)?;
        records.push(record);
    }
    let manifest = manifest_json(&identity, &records);
    write_utf8(&output, &manifest_name(&identity), &manifest)?;
    let checksums = checksum_text(&identity, output.path())?;
    write_utf8(&output, &checksums_name(&identity), &checksums)?;
    validate_assets_at(output.path(), &arguments.license, &identity)?;
    Ok(())
}

fn validate_assets_inner(arguments: &ValidateArguments) -> Result<(), AssetError> {
    let identity = identity(&arguments.version, &arguments.tag, &arguments.source_commit)?;
    validate_assets_at(&arguments.asset_dir, &arguments.license, &identity)?;
    if arguments.verify_attestations {
        verify_artifact_attestations(&arguments.asset_dir, &identity)?;
    }
    Ok(())
}

fn validate_assets_at(
    output_dir: &Path,
    license_path: &Path,
    identity: &ReleaseIdentity,
) -> Result<(), AssetError> {
    let expected = expected_output_names(identity);
    let discovered = discover_output(output_dir, &expected)?;
    let _ = require_regular(license_path, "license", true)?;
    let license_text = fs::read(license_path)
        .map_err(|error| AssetError::new(format!("license is not readable: {error}")))?;
    let records = parse_manifest(&discovered[&manifest_name(identity)], identity)?;
    for record in &records {
        if record.archive != archive_name(identity, &record.target) {
            return Err(AssetError::new(format!(
                "release manifest archive name mismatch: {}",
                record.target
            )));
        }
        if record.minimum_os_or_libc != target_contract(&record.target)? {
            return Err(AssetError::new(format!(
                "release manifest minimum platform mismatch: {}",
                record.target
            )));
        }
        verify_record_file(record, &discovered[&record.archive], &license_text)?;
    }
    let expected_checksums = checksum_text(identity, output_dir)?;
    let actual_checksums =
        fs::read_to_string(&discovered[&checksums_name(identity)]).map_err(|error| {
            AssetError::new(format!("checksum file must be readable ASCII: {error}"))
        })?;
    if !actual_checksums.is_ascii() {
        return Err(AssetError::new("checksum file must be readable ASCII"));
    }
    if actual_checksums != expected_checksums {
        return Err(AssetError::new("checksum file contents mismatch"));
    }
    Ok(())
}

fn verify_artifact_attestations(
    asset_dir: &Path,
    identity: &ReleaseIdentity,
) -> Result<(), AssetError> {
    let runtime = LarchRuntime::new()
        .map_err(|error| AssetError::new(format!("attestation runtime failed: {error}")))?;
    runtime.block_on(async {
        let working_directory = std::env::current_dir()
            .map_err(|error| AssetError::new(format!("credential lookup failed: {error}")))?;
        let cancellation = Cancellation::new();
        let runner = TokioProcessRunner::default();
        let service = OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation)
            .await
            .map_err(|error| AssetError::new(error.to_string()))?;
        let transport = OctocrabAttestationTransport::new(&service, &cancellation);
        let operations = AttestationOperations::new(&transport);
        let tag =
            ReleaseTag::parse(&identity.tag).map_err(|error| AssetError::new(error.to_string()))?;
        let source_commit = ReleaseSourceCommit::parse(&identity.source_commit)
            .map_err(|error| AssetError::new(error.to_string()))?;
        for name in expected_asset_names(identity) {
            let path = asset_dir.join(&name);
            let digest = format!("sha256:{}", sha256_file(&path)?);
            let subject = ReleaseAssetSubject::new(&name, &digest)
                .map_err(|error| AssetError::new(error.to_string()))?;
            let request =
                ArtifactAttestationRequest::new(subject, tag.clone(), source_commit.clone());
            operations
                .verify_artifact(&request)
                .await
                .map_err(|error| AssetError::new(error.to_string()))?;
        }
        Ok(())
    })
}

fn expected_asset_names(identity: &ReleaseIdentity) -> Vec<String> {
    let mut names: Vec<String> = TARGETS
        .iter()
        .map(|target| archive_name(identity, target))
        .collect();
    names.push(manifest_name(identity));
    names.push(checksums_name(identity));
    names
}

fn target_contract(target: &str) -> Result<PlatformContract, AssetError> {
    target_contracts()
        .into_iter()
        .find_map(|(name, contract)| (name == target).then_some(contract))
        .ok_or_else(|| AssetError::new(format!("unsupported release target: {target}")))
}

fn archive_name(identity: &ReleaseIdentity, target: &str) -> String {
    format!("larch-v{}-{target}.tar.gz", identity.version)
}

fn fragment_name(identity: &ReleaseIdentity, target: &str) -> String {
    format!("larch-v{}-{target}.asset.json", identity.version)
}

fn manifest_name(identity: &ReleaseIdentity) -> String {
    format!("larch-v{}-manifest.json", identity.version)
}

fn checksums_name(identity: &ReleaseIdentity) -> String {
    format!("larch-v{}-SHA256SUMS", identity.version)
}

fn expected_input_names(identity: &ReleaseIdentity) -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    for target in TARGETS {
        names.insert(archive_name(identity, target));
        names.insert(fragment_name(identity, target));
    }
    names
}

fn expected_output_names(identity: &ReleaseIdentity) -> BTreeSet<String> {
    expected_asset_names(identity).into_iter().collect()
}

fn deterministic_archive(binary: &[u8], license_text: &[u8]) -> Result<Vec<u8>, AssetError> {
    const RECORD_SIZE: usize = TAR_BLOCK * 20;
    let mut tar = Vec::new();
    write_ustar_file(&mut tar, BINARY_PATH, binary, 0o755)?;
    write_ustar_file(&mut tar, LICENSE_PATH, license_text, 0o644)?;
    tar.extend_from_slice(&[0_u8; TAR_BLOCK * 2]);
    let remainder = tar.len() % RECORD_SIZE;
    if remainder != 0 {
        tar.extend(std::iter::repeat_n(0_u8, RECORD_SIZE - remainder));
    }
    let mut encoder = GzBuilder::new()
        .mtime(0)
        .write(Vec::new(), Compression::best());
    encoder
        .write_all(&tar)
        .map_err(|error| AssetError::new(format!("archive gzip failed: {error}")))?;
    let gzipped = encoder
        .finish()
        .map_err(|error| AssetError::new(format!("archive gzip failed: {error}")))?;
    if gzipped.len() < GZIP_HEADER.len() || gzipped[..GZIP_HEADER.len()] != GZIP_HEADER {
        return Err(AssetError::new(
            "archive gzip metadata is not deterministic",
        ));
    }
    Ok(gzipped)
}

fn write_ustar_file(
    output: &mut Vec<u8>,
    name: &str,
    data: &[u8],
    mode: u32,
) -> Result<(), AssetError> {
    if name.len() >= 100 || name.contains('/') || name.contains('\\') {
        return Err(AssetError::new(format!(
            "archive member name is invalid: {name}"
        )));
    }
    let mut header = [0_u8; TAR_BLOCK];
    header[..name.len()].copy_from_slice(name.as_bytes());
    write_octal(&mut header[100..108], u64::from(mode))?;
    write_octal(&mut header[108..116], 0)?;
    write_octal(&mut header[116..124], 0)?;
    write_octal(&mut header[124..136], data.len() as u64)?;
    write_octal(&mut header[136..148], 0)?;
    header[148..156].fill(b' ');
    header[156] = b'0';
    header[257..263].copy_from_slice(b"ustar\0");
    header[263..265].copy_from_slice(b"00");
    let checksum: u32 = header.iter().map(|byte| u32::from(*byte)).sum();
    write_octal(&mut header[148..155], u64::from(checksum))?;
    header[155] = b' ';
    output.extend_from_slice(&header);
    output.extend_from_slice(data);
    let padding = (TAR_BLOCK - (data.len() % TAR_BLOCK)) % TAR_BLOCK;
    output.extend(std::iter::repeat_n(0_u8, padding));
    Ok(())
}

fn write_octal(slot: &mut [u8], value: u64) -> Result<(), AssetError> {
    let width = slot.len().saturating_sub(1);
    let rendered = format!("{value:0width$o}");
    if rendered.len() != width {
        return Err(AssetError::new("archive member metadata overflow"));
    }
    slot[..width].copy_from_slice(rendered.as_bytes());
    slot[width] = b'\0';
    Ok(())
}

fn validate_archive(path: &Path, license_text: &[u8]) -> Result<(), AssetError> {
    let _ = require_regular(path, "archive", true)?;
    let data = fs::read(path)
        .map_err(|error| AssetError::new(format!("archive is not readable: {error}")))?;
    if data.len() as u64 > MAX_ARCHIVE_BYTES {
        return Err(AssetError::new(format!(
            "archive exceeds size limit: {}",
            basename(path)
        )));
    }
    let tar_data = decompress_archive(&data, path)?;
    let members = parse_ustar_members(&tar_data, path)?;
    if members.len() != 2 || members[0].name != BINARY_PATH || members[1].name != LICENSE_PATH {
        return Err(AssetError::new(format!(
            "archive member allowlist mismatch: {}",
            basename(path)
        )));
    }
    for (member, expected_mode) in members.iter().zip([0o755_u32, 0o644_u32]) {
        if member.mode != expected_mode
            || member.uid != 0
            || member.gid != 0
            || member.mtime != 0
            || !member.uname.is_empty()
            || !member.gname.is_empty()
        {
            return Err(AssetError::new(format!(
                "archive member metadata is not deterministic: {}",
                member.name
            )));
        }
    }
    if members[0].data.is_empty() {
        return Err(AssetError::new(format!(
            "archive executable is empty: {}",
            basename(path)
        )));
    }
    if members[1].data != license_text {
        return Err(AssetError::new(format!(
            "archive license does not match repository LICENSE: {}",
            basename(path)
        )));
    }
    Ok(())
}

fn decompress_archive(data: &[u8], path: &Path) -> Result<Vec<u8>, AssetError> {
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("archive");
    if data.len() < GZIP_HEADER.len() || data[..GZIP_HEADER.len()] != GZIP_HEADER {
        return Err(AssetError::new(format!(
            "archive gzip metadata is not deterministic: {name}"
        )));
    }
    let mut decoder = GzDecoder::new(data);
    let mut tar_data = Vec::new();
    std::io::copy(&mut decoder, &mut tar_data)
        .map_err(|error| AssetError::new(format!("invalid archive {name}: {error}")))?;
    Ok(tar_data)
}

struct TarMember {
    name: String,
    mode: u32,
    uid: u32,
    gid: u32,
    mtime: u64,
    uname: String,
    gname: String,
    data: Vec<u8>,
}

fn parse_ustar_members(tar_data: &[u8], path: &Path) -> Result<Vec<TarMember>, AssetError> {
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("archive");
    if tar_data.len() < TAR_BLOCK * 2 {
        return Err(AssetError::new(format!(
            "invalid archive {name}: truncated"
        )));
    }
    let mut offset = 0_usize;
    let mut members = Vec::new();
    while offset + TAR_BLOCK <= tar_data.len() {
        let header = &tar_data[offset..offset + TAR_BLOCK];
        if header.iter().all(|byte| *byte == 0) {
            let trailing = &tar_data[offset..];
            if trailing.len() < TAR_BLOCK * 2 || trailing.iter().any(|byte| *byte != 0) {
                return Err(AssetError::new(format!(
                    "archive tar padding is not deterministic: {name}"
                )));
            }
            return Ok(members);
        }
        let checksum = parse_octal_field(&header[148..156], name, "bad checksum")?;
        let mut sum = 0_u32;
        for (index, byte) in header.iter().enumerate() {
            sum += u32::from(if (148..156).contains(&index) {
                b' '
            } else {
                *byte
            });
        }
        if u64::from(sum) != checksum {
            return Err(AssetError::new(format!("invalid archive {name}: checksum")));
        }
        if header[156] != b'0' {
            return Err(AssetError::new(format!(
                "archive member is not regular: {}",
                read_c_string(&header[..100])
            )));
        }
        let size = usize::try_from(parse_octal_field(&header[124..136], name, "bad size")?)
            .map_err(|_| AssetError::new(format!("invalid archive {name}: size overflow")))?;
        let data_start = offset + TAR_BLOCK;
        let data_end = data_start
            .checked_add(size)
            .ok_or_else(|| AssetError::new(format!("invalid archive {name}: size overflow")))?;
        if data_end > tar_data.len() {
            return Err(AssetError::new(format!(
                "invalid archive {name}: truncated member"
            )));
        }
        members.push(TarMember {
            name: read_c_string(&header[..100]),
            mode: u32::try_from(parse_octal_field(&header[100..108], name, "bad mode")?)
                .map_err(|_| AssetError::new(format!("invalid archive {name}: bad mode")))?,
            uid: u32::try_from(parse_octal_field(&header[108..116], name, "bad uid")?)
                .map_err(|_| AssetError::new(format!("invalid archive {name}: bad uid")))?,
            gid: u32::try_from(parse_octal_field(&header[116..124], name, "bad gid")?)
                .map_err(|_| AssetError::new(format!("invalid archive {name}: bad gid")))?,
            mtime: parse_octal_field(&header[136..148], name, "bad mtime")?,
            uname: read_c_string(&header[265..297]),
            gname: read_c_string(&header[297..329]),
            data: tar_data[data_start..data_end].to_vec(),
        });
        let padded = data_end + ((TAR_BLOCK - (size % TAR_BLOCK)) % TAR_BLOCK);
        offset = padded;
    }
    Err(AssetError::new(format!(
        "archive tar padding is not deterministic: {name}"
    )))
}

fn parse_octal_field(bytes: &[u8], archive: &str, detail: &str) -> Result<u64, AssetError> {
    parse_octal(bytes).map_err(|()| AssetError::new(format!("invalid archive {archive}: {detail}")))
}

fn parse_octal(bytes: &[u8]) -> Result<u64, ()> {
    let text = read_c_string(bytes);
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return Ok(0);
    }
    u64::from_str_radix(trimmed, 8).map_err(|_| ())
}

fn read_c_string(bytes: &[u8]) -> String {
    let end = bytes
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(bytes.len());
    String::from_utf8_lossy(&bytes[..end]).into_owned()
}

fn check_binary_version(binary: &Path, version: &str) -> Result<(), AssetError> {
    let metadata = require_regular(binary, "release executable", true)?;
    if metadata.mode() & 0o111 == 0 {
        return Err(AssetError::new("release executable is not executable"));
    }
    let output = Command::new(binary) // lint-subprocess-via-runner: ok release packaging smokes the staged target binary --version contract
        .arg("--version")
        .output()
        .map_err(|error| {
            AssetError::new(format!(
                "release executable did not report the requested version: {error}"
            ))
        })?;
    let expected = format!("larch {version}\n");
    if !output.status.success() || output.stdout != expected.as_bytes() || !output.stderr.is_empty()
    {
        return Err(AssetError::new(
            "release executable did not report the requested version",
        ));
    }
    Ok(())
}

fn verify_record_file(
    record: &AssetRecord,
    path: &Path,
    license_text: &[u8],
) -> Result<(), AssetError> {
    let metadata = require_regular(path, "archive", true)?;
    let data = fs::read(path)
        .map_err(|error| AssetError::new(format!("archive is not readable: {error}")))?;
    if metadata.len() != record.byte_size {
        return Err(AssetError::new(format!(
            "archive size mismatch: {}",
            basename(path)
        )));
    }
    if sha256_hex(&data) != record.sha256 {
        return Err(AssetError::new(format!(
            "archive digest mismatch: {}",
            basename(path)
        )));
    }
    validate_archive(path, license_text)
}

fn fragment_record(
    path: &Path,
    identity: &ReleaseIdentity,
    target: &str,
) -> Result<AssetRecord, AssetError> {
    let fragment = object(load_json(path)?, "asset fragment")?;
    exact_keys(
        &fragment,
        &[
            "fragment_schema_version",
            "plugin_version",
            "tag",
            "source_commit",
            "asset",
        ],
        "asset fragment",
    )?;
    if fragment
        .get("fragment_schema_version")
        .and_then(Value::as_u64)
        != Some(FRAGMENT_SCHEMA_VERSION)
    {
        return Err(AssetError::new(format!(
            "fragment schema version mismatch: {}",
            basename(path)
        )));
    }
    if fragment.get("plugin_version").and_then(Value::as_str) != Some(identity.version.as_str())
        || fragment.get("tag").and_then(Value::as_str) != Some(identity.tag.as_str())
    {
        return Err(AssetError::new(format!(
            "fragment release identity mismatch: {}",
            basename(path)
        )));
    }
    if fragment.get("source_commit").and_then(Value::as_str)
        != Some(identity.source_commit.as_str())
    {
        return Err(AssetError::new(format!(
            "fragment source commit mismatch: {}",
            basename(path)
        )));
    }
    let record = parse_record(
        fragment.get("asset").cloned().unwrap_or(Value::Null),
        &format!("asset fragment {}", basename(path)),
    )?;
    if record.target != target {
        return Err(AssetError::new(format!(
            "fragment target mismatch: {}",
            basename(path)
        )));
    }
    if record.archive != archive_name(identity, target) {
        return Err(AssetError::new(format!(
            "fragment archive name mismatch: {}",
            basename(path)
        )));
    }
    if record.minimum_os_or_libc != target_contract(target)? {
        return Err(AssetError::new(format!(
            "fragment minimum platform mismatch: {}",
            basename(path)
        )));
    }
    Ok(record)
}

fn parse_manifest(path: &Path, identity: &ReleaseIdentity) -> Result<Vec<AssetRecord>, AssetError> {
    let manifest = object(load_json(path)?, "release manifest")?;
    exact_keys(
        &manifest,
        &[
            "schema_version",
            "plugin_version",
            "tag",
            "source_commit",
            "assets",
        ],
        "release manifest",
    )?;
    if manifest.get("schema_version").and_then(Value::as_u64) != Some(SCHEMA_VERSION) {
        return Err(AssetError::new("release manifest schema version mismatch"));
    }
    if manifest.get("plugin_version").and_then(Value::as_str) != Some(identity.version.as_str())
        || manifest.get("tag").and_then(Value::as_str) != Some(identity.tag.as_str())
    {
        return Err(AssetError::new("release manifest identity mismatch"));
    }
    if manifest.get("source_commit").and_then(Value::as_str)
        != Some(identity.source_commit.as_str())
    {
        return Err(AssetError::new("release manifest source commit mismatch"));
    }
    let assets = manifest
        .get("assets")
        .and_then(Value::as_array)
        .ok_or_else(|| AssetError::new("release manifest assets must be an array"))?;
    let records = assets
        .iter()
        .enumerate()
        .map(|(index, value)| {
            parse_record(value.clone(), &format!("release manifest asset {index}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let targets: Vec<&str> = records
        .iter()
        .map(|record| record.target.as_str())
        .collect();
    if targets != TARGETS {
        return Err(AssetError::new(
            "release manifest targets are missing, duplicated, unexpected, or out of order",
        ));
    }
    Ok(records)
}

fn parse_record(value: Value, label: &str) -> Result<AssetRecord, AssetError> {
    let record = object(value, label)?;
    exact_keys(
        &record,
        &[
            "target",
            "archive",
            "byte_size",
            "sha256",
            "binary_path",
            "minimum_os_or_libc",
        ],
        label,
    )?;
    let target = string_field(&record, "target", label)?.to_owned();
    let _ = target_contract(&target)
        .map_err(|_| AssetError::new(format!("{label} has an unsupported target")))?;
    let archive = string_field(&record, "archive", label)?.to_owned();
    if Path::new(&archive)
        .file_name()
        .and_then(|value| value.to_str())
        != Some(archive.as_str())
    {
        return Err(AssetError::new(format!(
            "{label} archive must be a basename"
        )));
    }
    let byte_size = record
        .get("byte_size")
        .and_then(Value::as_u64)
        .filter(|value| *value > 0)
        .ok_or_else(|| AssetError::new(format!("{label} byte_size must be a positive integer")))?;
    let sha256 = string_field(&record, "sha256", label)?.to_owned();
    if !is_sha256(&sha256) {
        return Err(AssetError::new(format!("{label} sha256 is invalid")));
    }
    let binary_path = string_field(&record, "binary_path", label)?;
    if binary_path != BINARY_PATH {
        return Err(AssetError::new(format!(
            "{label} binary_path must be {BINARY_PATH}"
        )));
    }
    let contract_value = record
        .get("minimum_os_or_libc")
        .cloned()
        .unwrap_or(Value::Null);
    let contract = parse_contract(contract_value, &format!("{label} minimum contract"))?;
    Ok(AssetRecord {
        target,
        archive,
        byte_size,
        sha256,
        binary_path: BINARY_PATH.to_owned(),
        minimum_os_or_libc: contract,
    })
}

fn parse_contract(value: Value, label: &str) -> Result<PlatformContract, AssetError> {
    let contract = object(value, label)?;
    exact_keys(&contract, &["kind", "version"], label)?;
    Ok(PlatformContract {
        kind: string_field(&contract, "kind", label)?.to_owned(),
        version: string_field(&contract, "version", label)?.to_owned(),
    })
}

fn fragment_json(identity: &ReleaseIdentity, record: &AssetRecord) -> String {
    format!(
        "{{\n  \"fragment_schema_version\": {FRAGMENT_SCHEMA_VERSION},\n  \"plugin_version\": {},\n  \"tag\": {},\n  \"source_commit\": {},\n  \"asset\": {{\n    \"target\": {},\n    \"archive\": {},\n    \"byte_size\": {},\n    \"sha256\": {},\n    \"binary_path\": {},\n    \"minimum_os_or_libc\": {{\n      \"kind\": {},\n      \"version\": {}\n    }}\n  }}\n}}\n",
        json_string(&identity.version),
        json_string(&identity.tag),
        json_string(&identity.source_commit),
        json_string(&record.target),
        json_string(&record.archive),
        record.byte_size,
        json_string(&record.sha256),
        json_string(&record.binary_path),
        json_string(&record.minimum_os_or_libc.kind),
        json_string(&record.minimum_os_or_libc.version),
    )
}

fn manifest_json(identity: &ReleaseIdentity, records: &[AssetRecord]) -> String {
    let mut assets = String::new();
    for (index, record) in records.iter().enumerate() {
        if index > 0 {
            assets.push(',');
        }
        let _ = write!(
            assets,
            "\n    {{\n      \"target\": {},\n      \"archive\": {},\n      \"byte_size\": {},\n      \"sha256\": {},\n      \"binary_path\": {},\n      \"minimum_os_or_libc\": {{\n        \"kind\": {},\n        \"version\": {}\n      }}\n    }}",
            json_string(&record.target),
            json_string(&record.archive),
            record.byte_size,
            json_string(&record.sha256),
            json_string(&record.binary_path),
            json_string(&record.minimum_os_or_libc.kind),
            json_string(&record.minimum_os_or_libc.version),
        );
    }
    format!(
        "{{\n  \"schema_version\": {SCHEMA_VERSION},\n  \"plugin_version\": {},\n  \"tag\": {},\n  \"source_commit\": {},\n  \"assets\": [{assets}\n  ]\n}}\n",
        json_string(&identity.version),
        json_string(&identity.tag),
        json_string(&identity.source_commit),
    )
}

fn json_string(value: &str) -> String {
    serde_json::to_string(value).expect("string json")
}

fn checksum_text(identity: &ReleaseIdentity, output_dir: &Path) -> Result<String, AssetError> {
    let mut names: Vec<String> = TARGETS
        .iter()
        .map(|target| archive_name(identity, target))
        .collect();
    names.push(manifest_name(identity));
    let mut text = String::new();
    for name in names {
        let digest = sha256_file(&output_dir.join(&name))?;
        let _ = writeln!(text, "{digest}  {name}");
    }
    Ok(text)
}

fn discover_recursive(root: &Path) -> Result<BTreeMap<String, PathBuf>, AssetError> {
    let metadata = fs::symlink_metadata(root).map_err(|error| {
        AssetError::new(format!(
            "asset input root must be a real directory: {error}"
        ))
    })?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(AssetError::new("asset input root must be a real directory"));
    }
    let mut discovered = BTreeMap::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in fs::read_dir(&dir).map_err(|error| {
            AssetError::new(format!(
                "asset input root must be a real directory: {error}"
            ))
        })? {
            let entry = entry.map_err(|error| {
                AssetError::new(format!(
                    "asset input root must be a real directory: {error}"
                ))
            })?;
            let path = entry.path();
            let metadata = fs::symlink_metadata(&path).map_err(|error| {
                AssetError::new(format!("asset input is not readable: {error}"))
            })?;
            if metadata.file_type().is_symlink() {
                return Err(AssetError::new(format!(
                    "asset input contains a symlink: {}",
                    basename(&path)
                )));
            }
            if metadata.is_dir() {
                stack.push(path);
                continue;
            }
            let _ = require_regular(&path, "asset input", true)?;
            let name = path
                .file_name()
                .and_then(|value| value.to_str())
                .ok_or_else(|| AssetError::new("asset input name is invalid"))?
                .to_owned();
            if discovered.insert(name.clone(), path).is_some() {
                return Err(AssetError::new(format!("duplicate asset input: {name}")));
            }
        }
    }
    Ok(discovered)
}

fn discover_output(
    root: &Path,
    expected: &BTreeSet<String>,
) -> Result<BTreeMap<String, PathBuf>, AssetError> {
    let metadata = fs::symlink_metadata(root).map_err(|error| {
        AssetError::new(format!(
            "asset output root must be a real directory: {error}"
        ))
    })?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(AssetError::new(
            "asset output root must be a real directory",
        ));
    }
    let mut discovered = BTreeMap::new();
    for entry in fs::read_dir(root).map_err(|error| {
        AssetError::new(format!(
            "asset output root must be a real directory: {error}"
        ))
    })? {
        let entry = entry.map_err(|error| {
            AssetError::new(format!(
                "asset output root must be a real directory: {error}"
            ))
        })?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)
            .map_err(|error| AssetError::new(format!("final asset is not readable: {error}")))?;
        if metadata.is_dir() {
            return Err(AssetError::new(
                "final asset set must not contain directories",
            ));
        }
        let _ = require_regular(&path, "final asset", true)?;
        let name = path
            .file_name()
            .and_then(|value| value.to_str())
            .ok_or_else(|| AssetError::new("final asset name is invalid"))?
            .to_owned();
        discovered.insert(name, path);
    }
    let actual: BTreeSet<String> = discovered.keys().cloned().collect();
    if &actual != expected {
        return Err(AssetError::new(format!(
            "final asset set mismatch: missing={:?}, unexpected={:?}",
            sorted_diff(expected, &actual),
            sorted_diff(&actual, expected)
        )));
    }
    Ok(discovered)
}

fn ensure_output_root(path: &Path) -> Result<TemporaryRoot, AssetError> {
    fs::create_dir_all(path).map_err(|error| {
        AssetError::new(format!(
            "asset output root must be a real directory: {error}"
        ))
    })?;
    TemporaryRoot::resolve(Some(path)).map_err(|error| AssetError::new(error.to_string()))
}

fn write_bytes(root: &TemporaryRoot, name: &str, data: &[u8]) -> Result<(), AssetError> {
    let path = root
        .confine(name, PathIntent::Write)
        .map_err(|error| AssetError::new(error.to_string()))?;
    atomic_write_bytes(&path, data, 0o644).map_err(|error| AssetError::new(error.to_string()))
}

fn write_utf8(root: &TemporaryRoot, name: &str, text: &str) -> Result<(), AssetError> {
    let path = root
        .confine(name, PathIntent::Write)
        .map_err(|error| AssetError::new(error.to_string()))?;
    atomic_write_utf8(&path, text, 0o644).map_err(|error| AssetError::new(error.to_string()))
}

fn require_regular(path: &Path, label: &str, nonempty: bool) -> Result<fs::Metadata, AssetError> {
    let name = basename(path);
    let metadata = fs::symlink_metadata(path)
        .map_err(|_| AssetError::new(format!("{label} is not readable: {name}")))?;
    if metadata.file_type().is_symlink() {
        return Err(AssetError::new(format!(
            "{label} must not be a symlink: {name}"
        )));
    }
    if !metadata.is_file() {
        return Err(AssetError::new(format!(
            "{label} must be a regular file: {name}"
        )));
    }
    if nonempty && metadata.len() == 0 {
        return Err(AssetError::new(format!(
            "{label} must not be empty: {name}"
        )));
    }
    Ok(metadata)
}

fn basename(path: &Path) -> &str {
    path.file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("path")
}

fn load_json(path: &Path) -> Result<Value, AssetError> {
    let _ = require_regular(path, "JSON file", true)?;
    let text = fs::read_to_string(path)
        .map_err(|error| AssetError::new(format!("invalid JSON in {}: {error}", basename(path))))?;
    serde_json::from_str(&text)
        .map_err(|error| AssetError::new(format!("invalid JSON in {}: {error}", basename(path))))
}

fn object(value: Value, label: &str) -> Result<Map<String, Value>, AssetError> {
    match value {
        Value::Object(map) => Ok(map),
        _ => Err(AssetError::new(format!("{label} must be a JSON object"))),
    }
}

fn exact_keys(
    value: &Map<String, Value>,
    expected: &[&str],
    label: &str,
) -> Result<(), AssetError> {
    let actual: BTreeSet<&str> = value.keys().map(String::as_str).collect();
    let expected: BTreeSet<&str> = expected.iter().copied().collect();
    if actual == expected {
        return Ok(());
    }
    Err(AssetError::new(format!(
        "{label} keys mismatch: missing={:?}, unexpected={:?}",
        sorted_diff_str(&expected, &actual),
        sorted_diff_str(&actual, &expected)
    )))
}

fn string_field<'a>(
    value: &'a Map<String, Value>,
    key: &str,
    label: &str,
) -> Result<&'a str, AssetError> {
    match value.get(key) {
        Some(Value::String(text)) => Ok(text.as_str()),
        _ if key == "version" && label == "plugin manifest" => {
            Err(AssetError::new("plugin manifest version must be a string"))
        }
        _ => Err(AssetError::new(format!("{label} fields must be strings"))),
    }
}

fn sha256_hex(data: &[u8]) -> String {
    let digest = Sha256::digest(data);
    hex_lower(&digest)
}

fn sha256_file(path: &Path) -> Result<String, AssetError> {
    let _ = require_regular(path, "release asset", true)?;
    let data = fs::read(path)
        .map_err(|error| AssetError::new(format!("release asset is not readable: {error}")))?;
    Ok(sha256_hex(&data))
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

fn is_semver(value: &str) -> bool {
    let mut parts = value.split('.');
    let Some(major) = parts.next() else {
        return false;
    };
    let Some(minor) = parts.next() else {
        return false;
    };
    let Some(patch) = parts.next() else {
        return false;
    };
    parts.next().is_none()
        && [major, minor, patch].into_iter().all(|part| {
            !part.is_empty()
                && part.bytes().all(|byte| byte.is_ascii_digit())
                && !(part.len() > 1 && part.starts_with('0'))
        })
}

pub fn is_commit(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn sorted_diff(left: &BTreeSet<String>, right: &BTreeSet<String>) -> Vec<String> {
    left.difference(right).cloned().collect()
}

fn sorted_diff_str(left: &BTreeSet<&str>, right: &BTreeSet<&str>) -> Vec<String> {
    left.difference(right)
        .map(|value| (*value).to_owned())
        .collect()
}
