//! Reject ad-hoc `KEY=value` readers and emitters outside shared owners.
//!
//! # Crate survey (issue #7617)
//!
//! | Need | Candidates | Selection |
//! |------|------------|-----------|
//! | Rust syntax | workspace `syn`, `ra_ap_syntax` | Use `syn` visitors already established by #7604 for call-shape detection. Line numbers come from the source text (no `proc-macro2` `span-locations` feature; leaves must not add workspace dependencies). Custom code encodes only owner paths and prohibited shapes. |
//! | Shell line shapes | workspace `regex`, `tree-sitter-bash` | Reuse the workspace regex crate for the three retained line-oriented shell reader shapes. A full shell parser would not improve this narrow compatibility ratchet and would diverge from its existing line contract. |
//! | Serialization / baselines | workspace `serde`/`toml` | Not required: the Rust corpus starts at zero findings, so no grandfathering baseline ships. |
//!
//! No workspace `Cargo.toml` dependency is added (umbrella concurrency contract).

use std::{collections::BTreeSet, path::Path, sync::LazyLock};

use regex::Regex;
use tree_sitter::Node;

use syn::{
    Expr, ExprForLoop, ExprMethodCall, ItemFn, Member,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::parse_python,
};

use super::path_discovery;

const NAME: &str = "kv-codec";
const DESCRIPTION: &str =
    "Reject ad-hoc KEY=value readers and emitters outside shared codec owners";

/// Future-state reader owners (Rust equivalents of `larch.io` / `env_file`).
const READER_OWNERS: &[&str] = &[
    "crates/larch-io/src/lib.rs",
    "crates/larch-io/src/env_file.rs",
    "crates/larch-core/src/env_file.rs",
];

/// Future-state emitter owner (Rust equivalent of `logging_util.emit_kv`).
const EMITTER_OWNER: &str = "crates/larch-core/src/logging_util.rs";

/// Modules where ad-hoc `print!`/`println!` KEY=value wrappers are also gated.
const EMITTER_GUARDED_PREFIXES: &[&str] = &["crates/larch-issue/"];

/// Compatibility reader owners retained until their runtime surfaces move.
const PYTHON_READER_OWNERS: &[&str] = &[
    "python/larch/io.py",
    "python/larch/core/env_file.py",
];
const PYTHON_EMITTER_OWNER: &str = "python/larch/core/logging_util.py";
const PYTHON_EMITTER_GUARDED: &[&str] = &[
    "python/larch/issue/issue_create.py",
    "python/larch/issue/execution_issues.py",
];

const OPTION_ITER_NAMES: &[&str] = &["args", "argv", "options", "tokens"];
const OPTION_BINDING_NAMES: &[&str] = &["arg", "token", "opt", "option", "argv_item"];

static AWK_FIELD_DELIMITER: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"-F\s*(?:=|['\"]=['\"]?)"#).expect("awk delimiter expression"));
static CUT_FIELD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)-f\s*\d").expect("cut field expression"));
static CUT_DELIMITER: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"-d\s*(?:=|['\"]=['\"]?)"#).expect("cut delimiter expression"));
static GREP_KEY_PREFIX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"[\"']\^[A-Za-z_${][^\"']*=[^\"']*[\"']"#)
        .expect("grep key-prefix expression")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/kv-codec.toml",
);

#[derive(Debug)]
pub struct KvCodecRule;

pub static RULE: KvCodecRule = KvCodecRule;

impl Rule for KvCodecRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let rust = PathSelector::new(&["crates/**/*.rs"], &[])?;
        let shell = PathSelector::new(&["scripts/**/*.sh", "skills/**/*.sh"], &[])?;
        let python = PathSelector::new(&["python/larch/**/*.py"], &[])?;
        let mut findings = Vec::new();
        for path in rust.select(repository) {
            findings.extend(check_rust_file(repository, path)?);
        }
        for path in shell.select(repository) {
            findings.extend(check_shell_file(repository, path)?);
        }
        for path in python.select(repository) {
            findings.extend(check_python_file(repository, path)?);
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum ViolationKind {
    Split,
    EmitterDef,
    PrintWrapper,
}

impl ViolationKind {
    const fn message(self) -> &'static str {
        match self {
            Self::Split => "ad-hoc KEY=value split; use the shared KV codec owner",
            Self::EmitterDef => "ad-hoc KEY=value emitter; use the shared emit_kv owner",
            Self::PrintWrapper => {
                "ad-hoc KEY=value print wrapper; use the shared emit_kv owner"
            }
        }
    }
}

fn check_rust_file(repository: &Repository, path: &RepoPath) -> Result<Vec<Finding>, LintError> {
    let (source, syntax) = path_discovery::read_rust_syntax(repository, path)?;
    let mut visitor = KvCodecVisitor {
        reader_owner: is_reader_owner(path.as_str()),
        emitter_owner: path.as_str() == EMITTER_OWNER,
        emitter_guarded: is_emitter_guarded(path.as_str()),
        option_loop_depth: 0,
        pending: Vec::new(),
    };
    visitor.visit_file(syntax.file());
    Ok(resolve_findings(path.as_str(), &source, &visitor.pending))
}

fn check_shell_file(repository: &Repository, path: &RepoPath) -> Result<Vec<Finding>, LintError> {
    if Path::new(path.as_str())
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.starts_with("test-"))
    {
        return Ok(Vec::new());
    }
    let source = repository.read_utf8(path)?;
    let findings = source
        .lines()
        .enumerate()
        .filter(|(_, line)| shell_reader(line))
        .map(|(index, _)| {
            let line = u32::try_from(index + 1).unwrap_or(1);
            Finding::new(
                path.as_str(),
                line,
                "ad-hoc shell KEY=value reader; use scripts/larch.sh kv get",
            )
        })
        .collect();
    Ok(findings)
}

fn check_python_file(repository: &Repository, path: &RepoPath) -> Result<Vec<Finding>, LintError> {
    let source = repository.read_utf8(path)?;
    let tree = parse_python(&source)?;
    let mut pending = BTreeSet::new();
    collect_python_findings(
        tree.root_node(),
        &source,
        !PYTHON_READER_OWNERS.contains(&path.as_str()),
        path.as_str() != PYTHON_EMITTER_OWNER,
        PYTHON_EMITTER_GUARDED.contains(&path.as_str()) && path.as_str() != PYTHON_EMITTER_OWNER,
        &mut pending,
    );
    Ok(pending
        .into_iter()
        .map(|(line, kind)| {
            Finding::new(
                path.as_str(),
                u32::try_from(line).unwrap_or(u32::MAX),
                kind.message(),
            )
        })
        .collect())
}

fn collect_python_findings(
    node: Node<'_>,
    source: &str,
    scan_readers: bool,
    scan_emitter_definition: bool,
    emitter_guarded: bool,
    pending: &mut BTreeSet<(usize, ViolationKind)>,
) {
    collect_python_findings_inner(
        node,
        source,
        scan_readers,
        scan_emitter_definition,
        emitter_guarded,
        false,
        pending,
    );
}

fn collect_python_findings_inner(
    node: Node<'_>,
    source: &str,
    scan_readers: bool,
    scan_emitter_definition: bool,
    emitter_guarded: bool,
    within_reader_loop: bool,
    pending: &mut BTreeSet<(usize, ViolationKind)>,
) {
    if scan_emitter_definition
        && node.kind() == "function_definition"
        && node
            .child_by_field_name("name")
            .is_some_and(|name| node_text(name, source) == "emit_kv")
    {
        pending.insert((node.start_position().row + 1, ViolationKind::EmitterDef));
    }
    if node.kind() == "call" {
        if scan_readers && within_reader_loop && python_is_equals_split(node, source) {
            pending.insert((node.start_position().row + 1, ViolationKind::Split));
        }
        if emitter_guarded && python_is_kv_print(node, source) {
            pending.insert((node.start_position().row + 1, ViolationKind::PrintWrapper));
        }
    }
    let loop_scope = within_reader_loop || python_is_reader_loop(node, source);
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_findings_inner(
            child,
            source,
            scan_readers,
            scan_emitter_definition,
            emitter_guarded,
            loop_scope,
            pending,
        );
    }
}

fn python_is_reader_loop(node: Node<'_>, source: &str) -> bool {
    if node.kind() == "for_in_clause" {
        // Python's old AST rule exempted only `for` and `async for` option
        // loops. A comprehension is a reader shape even when one of its
        // clauses happens to iterate an option-looking identifier.
        return true;
    }
    if !matches!(node.kind(), "for_statement" | "async_for_statement") {
        return false;
    }
    let Some(iterable) = node.child_by_field_name("right") else {
        return false;
    };
    if iterable.kind() != "identifier" {
        return true;
    }
    !OPTION_ITER_NAMES.contains(&node_text(iterable, source))
}

fn python_is_equals_split(call: Node<'_>, source: &str) -> bool {
    let Some(function) = call.child_by_field_name("function") else {
        return false;
    };
    if !node_text(function, source).trim_end().ends_with(".split") {
        return false;
    }
    let Some(arguments) = call.child_by_field_name("arguments") else {
        return false;
    };
    let mut cursor = arguments.walk();
    let values: Vec<_> = arguments
        .named_children(&mut cursor)
        .filter(|argument| argument.kind() != "keyword_argument")
        .collect();
    values.len() >= 2
        && python_is_text_equals_string(values[0], source)
        && node_text(values[1], source).trim() == "1"
}

fn python_is_kv_print(call: Node<'_>, source: &str) -> bool {
    let Some(function) = call.child_by_field_name("function") else {
        return false;
    };
    if node_text(function, source).trim() != "print" {
        return false;
    }
    let Some(arguments) = call.child_by_field_name("arguments") else {
        return false;
    };
    let mut cursor = arguments.walk();
    let Some(value) = arguments
        .named_children(&mut cursor)
        .find(|argument| argument.kind() != "keyword_argument")
    else {
        return false;
    };
    let text = node_text(value, source).trim_start();
    if value.kind() != "string" || !matches!(text.as_bytes().first(), Some(b'f' | b'F')) {
        return false;
    }
    let mut cursor = value.walk();
    value
        .named_children(&mut cursor)
        .any(|part| part.kind() == "string_content" && node_text(part, source) == "=")
}

fn python_is_text_equals_string(node: Node<'_>, source: &str) -> bool {
    if node.kind() != "string" {
        return false;
    }
    let raw = node_text(node, source).trim();
    let Some(quote_start) = raw.find(['\"', '\'']) else {
        return false;
    };
    // `ast.Constant(value="=")` accepts ordinary, raw, and unicode strings,
    // but never bytes or formatted strings.
    if !raw[..quote_start]
        .bytes()
        .all(|prefix| matches!(prefix, b'r' | b'R' | b'u' | b'U'))
    {
        return false;
    }
    let quoted = &raw[quote_start..];
    let delimiter = if quoted.starts_with("\"\"\"") {
        "\"\"\""
    } else if quoted.starts_with("'''") {
        "'''"
    } else if quoted.starts_with('\"') {
        "\""
    } else if quoted.starts_with('\'') {
        "'"
    } else {
        return false;
    };
    quoted
        .strip_prefix(delimiter)
        .and_then(|value| value.strip_suffix(delimiter))
        == Some("=")
}

fn node_text<'source>(node: Node<'_>, source: &'source str) -> &'source str {
    source.get(node.byte_range()).unwrap_or("")
}

fn shell_reader(line: &str) -> bool {
    (command_indices(line, "awk").any(|index| {
        let suffix = &line[index + "awk".len()..];
        (suffix.contains("$1") || suffix.contains("index($0)")) && AWK_FIELD_DELIMITER.is_match(suffix)
    })) || (command_indices(line, "cut").any(|index| {
        let suffix = &line[index + "cut".len()..];
        CUT_FIELD.is_match(suffix) && CUT_DELIMITER.is_match(suffix)
    })) || command_indices(line, "grep").any(|index| {
        let suffix = &line[index + "grep".len()..];
        let has_option = suffix
            .chars()
            .next()
            .is_some_and(char::is_whitespace)
            && suffix
                .trim_start_matches(char::is_whitespace)
                .starts_with('-');
        !has_option && GREP_KEY_PREFIX.is_match(suffix)
    })
}

fn command_indices<'line>(line: &'line str, command: &'line str) -> impl Iterator<Item = usize> + 'line {
    line.match_indices(command)
        .filter_map(move |(index, _)| command_boundary(line, index, command.len()).then_some(index))
}

fn command_boundary(line: &str, index: usize, length: usize) -> bool {
    let bytes = line.as_bytes();
    let is_identifier = |byte: u8| byte.is_ascii_alphanumeric() || byte == b'_';
    !index
        .checked_sub(1)
        .and_then(|before| bytes.get(before))
        .is_some_and(|byte| is_identifier(*byte))
        && !bytes
            .get(index + length)
            .is_some_and(|byte| is_identifier(*byte))
}

fn is_reader_owner(path: &str) -> bool {
    READER_OWNERS.contains(&path)
}

fn is_emitter_guarded(path: &str) -> bool {
    EMITTER_GUARDED_PREFIXES
        .iter()
        .any(|prefix| path.starts_with(prefix))
}

struct PendingViolation {
    kind: ViolationKind,
    needles: &'static [&'static str],
}

struct KvCodecVisitor {
    reader_owner: bool,
    emitter_owner: bool,
    emitter_guarded: bool,
    option_loop_depth: usize,
    pending: Vec<PendingViolation>,
}

impl<'ast> Visit<'ast> for KvCodecVisitor {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        if !self.emitter_owner && node.sig.ident == "emit_kv" {
            self.pending.push(PendingViolation {
                kind: ViolationKind::EmitterDef,
                needles: &["fn emit_kv", "fn emit_kv("],
            });
        }
        visit::visit_item_fn(self, node);
    }

    fn visit_expr_for_loop(&mut self, node: &'ast ExprForLoop) {
        let option_loop = is_option_iter_expr(&node.expr);
        if option_loop {
            self.option_loop_depth += 1;
        }
        visit::visit_expr_for_loop(self, node);
        if option_loop {
            self.option_loop_depth -= 1;
        }
    }

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        if !self.reader_owner
            && self.option_loop_depth == 0
            && is_equals_split(node)
            && !is_option_receiver(&node.receiver)
        {
            self.pending.push(PendingViolation {
                kind: ViolationKind::Split,
                needles: split_needles(node),
            });
        }
        if self.emitter_guarded && !self.emitter_owner && is_kv_print_method(node) {
            self.pending.push(PendingViolation {
                kind: ViolationKind::PrintWrapper,
                needles: &[".print(", ".println(", ".write(", ".writeln("],
            });
        }
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_macro(&mut self, node: &'ast syn::ExprMacro) {
        self.maybe_print_macro(node);
        visit::visit_expr_macro(self, node);
    }

    fn visit_stmt_macro(&mut self, node: &'ast syn::StmtMacro) {
        self.maybe_print_macro_path_tokens(&node.mac);
        visit::visit_stmt_macro(self, node);
    }
}

impl KvCodecVisitor {
    fn maybe_print_macro(&mut self, node: &syn::ExprMacro) {
        self.maybe_print_macro_path_tokens(&node.mac);
    }

    fn maybe_print_macro_path_tokens(&mut self, mac: &syn::Macro) {
        if self.emitter_guarded && !self.emitter_owner && is_kv_print_macro(mac) {
            self.pending.push(PendingViolation {
                kind: ViolationKind::PrintWrapper,
                needles: &[
                    "print!(",
                    "println!(",
                    "eprint!(",
                    "eprintln!(",
                    "write!(",
                    "writeln!(",
                ],
            });
        }
    }
}

fn split_needles(call: &ExprMethodCall) -> &'static [&'static str] {
    match call.method.to_string().as_str() {
        "split_once" => &[".split_once('=')", ".split_once(\"=\")"],
        "rsplit_once" => &[".rsplit_once('=')", ".rsplit_once(\"=\")"],
        "splitn" => &[".splitn(2, '=')", ".splitn(2, \"=\")"],
        "rsplitn" => &[".rsplitn(2, '=')", ".rsplitn(2, \"=\")"],
        _ => &[".split_once('=')"],
    }
}

fn resolve_findings(path: &str, source: &str, pending: &[PendingViolation]) -> Vec<Finding> {
    let lines: Vec<(u32, &str)> = source
        .lines()
        .enumerate()
        .map(|(index, line)| (u32::try_from(index + 1).unwrap_or(1), line))
        .collect();
    let mut used_lines = BTreeSet::new();
    let mut findings = Vec::new();
    for item in pending {
        let line = take_line(&lines, &mut used_lines, item.needles, item.kind).unwrap_or(1);
        findings.push(Finding::new(path, line, item.kind.message()));
    }
    findings
}

fn take_line(
    lines: &[(u32, &str)],
    used: &mut BTreeSet<u32>,
    needles: &[&str],
    kind: ViolationKind,
) -> Option<u32> {
    for (number, text) in lines {
        if used.contains(number) {
            continue;
        }
        let matches = match kind {
            ViolationKind::Split => needles.iter().any(|needle| text.contains(needle)),
            ViolationKind::EmitterDef => {
                text.contains("fn emit_kv") && !text.trim_start().starts_with("//")
            }
            ViolationKind::PrintWrapper => {
                needles.iter().any(|needle| text.contains(needle)) && looks_like_kv_format(text)
            }
        };
        if matches && used.insert(*number) {
            return Some(*number);
        }
    }
    None
}

fn is_option_iter_expr(expr: &Expr) -> bool {
    match expr {
        Expr::Path(path) => path
            .path
            .get_ident()
            .is_some_and(|ident| OPTION_ITER_NAMES.contains(&ident.to_string().as_str())),
        Expr::Field(field) => match &field.member {
            Member::Named(ident) => OPTION_ITER_NAMES.contains(&ident.to_string().as_str()),
            Member::Unnamed(_) => false,
        },
        _ => false,
    }
}

fn is_option_receiver(expr: &Expr) -> bool {
    match expr {
        Expr::Path(path) => path
            .path
            .get_ident()
            .is_some_and(|ident| OPTION_BINDING_NAMES.contains(&ident.to_string().as_str())),
        Expr::Reference(reference) => is_option_receiver(&reference.expr),
        Expr::Paren(paren) => is_option_receiver(&paren.expr),
        _ => false,
    }
}

fn is_equals_split(call: &ExprMethodCall) -> bool {
    let method = call.method.to_string();
    match method.as_str() {
        "split_once" | "rsplit_once" => equals_literal(call.args.first()),
        "splitn" | "rsplitn" => {
            is_two_literal(call.args.first()) && equals_literal(call.args.iter().nth(1))
        }
        _ => false,
    }
}

fn equals_literal(expr: Option<&Expr>) -> bool {
    match expr {
        Some(Expr::Lit(lit)) => match &lit.lit {
            syn::Lit::Char(character) => character.value() == '=',
            syn::Lit::Str(string) => string.value() == "=",
            _ => false,
        },
        _ => false,
    }
}

fn is_two_literal(expr: Option<&Expr>) -> bool {
    matches!(expr, Some(Expr::Lit(lit)) if matches!(&lit.lit, syn::Lit::Int(value) if value.base10_digits() == "2"))
}

fn is_kv_print_method(call: &ExprMethodCall) -> bool {
    let method = call.method.to_string();
    if method != "print" && method != "println" && method != "write" && method != "writeln" {
        return false;
    }
    call.args.iter().any(expr_contains_equals_format)
}

fn is_kv_print_macro(mac: &syn::Macro) -> bool {
    let name = mac
        .path
        .segments
        .last()
        .map(|segment| segment.ident.to_string())
        .unwrap_or_default();
    if !matches!(
        name.as_str(),
        "print" | "println" | "eprint" | "eprintln" | "write" | "writeln"
    ) {
        return false;
    }
    looks_like_kv_format(&mac.tokens.to_string())
}

fn looks_like_kv_format(tokens: &str) -> bool {
    let compact: String = tokens.chars().filter(|ch| !ch.is_whitespace()).collect();
    compact.contains("}={")
        || compact.contains("{}={}")
        || compact.contains("\"=\"")
        || compact.contains("{key}={value}")
        || compact.contains("{k}={v}")
}

fn expr_contains_equals_format(expr: &Expr) -> bool {
    match expr {
        Expr::Lit(lit) => match &lit.lit {
            syn::Lit::Str(string) => {
                let value = string.value();
                value.contains('=') && (value.contains('{') || value.contains("{}"))
            }
            _ => false,
        },
        Expr::Reference(reference) => expr_contains_equals_format(&reference.expr),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        EMITTER_OWNER, PYTHON_EMITTER_OWNER, PYTHON_READER_OWNERS, KvCodecRule, READER_OWNERS,
    };
    use crate::{Git, LintError, Repository, Rule};
    use std::path::{Path, PathBuf};

    struct Fixture {
        _temporary: tempfile::TempDir,
        repository: Repository,
    }

    struct FakeGit {
        root: PathBuf,
        stream: Vec<u8>,
    }

    impl Git for FakeGit {
        fn repository_root(&self, _cwd: &Path) -> Result<PathBuf, LintError> {
            Ok(self.root.clone())
        }

        fn tracked_paths(&self, _root: &Path) -> Result<Vec<u8>, LintError> {
            Ok(self.stream.clone())
        }
    }

    fn repository_with(files: &[(&str, &str)]) -> Fixture {
        let temporary = tempfile::tempdir().expect("tempdir");
        let mut stream = Vec::new();
        for (relative, contents) in files {
            let path = temporary.path().join(relative);
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).expect("parents");
            }
            std::fs::write(&path, contents).expect("write");
            stream.extend(relative.as_bytes());
            stream.push(0);
        }
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream,
            },
            temporary.path(),
        )
        .expect("repository");
        Fixture {
            _temporary: temporary,
            repository,
        }
    }

    #[test]
    fn detects_split_once_reader_outside_owner() {
        let fixture = repository_with(&[(
            "crates/larch-example/src/lib.rs",
            "fn parse(rows: &[String]) {\n    for line in rows {\n        let _ = line.split_once('=');\n    }\n}\n",
        )]);
        let findings = KvCodecRule.check(&fixture.repository).expect("check");
        assert_eq!(findings.findings().len(), 1);
        assert!(findings.findings()[0].to_string().contains(":3:"));
        assert!(findings.findings()[0]
            .to_string()
            .contains("ad-hoc KEY=value split"));
    }

    #[test]
    fn ignores_option_loop_and_reader_owner() {
        let option = repository_with(&[(
            "crates/larch-example/src/lib.rs",
            "fn parse(args: &[String]) {\n    for arg in args {\n        let _ = arg.split_once('=');\n    }\n}\n",
        )]);
        assert!(
            KvCodecRule
                .check(&option.repository)
                .expect("check")
                .findings()
                .is_empty()
        );

        let owner = repository_with(&[(
            READER_OWNERS[0],
            "fn parse(rows: &[String]) {\n    for line in rows {\n        let _ = line.split_once('=');\n    }\n}\n",
        )]);
        assert!(
            KvCodecRule
                .check(&owner.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }

    #[test]
    fn detects_splitn_and_private_emit_kv() {
        let fixture = repository_with(&[(
            "crates/larch-issue/src/create.rs",
            "fn emit_kv(key: &str, value: &str) {\n    println!(\"{key}={value}\");\n}\nfn read(line: &str) {\n    let _ = line.splitn(2, '=');\n}\n",
        )]);
        let findings = KvCodecRule.check(&fixture.repository).expect("check");
        let messages: Vec<_> = findings.findings().iter().map(ToString::to_string).collect();
        assert!(
            messages
                .iter()
                .any(|message| message.contains("ad-hoc KEY=value emitter")),
            "{messages:?}"
        );
        assert!(
            messages
                .iter()
                .any(|message| message.contains("ad-hoc KEY=value split")),
            "{messages:?}"
        );
        assert!(
            messages
                .iter()
                .any(|message| message.contains("ad-hoc KEY=value print wrapper")),
            "{messages:?}"
        );
    }

    #[test]
    fn emitter_owner_may_define_emit_kv() {
        let fixture = repository_with(&[(
            EMITTER_OWNER,
            "pub fn emit_kv(key: &str, value: &str) {\n    println!(\"{key}={value}\");\n}\n",
        )]);
        assert!(
            KvCodecRule
                .check(&fixture.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }

    #[test]
    fn ignores_non_equals_splits() {
        let fixture = repository_with(&[(
            "crates/larch-example/src/lib.rs",
            "fn parse(rows: &[String]) {\n    for line in rows {\n        let _ = line.split_once(':');\n        let _ = line.splitn(2, ',');\n    }\n}\n",
        )]);
        assert!(
            KvCodecRule
                .check(&fixture.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }

    #[test]
    fn detects_retained_shell_readers_and_ignores_harnesses() {
        let fixture = repository_with(&[
            (
                "scripts/reader.sh",
                "value=$(awk -F= '$1 == key { print $2 }' file)\ncut -d '=' -f2 values.txt\nvalue=$(grep \"^${key}=\" file)\n",
            ),
            (
                "skills/example/scripts/reader.sh",
                "cut -d= -f2 values.txt\n",
            ),
            (
                "scripts/test-reader.sh",
                "cut -d= -f2 values.txt\n",
            ),
        ]);
        let findings = KvCodecRule.check(&fixture.repository).expect("check");
        let messages: Vec<_> = findings.findings().iter().map(ToString::to_string).collect();
        assert_eq!(messages.len(), 4, "{messages:?}");
        assert!(messages.iter().all(|message| message.contains("shell KEY=value reader")));
        assert!(messages.iter().all(|message| !message.contains("test-reader")));
    }

    #[test]
    fn detects_python_reader_loops_and_guarded_emitters() {
        let fixture = repository_with(&[
            (
                "python/larch/example.py",
                "for line in rows:\n    key, value = line.split('=', 1)\n\
                 for token in args:\n    key, value = token.split('=', 1)\n\
                 pairs = {key: value for line in rows for key, value in [line.split('=', 1)]}\n\
                 option_pairs = {key: value for token in args for key, value in [token.split('=', 1)]}\n\
                 async def async_parse(rows):\n    async for line in rows:\n        key, value = line.split('=', 1)\n",
            ),
            (
                "python/larch/issue/issue_create.py",
                "def emit_kv(key, value):\n    print(f'{key}={value}')\n    print(f'literal=value')\n",
            ),
            (
                PYTHON_READER_OWNERS[0],
                "for line in rows:\n    key, value = line.split('=', 1)\n",
            ),
            (
                PYTHON_EMITTER_OWNER,
                "def emit_kv(key, value):\n    print(f'{key}={value}')\n",
            ),
        ]);
        let findings = KvCodecRule.check(&fixture.repository).expect("check");
        let messages: Vec<_> = findings.findings().iter().map(ToString::to_string).collect();
        assert_eq!(messages.len(), 6, "{messages:?}");
        assert!(messages.iter().filter(|message| message.contains("KEY=value split")).count() == 4);
        assert!(messages.iter().any(|message| message.contains("KEY=value emitter")));
        assert_eq!(
            messages
                .iter()
                .filter(|message| message.contains("KEY=value print wrapper"))
                .count(),
            1
        );
        assert!(messages.iter().all(|message| !message.contains(PYTHON_READER_OWNERS[0])));
        assert!(messages.iter().all(|message| !message.contains(PYTHON_EMITTER_OWNER)));
    }
}
