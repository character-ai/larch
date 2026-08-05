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

use std::collections::BTreeSet;

use regex::Regex;
use tree_sitter::Node;

use crate::suppression;
use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::parse_python,
};

const NAME: &str = "run-log-corpus-walkers";
const DESCRIPTION: &str = "Reject raw committed run-log corpus walkers outside the shared owner";
const RUST_SCOPE_INCLUDE: &str = "crates/*/src/**/*.rs";
const LINTER_CRATE_EXCLUDE: &str = "crates/larch-lint/**";
const OWNER_SUFFIX: &str = "report/run_log_corpus.rs";
const PYTHON_SCOPE_INCLUDES: [&str; 3] = [
    "python/**/*.py",
    "skills/fluff-analysis/scripts/fluff-analysis.py",
    "skills/voter-calibration/scripts/voter-calibration.py",
];
const PYTHON_OWNER: &str = "python/larch/report/run_log_corpus.py";
const PYTHON_EXEMPTIONS: [&str; 3] = [
    "python/larch/report/retro_fix_cursor.py",
    "python/larch/report/retro_v3_sweep.py",
    "python/larch/report/cleanup_implement_logs.py",
];
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
        let rust = PathSelector::new(&[RUST_SCOPE_INCLUDE], &[LINTER_CRATE_EXCLUDE])?;
        let python = PathSelector::new(&PYTHON_SCOPE_INCLUDES, &[])?;
        let mut findings = Vec::new();
        for path in rust.select(repository) {
            if is_owner(path) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            findings.extend(scan_source(path.as_str(), &source, &walker)?);
        }
        for path in python.select(repository) {
            if is_python_owner_or_exempt(path) || is_excluded_python_path(path.as_str()) {
                continue;
            }
            findings.extend(scan_python_source(path.as_str(), &repository.read_utf8(path)?)?);
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn is_owner(path: &RepoPath) -> bool {
    path.as_str().ends_with(OWNER_SUFFIX)
}

fn is_python_owner_or_exempt(path: &RepoPath) -> bool {
    path.as_str() == PYTHON_OWNER || PYTHON_EXEMPTIONS.contains(&path.as_str())
}

fn is_excluded_python_path(path: &str) -> bool {
    let parts: Vec<_> = path.split('/').collect();
    parts.iter().any(|part| {
        matches!(
            *part,
            ".git" | "node_modules" | ".venv" | ".agents" | "__pycache__" | "larch-logs" | "tests" | "test"
        )
    }) || path
        .rsplit('/')
        .next()
        .is_some_and(|name| name.starts_with("test_") || name.ends_with("_test.py"))
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

fn scan_python_source(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let tree = parse_python(source)?;
    let mut symbols = PythonWalkerSymbols::default();
    let mut detections = BTreeSet::new();
    collect_python_walkers(tree.root_node(), source, &mut symbols, &mut detections);
    detections
        .into_iter()
        .map(|(line, detection)| {
            if suppression::reason(source.lines().nth(line.saturating_sub(1)).unwrap_or(""), SUPPRESSION_TOKEN)?.is_some() {
                return Ok(None);
            }
            let line = u32::try_from(line)
                .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
            Ok(Some(Finding::new(path, line, detection.message())))
        })
        .filter_map(Result::transpose)
        .collect()
}

#[derive(Default)]
struct PythonWalkerSymbols {
    corpus_aliases: BTreeSet<String>,
    safe_run_aliases: BTreeSet<String>,
}

fn python_target_names(node: Node<'_>, source: &str) -> Vec<String> {
    if node.kind() == "identifier" {
        return vec![node_text(node, source).trim().to_owned()];
    }
    let mut names = Vec::new();
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        names.extend(python_target_names(child, source));
    }
    names
}

fn python_expression_is_safe_run(node: Node<'_>, source: &str, symbols: &PythonWalkerSymbols) -> bool {
    if node.kind() == "identifier" {
        return symbols.safe_run_aliases.contains(node_text(node, source).trim());
    }
    if node.kind() != "call" {
        return false;
    }
    let Some(function) = node.child_by_field_name("function") else {
        return false;
    };
    if !matches!(node_text(function, source).trim(), "str" | "Path") {
        return false;
    }
    first_python_argument(node).is_some_and(|argument| python_expression_is_safe_run(argument, source, symbols))
}

fn python_expression_is_corpus(node: Node<'_>, source: &str, symbols: &PythonWalkerSymbols) -> bool {
    let text = node_text(node, source);
    if has_marker(text, &SESSION_MARKERS) {
        return false;
    }
    if has_marker(text, &CORPUS_MARKERS) {
        return true;
    }
    match node.kind() {
        "identifier" => symbols.corpus_aliases.contains(text.trim()),
        "binary_operator" => node
            .child_by_field_name("left")
            .is_some_and(|left| python_expression_is_corpus(left, source, symbols)),
        "call" => node
            .child_by_field_name("function")
            .filter(|function| function.kind() == "attribute")
            .and_then(|function| function.child_by_field_name("object"))
            .is_some_and(|receiver| python_expression_is_corpus(receiver, source, symbols)),
        _ => false,
    }
}

fn collect_python_walkers(
    node: Node<'_>,
    source: &str,
    symbols: &mut PythonWalkerSymbols,
    detections: &mut BTreeSet<(usize, Detection)>,
) {
    if node.kind() == "for_statement" {
        record_python_safe_run_loop(node, source, symbols);
    }
    if node.kind() == "call"
        && let Some(detection) = python_walker_detection(node, source, symbols)
    {
        detections.insert((node.start_position().row + 1, detection));
    }
    if node.kind() == "for_statement" && is_python_dual_manifest_loop(node, source) {
        detections.insert((node.start_position().row + 1, Detection::DualManifest));
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_walkers(child, source, symbols, detections);
    }
    if node.kind() == "assignment" {
        record_python_assignment(node, source, symbols);
    }
}

fn record_python_assignment(node: Node<'_>, source: &str, symbols: &mut PythonWalkerSymbols) {
    let Some(left) = node.child_by_field_name("left") else {
        return;
    };
    let Some(right) = node.child_by_field_name("right") else {
        return;
    };
    let names = python_target_names(left, source);
    if python_expression_is_safe_run(right, source, symbols) {
        for name in names {
            symbols.safe_run_aliases.insert(name.clone());
            symbols.corpus_aliases.remove(&name);
        }
    } else if python_expression_is_corpus(right, source, symbols) {
        for name in names {
            if !symbols.safe_run_aliases.contains(&name) {
                symbols.corpus_aliases.insert(name);
            }
        }
    }
}

fn record_python_safe_run_loop(
    node: Node<'_>,
    source: &str,
    symbols: &mut PythonWalkerSymbols,
) {
    let Some(iterable) = node.child_by_field_name("right") else {
        return;
    };
    let Some(function) = iterable
        .child_by_field_name("function")
        .filter(|_| iterable.kind() == "call")
    else {
        return;
    };
    if node_text(function, source).trim() != "safe_child_run_dirs" {
        return;
    }
    let Some(target) = node.child_by_field_name("left") else {
        return;
    };
    for name in python_target_names(target, source) {
        symbols.safe_run_aliases.insert(name.clone());
        symbols.corpus_aliases.remove(&name);
    }
}

fn python_walker_detection(
    call: Node<'_>,
    source: &str,
    symbols: &PythonWalkerSymbols,
) -> Option<Detection> {
    let function = call.child_by_field_name("function")?;
    let function_text = node_text(function, source).trim();
    let name = function_text.rsplit('.').next()?;
    if !matches!(name, "glob" | "rglob" | "iglob" | "walk" | "scandir") {
        return None;
    }
    let argument = first_python_argument(call)?;
    let argument_text = node_text(argument, source);
    if matches!(name, "glob" | "rglob" | "iglob")
        && python_constant_string(argument, source).is_some_and(is_python_classification_glob)
    {
        return Some(Detection::Classification);
    }
    let receiver = function_text.rsplit_once('.').map(|(receiver, _)| receiver);
    let stdlib_glob = receiver == Some("glob");
    let corpus_receiver = function
        .child_by_field_name("object")
        .is_some_and(|receiver| python_expression_is_corpus(receiver, source, symbols));
    let corpus_argument = python_expression_is_corpus(argument, source, symbols);
    match name {
        "rglob" if corpus_receiver => Some(Detection::Glob),
        "glob" | "iglob"
            if (stdlib_glob && corpus_argument)
                || (corpus_receiver && python_glob_looks_like_corpus(argument_text)) =>
        {
            Some(Detection::Glob)
        }
        "walk" if (receiver == Some("os") || corpus_receiver) && corpus_argument => {
            Some(Detection::Walk)
        }
        "scandir" if corpus_argument => Some(Detection::ReadDir),
        _ => None,
    }
}

fn first_python_argument(call: Node<'_>) -> Option<Node<'_>> {
    let arguments = call.child_by_field_name("arguments")?;
    let mut cursor = arguments.walk();
    arguments
        .named_children(&mut cursor)
        .find(|argument| argument.kind() != "keyword_argument")
}

fn is_python_classification_glob(argument: &str) -> bool {
    argument.contains(CLASSIFICATION_MARKER)
        && CLASSIFICATION_ROOTS
            .iter()
            .any(|root| argument.contains(root))
}

fn python_glob_looks_like_corpus(argument: &str) -> bool {
    let trimmed = argument.trim().trim_matches(['\"', '\'']);
    trimmed == "*"
        || trimmed == "**"
        || trimmed.starts_with("*/")
        || argument.contains("larch-logs")
        || CLASSIFICATION_ROOTS.iter().any(|root| argument.contains(root))
}

fn is_python_dual_manifest_loop(node: Node<'_>, source: &str) -> bool {
    let Some(iterable) = node.child_by_field_name("right") else {
        return false;
    };
    python_manifest_iterable(iterable, source)
        && contains_python_manifest(node, source, "manifest.json")
        && contains_python_manifest(node, source, "run-manifest.json")
}

fn python_manifest_iterable(node: Node<'_>, source: &str) -> bool {
    match node.kind() {
        "list" | "tuple" => contains_python_manifest(node, source, "manifest.json")
            || contains_python_manifest(node, source, "run-manifest.json"),
        "call" => {
            let Some(function) = node.child_by_field_name("function") else {
                return false;
            };
            if !matches!(node_text(function, source).trim(), "list" | "tuple") {
                return false;
            }
            first_python_argument(node)
                .is_some_and(|argument| python_manifest_iterable(argument, source))
        }
        _ => false,
    }
}

fn contains_python_manifest(node: Node<'_>, source: &str, expected: &str) -> bool {
    if python_constant_string(node, source) == Some(expected) {
        return true;
    }
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .any(|child| contains_python_manifest(child, source, expected))
}

fn python_constant_string<'source>(node: Node<'_>, source: &'source str) -> Option<&'source str> {
    if node.kind() != "string" {
        return None;
    }
    let raw = node_text(node, source).trim();
    if matches!(raw.as_bytes().first(), Some(b'f' | b'F')) {
        return None;
    }
    let stripped = raw.trim_start_matches(['r', 'R', 'b', 'B']);
    let quote = stripped
        .chars()
        .next()
        .filter(|quote| matches!(quote, '\"' | '\''))?;
    stripped
        .strip_prefix(quote)
        .and_then(|value| value.strip_suffix(quote))
}

fn node_text<'source>(node: Node<'_>, source: &'source str) -> &'source str {
    source.get(node.byte_range()).unwrap_or("")
}

/// A classified corpus-walker violation and its remediation family.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum Detection {
    Classification,
    Walk,
    Glob,
    ReadDir,
    DualManifest,
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
            Self::DualManifest => {
                "dual-manifest candidate loop outside run_log_corpus: use its metadata helpers".to_owned()
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
