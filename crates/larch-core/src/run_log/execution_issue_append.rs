//! Execution-issue ledger composition for `run-log append-entry` and
//! `run-log append-failure`.
//!
//! Ported from `_append_execution_issue`, `_failure_retry_suffix`, and
//! `log_append_failure` in `larch.report`.

use std::sync::LazyLock;

use regex::Regex;

/// Categories accepted by `run-log append-entry`.
pub const EXECUTION_ISSUE_CATEGORIES: &[&str] = &[
    "Pre-existing Code Issues",
    "Tool Failures",
    "Permission Prompts",
    "External Reviewer Issues",
    "CI Issues",
    "Warnings",
    "Q/A",
];

/// Categories accepted by `run-log append-failure`.
pub const FAILURE_CATEGORIES: &[&str] = &[
    "Tool Failures",
    "External Reviewer Issues",
    "CI Issues",
    "Warnings",
];

static NON_NEGATIVE_INTEGER: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[0-9]+$").expect("static integer regex must compile"));

/// Insert `entry` under the `### category` heading of an execution-issue log.
///
/// Returns the whole new file body. An existing heading receives the entry at
/// the end of its section, just before the next `### ` heading; an unseen
/// category is appended as a new section at the end of the file.
#[must_use]
pub fn compose_execution_issue(existing: &str, category: &str, entry: &str) -> String {
    let header = format!("### {category}");
    let lines: Vec<&str> = existing.lines().collect();
    if !lines.contains(&header.as_str()) {
        let prefix = if existing.is_empty() { "" } else { "\n" };
        return format!(
            "{}{prefix}{header}\n\n{}\n",
            existing.trim_end_matches('\n'),
            entry.trim_end_matches('\n')
        );
    }
    let mut out: Vec<String> = Vec::with_capacity(lines.len() + 2);
    let mut inserted = false;
    let mut in_target = false;
    for line in lines {
        if line == header {
            in_target = true;
            out.push(line.to_owned());
            continue;
        }
        if in_target && line.starts_with("### ") {
            if !inserted {
                out.push(String::new());
                out.push(entry.trim_end_matches('\n').to_owned());
                inserted = true;
            }
            in_target = false;
        }
        out.push(line.to_owned());
    }
    if in_target && !inserted {
        out.push(String::new());
        out.push(entry.trim_end_matches('\n').to_owned());
    }
    let mut text = out.join("\n");
    text.push('\n');
    text
}

/// Retry annotation appended to a failure entry heading.
#[must_use]
pub fn failure_retry_suffix(retry_count: &str, transient_retry_count: &str) -> String {
    if !retry_count.is_empty() && !transient_retry_count.is_empty() {
        // Both counters include the initial attempt, so subtract it before display.
        let auth_retries = retry_count.parse::<i64>().unwrap_or(0) - 1;
        let transient_retries = transient_retry_count.parse::<i64>().unwrap_or(0) - 1;
        let mut parts: Vec<String> = Vec::new();
        if auth_retries > 0 {
            parts.push(format!("auth-retries={auth_retries}"));
        }
        if transient_retries > 0 {
            parts.push(format!("transient-retries={transient_retries}"));
        }
        if parts.is_empty() {
            return String::new();
        }
        return format!(", {}", parts.join(", "));
    }
    if retry_count.is_empty() {
        String::new()
    } else {
        format!(", retries={retry_count}")
    }
}

/// Inputs for one `run-log append-failure` entry body.
#[derive(Clone, Debug)]
pub struct FailureEntry<'a> {
    /// Workflow site label, e.g. `implement Step 2`.
    pub site: &'a str,
    /// Tool name that failed.
    pub tool: &'a str,
    /// Captured exit code, as supplied.
    pub exit_code: &'a str,
    /// Optional verdict fragment inserted before the retry suffix.
    pub verdict: &'a str,
    /// Total attempts including the first, or empty.
    pub retry_count: &'a str,
    /// Transient attempts including the first, or empty.
    pub transient_retry_count: &'a str,
    /// Status word rendered after the tool name.
    pub status_label: &'a str,
    /// Diagnostics body, already redacted and sanitized by the caller.
    pub body: &'a str,
}

/// Validate the integer-shaped flags of a failure entry.
///
/// # Errors
///
/// Returns the operator-facing message naming the offending flag.
pub fn validate_failure_counts(
    exit_code: &str,
    retry_count: &str,
    transient_retry_count: &str,
) -> Result<(), String> {
    for (flag, value) in [
        ("exit-code", exit_code),
        ("retry-count", retry_count),
        ("transient-retry-count", transient_retry_count),
    ] {
        if !value.is_empty() && !NON_NEGATIVE_INTEGER.is_match(value) {
            return Err(format!("--{flag} must be a non-negative integer"));
        }
    }
    Ok(())
}

/// Render one failure entry in the execution-issue bullet shape.
#[must_use]
pub fn compose_failure_entry(entry: &FailureEntry<'_>) -> String {
    let mut suffix = String::new();
    if !entry.verdict.is_empty() {
        suffix.push_str(", ");
        suffix.push_str(entry.verdict);
    }
    suffix.push_str(&failure_retry_suffix(
        entry.retry_count,
        entry.transient_retry_count,
    ));
    format!(
        "- **Step {site}: {tool} {status} (exit {exit}{suffix})**:\n  ```\n{body}\n  ```\n",
        site = entry.site,
        tool = entry.tool,
        status = entry.status_label,
        exit = entry.exit_code,
        body = entry.body.trim_end()
    )
}

#[cfg(test)]
mod tests {
    use super::{
        FailureEntry, compose_execution_issue, compose_failure_entry, failure_retry_suffix,
        validate_failure_counts,
    };

    #[test]
    fn appends_a_new_category_section() {
        assert_eq!(
            compose_execution_issue("", "Warnings", "- first\n"),
            "### Warnings\n\n- first\n"
        );
        assert_eq!(
            compose_execution_issue("### CI Issues\n\n- old\n", "Warnings", "- new\n"),
            "### CI Issues\n\n- old\n### Warnings\n\n- new\n"
        );
    }

    #[test]
    fn appends_at_the_end_of_an_existing_section() {
        let existing = "### Warnings\n\n- old\n\n### CI Issues\n\n- ci\n";
        assert_eq!(
            compose_execution_issue(existing, "Warnings", "- new\n"),
            "### Warnings\n\n- old\n\n\n- new\n### CI Issues\n\n- ci\n"
        );
        // A trailing target section has no following heading to anchor on.
        assert_eq!(
            compose_execution_issue("### Warnings\n\n- old\n", "Warnings", "- new\n"),
            "### Warnings\n\n- old\n\n- new\n"
        );
    }

    #[test]
    fn retry_suffix_subtracts_the_initial_attempt() {
        assert_eq!(failure_retry_suffix("", ""), "");
        assert_eq!(failure_retry_suffix("3", ""), ", retries=3");
        assert_eq!(failure_retry_suffix("1", "1"), "");
        assert_eq!(
            failure_retry_suffix("3", "2"),
            ", auth-retries=2, transient-retries=1"
        );
    }

    #[test]
    fn rejects_non_integer_counts() {
        assert!(validate_failure_counts("1", "", "").is_ok());
        assert_eq!(
            validate_failure_counts("x", "", "").expect_err("bad exit code"),
            "--exit-code must be a non-negative integer"
        );
        assert_eq!(
            validate_failure_counts("1", "-2", "").expect_err("bad retry count"),
            "--retry-count must be a non-negative integer"
        );
    }

    #[test]
    fn renders_the_failure_bullet() {
        let rendered = compose_failure_entry(&FailureEntry {
            site: "implement Step 2",
            tool: "codex-implement",
            exit_code: "9",
            verdict: "verdict=timeout",
            retry_count: "2",
            transient_retry_count: "",
            status_label: "failed",
            body: "boom\n\n",
        });
        assert_eq!(
            rendered,
            "- **Step implement Step 2: codex-implement failed (exit 9, verdict=timeout, retries=2)**:\n  ```\nboom\n  ```\n"
        );
    }
}
