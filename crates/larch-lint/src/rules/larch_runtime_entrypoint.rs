//! Require production Rust-backed commands to enter through `scripts/larch.sh`.

use std::{path::Path, sync::LazyLock};

use regex::Regex;

use crate::{Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "larch-runtime-entrypoint";
const DESCRIPTION: &str = "Reject production callers that bypass scripts/larch.sh";
const MESSAGE: &str =
    "direct bin/larch production entrypoint; invoke ${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh";
const ALLOWED_PATHS: [&str; 2] = [
    "scripts/larch.sh",
    "python/larch/core/upgrade_larch.py",
];

static DIRECT_BINARY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:^|[^A-Za-z0-9_.-])bin/larch(?:$|[^A-Za-z0-9_.-])")
        .expect("direct larch binary expression is valid")
});
static SEGMENTED_PATH: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"[\"']bin[\"']\s*(?:/|,)\s*[\"']larch[\"']"#)
        .expect("segmented larch binary path expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/larch-runtime-entrypoint.toml",
);

#[derive(Debug)]
pub struct LarchRuntimeEntrypointRule;

pub static RULE: LarchRuntimeEntrypointRule = LarchRuntimeEntrypointRule;

impl Rule for LarchRuntimeEntrypointRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository.paths() {
            let path_text = path.as_str();
            if !is_production_surface(path_text) || ALLOWED_PATHS.contains(&path_text) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            for (index, line) in source.lines().enumerate() {
                if DIRECT_BINARY.is_match(line) || SEGMENTED_PATH.is_match(line) {
                    findings.push(Finding::new(
                        path_text,
                        u32::try_from(index + 1).unwrap_or(u32::MAX),
                        MESSAGE,
                    ));
                }
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

pub(super) fn is_production_surface(path: &str) -> bool {
    if path.starts_with("python/larch/") {
        return has_extension(path, "py");
    }
    if path.starts_with("skills/")
        || path.starts_with(".claude/skills/")
        || path.starts_with("agents/")
    {
        return has_extension(path, "md") || has_extension(path, "sh");
    }
    if path.starts_with("hooks/") {
        return has_extension(path, "json") || has_extension(path, "sh");
    }
    if path.starts_with("scripts/") {
        let name = path.rsplit('/').next().unwrap_or(path);
        return has_extension(path, "sh") && !name.starts_with("test-");
    }
    false
}

fn has_extension(path: &str, expected: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension.eq_ignore_ascii_case(expected))
}

crate::register_rule!(METADATA, RULE);

#[cfg(test)]
mod tests {
    use super::is_production_surface;

    #[test]
    fn scopes_only_runtime_sources() {
        assert!(is_production_surface("python/larch/core/example.py"));
        assert!(is_production_surface("skills/example/SKILL.md"));
        assert!(is_production_surface("agents/example.md"));
        assert!(is_production_surface("hooks/hooks.json"));
        assert!(is_production_surface("scripts/example.sh"));
        assert!(!is_production_surface("python/tests/test_example.py"));
        assert!(!is_production_surface("docs/example.md"));
        assert!(!is_production_surface("plugin/agents/example.md"));
        assert!(!is_production_surface("scripts/test-example.sh"));
    }
}
