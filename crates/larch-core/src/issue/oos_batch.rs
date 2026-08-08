//! The out-of-scope batch a run composes before it files anything.
//!
//! Two compositions live here, and both write text that leaves the machine.
//!
//! Manifest materialization turns an external implementer's
//! `oos_observations[]` into canonical `### OOS_<n>:` blocks. The observations
//! are vendor output, so every byte of them is untrusted: titles are flattened to
//! one line so a forged heading cannot open a second record, and every string
//! is redacted and PII-scrubbed before it reaches a public artifact. An
//! observation that names a security focus area is never materialized publicly;
//! it is routed to a private sidecar instead.
//!
//! The per-run cap bounds how many issues one run may file. Beyond the cap the
//! surplus records are rolled into one aggregate whose body preserves each
//! rolled-up record verbatim, indented so its own field lines can never re-open
//! as separate items.
//!
//! Ports the manifest and cap halves of Python `larch.issue.file_oos`.

use crate::issue::input::{ParsedItem, parse_issue_input};
use crate::issue::oos_record::{
    BlockBoundary, OosItemKind, is_canonical_heading, parse_oos_blocks,
};
use crate::redaction::redact;
use crate::text::{balanced_fence_line_indices, split_text_lines, trim_python_whitespace};
use regex::{NoExpand, Regex};
use std::sync::LazyLock;

/// Indent applied to a rolled-up body so its field lines stay payload.
const ROLLED_BODY_INDENT: &str = "    ";
/// Replacement published in place of a non-public URL.
const INTERNAL_URL: &str = "<INTERNAL-URL>";
/// Replacement published in place of an address or account identifier.
const REDACTED_PII: &str = "<REDACTED-PII>";

static INTERNAL_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
        r"(?i-u:https?)://(?:(?i-u:localhost)|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|",
        r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|",
        r"\[?(?:(?i-u:fc)[0-9a-fA-F]{2}:|(?i-u:fd)[0-9a-fA-F]{2}:|(?i-u:fe80):)|",
        r"[^\s\x1c-\x1f/]+\.(?i-u:internal|local|corp|lan|intranet|test|example|invalid))",
        r"[^\s\x1c-\x1f]*",
        r"|\b(?:(?i-u:localhost)|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|",
        r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|",
        r"[^\s\x1c-\x1f/]+\.(?i-u:internal|local|corp|lan|intranet))\b",
    ))
    .expect("internal url expression")
});
static EMAIL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}").expect("email expression")
});
static PHONE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-]?[0-9]{3}[ .-]?[0-9]{4}")
        .expect("phone expression")
});
static SSN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[0-9]{3}-[0-9]{2}-[0-9]{4}").expect("ssn expression"));
static ACCOUNT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\b(?i-u:account|user|customer|employee|tenant|org)[_-]?[A-Za-z0-9]{8,}\b")
        .expect("account expression")
});
static FOCUS_AREA_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
        r"(?m)^[ \t-]*(?:[-*][ \t]*)?(?:\*\*)?(?i-u:focus)[- \t]*(?i-u:area)(?:\*\*)?",
        r"[ \t]*[:=][ \t]*(?i-u:security)[-a-zA-Z0-9 _]*(?:[\s\x1c-\x1f]|$|\(|#|\.|,)",
    ))
    .expect("focus area expression")
});
static CONTROL_CHARACTER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[\x00-\x1f\x7f]").expect("control character expression"));
static WHITESPACE_RUN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[\s\x1c-\x1f]+").expect("whitespace run expression"));
static ROLLUP_CONTROL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]").expect("rollup control expression")
});
static ROLLUP_BREAK_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[\r\n\t]+").expect("rollup break expression"));
static ROLLUP_LEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ *_#`]+").expect("rollup leading expression"));
static ROLLUP_EMPHASIS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[*`]+").expect("rollup emphasis expression"));
static FILE_REF_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?(?::[0-9]+(?:-[0-9]+)?)?",
    )
    .expect("file reference expression")
});
static OOS_HEADING_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^### OOS_[0-9]+:").expect("oos heading prefix expression"));

/// Redact exactly as the Python `redact` helper the OOS path calls does.
///
/// The Python owner is line oriented and terminates a non-empty result with a
/// newline. Every consumer here splits or trims afterwards, but the rule is
/// reproduced so the two spellings cannot drift.
fn python_redact(text: &str) -> String {
    let mut scrubbed = redact(text).text().to_owned();
    if !scrubbed.is_empty() && !scrubbed.ends_with('\n') {
        scrubbed.push('\n');
    }
    scrubbed
}

/// Scrub secrets, non-public hosts, and personal data out of published prose.
///
/// The order is load bearing: secret redaction runs first so a credential
/// inside an internal URL is already gone before the URL itself collapses to a
/// placeholder.
#[must_use]
pub fn sanitize_public_text(text: &str) -> String {
    let redacted = python_redact(text);
    let without_urls = INTERNAL_URL_RE.replace_all(&redacted, NoExpand(INTERNAL_URL));
    let without_email = EMAIL_RE.replace_all(&without_urls, NoExpand(REDACTED_PII));
    let without_ssn = SSN_RE.replace_all(&without_email, NoExpand(REDACTED_PII));
    let without_phone = PHONE_RE.replace_all(&without_ssn, NoExpand(REDACTED_PII));
    ACCOUNT_RE
        .replace_all(&without_phone, NoExpand(REDACTED_PII))
        .into_owned()
}

/// Flatten untrusted text into one sanitized single-line title.
///
/// Control characters become spaces before whitespace collapses, so a title
/// carrying an embedded newline and a forged `### OOS_99:` heading survives as
/// inert prose on the record's own heading line rather than opening a record.
#[must_use]
pub fn normalize_title(text: &str) -> String {
    let sanitized = sanitize_public_text(text);
    let without_controls = CONTROL_CHARACTER_RE.replace_all(&sanitized, NoExpand(" "));
    WHITESPACE_RUN_RE
        .replace_all(&without_controls, NoExpand(" "))
        .trim()
        .to_owned()
}

/// Render a sanitized description as one `- **Description**:` field.
///
/// Continuation lines are indented two columns so a multi-line description
/// stays inside its own field instead of reading as a new one.
#[must_use]
pub fn description_lines(description: &str) -> Vec<String> {
    let sanitized = sanitize_public_text(description);
    let mut lines = split_text_lines(&sanitized);
    if lines.is_empty() {
        lines.push("");
    }
    lines
        .into_iter()
        .enumerate()
        .map(|(index, line)| {
            if index == 0 {
                format!("- **Description**: {line}")
            } else {
                format!("  {line}")
            }
        })
        .collect()
}

/// Report whether one manifest observation must route to the private sidecar.
///
/// A declared focus area decides on its own. Otherwise the description is read
/// for the same dedicated field line, with Markdown emphasis stripped first so
/// `- **focus-area**: security` and `- focus-area: security` route alike.
#[must_use]
pub fn observation_is_security(description: &str, focus_area: &str) -> bool {
    if !focus_area.is_empty()
        && FOCUS_AREA_LINE_RE.is_match(&format!("- **focus-area**: {focus_area}\n"))
    {
        return true;
    }
    FOCUS_AREA_LINE_RE.is_match(&description.replace(['`', '*'], ""))
}

/// One manifest observation, already sanitized into publishable fields.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ManifestObservation {
    /// The one-line title, never empty by the time it is rendered.
    pub title: String,
    /// The raw description text, sanitized when it is rendered.
    pub description: String,
    /// Which phase surfaced the observation.
    pub phase: String,
    /// The declared focus area, or empty when none was declared.
    pub focus_area: String,
}

impl ManifestObservation {
    /// Render this observation as one public `### OOS_<seq>:` block.
    #[must_use]
    pub fn render_public_block(&self, seq: u64) -> String {
        let mut lines = vec![format!("### OOS_{seq}: {}", self.title)];
        lines.extend(description_lines(&self.description));
        lines.push("- **Reviewer**: External implementer".to_owned());
        lines.push("- **Vote tally**: N/A — auto-filed per policy".to_owned());
        lines.push(format!("- **Phase**: {}", self.phase));
        if !self.focus_area.is_empty() {
            lines.push(format!("- **focus-area**: {}", self.focus_area));
        }
        lines.join("\n")
    }

    /// Render this observation as one private security-sidecar entry.
    ///
    /// `separated` inserts a leading blank line, which the caller sets when the
    /// sidecar already carries an entry.
    #[must_use]
    pub fn render_security_entry(&self, separated: bool) -> String {
        let mut lines: Vec<String> = Vec::new();
        if separated {
            lines.push(String::new());
        }
        lines.push(format!("### Security OOS: {}", self.title));
        lines.extend(description_lines(&self.description));
        lines.push(format!("- **Phase**: {}", self.phase));
        if !self.focus_area.is_empty() {
            lines.push(format!("- **focus-area**: {}", self.focus_area));
        }
        lines.push(
            "- **Disposition**: security-routed; not materialized for public OOS filing".to_owned(),
        );
        lines.join("\n") + "\n"
    }

    /// The heading one sidecar entry claims, used to keep reruns idempotent.
    #[must_use]
    pub fn security_heading(&self) -> String {
        format!("### Security OOS: {}", self.title)
    }
}

/// Return the lowercased normalized titles of every OOS record in `text`.
#[must_use]
pub fn existing_oos_titles(text: &str) -> Vec<String> {
    parse_oos_blocks(text, BlockBoundary::OosHeading)
        .into_iter()
        .filter(|block| block.kind == OosItemKind::Oos)
        .map(|block| normalize_title(&block.title).to_lowercase())
        .collect()
}

/// Return the next free `OOS_<n>` ordinal for `text`, or one when it has none.
#[must_use]
pub fn next_oos_number(text: &str) -> u64 {
    parse_oos_blocks(text, BlockBoundary::OosHeading)
        .iter()
        .filter(|block| block.kind == OosItemKind::Oos)
        .filter_map(|block| block.item_id.strip_prefix("OOS_"))
        .filter_map(|digits| digits.parse::<u64>().ok())
        .max()
        .unwrap_or(0)
        .saturating_add(1)
}

/// Why one batch could not be capped.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum IssueCapError {
    /// The file parsed as items but carries no canonical OOS heading.
    NotOosShaped,
    /// The item count and the raw heading count disagree.
    HeadingCountMismatch {
        /// How many items the batch parser produced.
        items: usize,
        /// How many unfenced canonical OOS headings the file carries.
        headings: usize,
    },
}

impl IssueCapError {
    /// Render the exact diagnostic the caller reports.
    #[must_use]
    pub fn message(&self) -> String {
        match *self {
            Self::NotOosShaped => "input is not OOS-shaped (no '### OOS_<N>:' headings)".to_owned(),
            Self::HeadingCountMismatch { items, headings } => {
                format!("ITEMS_TOTAL ({items}) != raw '### OOS_<N>:' heading count ({headings})")
            }
        }
    }
}

/// Check that a cap input parses as the OOS batch it claims to be.
///
/// The two counts must agree: a file whose parser sees fewer items than it has
/// headings is silently losing records, and capping it would file a batch that
/// does not match what a reviewer wrote.
///
/// # Errors
///
/// Returns [`IssueCapError`] when the file is not OOS shaped or the two counts
/// disagree.
pub fn validate_issue_cap_input(text: &str) -> Result<Vec<ParsedItem>, IssueCapError> {
    if trim_python_whitespace(text).is_empty() {
        return Ok(Vec::new());
    }
    let items = parse_issue_input(text).items;
    let lines = split_text_lines(text);
    let fenced = balanced_fence_line_indices(&lines);
    let headings = lines
        .iter()
        .enumerate()
        .filter(|(index, line)| {
            !fenced.contains(index) && is_canonical_heading(line, Some(OosItemKind::Oos))
        })
        .count();
    if !items.is_empty() && headings == 0 {
        return Err(IssueCapError::NotOosShaped);
    }
    if headings != 0 && items.len() != headings {
        return Err(IssueCapError::HeadingCountMismatch {
            items: items.len(),
            headings,
        });
    }
    Ok(items)
}

/// Collapse untrusted rollup prose to one inert single-line summary.
fn normalize_rollup_text(text: &str) -> String {
    let without_controls = ROLLUP_CONTROL_RE.replace_all(text, NoExpand(""));
    let single_line = ROLLUP_BREAK_RE.replace_all(&without_controls, NoExpand(" "));
    let without_leading = ROLLUP_LEADING_RE.replace(&single_line, NoExpand(""));
    let without_emphasis = ROLLUP_EMPHASIS_RE.replace_all(&without_leading, NoExpand(""));
    WHITESPACE_RUN_RE
        .replace_all(&without_emphasis, NoExpand(" "))
        .trim()
        .to_owned()
}

/// Return the distinct file references a rolled-up body names, in order.
fn file_refs_from_body(body: &str) -> String {
    let mut seen: Vec<String> = Vec::new();
    for found in FILE_REF_RE.find_iter(body) {
        let candidate = found
            .as_str()
            .trim_matches(|character| matches!(character, '*' | '_' | '#' | '`' | ' '))
            .to_owned();
        if !candidate.is_empty() && !seen.contains(&candidate) {
            seen.push(candidate);
        }
    }
    seen.join(" ")
}

/// Indent one rolled-up body so none of its lines re-opens as a new field.
fn indent_rolled_body(body: &str) -> String {
    split_text_lines(body)
        .into_iter()
        .map(|line| {
            if trim_python_whitespace(line).is_empty() {
                String::new()
            } else {
                format!("{ROLLED_BODY_INDENT}{line}")
            }
        })
        .collect::<Vec<String>>()
        .join("\n")
}

/// One record the cap kept or rolled up: its title and its exact source bytes.
#[derive(Clone, Debug, Eq, PartialEq)]
struct CapRecord {
    title: String,
    body: String,
}

/// Render the one aggregate block that carries every capped-out record.
fn aggregate_block(seq: usize, items: &[CapRecord], cap: usize) -> String {
    let surplus = items.len();
    let mut lines = vec![
        format!("### OOS_{seq}: Aggregated rollup of {surplus} capped OOS items"),
        format!(
            "- **Description**: Cap {cap} (OOS_ISSUES_PER_RUN_CAP) exceeded; the following {surplus} items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:"
        ),
    ];
    for item in items {
        let title = {
            let normalized = normalize_rollup_text(&item.title);
            if normalized.is_empty() {
                "(no title)".to_owned()
            } else {
                normalized
            }
        };
        let refs = file_refs_from_body(&item.body);
        let suffix = if refs.is_empty() {
            String::new()
        } else {
            format!(" [Files: {refs}]")
        };
        lines.push(format!("  - **{title}**:{suffix}"));
        let body = item.body.trim_end();
        if trim_python_whitespace(body).is_empty() {
            lines.push(format!("{ROLLED_BODY_INDENT}(body unavailable)"));
        } else {
            lines.push(indent_rolled_body(body));
        }
    }
    lines.push("- **Reviewer**: Combined: capped per-run rollup".to_owned());
    lines.push(format!(
        "- **Vote tally**: N/A — capped rollup of {surplus} entries"
    ));
    lines.push("- **Phase**: implement".to_owned());
    lines.push(String::new());
    lines.join("\n")
}

/// Renumber every canonical OOS heading from one, leaving all other bytes.
fn renumber_oos_headings(text: &str) -> String {
    let mut index = 0_u64;
    let rendered = split_text_lines(text)
        .into_iter()
        .map(|line| {
            if is_canonical_heading(line, Some(OosItemKind::Oos)) {
                index = index.saturating_add(1);
                let replacement = format!("### OOS_{index}:");
                OOS_HEADING_PREFIX_RE
                    .replacen(line, 1, NoExpand(&replacement))
                    .into_owned()
            } else {
                line.to_owned()
            }
        })
        .collect::<Vec<String>>()
        .join("\n");
    if text.ends_with('\n') {
        rendered + "\n"
    } else {
        rendered
    }
}

/// Apply the per-run issue cap to one batch.
///
/// Returns `None` when the batch already fits, so the caller can copy the
/// input through unchanged rather than re-rendering bytes it did not need to
/// touch. Otherwise the first `cap - 1` records survive verbatim and every
/// remaining record is folded into one aggregate.
///
/// # Errors
///
/// Returns [`IssueCapError`] when the input does not validate as an OOS batch.
pub fn apply_issue_cap(text: &str, cap: usize) -> Result<Option<String>, IssueCapError> {
    let parsed = validate_issue_cap_input(text)?;
    let raw: Vec<CapRecord> = parse_oos_blocks(text, BlockBoundary::ItemHeading)
        .into_iter()
        .filter(|block| block.kind == OosItemKind::Oos)
        .map(|block| CapRecord {
            title: block.title,
            body: block.block.trim_end().to_owned(),
        })
        .collect();
    if raw.is_empty() || raw.len() <= cap {
        return Ok(None);
    }
    let keep_count = cap.saturating_sub(1);
    let rolled: Vec<CapRecord> = raw[keep_count..]
        .iter()
        .enumerate()
        .map(|(offset, record)| CapRecord {
            title: parsed
                .get(keep_count + offset)
                .map_or_else(|| record.title.clone(), |item| item.title.clone()),
            body: record.body.clone(),
        })
        .collect();
    let mut blocks: Vec<String> = raw[..keep_count]
        .iter()
        .map(|record| record.body.clone())
        .collect();
    blocks.push(aggregate_block(blocks.len() + 1, &rolled, cap));
    let joined = blocks.join("\n\n").trim_end().to_owned() + "\n";
    Ok(Some(renumber_oos_headings(&joined)))
}

#[cfg(test)]
mod tests {
    use super::{
        IssueCapError, ManifestObservation, apply_issue_cap, description_lines,
        existing_oos_titles, next_oos_number, normalize_title, observation_is_security,
        sanitize_public_text, validate_issue_cap_input,
    };

    fn observation(title: &str, description: &str) -> ManifestObservation {
        ManifestObservation {
            title: title.to_owned(),
            description: description.to_owned(),
            phase: "implement".to_owned(),
            focus_area: String::new(),
        }
    }

    #[test]
    fn personal_data_and_internal_hosts_never_reach_public_text() {
        let sanitized = sanitize_public_text(concat!(
            "mail admin@example.com call 415-555-1212 ssn 123-45-6789 ",
            "tenant_ABCDEF123456 http://service.internal/path http://10.1.2.3/p http://fe80::1/p\n",
        ));
        for leaked in [
            "admin@example.com",
            "415-555-1212",
            "123-45-6789",
            "tenant_ABCDEF123456",
            "service.internal",
            "10.1.2.3",
            "fe80::1",
        ] {
            assert!(!sanitized.contains(leaked), "{leaked} in {sanitized}");
        }
        assert!(sanitized.contains("<INTERNAL-URL>"));
        assert!(sanitized.contains("<REDACTED-PII>"));
        assert_eq!(sanitize_public_text(""), "");
    }

    #[test]
    fn a_forged_heading_inside_a_title_cannot_open_a_record() {
        assert_eq!(
            normalize_title("Injected\n### OOS_99: forged"),
            "Injected ### OOS_99: forged"
        );
        assert_eq!(normalize_title("  spaced\tout  "), "spaced out");
        assert_eq!(normalize_title(""), "");
    }

    #[test]
    fn a_description_stays_inside_its_own_field() {
        assert_eq!(
            description_lines("first\nsecond"),
            ["- **Description**: first", "  second"]
        );
        assert_eq!(description_lines(""), ["- **Description**: "]);
    }

    #[test]
    fn only_a_dedicated_focus_area_field_routes_an_observation_privately() {
        assert!(observation_is_security("", "security-hardening"));
        assert!(observation_is_security("- **focus-area**: security\n", ""));
        assert!(observation_is_security("- focus-area: security\n", ""));
        assert!(!observation_is_security("this is a security problem", ""));
        assert!(!observation_is_security("", "correctness"));
    }

    #[test]
    fn a_public_block_carries_every_field_the_pipeline_reads() {
        let mut item = observation("Widen retries", "The backoff is tight.");
        assert_eq!(
            item.render_public_block(3),
            concat!(
                "### OOS_3: Widen retries\n",
                "- **Description**: The backoff is tight.\n",
                "- **Reviewer**: External implementer\n",
                "- **Vote tally**: N/A — auto-filed per policy\n",
                "- **Phase**: implement",
            )
        );
        item.focus_area = "correctness".to_owned();
        assert!(
            item.render_public_block(1)
                .ends_with("- **focus-area**: correctness")
        );
    }

    #[test]
    fn a_security_entry_records_its_disposition_and_separates_from_the_last() {
        let item = ManifestObservation {
            focus_area: "security".to_owned(),
            ..observation("Leaky token", "It leaks.")
        };
        let entry = item.render_security_entry(true);
        assert!(entry.starts_with("\n### Security OOS: Leaky token\n"));
        assert!(entry.ends_with("not materialized for public OOS filing\n"));
        assert!(
            item.render_security_entry(false)
                .starts_with("### Security OOS:")
        );
        assert_eq!(item.security_heading(), "### Security OOS: Leaky token");
    }

    #[test]
    fn existing_records_seed_the_title_set_and_the_next_ordinal() {
        let text = "### OOS_2: Alpha\n### OOS_7: Beta\n";
        assert_eq!(existing_oos_titles(text), ["alpha", "beta"]);
        assert_eq!(next_oos_number(text), 8);
        assert_eq!(next_oos_number(""), 1);
        assert!(existing_oos_titles("").is_empty());
    }

    #[test]
    fn a_batch_whose_counts_disagree_is_refused() {
        assert!(validate_issue_cap_input("").expect("empty").is_empty());
        assert_eq!(
            validate_issue_cap_input("### Item\n- **Description**: d\n"),
            Err(IssueCapError::NotOosShaped)
        );
        assert_eq!(
            IssueCapError::NotOosShaped.message(),
            "input is not OOS-shaped (no '### OOS_<N>:' headings)"
        );
        assert_eq!(
            IssueCapError::HeadingCountMismatch {
                items: 1,
                headings: 2
            }
            .message(),
            "ITEMS_TOTAL (1) != raw '### OOS_<N>:' heading count (2)"
        );
    }

    #[test]
    fn a_fitting_batch_is_left_alone() {
        let text = "### OOS_1: a\n- **Description**: d\n";
        assert_eq!(apply_issue_cap(text, 1), Ok(None));
        assert_eq!(apply_issue_cap("", 1), Ok(None));
    }

    #[test]
    fn surplus_records_roll_into_one_renumbered_aggregate() {
        let text = concat!(
            "### OOS_1: keep me\n- **Description**: first\n\n",
            "### OOS_2: roll me\n- **Description**: see a/b.py:10-20\n\n",
            "### OOS_3: roll me too\n- **Description**: second\n",
        );
        let capped = apply_issue_cap(text, 2).expect("cap").expect("rendered");
        assert!(capped.starts_with("### OOS_1: keep me\n"));
        assert!(capped.contains("### OOS_2: Aggregated rollup of 2 capped OOS items"));
        assert!(capped.contains("  - **roll me**: [Files: a/b.py:10-20]"));
        assert!(capped.contains("    ### OOS_2: roll me"));
        assert!(capped.contains("- **Vote tally**: N/A — capped rollup of 2 entries"));
        assert!(capped.ends_with("- **Phase**: implement\n"));
    }

    #[test]
    fn a_cap_of_one_rolls_every_record_and_names_an_empty_title() {
        let text = "### OOS_1: ``\n### OOS_2: b\n";
        let capped = apply_issue_cap(text, 1).expect("cap").expect("rendered");
        assert!(capped.starts_with("### OOS_1: Aggregated rollup of 2 capped OOS items\n"));
        assert!(capped.contains("  - **(no title)**:"));
    }
}
