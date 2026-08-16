//! Recovery-path porcelain filtering contracts.

use std::fs;

use larch_core::{
    RecoveryPorcelainInputs, compute_recovery_paths, parse_porcelain_z, resolve_tmpdir_path,
    write_bytes_atomic,
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
    assert!(parsed.tuples.contains(&("D ".to_owned(), "old.txt".to_owned())));
}
