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
        repository.write(
            "crates/larch-lint/migration-ledger/fixture.toml",
            b"rule = \"fixture\"\n",
        );
        repository.write(
            "crates/larch-lint/migration-ledger/kv-codec.toml",
            b"rule = \"kv-codec\"\n",
        );
        repository.write(
            "crates/larch-lint/migration-ledger/result-env-key-parity.toml",
            b"rule = \"result-env-key-parity\"\n",
        );
        repository.write(
            "crates/larch-lint/migration-ledger/tempfile-dir.toml",
            b"rule = \"tempfile-dir\"\n",
        );
        repository.write(
            "crates/larch-lint/migration-ledger/tmpdir-arg-env-fallback.toml",
            b"rule = \"tmpdir-arg-env-fallback\"\n",
        );
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

fn run_git<const N: usize>(root: &Path, args: [&str; N]) {
    let status = Command::new("git")
        .arg("-C")
        .arg(root)
        .args(args)
        .status()
        .expect("run git fixture command");
    assert!(status.success(), "git fixture command failed: {status}");
}
