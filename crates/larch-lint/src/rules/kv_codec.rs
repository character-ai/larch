//! Reject ad-hoc `KEY=value` readers and emitters outside shared owners.
//!
//! # Crate survey (issue #7617)
//!
//! | Need | Candidates | Selection |
//! |------|------------|-----------|
//! | Rust syntax | workspace `syn`, `ra_ap_syntax` | Use `syn` visitors already established by #7604 for call-shape detection. Line numbers come from the source text (no `proc-macro2` `span-locations` feature; leaves must not add workspace dependencies). Custom code encodes only owner paths and prohibited shapes. |
//! | Shell line shapes | workspace `regex`, `tree-sitter-bash` | This future-state rule targets Rust sources only. Shell KEY=value ratchet remains with the Python `kv-codec` lint until the non-Python cutover leaf retires it. |
//! | Serialization / baselines | workspace `serde`/`toml` | Not required: the Rust corpus starts at zero findings, so no grandfathering baseline ships. |
//!
//! No workspace `Cargo.toml` dependency is added (umbrella concurrency contract).

use std::collections::BTreeSet;

use syn::{
    Expr, ExprForLoop, ExprMethodCall, ItemFn, Member,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::RustSyntax,
};

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

const OPTION_ITER_NAMES: &[&str] = &["args", "argv", "options", "tokens"];
const OPTION_BINDING_NAMES: &[&str] = &["arg", "token", "opt", "option", "argv_item"];

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
        let selector = PathSelector::new(&["crates/**/*.rs"], &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            findings.extend(check_rust_file(repository, path)?);
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
    let source = repository.read_utf8(path)?;
    let syntax = RustSyntax::parse(path.as_str(), &source)?;
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
    use super::{EMITTER_OWNER, KvCodecRule, READER_OWNERS};
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
}
