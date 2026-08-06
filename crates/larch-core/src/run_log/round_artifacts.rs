//! Round-artifact inclusion tables and staging transforms.
//!
//! Ported from the `_ROUND_*` tables and `_stage_round_artifact` in
//! `larch.report.run_log_batch`.

use crate::redaction::{redact, redact_secrets};

use super::batch::normalize_run_log_text;

const VOTE_OUTPUT_TRUNCATE_BYTES: usize = 2048;

/// Round-local files that never reach the durable round directory.
const SIDECAR_FILES: &[&str] = &[
    "review-tally.env",
    "collect-agent-results.log",
    "review-summary.json",
    "coder.env",
    "coder-codex.wrapper.log",
    "coder-cursor.wrapper.log",
];

const ALLOW: &[&str] = &[
    "prune-decision.env",
    "prune-nit.env",
    "collector-results.env",
    "review-core-threshold.env",
    "findings-classification.tsv",
    "scout-archetype-yield.tsv",
    "rejected-findings.md",
    "oos.md",
    "oos-accepted-review.md",
    "oos-dropped-before-vote.md",
    "review-round-summary.md",
    "voting-tally.md",
    "aggregator-validate.stderr",
    "aggregator-dispatch.stderr",
    "review-dirty-tree-summary.env",
    "panel-manifest.ndjson",
    "panel-prompt-sizes.tsv",
    "code-voter-slots.ndjson",
    "coder-prompt.md",
    "coder-tool.txt",
    "coder-cursor.log",
    "round-meta.json",
];

const ALLOW_GLOBS: &[&str] = &[
    "cursor-ci-stall-*.json",
    "dirty-checkpoint-*.env",
    "*.dropped-slots",
    "dropped-*-*.txt",
    "voter*-diag.txt",
    "voting-tally-degraded-attempt-*.md",
    "*-parse-rate-diag.txt",
    "skipped-findings*.md",
    "scout-round*-status.env",
    "scout-round*-manifest.json",
];

const DENY_GLOBS: &[&str] = &[
    "cursor-specialist-*-output.txt",
    "cursor-specialist-*-output.txt.meta",
    "cursor-specialist-*-output.txt.json",
    "cursor-specialist-*-output.txt.cap-hit",
    "codex-specialist-*-output.txt",
    "codex-specialist-*-output.txt.meta",
    "codex-specialist-*-output.txt.json",
    "codex-specialist-*-output.txt.cap-hit",
    "cursor-specialist-*-output-phase*.txt",
    "cursor-specialist-*-output-phase*.txt.*",
    "cursor-specialist-*-output-retry.txt",
    "cursor-specialist-*-output-retry.txt.*",
    "codex-specialist-*-output-phase*.txt",
    "codex-specialist-*-output-phase*.txt.*",
    "codex-specialist-*-output-retry.txt",
    "codex-specialist-*-output-retry.txt.*",
    "*.dirty-tree",
    "*.untracked-baseline",
    "*.done",
    "*.diag",
    "*.sidecar",
    "*.events.jsonl",
    "*.sidecar.history",
    "*.events.history",
    "*.failure-diag",
    "*-output.txt.prompt",
    "*-output-*.txt.prompt",
    "coder-output.log",
    "coder-codex.log",
    "*-vote-prompt.txt",
    "dyn-*-codex-output-retry*.txt",
    "dyn-*-codex-output-retry*.txt.meta",
    "dyn-*-codex-output-retry*.txt.json",
    "dyn-*-codex-output-retry*.txt.cap-hit",
    "skipped-findings.security.md",
    "submodule-paths.txt",
    "submodule-scrub.log",
    "submodule-revert.log",
    "coder-commit.log",
    "dyn-*-prompt.md",
    "scout-round*-manifest.json.raw",
    "findings.md",
    "accepted-findings.md",
    "rejected-findings-full.md",
    "reviewer-dyn-*.md",
];

const DEBUG_GLOBS: &[&str] = &[
    "dyn-*-codex-output.txt",
    "dyn-*-codex-output-phase*.txt",
    "dyn-*-codex-output.txt.meta",
    "dyn-*-codex-output-phase*.txt.meta",
    "dyn-*-codex-output.txt.json",
    "dyn-*-codex-output-phase*.txt.json",
    "dyn-*-codex-output.txt.cap-hit",
    "dyn-*-codex-output-phase*.txt.cap-hit",
    "*-vote-output*.txt",
    "*-vote-output*.txt.*",
    "*-ns-retry*.txt",
    "*-ns-retry*.txt.*",
    "*-output-first-pass.txt",
    "*-output.txt",
    "*-output-*.txt",
    "*-output.txt.meta",
    "*-output-*.txt.meta",
    "*-output.txt.json",
    "*-output-*.txt.json",
    "*-output.txt.cap-hit",
    "*-output-*.txt.cap-hit",
];

/// Case-sensitive `fnmatch` for the `*` and `?` wildcards used by these tables.
#[must_use]
pub fn glob_matches(name: &str, pattern: &str) -> bool {
    let name: Vec<char> = name.chars().collect();
    let pattern: Vec<char> = pattern.chars().collect();
    let (mut n, mut p) = (0_usize, 0_usize);
    let (mut star, mut resume) = (None::<usize>, 0_usize);
    while n < name.len() {
        if p < pattern.len() && (pattern[p] == '?' || pattern[p] == name[n]) {
            n += 1;
            p += 1;
        } else if p < pattern.len() && pattern[p] == '*' {
            star = Some(p);
            resume = n;
            p += 1;
        } else if let Some(index) = star {
            p = index + 1;
            resume += 1;
            n = resume;
        } else {
            return false;
        }
    }
    while p < pattern.len() && pattern[p] == '*' {
        p += 1;
    }
    p == pattern.len()
}

fn matches_any(name: &str, patterns: &[&str]) -> bool {
    patterns.iter().any(|pattern| glob_matches(name, pattern))
}

/// True for round-local sidecars that never publish.
#[must_use]
pub fn is_round_sidecar_file(name: &str) -> bool {
    SIDECAR_FILES.contains(&name)
}

/// Decide whether a round artifact basename publishes.
///
/// `flush_debug` mirrors `LARCH_FLUSH_DEBUG=1`, which widens the allow list to
/// the bounded debug globs.
#[must_use]
pub fn round_artifact_included(name: &str, flush_debug: bool) -> bool {
    if matches_any(name, DENY_GLOBS) {
        return false;
    }
    if ALLOW.contains(&name) || matches_any(name, ALLOW_GLOBS) {
        return true;
    }
    flush_debug && matches_any(name, DEBUG_GLOBS)
}

/// A secret that survived two scrubbing passes in a round artifact.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResidualSecretError {
    name: String,
}

impl ResidualSecretError {
    /// Return the operator-facing message.
    #[must_use]
    pub fn message(&self) -> String {
        format!("secret survived scrubbing in round artifact {}", self.name)
    }
}

/// Apply truncation, secret scrubbing, and redaction to one round artifact body.
///
/// # Errors
///
/// Returns [`ResidualSecretError`] when a `dropped-` artifact still carries a
/// recognized secret after a second scrubbing pass.
pub fn stage_round_artifact(name: &str, text: &str) -> Result<String, ResidualSecretError> {
    let mut staged = text.to_owned();
    if name.contains("-vote-output") {
        let raw = staged.as_bytes();
        if raw.len() > VOTE_OUTPUT_TRUNCATE_BYTES {
            let original = raw.len();
            let head = decode_ignoring_partial_tail(&raw[..VOTE_OUTPUT_TRUNCATE_BYTES]);
            staged = format!("{head}\n[TRUNCATED: original {original} bytes]\n");
        }
    }
    if name.starts_with("dropped-") || name.ends_with(".dropped-slots") {
        let first = redact_secrets(&staged);
        if !first.findings().is_empty() {
            let second = redact_secrets(first.text());
            if !second.findings().is_empty() {
                return Err(ResidualSecretError {
                    name: name.to_owned(),
                });
            }
        }
        first.text().clone_into(&mut staged);
    }
    Ok(normalize_run_log_text(redact(&staged).text()))
}

/// Decode a byte prefix, dropping a trailing partial UTF-8 sequence.
///
/// Mirrors Python's `bytes.decode("utf-8", errors="ignore")` for the truncation
/// path, where the byte cut can land mid-character. The source body is already
/// valid UTF-8, so only the tail can be incomplete.
fn decode_ignoring_partial_tail(bytes: &[u8]) -> String {
    match std::str::from_utf8(bytes) {
        Ok(text) => text.to_owned(),
        Err(error) => String::from_utf8_lossy(&bytes[..error.valid_up_to()]).into_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        glob_matches, is_round_sidecar_file, round_artifact_included, stage_round_artifact,
    };

    #[test]
    fn glob_supports_multiple_wildcards() {
        assert!(glob_matches("dropped-voter-1.txt", "dropped-*-*.txt"));
        assert!(!glob_matches("dropped.txt", "dropped-*-*.txt"));
        assert!(glob_matches("anything.done", "*.done"));
        assert!(!glob_matches("Anything.DONE", "*.done"));
    }

    #[test]
    fn deny_beats_allow_and_debug_needs_the_flag() {
        assert!(!round_artifact_included("findings.md", true));
        assert!(round_artifact_included("panel-manifest.ndjson", false));
        assert!(!round_artifact_included("reviewer-1-output.txt", false));
        assert!(round_artifact_included("reviewer-1-output.txt", true));
        assert!(is_round_sidecar_file("coder.env"));
        assert!(!is_round_sidecar_file("coder-prompt.md"));
    }

    #[test]
    fn vote_output_is_truncated_with_a_marker() {
        let body = "x".repeat(4096);
        let staged =
            stage_round_artifact("voter1-vote-output.txt", &body).expect("staging should succeed");
        assert!(staged.contains("[TRUNCATED: original 4096 bytes]"));
        assert!(staged.len() < body.len());
    }

    #[test]
    fn dropped_artifacts_are_scrubbed() {
        let staged = stage_round_artifact(
            "dropped-voter-1.txt",
            "token sk-ant-abcdefghijklmnopqrstuvwxyz0123\n",
        )
        .expect("staging should succeed");
        assert!(!staged.contains("sk-ant-"));
        assert!(staged.contains("<REDACTED-TOKEN>"));
    }
}
