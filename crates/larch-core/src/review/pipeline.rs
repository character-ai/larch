//! Typed, side-effect-free helpers shared by review pipeline commands.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};

use crate::{KvDocument, ParseOptions};

/// Stable help text for `review gather-context`.
pub const GATHER_CONTEXT_USAGE: &str = "Usage: review gather-context --mode diff|description --output-dir DIR [--description-text TEXT --scope-files FILE]";

/// Context source selected by `review gather-context`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GatherContextMode {
    /// Collect the branch diff, changed-file list, and commit summary.
    Diff,
    /// Find scoped repository files from a description.
    Description,
}

impl GatherContextMode {
    /// Return the stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Diff => "diff",
            Self::Description => "description",
        }
    }

    fn parse(value: &str) -> Option<Self> {
        match value {
            "diff" => Some(Self::Diff),
            "description" => Some(Self::Description),
            _ => None,
        }
    }
}

/// Validated `review gather-context` arguments.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GatherContextArguments {
    /// Selected context source.
    pub mode: GatherContextMode,
    /// Destination directory. An empty spelling intentionally retains Python's
    /// current-directory compatibility behavior.
    pub output_dir: String,
    /// Free-form description used only by description mode.
    pub description_text: String,
    /// Optional caller-selected file-list path.
    pub scope_files: String,
}

/// Result of parsing the legacy-compatible gather-context option grammar.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GatherContextParse {
    /// `--help` was present anywhere in the argument list.
    Help,
    /// A validated request.
    Arguments(GatherContextArguments),
}

/// One gather-context option grammar failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GatherContextArgumentError {
    /// An option was not part of the established grammar.
    UnknownOption(String),
    /// An option had no following value.
    MissingValue(String),
    /// `--mode` was missing or held an unsupported value.
    InvalidMode,
}

impl GatherContextArgumentError {
    /// Render the exact diagnostic prefix used by the Python owner.
    #[must_use]
    pub fn prefix(&self) -> String {
        match self {
            Self::UnknownOption(option) => format!("unknown option: {option}"),
            Self::MissingValue(option) => format!("{option} requires a value"),
            Self::InvalidMode => {
                "review gather-context: --mode must be diff or description".to_owned()
            }
        }
    }

    /// Whether the usage text follows the diagnostic without an inserted line break.
    #[must_use]
    pub const fn includes_usage(&self) -> bool {
        !matches!(self, Self::InvalidMode)
    }
}

/// Parse `review gather-context` options without performing filesystem work.
///
/// The parser deliberately mirrors the small Python helper: duplicate options
/// use the last spelling, `--help` wins even after an unknown option, and an
/// option-looking next token remains a value when one is required.
///
/// # Errors
///
/// Returns the corresponding legacy grammar error for an unknown option, a
/// missing option value, or an unsupported mode.
pub fn parse_gather_context_arguments(
    arguments: &[String],
) -> Result<GatherContextParse, GatherContextArgumentError> {
    if arguments.iter().any(|argument| argument == "--help") {
        return Ok(GatherContextParse::Help);
    }
    let mut values = BTreeMap::new();
    let mut index = 0_usize;
    while index < arguments.len() {
        let option = &arguments[index];
        if !matches!(
            option.as_str(),
            "--mode" | "--output-dir" | "--description-text" | "--scope-files"
        ) {
            return Err(GatherContextArgumentError::UnknownOption(option.clone()));
        }
        let Some(value) = arguments.get(index + 1) else {
            return Err(GatherContextArgumentError::MissingValue(option.clone()));
        };
        values.insert(option.clone(), value.clone());
        index += 2;
    }
    let mode = values.get("--mode").map_or("", String::as_str);
    let Some(mode) = GatherContextMode::parse(mode) else {
        return Err(GatherContextArgumentError::InvalidMode);
    };
    Ok(GatherContextParse::Arguments(GatherContextArguments {
        mode,
        output_dir: values.remove("--output-dir").unwrap_or_default(),
        description_text: values.remove("--description-text").unwrap_or_default(),
        scope_files: values.remove("--scope-files").unwrap_or_default(),
    }))
}

/// Derive at most twenty lower-cased path-search tokens from a description.
#[must_use]
pub fn description_tokens(description: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    for character in description.chars() {
        if character.is_ascii_alphanumeric() || matches!(character, '_' | '.' | '/' | '-') {
            current.push(character.to_ascii_lowercase());
            continue;
        }
        push_description_token(&mut tokens, &mut current);
    }
    push_description_token(&mut tokens, &mut current);
    tokens.truncate(20);
    tokens
}

fn push_description_token(tokens: &mut Vec<String>, current: &mut String) {
    if current.len() >= 3 {
        tokens.push(std::mem::take(current));
    } else {
        current.clear();
    }
}

/// Return whether one `git ls-files` or `rg` result is eligible for the
/// description-mode file list before the caller checks the filesystem.
#[must_use]
pub fn valid_relative_review_path(path: &str) -> bool {
    !path.is_empty()
        && !path.starts_with('/')
        && !path.contains("..")
        && !path.contains(['\n', '\r', '\t'])
}

/// Select the token-matching path names in deterministic order.
#[must_use]
pub fn description_path_matches<'a>(
    tokens: &[String],
    paths: impl IntoIterator<Item = &'a str>,
    mut eligible: impl FnMut(&str) -> bool,
) -> BTreeSet<String> {
    let mut matches = BTreeSet::new();
    if tokens.is_empty() {
        return matches;
    }
    for path in paths {
        let lowercase = path.to_ascii_lowercase();
        if tokens.iter().any(|token| lowercase.contains(token)) && eligible(path) {
            matches.insert(path.to_owned());
        }
    }
    matches
}

/// Parse collector output into `REVIEWER_FILE`-anchored records.
///
/// Leading diagnostics never form a record and a new anchor closes the
/// preceding record. Duplicate key lines retain the final value, matching the
/// existing key/value decoder.
#[must_use]
pub fn parse_collector_records(text: &str) -> Vec<BTreeMap<String, String>> {
    let mut records = Vec::new();
    let mut current: Option<BTreeMap<String, String>> = None;
    for line in text.lines() {
        let Ok(document) = KvDocument::parse(line, ParseOptions::legacy()) else {
            continue;
        };
        let Some(row) = document.rows().first() else {
            if line.trim().is_empty()
                && let Some(record) = current.take()
            {
                records.push(record);
            }
            continue;
        };
        let key = row.key();
        let value = row.value();
        if key == "REVIEWER_FILE" {
            if let Some(record) =
                current.replace(BTreeMap::from([(key.to_owned(), value.to_owned())]))
            {
                records.push(record);
            }
        } else if let Some(record) = &mut current {
            record.insert(key.to_owned(), value.to_owned());
        }
    }
    if let Some(record) = current {
        records.push(record);
    }
    records
}

/// Parse legacy blank-line-delimited blocks, keeping malformed leading blocks.
#[must_use]
pub fn parse_legacy_collector_blocks(text: &str) -> Vec<BTreeMap<String, String>> {
    let mut records = Vec::new();
    let mut current = BTreeMap::<String, String>::new();
    for line in crate::split_text_lines(text) {
        if line.is_empty() {
            if !current.is_empty() {
                records.push(std::mem::take(&mut current));
            }
            continue;
        }
        let Ok(document) = KvDocument::parse(line, ParseOptions::legacy()) else {
            continue;
        };
        let Some(row) = document.rows().first() else {
            continue;
        };
        current.insert(row.key().to_owned(), row.value().to_owned());
    }
    if !current.is_empty() {
        records.push(current);
    }
    records
}

/// Normalize a reviewer output basename across retry and phase suffixes.
#[must_use]
pub fn normalize_output_base(base: &str) -> String {
    let base = Path::new(base)
        .file_name()
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned());
    let fallback = base.clone();
    let (mut stem, extension) = base
        .strip_suffix(".txt")
        .map_or((fallback, ""), |value| (value.to_owned(), ".txt"));
    loop {
        let next = ["-phase2", "-phase3", "-retry"]
            .iter()
            .find_map(|suffix| stem.strip_suffix(suffix))
            .map(str::to_owned);
        let Some(next) = next else {
            break;
        };
        stem = next;
    }
    format!("{stem}{extension}")
}

/// Parse the review pipeline's positive integer option shape.
#[must_use]
pub fn positive_integer(value: &str) -> Option<usize> {
    value
        .bytes()
        .all(|byte| byte.is_ascii_digit())
        .then(|| value.parse::<usize>().ok())
        .flatten()
        .filter(|parsed| *parsed > 0)
}
