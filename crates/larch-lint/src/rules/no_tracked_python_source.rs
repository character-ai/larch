//! Fail when the tracked tree contains any Python source file.
//!
//! Umbrella #8926 finished retiring the Python runtime: `python/` is deleted
//! and `git ls-files '*.py'` is empty. The six `*-python-free` rules and
//! `python_boundary.rs` remain as domain tripwires, but the per-rule `.py`
//! scanners that classified `python/larch/` paths were removed once no Python
//! source remained (leaf #9034). This rule is the single replacement tripwire:
//! it fails when any tracked path ends in `.py`, so a reintroduced Python
//! source is caught even where a former domain scanner no longer looks.

use crate::{Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "no-tracked-python-source";
const DESCRIPTION: &str = "Fail when any tracked path is a Python source file";
const MESSAGE: &str = "tracked Python source is not permitted after the Rust migration";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/no-tracked-python-source.toml",
);

#[derive(Debug)]
pub struct NoTrackedPythonSourceRule;

pub static RULE: NoTrackedPythonSourceRule = NoTrackedPythonSourceRule;

crate::register_rule!(METADATA, RULE);

impl Rule for NoTrackedPythonSourceRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let findings = repository
            .paths()
            .iter()
            .filter(|path| is_python_source(path.as_str()))
            .map(|path| Finding::new(path.as_str(), 1, MESSAGE))
            .collect();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn is_python_source(path: &str) -> bool {
    path.rsplit('/')
        .next()
        .unwrap_or(path)
        .rsplit_once('.')
        .is_some_and(|(_, extension)| extension.eq_ignore_ascii_case("py"))
}

#[cfg(test)]
mod tests {
    use super::{MESSAGE, NoTrackedPythonSourceRule};
    use crate::{Git, LintError, Repository, Rule};
    use std::path::{Path, PathBuf};

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

    fn repository_with(files: &[(&str, &str)]) -> (tempfile::TempDir, Repository) {
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
        (temporary, repository)
    }

    #[test]
    fn fails_on_a_tracked_python_source() {
        let (_temporary, repository) = repository_with(&[("scripts/x.py", "print('x')\n")]);
        let output = NoTrackedPythonSourceRule.check(&repository).expect("check");
        assert_eq!(output.findings().len(), 1);
        let rendered = output.findings()[0].to_string();
        assert!(rendered.starts_with("scripts/x.py:1:"), "{rendered}");
        assert!(rendered.contains(MESSAGE), "{rendered}");
    }

    #[test]
    fn passes_when_no_python_source_is_tracked() {
        let (_temporary, repository) = repository_with(&[
            ("crates/larch-lint/src/lib.rs", "// rust\n"),
            ("scripts/larch.sh", "#!/usr/bin/env bash\n"),
            ("docs/notes.md", "# notes\n"),
        ]);
        let output = NoTrackedPythonSourceRule.check(&repository).expect("check");
        assert!(output.findings().is_empty(), "{:?}", output.findings());
    }
}
