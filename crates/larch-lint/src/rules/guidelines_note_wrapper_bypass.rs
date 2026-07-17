//! Reject direct guidelines-note invalidation outside its pin-or-invalidate owner.
//!
//! # Crate survey (issue #7620)
//!
//! | Need | Candidates | Selection |
//! |------|------------|-----------|
//! | Rust syntax | workspace `syn`, `ra_ap_syntax` | Use `syn` visitors already established by #7604 for call and `use` alias shapes. Line numbers come from `proc-macro2` span locations already enabled in the workspace. Custom code encodes only the owner path and the forbidden callee names. |
//! | Call-name matching | workspace `regex`, exact ident compare | Exact identifier compare is enough for the closed callee set; `regex` would add no signal for these owner symbols. |
//! | Suppression parsing | workspace shared `suppression` module | Reuse the reason-bearing `lint-<rule>: ok <reason>` helper from #7604. |
//! | Serialization / baselines | workspace `serde`/`toml` | Not required: the Rust corpus starts at zero findings, so no grandfathering baseline ships. |
//!
//! No workspace `Cargo.toml` dependency is added (umbrella concurrency contract).

use std::collections::BTreeSet;

use syn::{
    Expr, ExprCall, ExprMethodCall, ItemUse, UseTree,
    spanned::Spanned,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    suppression, syntax::RustSyntax,
};

const NAME: &str = "guidelines-note-wrapper-bypass";
const DESCRIPTION: &str =
    "Reject direct guidelines-note invalidation outside the pin-or-invalidate owner";
const SUPPRESSION_TOKEN: &str = "lint-guidelines-note-wrapper-bypass";
const TARGET_CALLEE: &str = "invalidate_guidelines_note";
const TARGET_CALLEE_PRIVATE: &str = "_invalidate_guidelines_note";
const WRAPPER_CALLEE: &str = "pin_or_invalidate_guidelines_note";
const WRAPPER_CALLEE_PRIVATE: &str = "_pin_or_invalidate_guidelines_note";
const OWNER_PATH: &str = "crates/larch-implement/src/ship_guidelines.rs";
const RULE_PATH: &str = "crates/larch-lint/src/rules/guidelines_note_wrapper_bypass.rs";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/guidelines-note-wrapper-bypass.toml",
);

#[derive(Debug)]
pub struct GuidelinesNoteWrapperBypassRule;

pub static RULE: GuidelinesNoteWrapperBypassRule = GuidelinesNoteWrapperBypassRule;

impl Rule for GuidelinesNoteWrapperBypassRule {
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

fn check_rust_file(repository: &Repository, path: &RepoPath) -> Result<Vec<Finding>, LintError> {
    let relative = path.as_str();
    if relative == OWNER_PATH || relative == RULE_PATH {
        return Ok(Vec::new());
    }
    let source = repository.read_utf8(path)?;
    let syntax = RustSyntax::parse(relative, &source)?;
    let mut visitor = BypassVisitor {
        aliases: BTreeSet::new(),
        lines: BTreeSet::new(),
    };
    visitor.visit_file(syntax.file());
    resolve_findings(relative, &source, &visitor.lines)
}

struct BypassVisitor {
    aliases: BTreeSet<String>,
    lines: BTreeSet<u32>,
}

impl<'ast> Visit<'ast> for BypassVisitor {
    fn visit_item_use(&mut self, node: &'ast ItemUse) {
        collect_target_aliases(&node.tree, &mut self.aliases);
        visit::visit_item_use(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if call_targets_invalidate(&node.func, &self.aliases) {
            self.lines.insert(line_number(node.span()));
        }
        visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        let method = node.method.to_string();
        if is_target_name(&method) {
            self.lines.insert(line_number(node.span()));
        }
        visit::visit_expr_method_call(self, node);
    }
}

fn resolve_findings(
    path: &str,
    source: &str,
    lines: &BTreeSet<u32>,
) -> Result<Vec<Finding>, LintError> {
    let source_lines: Vec<&str> = source.lines().collect();
    let mut findings = Vec::new();
    for line in lines {
        let line_text = source_lines
            .get(usize::try_from(line.saturating_sub(1)).unwrap_or(0))
            .copied()
            .unwrap_or("");
        if suppression::reason(line_text, SUPPRESSION_TOKEN)?.is_some() {
            continue;
        }
        findings.push(Finding::new(
            path,
            *line,
            format!("calls {TARGET_CALLEE}; use {WRAPPER_CALLEE} instead"),
        ));
    }
    Ok(findings)
}

fn line_number(span: proc_macro2::Span) -> u32 {
    u32::try_from(span.start().line).unwrap_or(1)
}

fn is_target_name(name: &str) -> bool {
    name == TARGET_CALLEE || name == TARGET_CALLEE_PRIVATE
}

fn is_wrapper_name(name: &str) -> bool {
    name == WRAPPER_CALLEE || name == WRAPPER_CALLEE_PRIVATE
}

fn call_targets_invalidate(func: &Expr, aliases: &BTreeSet<String>) -> bool {
    match func {
        Expr::Path(path) => {
            let Some(last) = path.path.segments.last() else {
                return false;
            };
            let name = last.ident.to_string();
            if is_wrapper_name(&name) {
                return false;
            }
            is_target_name(&name) || aliases.contains(&name)
        }
        Expr::Paren(paren) => call_targets_invalidate(&paren.expr, aliases),
        Expr::Group(group) => call_targets_invalidate(&group.expr, aliases),
        _ => false,
    }
}

fn collect_target_aliases(tree: &UseTree, aliases: &mut BTreeSet<String>) {
    match tree {
        UseTree::Path(path) => collect_target_aliases(&path.tree, aliases),
        UseTree::Name(name) => {
            let ident = name.ident.to_string();
            if is_target_name(&ident) {
                aliases.insert(ident);
            }
        }
        UseTree::Rename(rename) => {
            if is_target_name(&rename.ident.to_string()) {
                aliases.insert(rename.rename.to_string());
            }
        }
        UseTree::Group(group) => {
            for item in &group.items {
                collect_target_aliases(item, aliases);
            }
        }
        UseTree::Glob(_) => {}
    }
}

#[cfg(test)]
mod tests {
    use super::{GuidelinesNoteWrapperBypassRule, OWNER_PATH};
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
    fn detects_direct_qualified_aliased_and_private_calls() {
        let fixture = repository_with(&[(
            "crates/demo/src/lib.rs",
            "use ship_guidelines::invalidate_guidelines_note as wipe;\nfn run(module: Helper) {\n    invalidate_guidelines_note();\n    _invalidate_guidelines_note();\n    ship_guidelines::invalidate_guidelines_note();\n    module.invalidate_guidelines_note();\n    wipe();\n}\nstruct Helper;\nimpl Helper {\n    fn invalidate_guidelines_note(&self) {}\n}\n",
        )]);
        let findings = GuidelinesNoteWrapperBypassRule
            .check(&fixture.repository)
            .expect("check");
        assert_eq!(findings.findings().len(), 5);
        assert!(findings.findings().iter().all(|finding| {
            finding
                .to_string()
                .contains("use pin_or_invalidate_guidelines_note")
        }));
    }

    #[test]
    fn owner_wrapper_definition_and_false_positives_are_clean() {
        let fixture = repository_with(&[
            (
                OWNER_PATH,
                "fn run() {\n    invalidate_guidelines_note();\n}\n",
            ),
            (
                "crates/demo/src/lib.rs",
                "fn invalidate_guidelines_note() {}\nfn run() {\n    pin_or_invalidate_guidelines_note();\n    _pin_or_invalidate_guidelines_note();\n}\n",
            ),
        ]);
        assert!(
            GuidelinesNoteWrapperBypassRule
                .check(&fixture.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }

    #[test]
    fn suppression_requires_reason() {
        let ok = repository_with(&[(
            "crates/demo/src/lib.rs",
            "fn run() {\n    invalidate_guidelines_note(); // lint-guidelines-note-wrapper-bypass: ok fixture\n}\n",
        )]);
        assert!(
            GuidelinesNoteWrapperBypassRule
                .check(&ok.repository)
                .expect("check")
                .findings()
                .is_empty()
        );

        let bad = repository_with(&[(
            "crates/demo/src/lib.rs",
            "fn run() {\n    invalidate_guidelines_note(); // lint-guidelines-note-wrapper-bypass: ok\n}\n",
        )]);
        assert!(
            GuidelinesNoteWrapperBypassRule
                .check(&bad.repository)
                .expect_err("missing reason")
                .to_string()
                .contains("lacks a reason")
        );
    }
}
