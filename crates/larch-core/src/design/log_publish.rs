//! Pure helpers for `/design` log-publish staging and lifecycle outcome mapping.
//!
//! Leaf #8592. Command orchestration lives in `larch-cli`; this module owns the
//! basename exclusion predicates and the reason/outcome → lifecycle terminal map
//! so they stay network-free and unit-testable.

use crate::run_log::glob_matches;

/// Exact basenames excluded at every tree depth.
const EXCLUDE_NAMES: &[&str] = &[
    "plan-review-collector.stderr",
    "plan-review-slots.ndjson.output-files.dropped-slots",
    "composed-plan.redacted.md",
    "findings-ledger.tsv",
    "claude-source.env",
    "source-env.sh",
    "security-oos-observations.md",
];

/// Whole subtrees that carry no final committed-log value.
const EXCLUDE_DIRS: &[&str] = &["plan-autofix", ".completed", "larch-logs"];

/// GitHub-redundant snapshots dropped only at the design-tmpdir root.
const EXCLUDE_TOPLEVEL_NAMES: &[&str] = &[
    "issue-body.txt",
    "issue.json",
    "architecture-diagram.md",
    "architecture-diagram.candidate.md",
    "architecture-diagram.skipped",
    "architecture-diagram-generation.failure.log",
    "architecture-diagram-sanitizer.failure.log",
    "panel-manifest.ndjson",
    "panel-prompt-sizes.tsv",
];

/// Suffixes for raw machine sidecars/transcripts.
const EXCLUDE_SUFFIXES: &[&str] = &[
    ".events.jsonl",
    ".events.history",
    ".prompt",
    ".meta",
    ".sidecar",
    ".sidecar.history",
    ".token-record",
    ".dirty-tree",
    ".untracked-baseline",
    ".diag",
    ".done",
    ".cap-hit",
    ".launch-stderr",
    ".launcher-stderr",
    ".stderr-tail",
    ".porcelain",
    ".txt.json",
    ".txt.tsv",
];

/// Glob-matched basenames for raw per-lane transcripts and prompt carriers.
const EXCLUDE_GLOBS: &[&str] = &[
    "*-plan-*-output*.txt",
    "*-plan-*-output*.txt.*",
    "*-prompt.txt",
    "*-prompt.md",
    "step2b-codex-raw.*",
    "*-collector.failure.log",
    "*-diagram-failure.bounded.log",
    "*.raw.cursor",
    "*.raw.claude",
];

/// Artifact name for the Gate C invariant assessment note.
pub const INVARIANT_ASSESSMENT_ARTIFACT: &str = "architectural-invariant-assessment.md";
/// Artifact name for the Gate C guideline assessment note.
pub const GUIDELINE_ASSESSMENT_ARTIFACT: &str = "architectural-guideline-assessment.md";

/// Return true for raw machine sidecars/transcripts that must not be committed.
///
/// `name` is a single path component (basename). Directory names match
/// [`EXCLUDE_DIRS`]; files match exact-name, suffix, and glob sets. When
/// `top_level` is set, GitHub-redundant snapshots in [`EXCLUDE_TOPLEVEL_NAMES`]
/// are also dropped.
#[must_use]
pub fn publish_excluded(name: &str, is_dir: bool, top_level: bool) -> bool {
    if is_dir {
        return EXCLUDE_DIRS.contains(&name);
    }
    if top_level && EXCLUDE_TOPLEVEL_NAMES.contains(&name) {
        return true;
    }
    if EXCLUDE_NAMES.contains(&name) {
        return true;
    }
    if EXCLUDE_SUFFIXES.iter().any(|suffix| name.ends_with(suffix)) {
        return true;
    }
    if name.ends_with("-vote-output.txt") {
        return false;
    }
    EXCLUDE_GLOBS
        .iter()
        .any(|pattern| glob_matches(name, pattern))
}

/// Map a publish reason and outcome label to the shared lifecycle terminal.
#[must_use]
pub fn lifecycle_outcome(reason: &str, outcome: &str) -> &'static str {
    let normalized = outcome.to_ascii_lowercase();
    if normalized.starts_with("cancelled") {
        return "cancelled";
    }
    if normalized.starts_with("failed") {
        return "failure";
    }
    if reason == "pause" {
        return "early-return";
    }
    "success"
}

/// Default outcome label when the caller omits `--outcome`.
#[must_use]
pub fn default_outcome_for_reason(reason: &str) -> &'static str {
    if reason == "pause" {
        "paused"
    } else {
        "approved"
    }
}

/// True when `value` is a non-zero digit-only issue number.
#[must_use]
pub fn validate_issue(value: &str) -> bool {
    !value.is_empty() && value != "0" && value.bytes().all(|byte| byte.is_ascii_digit())
}

/// True when `value` matches `[A-Za-z0-9._-]+`.
#[must_use]
pub fn validate_slug(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

/// True when `value` matches `OWNER/REPO` with the shared slug charset.
#[must_use]
pub fn validate_repo(value: &str) -> bool {
    let Some((owner, repo)) = value.split_once('/') else {
        return false;
    };
    validate_slug(owner) && validate_slug(repo) && !value.contains("//")
}

/// Assessment completeness for a Gate C design note.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AssessmentCompleteness {
    /// Whether the outcome and repo knowledge require the artifact.
    pub required: bool,
    /// Whether a regular (non-symlink) artifact file is present.
    pub present: bool,
}

/// Decide whether an approved outcome requires a Gate C assessment artifact.
#[must_use]
pub fn assessment_required(
    outcome: &str,
    knowledge_present: bool,
    knowledge_nonempty: bool,
) -> bool {
    matches!(outcome, "approved" | "approved-partition") && knowledge_present && knowledge_nonempty
}

/// Classify whether a path is a present regular assessment artifact.
#[must_use]
pub const fn assessment_present(is_file: bool, is_symlink: bool) -> bool {
    is_file && !is_symlink
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn excludes_raw_sidecars_and_spares_vote_output() {
        assert!(publish_excluded("lane.events.jsonl", false, false));
        assert!(publish_excluded("cursor-plan-1-output.txt", false, false));
        assert!(!publish_excluded("cursor-vote-output.txt", false, false));
        assert!(!publish_excluded("aggregator-output.txt", false, false));
        assert!(publish_excluded("plan-autofix", true, false));
        assert!(publish_excluded(".completed", true, false));
    }

    #[test]
    fn top_level_only_drops_github_redundant_snapshots() {
        assert!(publish_excluded("issue-body.txt", false, true));
        assert!(!publish_excluded("issue-body.txt", false, false));
        assert!(publish_excluded("panel-manifest.ndjson", false, true));
        assert!(!publish_excluded("panel-manifest.ndjson", false, false));
    }

    #[test]
    fn lifecycle_outcome_maps_cancellation_and_pause() {
        assert_eq!(
            lifecycle_outcome("final", "cancelled-title-filter"),
            "cancelled"
        );
        assert_eq!(lifecycle_outcome("final", "approved"), "success");
        assert_eq!(lifecycle_outcome("pause", "approved"), "early-return");
        assert_eq!(lifecycle_outcome("final", "failed-gate"), "failure");
    }

    #[test]
    fn validation_helpers_match_python_charset() {
        assert!(validate_issue("42"));
        assert!(!validate_issue("0"));
        assert!(!validate_issue("4a"));
        assert!(validate_slug("ABCDEF01-2345-6789-ABCD-EF0123456789"));
        assert!(!validate_slug("bad/id"));
        assert!(validate_repo("owner/repo"));
        assert!(!validate_repo("owner"));
        assert!(!validate_repo("owner//repo"));
    }
}
