//! Which deferred observations are high risk, and how they are marked.
//!
//! Ports Python `larch.issue.oos_priority`. Most out-of-scope items are
//! ordinary backlog. A few defer a correctness or regression risk, and those
//! must stay findable after the run that deferred them ends, so the filer puts
//! a dedicated label on them. The signal is the item's own `focus-area` field:
//! it is reviewer prose, so the reader accepts the spellings reviewers
//! actually write — bulleted, bolded, `:` or `=` — and nothing else.

use crate::text::{split_text_lines, trim_python_whitespace};
use regex::Regex;
use std::sync::LazyLock;

/// The label a high-risk public OOS issue carries.
pub const OOS_CORRECTNESS_LABEL: &str = "oos-correctness";
/// The label's hex color, without a leading `#`.
pub const OOS_CORRECTNESS_LABEL_COLOR: &str = "d73a4a";
/// The label's description.
pub const OOS_CORRECTNESS_LABEL_DESCRIPTION: &str =
    "High-risk correctness or regression OOS deferral";
/// The focus areas that make a deferral high risk.
pub const HIGH_RISK_FOCUS_VALUES: [&str; 2] = ["correctness", "regression"];

/// Characters Python strips from both ends of a parsed focus-area value.
const FOCUS_AREA_TRIM: [char; 13] = [
    '`', '*', '_', '[', ']', '(', ')', '{', '}', '.', ',', ';', ':',
];

static FOCUS_AREA_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^[\s\x1c-\x1f]*(?:[-*+][\s\x1c-\x1f]*)?(?:\*\*)?(?i-u:focus)[ -](?i-u:area)(?:\*\*)?[\s\x1c-\x1f]*[:=][\s\x1c-\x1f]*([^\s\x1c-\x1f,;.)]+)",
    )
    .expect("focus-area expression")
});
static ISSUE_NUMBER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"/issues/(\d+)\D*$").expect("issue number expression"));

/// Return the high-risk verdict for one focus-area line, if it is one.
fn line_is_high_risk(line: &str) -> bool {
    let Some(captures) = FOCUS_AREA_LINE_RE.captures(line) else {
        return false;
    };
    let value = trim_python_whitespace(&captures[1])
        .trim_matches(FOCUS_AREA_TRIM)
        .to_lowercase();
    HIGH_RISK_FOCUS_VALUES.contains(&value.as_str())
}

/// Report whether an OOS block carries a high-risk focus area.
#[must_use]
pub fn is_high_risk_oos_block(text: &str) -> bool {
    split_text_lines(text).into_iter().any(line_is_high_risk)
}

/// Extract the issue number from a GitHub issue URL, or `""`.
#[must_use]
pub fn issue_number_from_url(url: &str) -> String {
    ISSUE_NUMBER_RE
        .captures(trim_python_whitespace(url))
        .map_or_else(String::new, |captures| captures[1].to_owned())
}

/// Return the arguments that idempotently provision the high-risk OOS label.
///
/// `--force` makes the call safe to repeat, which is what lets every filing
/// run provision the label without first querying for it.
#[must_use]
pub fn label_create_argv(repo: &str) -> Vec<String> {
    let mut argv = vec![
        "label".to_owned(),
        "create".to_owned(),
        OOS_CORRECTNESS_LABEL.to_owned(),
        "--force".to_owned(),
        "--color".to_owned(),
        OOS_CORRECTNESS_LABEL_COLOR.to_owned(),
        "--description".to_owned(),
        OOS_CORRECTNESS_LABEL_DESCRIPTION.to_owned(),
    ];
    if !repo.is_empty() {
        argv.push("--repo".to_owned());
        argv.push(repo.to_owned());
    }
    argv
}

#[cfg(test)]
mod tests {
    use super::{is_high_risk_oos_block, issue_number_from_url, label_create_argv};

    #[test]
    fn reviewer_spellings_of_the_focus_area_all_read_as_high_risk() {
        for line in [
            "- **Focus area**: correctness",
            "* focus-area = regression",
            "focus area:`correctness`.",
            "\x1f+ FOCUS-AREA:  [Regression]",
        ] {
            assert!(
                is_high_risk_oos_block(&format!("### OOS_1: t\n{line}\nmore\n")),
                "{line}"
            );
        }
    }

    #[test]
    fn ordinary_focus_areas_and_near_misses_stay_low_risk() {
        for line in [
            "- **Focus area**: security",
            "- **Focus area**: correctness-adjacent",
            "prefixed focus-area: correctness",
            "- **Focus**: correctness",
            "- **Focus area**:",
        ] {
            assert!(
                !is_high_risk_oos_block(&format!("### OOS_1: t\n{line}\n")),
                "{line}"
            );
        }
    }

    #[test]
    fn issue_numbers_survive_trailing_prose_and_whitespace() {
        assert_eq!(
            issue_number_from_url("  https://github.com/o/r/issues/42  "),
            "42"
        );
        assert_eq!(
            issue_number_from_url("https://github.com/o/r/issues/42#c"),
            "42"
        );
        assert_eq!(issue_number_from_url("https://github.com/o/r/pull/42"), "");
        assert_eq!(issue_number_from_url(""), "");
    }

    #[test]
    fn label_provisioning_appends_the_repository_only_when_named() {
        let plain = label_create_argv("");
        assert_eq!(plain.len(), 8);
        assert_eq!(plain[2], super::OOS_CORRECTNESS_LABEL);
        assert_eq!(plain[3], "--force");
        let scoped = label_create_argv("owner/repo");
        assert_eq!(&scoped[8..], ["--repo".to_owned(), "owner/repo".to_owned()]);
    }
}
