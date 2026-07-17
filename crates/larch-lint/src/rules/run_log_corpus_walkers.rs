//! Reject raw committed run-log corpus walkers outside the shared owner.
//!
//! This is the future-state Rust equivalent of the Python `run-log-walkers`
//! lint. It scans production Rust sources for directory-walking calls
//! (`read_dir`, `glob`, `WalkDir::new`, `scandir`, `walk_dir`) whose argument
//! references a committed-corpus root, and for classification-glob families,
//! and reports any that appear outside the shared `run_log_corpus` owner
//! module. Validated per-run recursion must route through that owner.
//!
//! Line anchoring: the shared `syn` parser retains no source line numbers in
//! this build (the `proc-macro2` `span-locations` feature is not enabled, and a
//! leaf rule may not add a workspace dependency feature), so this rule matches
//! over source lines to report the exact offending line. Each line is first run
//! through a lexer that blanks comment, string, and char-literal spans, so a
//! walker token only matches a real call, never one quoted inside a string or a
//! comment. The corpus/session marker check is scoped to the parenthesized call
//! argument, so a marker on an adjacent statement does not bleed in. The
//! residual limitation is single-line: a call whose argument or corpus marker
//! spans multiple physical lines, or a multi-line raw string, is not tracked;
//! such cases can carry an inline suppression when intentional.
//!
//! Scope note: the larch-lint crate is excluded from the scanned surface, like
//! the sibling `wire-artifact-pairing` rule. It is tooling that names walker
//! vocabulary in rule definitions and test fixtures rather than run-time larch
//! code, so scanning it would report those meta-references. The runtime
//! migration lands larch runtime code in its own crate, which this rule scans.
//!
//! Deviation from the Python rule: within a scanned runtime crate, inline
//! `#[cfg(test)]` modules are scanned (integration `tests/` trees are already
//! outside the `src` scope). Test code that must walk a corpus root should
//! route through the owner or carry an inline suppression.
//!
//! Crate survey: comment and literal lexing and marker matching reuse the
//! workspace `regex` crate for the call pattern; inline suppression reuses the
//! crate [`crate::suppression`] helper; path selection reuses the
//! `globset`-backed [`PathSelector`]. The bespoke code expresses only the larch
//! corpus-ownership grammar (walker families, corpus and session markers,
//! classification patterns) and the line lexer, which no general crate owns
//! without pulling a full parser that this build cannot line-anchor.

use regex::Regex;

use crate::suppression;
use crate::{Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "run-log-corpus-walkers";
const DESCRIPTION: &str = "Reject raw committed run-log corpus walkers outside the shared owner";
const RUST_SCOPE_INCLUDE: &str = "crates/*/src/**/*.rs";
const LINTER_CRATE_EXCLUDE: &str = "crates/larch-lint/**";
const OWNER_SUFFIX: &str = "report/run_log_corpus.rs";
const SUPPRESSION_TOKEN: &str = "lint-run-log-corpus-walkers";
const CLASSIFICATION_MARKER: &str = "findings-classification";
const CLASSIFICATION_ROOTS: [&str; 3] = ["design/", "implement/", "review/"];

const CORPUS_MARKERS: [&str; 9] = [
    "larch-logs",
    "log_root",
    "log_base",
    "logs_root",
    "impl_root",
    "design_root",
    "implement_root",
    "skill_dir",
    "skill_root",
];
const SESSION_MARKERS: [&str; 6] = [
    "tmpdir",
    "implement_tmpdir",
    "design_tmpdir",
    "canonical_tmp",
    "session_tmpdir",
    "session_env",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/run-log-corpus-walkers.toml",
);

#[derive(Debug)]
pub struct RunLogCorpusWalkersRule;

pub static RULE: RunLogCorpusWalkersRule = RunLogCorpusWalkersRule;

impl Rule for RunLogCorpusWalkersRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let walker = walker_regex()?;
        let selector = PathSelector::new(&[RUST_SCOPE_INCLUDE], &[LINTER_CRATE_EXCLUDE])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            if is_owner(path) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            findings.extend(scan_source(path.as_str(), &source, &walker)?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

fn is_owner(path: &RepoPath) -> bool {
    path.as_str().ends_with(OWNER_SUFFIX)
}

fn walker_regex() -> Result<Regex, LintError> {
    // A directory-walking call: a family token followed by `(`, or `WalkDir::new(`.
    Regex::new(
        r"(?:^|[^A-Za-z0-9_])(read_dir|scandir|walk_dir|iglob|rglob|glob)\s*\(|(WalkDir)::new\s*\(",
    )
    .map_err(|error| LintError::new(format!("invalid walker pattern: {error}")))
}

fn scan_source(path: &str, source: &str, walker: &Regex) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    let mut block_depth = 0usize;
    for (index, raw) in source.lines().enumerate() {
        let view = clean_line(raw, &mut block_depth);
        let Some(detection) = classify(&view, walker) else {
            continue;
        };
        if suppression::reason(raw, SUPPRESSION_TOKEN)?.is_some() {
            continue;
        }
        let line = u32::try_from(index + 1)
            .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
        findings.push(Finding::new(path, line, detection.message()));
    }
    Ok(findings)
}

/// A classified corpus-walker violation and its remediation family.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Detection {
    Classification,
    Walk,
    Glob,
    ReadDir,
}

impl Detection {
    fn message(self) -> String {
        let remediation =
            "route through the run_log_corpus owner (safe_child_run_dirs / validated-run helpers)";
        match self {
            Self::Classification => "raw classification-glob outside run_log_corpus: use its \
                 classification discovery helpers"
                .to_owned(),
            Self::Walk => format!("raw corpus directory walk outside run_log_corpus: {remediation}"),
            Self::Glob => format!("raw corpus glob outside run_log_corpus: {remediation}"),
            Self::ReadDir => {
                format!("raw corpus directory read outside run_log_corpus: {remediation}")
            }
        }
    }
}

/// Classify a lexed line: match a real walker call, then judge its argument.
fn classify(view: &LineView, walker: &Regex) -> Option<Detection> {
    for captures in walker.captures_iter(&view.code) {
        let whole = captures.get(0)?;
        let argument = argument_slice(&view.code, &view.markers, whole.end());
        if is_classification(argument) {
            return Some(Detection::Classification);
        }
        if has_marker(argument, &CORPUS_MARKERS) && !has_marker(argument, &SESSION_MARKERS) {
            return Some(family(&captures));
        }
    }
    None
}

fn family(captures: &regex::Captures<'_>) -> Detection {
    if captures.get(2).is_some() {
        return Detection::Walk;
    }
    match captures.get(1).map(|token| token.as_str()) {
        Some("walk_dir") => Detection::Walk,
        Some("glob" | "iglob" | "rglob") => Detection::Glob,
        _ => Detection::ReadDir,
    }
}

/// Return the marker view of the call argument that begins at `arg_start`,
/// bounded by the matching close paren in the (literal-blanked) code view.
fn argument_slice<'markers>(code: &str, markers: &'markers str, arg_start: usize) -> &'markers str {
    let bytes = code.as_bytes();
    let mut depth = 1i32;
    let mut index = arg_start;
    while index < bytes.len() {
        match bytes[index] {
            b'(' => depth += 1,
            b')' => {
                depth -= 1;
                if depth == 0 {
                    return &markers[arg_start..index];
                }
            }
            _ => {}
        }
        index += 1;
    }
    &markers[arg_start..]
}

fn is_classification(argument: &str) -> bool {
    argument.contains(CLASSIFICATION_MARKER)
        && CLASSIFICATION_ROOTS
            .iter()
            .any(|root| argument.contains(root))
}

fn has_marker(text: &str, markers: &[&str]) -> bool {
    markers.iter().any(|marker| text.contains(marker))
}

/// A lexed source line, byte-aligned with the original. `code` blanks comment,
/// string, and char-literal spans so a walker token matches only real calls and
/// paren matching ignores literal parens; `markers` blanks comments but keeps
/// string and identifier text so a literal corpus path stays visible.
struct LineView {
    code: String,
    markers: String,
}

impl LineView {
    fn with_capacity(capacity: usize) -> Self {
        Self {
            code: String::with_capacity(capacity),
            markers: String::with_capacity(capacity),
        }
    }

    fn push_code(&mut self, character: char) {
        self.code.push(character);
        self.markers.push(character);
    }

    fn push_literal(&mut self, character: char) {
        blank(&mut self.code, character);
        self.markers.push(character);
    }

    fn push_comment(&mut self, character: char) {
        blank(&mut self.code, character);
        blank(&mut self.markers, character);
    }
}

fn blank(target: &mut String, character: char) {
    for _ in 0..character.len_utf8() {
        target.push(' ');
    }
}

fn is_ident_continue(character: char) -> bool {
    character.is_alphanumeric() || character == '_'
}

/// Lex one line into its code and marker views, carrying block-comment depth.
fn clean_line(line: &str, block_depth: &mut usize) -> LineView {
    let chars: Vec<char> = line.chars().collect();
    let mut view = LineView::with_capacity(line.len());
    let mut index = 0;
    while index < chars.len() {
        index = if *block_depth > 0 {
            consume_block(&chars, index, block_depth, &mut view)
        } else {
            consume_token(&chars, index, block_depth, &mut view)
        };
    }
    view
}

fn consume_block(
    chars: &[char],
    index: usize,
    block_depth: &mut usize,
    view: &mut LineView,
) -> usize {
    if chars[index] == '*' && chars.get(index + 1) == Some(&'/') {
        *block_depth -= 1;
        view.push_comment(chars[index]);
        view.push_comment(chars[index + 1]);
        return index + 2;
    }
    if chars[index] == '/' && chars.get(index + 1) == Some(&'*') {
        *block_depth += 1;
        view.push_comment(chars[index]);
        view.push_comment(chars[index + 1]);
        return index + 2;
    }
    view.push_comment(chars[index]);
    index + 1
}

fn consume_token(
    chars: &[char],
    index: usize,
    block_depth: &mut usize,
    view: &mut LineView,
) -> usize {
    let current = chars[index];
    let next = chars.get(index + 1).copied();
    match (current, next) {
        ('/', Some('/')) => consume_line_comment(chars, index, view),
        ('/', Some('*')) => {
            *block_depth += 1;
            view.push_comment(current);
            view.push_comment('*');
            index + 2
        }
        _ if is_raw_string_start(chars, index) => consume_raw_string(chars, index, view),
        ('"', _) => consume_string(chars, index, view),
        ('\'', _) => consume_char(chars, index, view),
        _ => {
            view.push_code(current);
            index + 1
        }
    }
}

fn consume_line_comment(chars: &[char], start: usize, view: &mut LineView) -> usize {
    for &character in &chars[start..] {
        view.push_comment(character);
    }
    chars.len()
}

fn consume_string(chars: &[char], start: usize, view: &mut LineView) -> usize {
    view.push_literal(chars[start]);
    let mut index = start + 1;
    while index < chars.len() {
        let character = chars[index];
        if character == '\\' {
            view.push_literal(character);
            if let Some(&escaped) = chars.get(index + 1) {
                view.push_literal(escaped);
                index += 2;
                continue;
            }
            return index + 1;
        }
        view.push_literal(character);
        index += 1;
        if character == '"' {
            return index;
        }
    }
    index
}

fn consume_char(chars: &[char], start: usize, view: &mut LineView) -> usize {
    // A simple char literal `'x'` (covers `'"'`), keeping any interior quote out
    // of string state.
    if chars.get(start + 1) != Some(&'\\') && chars.get(start + 2) == Some(&'\'') {
        for &character in &chars[start..start + 3] {
            view.push_literal(character);
        }
        return start + 3;
    }
    // An escaped char literal `'\n'`, `'\''`, `'\u{1F}'`.
    if chars.get(start + 1) == Some(&'\\') {
        let mut index = start + 2;
        while index < chars.len() && chars[index] != '\'' {
            index += 1;
        }
        if index < chars.len() {
            for &character in &chars[start..=index] {
                view.push_literal(character);
            }
            return index + 1;
        }
    }
    // A lifetime (`'a`) or stray apostrophe: emit as code and move on.
    view.push_code(chars[start]);
    start + 1
}

fn is_raw_string_start(chars: &[char], index: usize) -> bool {
    if index > 0 && is_ident_continue(chars[index - 1]) {
        return false;
    }
    let mut cursor = index;
    if chars.get(cursor) == Some(&'b') {
        cursor += 1;
    }
    if chars.get(cursor) != Some(&'r') {
        return false;
    }
    cursor += 1;
    while chars.get(cursor) == Some(&'#') {
        cursor += 1;
    }
    chars.get(cursor) == Some(&'"')
}

fn consume_raw_string(chars: &[char], start: usize, view: &mut LineView) -> usize {
    let mut index = start;
    if chars[index] == 'b' {
        view.push_literal(chars[index]);
        index += 1;
    }
    view.push_literal(chars[index]); // 'r'
    index += 1;
    let mut hashes = 0usize;
    while chars.get(index) == Some(&'#') {
        view.push_literal(chars[index]);
        index += 1;
        hashes += 1;
    }
    if chars.get(index) == Some(&'"') {
        view.push_literal(chars[index]);
        index += 1;
    }
    while index < chars.len() {
        if chars[index] == '"' && raw_closes(chars, index + 1, hashes) {
            view.push_literal(chars[index]);
            index += 1;
            for _ in 0..hashes {
                view.push_literal(chars[index]);
                index += 1;
            }
            return index;
        }
        view.push_literal(chars[index]);
        index += 1;
    }
    index
}

fn raw_closes(chars: &[char], from: usize, hashes: usize) -> bool {
    (0..hashes).all(|offset| chars.get(from + offset) == Some(&'#'))
}

crate::register_rule!(METADATA, RULE);

#[cfg(test)]
mod tests {
    use super::{Detection, LineView, classify, clean_line, walker_regex};

    fn lex(line: &str) -> LineView {
        let mut depth = 0usize;
        clean_line(line, &mut depth)
    }

    fn classify_line(line: &str) -> Option<Detection> {
        let walker = walker_regex().expect("walker regex");
        classify(&lex(line), &walker)
    }

    #[test]
    fn classifies_each_walker_family_over_corpus_arguments() {
        assert_eq!(
            classify_line("let e = std::fs::read_dir(log_root)?;"),
            Some(Detection::ReadDir)
        );
        assert_eq!(
            classify_line("for p in glob::glob(log_base)? {"),
            Some(Detection::Glob)
        );
        assert_eq!(
            classify_line("let w = WalkDir::new(impl_root);"),
            Some(Detection::Walk)
        );
        assert_eq!(
            classify_line("read_dir(\"larch-logs/run\")"),
            Some(Detection::ReadDir)
        );
    }

    #[test]
    fn ignores_session_roots_and_non_corpus_arguments() {
        assert_eq!(classify_line("read_dir(session_tmpdir)"), None);
        // A corpus marker paired with a session marker in the argument is a
        // session read.
        assert_eq!(classify_line("read_dir(log_root_tmpdir)"), None);
        assert_eq!(classify_line("read_dir(some_local_dir)"), None);
        // A bare mention that is not a call is never flagged.
        assert_eq!(classify_line("let handler = read_dir_for(log_root);"), None);
    }

    #[test]
    fn classification_globs_require_a_corpus_root_segment() {
        assert_eq!(
            classify_line("glob(\"design/x/plan-review/round-1/findings-classification.tsv\")"),
            Some(Detection::Classification)
        );
        // The classification token alone, without a design/implement/review
        // root, is not a classification glob.
        assert_ne!(
            classify_line("glob(log_root_findings_classification)"),
            Some(Detection::Classification)
        );
    }

    #[test]
    fn walker_token_inside_a_string_literal_is_not_a_call() {
        // 2a: a walker token quoted inside a log or error string is data.
        assert_eq!(
            classify_line("return Err(format!(\"failed read_dir(log_root): {e}\"));"),
            None
        );
    }

    #[test]
    fn corpus_marker_does_not_bleed_from_an_adjacent_statement() {
        // 2b: the marker on a following statement is outside the call argument.
        assert_eq!(
            classify_line("let _ = std::fs::read_dir(scratch); let _k = log_root;"),
            None
        );
    }

    #[test]
    fn nested_block_comment_hides_an_inner_walker() {
        // 2c: Rust block comments nest.
        let mut depth = 0usize;
        let view = clean_line("/* outer /* inner */ read_dir(log_root); */", &mut depth);
        let walker = walker_regex().expect("walker regex");
        assert_eq!(classify(&view, &walker), None);
        assert_eq!(depth, 0);
    }

    #[test]
    fn char_literal_quote_does_not_open_a_string() {
        // 2d: `'"'` must not swallow the following real comment.
        assert_eq!(
            classify_line("let _q = '\"'; // read_dir(log_root) note"),
            None
        );
    }

    #[test]
    fn literal_corpus_path_argument_is_still_detected() {
        // A real call over a literal corpus path survives lexing.
        assert_eq!(
            classify_line("let _ = std::fs::read_dir(\"larch-logs/x\");"),
            Some(Detection::ReadDir)
        );
    }

    #[test]
    fn raw_string_argument_is_preserved_for_markers() {
        assert_eq!(
            classify_line("let _ = glob::glob(r\"larch-logs/**\");"),
            Some(Detection::Glob)
        );
        // A walker token inside a raw string is data, not a call.
        assert_eq!(classify_line("let _m = r#\"read_dir(log_root)\"#;"), None);
    }
}
