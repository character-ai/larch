//! Execution-issue ledger record composition for the `execution-issues` verbs.
//!
//! `/implement` accumulates its problems as Markdown in one mutable
//! `execution-issues.md`. Publishing them means turning that prose into the
//! append-only `execution-issues` NDJSON batch, once per distinct problem, no
//! matter how many times a flush runs.
//!
//! Three readers do that work. [`execution_issue_sections`] buckets the file's
//! lines under the category headings the ledger recognizes, treating every
//! unrecognized heading as a warning rather than dropping it.
//! [`execution_issue_chunks`] splits one section into the individual entries a
//! record is composed from, keeping a fenced code block whole even when its
//! lines are bulleted. [`execution_issue_records`] then redacts each entry,
//! skips the ones the batch already carries, and renders the rest.
//!
//! Identity is not this module's to define. Dedupe keys come from
//! [`structured_body_dedupe_keys`] and the hash grammar from
//! [`normalize_body_for_hash`], so a record composed here and a resolution
//! event recorded elsewhere name the same issue.
//!
//! Ported from `larch.issue.execution_issues`.

use std::{collections::BTreeSet, fmt::Write as _};

use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};

use crate::{
    ensure_ascii_json,
    redaction::redact,
    report::{normalize_body_for_hash, structured_body_dedupe_keys},
    run_log::execution_issue_append::EXECUTION_ISSUE_CATEGORIES,
    split_text_lines,
};

/// Category an unrecognized heading collapses into.
const WARNINGS_CATEGORY: &str = "Warnings";
/// Title line the ledger writes above its sections.
const LEDGER_TITLE: &str = "Execution Issues";
/// Marker the shared redactor leaves when it had to drop a payload tail.
const TRUNCATION_MARKER: &str = "[content truncated";

/// One payload the shared redactor could not scrub without dropping content.
///
/// The ledger fails closed rather than persisting a partially redacted body.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RedactionRefusal;

/// Redact one entry body, refusing a payload the redactor had to truncate.
///
/// # Errors
///
/// Returns [`RedactionRefusal`] when the redactor dropped a payload tail.
pub fn redact_batch_payload(text: &str) -> Result<String, RedactionRefusal> {
    let redacted = redact(text).text().to_owned();
    if redacted.contains(TRUNCATION_MARKER) {
        return Err(RedactionRefusal);
    }
    Ok(redacted)
}

/// Return the SHA-256 of one entry body under the ledger's hash grammar.
#[must_use]
pub fn normalized_body_sha256(body: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(normalize_body_for_hash(body).as_bytes());
    hex_lower(&hasher.finalize())
}

/// Render bytes as lowercase hexadecimal.
fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _written = write!(&mut out, "{byte:02x}");
    }
    out
}

/// Whether one line opens or closes a fenced block, bulleted or not.
fn is_fence(line: &str) -> bool {
    let mut candidate = line.trim_start();
    if let Some(rest) = candidate.strip_prefix("- ") {
        candidate = rest.trim_start();
    }
    candidate.starts_with("```")
}

/// Split one ledger file into `(category, section body)` pairs.
///
/// A `### ` or `## ` heading that names a known category opens that category.
/// Any other heading opens `Warnings`, so a hand-written section is published
/// rather than silently dropped. Content that precedes every heading also
/// lands in `Warnings`. A section whose lines are all blank is not emitted.
#[must_use]
pub fn execution_issue_sections(text: &str) -> Vec<(String, String)> {
    let mut sections: Vec<(String, String)> = Vec::new();
    let mut current: Option<String> = None;
    let mut body: Vec<&str> = Vec::new();
    let mut in_fence = false;

    for line in split_text_lines(text) {
        if !in_fence && line.trim() == "---" {
            continue;
        }
        if !in_fence && (line.starts_with("### ") || line.starts_with("## ")) {
            let heading = line
                .split_once(' ')
                .map_or("", |(_marker, rest)| rest)
                .trim()
                .to_owned();
            close_section(&mut sections, current.as_deref(), &mut body);
            current = Some(if EXECUTION_ISSUE_CATEGORIES.contains(&heading.as_str()) {
                heading
            } else {
                WARNINGS_CATEGORY.to_owned()
            });
            continue;
        }
        if !in_fence
            && let Some(rest) = line.strip_prefix("# ")
            && rest.trim() == LEDGER_TITLE
        {
            continue;
        }
        if current.is_none() && !line.trim().is_empty() {
            current = Some(WARNINGS_CATEGORY.to_owned());
        }
        body.push(line);
        if is_fence(line) {
            in_fence = !in_fence;
        }
    }
    close_section(&mut sections, current.as_deref(), &mut body);
    sections
}

/// Emit the buffered section when it carries any non-blank line.
fn close_section(
    sections: &mut Vec<(String, String)>,
    current: Option<&str>,
    body: &mut Vec<&str>,
) {
    if let Some(category) = current
        && body.iter().any(|line| !line.trim().is_empty())
    {
        sections.push((category.to_owned(), format!("{}\n", body.join("\n"))));
    }
    body.clear();
}

/// Split one section body into the individual entries it publishes.
///
/// A new `- ` bullet starts an entry, and so does a blank line. Neither rule
/// applies inside a fenced block, so a multi-line code sample stays with the
/// bullet that introduced it instead of fragmenting into one record per line.
#[must_use]
pub fn execution_issue_chunks(body: &str) -> Vec<String> {
    let mut chunks: Vec<String> = Vec::new();
    let mut current: Vec<&str> = Vec::new();
    let mut in_fence = false;
    let mut pending_break = false;
    for line in split_text_lines(body) {
        if !in_fence && line.trim().is_empty() {
            pending_break = !current.is_empty();
            continue;
        }
        let fence = is_fence(line);
        if !in_fence && line.starts_with("- ") && !current.is_empty() && !fence {
            chunks.push(flush_chunk(&mut current));
            pending_break = false;
        }
        if pending_break && !current.is_empty() {
            chunks.push(flush_chunk(&mut current));
        }
        pending_break = false;
        current.push(line);
        if fence {
            in_fence = !in_fence;
        }
    }
    if !current.is_empty() {
        chunks.push(flush_chunk(&mut current));
    }
    chunks
}

/// Render and clear the buffered entry lines.
fn flush_chunk(current: &mut Vec<&str>) -> String {
    let rendered = format!("{}\n", trim_python_whitespace(&current.join("\n")));
    current.clear();
    rendered
}

/// Trim the whitespace set Python's `str.strip()` removes.
fn trim_python_whitespace(text: &str) -> &str {
    text.trim_matches(|character: char| character.is_whitespace())
}

/// Return the dedupe keys one entry body contributes, scoped by category.
#[must_use]
pub fn execution_issue_body_keys(category: &str, body: &str) -> BTreeSet<String> {
    structured_body_dedupe_keys(body, category)
        .into_iter()
        .map(|key| format!("{category}\u{0}{key}"))
        .collect()
}

/// Return every dedupe key the staged batch text already carries.
///
/// Rows that are not JSON objects, and objects without both a string
/// `category` and a string `body`, are skipped: a batch is append-only and may
/// carry resolution events and rows written by an older grammar.
#[must_use]
pub fn existing_execution_issue_keys(batch_text: &str) -> BTreeSet<String> {
    let mut keys = BTreeSet::new();
    for raw in split_text_lines(batch_text) {
        let Ok(Value::Object(row)) = serde_json::from_str::<Value>(raw) else {
            continue;
        };
        if let (Some(Value::String(category)), Some(Value::String(body))) =
            (row.get("category"), row.get("body"))
        {
            keys.extend(execution_issue_body_keys(category, body));
        }
    }
    keys
}

/// The labels one flush stamps on every record it composes.
#[derive(Clone, Copy, Debug)]
pub struct RecordLabels<'a> {
    /// `/implement` step the flush ran from.
    pub step: &'a str,
    /// Human-readable provenance for the records.
    pub source: &'a str,
}

/// Compose the batch records one ledger file still owes the staged batch.
///
/// An entry whose dedupe keys the batch already carries is skipped, and each
/// composed record's keys join that set, so one flush cannot publish the same
/// problem twice under two spellings.
///
/// # Errors
///
/// Returns [`RedactionRefusal`] when any entry body fails redaction closed.
pub fn execution_issue_records(
    text: &str,
    existing_batch: &str,
    labels: RecordLabels<'_>,
) -> Result<Vec<String>, RedactionRefusal> {
    let mut records: Vec<String> = Vec::new();
    let mut seen = existing_execution_issue_keys(existing_batch);
    for (category, section) in execution_issue_sections(text) {
        for chunk in execution_issue_chunks(&section) {
            let body = redact_batch_payload(&chunk)?;
            let body_keys = execution_issue_body_keys(&category, &body);
            if body_keys.is_subset(&seen) {
                continue;
            }
            records.push(render_record(&category, &body, labels));
            seen.extend(body_keys);
        }
    }
    Ok(records)
}

/// Render one NDJSON record the way Python's `json.dumps` spelled it.
fn render_record(category: &str, body: &str, labels: RecordLabels<'_>) -> String {
    let mut row = Map::new();
    let _previous = row.insert("body".to_owned(), Value::String(body.to_owned()));
    let _previous = row.insert("category".to_owned(), Value::String(category.to_owned()));
    let _previous = row.insert("phase".to_owned(), Value::String("implement".to_owned()));
    let _previous = row.insert("source".to_owned(), Value::String(labels.source.to_owned()));
    let _previous = row.insert(
        "source_sha256".to_owned(),
        Value::String(normalized_body_sha256(body)),
    );
    let _previous = row.insert("step".to_owned(), Value::String(labels.step.to_owned()));
    ensure_ascii_json(&Value::Object(row).to_string())
}

/// Whether the staged batch already carries every entry the ledger holds.
///
/// An empty ledger answers `false`: there is nothing to call already flushed.
///
/// # Errors
///
/// Returns [`RedactionRefusal`] when any entry body fails redaction closed.
pub fn batch_contains_all_sections(text: &str, batch_text: &str) -> Result<bool, RedactionRefusal> {
    let existing = existing_execution_issue_keys(batch_text);
    let mut saw = false;
    for (category, section) in execution_issue_sections(text) {
        for chunk in execution_issue_chunks(&section) {
            let body = redact_batch_payload(&chunk)?;
            let body_keys = execution_issue_body_keys(&category, &body);
            let digest = normalized_body_sha256(&body);
            if !body_keys.is_subset(&existing)
                && !batch_text.contains(&format!("\"source_sha256\":\"{digest}\""))
            {
                return Ok(false);
            }
            saw = true;
        }
    }
    Ok(saw)
}

#[cfg(test)]
mod tests {
    use super::{
        RecordLabels, batch_contains_all_sections, execution_issue_body_keys,
        execution_issue_chunks, execution_issue_records, execution_issue_sections,
        existing_execution_issue_keys, normalized_body_sha256, redact_batch_payload,
    };
    use serde_json::Value;

    /// A PEM opener the redactor must refuse, assembled at runtime so no secret
    /// scanner reads a contiguous key header out of this source file.
    fn unterminated_pem_body() -> String {
        format!("-----BEGIN {} KEY-----\nAAAA\n", "PRIVATE")
    }

    const LABELS: RecordLabels<'static> = RecordLabels {
        step: "7a",
        source: "execution-issues.md pre-bump",
    };

    fn parsed(records: &[String]) -> Vec<Value> {
        records
            .iter()
            .map(|record| serde_json::from_str(record).expect("record must be JSON"))
            .collect()
    }

    #[test]
    fn sections_bucket_known_headings_and_collapse_unknown_ones() {
        let sections =
            execution_issue_sections("### Tool Failures\n- one\n\n### Odd Heading\n- two\n");

        assert_eq!(
            sections,
            vec![
                ("Tool Failures".to_owned(), "- one\n\n".to_owned()),
                ("Warnings".to_owned(), "- two\n".to_owned()),
            ]
        );
    }

    #[test]
    fn sections_drop_the_ledger_title_rule_and_blank_bodies() {
        let sections = execution_issue_sections(
            "# Execution Issues\n\n## Warnings\n- self-review complete\n\n---\n### CI Issues\n\n",
        );

        assert_eq!(
            sections,
            vec![(
                "Warnings".to_owned(),
                "- self-review complete\n\n".to_owned()
            )]
        );
    }

    #[test]
    fn sections_treat_leading_content_as_a_warning() {
        let sections = execution_issue_sections("stray line\n");

        assert_eq!(
            sections,
            vec![("Warnings".to_owned(), "stray line\n".to_owned())]
        );
    }

    #[test]
    fn sections_keep_a_heading_inside_a_fence_with_its_entry() {
        let sections =
            execution_issue_sections("### Warnings\n- ```text\n### Tool Failures\n- ```\n");

        assert_eq!(sections.len(), 1);
        assert!(sections[0].1.contains("### Tool Failures"));
    }

    #[test]
    fn chunks_split_on_bullets_and_blank_lines_but_not_inside_fences() {
        let chunks = execution_issue_chunks(
            "- first\n- second\n\nloose\n- ```python\n- assert value\n- ```\n",
        );

        assert_eq!(
            chunks,
            vec![
                "- first\n".to_owned(),
                "- second\n".to_owned(),
                "loose\n- ```python\n- assert value\n- ```\n".to_owned(),
            ]
        );
    }

    #[test]
    fn body_keys_are_scoped_by_category() {
        let failures = execution_issue_body_keys("Tool Failures", "- boom\n");
        let warnings = execution_issue_body_keys("Warnings", "- boom\n");

        assert_eq!(failures.len(), 1);
        assert!(failures.is_disjoint(&warnings));
    }

    #[test]
    fn existing_keys_skip_rows_that_are_not_composed_records() {
        let keys = existing_execution_issue_keys(
            "not json\n[1,2]\n{\"event\":\"resolved\",\"issue_ids\":[\"x\"]}\n{\"category\":\"Warnings\",\"body\":\"- one\\n\"}\n",
        );

        assert_eq!(keys, execution_issue_body_keys("Warnings", "- one\n"));
    }

    #[test]
    fn records_carry_the_python_field_set_and_hash() {
        let records =
            execution_issue_records("### Tool Failures\n\n- tool failed once\n", "", LABELS)
                .expect("clean body must compose");

        let rows = parsed(&records);
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["phase"], "implement");
        assert_eq!(rows[0]["step"], "7a");
        assert_eq!(rows[0]["category"], "Tool Failures");
        assert_eq!(rows[0]["source"], "execution-issues.md pre-bump");
        assert_eq!(rows[0]["body"], "- tool failed once\n");
        assert_eq!(
            rows[0]["source_sha256"],
            normalized_body_sha256("- tool failed once\n")
        );
    }

    #[test]
    fn records_escape_non_ascii_the_way_python_did() {
        let records = execution_issue_records("### Warnings\n- caf\u{e9}\n", "", LABELS)
            .expect("clean body must compose");

        assert!(records[0].contains("caf\\u00e9"));
        assert!(records[0].is_ascii());
    }

    #[test]
    fn records_skip_entries_the_batch_already_carries() {
        let first = execution_issue_records("### Warnings\n- one\n- two\n", "", LABELS)
            .expect("clean body must compose");
        let batch = format!("{}\n", first.join("\n"));

        let second = execution_issue_records("### Warnings\n- one\n- two\n", &batch, LABELS)
            .expect("clean body must compose");

        assert_eq!(first.len(), 2);
        assert!(second.is_empty());
    }

    #[test]
    fn records_publish_one_row_per_section() {
        let records = execution_issue_records(
            "### Tool Failures\n\n- first failure\n\n### Warnings\n\n- warning entry\n",
            "",
            LABELS,
        )
        .expect("clean body must compose");

        let rows = parsed(&records);
        assert_eq!(
            rows.iter()
                .map(|row| row["category"].as_str().unwrap_or_default())
                .collect::<Vec<_>>(),
            vec!["Tool Failures", "Warnings"]
        );
    }

    #[test]
    fn redaction_refuses_a_payload_it_had_to_truncate() {
        let ledger = format!("### Warnings\n{}", unterminated_pem_body());

        assert!(redact_batch_payload(&unterminated_pem_body()).is_err());
        assert!(execution_issue_records(&ledger, "", LABELS).is_err());
        assert!(batch_contains_all_sections(&ledger, "").is_err());
    }

    #[test]
    fn batch_probe_matches_normalized_hashes_and_composed_rows() {
        let ledger = "### Warnings\n- one\n\n### Tool Failures\n- two\n";
        let digests: Vec<String> = ["- one\n", "- two\n"]
            .iter()
            .map(|body| format!("{{\"source_sha256\":\"{}\"}}", normalized_body_sha256(body)))
            .collect();

        assert!(
            batch_contains_all_sections(ledger, &format!("{}\n", digests.join("\n")))
                .expect("clean body must probe")
        );
        assert!(
            !batch_contains_all_sections(ledger, &format!("{}\n", digests[0]))
                .expect("clean body must probe")
        );
    }

    #[test]
    fn batch_probe_is_false_for_an_empty_ledger() {
        assert!(
            !batch_contains_all_sections("", "{\"category\":\"Warnings\",\"body\":\"- one\\n\"}\n")
                .expect("clean body must probe")
        );
    }
}
