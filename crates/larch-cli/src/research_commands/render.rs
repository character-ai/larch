//! The `/research` findings issue-batch renderer ported from Python.
//!
//! This helper cluster (`render_findings_issue_batch` and its section, flatten,
//! split, title, and escape helpers) was used only by `research
//! render-findings-batch`, never by `render findings-view`, so #8499 ports it
//! into the Rust research owner and deletes the superseded Python. The output is
//! byte-for-byte the retired payload.

use std::fmt::Write as _;
use std::sync::LazyLock;

use larch_core::split_text_lines;
use regex::Regex;

/// Headers that terminate the `### Findings Summary` section body.
const END_HEADERS: &[&str] = &[
    "### Risk Assessment",
    "### Difficulty Estimate",
    "### Feasibility Verdict",
    "### Key Files and Areas",
    "### Open Questions",
];

const FINDINGS_HEADER: &str = "### Findings Summary";
const PUNCTUATION: &str = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";

static FENCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*```").expect("fence regex"));
static SUBQUESTION_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)^####\s+subquestion\s+[0-9]+").expect("subquestion regex"));
static NUMBERED_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*[0-9]+\.[ \t]").expect("numbered regex"));
static BULLETED_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]{0,2}[-*][ \t]").expect("bulleted regex"));
static INDENT_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"^[ \t]+").expect("indent regex"));
static NUM_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*[0-9]+\.[ \t]+").expect("numbered-prefix regex"));
static BULLET_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*[-*][ \t]+").expect("bullet-prefix regex"));
static FLATTEN_BULLET_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*[-*][ \t]*").expect("flatten bullet-prefix regex"));
static QUOTE_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*>[ \t]*").expect("quote-prefix regex"));
static HEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^###[ \t]").expect("heading regex"));

/// The per-run context threaded into every rendered issue-batch item.
pub struct FindingsContext<'a> {
    pub research_question: &'a str,
    pub branch: &'a str,
    pub commit: &'a str,
    pub timestamp: &'a str,
}

/// Render `/research` findings. Returns `(count, markdown, section_absent)`.
#[must_use]
pub fn render_findings_issue_batch(
    report_text: &str,
    context: &FindingsContext<'_>,
) -> (usize, String, bool) {
    let findings = extract_markdown_section(report_text, FINDINGS_HEADER);
    let section_absent = !split_text_lines(report_text)
        .into_iter()
        .any(|line| line == FINDINGS_HEADER);
    let items = split_finding_items(&findings);
    if items.is_empty() {
        return (0, String::new(), section_absent);
    }
    let metadata = Metadata::from_report(report_text);
    let payload = render_issue_batch_items(&items, &metadata, context);
    (items.len(), payload, section_absent)
}

/// The flattened metadata block a rendered item repeats verbatim.
struct Metadata {
    risk: String,
    difficulty: String,
    feasibility: String,
    files_touched: String,
    open_questions: String,
}

impl Metadata {
    fn from_report(report_text: &str) -> Self {
        Self {
            risk: flatten_metadata(report_text, "### Risk Assessment", "N/A", " "),
            difficulty: flatten_metadata(report_text, "### Difficulty Estimate", "N/A", " "),
            feasibility: flatten_metadata(report_text, "### Feasibility Verdict", "N/A", " "),
            files_touched: flatten_metadata(report_text, "### Key Files and Areas", "N/A", ", "),
            open_questions: flatten_metadata(report_text, "### Open Questions", "", "; "),
        }
    }
}

/// Return a fenced-aware markdown section body without its start header.
fn extract_markdown_section(text: &str, start_header: &str) -> String {
    let mut in_section = false;
    let mut in_fence = false;
    let mut out: Vec<&str> = Vec::new();
    for line in split_text_lines(text) {
        if FENCE_RE.is_match(line) {
            if in_section {
                out.push(line);
            }
            in_fence = !in_fence;
            continue;
        }
        if in_fence {
            if in_section {
                out.push(line);
            }
            continue;
        }
        if !in_section {
            if line == start_header {
                in_section = true;
            }
            continue;
        }
        if line.starts_with("## ") || END_HEADERS.contains(&line) {
            break;
        }
        out.push(line);
    }
    out.join("\n")
}

/// Trim only leading and trailing blank lines from `text`.
fn strip_outer_blank_lines(text: &str) -> String {
    let lines = split_text_lines(text);
    let start = lines.iter().position(|line| !line.trim().is_empty());
    let Some(start) = start else {
        return String::new();
    };
    let end = lines
        .iter()
        .rposition(|line| !line.trim().is_empty())
        .unwrap_or(start);
    lines[start..=end].join("\n")
}

/// Extract a section and flatten its non-empty lines into one metadata value.
fn flatten_metadata(text: &str, header: &str, default: &str, joiner: &str) -> String {
    let body = strip_outer_blank_lines(&extract_markdown_section(text, header));
    if body.is_empty() {
        return default.to_owned();
    }
    let values: Vec<String> = split_text_lines(&body)
        .into_iter()
        .map(|line| {
            let without_bullet = FLATTEN_BULLET_RE.replace(line, "");
            QUOTE_PREFIX_RE
                .replace(&without_bullet, "")
                .trim()
                .to_owned()
        })
        .filter(|value| !value.is_empty())
        .collect();
    if values.is_empty() {
        return default.to_owned();
    }
    values.join(joiner)
}

/// The running state of the finding splitter.
#[derive(Default)]
struct Splitter {
    items: Vec<String>,
    current: Vec<String>,
    mode: &'static str,
    base_indent: usize,
    in_fence: bool,
}

impl Splitter {
    fn emit_current(&mut self) {
        let item = strip_outer_blank_lines(&self.current.join("\n"));
        if !item.is_empty() {
            self.items.push(item);
        }
        self.current.clear();
    }

    fn start(&mut self, mode: &'static str, line: &str, indent: usize) {
        self.mode = mode;
        self.current = vec![line.to_owned()];
        self.base_indent = indent;
    }

    fn feed(&mut self, line: &str) {
        if line.starts_with("```") {
            self.in_fence = !self.in_fence;
            self.current.push(line.to_owned());
            return;
        }
        if self.in_fence {
            self.current.push(line.to_owned());
            return;
        }
        if SUBQUESTION_RE.is_match(line) {
            self.emit_current();
            self.base_indent = 0;
            return;
        }
        self.feed_item_line(line);
    }

    fn feed_item_line(&mut self, line: &str) {
        let is_numbered = NUMBERED_RE.is_match(line);
        let is_bulleted = BULLETED_RE.is_match(line);
        let indent = INDENT_RE
            .find(line)
            .map_or(0, |matched| matched.as_str().len());
        if self.mode.is_empty() {
            self.feed_first(line, is_numbered, is_bulleted, indent);
            return;
        }
        if self.current.is_empty() && (is_numbered || is_bulleted) {
            self.start(
                if is_numbered { "numbered" } else { "bulleted" },
                line,
                indent,
            );
            return;
        }
        if (is_numbered || is_bulleted) && indent <= self.base_indent {
            self.emit_current();
            self.start(
                if is_numbered { "numbered" } else { "bulleted" },
                line,
                indent,
            );
            return;
        }
        if self.mode == "paragraph" && line.trim().is_empty() {
            self.emit_current();
            self.base_indent = 0;
            return;
        }
        self.current.push(line.to_owned());
    }

    fn feed_first(&mut self, line: &str, is_numbered: bool, is_bulleted: bool, indent: usize) {
        if is_numbered {
            self.start("numbered", line, indent);
        } else if is_bulleted {
            self.start("bulleted", line, indent);
        } else if !line.trim().is_empty() {
            self.mode = "paragraph";
            self.current = vec![line.to_owned()];
        }
    }
}

/// Split a Findings Summary body into numbered, bullet, or paragraph items.
fn split_finding_items(findings_text: &str) -> Vec<String> {
    let text = strip_outer_blank_lines(findings_text);
    if text.is_empty() {
        return Vec::new();
    }
    let mut splitter = Splitter::default();
    for line in split_text_lines(&text) {
        splitter.feed(line);
    }
    splitter.emit_current();
    splitter.items
}

/// Derive a stable issue title from the first finding sentence.
fn finding_title_from_body(body: &str, index: usize) -> String {
    let first_line = split_text_lines(body)
        .first()
        .map_or(String::new(), |line| (*line).to_owned());
    let without_number = NUM_PREFIX_RE.replace(&first_line, "");
    let first = BULLET_PREFIX_RE
        .replace(&without_number, "")
        .trim()
        .to_owned();
    let chars: Vec<char> = first.chars().collect();
    let mut sentence: Vec<char> = chars.clone();
    for window in 0..chars.len().saturating_sub(1) {
        if matches!(chars[window], '.' | '!' | '?') && chars[window + 1] == ' ' {
            sentence = chars[..window].to_vec();
            break;
        }
    }
    if sentence.len() > 80 {
        sentence.truncate(80);
    }
    let trimmed: String = sentence
        .into_iter()
        .collect::<String>()
        .trim_end_matches(|ch: char| is_python_whitespace(ch) || PUNCTUATION.contains(ch))
        .to_owned();
    if trimmed.is_empty() {
        format!("Finding {index}")
    } else {
        trimmed
    }
}

/// The six ASCII bytes Python's `string.whitespace` strips, and no others.
const fn is_python_whitespace(ch: char) -> bool {
    matches!(ch, ' ' | '\t' | '\n' | '\r' | '\u{0b}' | '\u{0c}')
}

/// Escape body lines that would otherwise read as issue-batch `### ` headings.
fn escape_issue_body_lines(body: &str) -> String {
    let mut in_fence = false;
    let mut out: Vec<String> = Vec::new();
    for line in split_text_lines(body) {
        if FENCE_RE.is_match(line) {
            in_fence = !in_fence;
            out.push(line.to_owned());
        } else if !in_fence && HEADING_RE.is_match(line) {
            out.push(format!("\\{line}"));
        } else {
            out.push(line.to_owned());
        }
    }
    out.join("\n")
}

/// Render generic `### <title>` issue-batch markdown for every finding item.
fn render_issue_batch_items(
    items: &[String],
    metadata: &Metadata,
    context: &FindingsContext<'_>,
) -> String {
    let mut chunks = String::new();
    for (offset, item) in items.iter().enumerate() {
        let index = offset + 1;
        let title = finding_title_from_body(item, index);
        let prose = escape_issue_body_lines(item);
        let _ = write!(
            chunks,
            "### {title}\n\n\
**Source**: /research output, branch `{branch}` at `{commit}`, run {timestamp}\n\
**Risk**: {risk}\n\
**Difficulty**: {difficulty}\n\
**Feasibility**: {feasibility}\n\
**Files touched**: {files}\n\n\
{prose}\n",
            branch = context.branch,
            commit = context.commit,
            timestamp = context.timestamp,
            risk = metadata.risk,
            difficulty = metadata.difficulty,
            feasibility = metadata.feasibility,
            files = metadata.files_touched,
        );
        if !metadata.open_questions.is_empty() {
            let _ = write!(
                chunks,
                "\n**Open questions** (if any): {}\n",
                metadata.open_questions
            );
        }
        let _ = write!(
            chunks,
            "\n---\n*This issue was filed from /research output. Audit context: {}*\n\n",
            context.research_question
        );
    }
    chunks
}
