//! Require the shipped skill inventory to match both documentation catalogs.
//!
//! # Crate survey (issue #7606)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Repository inventory | `walkdir`, shared `Repository` / `PathSelector` | Reuse the shared tracked-and-untracked repository snapshot and glob selector so symlink and non-UTF-8 failures stay fail-closed. |
//! | Markdown structure | workspace `pulldown-cmark`, handwritten heading parser | Reuse `MarkdownDocument` and its CommonMark event stream for the detailed catalog headings. |
//! | README HTML entries | `scraper`, workspace `regex` | Use the existing lightweight regex engine for the deliberately narrow legacy HTML-table grammar; a DOM dependency would not improve the exact catalog predicate. |

use std::{collections::BTreeSet, sync::LazyLock};

use pulldown_cmark::{Event, HeadingLevel, Tag, TagEnd};
use regex::Regex;

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::MarkdownDocument,
};

const NAME: &str = "skill-documentation";
const DESCRIPTION: &str = "Require public, alias, and private skills in both documentation catalogs";
const README_PATH: &str = "README.md";
const SKILLS_DOCUMENT_PATH: &str = "docs/skills.md";
const SKILL_PATTERNS: &[&str] = &["skills/*/SKILL.md", ".claude/skills/*/SKILL.md"];

static HTML_TABLE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?is)<table\b[^>]*>(?P<body>.*?)</table>")
        .expect("skill documentation HTML table expression is valid")
});
static HTML_ENTRY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)<td>\s*<a\s+href=\"docs/skills\.md#(?P<href>[a-z0-9-]+)\">\s*<code>/(?P<code>[a-z0-9-]+)</code>\s*</a>\s*</td>"#)
        .expect("skill documentation HTML entry expression is valid")
});
static MARKDOWN_ENTRY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^\|\s*\[`/(?P<label>[a-z0-9-]+)`\]\(docs/skills\.md#(?P<target>[a-z0-9-]+)\)")
        .expect("skill documentation Markdown entry expression is valid")
});
static SKILL_NAME: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[a-z0-9-]+$").expect("skill name expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/skill-documentation.toml",
);

#[derive(Debug)]
pub struct SkillDocumentationRule;

pub static RULE: SkillDocumentationRule = SkillDocumentationRule;

impl Rule for SkillDocumentationRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let defined = defined_skills(repository)?;
        let summary = summary_skills(repository)?;
        let detailed = detailed_skills(repository)?;
        let mut findings = Vec::new();
        extend_findings(
            &mut findings,
            &defined,
            &summary,
            README_PATH,
            "missing summary-table entry for",
        );
        extend_findings(
            &mut findings,
            &defined,
            &detailed,
            SKILLS_DOCUMENT_PATH,
            "missing detailed skill heading for",
        );
        extend_findings(
            &mut findings,
            &summary,
            &defined,
            README_PATH,
            "summary-table entry has no matching skill definition for",
        );
        extend_findings(
            &mut findings,
            &detailed,
            &defined,
            SKILLS_DOCUMENT_PATH,
            "detailed skill heading has no matching skill definition for",
        );
        extend_findings(
            &mut findings,
            &summary,
            &detailed,
            README_PATH,
            "summary-table entry has no matching detailed skill heading for",
        );
        extend_findings(
            &mut findings,
            &detailed,
            &summary,
            SKILLS_DOCUMENT_PATH,
            "detailed skill heading has no matching summary-table entry for",
        );
        Ok(RuleOutput::from_findings(findings))
    }
}

fn extend_findings(
    findings: &mut Vec<Finding>,
    left: &BTreeSet<String>,
    right: &BTreeSet<String>,
    path: &str,
    message: &str,
) {
    for name in left.difference(right) {
        findings.push(Finding::new(path, 1, format!("{message} /{name}")));
    }
}

fn defined_skills(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let selector = PathSelector::new(SKILL_PATTERNS, &[])?;
    let mut names = BTreeSet::new();
    for path in selector.select(repository) {
        let Some(name) = path.as_str().split('/').nth_back(1) else {
            return Err(LintError::new(format!("{}: malformed skill definition path", path.as_str())));
        };
        let _ = names.insert(name.to_owned());
    }
    Ok(names)
}

fn summary_skills(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let readme = required_document(repository, README_PATH)?;
    let mut names = BTreeSet::new();
    for table in HTML_TABLE.captures_iter(&readme) {
        for entry in HTML_ENTRY.captures_iter(&table["body"]) {
            if entry["href"] == entry["code"] {
                let _ = names.insert(entry["href"].to_owned());
            }
        }
    }
    for entry in MARKDOWN_ENTRY.captures_iter(&readme) {
        if entry["label"] == entry["target"] {
            let _ = names.insert(entry["label"].to_owned());
        }
    }
    Ok(names)
}

fn detailed_skills(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let document = required_document(repository, SKILLS_DOCUMENT_PATH)?;
    let mut names = BTreeSet::new();
    let mut heading = None;
    for event in MarkdownDocument::new(&document).parser() {
        match event {
            Event::Start(Tag::Heading { level: HeadingLevel::H3, .. }) => {
                heading = Some(Heading::Empty);
            }
            Event::Code(value) if heading.is_some() => heading = Some(match heading {
                Some(Heading::Empty) => Heading::Name(value.into_string()),
                Some(Heading::Name(_) | Heading::Invalid) | None => Heading::Invalid,
            }),
            Event::End(TagEnd::Heading(HeadingLevel::H3)) => {
                if let Some(Heading::Name(value)) = heading.take()
                    && let Some(name) = value.strip_prefix('/')
                    && SKILL_NAME.is_match(name)
                {
                    let _ = names.insert(name.to_owned());
                }
            }
            Event::End(TagEnd::Heading(_)) => heading = None,
            Event::Text(_) | Event::Html(_) | Event::InlineHtml(_) if heading.is_some() => {
                heading = Some(Heading::Invalid);
            }
            _ => {}
        }
    }
    Ok(names)
}

enum Heading {
    Empty,
    Invalid,
    Name(String),
}

fn required_document(repository: &Repository, path: &str) -> Result<String, LintError> {
    let document = RepoPath::from_trusted(path);
    if repository.paths().binary_search(&document).is_err() {
        return Err(LintError::new(format!("{path}: required documentation file is missing")));
    }
    repository.read_utf8(&document)
}

crate::register_rule!(METADATA, RULE);
