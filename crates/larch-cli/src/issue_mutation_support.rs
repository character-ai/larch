//! Shared refusal vocabulary for the GitHub issue-writing commands.
//!
//! `/issue` and `/block-issue` publish their outcomes differently, but every
//! verb that writes to a GitHub issue answers the same two questions the same
//! way: is this caller authorized to mutate live state, and how does one
//! diagnostic become a single printable contract row? Both answers live here so
//! the filing verbs and the issue-graph verbs cannot drift apart on the
//! refusal token, the reserved exit code, or the redaction that runs before a
//! diagnostic is published.

use larch_adapters::{
    github::{IssueCreateFailure, IssueMutationOwner, LiveMutationRequest, OctocrabGitHubService},
    runtime::Cancellation,
};
use larch_core::{
    CreatedIssue, IssueCreateRequest, is_python_whitespace, redact_issue_text_outbound,
};
use std::{env, path::Path};

/// Exit code reserved for a refused live mutation, shared with Python config.
pub const EXIT_MUTATION_REFUSED: u8 = 5;
/// Row a caller reads to tell a refused mutation from any other failure.
pub const MUTATION_REFUSAL_STATUS: &str = "mutation-refused";
/// Reason token every refused live mutation prefixes its detail with.
pub const MUTATION_REFUSAL_REASON: &str = "unauthorized-mutation";
/// Environment override that denies session-inherited authorization in tests.
const MUTATION_TEST_DENY_KEY: &str = "LARCH_ISSUE_MUTATION_DENY";

/// A failed create and the orphan close it attempted, when there was one.
pub type CreateRollback = (IssueCreateFailure, Option<(u64, Result<(), String>)>);

/// Create one issue and close the orphan a failed create left behind.
///
/// GitHub can open the issue and still fail the call, which leaves a
/// half-filed issue nobody asked for. Every caller that files an issue owes
/// that rollback, so the attempt lives here rather than in each command: the
/// create and the close then share one client and one credential acquisition,
/// and no filing verb can quietly skip the cleanup.
///
/// # Errors
/// Returns the failure and its rollback outcome when the create did not
/// produce a usable issue.
pub async fn create_with_rollback(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    authorization: &LiveMutationRequest<'_>,
    request: &IssueCreateRequest,
) -> Result<CreatedIssue, CreateRollback> {
    let owner = IssueMutationOwner::new(service);
    match owner.create(cancellation, authorization, request).await {
        Ok(created) => Ok(created),
        Err(failure) => {
            let rollback = match failure.orphan {
                None => None,
                Some(orphan) => Some((
                    orphan,
                    owner
                        .close_not_planned(cancellation, &request.repository, orphan)
                        .await,
                )),
            };
            Err((failure, rollback))
        }
    }
}

/// Build the live-mutation authorization request for one command line.
pub fn authorization_request<'a>(
    context_file: &'a str,
    run_id: &'a str,
    trusted_root: &'a str,
    operator_invoked: bool,
) -> LiveMutationRequest<'a> {
    LiveMutationRequest {
        context_file: (!context_file.is_empty()).then(|| Path::new(context_file)),
        operator_mode: operator_invoked,
        run_id,
        trusted_root: (!trusted_root.is_empty()).then(|| Path::new(trusted_root)),
        test_deny: env::var(MUTATION_TEST_DENY_KEY).as_deref() == Ok("true"),
    }
}

/// Report the gate's decision as the reason token the error line carries.
///
/// # Errors
/// Returns the refusal reason when the gate does not authorize the request.
pub fn authorized(request: &LiveMutationRequest<'_>) -> Result<(), &'static str> {
    let decision = larch_adapters::github::check_live_mutation_auth(request);
    if decision.is_authorized() {
        Ok(())
    } else {
        Err(decision.reason())
    }
}

/// Strip C0 controls and DEL from one line, as the Python emitters did.
///
/// A diagnostic reaches these rows from GitHub and from operator input, so a
/// carriage return or newline inside one must not be able to forge a second
/// `KEY=value` row in a stream a caller parses.
#[must_use]
pub fn sanitized_line(text: &str) -> String {
    text.chars()
        .filter(|character| *character >= ' ' && *character != '\u{7f}')
        .collect()
}

/// Collapse, redact, and bound one diagnostic into a single contract value.
///
/// Whitespace collapse removes the newlines a row cannot carry, redaction runs
/// before the value is published, and the control strip keeps the row
/// printable.
#[must_use]
pub fn flat_error(message: &str, limit: usize) -> String {
    let redacted =
        redact_issue_text_outbound(message).unwrap_or_else(|error| error.reason().to_owned());
    let bounded = redacted
        .split(is_python_whitespace)
        .filter(|piece| !piece.is_empty())
        .collect::<Vec<&str>>()
        .join(" ")
        .chars()
        .take(limit)
        .collect::<String>();
    sanitized_line(&bounded)
}

#[cfg(test)]
mod tests {
    use super::{authorization_request, authorized, flat_error, sanitized_line};

    #[test]
    fn a_diagnostic_is_collapsed_redacted_bounded_and_control_free() {
        assert_eq!(flat_error("one\n  two\tthree\n", 500), "one two three");
        assert_eq!(
            flat_error("token ghp_abcdefghijklmnopqrstuvwxyz0123456789", 500),
            "token <REDACTED-TOKEN>"
        );
        assert_eq!(flat_error("a\u{0}b\u{7f}c", 500), "abc");
        assert_eq!(flat_error(&"x".repeat(600), 500).len(), 500);
        assert_eq!(flat_error(&"x".repeat(1200), 1000).len(), 1000);
        assert_eq!(sanitized_line("row\rFORGED=value"), "rowFORGED=value");
    }

    #[test]
    fn operator_mode_authorizes_and_a_bare_line_refuses() {
        assert_eq!(authorized(&authorization_request("", "", "", true)), Ok(()));
        assert!(
            authorized(&authorization_request("", "", "", false)).is_err(),
            "a line with neither operator mode nor a session context must refuse"
        );
    }
}
