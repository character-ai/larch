//! Recovery-path porcelain filtering contracts.

use std::{collections::BTreeMap, fs};

use larch_core::{
    RecoveryPorcelainInputs, compute_recovery_paths, load_digest_map, parse_porcelain_z,
    rel_under_tmp, resolve_tmpdir_path, sha256_file, tmpdir_rel_in_repo, write_bytes_atomic,
    write_digest_map,
};
use tempfile::TempDir;

#[test]
fn resolve_tmpdir_path_rebases_absolute_outside_tmpdir() {
    let root = TempDir::new().expect("temp");
    let tmp = root.path().join("impl");
    fs::create_dir_all(&tmp).expect("tmpdir");
    let resolved = resolve_tmpdir_path(&tmp, "/elsewhere/step2-out.nul", "default.nul");
    assert_eq!(resolved, tmp.join("elsewhere/step2-out.nul"));
}

#[test]
fn empty_candidates_write_empty_nul_file() {
    let root = TempDir::new().expect("temp");
    let repo = root.path().join("repo");
    let tmp = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmp).expect("tmp");
    let pre = tmp.join("pre.nul");
    let post = tmp.join("post.nul");
    let digests = tmp.join("digests.txt");
    let out = tmp.join("out.nul");
    write_bytes_atomic(&pre, b"").expect("pre");
    write_bytes_atomic(&post, b"").expect("post");
    fs::write(&digests, "").expect("digests");
    let ok = compute_recovery_paths(
        &repo,
        &tmp,
        &RecoveryPorcelainInputs {
            prelaunch_porcelain: pre,
            postlaunch_porcelain: post,
            prelaunch_digests: digests,
        },
        &out,
    )
    .expect("compute");
    assert!(!ok);
    assert_eq!(fs::read(&out).expect("out"), b"");
}

#[test]
fn rename_source_is_parsed_as_delete() {
    let root = TempDir::new().expect("temp");
    let path = root.path().join("p.nul");
    write_bytes_atomic(&path, b"R  new.txt\0old.txt\0").expect("write");
    let parsed = parse_porcelain_z(&path);
    assert!(parsed.paths.contains("old.txt"));
    assert!(
        parsed
            .tuples
            .contains(&("D ".to_owned(), "old.txt".to_owned()))
    );
}

#[test]
fn resolve_tmpdir_path_keeps_relative_and_inside_absolute() {
    let root = TempDir::new().expect("temp");
    let tmp = root.path().join("impl");
    fs::create_dir_all(&tmp).expect("tmpdir");
    assert_eq!(
        resolve_tmpdir_path(&tmp, "", "default.nul"),
        tmp.join("default.nul")
    );
    assert_eq!(
        resolve_tmpdir_path(&tmp, "nested/out.nul", "default.nul"),
        tmp.join("nested/out.nul")
    );
    let inside = tmp.join("inside.nul");
    assert_eq!(
        resolve_tmpdir_path(&tmp, inside.to_str().expect("utf8"), "default.nul"),
        inside
    );
}

#[test]
fn digest_map_round_trip_and_sha() {
    let root = TempDir::new().expect("temp");
    let repo = root.path().join("repo");
    fs::create_dir_all(&repo).expect("repo");
    fs::write(repo.join("a.txt"), b"abc").expect("file");
    let digests_path = root.path().join("digests.txt");
    let mut digests = BTreeMap::new();
    digests.insert("a.txt".to_owned(), sha256_file(&repo, "a.txt"));
    write_digest_map(&digests_path, &digests).expect("write");
    let loaded = load_digest_map(&digests_path);
    assert_eq!(loaded.get("a.txt"), digests.get("a.txt"));
    assert_eq!(sha256_file(&repo, "missing.txt"), "missing");
}

#[test]
fn tmpdir_rel_and_under_tmp_helpers() {
    let root = TempDir::new().expect("temp");
    let repo = root.path().join("repo");
    let tmp = repo.join(".tmp");
    fs::create_dir_all(&tmp).expect("tmpdir");
    let rel = tmpdir_rel_in_repo(&repo, &tmp).expect("rel");
    assert_eq!(rel, ".tmp");
    assert!(rel_under_tmp(".tmp/noise", Some(".tmp")));
    assert!(rel_under_tmp(".tmp", Some(".tmp")));
    assert!(!rel_under_tmp("outside", Some(".tmp")));
    assert!(!rel_under_tmp("outside", None));
}
