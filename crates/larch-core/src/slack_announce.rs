//! Slack issue-announcement planning for `slack issue-announce`.

use std::path::Path;

/// Environment variable holding the outbound Slack webhook URL.
pub const LARCH_SLACK_WEBHOOK_URL: &str = "LARCH_SLACK_WEBHOOK_URL";

/// Outcome statuses emitted on the machine stdout stream.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SlackAnnounceStatus {
    /// Webhook accepted the announcement.
    Posted,
    /// Announcement was intentionally skipped.
    Skipped,
    /// Announcement failed.
    Failed,
}

impl SlackAnnounceStatus {
    /// Return the wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Posted => "posted",
            Self::Skipped => "skipped",
            Self::Failed => "failed",
        }
    }
}

/// Planned Slack announcement after reading local state files.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SlackIssueAnnouncement {
    /// Process exit code after mapping `--best-effort`.
    pub exit_code: u8,
    /// Machine status token.
    pub status: SlackAnnounceStatus,
    /// Skip reason or failure diagnostic. Never contains the webhook URL.
    pub reason: String,
    /// JSON body to POST when status is [`SlackAnnounceStatus::Posted`] pending transport.
    pub payload: Option<Vec<u8>>,
    /// Validated webhook URL used only by the adapter transport layer.
    pub webhook_url: Option<String>,
}

/// Inputs collected from the implement tmpdir and process environment.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SlackAnnounceInputs {
    /// `ISSUE_NUMBER` from `parent-issue.md`.
    pub issue_number: String,
    /// `RUN_ID` from `parent-issue.md`, else session-id file contents.
    pub run_id: String,
    /// `PR_URL` from `ship-pr-state.sh`.
    pub pr_url: String,
    /// Optional `PR_TITLE` from `ship-pr-state.sh`.
    pub pr_title: String,
    /// Raw webhook URL from the environment. May be empty.
    pub webhook_url: String,
    /// Map transport and validation failures to exit 0.
    pub best_effort: bool,
}

/// Build the announcement plan without performing HTTP I/O.
#[must_use]
pub fn plan_slack_issue_announce(inputs: &SlackAnnounceInputs) -> SlackIssueAnnouncement {
    if !inputs.issue_number.chars().all(|ch| ch.is_ascii_digit()) || inputs.issue_number.is_empty()
    {
        return failure(inputs.best_effort, "ISSUE_NUMBER must be numeric");
    }
    if inputs.issue_number == "0" {
        return skipped("issue-not-set");
    }
    if inputs.webhook_url.is_empty() {
        return skipped("webhook-not-set");
    }
    if !webhook_scheme_allowed(&inputs.webhook_url) {
        return failure(inputs.best_effort, "webhook scheme must be http or https");
    }
    let mut text = format!(
        "Implement run {} opened PR {} for tracking issue #{}",
        inputs.run_id,
        if inputs.pr_url.is_empty() {
            "N/A"
        } else {
            inputs.pr_url.as_str()
        },
        inputs.issue_number
    );
    if !inputs.pr_title.is_empty() {
        text.push_str(": ");
        text.push_str(&inputs.pr_title);
    }
    let payload = serde_json::json!({ "text": text }).to_string().into_bytes();
    SlackIssueAnnouncement {
        exit_code: 0,
        status: SlackAnnounceStatus::Posted,
        reason: String::new(),
        payload: Some(payload),
        webhook_url: Some(inputs.webhook_url.clone()),
    }
}

/// Record a transport failure without embedding the webhook URL.
#[must_use]
pub fn transport_failure(best_effort: bool, error: &str) -> SlackIssueAnnouncement {
    failure(best_effort, &collapse_whitespace(error))
}

/// Mark a planned announcement as successfully posted.
#[must_use]
pub const fn mark_posted() -> SlackIssueAnnouncement {
    SlackIssueAnnouncement {
        exit_code: 0,
        status: SlackAnnounceStatus::Posted,
        reason: String::new(),
        payload: None,
        webhook_url: None,
    }
}

/// Read one KEY=value from a small env-style file body.
#[must_use]
pub fn read_kv_from_text(text: &str, key: &str) -> Option<String> {
    let prefix = format!("{key}=");
    for line in text.split('\n') {
        let trimmed = line.trim_end_matches('\r');
        if let Some(value) = trimmed.strip_prefix(&prefix) {
            return Some(value.to_owned());
        }
    }
    None
}

/// Compose [`SlackAnnounceInputs`] from tmpdir file bodies and the webhook env value.
#[must_use]
pub fn inputs_from_files(
    parent_issue: &str,
    ship_state: &str,
    session_id: &str,
    webhook_url: &str,
    best_effort: bool,
) -> SlackAnnounceInputs {
    let issue_number = read_kv_from_text(parent_issue, "ISSUE_NUMBER")
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "0".to_owned());
    let run_id = read_kv_from_text(parent_issue, "RUN_ID")
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| session_id.trim().to_owned());
    SlackAnnounceInputs {
        issue_number,
        run_id,
        pr_url: read_kv_from_text(ship_state, "PR_URL").unwrap_or_default(),
        pr_title: read_kv_from_text(ship_state, "PR_TITLE").unwrap_or_default(),
        webhook_url: webhook_url.to_owned(),
        best_effort,
    }
}

/// Return true when the webhook URL uses http or https.
#[must_use]
pub fn webhook_scheme_allowed(url: &str) -> bool {
    matches!(
        url.split_once("://").map(|(scheme, _)| scheme),
        Some("http" | "https")
    )
}

/// Scrub a diagnostic so a webhook URL cannot leak into stdout or logs.
#[must_use]
pub fn redact_webhook_url(diagnostic: &str, webhook_url: &str) -> String {
    if webhook_url.is_empty() {
        return collapse_whitespace(diagnostic);
    }
    collapse_whitespace(&diagnostic.replace(webhook_url, "<redacted-webhook-url>"))
}

fn skipped(reason: &str) -> SlackIssueAnnouncement {
    SlackIssueAnnouncement {
        exit_code: 0,
        status: SlackAnnounceStatus::Skipped,
        reason: reason.to_owned(),
        payload: None,
        webhook_url: None,
    }
}

fn failure(best_effort: bool, reason: &str) -> SlackIssueAnnouncement {
    SlackIssueAnnouncement {
        exit_code: u8::from(!best_effort),
        status: SlackAnnounceStatus::Failed,
        reason: reason.to_owned(),
        payload: None,
        webhook_url: None,
    }
}

fn collapse_whitespace(value: &str) -> String {
    value
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(500)
        .collect()
}

/// Join implement-tmpdir relative paths the same way Python does.
#[must_use]
pub fn parent_issue_path(implement_tmpdir: &Path) -> std::path::PathBuf {
    implement_tmpdir.join("parent-issue.md")
}

/// Join ship-pr-state path.
#[must_use]
pub fn ship_state_path(implement_tmpdir: &Path) -> std::path::PathBuf {
    implement_tmpdir.join("ship-pr-state.sh")
}

/// Join session-id path.
#[must_use]
pub fn session_id_path(implement_tmpdir: &Path) -> std::path::PathBuf {
    implement_tmpdir.join("session-id")
}

#[cfg(test)]
mod tests {
    use super::{
        inputs_from_files, plan_slack_issue_announce, redact_webhook_url, transport_failure,
        webhook_scheme_allowed,
    };

    #[test]
    fn skips_and_fails_closed_like_python() {
        let unset = inputs_from_files("", "", "", "", false);
        let skipped = plan_slack_issue_announce(&unset);
        assert_eq!(skipped.status.as_str(), "skipped");
        assert_eq!(skipped.reason, "issue-not-set");

        let bad = inputs_from_files("ISSUE_NUMBER=abc\n", "", "", "https://example.test", false);
        let failed = plan_slack_issue_announce(&bad);
        assert_eq!(failed.exit_code, 1);
        assert_eq!(failed.reason, "ISSUE_NUMBER must be numeric");

        let best = inputs_from_files("ISSUE_NUMBER=abc\n", "", "", "https://example.test", true);
        assert_eq!(plan_slack_issue_announce(&best).exit_code, 0);

        assert!(!webhook_scheme_allowed("ftp://example.test/hook"));
        let scheme = inputs_from_files(
            "ISSUE_NUMBER=12\n",
            "PR_URL=https://example.test/pr/1\n",
            "run",
            "ftp://example.test/hook",
            false,
        );
        assert_eq!(
            plan_slack_issue_announce(&scheme).reason,
            "webhook scheme must be http or https"
        );
    }

    #[test]
    fn posts_json_and_redacts_webhook_url() {
        let inputs = inputs_from_files(
            "ISSUE_NUMBER=9\nRUN_ID=run-1\n",
            "PR_URL=https://example.test/pr/9\nPR_TITLE=Hello\n",
            "",
            "https://hooks.example.test/secret",
            false,
        );
        let planned = plan_slack_issue_announce(&inputs);
        assert_eq!(planned.status.as_str(), "posted");
        let body = String::from_utf8(planned.payload.expect("payload")).expect("utf8");
        assert!(body.contains("Implement run run-1 opened PR https://example.test/pr/9"));
        assert!(body.contains(": Hello"));
        assert!(!body.contains("hooks.example.test/secret"));

        let scrubbed = redact_webhook_url(
            "POST https://hooks.example.test/secret failed",
            "https://hooks.example.test/secret",
        );
        assert!(!scrubbed.contains("hooks.example.test/secret"));
        assert_eq!(transport_failure(true, "boom\nline").exit_code, 0);
    }
}
