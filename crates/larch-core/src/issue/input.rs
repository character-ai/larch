//! The `/issue` batch-input grammar.
//!
//! Ports Python `larch.issue.issue_create.parse_issue_input`. One file yields an
//! ordered item list: an OOS block introduced by `### OOS_<n>: <title>` with its
//! `- **Description**:` / `- **Concern**:` body and metadata fields, or the
//! generic `### <title>` fallback whose body is every following line. At a
//! generic heading boundary, the final separator newline belongs to the
//! boundary rather than the preceding body; additional blank lines remain body
//! content. Equivalent inner and final generic items therefore materialize
//! byte-identical bodies.
//!
//! Two rules make the grammar ambiguous on purpose, and both are load bearing.
//! A `### <heading>` inside an OOS body is held pending until the next line
//! decides whether it opened a new item or belongs to the body it interrupted,
//! and a heading inside a balanced code fence is payload rather than a
//! boundary. Item text is untrusted operator and reviewer prose, so nothing here
//! interprets it; the parser only decides where one item ends and the next
//! begins.

use crate::text::{balanced_fence_line_indices, split_text_lines};
use regex::Regex;
use std::sync::LazyLock;

/// One parsed item: its title, its verbatim body, and its OOS metadata.
///
/// `malformed` marks an item `/issue` must not file — a title with no body, or
/// an OOS block an ambiguous heading cut short before any field closed it.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedItem {
    pub title: String,
    pub body: String,
    pub reviewer: String,
    pub vote: String,
    pub phase: String,
    pub malformed: bool,
}

/// Which grammar read the file as a whole.
///
/// One OOS heading anywhere in the file makes the whole parse `oos`; the mode
/// never falls back to `generic` afterwards.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum InputMode {
    #[default]
    Generic,
    Oos,
}

impl InputMode {
    /// Render the token the `parse-input` breadcrumb prints.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Generic => "generic",
            Self::Oos => "oos",
        }
    }
}

/// The items one input file yields, plus the grammar that read them.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedInput {
    pub items: Vec<ParsedItem>,
    pub mode: InputMode,
}

/// Which grammar opened the item currently being read.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
enum ItemMode {
    #[default]
    None,
    Oos,
    Generic,
}

fn oos_heading_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^###[ \t]+OOS_[0-9]+:[ \t]+(.+)$").expect("OOS heading regex should compile")
    });
    &PATTERN
}

fn plain_heading_pattern() -> &'static Regex {
    static PATTERN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^###[ \t]+(.+)$").expect("plain heading regex should compile")
    });
    &PATTERN
}

/// `- **Concern**` is a Description equivalent and `- **Reviewer(s)**` a
/// Reviewer equivalent, so a review-pipeline FINDING block still captures a
/// body instead of filing an empty issue.
fn oos_field_patterns() -> &'static [(OosField, Regex); 5] {
    static PATTERNS: LazyLock<[(OosField, Regex); 5]> = LazyLock::new(|| {
        [
            (
                OosField::Description,
                Regex::new(r"^-[ \t]+\*\*Description\*\*:[ \t]*(.*)$")
                    .expect("description regex should compile"),
            ),
            (
                OosField::Concern,
                Regex::new(r"^-[ \t]+\*\*Concern\*\*:[ \t]*(.*)$")
                    .expect("concern regex should compile"),
            ),
            (
                OosField::Reviewer,
                Regex::new(r"^-[ \t]+\*\*Reviewer(?:\(s\))?\*\*:[ \t]+(.+)$")
                    .expect("reviewer regex should compile"),
            ),
            (
                OosField::Vote,
                Regex::new(r"^-[ \t]+\*\*Vote tally\*\*:[ \t]+(.+)$")
                    .expect("vote regex should compile"),
            ),
            (
                OosField::Phase,
                Regex::new(r"^-[ \t]+\*\*Phase\*\*:[ \t]+(.+)$")
                    .expect("phase regex should compile"),
            ),
        ]
    });
    &PATTERNS
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OosField {
    Description,
    Concern,
    Reviewer,
    Vote,
    Phase,
}

/// Parse one batch-input file into its ordered items.
#[must_use]
pub fn parse_issue_input(text: &str) -> ParsedInput {
    let lines = split_text_lines(text);
    let fenced = balanced_fence_line_indices(&lines);
    let mut state = ParseState::default();
    for (index, line) in lines.iter().enumerate() {
        let open = !fenced.contains(&index);
        if open && let Some(captures) = oos_heading_pattern().captures(line) {
            state.read_oos_heading(line, &captures[1]);
        } else if open && let Some(captures) = plain_heading_pattern().captures(line) {
            state.read_plain_heading(line, &captures[1]);
        } else if open && state.current_mode == ItemMode::Oos && state.consume_oos_field(line) {
        } else if state.in_body {
            state.append_body_line(line);
        }
    }
    state.split_pending();
    state.emit_current();
    ParsedInput {
        items: state.items,
        mode: state.parse_mode,
    }
}

/// The scan's in-place state: the item being read, the heading held pending,
/// and the items already closed.
#[derive(Debug, Default)]
struct ParseState {
    current: ParsedItem,
    in_body: bool,
    current_mode: ItemMode,
    parse_mode: InputMode,
    pending_heading: String,
    pending_body: String,
    items: Vec<ParsedItem>,
}

impl ParseState {
    /// Read an `### OOS_<n>:` line as a boundary, or absorb it into a generic
    /// body that has already collected prose.
    fn read_oos_heading(&mut self, line: &str, title: &str) {
        if self.current_mode == ItemMode::Generic
            && self.in_body
            && !self.current.body.trim().is_empty()
        {
            self.append_line(line);
            return;
        }
        let title = title.to_owned();
        self.split_pending();
        self.emit_current();
        self.current.title = title;
        // Default to body capture so an OOS block with no `- **Description**:`
        // line still accumulates its content. A following metadata field flips
        // this back off.
        self.in_body = true;
        self.current_mode = ItemMode::Oos;
        self.parse_mode = InputMode::Oos;
    }

    /// Read a generic `### <title>` line, holding it pending inside an OOS body.
    fn read_plain_heading(&mut self, line: &str, title: &str) {
        if self.current_mode == ItemMode::Oos && self.in_body {
            self.hold_pending(line);
            return;
        }
        self.drop_generic_boundary_separator();
        self.emit_current();
        title.clone_into(&mut self.current.title);
        self.in_body = true;
        self.current_mode = ItemMode::Generic;
    }

    /// Remove exactly the separator newline that a following generic heading
    /// owns. Any earlier blank lines remain part of the preceding body.
    fn drop_generic_boundary_separator(&mut self) {
        if self.current_mode == ItemMode::Generic && self.current.body.ends_with('\n') {
            self.current.body.pop();
        }
    }

    /// Append one body line, routing it into the pending block when a heading
    /// is still undecided.
    fn append_body_line(&mut self, line: &str) {
        if self.pending_heading.is_empty() {
            self.append_line(line);
        } else {
            append_paragraph(&mut self.pending_body, line);
        }
    }

    fn append_line(&mut self, line: &str) {
        append_paragraph(&mut self.current.body, line);
    }

    /// Hold an ambiguous heading, or extend the block already held.
    fn hold_pending(&mut self, line: &str) {
        if self.pending_heading.is_empty() {
            line.clone_into(&mut self.pending_heading);
        } else {
            append_paragraph(&mut self.pending_body, line);
        }
    }

    /// Resolve the pending heading as body text of the item that held it.
    fn fold_pending(&mut self) {
        if self.pending_heading.is_empty() {
            return;
        }
        let heading = std::mem::take(&mut self.pending_heading);
        let body = std::mem::take(&mut self.pending_body);
        append_paragraph(&mut self.current.body, &heading);
        if !body.is_empty() {
            append_paragraph(&mut self.current.body, &body);
        }
    }

    /// Resolve the pending heading as a new item, and close the interrupted one
    /// as malformed because no field ever ended its body.
    fn split_pending(&mut self) {
        if self.pending_heading.is_empty() {
            return;
        }
        let heading = std::mem::take(&mut self.pending_heading);
        let body = std::mem::take(&mut self.pending_body);
        if !self.current.title.is_empty() {
            let mut interrupted = std::mem::take(&mut self.current);
            interrupted.malformed = true;
            self.items.push(interrupted);
        }
        self.current = ParsedItem::default();
        self.in_body = false;
        self.current_mode = ItemMode::None;
        if let Some(captures) = plain_heading_pattern().captures(&heading) {
            self.items.push(ParsedItem {
                title: captures[1].to_owned(),
                malformed: body.is_empty(),
                body,
                ..ParsedItem::default()
            });
        }
    }

    /// Close the item being read, dropping a boundary that never got a title.
    fn emit_current(&mut self) {
        if self.current.title.is_empty() {
            self.reset();
            return;
        }
        let mut item = std::mem::take(&mut self.current);
        item.malformed = item.body.is_empty();
        self.items.push(item);
        self.reset();
    }

    fn reset(&mut self) {
        self.current = ParsedItem::default();
        self.in_body = false;
        self.current_mode = ItemMode::None;
        self.pending_heading.clear();
        self.pending_body.clear();
    }

    /// Consume one OOS body or metadata line, reporting whether it matched.
    ///
    /// Every field first folds the pending heading back into the body, because
    /// reaching a field proves the heading did not open a new item.
    fn consume_oos_field(&mut self, line: &str) -> bool {
        let Some((field, captures)) = oos_field_patterns()
            .iter()
            .find_map(|(field, pattern)| pattern.captures(line).map(|captures| (*field, captures)))
        else {
            return false;
        };
        let value = captures[1].to_owned();
        self.fold_pending();
        match field {
            // A `Description` line restates the body, so it replaces whatever
            // the fold just produced.
            OosField::Description => {
                self.current.body = value;
                self.in_body = true;
            }
            OosField::Concern => {
                if self.current.body.is_empty() {
                    self.current.body = value;
                } else if !value.is_empty() {
                    append_paragraph(&mut self.current.body, &value);
                }
                self.in_body = true;
            }
            OosField::Reviewer => {
                self.current.reviewer = value;
                self.in_body = false;
            }
            OosField::Vote => {
                self.current.vote = value;
                self.in_body = false;
            }
            OosField::Phase => {
                self.current.phase = value;
                self.in_body = false;
            }
        }
        true
    }
}

/// Append `line` to `target`, separating it with a newline only when `target`
/// already holds text. An empty target keeps the line verbatim, so no body ever
/// gains a leading newline.
fn append_paragraph(target: &mut String, line: &str) {
    if !target.is_empty() {
        target.push('\n');
    }
    target.push_str(line);
}
