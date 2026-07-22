//! Black-box coverage for release asset construction and validation.

use std::{
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const VERSION: &str = "1.2.3";
const TAG: &str = "v1.2.3";
const SOURCE_COMMIT: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const TARGETS: [&str; 1] = ["aarch64-apple-darwin"];

#[test]
fn package_matches_golden_bytes_and_is_deterministic() {
    let root = TempDir::new().expect("temp");
    let (binary, license) = write_inputs(root.path());
    let first = root.path().join("first");
    let second = root.path().join("second");
    for output in [&first, &second] {
        larch()
            .args(package_args(&binary, &license, output, TARGETS[0]))
            .assert()
            .success();
    }
    let archive = first.join(format!("larch-v{VERSION}-{}.tar.gz", TARGETS[0]));
    let fragment = first.join(format!("larch-v{VERSION}-{}.asset.json", TARGETS[0]));
    assert_eq!(fs::read(&archive).expect("archive"), golden_archive_bytes());
    assert_eq!(
        fs::read(&fragment).expect("fragment"),
        fs::read(fixture("release-asset-golden.asset.json")).expect("golden")
    );
    assert_eq!(
        fs::read(&archive).expect("first"),
        fs::read(second.join(format!("larch-v{VERSION}-{}.tar.gz", TARGETS[0]))).expect("second")
    );
}

#[test]
fn package_rejects_wrong_version_and_unsupported_target() {
    let root = TempDir::new().expect("temp");
    let license = write_license(root.path());
    let binary = write_binary(root.path(), "9.9.9");
    larch()
        .args(package_args(
            &binary,
            &license,
            &root.path().join("out"),
            TARGETS[0],
        ))
        .assert()
        .failure()
        .stderr(predicates::str::contains("requested version"));
    let (binary, license) = write_inputs(root.path());
    larch()
        .args(package_args(
            &binary,
            &license,
            &root.path().join("bad-target"),
            "wasm32-unknown-unknown",
        ))
        .assert()
        .failure()
        .stderr(predicates::str::contains("unsupported release target"));
}

#[test]
fn collect_emits_exact_validated_set_and_rejects_failures() {
    let root = TempDir::new().expect("temp");
    let (incoming, license) = package_all(root.path());
    let output = root.path().join("release");
    larch()
        .args(collect_args(&incoming, &output, &license))
        .assert()
        .success();
    assert_eq!(
        fs::read(output.join(format!("larch-v{VERSION}-manifest.json"))).expect("manifest"),
        fs::read(fixture("release-asset-golden-manifest.json")).expect("golden manifest")
    );
    assert_eq!(
        fs::read_to_string(output.join(format!("larch-v{VERSION}-SHA256SUMS"))).expect("sums"),
        fs::read_to_string(fixture("release-asset-golden-SHA256SUMS")).expect("golden sums")
    );

    let missing = root.path().join("missing");
    fs::create_dir_all(&missing).expect("missing root");
    copy_tree(&incoming, &missing);
    fs::remove_file(
        missing
            .join(format!("build-{}", TARGETS[0]))
            .join(format!("larch-v{VERSION}-{}.asset.json", TARGETS[0])),
    )
    .expect("remove fragment");
    larch()
        .args(collect_args(
            &missing,
            &root.path().join("missing-out"),
            &license,
        ))
        .assert()
        .failure()
        .stderr(predicates::str::contains("input asset set mismatch"));

    let duplicate = root.path().join("duplicate");
    fs::create_dir_all(&duplicate).expect("duplicate root");
    copy_tree(&incoming, &duplicate);
    let dup_dir = duplicate.join("dup");
    fs::create_dir_all(&dup_dir).expect("dup dir");
    fs::copy(
        duplicate
            .join(format!("build-{}", TARGETS[0]))
            .join(format!("larch-v{VERSION}-{}.asset.json", TARGETS[0])),
        dup_dir.join(format!("larch-v{VERSION}-{}.asset.json", TARGETS[0])),
    )
    .expect("copy duplicate");
    larch()
        .args(collect_args(
            &duplicate,
            &root.path().join("duplicate-out"),
            &license,
        ))
        .assert()
        .failure()
        .stderr(predicates::str::contains("duplicate asset input"));
}

#[test]
fn collect_rejects_digest_and_gzip_mismatches() {
    let root = TempDir::new().expect("temp");
    let (incoming, license) = package_all(root.path());

    let tampered = root.path().join("tampered");
    copy_tree(&incoming, &tampered);
    let archive = tampered
        .join(format!("build-{}", TARGETS[0]))
        .join(format!("larch-v{VERSION}-{}.tar.gz", TARGETS[0]));
    let mut data = fs::read(&archive).expect("archive");
    data.push(b'x');
    fs::write(&archive, data).expect("tamper");
    larch()
        .args(collect_args(
            &tampered,
            &root.path().join("tampered-out"),
            &license,
        ))
        .assert()
        .failure()
        .stderr(predicates::str::contains("size mismatch"));

    let gzip = root.path().join("gzip");
    copy_tree(&incoming, &gzip);
    let archive = gzip
        .join(format!("build-{}", TARGETS[0]))
        .join(format!("larch-v{VERSION}-{}.tar.gz", TARGETS[0]));
    let mut data = fs::read(&archive).expect("archive");
    data[9] = 3;
    fs::write(&archive, &data).expect("rewrite");
    let fragment_path = gzip
        .join(format!("build-{}", TARGETS[0]))
        .join(format!("larch-v{VERSION}-{}.asset.json", TARGETS[0]));
    let mut fragment: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&fragment_path).expect("fragment")).expect("json");
    fragment["asset"]["sha256"] = serde_json::Value::String(hex_sha256(&data));
    fs::write(
        &fragment_path,
        format!(
            "{}\n",
            serde_json::to_string_pretty(&fragment).expect("write")
        ),
    )
    .expect("rewrite fragment");
    larch()
        .args(collect_args(&gzip, &root.path().join("gzip-out"), &license))
        .assert()
        .failure()
        .stderr(predicates::str::contains(
            "gzip metadata is not deterministic",
        ));
}

#[test]
fn validate_rejects_manifest_checksum_and_extra_assets() {
    let root = TempDir::new().expect("temp");
    let (incoming, license) = package_all(root.path());
    let output = root.path().join("release");
    larch()
        .args(collect_args(&incoming, &output, &license))
        .assert()
        .success();

    let mut manifest: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(output.join(format!("larch-v{VERSION}-manifest.json"))).expect("read"),
    )
    .expect("json");
    manifest["tag"] = serde_json::Value::String("v9.9.9".into());
    fs::write(
        output.join(format!("larch-v{VERSION}-manifest.json")),
        format!(
            "{}\n",
            serde_json::to_string_pretty(&manifest).expect("write")
        ),
    )
    .expect("rewrite");
    larch()
        .args(validate_args(&output, &license))
        .assert()
        .failure()
        .stderr(predicates::str::contains("manifest identity mismatch"));

    let clean = root.path().join("clean");
    larch()
        .args(collect_args(&incoming, &clean, &license))
        .assert()
        .success();
    fs::write(
        clean.join(format!("larch-v{VERSION}-SHA256SUMS")),
        format!("{}  wrong\n", "0".repeat(64)),
    )
    .expect("checksum");
    larch()
        .args(validate_args(&clean, &license))
        .assert()
        .failure()
        .stderr(predicates::str::contains("checksum file contents mismatch"));

    let extra = root.path().join("extra");
    larch()
        .args(collect_args(&incoming, &extra, &license))
        .assert()
        .success();
    fs::write(extra.join("extra"), "not allowed\n").expect("extra");
    larch()
        .args(validate_args(&extra, &license))
        .assert()
        .failure()
        .stderr(predicates::str::contains("final asset set mismatch"));
}

#[test]
fn asset_candidate_requires_matching_versions() {
    let root = TempDir::new().expect("temp");
    fs::create_dir(root.path().join(".claude-plugin")).expect("plugin dir");
    fs::write(
        root.path().join(".claude-plugin/plugin.json"),
        "{\"version\":\"1.2.3\"}\n",
    )
    .expect("plugin");
    fs::write(
        root.path().join("Cargo.toml"),
        "[workspace]\n[workspace.package]\nversion = \"1.2.3\"\n",
    )
    .expect("cargo");
    larch()
        .args([
            "release",
            "asset-candidate",
            "--repo-root",
            root.path().to_str().expect("utf8"),
            "--tag",
            TAG,
            "--source-commit",
            SOURCE_COMMIT,
        ])
        .assert()
        .success()
        .stdout(format!(
            "VERSION={VERSION}\nSOURCE_COMMIT={SOURCE_COMMIT}\n"
        ));

    fs::write(
        root.path().join("Cargo.toml"),
        "[workspace]\n[workspace.package]\nversion = \"1.2.4\"\n",
    )
    .expect("cargo mismatch");
    larch()
        .args([
            "release",
            "asset-candidate",
            "--repo-root",
            root.path().to_str().expect("utf8"),
            "--tag",
            TAG,
            "--source-commit",
            SOURCE_COMMIT,
        ])
        .assert()
        .failure()
        .stderr(predicates::str::contains("does not match plugin version"));
}

fn package_all(root: &Path) -> (PathBuf, PathBuf) {
    let (binary, license) = write_inputs(root);
    let incoming = root.join("incoming");
    for target in TARGETS {
        let output = incoming.join(format!("build-{target}"));
        larch()
            .args(package_args(&binary, &license, &output, target))
            .assert()
            .success();
    }
    (incoming, license)
}

fn write_inputs(root: &Path) -> (PathBuf, PathBuf) {
    (write_binary(root, VERSION), write_license(root))
}

fn write_license(root: &Path) -> PathBuf {
    let path = root.join("LICENSE");
    fs::write(&path, "test license\n").expect("license");
    path
}

fn write_binary(root: &Path, version: &str) -> PathBuf {
    let path = root.join("larch");
    fs::write(
        &path,
        format!("#!/bin/sh\n[ \"$1\" = --version ] || exit 2\nprintf 'larch {version}\\n'\n"),
    )
    .expect("binary");
    let mut permissions = fs::metadata(&path).expect("meta").permissions();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        permissions.set_mode(0o755);
    }
    fs::set_permissions(&path, permissions).expect("chmod");
    path
}

fn package_args(binary: &Path, license: &Path, output: &Path, target: &str) -> Vec<String> {
    vec![
        "release".into(),
        "package-asset".into(),
        "--version".into(),
        VERSION.into(),
        "--tag".into(),
        TAG.into(),
        "--source-commit".into(),
        SOURCE_COMMIT.into(),
        "--target".into(),
        target.into(),
        "--binary".into(),
        binary.display().to_string(),
        "--license".into(),
        license.display().to_string(),
        "--output-dir".into(),
        output.display().to_string(),
    ]
}

fn collect_args(input: &Path, output: &Path, license: &Path) -> Vec<String> {
    vec![
        "release".into(),
        "collect-assets".into(),
        "--version".into(),
        VERSION.into(),
        "--tag".into(),
        TAG.into(),
        "--source-commit".into(),
        SOURCE_COMMIT.into(),
        "--input-dir".into(),
        input.display().to_string(),
        "--output-dir".into(),
        output.display().to_string(),
        "--license".into(),
        license.display().to_string(),
    ]
}

fn validate_args(asset_dir: &Path, license: &Path) -> Vec<String> {
    vec![
        "release".into(),
        "validate-assets".into(),
        "--version".into(),
        VERSION.into(),
        "--tag".into(),
        TAG.into(),
        "--source-commit".into(),
        SOURCE_COMMIT.into(),
        "--asset-dir".into(),
        asset_dir.display().to_string(),
        "--license".into(),
        license.display().to_string(),
    ]
}

fn copy_tree(source: &Path, destination: &Path) {
    for entry in walkdir(source) {
        let relative = entry.strip_prefix(source).expect("relative");
        let target = destination.join(relative);
        if entry.is_dir() {
            fs::create_dir_all(&target).expect("dir");
        } else {
            if let Some(parent) = target.parent() {
                fs::create_dir_all(parent).expect("parent");
            }
            fs::copy(&entry, &target).expect("copy");
        }
    }
}

fn walkdir(root: &Path) -> Vec<PathBuf> {
    let mut stack = vec![root.to_path_buf()];
    let mut out = Vec::new();
    while let Some(path) = stack.pop() {
        out.push(path.clone());
        if path.is_dir() {
            for entry in fs::read_dir(&path).expect("read") {
                stack.push(entry.expect("entry").path());
            }
        }
    }
    out
}

fn hex_sha256(data: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let digest = Sha256::digest(data);
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name)
}

fn golden_archive_bytes() -> Vec<u8> {
    let hex = fs::read_to_string(fixture("release-asset-golden.tar.gz.hex")).expect("golden hex");
    let hex = hex.trim();
    (0..hex.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&hex[index..index + 2], 16).expect("hex"))
        .collect()
}

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary")
}
