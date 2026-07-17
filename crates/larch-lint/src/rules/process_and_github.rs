//! Enforce the Rust process and GitHub-command ownership seams.

use std::collections::{BTreeMap, BTreeSet};

use regex::Regex;
use syn::{Expr, ExprCall, ExprLit, ItemUse, Lit, UseTree, visit::Visit};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata,
    suppression,
    syntax::RustSyntax,
};

const PROCESS_NAME: &str = "subprocess-via-runner";
const PROCESS_DESCRIPTION: &str = "Require std::process::Command ownership by the shared runner";
const GITHUB_NAME: &str = "gh-argv-literal";
const GITHUB_DESCRIPTION: &str = "Require raw gh command ownership by the GitHub wrapper";
const PROCESS_OWNER: &str = "crates/larch-lint/src/repository.rs";
const GITHUB_OWNER: &str = "crates/larch-lint/src/git/gh.rs";
const RUST_SOURCE: &[&str] = &[
    "crates/larch-lint/src/*.rs",
    "crates/larch-lint/src/**/*.rs",
];
const ALL_RUST_SOURCE: &[&str] = &[
    "crates/larch-lint/*.rs",
    "crates/larch-lint/**/*.rs",
];

pub static PROCESS_METADATA: RuleMetadata = RuleMetadata::new(
    PROCESS_NAME,
    PROCESS_DESCRIPTION,
    "crates/larch-lint/migration-ledger/subprocess-via-runner.toml",
);
pub static GITHUB_METADATA: RuleMetadata = RuleMetadata::new(
    GITHUB_NAME,
    GITHUB_DESCRIPTION,
    "crates/larch-lint/migration-ledger/gh-argv-literal.toml",
);

#[derive(Debug)]
pub struct ProcessRule;

pub static PROCESS_RULE: ProcessRule = ProcessRule;

#[derive(Debug)]
pub struct GitHubRule;

pub static GITHUB_RULE: GitHubRule = GitHubRule;

crate::register_rule!(PROCESS_METADATA, PROCESS_RULE);
crate::register_rule!(GITHUB_METADATA, GITHUB_RULE);

impl Rule for ProcessRule {
    fn name(&self) -> &'static str {
        PROCESS_NAME
    }

    fn description(&self) -> &'static str {
        PROCESS_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<Vec<Finding>, LintError> {
        check_repository(
            repository,
            RUST_SOURCE,
            PROCESS_NAME,
            PROCESS_OWNER,
            FindingKind::Process,
        )
    }
}

impl Rule for GitHubRule {
    fn name(&self) -> &'static str {
        GITHUB_NAME
    }

    fn description(&self) -> &'static str {
        GITHUB_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<Vec<Finding>, LintError> {
        check_repository(
            repository,
            ALL_RUST_SOURCE,
            GITHUB_NAME,
            GITHUB_OWNER,
            FindingKind::GitHub,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FindingKind {
    Process,
    GitHub,
}

impl FindingKind {
    const fn message(self) -> &'static str {
        match self {
            Self::Process => "calls std::process::Command::new; route through the shared runner",
            Self::GitHub => "constructs a raw gh command; use the GitHub wrapper",
        }
    }

    fn matches(self, call: &DetectedCall) -> bool {
        match self {
            Self::Process => true,
            Self::GitHub => call.program.as_deref() == Some("gh"),
        }
    }
}

fn check_repository(
    repository: &Repository,
    includes: &[&str],
    token: &str,
    owner: &str,
    kind: FindingKind,
) -> Result<Vec<Finding>, LintError> {
    let selector = PathSelector::new(includes, &[])?;
    let suppression_token = format!("lint-{token}");
    let mut findings = Vec::new();
    for path in selector.select(repository) {
        if path.as_str() == owner {
            continue;
        }
        let source = repository.read_utf8(path)?;
        for call in calls_from_source(&source, path.as_str())? {
            if !kind.matches(&call) {
                continue;
            }
            let line = line_for_call(&source, &call)?;
            if suppression::reason(line, &suppression_token)?.is_some() {
                continue;
            }
            findings.push(Finding::new(path.as_str(), call.line, kind.message()));
        }
    }
    Ok(findings)
}

fn line_for_call<'source>(source: &'source str, call: &DetectedCall) -> Result<&'source str, LintError> {
    let line = source
        .lines()
        .nth(usize::try_from(call.line.saturating_sub(1)).map_err(|_| {
            LintError::new(format!("{}: line number exceeds usize", call.path))
        })?)
        .ok_or_else(|| LintError::new(format!("{}: call line is missing", call.path)))?;
    Ok(line)
}

fn calls_from_source(source: &str, path: &str) -> Result<Vec<DetectedCall>, LintError> {
    let syntax = RustSyntax::parse(path, source)?;
    let mut visitor = CommandVisitor::default();
    // Module imports are visible regardless of their textual order. Collect
    // them before scanning calls so a later `use` cannot hide a constructor.
    visitor.visit_file(syntax.file());
    visitor.calls.clear();
    visitor.visit_file(syntax.file());
    for call in &mut visitor.calls {
        path.clone_into(&mut call.path);
    }
    visitor.assign_lines(source, path)?;
    Ok(visitor.calls)
}

#[derive(Debug)]
struct DetectedCall {
    path: String,
    spelling: String,
    occurrence: usize,
    program: Option<String>,
    line: u32,
}

#[derive(Default)]
struct CommandVisitor {
    command_aliases: BTreeSet<String>,
    process_aliases: BTreeSet<String>,
    calls: Vec<DetectedCall>,
}

impl CommandVisitor {
    fn collect_use(&mut self, tree: &UseTree, prefix: &[String]) {
        match tree {
            UseTree::Path(path) => {
                let mut next = prefix.to_vec();
                next.push(path.ident.to_string());
                self.collect_use(&path.tree, &next);
            }
            UseTree::Name(name) => self.record_import(prefix, &name.ident.to_string(), &name.ident.to_string()),
            UseTree::Rename(rename) => {
                let imported = rename.ident.to_string();
                self.record_import(prefix, &imported, &rename.rename.to_string());
            }
            UseTree::Glob(_) if prefix == ["std", "process"] => {
                self.command_aliases.insert("Command".to_owned());
            }
            UseTree::Group(group) => {
                for tree in &group.items {
                    self.collect_use(tree, prefix);
                }
            }
            UseTree::Glob(_) => {}
        }
    }

    fn record_import(&mut self, prefix: &[String], imported: &str, local: &str) {
        let mut full = prefix.to_vec();
        if imported != "self" {
            full.push(imported.to_owned());
        }
        if full == ["std", "process", "Command"] {
            self.command_aliases.insert(local.to_owned());
        }
        if full == ["std", "process"] {
            self.process_aliases.insert(local.to_owned());
        }
    }

    fn is_command_constructor(&self, call: &ExprCall) -> Option<String> {
        let Expr::Path(function) = &*call.func else {
            return None;
        };
        let segments: Vec<String> = function
            .path
            .segments
            .iter()
            .map(|segment| segment.ident.to_string())
            .collect();
        let constructor = segments.last().is_some_and(|segment| segment == "new");
        if !constructor {
            return None;
        }
        let prefix = &segments[..segments.len().saturating_sub(1)];
        let standard_path = prefix == ["std", "process", "Command"];
        let command_alias = prefix.len() == 1 && self.command_aliases.contains(&prefix[0]);
        let process_alias = prefix.len() == 2
            && prefix[1] == "Command"
            && self.process_aliases.contains(&prefix[0]);
        (standard_path || command_alias || process_alias).then(|| segments.join("::"))
    }

    fn assign_lines(&mut self, source: &str, path: &str) -> Result<(), LintError> {
        let mut occurrences = BTreeMap::<String, usize>::new();
        for call in &mut self.calls {
            let occurrence = occurrences.entry(call.spelling.clone()).or_default();
            *occurrence += 1;
            call.occurrence = *occurrence;
            call.line = source_line(source, &call.spelling, call.occurrence).ok_or_else(|| {
                LintError::new(format!(
                    "{path}: cannot locate parsed std::process::Command constructor"
                ))
            })?;
        }
        Ok(())
    }
}

impl<'ast> Visit<'ast> for CommandVisitor {
    fn visit_item_use(&mut self, item: &'ast ItemUse) {
        self.collect_use(&item.tree, &[]);
        syn::visit::visit_item_use(self, item);
    }

    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if let Some(spelling) = self.is_command_constructor(call) {
            let program = call.args.first().and_then(string_literal);
            self.calls.push(DetectedCall {
                path: String::new(),
                spelling,
                occurrence: 0,
                program,
                line: 0,
            });
        }
        syn::visit::visit_expr_call(self, call);
    }
}

fn string_literal(expression: &Expr) -> Option<String> {
    let Expr::Lit(ExprLit { lit: Lit::Str(value), .. }) = expression else {
        return None;
    };
    Some(value.value())
}

fn source_line(source: &str, spelling: &str, occurrence: usize) -> Option<u32> {
    let path = spelling
        .strip_suffix("::new")?
        .split("::")
        .map(regex::escape)
        .collect::<Vec<_>>()
        .join(r"\s*::\s*");
    let expression = format!(r"\b{path}\s*::\s*new\s*\(");
    let matcher = Regex::new(&expression).ok()?;
    let executable = mask_comments_and_strings(source);
    let offset = matcher
        .find_iter(&executable)
        .nth(occurrence.checked_sub(1)?)?
        .start();
    u32::try_from(source[..offset].bytes().filter(|byte| *byte == b'\n').count() + 1).ok()
}

fn mask_comments_and_strings(source: &str) -> String {
    let bytes = source.as_bytes();
    let mut masked = bytes.to_vec();
    let mut index = 0;
    while index < bytes.len() {
        let end = match bytes.get(index..index + 2) {
            Some(b"//") => Some(line_comment_end(bytes, index)),
            Some(b"/*") => block_comment_end(bytes, index),
            Some(b"b\"") => quoted_string_end(bytes, index + 1),
            _ if bytes[index] == b'\"' => quoted_string_end(bytes, index),
            _ => raw_string_end(bytes, index),
        };
        let Some(end) = end else {
            index += 1;
            continue;
        };
        mask_non_newline(&mut masked, index, end);
        index = end;
    }
    String::from_utf8(masked).expect("masking preserves valid UTF-8")
}

fn line_comment_end(bytes: &[u8], start: usize) -> usize {
    bytes[start..]
        .iter()
        .position(|byte| *byte == b'\n')
        .map_or(bytes.len(), |offset| start + offset)
}

fn block_comment_end(bytes: &[u8], start: usize) -> Option<usize> {
    let mut depth = 1_u32;
    let mut index = start + 2;
    while index + 1 < bytes.len() {
        match &bytes[index..index + 2] {
            b"/*" => depth += 1,
            b"*/" => {
                depth -= 1;
                if depth == 0 {
                    return Some(index + 2);
                }
            }
            _ => {}
        }
        index += 1;
    }
    None
}

fn quoted_string_end(bytes: &[u8], quote: usize) -> Option<usize> {
    let mut index = quote + 1;
    while index < bytes.len() {
        if bytes[index] == b'\\' {
            index += 2;
        } else if bytes[index] == b'\"' {
            return Some(index + 1);
        } else {
            index += 1;
        }
    }
    None
}

fn raw_string_end(bytes: &[u8], start: usize) -> Option<usize> {
    let quote_start = if bytes.get(start) == Some(&b'r') {
        start + 1
    } else if bytes.get(start..start + 2) == Some(b"br") {
        start + 2
    } else {
        return None;
    };
    let hashes = bytes[quote_start..]
        .iter()
        .take_while(|byte| **byte == b'#')
        .count();
    let quote = quote_start + hashes;
    if bytes.get(quote) != Some(&b'\"') {
        return None;
    }
    let terminator = format!("\"{}", "#".repeat(hashes));
    let content = std::str::from_utf8(&bytes[quote + 1..]).ok()?;
    content
        .find(&terminator)
        .map(|offset| quote + 1 + offset + terminator.len())
}

fn mask_non_newline(bytes: &mut [u8], start: usize, end: usize) {
    for byte in &mut bytes[start..end] {
        if *byte != b'\n' {
            *byte = b' ';
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{FindingKind, calls_from_source, source_line};

    #[test]
    fn detects_aliases_qualified_paths_and_builder_chains() {
        let source = r#"
            use std::process::{self as process, Command as ProcessCommand};
            fn run() {
                ProcessCommand::new("git").arg("status").output().unwrap();
                process::Command::new("git").status().unwrap();
                std::process::Command::new("git").spawn().unwrap();
            }
        "#;
        let calls = calls_from_source(source, "src/example.rs").expect("valid source");
        assert_eq!(calls.len(), 3);
        assert!(calls.iter().all(|call| FindingKind::Process.matches(call)));
        assert!(calls.iter().all(|call| !FindingKind::GitHub.matches(call)));
        assert_eq!(calls[0].line, 4);
        assert_eq!(calls[2].line, 6);
    }

    #[test]
    fn detects_module_imports_declared_after_a_function() {
        let source = r#"
            fn run() { ProcessCommand::new("git"); }
            use std::process::Command as ProcessCommand;
        "#;
        assert_eq!(
            calls_from_source(source, "src/example.rs")
                .expect("valid source")
                .len(),
            1
        );
    }

    #[test]
    fn detects_only_literal_gh_commands() {
        let source = r#"
            use std::process::Command;
            fn run(program: &str) {
                Command::new("gh").arg("issue");
                Command::new(program).arg("issue");
                Command::new("git").arg("status");
            }
        "#;
        let calls = calls_from_source(source, "src/example.rs").expect("valid source");
        assert_eq!(calls.iter().filter(|call| FindingKind::GitHub.matches(call)).count(), 1);
    }

    #[test]
    fn ignores_non_standard_commands_comments_and_strings() {
        let source = r#"
            use tokio::process::Command;
            // std::process::Command::new("gh")
            const EXAMPLE: &str = "std::process::Command::new(\"gh\")";
            fn run() { Command::new("gh"); }
        "#;
        assert!(calls_from_source(source, "src/example.rs")
            .expect("valid source")
            .is_empty());
    }

    #[test]
    fn source_lines_follow_each_constructor_occurrence() {
        let source = "use std::process::Command;\nfn run() {\n  Command::new(\"git\");\n  Command::new(\"gh\");\n}\n";
        assert_eq!(source_line(source, "Command::new", 1), Some(3));
        assert_eq!(source_line(source, "Command::new", 2), Some(4));
    }

    #[test]
    fn source_lines_ignore_comments_and_strings_before_real_calls() {
        let source = concat!(
            "// Command::new(\"gh\")\n",
            "let example = \"Command::new(\\\"gh\\\")\";\n",
            "let command = Command::new(\"gh\");\n",
        );
        assert_eq!(source_line(source, "Command::new", 1), Some(3));
    }
}
