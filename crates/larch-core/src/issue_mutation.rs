//! Fail-closed request validation for GitHub issue field mutations.
//!
//! The concrete GitHub adapter owns reads and writes. This module owns the
//! typed request shape, redaction, compare-and-swap checks, protected-body
//! rules, and exact postconditions that every adapter-backed issue mutation
//! must share.

use std::{collections::BTreeSet, error::Error, fmt, sync::LazyLock};

use chrono::DateTime;
use regex::Regex;

use crate::{
    GitHubIssue, GitHubIssueState, GitHubRepositoryRef, MANAGED_PREFIXES, UMBRELLA_PREFIX,
    has_managed_prefix, redact, redact_secrets,
};

/// Marker proving that `/umbrella` persisted its proposal in the parent body.
pub const UMBRELLA_PROPOSAL_MARKER: &str = "<!-- larch:umbrella-proposal";
const IMPLEMENTATION_LEASE_MARKER: &str = "implementation-lease";
const PLAN_MARKER: &str = "plan";

static IMPLEMENTATION_LEASE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^<!-- larch:implementation-lease v1 run_id=([A-Za-z0-9][A-Za-z0-9._-]{0,127}) branch=[^\s]+ base=[0-9a-f]{40} plan=[0-9a-f]{64} updated_at=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z -->$",
    )
    .expect("implementation lease expression is valid")
});
static PLAN_RECEIPT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^[ \t]*<!--[ \t]+larch:plan-receipt[ \t]+v1[ \t]+plan_sha256=([0-9a-f]{64})[ \t]+base_sha=([0-9a-f]{40})[ \t]+blockers_sha256=[0-9a-f]{64}[ \t]+owners_sha256=[0-9a-f]{64}[ \t]+-->[ \t]*\r?$",
    )
    .expect("plan receipt expression is valid")
});

/// The plan and base identities an implementation lease inherits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanReceiptIdentity {
    pub plan_sha256: String,
    pub base_sha: String,
}

/// A field the issue-mutation owner may change.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum IssueMutationField {
    Title,
    Body,
    Labels,
    NamedBlock,
    ImplementationLease,
    UmbrellaConversion,
    UmbrellaAdoption,
}

/// The run binding attached to a protected named-block or lease mutation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueMutationLease {
    pub run_id: String,
    pub marker: String,
}

/// One freshness-checked request to mutate an issue's allowed fields.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueMutationRequest {
    pub repository: GitHubRepositoryRef,
    pub issue: u64,
    pub expected_updated_at: String,
    pub expected_state: GitHubIssueState,
    pub fields: BTreeSet<IssueMutationField>,
    pub title: Option<String>,
    pub body: Option<String>,
    pub labels: Option<BTreeSet<String>>,
    pub marker: Option<String>,
    pub lease: Option<IssueMutationLease>,
}

impl IssueMutationRequest {
    /// Build a labels-only freshness-checked mutation from a live snapshot.
    #[must_use]
    pub fn replace_labels(snapshot: &IssueMutationSnapshot, labels: BTreeSet<String>) -> Self {
        Self {
            repository: snapshot.repository.clone(),
            issue: snapshot.issue,
            expected_updated_at: snapshot.updated_at.clone(),
            expected_state: snapshot.state,
            fields: BTreeSet::from([IssueMutationField::Labels]),
            title: None,
            body: None,
            labels: Some(labels),
            marker: None,
            lease: None,
        }
    }
}

/// The canonical GitHub state used by a compare-and-swap mutation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueMutationSnapshot {
    pub repository: GitHubRepositoryRef,
    pub issue: u64,
    pub title: String,
    pub body: String,
    pub labels: BTreeSet<String>,
    pub state: GitHubIssueState,
    pub updated_at: String,
}

/// Verified before-and-after state returned by a successful owner mutation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedIssueMutation {
    pub before: IssueMutationSnapshot,
    pub after: IssueMutationSnapshot,
    pub fields: BTreeSet<IssueMutationField>,
}

/// Stable refusal returned when an issue mutation cannot be proved safe.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct IssueMutationError {
    reason: &'static str,
}

impl IssueMutationError {
    /// Build a refusal with one of the owner contract's stable reason tokens.
    #[must_use]
    pub const fn new(reason: &'static str) -> Self {
        Self { reason }
    }

    /// Return the stable machine-readable refusal reason.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        self.reason
    }
}

impl fmt::Display for IssueMutationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "protected-issue-mutation:{}", self.reason)
    }
}

impl Error for IssueMutationError {}

/// Reject a malformed or ambiguous issue mutation request before GitHub access.
///
/// # Errors
///
/// Returns a stable protected-mutation reason when the requested identity,
/// freshness precondition, or field combination is invalid.
pub fn validate_issue_mutation_request(
    request: &IssueMutationRequest,
) -> Result<(), IssueMutationError> {
    if request.issue == 0 {
        return Err(IssueMutationError::new("invalid-identity"));
    }
    if !valid_timestamp(&request.expected_updated_at) || !is_concrete_state(request.expected_state)
    {
        return Err(IssueMutationError::new("invalid-expected-identity"));
    }
    if request.fields.is_empty() {
        return Err(IssueMutationError::new("missing-allowed-field"));
    }
    validate_special_shape(request)?;
    validate_field_values(request)
}

fn validate_special_shape(request: &IssueMutationRequest) -> Result<(), IssueMutationError> {
    let has_lease = request
        .fields
        .contains(&IssueMutationField::ImplementationLease);
    if request
        .fields
        .contains(&IssueMutationField::UmbrellaConversion)
    {
        let expected = BTreeSet::from([
            IssueMutationField::Title,
            IssueMutationField::Body,
            IssueMutationField::UmbrellaConversion,
        ]);
        if request.fields != expected || request.title.is_none() || request.body.is_none() {
            return Err(IssueMutationError::new(
                "invalid-umbrella-conversion-request",
            ));
        }
    } else if request
        .fields
        .contains(&IssueMutationField::UmbrellaAdoption)
    {
        let expected = BTreeSet::from([
            IssueMutationField::Title,
            IssueMutationField::Body,
            IssueMutationField::UmbrellaAdoption,
        ]);
        if request.fields != expected || request.title.is_none() || request.body.is_none() {
            return Err(IssueMutationError::new("invalid-umbrella-adoption-request"));
        }
    } else if request.fields.contains(&IssueMutationField::NamedBlock) {
        if request.fields != BTreeSet::from([IssueMutationField::NamedBlock])
            || request.marker.as_deref().is_none_or(str::is_empty)
            || request.body.is_none()
        {
            return Err(IssueMutationError::new("invalid-named-block-request"));
        }
    } else if has_lease {
        let allowed = BTreeSet::from([
            IssueMutationField::ImplementationLease,
            IssueMutationField::Title,
        ]);
        if request.body.is_none()
            || request.lease.is_none()
            || request.marker.as_deref() != Some(IMPLEMENTATION_LEASE_MARKER)
            || !request.fields.is_subset(&allowed)
        {
            return Err(IssueMutationError::new(
                "invalid-implementation-lease-request",
            ));
        }
    } else if request.marker.is_some() || request.lease.is_some() {
        return Err(IssueMutationError::new("unexpected-marker-or-lease"));
    }
    Ok(())
}

fn validate_field_values(request: &IssueMutationRequest) -> Result<(), IssueMutationError> {
    let has_named_block = request.fields.contains(&IssueMutationField::NamedBlock);
    let has_lease = request
        .fields
        .contains(&IssueMutationField::ImplementationLease);
    if request.fields.contains(&IssueMutationField::Title) != request.title.is_some() {
        return Err(IssueMutationError::new("invalid-title-request"));
    }
    if !has_named_block
        && !has_lease
        && (request.fields.contains(&IssueMutationField::Body) != request.body.is_some())
    {
        return Err(IssueMutationError::new("invalid-body-request"));
    }
    if request.fields.contains(&IssueMutationField::Labels) != request.labels.is_some() {
        return Err(IssueMutationError::new("invalid-label-request"));
    }
    if !has_named_block
        && !has_lease
        && request.body.is_some()
        && !request.fields.contains(&IssueMutationField::Body)
    {
        return Err(IssueMutationError::new("invalid-body-request"));
    }
    if request.lease.as_ref().is_some_and(|lease| {
        lease.run_id.is_empty() || request.marker.as_deref() != Some(lease.marker.as_str())
    }) {
        return Err(IssueMutationError::new("invalid-lease"));
    }
    Ok(())
}

/// One request to create a new issue, already normalized by its caller.
///
/// Creation has no compare-and-swap precondition: there is no prior state to
/// be stale against. What it shares with a field mutation is the fail-closed
/// redaction of every outbound string and the live-mutation authorization the
/// owner checks before it contacts GitHub.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueCreateRequest {
    pub repository: GitHubRepositoryRef,
    pub title: String,
    pub body: String,
    pub labels: Vec<String>,
}

/// The verified identity of one freshly created issue.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CreatedIssue {
    pub number: u64,
    pub url: String,
    pub id: u64,
}

/// Redact every outbound string of a create request, failing closed.
///
/// # Errors
///
/// Returns `redaction-failed` when a known secret survives the verification
/// pass on the title, the body, or any label.
pub fn redact_issue_create_request(
    request: &IssueCreateRequest,
) -> Result<IssueCreateRequest, IssueMutationError> {
    Ok(IssueCreateRequest {
        repository: request.repository.clone(),
        title: redact_issue_text_outbound(&request.title)?,
        body: redact_issue_text_outbound(&request.body)?,
        labels: request
            .labels
            .iter()
            .map(|label| redact_issue_text_outbound(label))
            .collect::<Result<Vec<String>, IssueMutationError>>()?,
    })
}

/// Redact secret families from one outbound issue string, failing closed.
///
/// Unlike [`redact_issue_mutation_request`], this leaves session and operator
/// paths intact: an issue body legitimately names repository paths, and the
/// Python owner this ports scrubbed secrets only. The caller's newline intent
/// is preserved, so a value that did not end in a newline still does not.
///
/// A truncation marker is not a refusal here, unlike a protected-field
/// mutation: an unterminated private-key block drops the body tail and says so,
/// and a caller that legitimately publishes truncated evidence still files.
/// The verification pass is the fail-closed half, and it cannot fire on
/// redacted text because the replacement token matches no secret family.
///
/// # Errors
///
/// Returns `redaction-failed` when a known secret survives the verification
/// pass.
pub fn redact_issue_text_outbound(value: &str) -> Result<String, IssueMutationError> {
    if value.is_empty() {
        return Ok(String::new());
    }
    let scrubbed = redact_secrets(value).text().to_owned();
    let scrubbed = if value.ends_with('\n') {
        scrubbed
    } else {
        scrubbed.trim_end_matches('\n').to_owned()
    };
    if redact_secrets(&scrubbed).findings().is_empty() {
        Ok(scrubbed)
    } else {
        Err(IssueMutationError::new("redaction-failed"))
    }
}

/// Accept a create read-back only when it names one concrete open issue.
///
/// # Errors
///
/// Returns `invalid-read-back` when GitHub's echo of the created issue lacks
/// the number, node id, or URL every caller of `issue create-one` consumes.
pub fn verify_created_issue(issue: &GitHubIssue) -> Result<CreatedIssue, IssueMutationError> {
    if issue.number == 0
        || issue.id == 0
        || issue.url.is_empty()
        || issue.state != GitHubIssueState::Open
    {
        return Err(IssueMutationError::new("invalid-read-back"));
    }
    Ok(CreatedIssue {
        number: issue.number,
        url: issue.url.clone(),
        id: issue.id,
    })
}

/// Return a redacted copy of a mutation request before it crosses to GitHub.
///
/// # Errors
///
/// Returns `redaction-failed` when a known secret survives the verification
/// pass or when redaction had to truncate an unterminated private-key block.
pub fn redact_issue_mutation_request(
    request: &IssueMutationRequest,
) -> Result<IssueMutationRequest, IssueMutationError> {
    let mut redacted = request.clone();
    redacted.title = request
        .title
        .as_deref()
        .map(redact_outbound)
        .transpose()?
        .map(|title| title.trim_end_matches(['\r', '\n']).to_owned());
    redacted.body = request.body.as_deref().map(redact_outbound).transpose()?;
    Ok(redacted)
}

fn redact_outbound(value: &str) -> Result<String, IssueMutationError> {
    let value = redact(value).text().to_owned();
    if value.contains("[content truncated") || !redact_secrets(&value).findings().is_empty() {
        return Err(IssueMutationError::new("redaction-failed"));
    }
    Ok(value)
}

/// Verify that a redacted request is allowed to replace the selected body.
///
/// # Errors
///
/// Returns a stable refusal when a protected body, named block, lease, or
/// managed-to-umbrella conversion does not prove its required shape.
pub fn verify_authorized_body_change(
    request: &IssueMutationRequest,
    redacted: &IssueMutationRequest,
    before: &IssueMutationSnapshot,
) -> Result<Option<String>, IssueMutationError> {
    let Some(body) = redacted.body.as_deref() else {
        return Ok(None);
    };
    if request
        .fields
        .contains(&IssueMutationField::UmbrellaConversion)
    {
        validate_umbrella_conversion(request, redacted, before, body)?;
    } else if request
        .fields
        .contains(&IssueMutationField::UmbrellaAdoption)
    {
        validate_umbrella_adoption(request, redacted, before, body)?;
    } else if request
        .fields
        .contains(&IssueMutationField::ImplementationLease)
    {
        validate_lease_change(request, before, body)?;
    } else if request.fields.contains(&IssueMutationField::NamedBlock) {
        validate_named_block_change(request, before, body)?;
    } else if has_managed_prefix(&before.title) {
        return Err(IssueMutationError::new("protected-body"));
    }
    Ok(Some(body.to_owned()))
}

fn validate_umbrella_conversion(
    request: &IssueMutationRequest,
    redacted: &IssueMutationRequest,
    before: &IssueMutationSnapshot,
    body: &str,
) -> Result<(), IssueMutationError> {
    let Some(source_title) = umbrella_source_title(&before.title) else {
        return Err(IssueMutationError::new("invalid-umbrella-conversion"));
    };
    let requested_title = request.title.as_deref();
    let redacted_title = redacted.title.as_deref();
    let expected_title = format!("{UMBRELLA_PREFIX}{source_title}");
    if before.state != GitHubIssueState::Open
        || source_title.trim().is_empty()
        || requested_title != Some(expected_title.as_str())
        || redacted_title != requested_title
        || !body.contains(UMBRELLA_PROPOSAL_MARKER)
        || (!before.body.is_empty() && !body.contains(&before.body))
    {
        return Err(IssueMutationError::new("invalid-umbrella-conversion"));
    }
    Ok(())
}

fn validate_umbrella_adoption(
    request: &IssueMutationRequest,
    redacted: &IssueMutationRequest,
    before: &IssueMutationSnapshot,
    body: &str,
) -> Result<(), IssueMutationError> {
    let requested_title = request.title.as_deref();
    let redacted_title = redacted.title.as_deref();
    let Some(source_title) = before.title.strip_prefix(UMBRELLA_PREFIX) else {
        return Err(IssueMutationError::new("invalid-umbrella-adoption"));
    };
    if before.state != GitHubIssueState::Open
        || source_title.trim().is_empty()
        || before.body.contains(UMBRELLA_PROPOSAL_MARKER)
        || requested_title != Some(before.title.as_str())
        || redacted_title != requested_title
        || !body.contains(UMBRELLA_PROPOSAL_MARKER)
        || (!before.body.is_empty() && !body.contains(&before.body))
    {
        return Err(IssueMutationError::new("invalid-umbrella-adoption"));
    }
    Ok(())
}

fn umbrella_source_title(title: &str) -> Option<&str> {
    [MANAGED_PREFIXES[0], MANAGED_PREFIXES[1]]
        .into_iter()
        .find_map(|prefix| title.strip_prefix(prefix))
}

fn validate_lease_change(
    request: &IssueMutationRequest,
    before: &IssueMutationSnapshot,
    body: &str,
) -> Result<(), IssueMutationError> {
    let Some(lease) = request.lease.as_ref() else {
        return Err(IssueMutationError::new(
            "invalid-implementation-lease-request",
        ));
    };
    let old_run_id = implementation_lease_run_id(&before.body);
    let new_run_id = implementation_lease_run_id(body);
    if new_run_id.as_deref() != Some(lease.run_id.as_str())
        || old_run_id
            .as_deref()
            .is_some_and(|run_id| run_id != lease.run_id)
    {
        return Err(IssueMutationError::new("lease-run-mismatch"));
    }
    if strip_implementation_leases(&before.body).trim_end()
        != strip_implementation_leases(body).trim_end()
    {
        return Err(IssueMutationError::new("foreign-lease-body-change"));
    }
    if has_managed_prefix(&before.title) && old_run_id.is_none() {
        return Err(IssueMutationError::new("missing-lease"));
    }
    Ok(())
}

fn validate_named_block_change(
    request: &IssueMutationRequest,
    before: &IssueMutationSnapshot,
    body: &str,
) -> Result<(), IssueMutationError> {
    let Some(marker) = request.marker.as_deref() else {
        return Err(IssueMutationError::new("invalid-named-block-request"));
    };
    if !only_named_block_changed(&before.body, body, marker) {
        return Err(IssueMutationError::new("foreign-marker-or-body-change"));
    }
    if has_managed_prefix(&before.title) && request.lease.is_none() {
        return Err(IssueMutationError::new("missing-lease"));
    }
    Ok(())
}

/// Return whether the snapshot still matches the request's CAS identity.
#[must_use]
pub fn same_mutation_identity(
    snapshot: &IssueMutationSnapshot,
    request: &IssueMutationRequest,
) -> bool {
    snapshot.updated_at == request.expected_updated_at && snapshot.state == request.expected_state
}

/// Return whether the sanitized request changes any requested field.
#[must_use]
pub fn mutation_would_change(
    before: &IssueMutationSnapshot,
    request: &IssueMutationRequest,
    body: Option<&str>,
) -> bool {
    request.fields.contains(&IssueMutationField::Title)
        && before.title != request.title.as_deref().unwrap_or_default()
        || body_field_requested(request) && before.body != body.unwrap_or_default()
        || request.fields.contains(&IssueMutationField::Labels)
            && before.labels != request.labels.clone().unwrap_or_default()
}

/// Return whether a fresh snapshot proves exactly the requested fields changed.
#[must_use]
pub fn mutation_postcondition(
    before: &IssueMutationSnapshot,
    after: &IssueMutationSnapshot,
    request: &IssueMutationRequest,
    body: Option<&str>,
) -> bool {
    after.repository == before.repository
        && after.issue == before.issue
        && after.state == before.state
        && if request.fields.contains(&IssueMutationField::Title) {
            after.title == request.title.as_deref().unwrap_or_default()
        } else {
            after.title == before.title
        }
        && if body_field_requested(request) {
            after.body == body.unwrap_or_default()
        } else {
            after.body == before.body
        }
        && if request.fields.contains(&IssueMutationField::Labels) {
            after.labels == request.labels.clone().unwrap_or_default()
        } else {
            after.labels == before.labels
        }
}

/// Return whether `after` has a strictly newer valid timestamp than `before`.
#[must_use]
pub fn snapshot_is_strictly_newer(
    before: &IssueMutationSnapshot,
    after: &IssueMutationSnapshot,
) -> bool {
    let Ok(before_time) = DateTime::parse_from_rfc3339(&before.updated_at) else {
        return false;
    };
    let Ok(after_time) = DateTime::parse_from_rfc3339(&after.updated_at) else {
        return false;
    };
    after_time > before_time
}

fn body_field_requested(request: &IssueMutationRequest) -> bool {
    request.fields.contains(&IssueMutationField::Body)
        || request.fields.contains(&IssueMutationField::NamedBlock)
        || request
            .fields
            .contains(&IssueMutationField::ImplementationLease)
}

const fn is_concrete_state(state: GitHubIssueState) -> bool {
    matches!(state, GitHubIssueState::Open | GitHubIssueState::Closed)
}

fn valid_timestamp(value: &str) -> bool {
    DateTime::parse_from_rfc3339(value).is_ok()
}

fn only_named_block_changed(before: &str, after: &str, marker: &str) -> bool {
    let Some(old_outer) = strip_named_block(before, marker) else {
        return false;
    };
    let Some(new_outer) = strip_named_block(after, marker) else {
        return false;
    };
    if old_outer.trim_end() == new_outer.trim_end() {
        return true;
    }
    marker == PLAN_MARKER
        && strip_plan_receipts(&old_outer).trim_end() == strip_plan_receipts(&new_outer).trim_end()
}

fn strip_named_block(body: &str, marker: &str) -> Option<String> {
    let lines: Vec<&str> = body.split_inclusive('\n').collect();
    let fenced = balanced_fence_lines(&lines);
    let starts: Vec<usize> = lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!fenced.contains(&index) && is_named_block_marker(line, marker, "start"))
                .then_some(index)
        })
        .collect();
    let ends: Vec<usize> = lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!fenced.contains(&index) && is_named_block_marker(line, marker, "end"))
                .then_some(index)
        })
        .collect();
    match (starts.as_slice(), ends.as_slice()) {
        ([], []) => Some(body.to_owned()),
        ([start], [end]) if end >= start => Some(
            lines[..*start]
                .iter()
                .chain(lines[*end + 1..].iter())
                .copied()
                .collect(),
        ),
        _ => None,
    }
}

fn is_named_block_marker(line: &str, marker: &str, kind: &str) -> bool {
    let line = line.trim_end_matches(['\r', '\n']);
    let line = line.trim_start_matches([' ', '\t']);
    let Some(rest) = line.strip_prefix("<!--") else {
        return false;
    };
    let spaced = rest.trim_start_matches([' ', '\t']);
    if spaced.len() == rest.len() {
        return false;
    }
    let token = format!("larch:{marker}:{kind}");
    let Some(rest) = spaced.strip_prefix(&token) else {
        return false;
    };
    let spaced = rest.trim_start_matches([' ', '\t']);
    if spaced.len() == rest.len() {
        return false;
    }
    spaced.strip_prefix("-->").is_some_and(|rest| {
        rest.chars()
            .all(|character| matches!(character, ' ' | '\t'))
    })
}

fn balanced_fence_lines(lines: &[&str]) -> BTreeSet<usize> {
    let mut fenced = BTreeSet::new();
    let mut opener: Option<(usize, char, usize)> = None;
    for (index, line) in lines.iter().enumerate() {
        let Some((character, length, suffix)) = fence_marker(line) else {
            continue;
        };
        match opener {
            None => opener = Some((index, character, length)),
            Some((start, opener_character, opener_length))
                if character == opener_character
                    && length >= opener_length
                    && suffix.trim().is_empty() =>
            {
                fenced.extend(start + 1..index);
                opener = None;
            }
            Some(_) => {}
        }
    }
    fenced
}

/// Return the sole unfenced plan receipt's lease identity.
///
/// A missing, malformed, fenced, or duplicated receipt proves no admission
/// identity. The caller must refuse rather than choose one candidate.
#[must_use]
pub fn parse_plan_receipt_identity(body: &str) -> Option<PlanReceiptIdentity> {
    let lines: Vec<&str> = body.lines().collect();
    if !fences_are_balanced(&lines) {
        return None;
    }
    let fenced = balanced_fence_lines(&lines);
    let mut found = lines.iter().enumerate().filter_map(|(index, line)| {
        if fenced.contains(&index) {
            return None;
        }
        let captures = PLAN_RECEIPT_RE.captures(line)?;
        Some(PlanReceiptIdentity {
            plan_sha256: captures[1].to_owned(),
            base_sha: captures[2].to_owned(),
        })
    });
    let receipt = found.next()?;
    found.next().is_none().then_some(receipt)
}

fn fences_are_balanced(lines: &[&str]) -> bool {
    let mut opener: Option<(char, usize)> = None;
    for line in lines {
        let Some((character, length, suffix)) = fence_marker(line) else {
            continue;
        };
        match opener {
            None => opener = Some((character, length)),
            Some((opener_character, opener_length))
                if character == opener_character
                    && length >= opener_length
                    && suffix.trim().is_empty() =>
            {
                opener = None;
            }
            Some(_) => {}
        }
    }
    opener.is_none()
}

fn fence_marker(line: &str) -> Option<(char, usize, &str)> {
    let trimmed = line.trim();
    let character = trimmed.chars().next()?;
    if !matches!(character, '`' | '~') {
        return None;
    }
    let length = trimmed
        .chars()
        .take_while(|current| *current == character)
        .count();
    (length >= 3).then_some((character, length, &trimmed[length..]))
}

fn strip_plan_receipts(body: &str) -> String {
    let lines: Vec<&str> = body.split_inclusive('\n').collect();
    let fenced = balanced_fence_lines(&lines);
    lines
        .iter()
        .enumerate()
        .filter(|(index, line)| {
            fenced.contains(index) || !PLAN_RECEIPT_RE.is_match(line.trim_end_matches('\n'))
        })
        .map(|(_, line)| *line)
        .collect()
}

fn implementation_lease_run_id(body: &str) -> Option<String> {
    let lines: Vec<&str> = body.split_inclusive('\n').collect();
    let fenced = balanced_fence_lines(&lines);
    let candidates: Vec<&str> = lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!fenced.contains(&index)
                && line
                    .trim_end_matches(['\r', '\n'])
                    .starts_with("<!-- larch:implementation-lease"))
            .then_some(*line)
        })
        .collect();
    if candidates.len() != 1 {
        return None;
    }
    IMPLEMENTATION_LEASE_RE
        .captures(candidates[0].trim_end_matches(['\r', '\n']))
        .and_then(|captures| captures.get(1))
        .map(|capture| capture.as_str().to_owned())
}

fn strip_implementation_leases(body: &str) -> String {
    let lines: Vec<&str> = body.split_inclusive('\n').collect();
    let fenced = balanced_fence_lines(&lines);
    lines
        .iter()
        .enumerate()
        .filter(|(index, line)| {
            fenced.contains(index)
                || !IMPLEMENTATION_LEASE_RE.is_match(line.trim_end_matches(['\r', '\n']))
        })
        .map(|(_, line)| *line)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::{
        IssueMutationField, IssueMutationRequest, IssueMutationSnapshot, mutation_postcondition,
        parse_plan_receipt_identity, redact_issue_text_outbound, same_mutation_identity,
        snapshot_is_strictly_newer, validate_issue_mutation_request, verify_authorized_body_change,
        verify_created_issue,
    };
    use crate::{GitHubIssue, GitHubIssueState, GitHubRepositoryRef};
    use std::collections::BTreeSet;

    fn snapshot() -> IssueMutationSnapshot {
        IssueMutationSnapshot {
            repository: GitHubRepositoryRef::new("owner", "repo").expect("valid repository"),
            issue: 7,
            title: String::from("Regular issue"),
            body: String::from("Body"),
            labels: BTreeSet::new(),
            state: GitHubIssueState::Open,
            updated_at: String::from("2026-07-19T00:00:00Z"),
        }
    }

    fn title_request() -> IssueMutationRequest {
        IssueMutationRequest {
            repository: GitHubRepositoryRef::new("owner", "repo").expect("valid repository"),
            issue: 7,
            expected_updated_at: String::from("2026-07-19T00:00:00Z"),
            expected_state: GitHubIssueState::Open,
            fields: BTreeSet::from([IssueMutationField::Title]),
            title: Some(String::from("Renamed")),
            body: None,
            labels: None,
            marker: None,
            lease: None,
        }
    }

    #[test]
    fn request_validation_rejects_invalid_field_shapes() {
        let mut request = title_request();
        request.fields.clear();
        assert_eq!(
            validate_issue_mutation_request(&request)
                .expect_err("empty field set must fail")
                .reason(),
            "missing-allowed-field"
        );

        let mut request = title_request();
        request.body = Some(String::from("unexpected"));
        assert_eq!(
            validate_issue_mutation_request(&request)
                .expect_err("unspecified body must fail")
                .reason(),
            "invalid-body-request"
        );
    }

    #[test]
    fn replace_labels_copies_snapshot_identity_and_only_sets_labels() {
        let snapshot = snapshot();
        let labels = BTreeSet::from(["difficulty:hard".to_owned()]);
        let request = IssueMutationRequest::replace_labels(&snapshot, labels.clone());
        assert_eq!(request.repository, snapshot.repository);
        assert_eq!(request.issue, snapshot.issue);
        assert_eq!(request.expected_updated_at, snapshot.updated_at);
        assert_eq!(request.expected_state, snapshot.state);
        assert_eq!(request.fields, BTreeSet::from([IssueMutationField::Labels]));
        assert_eq!(request.labels.as_ref(), Some(&labels));
        assert!(request.title.is_none());
        assert!(request.body.is_none());
        assert!(request.marker.is_none());
        assert!(request.lease.is_none());
        assert_eq!(validate_issue_mutation_request(&request), Ok(()));
    }

    #[test]
    fn protected_named_block_comparison_ignores_fenced_examples() {
        let mut before = snapshot();
        before.title = String::from("[IMPLEMENTING] Protected");
        before.body = concat!(
            "prefix\n",
            "```text\n",
            "<!-- larch:plan:start -->\n",
            "example\n",
            "<!-- larch:plan:end -->\n",
            "```\n",
            "<!-- larch:plan:start -->\n",
            "old\n",
            "<!-- larch:plan:end -->\n",
        )
        .to_owned();
        let mut request = title_request();
        request.fields = BTreeSet::from([IssueMutationField::NamedBlock]);
        request.title = None;
        request.body = Some(before.body.replace("\nold\n", "\nnew\n"));
        request.marker = Some(String::from("plan"));
        request.lease = Some(super::IssueMutationLease {
            run_id: String::from("run-7"),
            marker: String::from("plan"),
        });
        let redacted = request.clone();
        assert_eq!(
            verify_authorized_body_change(&request, &redacted, &before)
                .expect("only the live named block changed"),
            request.body
        );
    }

    #[test]
    fn umbrella_adoption_keeps_the_recordless_source_title_and_context() {
        let mut before = snapshot();
        before.title = String::from("[UMBRELLA] External split");
        before.body = String::from("External context\n");
        let mut request = title_request();
        request.fields = BTreeSet::from([
            IssueMutationField::Title,
            IssueMutationField::Body,
            IssueMutationField::UmbrellaAdoption,
        ]);
        request.title = Some(before.title.clone());
        request.body = Some(format!(
            "{}<!-- larch:umbrella-proposal v1 -->\n",
            before.body
        ));
        let redacted = request.clone();

        assert!(validate_issue_mutation_request(&request).is_ok());
        assert_eq!(
            verify_authorized_body_change(&request, &redacted, &before)
                .expect("the guarded adoption is valid"),
            request.body
        );

        request.title = Some(String::from("[UMBRELLA] Renamed split"));
        assert_eq!(
            verify_authorized_body_change(&request, &redacted, &before)
                .expect_err("adoption must preserve the external title")
                .reason(),
            "invalid-umbrella-adoption"
        );

        let mut existing_record = before;
        existing_record
            .body
            .push_str("<!-- larch:umbrella-proposal v1 -->\n");
        assert_eq!(
            verify_authorized_body_change(&redacted, &redacted, &existing_record)
                .expect_err("a recorded umbrella resumes instead of adopting")
                .reason(),
            "invalid-umbrella-adoption"
        );
    }

    #[test]
    fn plan_receipt_identity_requires_one_exact_unfenced_receipt() {
        let receipt = format!(
            "<!-- larch:plan-receipt v1 plan_sha256={} base_sha={} blockers_sha256={} owners_sha256={} -->",
            "b".repeat(64),
            "a".repeat(40),
            "c".repeat(64),
            "d".repeat(64),
        );
        assert_eq!(
            parse_plan_receipt_identity(&receipt),
            Some(super::PlanReceiptIdentity {
                plan_sha256: "b".repeat(64),
                base_sha: "a".repeat(40),
            })
        );
        assert!(parse_plan_receipt_identity(&format!("{receipt}\n{receipt}")).is_none());
        assert!(parse_plan_receipt_identity(&format!("```text\n{receipt}\n```")).is_none());
        assert!(parse_plan_receipt_identity(&format!("```text\n{receipt}")).is_none());
        assert!(parse_plan_receipt_identity(&receipt.replace(" -->", " injected -->")).is_none());
    }

    #[test]
    fn implementation_lease_changes_are_bound_to_the_owning_run() {
        let mut before = snapshot();
        before.title = String::from("[IMPLEMENTING] Protected");
        before.body = format!(
            "<!-- larch:implementation-lease v1 run_id=run-7 branch=feature/owner base={} plan={} updated_at=2026-07-19T00:00:00Z -->\n",
            "a".repeat(40),
            "b".repeat(64)
        );
        let mut request = title_request();
        request.fields = BTreeSet::from([IssueMutationField::ImplementationLease]);
        request.title = None;
        request.body = Some(before.body.replace("00:00:00Z", "01:00:00Z"));
        request.marker = Some(String::from("implementation-lease"));
        request.lease = Some(super::IssueMutationLease {
            run_id: String::from("run-7"),
            marker: String::from("implementation-lease"),
        });
        let redacted = request.clone();
        assert_eq!(
            verify_authorized_body_change(&request, &redacted, &before)
                .expect("same-run lease update succeeds"),
            request.body
        );
        request.lease.as_mut().expect("lease").run_id = String::from("other-run");
        assert_eq!(
            verify_authorized_body_change(&request, &redacted, &before)
                .expect_err("foreign lease must fail")
                .reason(),
            "lease-run-mismatch"
        );
    }

    #[test]
    fn freshness_requires_matching_identity_and_a_strictly_newer_timestamp() {
        let before = snapshot();
        let request = title_request();
        assert!(same_mutation_identity(&before, &request));

        let mut after = before.clone();
        after.updated_at = String::from("2026-07-19T00:00:01Z");
        assert!(snapshot_is_strictly_newer(&before, &after));
        assert!(!snapshot_is_strictly_newer(&after, &before));
    }

    #[test]
    fn postcondition_rejects_changes_outside_the_requested_fields() {
        let before = snapshot();
        let request = title_request();
        let mut after = before.clone();
        after.title = String::from("Renamed");
        after.updated_at = String::from("2026-07-19T00:00:01Z");
        assert!(mutation_postcondition(&before, &after, &request, None));

        after.labels.insert(String::from("audit-report"));
        assert!(!mutation_postcondition(&before, &after, &request, None));
        after.labels.clear();
        after.state = GitHubIssueState::Closed;
        assert!(!mutation_postcondition(&before, &after, &request, None));
        after.state = GitHubIssueState::Open;
        after.body = String::from("concurrent body");
        assert!(!mutation_postcondition(&before, &after, &request, None));
    }
    #[test]
    fn outbound_issue_text_scrubs_secrets_keeps_paths_and_preserves_newline_intent() {
        assert_eq!(redact_issue_text_outbound("").expect("empty"), "");
        assert_eq!(
            redact_issue_text_outbound("leak ghp_abcdefghijklmnopqrstuvwxyz0123456789 here")
                .expect("scrubbed"),
            "leak <REDACTED-TOKEN> here"
        );
        // Operator and session paths survive: an issue body names repository
        // paths, and the Python owner scrubbed secrets only.
        let path = "see /Users/operator/clone/python/larch/issue/issue_create.py";
        assert_eq!(redact_issue_text_outbound(path).expect("kept"), path);
        assert_eq!(
            redact_issue_text_outbound("body\n").expect("kept"),
            "body\n"
        );
        assert_eq!(redact_issue_text_outbound("body").expect("kept"), "body");
        // A truncation marker files rather than refusing.
        let truncated = "evidence\n\n[content truncated to 10 characters]\n";
        assert_eq!(
            redact_issue_text_outbound(truncated).expect("kept"),
            truncated
        );
    }

    #[test]
    fn a_create_read_back_needs_a_number_a_node_id_a_url_and_an_open_state() {
        let created = GitHubIssue {
            id: 70,
            number: 7,
            title: String::from("T"),
            body: String::new(),
            state: GitHubIssueState::Open,
            state_reason: String::new(),
            url: String::from("https://github.com/owner/repo/issues/7"),
            author: String::new(),
            labels: Vec::new(),
            comments: 0,
            created_at: String::new(),
            closed_at: String::new(),
            updated_at: String::from("2026-07-19T00:00:00Z"),
            is_pull_request: false,
        };
        let verified = verify_created_issue(&created).expect("a usable echo");
        assert_eq!((verified.number, verified.id), (7, 70));
        assert_eq!(verified.url, created.url);

        for mutate in [
            (|issue: &mut GitHubIssue| issue.number = 0) as fn(&mut GitHubIssue),
            |issue: &mut GitHubIssue| issue.id = 0,
            |issue: &mut GitHubIssue| issue.url = String::new(),
            |issue: &mut GitHubIssue| issue.state = GitHubIssueState::Closed,
        ] {
            let mut broken = created.clone();
            mutate(&mut broken);
            assert_eq!(
                verify_created_issue(&broken)
                    .expect_err("an unusable echo")
                    .reason(),
                "invalid-read-back"
            );
        }
    }
}
