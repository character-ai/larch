//! Lean dispatch manifest state and pure validation helpers.

use std::path::{Path, PathBuf};

/// Mutable dispatch workspace state shared by later Step 2 cutovers.
#[derive(Clone, Debug)]
pub struct DispatchState {
    pub repo_root: PathBuf,
    pub tmpdir: PathBuf,
    pub plan_file: PathBuf,
    pub feature_file: PathBuf,
    pub coder: String,
    pub cursor_present: String,
    pub cursor_binary_found: String,
    pub codex_binary_found: String,
    pub answers_file: Option<PathBuf>,
    pub plugin_root: PathBuf,
    pub tool_tag: String,
    pub manifest_path: PathBuf,
    pub manifest_raw_path: PathBuf,
    pub qa_pending_path: PathBuf,
    pub transcript_path: PathBuf,
    pub sidecar_log: PathBuf,
    pub scout_coder_manifest: PathBuf,
    pub launch_scout_manifest: PathBuf,
    pub external_scout_marker: PathBuf,
    pub baseline_file: PathBuf,
    pub prelaunch_porcelain: PathBuf,
    pub postlaunch_porcelain: PathBuf,
    pub prelaunch_digests: PathBuf,
    pub prelaunch_index_flag: PathBuf,
    pub recovery_paths_file: PathBuf,
    pub resume_count_file: PathBuf,
    pub completion_retry_state_file: PathBuf,
    pub completion_retry_feedback_file: PathBuf,
    pub spawn_branch_file: PathBuf,
    pub spawn_coder_file: PathBuf,
    pub runtime_failure_token: String,
    pub bailed_no_reason_token: String,
    pub requires_head_unchanged: bool,
    pub nonzero_exit_warn_token: String,
    pub difficulty: String,
    pub baseline_sha: String,
    pub spawn_branch: String,
    pub scout_status: String,
}

/// Paths cleared when external scout state is discarded.
#[must_use]
pub fn clear_external_scout_paths(tmpdir: &Path) -> Vec<PathBuf> {
    [
        "scout-coder-manifest.json",
        "step2-external-scout-eligible.txt",
        "step2-scout-coder-status.env",
        "scout-coder-manifest.raw.json",
        ".producer-scout-warning-logged",
        "codex-step2-out/scout-coder-manifest.json",
        "cursor-step2-out/scout-coder-manifest.json",
    ]
    .into_iter()
    .map(|rel| tmpdir.join(rel))
    .collect()
}

/// True when `rel` equals a submodule root or lives under one.
#[must_use]
pub fn path_under_submodule(rel: &str, roots: impl IntoIterator<Item = impl AsRef<str>>) -> bool {
    roots.into_iter().any(|root| {
        let root = root.as_ref();
        !root.is_empty() && (rel == root || rel.starts_with(&format!("{root}/")))
    })
}

/// True for the legacy `{status, summary, checks}` manifest fingerprint.
#[must_use]
pub fn manifest_legacy_fingerprint(obj: &serde_json::Value) -> bool {
    let Some(map) = obj.as_object() else {
        return false;
    };
    if map.contains_key("schema_version") {
        return false;
    }
    map.keys()
        .all(|key| matches!(key.as_str(), "status" | "summary" | "checks"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn submodule_prefix_matching() {
        assert!(path_under_submodule("vendor/foo", ["vendor"]));
        assert!(!path_under_submodule("vendored/x", ["vendor"]));
    }

    #[test]
    fn legacy_fingerprint_requires_closed_key_set() {
        assert!(manifest_legacy_fingerprint(&json!({"status": "complete"})));
        assert!(!manifest_legacy_fingerprint(
            &json!({"status": "complete", "schema_version": 1})
        ));
    }
}
