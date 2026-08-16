//! Recovery-path computation matching Python `dispatch_recovery.compute_recovery_paths`.

use std::path::{Path, PathBuf};

use super::helpers::{
    RecoveryParse, load_digest_map, parse_porcelain_z, rel_under_tmp, sha256_file,
    tmpdir_rel_in_repo, write_bytes_atomic,
};

/// Porcelain and digest inputs for recovery-path filtering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RecoveryPorcelainInputs {
    /// Pre-launch porcelain snapshot.
    pub prelaunch_porcelain: PathBuf,
    /// Post-launch porcelain snapshot.
    pub postlaunch_porcelain: PathBuf,
    /// Pre-launch content digests (`digest\\trel` lines).
    pub prelaunch_digests: PathBuf,
}

/// Compute recovery candidates and write a NUL-delimited path list to `out_file`.
///
/// Returns `true` when at least one candidate path was written.
///
/// # Errors
/// Returns an I/O error when the output file cannot be written.
pub fn compute_recovery_paths(
    repo_root: &Path,
    tmpdir: &Path,
    porcelain: &RecoveryPorcelainInputs,
    out_file: &Path,
) -> std::io::Result<bool> {
    let pre = parse_porcelain_z(&porcelain.prelaunch_porcelain);
    let post = parse_porcelain_z(&porcelain.postlaunch_porcelain);
    let digests = load_digest_map(&porcelain.prelaunch_digests);
    let tmp_rel = tmpdir_rel_in_repo(repo_root, tmpdir);
    let candidates =
        collect_recovery_candidates(repo_root, tmp_rel.as_deref(), &pre, &post, &digests);
    let mut data = Vec::new();
    for path in &candidates {
        data.extend(path.as_bytes());
        data.push(0);
    }
    write_bytes_atomic(out_file, &data)?;
    Ok(!candidates.is_empty())
}

fn recovery_path_included(
    status: &str,
    rel: &str,
    pre: &RecoveryParse,
    digests: &std::collections::BTreeMap<String, String>,
    repo_root: &Path,
) -> bool {
    if !pre.tuples.contains(&(status.to_owned(), rel.to_owned())) {
        return true;
    }
    if pre.paths.contains(rel) {
        return sha256_file(repo_root, rel) != digests.get(rel).map_or("", String::as_str);
    }
    false
}

fn collect_recovery_candidates(
    repo_root: &Path,
    tmp_rel: Option<&str>,
    pre: &RecoveryParse,
    post: &RecoveryParse,
    digests: &std::collections::BTreeMap<String, String>,
) -> Vec<String> {
    let mut ordered: Vec<(String, String)> = post.tuples.iter().cloned().collect();
    ordered.sort_by(|left, right| left.1.cmp(&right.1));
    let mut candidates = Vec::new();
    for (status, rel) in ordered {
        if rel_under_tmp(&rel, tmp_rel) {
            continue;
        }
        if recovery_path_included(&status, &rel, pre, digests, repo_root)
            && !candidates.iter().any(|existing| existing == &rel)
        {
            candidates.push(rel);
        }
    }
    candidates
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::implement::helpers::write_bytes_atomic;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn filters_tmpdir_and_unchanged_prelaunch_paths() {
        let root = TempDir::new().expect("temp");
        let repo = root.path().join("repo");
        let tmp = repo.join(".tmp");
        fs::create_dir_all(&tmp).expect("tmpdir");
        fs::write(repo.join("kept.txt"), b"new").expect("kept");
        fs::write(repo.join("same.txt"), b"same").expect("same");
        fs::write(tmp.join("noise.txt"), b"x").expect("noise");
        let pre = tmp.join("pre.nul");
        let post = tmp.join("post.nul");
        let digests = tmp.join("digests.txt");
        let out = tmp.join("out.nul");
        write_bytes_atomic(&pre, b" M same.txt\0?? kept.txt\0").expect("pre");
        write_bytes_atomic(
            &post,
            b" M same.txt\0?? kept.txt\0?? .tmp/noise.txt\0 M changed.txt\0",
        )
        .expect("post");
        fs::write(repo.join("changed.txt"), b"after").expect("changed");
        let digest = crate::implement::helpers::sha256_file(&repo, "same.txt");
        fs::write(&digests, format!("{digest}\tsame.txt\n")).expect("digests");
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
        assert!(ok);
        let text = String::from_utf8(fs::read(&out).expect("out")).expect("utf8");
        assert!(text.contains("changed.txt"));
        assert!(text.contains("kept.txt"));
        assert!(!text.contains("noise"));
        assert!(!text.contains("same.txt\0") && !text.ends_with("same.txt"));
    }
}
