//! Reject duplicated convention regexes and lifecycle-prefix strip loops.
//!
//! # Crate survey (issue #7620)
//!
//! | Need | Candidates | Selection |
//! |------|------------|-----------|
//! | Rust syntax | workspace `syn`, `ra_ap_syntax` | Use `syn` visitors already established by #7604 for call, const, and loop shapes. Line numbers come from `proc-macro2` span locations already enabled in the workspace. Custom code encodes only owner paths and the forbidden duplicate shapes. |
//! | Pattern shape tests | workspace `regex`, hand-rolled `contains` | Heading-shape detection keeps the Python lint's multi-predicate `contains` heuristics so the future-state contract stays auditable and parity-tested. Workspace `regex` owns the bug-title selector shape (`[BUG]` + `in:title`). |
//! | Suppression parsing | workspace shared `suppression` module | Reuse the reason-bearing `lint-<rule>: ok <reason>` helper from #7604. |
//! | Serialization / baselines | workspace `serde`/`toml` | Not required: the Rust corpus starts at zero findings, so no grandfathering baseline ships. |
//!
//! No workspace `Cargo.toml` dependency is added (umbrella concurrency contract).

use std::collections::BTreeSet;

use regex::Regex;
use syn::{
    Expr, ExprCall, ExprForLoop, ExprMethodCall, ItemConst, ItemStatic, Lit, Member, Pat,
    spanned::Spanned,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    suppression, syntax::RustSyntax,
};

const NAME: &str = "shared-convention-regex";
const DESCRIPTION: &str =
    "Reject copied heading regexes, bug-title selectors, and lifecycle-prefix strip loops";
const SUPPRESSION_TOKEN: &str = "lint-shared-convention-regex";

/// Future-state owners for architectural heading regexes.
///
/// Until `larch-core` materializes, `guideline-no-exception` is the live
/// Rust owner that must parse guideline headings from
/// `ARCHITECTURAL_GUIDELINES.md`.
const HEADING_OWNERS: &[&str] = &[
    "crates/larch-core/src/architectural_guidelines.rs",
    "crates/larch-lint/src/rules/guideline_no_exception.rs",
];
/// Future-state owner for bug-title and lifecycle-prefix helpers.
const TITLE_OWNER: &str = "crates/larch-issue/src/title_match.rs";
/// Future-state owner for FINDING/OOS block parsers.
const REVIEW_OWNER: &str = "crates/larch-review/src/review_types.rs";
const RULE_PATH: &str = "crates/larch-lint/src/rules/shared_convention_regex.rs";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/shared-convention-regex.toml",
);

#[derive(Debug)]
pub struct SharedConventionRegexRule;

pub static RULE: SharedConventionRegexRule = SharedConventionRegexRule;

impl Rule for SharedConventionRegexRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["crates/**/*.rs"], &[])?;
        let bug_selector = Regex::new(r"\[BUG\].*in:title")
            .map_err(|error| LintError::new(format!("invalid rule regex: {error}")))?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            findings.extend(check_rust_file(repository, path, &bug_selector)?);
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum ViolationKind {
    GuidelineHeading,
    InvariantHeading,
    ReviewerItemHeading,
    BugTitleSelector,
    LifecycleStripLoop,
}

impl ViolationKind {
    const fn message(self) -> &'static str {
        match self {
            Self::GuidelineHeading => {
                "guideline-heading-regex; use architectural_guidelines::GUIDELINE_HEADING_RE"
            }
            Self::InvariantHeading => {
                "invariant-heading-regex; use architectural_guidelines::INVARIANT_HEADING_RE"
            }
            Self::ReviewerItemHeading => {
                "reviewer-item-heading-regex; use review_types::parse_blocks or review_types::parse_canonical_heading"
            }
            Self::BugTitleSelector => {
                "bug-title-selector; use title_match::bug_title_match or title_match::BUG_PREFIX"
            }
            Self::LifecycleStripLoop => {
                "lifecycle-prefix-strip-loop; use title_match::strip_lifecycle_prefix or title_match::detect_lifecycle_prefix"
            }
        }
    }
}

fn check_rust_file(
    repository: &Repository,
    path: &RepoPath,
    bug_selector: &Regex,
) -> Result<Vec<Finding>, LintError> {
    let relative = path.as_str();
    if is_allowlisted(relative) {
        return Ok(Vec::new());
    }
    let source = repository.read_utf8(path)?;
    let syntax = RustSyntax::parse(relative, &source)?;
    let mut visitor = ConventionVisitor {
        pending: Vec::new(),
        bug_selector,
    };
    visitor.visit_file(syntax.file());
    resolve_findings(relative, &source, &visitor.pending)
}

fn is_allowlisted(path: &str) -> bool {
    HEADING_OWNERS.contains(&path) || path == TITLE_OWNER || path == REVIEW_OWNER || path == RULE_PATH
}

fn looks_like_guideline_heading(value: &str) -> bool {
    let has_heading_anchor = value.starts_with("^#") || value.starts_with(r"\A#");
    let has_guideline_id = value.contains("G-") && value.contains(r"\d");
    let has_markdown_separator = value.contains(':') && value.contains(r"\s");
    has_heading_anchor && has_guideline_id && has_markdown_separator
}

fn looks_like_invariant_heading(value: &str) -> bool {
    let has_heading_anchor = value.starts_with("^#") || value.starts_with(r"\A#");
    let has_invariant_id =
        (value.contains("I-") || value.contains("INV-")) && value.contains(r"\d");
    let has_markdown_separator = value.contains(':') && value.contains(r"\s");
    has_heading_anchor && has_invariant_id && has_markdown_separator
}

fn looks_like_reviewer_item_heading(value: &str) -> bool {
    let has_item_token = value.contains("FINDING_")
        || value.contains("OOS_")
        || value.contains("(?:FINDING|OOS)")
        || value.contains("(?:OOS|FINDING)");
    let has_markdown_heading =
        value.contains("###") || value.contains("^#") || value.contains(r"\A#");
    let has_numeric_id = value.contains(r"\d") || value.contains("[0-9]");
    let has_block_segmentation =
        value.contains(".*?") && (value.contains("(?=") || value.contains(r"\Z"));
    let has_block_seg_multiline = value.contains("(?m") && value.contains(".*$");
    let has_full_heading_parse =
        has_item_token && value.contains("(.*?)") && !value.contains("MULTILINE");
    let has_canonical_id_capture = (value.contains(r"OOS_(\d") || value.contains(r"FINDING_(\d"))
        && has_markdown_heading;
    has_item_token
        && has_markdown_heading
        && has_numeric_id
        && (has_block_segmentation
            || has_block_seg_multiline
            || has_full_heading_parse
            || has_canonical_id_capture)
}

fn classify_heading(value: &str) -> Vec<ViolationKind> {
    let mut kinds = Vec::new();
    if looks_like_guideline_heading(value) {
        kinds.push(ViolationKind::GuidelineHeading);
    }
    if looks_like_invariant_heading(value) {
        kinds.push(ViolationKind::InvariantHeading);
    }
    if looks_like_reviewer_item_heading(value) {
        kinds.push(ViolationKind::ReviewerItemHeading);
    }
    kinds
}

struct PendingViolation {
    kind: ViolationKind,
    line: u32,
}

struct ConventionVisitor<'regex> {
    pending: Vec<PendingViolation>,
    bug_selector: &'regex Regex,
}

impl<'ast> Visit<'ast> for ConventionVisitor<'_> {
    fn visit_item_const(&mut self, node: &'ast ItemConst) {
        self.inspect_module_literal(&node.expr, node.span().start().line);
        visit::visit_item_const(self, node);
    }

    fn visit_item_static(&mut self, node: &'ast ItemStatic) {
        self.inspect_module_literal(&node.expr, node.span().start().line);
        visit::visit_item_static(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if is_regex_constructor(&node.func)
            && let Some(value) = first_string_literal(node.args.first())
        {
            self.record_heading_shapes(&value, line_number(node.span()));
        }
        visit::visit_expr_call(self, node);
    }

    fn visit_expr_for_loop(&mut self, node: &'ast ExprForLoop) {
        if let Some(loop_variable) = pat_ident(&node.pat)
            && iter_mentions_lifecycle_prefixes(&node.expr)
            && loop_body_strips_prefix(node, &loop_variable)
        {
            self.pending.push(PendingViolation {
                kind: ViolationKind::LifecycleStripLoop,
                line: line_number(node.span()),
            });
        }
        visit::visit_expr_for_loop(self, node);
    }
}

impl ConventionVisitor<'_> {
    fn inspect_module_literal(&mut self, expr: &Expr, line: usize) {
        let Some(value) = string_literal(expr) else {
            return;
        };
        let line = u32::try_from(line).unwrap_or(1);
        self.record_heading_shapes(&value, line);
        if self.bug_selector.is_match(&value) {
            self.pending.push(PendingViolation {
                kind: ViolationKind::BugTitleSelector,
                line,
            });
        }
    }

    fn record_heading_shapes(&mut self, value: &str, line: u32) {
        for kind in classify_heading(value) {
            self.pending.push(PendingViolation { kind, line });
        }
    }
}

fn resolve_findings(
    path: &str,
    source: &str,
    pending: &[PendingViolation],
) -> Result<Vec<Finding>, LintError> {
    let lines: Vec<&str> = source.lines().collect();
    let mut findings = Vec::new();
    let mut seen = BTreeSet::new();
    for item in pending {
        if !seen.insert((item.line, item.kind)) {
            continue;
        }
        let line_text = lines
            .get(usize::try_from(item.line.saturating_sub(1)).unwrap_or(0))
            .copied()
            .unwrap_or("");
        if suppression::reason(line_text, SUPPRESSION_TOKEN)?.is_some() {
            continue;
        }
        findings.push(Finding::new(path, item.line, item.kind.message()));
    }
    Ok(findings)
}

fn line_number(span: proc_macro2::Span) -> u32 {
    u32::try_from(span.start().line).unwrap_or(1)
}

fn string_literal(expr: &Expr) -> Option<String> {
    match expr {
        Expr::Lit(lit) => match &lit.lit {
            Lit::Str(string) => Some(string.value()),
            _ => None,
        },
        Expr::Reference(reference) => string_literal(&reference.expr),
        Expr::Paren(paren) => string_literal(&paren.expr),
        Expr::Group(group) => string_literal(&group.expr),
        _ => None,
    }
}

fn first_string_literal(expr: Option<&Expr>) -> Option<String> {
    expr.and_then(string_literal)
}

fn is_regex_constructor(func: &Expr) -> bool {
    let Expr::Path(path) = func else {
        return false;
    };
    let segments: Vec<String> = path
        .path
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect();
    let names: Vec<&str> = segments.iter().map(String::as_str).collect();
    matches!(
        names.as_slice(),
        ["Regex" | "RegexBuilder", "new"] | ["regex", "Regex" | "RegexBuilder", "new"]
    ) || (names.last() == Some(&"new")
        && names
            .iter()
            .rev()
            .nth(1)
            .is_some_and(|name| *name == "Regex" || *name == "RegexBuilder"))
}

fn pat_ident(pat: &Pat) -> Option<String> {
    match pat {
        Pat::Ident(ident) => Some(ident.ident.to_string()),
        Pat::Reference(reference) => pat_ident(&reference.pat),
        Pat::Paren(paren) => pat_ident(&paren.pat),
        _ => None,
    }
}

fn iter_mentions_lifecycle_prefixes(expr: &Expr) -> bool {
    match expr {
        Expr::Path(path) => path
            .path
            .segments
            .iter()
            .any(|segment| segment.ident.to_string().contains("LIFECYCLE_PREFIXES")),
        Expr::Reference(reference) => iter_mentions_lifecycle_prefixes(&reference.expr),
        Expr::Unary(unary) => iter_mentions_lifecycle_prefixes(&unary.expr),
        Expr::Field(field) => match &field.member {
            Member::Named(ident) => ident.to_string().contains("LIFECYCLE_PREFIXES"),
            Member::Unnamed(_) => false,
        },
        Expr::MethodCall(method) if method.method == "iter" || method.method == "into_iter" => {
            iter_mentions_lifecycle_prefixes(&method.receiver)
        }
        Expr::Paren(paren) => iter_mentions_lifecycle_prefixes(&paren.expr),
        _ => false,
    }
}

fn loop_body_strips_prefix(node: &ExprForLoop, loop_variable: &str) -> bool {
    let mut detector = StripDetector {
        loop_variable: loop_variable.to_owned(),
        found: false,
    };
    detector.visit_expr_for_loop(node);
    detector.found
}

struct StripDetector {
    loop_variable: String,
    found: bool,
}

impl<'ast> Visit<'ast> for StripDetector {
    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        if node.method == "starts_with"
            && node
                .args
                .first()
                .is_some_and(|argument| expr_is_ident(argument, &self.loop_variable))
        {
            self.found = true;
        }
        if node.method == "len" && expr_is_ident(&node.receiver, &self.loop_variable) {
            self.found = true;
        }
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if let Expr::Path(path) = &*node.func
            && path
                .path
                .segments
                .last()
                .is_some_and(|segment| segment.ident == "len")
            && node
                .args
                .first()
                .is_some_and(|argument| expr_is_ident(argument, &self.loop_variable))
        {
            self.found = true;
        }
        visit::visit_expr_call(self, node);
    }
}

fn expr_is_ident(expr: &Expr, name: &str) -> bool {
    match expr {
        Expr::Path(path) => path.path.is_ident(name),
        Expr::Reference(reference) => expr_is_ident(&reference.expr, name),
        Expr::Paren(paren) => expr_is_ident(&paren.expr, name),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::{HEADING_OWNERS, REVIEW_OWNER, SharedConventionRegexRule, TITLE_OWNER};
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
    fn detects_guideline_and_invariant_heading_regex_new() {
        let fixture = repository_with(&[
            (
                "crates/demo/src/guideline.rs",
                "fn compile() {\n    let _ = regex::Regex::new(r\"^###\\\\s+(G-[A-Za-z0-9-]+-\\\\d+):\\\\s*(.+?)\\\\s*$\").unwrap();\n}\n",
            ),
            (
                "crates/demo/src/invariant.rs",
                "fn compile() {\n    let _ = regex::Regex::new(r\"^#{1,6}\\\\s+(I-[A-Za-z0-9-]+-\\\\d+):\\\\s*(.+?)\\\\s*$\").unwrap();\n}\n",
            ),
        ]);
        let findings = SharedConventionRegexRule
            .check(&fixture.repository)
            .expect("check");
        let messages: Vec<_> = findings.findings().iter().map(ToString::to_string).collect();
        assert!(
            messages
                .iter()
                .any(|message| message.contains("GUIDELINE_HEADING_RE")),
            "{messages:?}"
        );
        assert!(
            messages
                .iter()
                .any(|message| message.contains("INVARIANT_HEADING_RE")),
            "{messages:?}"
        );
    }

    #[test]
    fn detects_module_bug_selector_and_lifecycle_strip() {
        let fixture = repository_with(&[(
            "crates/demo/src/lib.rs",
            "const DEFAULT_SEARCH: &str = \"[BUG] in:title\";\nconst LIFECYCLE_PREFIXES: &[&str] = &[\"[DONE] \"];\nfn strip(title: &str) -> &str {\n    for prefix in LIFECYCLE_PREFIXES {\n        if title.starts_with(prefix) {\n            return &title[prefix.len()..];\n        }\n    }\n    title\n}\n",
        )]);
        let findings = SharedConventionRegexRule
            .check(&fixture.repository)
            .expect("check");
        let messages: Vec<_> = findings.findings().iter().map(ToString::to_string).collect();
        assert!(
            messages
                .iter()
                .any(|message| message.contains("bug-title-selector")),
            "{messages:?}"
        );
        assert!(
            messages
                .iter()
                .any(|message| message.contains("lifecycle-prefix-strip-loop")),
            "{messages:?}"
        );
    }

    #[test]
    fn owners_and_shared_imports_are_clean() {
        let fixture = repository_with(&[
            (
                HEADING_OWNERS[0],
                "fn compile() {\n    let _ = regex::Regex::new(r\"^###\\\\s+(G-[A-Za-z0-9-]+-\\\\d+):\\\\s*(.+?)\\\\s*$\").unwrap();\n}\n",
            ),
            (
                TITLE_OWNER,
                "const DEFAULT_SEARCH: &str = \"[BUG] in:title\";\nconst LIFECYCLE_PREFIXES: &[&str] = &[\"[DONE] \"];\nfn strip(title: &str) -> &str {\n    for prefix in LIFECYCLE_PREFIXES {\n        if title.starts_with(prefix) {\n            return &title[prefix.len()..];\n        }\n    }\n    title\n}\n",
            ),
            (
                REVIEW_OWNER,
                "fn compile() {\n    let _ = regex::Regex::new(r\"(?ms)^### (?:FINDING|OOS)_[0-9]+:.*?(?=^### |\\\\Z)\").unwrap();\n}\n",
            ),
            (
                "crates/demo/src/lib.rs",
                "use larch_issue::title_match::BUG_PREFIX;\nconst SEARCH: &str = \"clean\";\n",
            ),
        ]);
        assert!(
            SharedConventionRegexRule
                .check(&fixture.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }

    #[test]
    fn suppression_requires_reason_and_false_positives_stay_clean() {
        let suppressed = repository_with(&[(
            "crates/demo/src/lib.rs",
            "const DEFAULT_SEARCH: &str = \"[BUG] in:title\"; // lint-shared-convention-regex: ok fixture\n",
        )]);
        assert!(
            SharedConventionRegexRule
                .check(&suppressed.repository)
                .expect("check")
                .findings()
                .is_empty()
        );

        let missing = repository_with(&[(
            "crates/demo/src/lib.rs",
            "const DEFAULT_SEARCH: &str = \"[BUG] in:title\"; // lint-shared-convention-regex: ok\n",
        )]);
        assert!(
            SharedConventionRegexRule
                .check(&missing.repository)
                .expect_err("missing reason")
                .to_string()
                .contains("lacks a reason")
        );

        let clean = repository_with(&[(
            "crates/demo/src/lib.rs",
            "fn compile(title: &str) -> bool {\n    let _ = regex::Regex::new(r\"^\\\\| (FINDING_[0-9]+) \\\\|\").unwrap();\n    title.starts_with(\"[BUG]\")\n}\n",
        )]);
        assert!(
            SharedConventionRegexRule
                .check(&clean.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }

    #[test]
    fn detects_reviewer_item_heading_shapes() {
        let fixture = repository_with(&[(
            "crates/demo/src/lib.rs",
            "fn compile() {\n    let _ = regex::Regex::new(r\"(?ms)^### (?:FINDING|OOS)_[0-9]+:.*?(?=^### |\\\\Z)\").unwrap();\n}\n",
        )]);
        let findings = SharedConventionRegexRule
            .check(&fixture.repository)
            .expect("check");
        assert_eq!(findings.findings().len(), 1);
        assert!(
            findings.findings()[0]
                .to_string()
                .contains("reviewer-item-heading-regex")
        );
    }
}
