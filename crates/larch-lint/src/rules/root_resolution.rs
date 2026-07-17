use std::collections::{HashMap, HashSet};

use syn::{Expr, ImplItemFn, ItemFn, Lit, visit::Visit};

use crate::suppression;
use crate::syntax::RustSyntax;
use crate::{Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput};

use super::path_discovery;

const NAME: &str = "root-resolution";
const DESCRIPTION: &str =
    "Reject private root helpers and direct git rev-parse --show-toplevel construction";
const SUPPRESSION_TOKEN: &str = "lint-root-resolution";
const PRIVATE_PLUGIN_ROOT: &str = "private-plugin-root";
const INLINE_GIT_TOPLEVEL: &str = "inline-git-toplevel";
const OWNER_PATHS: &[&str] = &[
    "crates/larch-lint/src/repository.rs",
    "crates/larch-lint/src/rules/root_resolution.rs",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/root-resolution.toml",
);

#[derive(Debug)]
pub struct RootResolutionRule;

pub static RULE: RootResolutionRule = RootResolutionRule;

impl Rule for RootResolutionRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in path_discovery::selected_rust_sources(repository)? {
            if OWNER_PATHS.contains(&path.as_str()) || path_discovery::is_test_path(path.as_str())
            {
                continue;
            }
            let source = repository.read_utf8(path)?;
            findings.extend(scan_source(path.as_str(), &source)?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn scan_source(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let syntax = RustSyntax::parse(path, source)?;
    let mut visitor = RootVisitor {
        matches: Vec::new(),
    };
    visitor.visit_file(syntax.file());
    let mut kind_counts = HashMap::<&str, u32>::new();
    let mut needle_counts = HashMap::<String, u32>::new();
    let mut findings = Vec::new();
    for (kind, needle) in visitor.matches {
        let occurrence = kind_counts.entry(kind).or_insert(0);
        *occurrence = occurrence.saturating_add(1);
        let needle_occurrence = needle_counts.entry(needle.clone()).or_insert(0);
        *needle_occurrence = needle_occurrence.saturating_add(1);
        let Some(line) =
            suppression::line_unless_suppressed(source, &needle, *needle_occurrence, SUPPRESSION_TOKEN)?
        else {
            continue;
        };
        findings.push(Finding::new(
            path,
            line,
            format!("{kind} must use the repository-root owner (occurrence {occurrence})"),
        ));
    }
    Ok(findings)
}

struct RootVisitor {
    matches: Vec<(&'static str, String)>,
}

impl<'ast> Visit<'ast> for RootVisitor {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        if node.sig.ident == "_plugin_root" {
            self.matches
                .push((PRIVATE_PLUGIN_ROOT, "fn _plugin_root".to_owned()));
        }
        syn::visit::visit_item_fn(self, node);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast ImplItemFn) {
        if node.sig.ident == "_plugin_root" {
            self.matches
                .push((PRIVATE_PLUGIN_ROOT, "fn _plugin_root".to_owned()));
        }
        syn::visit::visit_impl_item_fn(self, node);
    }

    fn visit_expr(&mut self, node: &'ast Expr) {
        if let Some(needle) = inline_git_toplevel_needle(node) {
            self.matches.push((INLINE_GIT_TOPLEVEL, needle));
        }
        syn::visit::visit_expr(self, node);
    }
}

fn inline_git_toplevel_needle(expr: &Expr) -> Option<String> {
    let values = match expr {
        Expr::Array(array) => collect_string_literals(array.elems.iter()),
        Expr::Tuple(tuple) => collect_string_literals(tuple.elems.iter()),
        _ => return None,
    };
    if values.contains("rev-parse") && values.contains("--show-toplevel") {
        Some("\"rev-parse\"".to_owned())
    } else {
        None
    }
}

fn collect_string_literals<'expr>(exprs: impl Iterator<Item = &'expr Expr>) -> HashSet<String> {
    let mut values = HashSet::new();
    for expr in exprs {
        if let Expr::Lit(lit) = expr
            && let Lit::Str(value) = &lit.lit
        {
            values.insert(value.value());
        }
    }
    values
}

#[cfg(test)]
mod tests {
    use super::scan_source;

    #[test]
    fn rejects_private_plugin_root_helpers() {
        let findings = scan_source("demo.rs", "fn _plugin_root() -> &'static str { \"x\" }\n")
            .expect("scan");
        assert_eq!(findings.len(), 1);
        assert!(findings[0].to_string().contains("private-plugin-root"));
    }

    #[test]
    fn rejects_impl_plugin_root_methods() {
        let source = "struct Owner;\nimpl Owner { fn _plugin_root(&self) {}\n}\n";
        let findings = scan_source("demo.rs", source).expect("scan");
        assert_eq!(findings.len(), 1);
        assert!(findings[0].to_string().contains("private-plugin-root"));
    }

    #[test]
    fn rejects_inline_git_toplevel_arrays_and_tuples() {
        let source = "fn demo() {\n    let one = [\"git\", \"rev-parse\", \"--show-toplevel\"];\n    let two = (\"rev-parse\", \"--show-toplevel\");\n}\n";
        let findings = scan_source("demo.rs", source).expect("scan");
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().all(|finding| finding.to_string().contains("inline-git-toplevel")));
    }

    #[test]
    fn honors_reason_bearing_suppressions() {
        let source = "fn _plugin_root() -> &'static str { \"x\" } // lint-root-resolution: ok fixture helper\n";
        assert!(scan_source("demo.rs", source).expect("scan").is_empty());
    }

    #[test]
    fn ignores_partial_git_argv_literals() {
        let source = "fn demo() { let one = [\"rev-parse\"]; let two = [\"--show-toplevel\"]; }\n";
        assert!(scan_source("demo.rs", source).expect("scan").is_empty());
    }
}
