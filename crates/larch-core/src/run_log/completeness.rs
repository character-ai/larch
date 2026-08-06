//! `run-log verify-completeness` reachability conditions and manifest scan.
//!
//! Ported from the `_*_reached` chain in `larch.report.run_log_manifest` and
//! `verify_completeness_main` in `larch.report.run_logs`.

use std::path::Path;
use std::sync::LazyLock;

use regex::Regex;
use serde_json::Value;

use super::tolerance::terminal_bail_skip_signal;

static RELATIVE_PATH_ALLOWED: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z0-9_./*-]+$").expect("static relative-path regex must compile")
});

/// Manifest evidence a reachability condition reads.
pub struct ReachabilityContext<'a> {
    run_dir: &'a Path,
    manifest: &'a Value,
    manifest_pr_number: i64,
}

impl<'a> ReachabilityContext<'a> {
    /// Bind one run directory to its already-parsed manifest body.
    #[must_use]
    pub fn new(run_dir: &'a Path, manifest: &'a Value) -> Self {
        Self {
            run_dir,
            manifest,
            manifest_pr_number: manifest_pr_number(manifest),
        }
    }

    fn has_file(&self, relative_path: &str) -> bool {
        self.run_dir.join(relative_path).is_file()
    }

    fn steps_ran(&self) -> Option<&serde_json::Map<String, Value>> {
        self.manifest.get("steps_ran").and_then(Value::as_object)
    }

    fn steps_ran_empty(&self) -> bool {
        self.steps_ran().is_none_or(serde_json::Map::is_empty)
    }

    fn step_flag(&self, step: &str) -> Option<bool> {
        match self.steps_ran()?.get(step) {
            Some(Value::Bool(flag)) => Some(*flag),
            _ => None,
        }
    }

    fn bail_skip(&self) -> bool {
        terminal_bail_skip_signal(self.run_dir, Some(self.manifest), self.manifest_pr_number)
    }

    fn execution_issue_text(&self) -> String {
        let path = self.run_dir.join("execution-issues.ndjson");
        if path.is_file() {
            std::fs::read_to_string(&path).unwrap_or_default()
        } else {
            String::new()
        }
    }
}

/// Read `pr_number` the way `_manifest_field` renders it, as an integer.
fn manifest_pr_number(manifest: &Value) -> i64 {
    let raw = match manifest.get("pr_number") {
        Some(Value::Number(number)) => number.to_string(),
        Some(Value::String(text)) => text.trim().to_owned(),
        _ => return 0,
    };
    raw.parse::<i64>().unwrap_or(0)
}

fn step5_reached(ctx: &ReachabilityContext<'_>) -> bool {
    ctx.has_file("code-review-tally.json")
        || ctx.has_file("review-findings-full.jsonl")
        || step7a_reached(ctx)
}

fn step7a_reached(ctx: &ReachabilityContext<'_>) -> bool {
    let has_step7a_file = ctx.has_file("token-report.json")
        || ctx.has_file("timing-report.json")
        || ctx.has_file("execution-issues.ndjson")
        || ctx.has_file("session-transcript.jsonl");
    if ctx.steps_ran_empty() && !has_step7a_file && ctx.bail_skip() {
        return false;
    }
    has_step7a_file || step8_reached(ctx)
}

fn step8_reached(ctx: &ReachabilityContext<'_>) -> bool {
    let has_version_bump = ctx.has_file("version-bump-reasoning.md");
    if ctx.steps_ran_empty() && !has_version_bump && ctx.bail_skip() {
        return false;
    }
    has_version_bump || ctx.has_file("final-summary.md") || step9a1_reached(ctx, true)
}

fn step9a1_reached(ctx: &ReachabilityContext<'_>, chain: bool) -> bool {
    let has_stats = ctx.has_file("run-statistics.md");
    match ctx.step_flag("step9a1") {
        Some(false) => return false,
        Some(true) => return true,
        None => {}
    }
    if ctx.steps_ran_empty() && !has_stats && ctx.bail_skip() {
        return false;
    }
    let steps_ran_nonempty_without_step9a1 = !ctx.steps_ran_empty()
        && ctx
            .steps_ran()
            .is_some_and(|steps| !steps.contains_key("step9a1"));
    if !has_stats && steps_ran_nonempty_without_step9a1 && ctx.bail_skip() {
        return false;
    }
    if chain { has_stats } else { true }
}

/// Evaluate one required-files condition against a run directory.
///
/// # Errors
///
/// Returns the unsupported-condition message for an unknown token.
pub fn condition_reached(ctx: &ReachabilityContext<'_>, condition: &str) -> Result<bool, String> {
    let reached = match condition {
        "always" => true,
        "step5" => step5_reached(ctx),
        "step7a" => step7a_reached(ctx),
        "step8" => step8_reached(ctx),
        "step18" => ctx.step_flag("step18") == Some(true),
        "step9a1" => step9a1_reached(ctx, false),
        "exn-agg-validate-fail" => ctx
            .execution_issue_text()
            .contains("merged output failed validation"),
        "exn-agg-dispatch-fail" => {
            let text = ctx.execution_issue_text();
            [
                "dispatch-with-waterfall exited non-zero",
                "agent dispatch-waterfall exited non-zero",
                "DISPATCH_OK=false",
            ]
            .iter()
            .any(|needle| text.contains(needle))
        }
        _ => return Err(format!("unsupported manifest condition: {condition}")),
    };
    Ok(reached)
}

/// Outcome of scanning the required-files manifest for one run directory.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CompletenessOutcome {
    /// Every reachable required file is present.
    Complete,
    /// The listed relative paths are reachable but absent.
    Missing(Vec<String>),
    /// The manifest row was malformed; the message names the defect.
    Invalid(String),
}

/// Scan required-files manifest rows against `run_dir`.
///
/// `glob_hit` resolves a single-`*` relative path to whether any regular file
/// matches, keeping filesystem globbing at the command boundary.
pub fn scan_required_files(
    ctx: &ReachabilityContext<'_>,
    manifest_tsv: &str,
    glob_hit: impl Fn(&str) -> bool,
) -> CompletenessOutcome {
    let mut missing: Vec<String> = Vec::new();
    for line in manifest_tsv.lines() {
        if line.trim().is_empty() || line.starts_with('#') {
            continue;
        }
        let mut columns = line.split('\t');
        let relative_path = columns.next().unwrap_or_default();
        if relative_path.is_empty() || relative_path == "relative_path" {
            continue;
        }
        // A row with no condition column defaults to `always`; an explicitly
        // empty column is a malformed row and fails loudly below.
        let condition = columns.next().unwrap_or("always");
        if relative_path.split('/').any(|segment| segment == "..") {
            return CompletenessOutcome::Invalid(format!(
                "verify-completeness: invalid relative_path (..): {relative_path}"
            ));
        }
        if !RELATIVE_PATH_ALLOWED.is_match(relative_path) {
            return CompletenessOutcome::Invalid(format!(
                "verify-completeness: invalid characters in relative_path: {relative_path}"
            ));
        }
        match condition_reached(ctx, condition) {
            Ok(false) => continue,
            Ok(true) => {}
            Err(message) => {
                return CompletenessOutcome::Invalid(format!("verify-completeness: {message}"));
            }
        }
        if relative_path.contains('*') {
            if relative_path.matches('*').count() > 1 {
                return CompletenessOutcome::Invalid(format!(
                    "verify-completeness: relative_path must contain at most one * wildcard: {relative_path}"
                ));
            }
            if !glob_hit(relative_path) {
                missing.push(relative_path.to_owned());
            }
        } else if !ctx.has_file(relative_path) {
            missing.push(relative_path.to_owned());
        }
    }
    if missing.is_empty() {
        CompletenessOutcome::Complete
    } else {
        CompletenessOutcome::Missing(missing)
    }
}

#[cfg(test)]
mod tests {
    use super::{CompletenessOutcome, ReachabilityContext, condition_reached, scan_required_files};
    use serde_json::json;
    use std::fs;

    #[test]
    fn always_and_step18_read_the_manifest_flags() {
        let dir = tempfile::tempdir().expect("temp dir");
        let manifest = json!({"steps_ran": {"step18": true}});
        let ctx = ReachabilityContext::new(dir.path(), &manifest);
        assert_eq!(condition_reached(&ctx, "always"), Ok(true));
        assert_eq!(condition_reached(&ctx, "step18"), Ok(true));
        assert_eq!(
            condition_reached(&ctx, "step99"),
            Err("unsupported manifest condition: step99".to_owned())
        );
    }

    #[test]
    fn terminal_bail_without_pr_evidence_suppresses_step7a() {
        let dir = tempfile::tempdir().expect("temp dir");
        fs::write(
            dir.path().join("final-summary.md"),
            "## /implement: bailed\n",
        )
        .expect("summary should write");
        let manifest = json!({"steps_ran": {}});
        let ctx = ReachabilityContext::new(dir.path(), &manifest);
        assert_eq!(condition_reached(&ctx, "step7a"), Ok(false));
        assert_eq!(condition_reached(&ctx, "step5"), Ok(false));

        // A step-7a artifact re-enables the condition even under the bail signal.
        fs::write(dir.path().join("token-report.json"), "{}\n").expect("report should write");
        let ctx = ReachabilityContext::new(dir.path(), &manifest);
        assert_eq!(condition_reached(&ctx, "step7a"), Ok(true));
    }

    #[test]
    fn explicit_step9a1_false_wins_over_present_statistics() {
        let dir = tempfile::tempdir().expect("temp dir");
        fs::write(dir.path().join("run-statistics.md"), "stats\n").expect("stats should write");
        let manifest = json!({"steps_ran": {"step9a1": false}});
        let ctx = ReachabilityContext::new(dir.path(), &manifest);
        assert_eq!(condition_reached(&ctx, "step9a1"), Ok(false));
    }

    #[test]
    fn scan_reports_missing_reachable_rows_only() {
        let dir = tempfile::tempdir().expect("temp dir");
        fs::write(dir.path().join("manifest.json"), "{}\n").expect("manifest should write");
        let manifest = json!({"steps_ran": {}});
        let ctx = ReachabilityContext::new(dir.path(), &manifest);
        let tsv = "relative_path\tcondition\nmanifest.json\talways\nfinal-summary.md\tstep18\nplan-review-tally.json\talways\n";
        assert_eq!(
            scan_required_files(&ctx, tsv, |_| false),
            CompletenessOutcome::Missing(vec!["plan-review-tally.json".to_owned()])
        );
    }

    #[test]
    fn scan_rejects_traversal_and_multi_wildcard_rows() {
        let dir = tempfile::tempdir().expect("temp dir");
        let manifest = json!({});
        let ctx = ReachabilityContext::new(dir.path(), &manifest);
        assert!(matches!(
            scan_required_files(&ctx, "../escape.md\talways\n", |_| true),
            CompletenessOutcome::Invalid(_)
        ));
        assert!(matches!(
            scan_required_files(&ctx, "round-*/*.stderr\talways\n", |_| true),
            CompletenessOutcome::Invalid(_)
        ));
    }
}
