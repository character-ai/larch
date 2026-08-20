//! Pure clarification round-trip logic for issue-anchored plans (#8587).
//!
//! This is the wire-exact half of the `/design` clarify loop: the
//! `larch:clarify-request` / `larch:clarify-response` comment markers, the
//! ordered-event state machine, and the request-body extraction. The CLI verbs
//! and the fetch/publish orchestrator live in `larch-cli`; every GitHub effect
//! and file write stays out of this module so the state machine stays testable
//! offline. Ported from `python/larch/design/clarify.py`.

use std::sync::LazyLock;

use regex::Regex;

/// The clarification label a stalled plan carries until a response lands.
pub const CLARIFY_LABEL_NAME: &str = "needs-design-clarification";
/// The label color, kept byte-identical with the retired Python owner.
pub const CLARIFY_LABEL_COLOR: &str = "D73A4A";
/// The label description shown on the GitHub issue.
pub const CLARIFY_LABEL_DESCRIPTION: &str =
    "Issue plan requires clarification before /implement can proceed";

/// One clarify marker: a request opening a thread or a response closing it.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ClarifyKind {
    /// A `larch:clarify-request` marker.
    Request,
    /// A `larch:clarify-response` marker.
    Response,
}

/// One ordered marker event: its kind and the positive thread id it carries.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ClarifyEvent {
    /// Whether this event opens (request) or closes (response) a thread.
    pub kind: ClarifyKind,
    /// The positive thread identifier the marker declared.
    pub id: u64,
}

/// The evaluated clarify thread state plus the last request/response ids.
///
/// `last_request_id` and `last_response_id` are text (empty when none) so the
/// KEY=value contract can emit them verbatim, matching the Python `NamedTuple`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClarifyState {
    /// One of `clean`, `awaiting-response`, `response-pending`, `ambiguous`.
    pub state: String,
    /// The most recent request id as text, or empty.
    pub last_request_id: String,
    /// The most recent response id as text, or empty.
    pub last_response_id: String,
}

impl ClarifyState {
    fn new(state: &str, last_request_id: &str, last_response_id: &str) -> Self {
        Self {
            state: state.to_owned(),
            last_request_id: last_request_id.to_owned(),
            last_response_id: last_response_id.to_owned(),
        }
    }
}

/// The marker grammar: whitespace-flexible, positive non-zero id, exact tags.
static MARKER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*<!--\s+larch:clarify-(request|response)\s+id=([1-9][0-9]*)\s*-->\s*$")
        .expect("clarify marker regex compiles")
});

/// Normalize a comment body's first line the way the Python owner did.
///
/// The first physical line (up to the first `\n`) has a leading BOM removed and
/// a trailing CR stripped, so a CRLF body or a BOM-prefixed marker still parses.
fn first_line_normalized(body: &str) -> &str {
    let first = body.split_once('\n').map_or(body, |(head, _tail)| head);
    first
        .strip_prefix('\u{feff}')
        .unwrap_or(first)
        .trim_end_matches('\r')
}

/// Parse one comment's first line into a clarify marker, if it is one.
fn parse_marker(first_line: &str) -> Option<ClarifyEvent> {
    let captures = MARKER_RE.captures(first_line)?;
    let kind = match &captures[1] {
        "request" => ClarifyKind::Request,
        _ => ClarifyKind::Response,
    };
    // The `[1-9][0-9]*` capture cannot overflow a realistic comment id, but a
    // pathological run of digits would; treat an unparseable id as no marker.
    let id: u64 = captures[2].parse().ok()?;
    Some(ClarifyEvent { kind, id })
}

/// Collect ordered marker events from comment bodies in listing order.
///
/// A comment whose first line is not a clarify marker is skipped, matching the
/// Python `_events_from_comments`.
pub fn events_from_comment_bodies<I, S>(bodies: I) -> Vec<ClarifyEvent>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    bodies
        .into_iter()
        .filter_map(|body| parse_marker(first_line_normalized(body.as_ref())))
        .collect()
}

/// Return the request body a `comment-fetch` writes, if `id` names a request.
///
/// The remainder is every byte after the first newline of the matching request
/// comment (empty when the comment is a single line). `comment_id` is the
/// positive-integer text the caller validated. Ported from
/// `clarify_comment_fetch`'s per-row loop.
pub fn request_body_remainder(body: &str, comment_id: &str) -> Option<String> {
    let (first, remainder) = match body.split_once('\n') {
        Some((head, tail)) => (head, Some(tail)),
        None => (body, None),
    };
    let normalized = first
        .strip_prefix('\u{feff}')
        .unwrap_or(first)
        .trim_end_matches('\r');
    let captures = MARKER_RE.captures(normalized)?;
    if &captures[1] != "request" || &captures[2] != comment_id {
        return None;
    }
    Some(remainder.unwrap_or("").to_owned())
}

/// Evaluate ordered marker events into a clarify thread state.
///
/// A verbatim port of `_evaluate_events`: non-monotonic ids, duplicate
/// request/response ids, and orphan responses all mark the thread ambiguous; a
/// satisfied latest request with no earlier gap is `response-pending`.
#[must_use]
pub fn evaluate_events(events: &[ClarifyEvent]) -> ClarifyState {
    let mut ambiguous = false;
    let mut max_so_far: u64 = 0;
    let mut last_req: Option<u64> = None;
    let mut last_req_idx: Option<usize> = None;
    let mut last_resp = String::new();
    let mut request_ids: Vec<u64> = Vec::new();
    let mut response_ids: Vec<u64> = Vec::new();

    for (idx, event) in events.iter().enumerate() {
        if event.id < max_so_far {
            ambiguous = true;
        }
        max_so_far = max_so_far.max(event.id);
        match event.kind {
            ClarifyKind::Request => {
                request_ids.push(event.id);
                last_req = Some(event.id);
                last_req_idx = Some(idx);
            }
            ClarifyKind::Response => {
                response_ids.push(event.id);
                last_resp = event.id.to_string();
            }
        }
    }

    if has_duplicate(&request_ids) || has_duplicate(&response_ids) {
        ambiguous = true;
    }

    for (idx, event) in events.iter().enumerate() {
        if event.kind != ClarifyKind::Response {
            continue;
        }
        let seen = events[..idx]
            .iter()
            .any(|prior| prior.kind == ClarifyKind::Request && prior.id == event.id);
        if !seen {
            ambiguous = true;
        }
    }

    let max_all = events.iter().map(|event| event.id).max().unwrap_or(0);

    let last_req_text = last_req.map(|id| id.to_string()).unwrap_or_default();
    if ambiguous {
        return ClarifyState::new("ambiguous", &last_req_text, &last_resp);
    }
    let (Some(rid), Some(req_idx)) = (last_req, last_req_idx) else {
        return ClarifyState::new("clean", "", "");
    };

    let has_match = events[req_idx + 1..]
        .iter()
        .any(|event| event.kind == ClarifyKind::Response && event.id == rid);
    if !has_match {
        return ClarifyState::new("awaiting-response", &rid.to_string(), &last_resp);
    }

    let gap_unsat = (1..rid).any(|mid| {
        request_ids.contains(&mid) && !response_ids.contains(&mid)
    });
    if gap_unsat {
        return ClarifyState::new("ambiguous", &rid.to_string(), &last_resp);
    }
    if rid == max_all {
        return ClarifyState::new("response-pending", &rid.to_string(), &last_resp);
    }
    ClarifyState::new("ambiguous", &rid.to_string(), &last_resp)
}

/// True when `ids` contains any value more than once.
fn has_duplicate(ids: &[u64]) -> bool {
    let mut sorted = ids.to_vec();
    sorted.sort_unstable();
    sorted.windows(2).any(|pair| pair[0] == pair[1])
}

/// Evaluate a clarify thread directly from comment bodies in listing order.
#[must_use]
pub fn evaluate_comment_bodies<I, S>(bodies: I) -> ClarifyState
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    evaluate_events(&events_from_comment_bodies(bodies))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn state(bodies: &[&str]) -> ClarifyState {
        evaluate_comment_bodies(bodies.iter().copied())
    }

    #[test]
    fn clean_when_no_markers() {
        assert_eq!(state(&[]), ClarifyState::new("clean", "", ""));
    }

    #[test]
    fn id_zero_is_ignored() {
        assert_eq!(
            state(&["<!-- larch:clarify-request id=0 -->"]),
            ClarifyState::new("clean", "", ""),
        );
    }

    #[test]
    fn single_request_awaits_response() {
        assert_eq!(
            state(&["<!-- larch:clarify-request id=1 -->"]),
            ClarifyState::new("awaiting-response", "1", ""),
        );
    }

    #[test]
    fn matched_request_is_response_pending() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
            ]),
            ClarifyState::new("response-pending", "1", "1"),
        );
    }

    #[test]
    fn duplicate_request_is_ambiguous() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-request id=1 -->",
            ]),
            ClarifyState::new("ambiguous", "1", ""),
        );
    }

    #[test]
    fn duplicate_response_is_ambiguous() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
            ]),
            ClarifyState::new("ambiguous", "1", "1"),
        );
    }

    #[test]
    fn orphan_response_is_ambiguous() {
        assert_eq!(
            state(&["<!-- larch:clarify-response id=1 -->"]),
            ClarifyState::new("ambiguous", "", "1"),
        );
    }

    #[test]
    fn non_monotonic_ids_are_ambiguous() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=2 -->",
                "<!-- larch:clarify-request id=1 -->",
            ]),
            ClarifyState::new("ambiguous", "1", ""),
        );
    }

    #[test]
    fn gap_with_high_response_is_ambiguous() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-request id=2 -->",
                "<!-- larch:clarify-response id=2 -->",
            ]),
            ClarifyState::new("ambiguous", "2", "2"),
        );
    }

    #[test]
    fn multiple_done_rounds_are_response_pending() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
                "<!-- larch:clarify-request id=2 -->",
                "<!-- larch:clarify-response id=2 -->",
            ]),
            ClarifyState::new("response-pending", "2", "2"),
        );
    }

    #[test]
    fn multiple_rounds_in_progress_awaits() {
        assert_eq!(
            state(&[
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
                "<!-- larch:clarify-request id=2 -->",
            ]),
            ClarifyState::new("awaiting-response", "2", "1"),
        );
    }

    #[test]
    fn flexible_whitespace_matches() {
        assert_eq!(
            state(&["<!--   larch:clarify-request   id=1   -->"]),
            ClarifyState::new("awaiting-response", "1", ""),
        );
    }

    #[test]
    fn first_line_only_marker_is_used() {
        assert_eq!(
            state(&["<!-- larch:clarify-request id=3 -->\nquestion body\nline two"]),
            ClarifyState::new("awaiting-response", "3", ""),
        );
    }

    #[test]
    fn bom_and_crlf_first_line_still_parses() {
        assert_eq!(
            state(&["\u{feff}<!-- larch:clarify-request id=1 -->\r\nbody"]),
            ClarifyState::new("awaiting-response", "1", ""),
        );
    }

    #[test]
    fn request_body_remainder_returns_tail() {
        let body = "<!-- larch:clarify-request id=2 -->\nlatest question";
        assert_eq!(
            request_body_remainder(body, "2"),
            Some("latest question".to_owned()),
        );
    }

    #[test]
    fn request_body_remainder_single_line_is_empty() {
        assert_eq!(
            request_body_remainder("<!-- larch:clarify-request id=2 -->", "2"),
            Some(String::new()),
        );
    }

    #[test]
    fn request_body_remainder_rejects_wrong_id_or_kind() {
        let body = "<!-- larch:clarify-request id=2 -->\nq";
        assert_eq!(request_body_remainder(body, "3"), None);
        let response = "<!-- larch:clarify-response id=2 -->\nr";
        assert_eq!(request_body_remainder(response, "2"), None);
    }
}
