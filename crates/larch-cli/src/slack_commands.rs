//! `slack` domain commands.

use std::{env, fs, path::PathBuf, process::ExitCode};

use clap::{Args, Subcommand};
use larch_adapters::http_client::post_json;
use larch_core::{
    LARCH_SLACK_WEBHOOK_URL, emit_kv, inputs_from_files, mark_posted, parent_issue_path,
    plan_slack_issue_announce, redact_webhook_url, session_id_path, ship_state_path,
    transport_failure,
};

#[derive(Subcommand)]
pub enum SlackCommand {
    /// Announce an implement-run PR to Slack when a webhook is configured.
    #[command(name = "issue-announce")]
    IssueAnnounce(IssueAnnounceArguments),
}

#[derive(Args)]
pub struct IssueAnnounceArguments {
    #[arg(long = "implement-tmpdir")]
    implement_tmpdir: Option<PathBuf>,
    #[arg(long = "best-effort")]
    best_effort: bool,
}

/// Run one slack command.
pub fn run(command: SlackCommand) -> ExitCode {
    match command {
        SlackCommand::IssueAnnounce(arguments) => issue_announce(&arguments),
    }
}

fn issue_announce(arguments: &IssueAnnounceArguments) -> ExitCode {
    let Some(tmpdir) = arguments.implement_tmpdir.as_ref() else {
        emit_kv("STATUS", "failed");
        emit_kv("ERROR", "--implement-tmpdir is required");
        return ExitCode::from(2);
    };
    if !tmpdir.is_dir() {
        emit_kv("STATUS", "failed");
        emit_kv("ERROR", "--implement-tmpdir not found");
        return ExitCode::from(2);
    }
    let parent = read_optional(parent_issue_path(tmpdir));
    let ship = read_optional(ship_state_path(tmpdir));
    let session = read_optional(session_id_path(tmpdir));
    let webhook = env::var(LARCH_SLACK_WEBHOOK_URL).unwrap_or_default();
    let planned = plan_slack_issue_announce(&inputs_from_files(
        &parent,
        &ship,
        &session,
        &webhook,
        arguments.best_effort,
    ));
    let result = if planned.status.as_str() == "posted" {
        let url = planned.webhook_url.clone().unwrap_or_default();
        let payload = planned.payload.unwrap_or_default();
        match post_json(&url, &payload) {
            Ok(()) => mark_posted(),
            Err(error) => {
                let scrubbed = redact_webhook_url(error.as_str(), &url);
                transport_failure(arguments.best_effort, &scrubbed)
            }
        }
    } else {
        planned
    };
    emit_kv("STATUS", result.status.as_str());
    if !result.reason.is_empty() {
        let key = if result.status.as_str() == "skipped" {
            "REASON"
        } else {
            "ERROR"
        };
        emit_kv(key, &result.reason);
    }
    ExitCode::from(result.exit_code)
}

fn read_optional(path: PathBuf) -> String {
    fs::read_to_string(path).unwrap_or_default()
}
