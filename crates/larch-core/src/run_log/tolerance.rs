//! Bail/terminal summary helpers ported from `larch.report.run_log_tolerance`.

use std::path::Path;

use serde_json::Value;

/// Return the first non-empty stripped line from `path`, or an empty string.
#[must_use]
pub fn first_nonempty_line(path: &Path) -> String {
    let Ok(text) = std::fs::read_to_string(path) else {
        return String::new();
    };
    for line in text.lines() {
        let stripped = line.trim();
        if !stripped.is_empty() {
            return stripped.to_owned();
        }
    }
    String::new()
}

/// Return whether `manifest` carries PR evidence matching `pr`.
///
/// When `pr > 0`, the manifest `pr_number` must equal that value. When `pr == 0`,
/// any positive integer `pr_number` counts as evidence.
#[must_use]
pub fn manifest_pr_evidence_matches(manifest: Option<&Value>, pr: i64) -> bool {
    let Some(Value::Object(map)) = manifest else {
        return false;
    };
    let Some(raw) = map.get("pr_number") else {
        return false;
    };
    let rendered = match raw {
        Value::Number(number) => number.to_string(),
        Value::String(text) => text.clone(),
        _ => return false,
    };
    let trimmed = rendered.trim();
    if trimmed.is_empty() || trimmed == "0" || !trimmed.chars().all(|ch| ch.is_ascii_digit()) {
        return false;
    }
    let Ok(value) = trimmed.parse::<i64>() else {
        return false;
    };
    if pr > 0 { value == pr } else { value > 0 }
}

fn heading_matches(line: &str, pattern: &regex::Regex) -> bool {
    let heading = line.trim();
    heading.starts_with("## /") && pattern.is_match(heading)
}

fn stale_bail_heading_re() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| regex::Regex::new(r"bailed(-needs-user-input)?$").expect("stale bail regex"))
}

fn terminal_outcome_re() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(
            r"(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?|shipping)$",
        )
        .expect("terminal outcome regex")
    })
}

/// True when `final-summary.md` has a stale bail heading and matching PR evidence.
#[must_use]
pub fn stale_bail_heading_with_pr_evidence(
    run_dir: &Path,
    manifest: Option<&Value>,
    pr: i64,
) -> bool {
    let summary = run_dir.join("final-summary.md");
    let Ok(text) = std::fs::read_to_string(&summary) else {
        return false;
    };
    for line in text.lines() {
        if heading_matches(line, stale_bail_heading_re()) {
            return manifest_pr_evidence_matches(manifest, pr);
        }
    }
    false
}

/// True when `final-summary.md` has a terminal outcome heading.
#[must_use]
pub fn final_summary_terminal_heading(run_dir: &Path) -> bool {
    let summary = run_dir.join("final-summary.md");
    let Ok(text) = std::fs::read_to_string(&summary) else {
        return false;
    };
    text.lines()
        .any(|line| heading_matches(line, terminal_outcome_re()))
}

/// True when verify/audit should apply bail-time required-file skip.
#[must_use]
pub fn terminal_bail_skip_signal(run_dir: &Path, manifest: Option<&Value>, pr: i64) -> bool {
    if stale_bail_heading_with_pr_evidence(run_dir, manifest, pr) {
        return false;
    }
    final_summary_terminal_heading(run_dir)
}

#[cfg(test)]
mod tests {
    use super::{
        final_summary_terminal_heading, first_nonempty_line, manifest_pr_evidence_matches,
        terminal_bail_skip_signal,
    };
    use serde_json::json;
    use std::fs;

    #[test]
    fn first_nonempty_line_skips_blank_prefix() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("notes.txt");
        fs::write(&path, "\n\n  hello  \n").unwrap();
        assert_eq!(first_nonempty_line(&path), "hello");
        assert_eq!(first_nonempty_line(&dir.path().join("missing")), "");
    }

    #[test]
    fn pr_evidence_and_terminal_bail_signal() {
        let dir = tempfile::tempdir().unwrap();
        let run_dir = dir.path();
        fs::write(
            run_dir.join("final-summary.md"),
            "## /implement: bailed\n\nnotes\n",
        )
        .unwrap();
        let manifest = json!({"pr_number": 7});
        assert!(manifest_pr_evidence_matches(Some(&manifest), 7));
        assert!(final_summary_terminal_heading(run_dir));
        // Stale bail with PR evidence suppresses the skip signal.
        assert!(!terminal_bail_skip_signal(run_dir, Some(&manifest), 7));
        // Without PR evidence, terminal bail heading enables the skip.
        assert!(terminal_bail_skip_signal(run_dir, None, 0));
    }
}
