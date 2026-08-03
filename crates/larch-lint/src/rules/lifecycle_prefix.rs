//! Ratchet lifecycle and bug title-prefix literals toward shared constants.
//!
//! This is the Rust equivalent of the Python `lifecycle-prefix-literal` rule.
//! It scans tracked Rust source with `syn`'s expression and literal visitors
//! and flags a lifecycle or bug title prefix that appears as a bare literal in
//! a comparison, a pattern match, a formatting macro, or a string composition.
//! The canonical owner of the prefix constant, a `const` or `static` literal
//! definition, is exempt, and a same-line `lint-lifecycle-prefix: ok <reason>`
//! comment suppresses a finding with a required reason.
//!
//! The Python rule also scans regex patterns (`re.compile`/`search`/`match`/
//! `fullmatch`); that context is intentionally out of scope for this port,
//! which covers the four acceptance-criteria contexts above.

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::visit::{self, Visit};

use crate::{Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput};

use super::rust_scan;

const NAME: &str = "lifecycle-prefix-literal";
const DESCRIPTION: &str = "Ratchet lifecycle and bug title-prefix literals toward shared constants";
const SUPPRESSION_TOKEN: &str = "lint-lifecycle-prefix";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/lifecycle-prefix-literal.toml",
);

#[derive(Debug)]
pub struct LifecyclePrefixRule;

pub static RULE: LifecyclePrefixRule = LifecyclePrefixRule;

/// Canonical lifecycle and bug title prefixes. Mirrors the Python owners
/// `config.TRACKING_ISSUE_PREFIX_BY_STATE` values,
/// `config.DEBATE_TITLE_PREFIX_BY_STATE` values, and `title_match.BUG_PREFIX`.
/// Matching normalizes both sides, so the trailing space carried by the Python
/// state prefixes is not repeated here.
pub const PREFIXES: &[&str] = &[
    "[DESIGNING]",
    "[DESIGNED]",
    "[IMPLEMENTING]",
    "[DONE]",
    "[STALLED]",
    "[DEBATING]",
    "[DEBATED]",
    "[BUG]",
];

/// Format-family macros whose string arguments compose user-facing text.
const FORMAT_MACROS: &[&str] = &[
    "format",
    "format_args",
    "print",
    "println",
    "eprint",
    "eprintln",
    "write",
    "writeln",
    "panic",
];

/// Concatenation macro; a composition context that is valid in `const` position.
const CONCAT_MACRO: &str = "concat";

/// Assertion macros whose operands and format message hide in a token stream.
const ASSERT_MACROS: &[&str] = &["assert_eq", "assert_ne", "debug_assert_eq", "debug_assert_ne"];

/// Pattern-test macro; its literal arguments are exact patterns.
const MATCHES_MACRO: &str = "matches";

/// String prefix and affix methods; a title-prefix operand is a composition.
const PREFIX_METHODS: &[&str] = &[
    "starts_with",
    "ends_with",
    "strip_prefix",
    "strip_suffix",
    "trim_start_matches",
    "trim_end_matches",
];

/// A prefix matcher: returns the canonical prefix a literal value resolves to.
type PrefixMatcher = fn(&str) -> Option<&'static str>;

/// The syntactic position a flagged literal was found in.
#[derive(Clone, Copy)]
enum Context {
    Comparison,
    Match,
    Formatting,
    Composition,
}

impl Context {
    const fn label(self) -> &'static str {
        match self {
            Self::Comparison => "comparison",
            Self::Match => "match",
            Self::Formatting => "formatting",
            Self::Composition => "composition",
        }
    }
}

/// One pre-suppression detection carrying its source line and message inputs.
struct RawFinding {
    line: usize,
    prefix: &'static str,
    context: Context,
}

impl RawFinding {
    fn message(&self) -> String {
        let (prefix, context) = (self.prefix, self.context.label());
        format!(
            "lifecycle-prefix literal {prefix} in {context}; \
             reference a shared lifecycle-prefix constant instead"
        )
    }
}

/// Trailing spaces are stripped and ASCII case is folded, matching the Python
/// rule's `rstrip(" ").casefold()` normalization for the ASCII bracket tokens.
fn normalize(value: &str) -> String {
    value.trim_end_matches(' ').to_ascii_lowercase()
}

/// Match a literal that equals a prefix exactly (comparisons and patterns).
fn equality_prefix(value: &str) -> Option<&'static str> {
    let normalized = normalize(value);
    PREFIXES
        .iter()
        .copied()
        .find(|prefix| normalize(prefix) == normalized)
}

/// Match a literal that equals a prefix or begins with `<prefix> ` / `<prefix>:`
/// (formatting and composition, where the prefix leads a longer string).
fn composition_prefix(value: &str) -> Option<&'static str> {
    let normalized = normalize(value);
    PREFIXES.iter().copied().find(|prefix| {
        let token = normalize(prefix);
        normalized == token
            || normalized
                .strip_prefix(token.as_str())
                .is_some_and(|rest| rest.starts_with(' ') || rest.starts_with(':'))
    })
}

/// Extract a direct string literal and its span from an expression operand.
fn str_literal(expr: &syn::Expr) -> Option<(String, Span)> {
    let syn::Expr::Lit(expr_lit) = expr else {
        return None;
    };
    let syn::Lit::Str(literal) = &expr_lit.lit else {
        return None;
    };
    Some((literal.value(), literal.span()))
}

/// Return a macro's final path segment, e.g. `concat` for `std::concat!`.
fn macro_name(mac: &syn::Macro) -> Option<String> {
    mac.path.segments.last().map(|seg| seg.ident.to_string())
}

/// Classify a macro name into its detection context and matcher, or ignore it.
fn classify_macro(name: &str) -> Option<(Context, PrefixMatcher)> {
    if FORMAT_MACROS.contains(&name) {
        Some((Context::Formatting, composition_prefix))
    } else if name == CONCAT_MACRO {
        Some((Context::Composition, composition_prefix))
    } else if ASSERT_MACROS.contains(&name) {
        Some((Context::Comparison, composition_prefix))
    } else if name == MATCHES_MACRO {
        Some((Context::Match, equality_prefix))
    } else {
        None
    }
}

/// Whether a `const`/`static` initializer is a pure prefix-literal definition,
/// the canonical owner that names the constant. Nested logic (closures, calls,
/// comparisons) is not a definition and is scanned normally.
fn is_owner_value(expr: &syn::Expr) -> bool {
    match expr {
        syn::Expr::Lit(expr_lit) => matches!(expr_lit.lit, syn::Lit::Str(_)),
        syn::Expr::Array(array) => array.elems.iter().all(is_owner_value),
        syn::Expr::Tuple(tuple) => tuple.elems.iter().all(is_owner_value),
        syn::Expr::Reference(reference) => is_owner_value(&reference.expr),
        syn::Expr::Paren(paren) => is_owner_value(&paren.expr),
        syn::Expr::Group(group) => is_owner_value(&group.expr),
        syn::Expr::Macro(expr_macro) => macro_name(&expr_macro.mac).as_deref() == Some(CONCAT_MACRO),
        _ => false,
    }
}

/// Walks a parsed file, recording prefix literals outside owner definitions.
#[derive(Default)]
struct Collector {
    findings: Vec<RawFinding>,
}

impl Collector {
    fn record(&mut self, span: Span, prefix: &'static str, context: Context) {
        self.findings.push(RawFinding {
            line: span.start().line,
            prefix,
            context,
        });
    }

    fn check_binary(&mut self, node: &syn::ExprBinary) {
        let classified = match node.op {
            syn::BinOp::Eq(_) | syn::BinOp::Ne(_) => {
                Some((Context::Comparison, equality_prefix as PrefixMatcher))
            }
            syn::BinOp::Add(_) => Some((Context::Composition, composition_prefix as PrefixMatcher)),
            _ => None,
        };
        let Some((context, matcher)) = classified else {
            return;
        };
        for operand in [node.left.as_ref(), node.right.as_ref()] {
            if let Some((value, span)) = str_literal(operand)
                && let Some(prefix) = matcher(&value)
            {
                self.record(span, prefix, context);
            }
        }
    }

    fn check_pattern(&mut self, node: &syn::Pat) {
        if let syn::Pat::Lit(expr_lit) = node
            && let syn::Lit::Str(literal) = &expr_lit.lit
            && let Some(prefix) = equality_prefix(&literal.value())
        {
            self.record(literal.span(), prefix, Context::Match);
        }
    }

    fn check_macro(&mut self, mac: &syn::Macro) {
        let Some(name) = macro_name(mac) else {
            return;
        };
        let Some((context, matcher)) = classify_macro(&name) else {
            return;
        };
        self.scan_tokens(mac.tokens.clone(), context, matcher);
    }

    /// Scan a macro token stream, descending into groups, for string literals.
    fn scan_tokens(&mut self, tokens: TokenStream, context: Context, matcher: PrefixMatcher) {
        for token in tokens {
            match token {
                TokenTree::Literal(literal) => {
                    if let syn::Lit::Str(text) = syn::Lit::new(literal)
                        && let Some(prefix) = matcher(&text.value())
                    {
                        self.record(text.span(), prefix, context);
                    }
                }
                TokenTree::Group(group) => self.scan_tokens(group.stream(), context, matcher),
                TokenTree::Ident(_) | TokenTree::Punct(_) => {}
            }
        }
    }

    fn check_method(&mut self, node: &syn::ExprMethodCall) {
        if !PREFIX_METHODS.contains(&node.method.to_string().as_str()) {
            return;
        }
        for operand in std::iter::once(node.receiver.as_ref()).chain(node.args.iter()) {
            if let Some((value, span)) = str_literal(operand)
                && let Some(prefix) = composition_prefix(&value)
            {
                self.record(span, prefix, Context::Composition);
            }
        }
    }
}

impl<'ast> Visit<'ast> for Collector {
    fn visit_item_const(&mut self, node: &'ast syn::ItemConst) {
        if !is_owner_value(&node.expr) {
            visit::visit_item_const(self, node);
        }
    }

    fn visit_item_static(&mut self, node: &'ast syn::ItemStatic) {
        if !is_owner_value(&node.expr) {
            visit::visit_item_static(self, node);
        }
    }

    fn visit_impl_item_const(&mut self, node: &'ast syn::ImplItemConst) {
        if !is_owner_value(&node.expr) {
            visit::visit_impl_item_const(self, node);
        }
    }

    fn visit_trait_item_const(&mut self, node: &'ast syn::TraitItemConst) {
        let owner = node
            .default
            .as_ref()
            .is_some_and(|(_, expr)| is_owner_value(expr));
        if !owner {
            visit::visit_trait_item_const(self, node);
        }
    }

    fn visit_expr_binary(&mut self, node: &'ast syn::ExprBinary) {
        self.check_binary(node);
        visit::visit_expr_binary(self, node);
    }

    fn visit_pat(&mut self, node: &'ast syn::Pat) {
        self.check_pattern(node);
        visit::visit_pat(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        self.check_method(node);
        visit::visit_expr_method_call(self, node);
    }

    fn visit_macro(&mut self, node: &'ast syn::Macro) {
        self.check_macro(node);
        visit::visit_macro(self, node);
    }
}

/// Scan one Rust source buffer, dropping owner definitions and suppressed lines.
///
/// # Errors
///
/// Returns an error when a suppression token lacks a reason or a line number
/// exceeds `u32`. Unparseable Rust is skipped, mirroring the Python rule.
fn check_source(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    rust_scan::findings(path, source, SUPPRESSION_TOKEN, |file| {
        let mut collector = Collector::default();
        collector.visit_file(file);
        collector
            .findings
            .iter()
            .map(|raw| (raw.line, raw.message()))
            .collect()
    })
}

impl Rule for LifecyclePrefixRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["**/*.rs"], &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            let source = repository.read_utf8(path)?;
            findings.extend(check_source(path.as_str(), &source)?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[cfg(test)]
mod tests {
    use super::check_source;

    /// Render findings as `path:line: message` strings for assertions.
    fn scan(source: &str) -> Vec<String> {
        check_source("test.rs", source)
            .expect("scan succeeds")
            .iter()
            .map(ToString::to_string)
            .collect()
    }

    #[test]
    fn flags_equality_and_inequality_comparisons() {
        let source = "fn f(x: &str) { let _ = x == \"[DONE]\"; let _ = \"[BUG]\" != x; }";
        let findings = scan(source);
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().any(|line| line.contains("[DONE] in comparison")));
        assert!(findings.iter().any(|line| line.contains("[BUG] in comparison")));
    }

    #[test]
    fn flags_match_arm_including_or_patterns() {
        let source = "fn f(x: &str) { match x { \"[STALLED]\" => {} \"[a]\" | \"[DONE]\" => {} _ => {} } }";
        let findings = scan(source);
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().any(|line| line.contains("[STALLED] in match")));
        assert!(findings.iter().any(|line| line.contains("[DONE] in match")));
    }

    #[test]
    fn flags_nested_and_if_let_patterns() {
        let source =
            "fn f(x: Option<&str>) { if let Some(\"[DONE]\") = x {} match x { Some(\"[BUG]\") => {} _ => {} } }";
        let findings = scan(source);
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().all(|line| line.contains("in match")));
    }

    #[test]
    fn flags_format_macro_template_and_argument() {
        let source =
            "fn f(x: &str) { let _ = format!(\"[IMPLEMENTING] {}\", x); println!(\"{}\", \"[DONE]\"); }";
        let findings = scan(source);
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().any(|line| line.contains("[IMPLEMENTING] in formatting")));
        assert!(findings.iter().any(|line| line.contains("[DONE] in formatting")));
    }

    #[test]
    fn flags_concat_and_plus_composition() {
        let source = "fn f(x: String) { let _ = concat!(\"[DONE] \", \"tail\"); let _ = x + \"[BUG]\"; }";
        let findings = scan(source);
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().any(|line| line.contains("[DONE] in composition")));
        assert!(findings.iter().any(|line| line.contains("[BUG] in composition")));
    }

    #[test]
    fn flags_prefix_method_receiver_and_argument() {
        // Argument, receiver, and a colon-suffixed variant are all composition.
        let source = "fn f(x: &str) { let _ = x.starts_with(\"[DONE]\"); let _ = \"[BUG]\".starts_with(x); let _ = x.strip_prefix(\"[DONE]:\"); }";
        let findings = scan(source);
        assert_eq!(findings.len(), 3);
        assert!(findings.iter().all(|line| line.contains("in composition")));
    }

    #[test]
    fn flags_assert_and_matches_macros() {
        let source = "fn f(x: &str) { assert_eq!(x, \"[DONE]\"); assert_eq!(x, x, \"[STALLED] context\"); let _ = matches!(x, \"[BUG]\"); }";
        let findings = scan(source);
        assert_eq!(findings.len(), 3);
        assert!(findings.iter().any(|line| line.contains("[DONE] in comparison")));
        assert!(findings.iter().any(|line| line.contains("[STALLED] in comparison")));
        assert!(findings.iter().any(|line| line.contains("[BUG] in match")));
    }

    #[test]
    fn flags_literals_wrapped_in_macro_groups() {
        let source = "fn f(x: Option<&str>) { let _ = matches!(x, Some(\"[DONE]\")); }";
        let findings = scan(source);
        assert_eq!(findings.len(), 1);
        assert!(findings[0].contains("[DONE] in match"));
    }

    #[test]
    fn reports_the_correct_line_number() {
        let source = "fn f(x: &str) {\n    let _ = x == \"[DONE]\";\n}";
        let findings = scan(source);
        assert_eq!(findings.len(), 1);
        assert!(findings[0].starts_with("test.rs:2:"));
    }

    #[test]
    fn exempts_literal_owner_definitions() {
        // A bare literal, a concat! definition, an array, static, impl, and
        // trait-default owners are all exempt.
        assert!(scan("const DONE: &str = \"[DONE] \";").is_empty());
        assert!(scan("const DONE: &str = concat!(\"[DONE] \", \"x\");").is_empty());
        assert!(scan("const PREFIXES: &[&str] = &[\"[DONE] \", \"[BUG]\"];").is_empty());
        assert!(scan("static DONE: &str = concat!(\"[DONE] \", \"x\");").is_empty());
        assert!(scan("struct S; impl S { const DONE: &str = concat!(\"[DONE] \", \"x\"); }").is_empty());
        assert!(scan("trait T { const DONE: &str = \"[DONE] \"; }").is_empty());
    }

    #[test]
    fn flags_usage_nested_inside_an_initializer() {
        // Only the direct definition is exempt; a comparison nested in a
        // static or const initializer is scanned and flagged.
        let closure = "static CHECK: fn(&str) -> bool = |s| s == \"[DONE]\";";
        let closure_findings = scan(closure);
        assert_eq!(closure_findings.len(), 1);
        assert!(closure_findings[0].contains("[DONE] in comparison"));
        assert_eq!(scan("static M: bool = { let s = \"a\"; s == \"[BUG]\" };").len(), 1);
    }

    #[test]
    fn suppresses_with_a_reason_on_the_same_line() {
        let source =
            "fn f(x: &str) {\n    let _ = x == \"[DONE]\"; // lint-lifecycle-prefix: ok legacy compare\n}";
        assert!(scan(source).is_empty());
    }

    #[test]
    fn suppression_without_a_reason_is_an_error() {
        let source = "fn f(x: &str) {\n    let _ = x == \"[DONE]\"; // lint-lifecycle-prefix: ok\n}";
        assert!(check_source("test.rs", source).is_err());
    }

    #[test]
    fn ignores_non_prefix_and_extended_literals() {
        // Not a prefix; a comparison literal that is longer than the prefix
        // (equality context) does not match.
        let source = "fn f(x: &str) { let _ = x == \"[FOO]\"; let _ = x == \"[DONE] later\"; }";
        assert!(scan(source).is_empty());
    }

    #[test]
    fn matches_case_insensitively_and_ignores_trailing_space() {
        let source = "fn f(x: &str) { let _ = x == \"[done] \"; }";
        let findings = scan(source);
        assert_eq!(findings.len(), 1);
        assert!(findings[0].contains("[DONE] in comparison"));
    }

    // The prefix set is owned by Python (`config.TRACKING_ISSUE_PREFIX_BY_STATE`
    // + `config.DEBATE_TITLE_PREFIX_BY_STATE` + `title_match.BUG_PREFIX`) and
    // cannot be imported across the process boundary, so it is embedded here.
    // This guards against silent drift (G-Cfg-3) by re-deriving the owner set
    // from the live Python source and comparing.
    #[test]
    fn prefixes_match_the_python_owner_constants() {
        use std::collections::BTreeSet;
        use std::path::Path;

        let python = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../python/larch");
        let config =
            std::fs::read_to_string(python.join("core/config.py")).expect("read config.py");
        let title = std::fs::read_to_string(python.join("issue/title_match.py"))
            .expect("read title_match.py");
        let literal = regex::Regex::new("\"([^\"]*)\"").expect("literal regex");

        // Bracket-token values of the TRACKING_ISSUE_PREFIX_BY_STATE dict literal.
        let (_, after_name) = config
            .split_once("TRACKING_ISSUE_PREFIX_BY_STATE")
            .expect("locate prefix dict");
        let (_, after_open) = after_name.split_once('{').expect("locate dict open");
        let (dict, _) = after_open.split_once('}').expect("locate dict close");
        let mut owner: BTreeSet<String> = literal
            .captures_iter(dict)
            .map(|caps| caps[1].to_owned())
            .filter(|value| value.starts_with('['))
            .map(|value| super::normalize(&value))
            .collect();

        // DEBATE_TITLE_PREFIX_BY_STATE is derived from the bare DEBATE_TITLE_STATES
        // tokens, so read that tuple and bracket each token to compare.
        let (_, after_states) = config
            .split_once("DEBATE_TITLE_STATES")
            .expect("locate debate states");
        let (_, after_tuple_open) = after_states.split_once('(').expect("locate tuple open");
        let (tuple, _) = after_tuple_open.split_once(')').expect("locate tuple close");
        owner.extend(
            literal
                .captures_iter(tuple)
                .map(|caps| super::normalize(&format!("[{}]", &caps[1]))),
        );

        // The BUG_PREFIX constant value.
        let bug_line = title
            .lines()
            .find(|line| line.trim_start().starts_with("BUG_PREFIX"))
            .expect("locate BUG_PREFIX");
        let bug = literal.captures(bug_line).expect("BUG_PREFIX value");
        owner.insert(super::normalize(&bug[1]));

        let rust: BTreeSet<String> =
            super::PREFIXES.iter().map(|prefix| super::normalize(prefix)).collect();
        assert_eq!(
            rust, owner,
            "Rust PREFIXES drifted from the Python lifecycle/bug prefix owners"
        );
    }
}
