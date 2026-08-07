//! Effect-free entry-gate, issue-lifecycle, and blocker-prose rules.
//!
//! These are the decisions `/implement` admission makes before any remote side
//! effect: which entry gate a branch earns, whether an issue title carries a
//! lifecycle prefix that forbids a fresh run, and which issue numbers a prose
//! document declares as blockers. Every function here is pure; the filesystem,
//! Git, and GitHub reads live in the command layer.

use std::sync::LazyLock;

use regex::Regex;

use crate::{DONE_PREFIX, IMPLEMENTING_PREFIX};

/// Resolved entry-gate decision for one `/implement` or `/design` entry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GateDecision {
    /// `strict` when the run must pass the clean-main contract, else `continue`.
    pub entry_gate: &'static str,
    /// `true` when the branch check is waived downstream.
    pub skip_branch_check: &'static str,
}

/// Resolve the entry gate from validated branch inputs.
///
/// # Errors
/// Returns the exact `GATE_ERROR` message for an invalid mode, an empty user
/// prefix, a non-boolean flag, or `--branch-info-supplied` under `mode=implement`.
pub fn entry_gate(
    mode: &str,
    is_main: &str,
    is_user_branch: &str,
    user_prefix: &str,
    branch_info_supplied: Option<&str>,
) -> Result<GateDecision, String> {
    if mode != "implement" && mode != "design" {
        return Err(format!("invalid mode: {mode}"));
    }
    if user_prefix.is_empty() {
        return Err("--user-prefix must be non-empty".to_owned());
    }
    if !is_bool(is_main) {
        return Err(format!("invalid value for --is-main: {is_main}"));
    }
    if !is_bool(is_user_branch) {
        return Err(format!(
            "invalid value for --is-user-branch: {is_user_branch}"
        ));
    }
    if mode == "implement" && branch_info_supplied.is_some() {
        return Err("--branch-info-supplied not allowed for mode=implement".to_owned());
    }
    let branch_info = branch_info_supplied
        .filter(|value| !value.is_empty())
        .unwrap_or("false");
    if !is_bool(branch_info) {
        return Err(format!(
            "invalid value for --branch-info-supplied: {branch_info}"
        ));
    }
    if (mode == "design" && branch_info == "true") || is_user_branch == "true" {
        return Ok(GateDecision {
            entry_gate: "continue",
            skip_branch_check: "true",
        });
    }
    Ok(GateDecision {
        entry_gate: "strict",
        skip_branch_check: "false",
    })
}

fn is_bool(value: &str) -> bool {
    value == "true" || value == "false"
}

/// Parse a positive decimal issue number, rejecting every other spelling.
#[must_use]
pub fn normal_issue(value: &str) -> Option<u64> {
    crate::positive_integer(value)
}

/// Lifecycle prefixes that mark an issue as already owned by a larch run.
///
/// The set is the busy tracking states and the reserved debate states from
/// `config.TRACKING_BUSY_STATES` and `config.DEBATE_TITLE_STATES`, plus the two
/// legacy tokens that predate both tables. Extend it whenever either table
/// gains a state.
pub const MANAGED_PREFIXES: [&str; 8] = [
    "[DESIGNING] ",
    IMPLEMENTING_PREFIX,
    DONE_PREFIX,
    "[STALLED] ",
    "[DEBATING] ",
    "[DEBATED] ",
    "[IN PROGRESS] ",
    "[PLANNED] ",
];

/// The prefix `/design` writes onto an issue it has finished planning.
pub const DESIGNED_PREFIX: &str = "[DESIGNED] ";

/// Return whether the title carries a lifecycle prefix that forbids a new run.
#[must_use]
pub fn has_managed_prefix(title: &str) -> bool {
    MANAGED_PREFIXES
        .iter()
        .any(|prefix| title.starts_with(prefix))
}

/// Return whether the title carries the `/design` completion prefix.
#[must_use]
pub fn has_designed_prefix(title: &str) -> bool {
    title.starts_with(DESIGNED_PREFIX)
}

/// Return whether the title opens with a bracketed report tag.
///
/// Mirrors the Python `^\[[^]]*\s+report\]` probe, case-insensitively.
#[must_use]
pub fn has_report_prefix(title: &str) -> bool {
    report_prefix_pattern().is_match(title)
}

fn report_prefix_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^\[[^]]*\s+(?i-u:report)\]").expect("report-prefix regex should compile")
    });
    &PATTERN
}

/// Collapse a value onto one line the way the admission emitter does.
///
/// Carriage returns and line feeds become spaces, runs of spaces collapse to
/// one, and the result is trimmed. Emitted values must never carry a newline.
#[must_use]
pub fn single_line(value: &str) -> String {
    let flattened: String = value
        .chars()
        .map(|character| match character {
            '\r' | '\n' => ' ',
            other => other,
        })
        .collect();
    let mut collapsed = String::with_capacity(flattened.len());
    let mut previous_space = false;
    for character in flattened.chars() {
        if character == ' ' {
            if !previous_space {
                collapsed.push(character);
            }
            previous_space = true;
        } else {
            collapsed.push(character);
            previous_space = false;
        }
    }
    collapsed.trim().to_owned()
}

/// Extract blocker issue numbers declared in one prose document.
///
/// Fenced code, inline code spans, HTML comments, and example lines are skipped,
/// and a keyword preceded by a negation inside the same clause does not count.
#[must_use]
pub fn parse_prose_blockers(text: &str) -> Vec<u64> {
    let mut refs: Vec<u64> = Vec::new();
    let mut in_fence = false;
    for raw_line in text.lines() {
        if fence_pattern().is_match(raw_line) {
            in_fence = !in_fence;
            continue;
        }
        if in_fence {
            continue;
        }
        let stripped = inline_code_pattern().replace_all(raw_line, "");
        let stripped = stripped.replace(['*', '_'], "");
        let line = markdown_prefix_pattern().replace(&stripped, "");
        let line = line.trim();
        if line.is_empty() || line.starts_with("<!--") || example_prefix_pattern().is_match(line) {
            continue;
        }
        for capture in keyword_pattern().captures_iter(line) {
            let (Some(whole), Some(digits)) = (capture.get(0), capture.get(1)) else {
                continue;
            };
            if has_scoped_negation(&line[..whole.start()]) {
                continue;
            }
            let Ok(number) = digits.as_str().parse::<u64>() else {
                continue;
            };
            if !refs.contains(&number) {
                refs.push(number);
            }
        }
    }
    refs.sort_unstable();
    refs
}

fn has_scoped_negation(prefix: &str) -> bool {
    let clause = negation_boundary_pattern()
        .split(prefix)
        .last()
        .unwrap_or(prefix);
    negation_pattern().is_match(clause)
}

fn keyword_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(
            r"(?i-u:Depends on|Blocked by|Blocked on|Requires|Needs)[ \t]+#([0-9]+)(?:[^0-9]|$)",
        )
        .expect("blocker keyword regex should compile")
    });
    &PATTERN
}

fn fence_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"^\s*(?:```|~~~)").expect("code-fence regex should compile"));
    &PATTERN
}

fn inline_code_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"`[^`\n]*`").expect("inline-code regex should compile"));
    &PATTERN
}

fn markdown_prefix_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?").expect("markdown-prefix regex should compile")
    });
    &PATTERN
}

fn example_prefix_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^(?i-u:example|examples|e\.g\.|eg\.|for example|sample)\b")
            .expect("example-prefix regex should compile")
    });
    &PATTERN
}

fn negation_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"\b(?i-u:does\s+not|do\s+not|did\s+not|not|no|never|without)\b")
            .expect("negation regex should compile")
    });
    &PATTERN
}

fn negation_boundary_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"[.;:!?]|\b(?i-u:and|but|however|then|yet)\b")
            .expect("negation-boundary regex should compile")
    });
    &PATTERN
}

#[cfg(test)]
mod tests {
    use super::{
        entry_gate, has_designed_prefix, has_managed_prefix, has_report_prefix, normal_issue,
        parse_prose_blockers, single_line,
    };

    #[test]
    fn a_user_branch_or_supplied_design_branch_info_relaxes_the_gate() {
        let strict = entry_gate("implement", "true", "false", "zhupanov", None)
            .expect("valid implement inputs");
        assert_eq!(strict.entry_gate, "strict");
        assert_eq!(strict.skip_branch_check, "false");

        let user_branch = entry_gate("implement", "false", "true", "zhupanov", None)
            .expect("valid implement inputs");
        assert_eq!(user_branch.entry_gate, "continue");
        assert_eq!(user_branch.skip_branch_check, "true");

        let design = entry_gate("design", "true", "false", "zhupanov", Some("true"))
            .expect("valid design inputs");
        assert_eq!(design.entry_gate, "continue");
    }

    #[test]
    fn every_invalid_input_carries_its_exact_gate_error() {
        assert_eq!(
            entry_gate("review", "true", "false", "u", None),
            Err("invalid mode: review".to_owned())
        );
        assert_eq!(
            entry_gate("design", "true", "false", "", None),
            Err("--user-prefix must be non-empty".to_owned())
        );
        assert_eq!(
            entry_gate("design", "yes", "false", "u", None),
            Err("invalid value for --is-main: yes".to_owned())
        );
        assert_eq!(
            entry_gate("design", "true", "yes", "u", None),
            Err("invalid value for --is-user-branch: yes".to_owned())
        );
        assert_eq!(
            entry_gate("implement", "true", "false", "u", Some("true")),
            Err("--branch-info-supplied not allowed for mode=implement".to_owned())
        );
        assert_eq!(
            entry_gate("design", "true", "false", "u", Some("maybe")),
            Err("invalid value for --branch-info-supplied: maybe".to_owned())
        );
    }

    #[test]
    fn an_empty_branch_info_value_falls_back_to_false() {
        let decision =
            entry_gate("design", "true", "false", "u", Some("")).expect("empty value defaults");

        assert_eq!(decision.entry_gate, "strict");
    }

    #[test]
    fn issue_numbers_accept_only_positive_decimals() {
        assert_eq!(normal_issue("8059"), Some(8059));
        assert_eq!(normal_issue("0"), None);
        assert_eq!(normal_issue(""), None);
        assert_eq!(normal_issue("-1"), None);
        assert_eq!(normal_issue("12a"), None);
        assert_eq!(normal_issue(" 12"), None);
    }

    #[test]
    fn lifecycle_prefixes_match_the_python_predicates() {
        assert!(has_managed_prefix("[IMPLEMENTING] Do the thing"));
        assert!(has_managed_prefix("[IN PROGRESS] Do the thing"));
        assert!(has_managed_prefix("[DEBATING] Do the thing"));
        assert!(has_managed_prefix("[DEBATED] Do the thing"));
        assert!(!has_managed_prefix("[IMPLEMENTING]No space"));
        assert!(has_designed_prefix("[DESIGNED] Do the thing"));
        assert!(!has_designed_prefix("Prefix [DESIGNED] elsewhere"));
        assert!(has_report_prefix("[BUG REPORT] something"));
        assert!(has_report_prefix("[weekly  report] something"));
        assert!(!has_report_prefix("[report] something"));
        assert!(!has_report_prefix("prefix [audit report] something"));
    }

    #[test]
    fn single_line_flattens_and_collapses_like_the_emitter() {
        assert_eq!(single_line("a\r\nb"), "a b");
        assert_eq!(single_line("  spaced    out  "), "spaced out");
        assert_eq!(single_line("\n\n"), "");
        assert_eq!(single_line("tab\tkept"), "tab\tkept");
    }

    #[test]
    fn prose_blockers_skip_fences_examples_and_negations() {
        let text = concat!(
            "- Blocked by #12\n",
            "```\n",
            "Depends on #99\n",
            "```\n",
            "Example: Depends on #98\n",
            "This does not depend on #97, and Requires #13\n",
            "<!-- Needs #96 -->\n",
            "`Requires #95`\n",
            "1. Depends on #12\n",
        );

        assert_eq!(parse_prose_blockers(text), vec![12, 13]);
    }

    #[test]
    fn a_negation_before_a_clause_boundary_does_not_suppress_the_keyword() {
        assert_eq!(parse_prose_blockers("not yet. Requires #7"), vec![7]);
        assert_eq!(parse_prose_blockers("never Requires #7"), Vec::<u64>::new());
        assert_eq!(parse_prose_blockers(""), Vec::<u64>::new());
    }
}
