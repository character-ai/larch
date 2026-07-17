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
    copy_tree(
        repository,
        &manifest_dir.join("migration-ledger"),
        "crates/larch-lint/migration-ledger",
    );
    let policy = manifest_dir.join("policy");
    if policy.is_dir() {
        copy_tree(repository, &policy, "crates/larch-lint/policy");
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
