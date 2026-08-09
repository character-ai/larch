//! Issue-title identity: protected lifecycle prefixes, eligibility, and markers.
//!
//! Ports Python `larch.issue.title_match` and the title half of
//! `larch.issue.issue_wire`. Prefix comparisons are case insensitive wherever
//! Python casefolds, and a rewritten title always preserves the original
//! spelling of the prefix it found.

use std::sync::LazyLock;

use regex::Regex;

use crate::text::is_python_whitespace;

/// The normalized bug prefix.
pub const BUG_PREFIX: &str = "[BUG]";
/// The active implementation lifecycle prefix.
pub const IMPLEMENTING_PREFIX: &str = "[IMPLEMENTING] ";
/// The completed implementation lifecycle prefix.
pub const DONE_PREFIX: &str = "[DONE] ";
/// The blocked implementation lifecycle prefix.
pub const STALLED_PREFIX: &str = "[STALLED] ";
/// The managed umbrella identity prefix.
pub const UMBRELLA_PREFIX: &str = "[UMBRELLA] ";

/// Every managed or legacy tracking lifecycle prefix, in match order.
///
/// The order mirrors Python's `LIFECYCLE_PREFIXES`: the tracking states, then
/// the debate states, then the two legacy tokens.
pub const LIFECYCLE_PREFIXES: [&str; 9] = [
    "[DESIGNING] ",
    "[DESIGNED] ",
    IMPLEMENTING_PREFIX,
    DONE_PREFIX,
    STALLED_PREFIX,
    "[DEBATING] ",
    "[DEBATED] ",
    "[IN PROGRESS] ",
    "[PLANNED] ",
];

/// The lifecycle prefixes a `[BUG]` title may carry ahead of its bug tag.
pub const BUG_TITLE_LIFECYCLE_PREFIXES: [&str; 6] = [
    DONE_PREFIX,
    "[DESIGNED] ",
    IMPLEMENTING_PREFIX,
    STALLED_PREFIX,
    "[DEBATING] ",
    "[DEBATED] ",
];

/// Lifecycle names a signal marker is inserted after, in match order.
const SIGNAL_INSERT_PREFIXES: [&str; 9] = [
    "DEBATING",
    "DEBATED",
    "DESIGNING",
    "DESIGNED",
    "IMPLEMENTING",
    "DONE",
    "STALLED",
    "IN PROGRESS",
    "PLANNED",
];

/// Title openings that mark an issue as an archival narrative artifact.
const ARCHIVAL_TITLE_PREFIXES: [&str; 4] =
    ["research ", "[research] ", "investigate ", "[investigate] "];

/// The `jq` archival-eligibility filter, byte compatible with the legacy shell
/// helper that still consumes it.
pub const ARCHIVAL_JQ_FILTER: &str = r#"select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\[.*report\] "))) | not)"#;

fn lifecycle_reject_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^\[((?i-u:IMPLEMENTING|DONE|DESIGNING|DESIGNED|DEBATING|DEBATED))\]")
            .expect("lifecycle-reject regex should compile")
    });
    &PATTERN
}

fn archival_report_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^\[.*(?i-u:report)\] ").expect("archival-report regex should compile")
    });
    &PATTERN
}

fn brainstorm_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^(?i-u:brainstorm)([^A-Za-z]|$)").expect("brainstorm regex should compile")
    });
    &PATTERN
}

fn square_bracket_prefix_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        // `[\s\x1c-\x1f]` is Python's `\s` for `str`: Unicode White_Space plus
        // the four information separators, which Rust's `\s` leaves out.
        Regex::new(r"^[\s\x1c-\x1f]*((?:\[[A-Za-z0-9 _.-]+\][\s\x1c-\x1f]*)+)")
            .expect("square-bracket prefix regex should compile")
    });
    &PATTERN
}

fn square_bracket_token_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"\[[A-Za-z0-9 _.-]+\]").expect("square-bracket token regex should compile")
    });
    &PATTERN
}

/// Return the uppercased lifecycle marker that forbids archival, or `None`.
///
/// A title such as `"  [done] fix"` yields `Some("[DONE]")`.
#[must_use]
pub fn title_lifecycle_reject_marker(title: &str) -> Option<String> {
    lifecycle_reject_pattern()
        .captures(trim_leading_whitespace(title))
        .and_then(|captures| captures.get(1))
        .map(|state| format!("[{}]", state.as_str().to_ascii_uppercase()))
}

/// Return whether the title opens with a bracketed report tag.
#[must_use]
pub fn title_has_archival_report_prefix(title: &str) -> bool {
    archival_report_pattern().is_match(trim_leading_whitespace(title))
}

/// Return whether the title names an archival research, investigation, or
/// report issue.
///
/// This is the predicate behind [`ARCHIVAL_JQ_FILTER`], expressed for readers
/// that hold the title in memory. Such issues are narrative artifacts, so a
/// dedup snapshot leaves them out rather than proposing them as duplicates.
#[must_use]
pub fn title_is_archival(title: &str) -> bool {
    let lowered = trim_leading_whitespace(title).to_lowercase();
    ARCHIVAL_TITLE_PREFIXES
        .iter()
        .any(|prefix| lowered.starts_with(prefix))
        || title_has_archival_report_prefix(&lowered)
}

/// Return whether the title opens with the `brainstorm` word.
#[must_use]
pub fn title_starts_with_brainstorm(title: &str) -> bool {
    brainstorm_pattern().is_match(trim_leading_whitespace(title))
}

/// Prepend `prefix` to `title`, absorbing the prefix the title already carries.
///
/// The rewrite is idempotent and case insensitive, so `"[oos] Fix"` under
/// `"[OOS]"` becomes `"[OOS] Fix"` rather than `"[OOS] [oos] Fix"`, and the
/// caller's spelling of the prefix always wins. An empty prefix leaves the
/// title untouched. This is the single normalization `/issue` relies on to
/// deduplicate prefixes it may have applied already.
#[must_use]
pub fn normalize_title_prefix(title: &str, prefix: &str) -> String {
    if prefix.is_empty() {
        return title.to_owned();
    }
    // Compare over the prefix's own character count so a title whose leading
    // characters lowercase to the prefix is absorbed. Python sliced the
    // original title by the prefix length after lowercasing both sides; the
    // two agree for every character whose lowercase form is one character.
    let width = prefix.chars().count();
    let head: String = title.chars().take(width).collect();
    let body = if head.to_lowercase() == prefix.to_lowercase() {
        title
            .chars()
            .skip(width)
            .collect::<String>()
            .trim_start_matches(is_python_whitespace)
            .to_owned()
    } else {
        title.to_owned()
    };
    format!("{prefix} {body}")
}

/// Insert `[marker]` into `title`, after a lifecycle prefix when one is present.
///
/// The insert is idempotent: a title that already carries the marker in its
/// leading bracket run is returned unchanged. The lifecycle prefix keeps its
/// original spelling even when it was matched case insensitively.
#[must_use]
pub fn insert_signal_marker(title: &str, marker: &str) -> String {
    let marker_block = format!("[{marker}]");
    if title.is_empty() {
        return marker_block;
    }
    let mut rest = title;
    while rest.starts_with('[') {
        let Some(close) = rest.find("] ") else {
            break;
        };
        if rest[..=close] == marker_block {
            return title.to_owned();
        }
        rest = &rest[close + 2..];
    }
    for prefix in SIGNAL_INSERT_PREFIXES {
        let block_len = prefix.len() + 3;
        if title.len() < block_len || !title.is_char_boundary(block_len) {
            continue;
        }
        if title[..block_len].eq_ignore_ascii_case(&format!("[{prefix}] ")) {
            return format!(
                "{} [{marker}] {}",
                &title[..block_len - 1],
                &title[block_len..]
            );
        }
    }
    format!("[{marker}] {title}")
}

/// Return whether a title is a normalized `[BUG]` title.
///
/// Any run of lifecycle prefixes ahead of the bug tag is stripped first.
#[must_use]
pub fn bug_title_match(title: &str) -> bool {
    let mut normalized = trim_leading_whitespace(title);
    loop {
        let Some(stripped) = BUG_TITLE_LIFECYCLE_PREFIXES
            .iter()
            .find_map(|prefix| strip_prefix_ignore_ascii_case(normalized, prefix))
        else {
            break;
        };
        normalized = trim_leading_whitespace(stripped);
    }
    strip_prefix_ignore_ascii_case(normalized, BUG_PREFIX).is_some()
}

/// Strip exactly one managed or legacy tracking lifecycle prefix.
#[must_use]
pub fn strip_lifecycle_prefix(title: &str) -> &str {
    LIFECYCLE_PREFIXES
        .iter()
        .find_map(|prefix| title.strip_prefix(prefix))
        .unwrap_or(title)
}

/// Return the first managed or legacy lifecycle prefix in `title`, or `""`.
#[must_use]
pub fn detect_lifecycle_prefix(title: &str) -> &'static str {
    LIFECYCLE_PREFIXES
        .into_iter()
        .find(|prefix| title.starts_with(prefix))
        .unwrap_or("")
}

/// Return the joined leading `[TAG]` tokens from a title, or `""`.
///
/// `"[BUG] foo"` yields `"[BUG]"` and `"[FEATURE][A] x"` yields `"[FEATURE][A]"`.
/// Whitespace between tokens is dropped so the caller can rejoin them.
#[must_use]
pub fn leading_square_bracket_prefix(title: &str) -> String {
    square_bracket_prefix_pattern()
        .captures(title)
        .and_then(|captures| captures.get(1))
        .map(|run| {
            square_bracket_token_pattern()
                .find_iter(run.as_str())
                .map(|token| token.as_str())
                .collect()
        })
        .unwrap_or_default()
}

/// Insert `tag` after a leading bug prefix, or prepend it.
///
/// A title that already mentions `tag` anywhere, in any case, is unchanged.
#[must_use]
pub fn insert_tag_after_bug_prefix(title: &str, tag: &str) -> String {
    if title.to_lowercase().contains(&tag.to_lowercase()) {
        return title.to_owned();
    }
    strip_prefix_ignore_ascii_case(title, BUG_PREFIX).map_or_else(
        || format!("{tag} {title}"),
        |rest| format!("{BUG_PREFIX} {tag} {}", trim_leading_whitespace(rest)),
    )
}

fn strip_prefix_ignore_ascii_case<'a>(text: &'a str, prefix: &str) -> Option<&'a str> {
    if text.len() < prefix.len() || !text.is_char_boundary(prefix.len()) {
        return None;
    }
    text[..prefix.len()]
        .eq_ignore_ascii_case(prefix)
        .then(|| &text[prefix.len()..])
}

/// Trim the leading run Python's `str.lstrip()` would remove.
fn trim_leading_whitespace(text: &str) -> &str {
    text.trim_start_matches(is_python_whitespace)
}
