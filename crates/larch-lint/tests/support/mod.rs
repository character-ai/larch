use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

pub struct TempRepo {
    directory: TempDir,
}

impl TempRepo {
    pub fn new() -> Self {
        let directory = tempfile::tempdir().expect("tempdir");
        run_git(directory.path(), ["init", "--quiet"]);
        let repository = Self { directory };
        seed_tracked_tree(&repository);
        repository
    }

    pub fn path(&self) -> &Path {
        self.directory.path()
    }

    pub fn write(&self, relative: &str, contents: &[u8]) {
        let path = self.path().join(relative);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create fixture parent");
        }
        fs::write(path, contents).expect("write fixture");
    }

    pub fn commit_all(&self) {
        run_git(self.path(), ["add", "--all"]);
        run_git(
            self.path(),
            [
                "-c",
                "user.email=fixture@example.invalid",
                "-c",
                "user.name=Fixture",
                "commit",
                "--quiet",
                "-m",
                "fixture",
            ],
        );
    }

    pub fn command_from(cwd: impl Into<PathBuf>) -> AssertCommand {
        let mut command = AssertCommand::cargo_bin("larch-lint").expect("larch-lint binary");
        command.current_dir(cwd.into());
        command
    }
}

fn seed_tracked_tree(repository: &TempRepo) {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    for (source_name, destination_prefix) in [
        ("migration-ledger", "crates/larch-lint/migration-ledger"),
        ("policy", "crates/larch-lint/policy"),
        ("config", "crates/larch-lint/config"),
    ] {
        let source = manifest_dir.join(source_name);
        if source.is_dir() {
            copy_tree(repository, &source, destination_prefix);
        }
    }
    // Fixture repos use an empty guideline baseline and a short guidelines
    // document so shared CLI tests stay independent of live debt.
    repository.write(
        "crates/larch-lint/config/guideline-no-exception-baseline.json",
        b"[]\n",
    );
    repository.write(
        "crates/larch-lint/config/bg-wait-allowlist.txt",
        b"# no retained exceptions\n",
    );
    repository.write(
        "ARCHITECTURAL_GUIDELINES.md",
        b"### G-Fixture-1: Fixture guidance\n- Why: fixture body.\n- Deviate when: when a fixture needs an exception.\n",
    );
    repository.write(
        "skills/shared/topology.tsv",
        b"fixture\tfixture authority\tcomposition\tskills/shared/topology-authority.md\n",
    );
    repository.write(
        "skills/shared/topology-authority.md",
        b"fixture authority\n",
    );
    repository.write(
        "README.md",
        b"<table>\n<tr><td><a href=\"docs/skills.md#design\"><code>/design</code></a></td></tr>\n<tr><td><a href=\"docs/skills.md#review\"><code>/review</code></a></td></tr>\n</table>\n",
    );
    repository.write("docs/skills.md", b"### `/design`\n\n### `/review`\n");
    repository.write(
        "scripts/lint-readability-preamble.tsv",
        b"__metadata__\tmetadata-min-count\t0\t\nskills/design/SKILL.md\tskill-exempt\t0\tfixture\t\nskills/review/SKILL.md\tskill-exempt\t0\tfixture\t\n",
    );
    repository.write("python/migrated-scripts.tsv", b"# retired paths\n");
    for path in [
        "skills/shared/reviewer-templates.md",
        "agents/code-reviewer.md",
        "agents/reviewer-structure.md",
        "agents/reviewer-correctness.md",
        "agents/reviewer-testing.md",
        "agents/reviewer-security.md",
        "agents/reviewer-edge-cases.md",
        "agents/reviewer-plan-fidelity.md",
        "agents/reviewer-code-robustness.md",
        "docs/review-agents.md",
    ] {
        repository.write(
            path,
            b"**MANDATORY: READ ENTIRE FILE before composing fixture text: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**\n`code-quality` / `risk-integration` / `correctness` / `architecture` / `security`\n",
        );
    }
    for path in [
        "skills/review/SKILL.md",
        "python/larch/rendering/rendering.py",
        "skills/design/SKILL.md",
    ] {
        repository.write(
            path,
            b"code-quality / risk-integration / correctness / architecture / security\n",
        );
    }
}

fn copy_tree(repository: &TempRepo, source_dir: &Path, destination_prefix: &str) {
    let mut entries: Vec<_> = fs::read_dir(source_dir)
        .unwrap_or_else(|error| panic!("read {}: {error}", source_dir.display()))
        .map(|entry| entry.expect("directory entry"))
        .collect();
    entries.sort_by_key(fs::DirEntry::file_name);
    for entry in entries {
        let metadata = entry.metadata().expect("entry metadata");
        if !metadata.is_file() {
            continue;
        }
        let name = entry.file_name();
        let name = name.to_string_lossy();
        let contents = fs::read(entry.path()).expect("read seeded file");
        repository.write(&format!("{destination_prefix}/{name}"), &contents);
    }
}

fn run_git<const N: usize>(root: &Path, args: [&str; N]) {
    let status = Command::new("git")
        .arg("-C")
        .arg(root)
        .args(args)
        .status()
        .expect("run git fixture command");
    assert!(status.success(), "git fixture command failed: {status}");
}
