//! Shared Rust and Markdown syntax support for rule implementations.

use std::sync::LazyLock;

use pulldown_cmark::Parser;
use regex::Regex;
use tree_sitter::Parser as TreeSitterParser;

use crate::LintError;

static INLINE_COMMAND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:run|execute|invoke|call|use)\s*:?\s*$")
        .expect("inline command lead-in is valid")
});
static NEGATED_INLINE_COMMAND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:do\s+not|don't|never)\s+(?:run|execute|invoke|call|use)\s*:?\s*$")
        .expect("negated inline command lead-in is valid")
});
static INLINE_CODE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"`([^`\n]+)`").expect("inline code expression is valid"));
static JSON_COMMAND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?s)\"command\"\s*:\s*\"((?:\\.|[^\"\\])*)\""#)
        .expect("JSON command expression is valid")
});

/// Parse one Rust source file and retain its source identity for diagnostics.
pub struct RustSyntax {
    path: String,
    file: syn::File,
}

impl RustSyntax {
    /// Parse Rust source with `syn`'s complete-file grammar.
    ///
    /// # Errors
    ///
    /// Returns a deterministic diagnostic when the source is not valid Rust.
    pub fn parse(path: impl Into<String>, source: &str) -> Result<Self, LintError> {
        let path = path.into();
        let file = syn::parse_file(source)
            .map_err(|error| LintError::new(format!("{path}: invalid Rust syntax: {error}")))?;
        Ok(Self { path, file })
    }

    /// Return the repository-relative source path.
    #[must_use]
    pub fn path(&self) -> &str {
        &self.path
    }

    /// Return the parsed syntax tree.
    #[must_use]
    pub const fn file(&self) -> &syn::File {
        &self.file
    }
}

/// Parse Bash source with the workspace's maintained grammar.
///
/// # Errors
///
/// Returns an error when the parser cannot be configured or produce a tree.
pub fn parse_bash(source: &str) -> Result<tree_sitter::Tree, LintError> {
    let mut parser = TreeSitterParser::new();
    parser
        .set_language(&tree_sitter_bash::LANGUAGE.into())
        .map_err(|error| LintError::new(format!("cannot configure Bash parser: {error}")))?;
    parser
        .parse(source, None)
        .ok_or_else(|| LintError::new("cannot parse Bash source"))
}

/// Parse Python source with the workspace's maintained grammar.
///
/// # Errors
///
/// Returns an error when the parser cannot be configured or produce a tree.
pub fn parse_python(source: &str) -> Result<tree_sitter::Tree, LintError> {
    let mut parser = TreeSitterParser::new();
    parser
        .set_language(&tree_sitter_python::LANGUAGE.into())
        .map_err(|error| LintError::new(format!("cannot configure Python parser: {error}")))?;
    parser
        .parse(source, None)
        .ok_or_else(|| LintError::new("cannot parse Python source"))
}

/// Return leaf Bash commands, excluding heredoc payloads.
#[must_use]
pub fn leaf_bash_commands(tree: &tree_sitter::Tree) -> Vec<tree_sitter::Node<'_>> {
    let mut commands = Vec::new();
    collect_leaf_bash_commands(tree.root_node(), false, &mut commands);
    commands
}

fn collect_leaf_bash_commands<'tree>(
    node: tree_sitter::Node<'tree>,
    within_heredoc: bool,
    commands: &mut Vec<tree_sitter::Node<'tree>>,
) {
    let inside_heredoc = within_heredoc || node.kind() == "heredoc_body";
    if node.kind() == "command" && !inside_heredoc && !contains_nested_bash_command(node) {
        commands.push(node);
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_leaf_bash_commands(child, inside_heredoc, commands);
    }
}

fn contains_nested_bash_command(node: tree_sitter::Node<'_>) -> bool {
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .any(|child| child.kind() == "command" || contains_nested_bash_command(child))
}

/// One executable shell command extracted from a runtime source surface.
#[derive(Debug, Eq, PartialEq)]
pub struct ShellCommand {
    line: usize,
    words: Vec<String>,
}

impl ShellCommand {
    /// Return the one-based source line of the command.
    #[must_use]
    pub const fn line(&self) -> usize {
        self.line
    }

    /// Return the normalized command words.
    #[must_use]
    pub fn words(&self) -> &[String] {
        &self.words
    }
}

/// Parse shell source into leaf commands with normalized words and source lines.
///
/// # Errors
///
/// Returns an error when the Bash parser cannot parse the source.
pub fn shell_commands(source: &str, line_offset: usize) -> Result<Vec<ShellCommand>, LintError> {
    let tree = parse_bash(source)?;
    Ok(leaf_bash_commands(&tree)
        .into_iter()
        .map(|command| ShellCommand {
            line: command.start_position().row + line_offset + 1,
            words: shell_command_words(command, source),
        })
        .collect())
}

/// Return normalized words for one parsed leaf Bash command.
#[must_use]
pub fn shell_command_words(command: tree_sitter::Node<'_>, source: &str) -> Vec<String> {
    let Some(name) = command.child_by_field_name("name") else {
        return Vec::new();
    };
    let mut words = vec![normalize_shell_word(
        source.get(name.byte_range()).unwrap_or(""),
    )];
    let mut cursor = command.walk();
    words.extend(
        command
            .children_by_field_name("argument", &mut cursor)
            .map(|argument| normalize_shell_word(source.get(argument.byte_range()).unwrap_or(""))),
    );
    words
}

/// Normalize a statically recoverable shell word for command matching.
#[must_use]
pub fn normalize_shell_word(word: &str) -> String {
    word.replace("\\\n", "")
        .replace(['\"', '\''], "")
        .replace('\\', "/")
}

/// Extract executable shell commands from Bash fences and command-like inline code.
///
/// # Errors
///
/// Returns an error when an executable snippet cannot be parsed as Bash.
pub fn markdown_shell_commands(source: &str) -> Result<Vec<ShellCommand>, LintError> {
    let mut commands = Vec::new();
    let mut block = String::new();
    let mut block_start = 0;
    for line in MarkdownDocument::new(source).lines() {
        let executable = matches!(
            line.fence_state(),
            FenceState::Inside { language: Some(language) } if is_shell_language(language)
        ) && !line.is_fence_boundary();
        if executable {
            if block.is_empty() {
                block_start = line.number() - 1;
            }
            block.push_str(
                line.text()
                    .strip_prefix("$ ")
                    .unwrap_or_else(|| line.text()),
            );
            block.push('\n');
        } else if !block.is_empty() {
            commands.extend(shell_commands(&block, block_start)?);
            block.clear();
        }
        if matches!(line.fence_state(), FenceState::Outside) {
            commands.extend(inline_shell_commands(line.number(), line.text())?);
        }
    }
    if !block.is_empty() {
        commands.extend(shell_commands(&block, block_start)?);
    }
    Ok(commands)
}

fn is_shell_language(language: &str) -> bool {
    matches!(
        language.to_ascii_lowercase().as_str(),
        "bash" | "sh" | "shell" | "console"
    )
}

fn inline_shell_commands(line: usize, text: &str) -> Result<Vec<ShellCommand>, LintError> {
    let mut commands = Vec::new();
    for capture in INLINE_CODE.captures_iter(text) {
        let Some(command) = capture.get(1) else {
            continue;
        };
        let lead_in = &text[..capture.get(0).map_or(0, |matched| matched.start())];
        if !INLINE_COMMAND.is_match(lead_in) || NEGATED_INLINE_COMMAND.is_match(lead_in) {
            continue;
        }
        commands.extend(shell_commands(command.as_str(), line.saturating_sub(1))?);
    }
    Ok(commands)
}

/// Extract shell commands from JSON `command` string fields.
///
/// # Errors
///
/// Returns an error when a command string is invalid JSON or invalid Bash.
pub fn json_shell_commands(path: &str, source: &str) -> Result<Vec<ShellCommand>, LintError> {
    let mut commands = Vec::new();
    for capture in JSON_COMMAND.captures_iter(source) {
        let Some(raw) = capture.get(1) else {
            continue;
        };
        let encoded = format!("\"{}\"", raw.as_str());
        let command: String = serde_json::from_str(&encoded)
            .map_err(|error| LintError::new(format!("{path}: invalid command string: {error}")))?;
        let line = source[..raw.start()].lines().count();
        commands.extend(shell_commands(&command, line.saturating_sub(1))?);
    }
    Ok(commands)
}

/// Return the one-based line of the `occurrence`-th match of `needle`.
///
/// # Errors
///
/// Returns an error when the occurrence cannot be located or the line number
/// cannot be represented as `u32`.
pub fn line_of_occurrence(source: &str, needle: &str, occurrence: u32) -> Result<u32, LintError> {
    let mut seen = 0_u32;
    for (index, line) in source.lines().enumerate() {
        let mut rest = line;
        while let Some(offset) = rest.find(needle) {
            seen = seen.saturating_add(1);
            if seen == occurrence {
                return u32::try_from(index + 1)
                    .map_err(|_| LintError::new("line number exceeds u32"));
            }
            rest = &rest[offset + needle.len()..];
        }
    }
    Err(LintError::new(format!(
        "cannot locate needle {needle:?} occurrence {occurrence}"
    )))
}

/// Whether a Markdown line is outside a fence or inside one with an optional language.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FenceState<'source> {
    /// The line is ordinary Markdown.
    Outside,
    /// The line belongs to a fenced code block.
    Inside { language: Option<&'source str> },
}

/// One source line annotated with its fenced-code state.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MarkdownLine<'source> {
    number: usize,
    text: &'source str,
    fence_state: FenceState<'source>,
    fence_boundary: bool,
}

impl<'source> MarkdownLine<'source> {
    /// Return the one-based source line number.
    #[must_use]
    pub const fn number(self) -> usize {
        self.number
    }

    /// Return the line without its newline terminator.
    #[must_use]
    pub const fn text(self) -> &'source str {
        self.text
    }

    /// Return whether this line appears within a fenced code block.
    #[must_use]
    pub const fn fence_state(self) -> FenceState<'source> {
        self.fence_state
    }

    /// Return whether this line closes the active fenced code block.
    #[must_use]
    pub const fn is_fence_boundary(self) -> bool {
        self.fence_boundary
    }
}

/// A Markdown document with `CommonMark` events and line-oriented fence state.
#[derive(Debug)]
pub struct MarkdownDocument<'source> {
    source: &'source str,
}

impl<'source> MarkdownDocument<'source> {
    /// Retain source for structural `CommonMark` parsing and line-level rules.
    #[must_use]
    pub const fn new(source: &'source str) -> Self {
        Self { source }
    }

    /// Return the maintained `CommonMark` parser for structural rules.
    #[must_use]
    pub fn parser(&self) -> Parser<'source> {
        Parser::new(self.source)
    }

    /// Iterate source lines with deterministic fenced-code state.
    #[must_use]
    pub fn lines(&self) -> MarkdownLines<'source> {
        MarkdownLines {
            lines: self.source.lines().enumerate(),
            open_fence: None,
        }
    }
}

/// Iterator returned by [`MarkdownDocument::lines`].
pub struct MarkdownLines<'source> {
    lines: std::iter::Enumerate<std::str::Lines<'source>>,
    open_fence: Option<OpenFence<'source>>,
}

impl<'source> Iterator for MarkdownLines<'source> {
    type Item = MarkdownLine<'source>;

    fn next(&mut self) -> Option<Self::Item> {
        let (index, text) = self.lines.next()?;
        let (fence_state, fence_boundary) = match self.open_fence {
            Some(open_fence) if open_fence.closes(text) => {
                let state = FenceState::Inside {
                    language: open_fence.language,
                };
                self.open_fence = None;
                (state, true)
            }
            Some(open_fence) => (
                FenceState::Inside {
                    language: open_fence.language,
                },
                false,
            ),
            None => {
                if let Some(open_fence) = OpenFence::opens(text) {
                    self.open_fence = Some(open_fence);
                }
                (FenceState::Outside, false)
            }
        };
        Some(MarkdownLine {
            number: index + 1,
            text,
            fence_state,
            fence_boundary,
        })
    }
}

#[derive(Clone, Copy, Debug)]
struct OpenFence<'source> {
    marker: char,
    width: usize,
    language: Option<&'source str>,
}

impl<'source> OpenFence<'source> {
    fn opens(line: &'source str) -> Option<Self> {
        let trimmed = line.trim_start_matches([' ', '\t']);
        let marker = trimmed.chars().next()?;
        if marker != '`' && marker != '~' {
            return None;
        }
        let width = trimmed
            .chars()
            .take_while(|character| *character == marker)
            .count();
        if width < 3 {
            return None;
        }
        let info = trimmed[width..].trim();
        if info.contains(marker) {
            return None;
        }
        Some(Self {
            marker,
            width,
            language: info.split_whitespace().next(),
        })
    }

    fn closes(self, line: &str) -> bool {
        let trimmed = line.trim_start_matches([' ', '\t']);
        let width = trimmed
            .chars()
            .take_while(|character| *character == self.marker)
            .count();
        width >= self.width && trimmed[width..].trim().is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::{FenceState, MarkdownDocument, RustSyntax, line_of_occurrence};

    #[test]
    fn rust_syntax_reports_the_source_path() {
        let Err(error) = RustSyntax::parse("src/bad.rs", "fn {") else {
            panic!("invalid source unexpectedly parsed");
        };
        assert!(
            error
                .to_string()
                .starts_with("src/bad.rs: invalid Rust syntax:")
        );
    }

    #[test]
    fn line_of_occurrence_finds_the_nth_match() {
        let source = "alpha\nbeta alpha\nalpha\n";
        assert_eq!(line_of_occurrence(source, "alpha", 2).expect("second"), 2);
        assert_eq!(line_of_occurrence(source, "alpha", 3).expect("third"), 3);
        assert!(line_of_occurrence(source, "alpha", 4).is_err());
    }

    #[test]
    fn markdown_lines_track_fence_marker_width_and_language() {
        let document = MarkdownDocument::new("# heading\n```bash\n# ignored\n````\n# visible");
        let lines: Vec<_> = document.lines().collect();
        assert_eq!(lines[0].fence_state(), FenceState::Outside);
        assert_eq!(
            lines[2].fence_state(),
            FenceState::Inside {
                language: Some("bash")
            }
        );
        assert!(lines[3].is_fence_boundary());
        assert_eq!(lines[4].fence_state(), FenceState::Outside);
        assert!(document.parser().next().is_some());
    }
}
