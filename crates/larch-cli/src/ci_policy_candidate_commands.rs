//! Prepare and verify Rust-policy cache candidates from CI integration artifacts.
//!
//! Three commands cooperate to move a coverage-built executable into the trusted
//! main Rust-policy cache without ever letting an arbitrary ref grant publication
//! authority. `prepare-rust-integration-artifact` copies a coverage executable
//! and proves the bundle; `stage-rust-policy-candidate` re-verifies the bundle
//! and stages a candidate under a fixed provenance label; and
//! `promote-rust-policy-candidate` rewrites a verified merge-group bundle into
//! trusted main provenance only when the final SHA matches.
//!
//! The wire contract is byte-compatible with the retired Python owner: the same
//! bundle filenames, the same `"{checksum}  larch\n"` checksum grammar, the same
//! fixed provenance strings, and the same stable failure messages.

use std::{
    fs,
    io::Write as _,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

use clap::Args;
use sha2::{Digest as _, Sha256};
use wait_timeout::ChildExt as _;

const CURRENT_CHECKOUT_PROVENANCE: &str = "current-checkout";
const MERGE_GROUP_PROVENANCE: &str = "merge-group";
const TRUSTED_MAIN_PROVENANCE: &str = "refs/heads/main";
const VERSION_TIMEOUT: Duration = Duration::from_secs(10);
const HASH_CHUNK_BYTES: usize = 1024 * 1024;

/// A candidate artifact cannot safely be prepared or staged.
#[derive(Debug)]
struct CandidateError(String);

impl CandidateError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

type CandidateResult<T> = Result<T, CandidateError>;

/// The integrity and identity fields proven for one executable bundle.
struct VerifiedArtifact {
    sha256: String,
    version: String,
}

/// Reads a bundle executable's self-reported version string.
type VersionReader<'reader> = &'reader dyn Fn(&Path) -> CandidateResult<String>;

#[derive(Args)]
pub struct PrepareRustIntegrationArtifactArgs {
    #[arg(long)]
    coverage_larch: PathBuf,
    #[arg(long)]
    artifact_dir: PathBuf,
    #[arg(long)]
    source_sha: String,
    #[arg(long)]
    rust_inputs_sha256: String,
}

#[derive(Args)]
pub struct StageRustPolicyCandidateArgs {
    #[arg(long)]
    artifact_dir: PathBuf,
    #[arg(long)]
    policy_dir: PathBuf,
    #[arg(long)]
    event_name: String,
    /// The workflow ref; spelled explicitly so clap binds `--ref`, not `--ref-name`.
    #[arg(long = "ref")]
    ref_value: String,
    #[arg(long)]
    source_sha: String,
    #[arg(long)]
    rust_inputs_sha256: String,
}

#[derive(Args)]
pub struct PromoteRustPolicyCandidateArgs {
    #[arg(long)]
    artifact_dir: PathBuf,
    #[arg(long)]
    policy_dir: PathBuf,
    #[arg(long)]
    source_sha: String,
    #[arg(long)]
    rust_inputs_sha256: String,
}

/// CLI entrypoint for the coverage action's integration-artifact writer.
pub fn prepare_rust_integration_artifact(args: &PrepareRustIntegrationArtifactArgs) -> u8 {
    let outcome = prepare_integration_artifact(args, &read_binary_version);
    report(outcome, "Rust integration artifact preparation failed")
}

/// CLI entrypoint for rust-full's post-prune candidate stage.
pub fn stage_rust_policy_candidate(args: &StageRustPolicyCandidateArgs) -> u8 {
    let outcome = stage_policy_candidate(args, &read_binary_version);
    report(outcome, "Rust policy candidate staging failed")
}

/// CLI entrypoint for trusted main publication after artifact verification.
pub fn promote_rust_policy_candidate(args: &PromoteRustPolicyCandidateArgs) -> u8 {
    let outcome = promote_policy_candidate(args, &read_binary_version);
    report(outcome, "Rust policy candidate promotion failed")
}

fn report(outcome: CandidateResult<()>, prefix: &str) -> u8 {
    match outcome {
        Ok(()) => 0,
        Err(error) => {
            eprintln!("{prefix}: {}", error.0);
            1
        }
    }
}

/// Copy a coverage executable and prove the resulting integration artifact.
fn prepare_integration_artifact(
    args: &PrepareRustIntegrationArtifactArgs,
    version_reader: VersionReader,
) -> CandidateResult<()> {
    let source_sha = require_source_sha(&args.source_sha)?;
    let rust_inputs_sha256 = require_sha256(&args.rust_inputs_sha256, "Rust-input digest")?;
    require_regular_file(&args.coverage_larch, "coverage executable")?;
    require_executable(&args.coverage_larch, "coverage executable")?;
    let version = version_reader(&args.coverage_larch)?;

    replace_directory(&args.artifact_dir, "integration artifact directory")?;
    let artifact_larch = args.artifact_dir.join("larch");
    copy_executable(&args.coverage_larch, &artifact_larch)?;
    let checksum = sha256_file(&artifact_larch)?;
    write_text(
        &args.artifact_dir.join("larch.sha256"),
        &format!("{checksum}  larch\n"),
    )?;
    write_text(
        &args.artifact_dir.join("source-sha"),
        &format!("{source_sha}\n"),
    )?;
    write_text(
        &args.artifact_dir.join("rust-inputs-sha256"),
        &format!("{rust_inputs_sha256}\n"),
    )?;
    write_text(
        &args.artifact_dir.join("producer-ref"),
        &format!("{CURRENT_CHECKOUT_PROVENANCE}\n"),
    )?;
    write_text(&args.artifact_dir.join("version"), &version)?;
    verify_bundle(
        &args.artifact_dir,
        CURRENT_CHECKOUT_PROVENANCE,
        &source_sha,
        &rust_inputs_sha256,
        version_reader,
    )?;
    Ok(())
}

/// Stage and verify a cache candidate without granting publication authority.
fn stage_policy_candidate(
    args: &StageRustPolicyCandidateArgs,
    version_reader: VersionReader,
) -> CandidateResult<()> {
    let source_sha = require_source_sha(&args.source_sha)?;
    let rust_inputs_sha256 = require_sha256(&args.rust_inputs_sha256, "Rust-input digest")?;
    let artifact = verify_bundle(
        &args.artifact_dir,
        CURRENT_CHECKOUT_PROVENANCE,
        &source_sha,
        &rust_inputs_sha256,
        version_reader,
    )?;
    let producer_ref = candidate_producer_ref(&args.event_name, &args.ref_value);

    replace_directory(&args.policy_dir, "policy candidate directory")?;
    copy_executable(
        &args.artifact_dir.join("larch"),
        &args.policy_dir.join("larch"),
    )?;
    copy_regular_file(
        &args.artifact_dir.join("larch.sha256"),
        &args.policy_dir.join("larch.sha256"),
    )?;
    write_text(
        &args.policy_dir.join("producer-ref"),
        &format!("{producer_ref}\n"),
    )?;
    write_text(
        &args.policy_dir.join("source-sha"),
        &format!("{source_sha}\n"),
    )?;
    write_text(
        &args.policy_dir.join("rust-inputs-sha256"),
        &format!("{rust_inputs_sha256}\n"),
    )?;
    write_text(&args.policy_dir.join("version"), &artifact.version)?;
    let staged = verify_bundle(
        &args.policy_dir,
        &producer_ref,
        &source_sha,
        &rust_inputs_sha256,
        version_reader,
    )?;
    if staged.sha256 != artifact.sha256 {
        return Err(CandidateError::new(
            "staged policy executable checksum does not match integration artifact",
        ));
    }
    Ok(())
}

/// Rewrite verified merge-group provenance only after the final SHA matches.
fn promote_policy_candidate(
    args: &PromoteRustPolicyCandidateArgs,
    version_reader: VersionReader,
) -> CandidateResult<()> {
    let source_sha = require_source_sha(&args.source_sha)?;
    let rust_inputs_sha256 = require_sha256(&args.rust_inputs_sha256, "Rust-input digest")?;
    let artifact = verify_bundle(
        &args.artifact_dir,
        MERGE_GROUP_PROVENANCE,
        &source_sha,
        &rust_inputs_sha256,
        version_reader,
    )?;
    replace_directory(&args.policy_dir, "promoted policy directory")?;
    for filename in [
        "larch",
        "larch.sha256",
        "source-sha",
        "rust-inputs-sha256",
        "version",
    ] {
        let source = args.artifact_dir.join(filename);
        let destination = args.policy_dir.join(filename);
        if filename == "larch" {
            copy_executable(&source, &destination)?;
        } else {
            copy_regular_file(&source, &destination)?;
        }
    }
    write_text(
        &args.policy_dir.join("producer-ref"),
        &format!("{TRUSTED_MAIN_PROVENANCE}\n"),
    )?;
    let promoted = verify_bundle(
        &args.policy_dir,
        TRUSTED_MAIN_PROVENANCE,
        &source_sha,
        &rust_inputs_sha256,
        version_reader,
    )?;
    if promoted.sha256 != artifact.sha256 {
        return Err(CandidateError::new(
            "promoted policy executable checksum does not match merge-group artifact",
        ));
    }
    Ok(())
}

/// Return a fixed provenance label; arbitrary refs never enter the cache.
fn candidate_producer_ref(event_name: &str, ref_name: &str) -> String {
    if event_name == "push" && ref_name == TRUSTED_MAIN_PROVENANCE {
        return TRUSTED_MAIN_PROVENANCE.to_owned();
    }
    if event_name == "merge_group" {
        return MERGE_GROUP_PROVENANCE.to_owned();
    }
    CURRENT_CHECKOUT_PROVENANCE.to_owned()
}

fn verify_bundle(
    directory: &Path,
    expected_producer_ref: &str,
    expected_source_sha: &str,
    expected_rust_inputs_sha256: &str,
    version_reader: VersionReader,
) -> CandidateResult<VerifiedArtifact> {
    require_regular_directory(directory, "executable bundle directory")?;
    let larch = directory.join("larch");
    require_regular_file(&larch, "bundle executable")?;
    require_executable(&larch, "bundle executable")?;
    let checksum = read_checksum(&directory.join("larch.sha256"))?;
    let actual_checksum = sha256_file(&larch)?;
    if checksum != actual_checksum {
        return Err(CandidateError::new(
            "bundle executable checksum verification failed",
        ));
    }
    require_metadata(
        &directory.join("producer-ref"),
        expected_producer_ref,
        "producer provenance",
    )?;
    require_metadata(
        &directory.join("source-sha"),
        expected_source_sha,
        "source SHA",
    )?;
    require_metadata(
        &directory.join("rust-inputs-sha256"),
        expected_rust_inputs_sha256,
        "Rust-input digest",
    )?;
    let version = read_text(&directory.join("version"), "bundle version")?;
    if version.trim().is_empty() {
        return Err(CandidateError::new("bundle version is empty"));
    }
    if version_reader(&larch)? != version {
        return Err(CandidateError::new(
            "bundle executable version verification failed",
        ));
    }
    Ok(VerifiedArtifact {
        sha256: checksum,
        version,
    })
}

fn require_source_sha(value: &str) -> CandidateResult<String> {
    let length = value.len();
    if (length == 40 || length == 64)
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Ok(value.to_owned());
    }
    Err(CandidateError::new("source SHA is invalid"))
}

fn require_sha256(value: &str, name: &str) -> CandidateResult<String> {
    if value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Ok(value.to_owned());
    }
    Err(CandidateError::new(format!("{name} is invalid")))
}

fn replace_directory(path: &Path, label: &str) -> CandidateResult<()> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .ok_or_else(|| CandidateError::new(format!("{label} parent is unavailable")))?;
    require_regular_directory(parent, &format!("{label} parent"))?;
    let metadata = fs::symlink_metadata(path);
    if let Ok(metadata) = metadata {
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(CandidateError::new(format!(
                "{label} is not a regular directory"
            )));
        }
        fs::remove_dir_all(path)
            .map_err(|_| CandidateError::new(format!("could not remove {label}")))?;
    }
    fs::create_dir(path).map_err(|_| CandidateError::new(format!("could not create {label}")))?;
    fs::set_permissions(path, fs::Permissions::from_mode(0o755))
        .map_err(|_| CandidateError::new(format!("could not create {label}")))?;
    Ok(())
}

fn require_regular_directory(path: &Path, label: &str) -> CandidateResult<()> {
    let metadata = lstat(path, label)?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(CandidateError::new(format!(
            "{label} is not a regular directory"
        )));
    }
    Ok(())
}

fn require_regular_file(path: &Path, label: &str) -> CandidateResult<()> {
    let metadata = lstat(path, label)?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(CandidateError::new(format!(
            "{label} is not a regular file"
        )));
    }
    Ok(())
}

fn lstat(path: &Path, label: &str) -> CandidateResult<fs::Metadata> {
    fs::symlink_metadata(path).map_err(|_| CandidateError::new(format!("{label} is unavailable")))
}

fn require_executable(path: &Path, label: &str) -> CandidateResult<()> {
    let metadata = lstat(path, label)?;
    if metadata.permissions().mode() & 0o111 == 0 {
        return Err(CandidateError::new(format!("{label} is not executable")));
    }
    Ok(())
}

fn copy_executable(source: &Path, destination: &Path) -> CandidateResult<()> {
    copy_regular_file(source, destination)?;
    fs::set_permissions(destination, fs::Permissions::from_mode(0o755))
        .map_err(|_| CandidateError::new("could not mark executable bundle file executable"))?;
    Ok(())
}

fn copy_regular_file(source: &Path, destination: &Path) -> CandidateResult<()> {
    require_regular_file(source, "source bundle file")?;
    let bytes = fs::read(source).map_err(|_| CandidateError::new("could not copy bundle file"))?;
    fs::write(destination, &bytes)
        .map_err(|_| CandidateError::new("could not copy bundle file"))?;
    Ok(())
}

fn write_text(path: &Path, value: &str) -> CandidateResult<()> {
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|_| CandidateError::new("could not write bundle metadata"))?;
    file.write_all(value.as_bytes())
        .map_err(|_| CandidateError::new("could not write bundle metadata"))?;
    Ok(())
}

fn read_checksum(path: &Path) -> CandidateResult<String> {
    let value = read_text(path, "bundle checksum")?;
    let checksum = value
        .strip_suffix("  larch\n")
        .filter(|checksum| is_sha256_hex(checksum))
        .ok_or_else(|| CandidateError::new("bundle checksum has an invalid format"))?;
    Ok(checksum.to_owned())
}

fn is_sha256_hex(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn require_metadata(path: &Path, expected: &str, label: &str) -> CandidateResult<()> {
    if read_text(path, label)? != format!("{expected}\n") {
        return Err(CandidateError::new(format!("{label} verification failed")));
    }
    Ok(())
}

fn read_text(path: &Path, label: &str) -> CandidateResult<String> {
    require_regular_file(path, label)?;
    let bytes =
        fs::read(path).map_err(|_| CandidateError::new(format!("could not read {label}")))?;
    String::from_utf8(bytes).map_err(|_| CandidateError::new(format!("could not read {label}")))
}

fn sha256_file(path: &Path) -> CandidateResult<String> {
    require_regular_file(path, "bundle executable")?;
    let file = fs::File::open(path)
        .map_err(|_| CandidateError::new("could not hash bundle executable"))?;
    let mut reader = std::io::BufReader::with_capacity(HASH_CHUNK_BYTES, file);
    let mut hasher = Sha256::new();
    std::io::copy(&mut reader, &mut hasher)
        .map_err(|_| CandidateError::new("could not hash bundle executable"))?;
    Ok(format!("{:x}", hasher.finalize()))
}

fn read_binary_version(binary: &Path) -> CandidateResult<String> {
    let mut child = Command::new(binary) // lint-subprocess-via-runner: ok reads a caller-supplied bundle executable's own --version, mirroring the retired Python _read_binary_version; not a plugin-root larch program
        .arg("--version")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map_err(|_| CandidateError::new("could not read bundle executable version"))?;
    let Some(status) = child
        .wait_timeout(VERSION_TIMEOUT)
        .map_err(|_| CandidateError::new("could not read bundle executable version"))?
    else {
        let _ = child.kill();
        let _ = child.wait();
        return Err(CandidateError::new(
            "could not read bundle executable version",
        ));
    };
    let mut stdout = Vec::new();
    if let Some(mut handle) = child.stdout.take() {
        use std::io::Read as _;
        handle
            .read_to_end(&mut stdout)
            .map_err(|_| CandidateError::new("could not read bundle executable version"))?;
    }
    let stdout = String::from_utf8_lossy(&stdout).into_owned();
    if !status.success() || stdout.trim().is_empty() {
        return Err(CandidateError::new(
            "bundle executable version command failed",
        ));
    }
    Ok(stdout)
}

#[cfg(test)]
mod tests {
    use super::{
        CURRENT_CHECKOUT_PROVENANCE, MERGE_GROUP_PROVENANCE, PrepareRustIntegrationArtifactArgs,
        PromoteRustPolicyCandidateArgs, StageRustPolicyCandidateArgs, TRUSTED_MAIN_PROVENANCE,
        candidate_producer_ref, prepare_integration_artifact, promote_policy_candidate,
        stage_policy_candidate,
    };
    use std::{fs, os::unix::fs::PermissionsExt as _, path::Path};
    use tempfile::TempDir;

    const SOURCE_SHA: &str = "0123456789abcdef0123456789abcdef01234567";
    const INPUTS_SHA: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    const VERSION: &str = "larch 57.0.4\n";

    #[allow(clippy::unnecessary_wraps)]
    fn fixed_version(_: &Path) -> Result<String, super::CandidateError> {
        Ok(VERSION.to_owned())
    }

    fn write_coverage_larch(root: &Path) -> std::path::PathBuf {
        let coverage = root.join("coverage-larch");
        fs::write(&coverage, b"an executable body").expect("coverage body");
        fs::set_permissions(&coverage, fs::Permissions::from_mode(0o755)).expect("coverage mode");
        coverage
    }

    #[test]
    fn prepare_then_stage_then_promote_round_trips() {
        let root = TempDir::new().expect("root");
        let coverage = write_coverage_larch(root.path());
        let artifact_dir = root.path().join("artifact");
        let prepare = PrepareRustIntegrationArtifactArgs {
            coverage_larch: coverage,
            artifact_dir: artifact_dir.clone(),
            source_sha: SOURCE_SHA.to_owned(),
            rust_inputs_sha256: INPUTS_SHA.to_owned(),
        };
        prepare_integration_artifact(&prepare, &fixed_version).expect("prepare");

        assert_eq!(
            fs::read_to_string(artifact_dir.join("producer-ref")).expect("producer"),
            format!("{CURRENT_CHECKOUT_PROVENANCE}\n")
        );
        assert_eq!(
            fs::read_to_string(artifact_dir.join("version")).expect("version"),
            VERSION
        );
        let checksum_line =
            fs::read_to_string(artifact_dir.join("larch.sha256")).expect("checksum");
        assert!(checksum_line.ends_with("  larch\n"));

        let policy_dir = root.path().join("policy");
        let stage = StageRustPolicyCandidateArgs {
            artifact_dir,
            policy_dir: policy_dir.clone(),
            event_name: "merge_group".to_owned(),
            ref_value: "refs/heads/gh-readonly-queue/main/x".to_owned(),
            source_sha: SOURCE_SHA.to_owned(),
            rust_inputs_sha256: INPUTS_SHA.to_owned(),
        };
        stage_policy_candidate(&stage, &fixed_version).expect("stage");
        assert_eq!(
            fs::read_to_string(policy_dir.join("producer-ref")).expect("staged provenance"),
            format!("{MERGE_GROUP_PROVENANCE}\n")
        );

        let promoted_dir = root.path().join("trusted");
        let promote = PromoteRustPolicyCandidateArgs {
            artifact_dir: policy_dir,
            policy_dir: promoted_dir.clone(),
            source_sha: SOURCE_SHA.to_owned(),
            rust_inputs_sha256: INPUTS_SHA.to_owned(),
        };
        promote_policy_candidate(&promote, &fixed_version).expect("promote");
        assert_eq!(
            fs::read_to_string(promoted_dir.join("producer-ref")).expect("promoted provenance"),
            format!("{TRUSTED_MAIN_PROVENANCE}\n")
        );
    }

    #[test]
    fn provenance_never_trusts_an_arbitrary_ref() {
        assert_eq!(
            candidate_producer_ref("push", "refs/heads/main"),
            TRUSTED_MAIN_PROVENANCE
        );
        assert_eq!(
            candidate_producer_ref("push", "refs/heads/feature"),
            CURRENT_CHECKOUT_PROVENANCE
        );
        assert_eq!(
            candidate_producer_ref("merge_group", "refs/heads/anything"),
            MERGE_GROUP_PROVENANCE
        );
        assert_eq!(
            candidate_producer_ref("pull_request", "refs/heads/main"),
            CURRENT_CHECKOUT_PROVENANCE
        );
    }

    #[test]
    fn invalid_source_sha_fails_before_touching_the_filesystem() {
        let root = TempDir::new().expect("root");
        let coverage = write_coverage_larch(root.path());
        let prepare = PrepareRustIntegrationArtifactArgs {
            coverage_larch: coverage,
            artifact_dir: root.path().join("artifact"),
            source_sha: "not-a-sha".to_owned(),
            rust_inputs_sha256: INPUTS_SHA.to_owned(),
        };
        let error =
            prepare_integration_artifact(&prepare, &fixed_version).expect_err("invalid source sha");
        assert_eq!(error.0, "source SHA is invalid");
        assert!(!root.path().join("artifact").exists());
    }

    #[test]
    fn stage_rejects_a_forged_bundle_checksum() {
        let root = TempDir::new().expect("root");
        let coverage = write_coverage_larch(root.path());
        let artifact_dir = root.path().join("artifact");
        let prepare = PrepareRustIntegrationArtifactArgs {
            coverage_larch: coverage,
            artifact_dir: artifact_dir.clone(),
            source_sha: SOURCE_SHA.to_owned(),
            rust_inputs_sha256: INPUTS_SHA.to_owned(),
        };
        prepare_integration_artifact(&prepare, &fixed_version).expect("prepare");
        fs::write(artifact_dir.join("larch"), b"tampered body").expect("tamper");

        let stage = StageRustPolicyCandidateArgs {
            artifact_dir,
            policy_dir: root.path().join("policy"),
            event_name: "merge_group".to_owned(),
            ref_value: "refs/heads/x".to_owned(),
            source_sha: SOURCE_SHA.to_owned(),
            rust_inputs_sha256: INPUTS_SHA.to_owned(),
        };
        let error = stage_policy_candidate(&stage, &fixed_version).expect_err("tampered");
        assert_eq!(error.0, "bundle executable checksum verification failed");
    }
}
