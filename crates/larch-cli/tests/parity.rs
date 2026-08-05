#[path = "support/parity.rs"]
mod parity_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};
use tempfile::TempDir;

#[derive(Clone, Copy)]
struct CleanInstallCase {
    id: &'static str,
    domain: &'static str,
    verb: &'static str,
}

impl CleanInstallCase {
    const fn new(id: &'static str, domain: &'static str, verb: &'static str) -> Self {
        Self { id, domain, verb }
    }

    fn arguments(self) -> &'static [&'static str] {
        match self.id {
            "clean-install-kv-get" => &["--key", "MISSING", "--default", "clean-install"],
            "clean-install-session-read-key" => &[
                "--file",
                "/larch-clean-install-read-key-missing",
                "--key",
                "KEY",
                "--default",
                "clean-install",
            ],
            "clean-install-session-read-keys" => &[
                "--file",
                "/larch-clean-install-read-keys-missing",
                "--key",
                "KEY=clean-install",
            ],
            "clean-install-session-cleanup-tmpdir" => {
                &["--dir", "/tmp/larch-clean-install-session-missing"]
            }
            // The verb rejects every argument, so a clean dispatch carries none.
            "clean-install-session-require-plugin-root" => &[],
            "clean-install-session-resolve-implement-tmpdir" => {
                &["--cwd", "/larch-clean-install-clone-missing"]
            }
            "clean-install-session-validate-design-tmpdir" => {
                &["/tmp/larch-clean-install-design-tmpdir-missing"]
            }
            _ => &["--help"],
        }
    }
}

const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[
    CleanInstallCase::new(
        "clean-install-agent-parse-codex-usage",
        "agent",
        "parse-codex-usage",
    ),
    CleanInstallCase::new("clean-install-kv-get", "kv", "get"),
    CleanInstallCase::new(
        "clean-install-session-cleanup-tmpdir",
        "session",
        "cleanup-tmpdir",
    ),
    CleanInstallCase::new("clean-install-session-read-key", "session", "read-key"),
    CleanInstallCase::new("clean-install-session-read-keys", "session", "read-keys"),
    CleanInstallCase::new(
        "clean-install-session-kill-background-processes",
        "session",
        "kill-background-processes",
    ),
    CleanInstallCase::new(
        "clean-install-session-require-plugin-root",
        "session",
        "require-plugin-root",
    ),
    CleanInstallCase::new(
        "clean-install-session-resolve-implement-tmpdir",
        "session",
        "resolve-implement-tmpdir",
    ),
    CleanInstallCase::new(
        "clean-install-session-validate-design-tmpdir",
        "session",
        "validate-design-tmpdir",
    ),
    CleanInstallCase::new("clean-install-ci-timing-harness", "ci-timing", "harness"),
    CleanInstallCase::new("clean-install-ci-timing-jobs", "ci-timing", "jobs"),
    CleanInstallCase::new("clean-install-ci-timing-pytest", "ci-timing", "pytest"),
    CleanInstallCase::new("clean-install-test-shard-pack", "test-shard", "pack"),
    CleanInstallCase::new(
        "clean-install-test-shard-read-makefile",
        "test-shard",
        "read-makefile",
    ),
    CleanInstallCase::new(
        "clean-install-test-shard-write-makefile",
        "test-shard",
        "write-makefile",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-baseline",
        "dirty-tree",
        "baseline",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-checkpoint",
        "dirty-tree",
        "checkpoint",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-scope-check",
        "dirty-tree",
        "scope-check",
    ),
    CleanInstallCase::new(
        "clean-install-dirty-tree-scope-marker",
        "dirty-tree",
        "scope-marker",
    ),
    CleanInstallCase::new("clean-install-gh-remote-repo", "gh", "remote-repo"),
    CleanInstallCase::new("clean-install-gh-resolve-repo", "gh", "resolve-repo"),
    CleanInstallCase::new("clean-install-gh-run-logs", "gh", "run-logs"),
    CleanInstallCase::new("clean-install-gh-workflow-path", "gh", "workflow-path"),
    CleanInstallCase::new("clean-install-git-amend-add", "git", "amend-add"),
    CleanInstallCase::new("clean-install-git-branch-info", "git", "branch-info"),
    CleanInstallCase::new(
        "clean-install-git-check-main-sync",
        "git",
        "check-main-sync",
    ),
    CleanInstallCase::new(
        "clean-install-git-check-phantom-dirty",
        "git",
        "check-phantom-dirty",
    ),
    CleanInstallCase::new(
        "clean-install-git-check-remote-branch",
        "git",
        "check-remote-branch",
    ),
    CleanInstallCase::new("clean-install-git-checkout-ours", "git", "checkout-ours"),
    CleanInstallCase::new("clean-install-git-clean-tree", "git", "clean-tree"),
    CleanInstallCase::new("clean-install-git-commit", "git", "commit"),
    CleanInstallCase::new("clean-install-git-conflict-files", "git", "conflict-files"),
    CleanInstallCase::new("clean-install-git-count-commits", "git", "count-commits"),
    CleanInstallCase::new("clean-install-git-current-branch", "git", "current-branch"),
    CleanInstallCase::new("clean-install-git-phantom-probe", "git", "phantom-probe"),
    CleanInstallCase::new("clean-install-git-rebase-abort", "git", "rebase-abort"),
    CleanInstallCase::new("clean-install-git-rebase-skip", "git", "rebase-skip"),
    CleanInstallCase::new("clean-install-git-show-stage", "git", "show-stage"),
    CleanInstallCase::new(
        "clean-install-git-snapshot-untracked",
        "git",
        "snapshot-untracked",
    ),
    CleanInstallCase::new("clean-install-git-stage", "git", "stage"),
    CleanInstallCase::new(
        "clean-install-git-sync-local-main",
        "git",
        "sync-local-main",
    ),
    CleanInstallCase::new(
        "clean-install-plugin-read-version",
        "plugin",
        "read-version",
    ),
    CleanInstallCase::new("clean-install-object-store-gcs", "object-store", "gcs"),
    CleanInstallCase::new("clean-install-push-branch", "push", "branch"),
    CleanInstallCase::new(
        "clean-install-push-checkpoint-probe",
        "push",
        "checkpoint-probe",
    ),
    CleanInstallCase::new("clean-install-push-force", "push", "force"),
    CleanInstallCase::new("clean-install-push-rebase", "push", "rebase"),
    CleanInstallCase::new(
        "clean-install-release-asset-candidate",
        "release",
        "asset-candidate",
    ),
    CleanInstallCase::new(
        "clean-install-release-classify-bump",
        "release",
        "classify-bump",
    ),
    CleanInstallCase::new(
        "clean-install-release-collect-assets",
        "release",
        "collect-assets",
    ),
    CleanInstallCase::new(
        "clean-install-release-package-asset",
        "release",
        "package-asset",
    ),
    CleanInstallCase::new(
        "clean-install-release-plugin-runtime",
        "release",
        "plugin-runtime",
    ),
    CleanInstallCase::new("clean-install-release-prepare", "release", "prepare"),
    CleanInstallCase::new(
        "clean-install-release-set-version",
        "release",
        "set-version",
    ),
    CleanInstallCase::new(
        "clean-install-release-validate-assets",
        "release",
        "validate-assets",
    ),
    CleanInstallCase::new(
        "clean-install-upgrade-larch-release-step7-root",
        "upgrade-larch",
        "release-step7-root",
    ),
    CleanInstallCase::new("clean-install-upgrade-larch-run", "upgrade-larch", "run"),
    CleanInstallCase::new(
        "clean-install-upgrade-larch-sparse-dirs",
        "upgrade-larch",
        "sparse-dirs",
    ),
];

#[test]
fn release_publication_commands_are_exposed_by_the_rust_binary() {
    for command in ["finish", "promote", "promote-latest"] {
        let output = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["release", command, "--help"])
            .output()
            .unwrap_or_else(|error| panic!("launch release {command}: {error}"));

        assert!(
            output.status.success(),
            "release {command} --help failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            String::from_utf8_lossy(&output.stdout)
                .contains(&format!("Usage: larch release {command}")),
            "release {command} did not enter the Rust CLI"
        );
    }
}

#[test]
fn representative_python_and_rust_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let compiled_rust_fixture = compile_rust_fixture(&fixture_directory);
    let rust_fixture = compiled_rust_fixture.path().join("reference-command");
    let python_fixture = fixture_directory.join("reference_command.py");
    let golden_directory = fixture_directory.join("goldens");

    let cases = [
        ParityCase {
            name: "clean",
            python: Program::new(&python)
                .args([path_text(&python_fixture), "clean", "{sandbox}"])
                .env("FIXTURE_TIMESTAMP", "2026-07-18T20:00:00.123Z"),
            rust: Program::new(&rust_fixture)
                .args(["clean", "{sandbox}"])
                .env("FIXTURE_TIMESTAMP", "2026-07-18T20:00:01Z"),
            seed_files: vec![SeedFile::text("input/seed.txt", "fixture\n")],
            side_effect_records: vec![PathBuf::from("effects.ndjson")],
            normalization: vec![
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        },
        ParityCase {
            name: "usage-error",
            python: Program::new(&python).args([path_text(&python_fixture)]),
            rust: Program::new(&rust_fixture),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "malformed-input",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "malformed",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["malformed", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "environmental-failure",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "environment",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["environment", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "service-isolation",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "isolation",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["isolation", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        },
    ];

    for case in cases {
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct SessionKvFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    stdin: Option<&'static [u8]>,
    seed: Option<(&'static str, &'static str)>,
    normalize_root: bool,
}

impl SessionKvFixture {
    fn build(self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let rust_command = match self.command {
            "kv-get" => ["kv", "get"],
            "read-key" => ["session", "read-key"],
            "read-keys" => ["session", "read-keys"],
            command => panic!("unknown session parity command: {command}"),
        };
        let mut python = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.command))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust = Program::new(rust).args(
            rust_command
                .into_iter()
                .chain(self.arguments.iter().copied()),
        );
        if let Some(input) = self.stdin {
            python = python.stdin(input);
            rust = rust.stdin(input);
        }
        ParityCase {
            name: self.name,
            python,
            rust,
            seed_files: self
                .seed
                .map(|(path, contents)| SeedFile::text(path, contents))
                .into_iter()
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self
                .normalize_root
                .then_some(NormalizationRule::SandboxRoot)
                .into_iter()
                .collect(),
        }
    }
}

#[test]
fn session_kv_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("session_kv_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");
    let cases = [
        SessionKvFixture {
            name: "kv-stdin-bytes",
            command: "kv-get",
            arguments: &["--key", "KEY", "--match", "last-non-empty"],
            stdin: Some(b"KEY=first\nKEY=\xff\nKEY=\n"),
            seed: None,
            normalize_root: false,
        },
        SessionKvFixture {
            name: "kv-file-cr-strip",
            command: "kv-get",
            arguments: &[
                "--file",
                "{sandbox}/values.env",
                "--key",
                "KEY",
                "--match",
                "last",
                "--cr-strip",
                "strip",
            ],
            stdin: None,
            seed: Some(("values.env", "KEY=first\r\nKEY=\rvalue\r\r\n")),
            normalize_root: false,
        },
        SessionKvFixture {
            name: "kv-usage-error",
            command: "kv-get",
            arguments: &[],
            stdin: None,
            seed: None,
            normalize_root: false,
        },
        SessionKvFixture {
            name: "session-read-key-first",
            command: "read-key",
            arguments: &["--file", "{sandbox}/session.env", "--key", "KEY"],
            stdin: None,
            seed: Some(("session.env", "IGNORED=value\u{85}KEY=first\nKEY=last\n")),
            normalize_root: false,
        },
        SessionKvFixture {
            name: "session-read-key-cr-error",
            command: "read-key",
            arguments: &[
                "--file",
                "{sandbox}/session.env",
                "--key",
                "KEY",
                "--default",
                "fallback",
            ],
            stdin: None,
            seed: Some(("session.env", "KEY=value\r\n")),
            normalize_root: true,
        },
        SessionKvFixture {
            name: "session-read-keys",
            command: "read-keys",
            arguments: &[
                "--file",
                "{sandbox}/session.env",
                "--key",
                "A",
                "--key",
                "B=default",
                "--key",
                "MISSING=fallback",
            ],
            stdin: None,
            seed: Some(("session.env", "A=first\nA=last\nB=\n")),
            normalize_root: false,
        },
    ];

    for fixture in cases {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct SessionLifecycleFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    environment: &'static [(&'static str, &'static str)],
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl SessionLifecycleFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.command))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust_program = Program::new(rust).args(
            ["session", self.command]
                .into_iter()
                .chain(self.arguments.iter().copied()),
        );
        for (key, value) in self.environment {
            python_program = python_program.env(key, value);
            rust_program = rust_program.env(key, value);
        }
        ParityCase {
            name: self.name,
            python: python_program,
            rust: rust_program,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: self.normalization.to_vec(),
        }
    }
}

/// Environment shared by every lifecycle case that needs an expanded plugin root.
const PLUGIN_ROOT_ENVIRONMENT: &[(&str, &str)] = &[("CLAUDE_PLUGIN_ROOT", "{sandbox}")];
const SANDBOX_ONLY: &[NormalizationRule] = &[NormalizationRule::SandboxRoot];
const CLEANUP_NORMALIZATION: &[NormalizationRule] = &[
    NormalizationRule::SandboxRoot,
    NormalizationRule::Rfc3339Utc,
    NormalizationRule::ProcessIdentity,
];
/// One implement session bound to the clone and identity the match case queries.
const IMPLEMENT_KEEPALIVE: &str = "CLONE_PATH=/clone/for/parity\nSESSION_ID=S1\n";
/// A sibling session in the same root bound to a different identity.
const OTHER_KEEPALIVE: &str = "CLONE_PATH=/clone/for/parity\nSESSION_ID=S2\n";

const SESSION_LIFECYCLE_CASES: &[SessionLifecycleFixture] = &[
    SessionLifecycleFixture {
        name: "session-require-plugin-root-expanded",
        command: "require-plugin-root",
        arguments: &[],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-require-plugin-root-empty",
        command: "require-plugin-root",
        arguments: &[],
        environment: &[("CLAUDE_PLUGIN_ROOT", "")],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-require-plugin-root-unexpanded",
        command: "require-plugin-root",
        arguments: &[],
        environment: &[("CLAUDE_PLUGIN_ROOT", "${CLAUDE_PLUGIN_ROOT}")],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-require-plugin-root-unrecognized",
        command: "require-plugin-root",
        arguments: &["--bogus"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-missing-path",
        command: "validate-design-tmpdir",
        arguments: &[],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-allowed",
        command: "validate-design-tmpdir",
        arguments: &["{sandbox}/.tmp/claude-design-parity"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[(".tmp/claude-design-parity/.keep", "")],
        normalization: SANDBOX_ONLY,
    },
    // Not a sandbox path: every platform's temporary root is itself allowlisted,
    // on Linux through `/tmp` and on macOS through `TMPDIR`. `/usr` is a real
    // directory on both, so the rejected path resolves to itself either way.
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-outside-allowlist",
        command: "validate-design-tmpdir",
        arguments: &["/usr/larch-parity-not-a-session"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-relative",
        command: "validate-design-tmpdir",
        arguments: &["relative/design"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-dot-segment",
        command: "validate-design-tmpdir",
        arguments: &["{sandbox}/.tmp/../escape"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-validate-design-tmpdir-unrecognized",
        command: "validate-design-tmpdir",
        arguments: &["--bogus"],
        environment: PLUGIN_ROOT_ENVIRONMENT,
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-missing-output",
        command: "write-id",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-unrecognized",
        command: "write-id",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-outside-allowed-root",
        command: "write-id",
        arguments: &["--output", "/larch-parity-not-a-session/session-id"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-write-id-preserves-existing-identity",
        command: "write-id",
        arguments: &["--output", "{sandbox}/.tmp/claude-design-parity/session-id"],
        environment: &[],
        seeds: &[(".tmp/claude-design-parity/session-id", "PRESERVED\n")],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-missing-dir",
        command: "cleanup-tmpdir",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-outside-allowed-root",
        command: "cleanup-tmpdir",
        arguments: &["--dir", "/larch-parity-not-a-session"],
        environment: &[],
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-unrecognized",
        command: "cleanup-tmpdir",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-removes-session",
        command: "cleanup-tmpdir",
        arguments: &["--dir", "{sandbox}/.tmp/claude-design-parity"],
        environment: &[],
        seeds: &[
            (".tmp/claude-design-parity/nested/artifact.txt", "payload\n"),
            (".tmp/claude-design-parity/session-id", "ID\n"),
        ],
        normalization: CLEANUP_NORMALIZATION,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-cache-sessions-root",
        command: "cleanup-tmpdir",
        arguments: &[
            "--dir",
            "{sandbox}/xdg/larch/sessions/claude-implement-cache",
        ],
        environment: &[("XDG_CACHE_HOME", "{sandbox}/xdg")],
        seeds: &[(
            "xdg/larch/sessions/claude-implement-cache/artifact.txt",
            "payload\n",
        )],
        normalization: CLEANUP_NORMALIZATION,
    },
    SessionLifecycleFixture {
        name: "session-cleanup-tmpdir-missing-target",
        command: "cleanup-tmpdir",
        arguments: &["--dir", "{sandbox}/.tmp/claude-design-absent"],
        environment: &[],
        seeds: &[],
        normalization: CLEANUP_NORMALIZATION,
    },
    SessionLifecycleFixture {
        name: "session-resolve-implement-tmpdir-no-match",
        command: "resolve-implement-tmpdir",
        arguments: &["--cwd", "/clone/without/session"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionLifecycleFixture {
        name: "session-resolve-implement-tmpdir-session-bound",
        command: "resolve-implement-tmpdir",
        arguments: &["--cwd", "/clone/for/parity"],
        environment: &[("LARCH_TOKEN_SESSION_ID", "S1")],
        seeds: &[
            (
                ".home/.cache/larch/sessions/claude-implement-alpha/design-export/manifest.env",
                "MANIFEST=1\n",
            ),
            (
                ".home/.cache/larch/sessions/claude-implement-alpha/.larch-keepalive",
                IMPLEMENT_KEEPALIVE,
            ),
            (
                ".home/.cache/larch/sessions/claude-implement-beta/review-round-summary.md",
                "# round\n",
            ),
            (
                ".home/.cache/larch/sessions/claude-implement-beta/.larch-keepalive",
                OTHER_KEEPALIVE,
            ),
        ],
        normalization: SANDBOX_ONLY,
    },
    SessionLifecycleFixture {
        name: "session-resolve-implement-tmpdir-unrecognized",
        command: "resolve-implement-tmpdir",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
];

#[test]
fn session_lifecycle_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("session_lifecycle_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in SESSION_LIFECYCLE_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn hung_command_fails_at_the_case_boundary() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let compiled_rust_fixture = compile_rust_fixture(&fixture_directory);
    let case = ParityCase {
        name: "timeout",
        python: Program::new(&python)
            .args(["-c", "import time; time.sleep(2)"])
            .timeout(Duration::from_millis(50)),
        rust: Program::new(compiled_rust_fixture.path().join("reference-command")),
        seed_files: Vec::new(),
        side_effect_records: Vec::new(),
        normalization: Vec::new(),
    };

    let error = assert_case(&case, Path::new("unused.golden.json"))
        .expect_err("hung command should fail the harness");

    assert!(error.contains("timed out after 50ms"));
}

#[test]
fn rust_owned_selector_matrix_enters_through_verified_clean_install_script() {
    let fixture = clean_install_fixture();
    for case in CLEAN_INSTALL_CASES {
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, *case, None);
        assert!(
            output.status.success(),
            "{} failed: {}",
            case.id,
            String::from_utf8_lossy(&output.stderr)
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        let lines: Vec<&str> = events.lines().collect();
        let expected_dispatch = clean_install_dispatch(*case);
        assert_eq!(lines.first(), Some(&"--version"), "{}", case.id);
        assert_eq!(lines.get(1), Some(&"bootstrap self-check"), "{}", case.id);
        assert_eq!(
            lines.get(2),
            Some(&expected_dispatch.as_str()),
            "{}",
            case.id
        );
        assert_eq!(lines.len(), 3, "{}", case.id);
        assert!(!fixture.root.join("bin/larch").exists(), "{}", case.id);
    }
}

#[test]
fn clean_install_validation_failures_precede_selector_dispatch() {
    let fixture = clean_install_fixture();
    let case = CLEAN_INSTALL_CASES[0];
    for failure in ["version", "target", "bootstrap"] {
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, case, Some(failure));
        assert!(
            !output.status.success(),
            "{failure} unexpectedly dispatched"
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        assert!(
            !events
                .lines()
                .any(|line| line == clean_install_dispatch(case)),
            "{failure} reached selector dispatch"
        );
    }
}

struct CleanInstallFixture {
    _temporary: TempDir,
    root: PathBuf,
    wrapper: PathBuf,
    events: PathBuf,
    binary: PathBuf,
}

fn clean_install_fixture() -> CleanInstallFixture {
    let temporary = tempfile::tempdir().expect("clean-install tempdir");
    let temporary_root = fs::canonicalize(temporary.path()).expect("canonical clean-install root");
    let root = temporary_root.join("plugin");
    let scripts = root.join("scripts");
    let manifest_directory = root.join(".claude-plugin");
    fs::create_dir_all(&scripts).expect("create clean-install scripts directory");
    fs::create_dir_all(&manifest_directory).expect("create clean-install manifest directory");
    fs::copy(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../scripts/larch.sh"),
        scripts.join("larch.sh"),
    )
    .expect("copy verified bootstrap script");
    fs::write(
        manifest_directory.join("plugin.json"),
        format!(
            "{{\n  \"name\": \"larch\",\n  \"version\": \"{}\"\n}}\n",
            env!("CARGO_PKG_VERSION")
        ),
    )
    .expect("write clean-install plugin manifest");
    let wrapper = temporary_root.join("verified-larch");
    fs::write(
        &wrapper,
        r#"#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$CLEAN_INSTALL_EVENTS"
case "$CLEAN_INSTALL_FAILURE" in
  version)
    if [ "$1" = --version ]; then printf '%s\n' 'larch 0.0.0'; exit 0; fi
    ;;
  target)
    if [ "$1" = bootstrap ]; then
      if [ "$2" = self-check ]; then
        "$REAL_LARCH" "$@" | sed 's/"target":"[^"]*"/"target":"wrong-target"/'
        exit "$?"
      fi
    fi
    ;;
  bootstrap)
    if [ "$1" = bootstrap ]; then
      if [ "$2" = self-check ]; then exit 9; fi
    fi
    ;;
esac
exec "$REAL_LARCH" "$@"
"#,
    )
    .expect("write verified binary wrapper");
    #[cfg(unix)]
    {
        let mut permissions = fs::metadata(&wrapper)
            .expect("read wrapper metadata")
            .permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&wrapper, permissions).expect("make wrapper executable");
    }
    CleanInstallFixture {
        events: temporary_root.join("events.log"),
        binary: PathBuf::from(env!("CARGO_BIN_EXE_larch")),
        _temporary: temporary,
        root,
        wrapper,
    }
}

/// Render the argv line the verified bootstrap wrapper records for one case.
///
/// An argument-free verb records only its domain and verb, with no trailing
/// separator, because the wrapper logs the shell's joined argument list.
fn clean_install_dispatch(case: CleanInstallCase) -> String {
    std::iter::once(case.domain)
        .chain(std::iter::once(case.verb))
        .chain(case.arguments().iter().copied())
        .collect::<Vec<_>>()
        .join(" ")
}

fn run_clean_install_case(
    fixture: &CleanInstallFixture,
    case: CleanInstallCase,
    failure: Option<&str>,
) -> std::process::Output {
    let mut command = Command::new("/bin/bash");
    command
        .arg(fixture.root.join("scripts/larch.sh"))
        .args([case.domain, case.verb])
        .args(case.arguments())
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        .env("CLEAN_INSTALL_FAILURE", failure.unwrap_or_default());
    command.output().expect("run clean-install selector")
}

fn fixture_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../fixtures/rust-parity")
}

fn compile_rust_fixture(fixture_directory: &Path) -> TempDir {
    let output = tempfile::tempdir().expect("compiled Rust fixture tempdir");
    let executable = output.path().join("reference-command");
    let rustc = env::var_os("RUSTC").map_or_else(|| find_executable("rustc"), PathBuf::from);
    let status = Command::new(&rustc)
        .args(["--edition=2024", "-o"])
        .arg(&executable)
        .arg(fixture_directory.join("reference_command.rs"))
        .status()
        .unwrap_or_else(|error| panic!("launch {}: {error}", rustc.display()));
    assert!(status.success(), "Rust parity fixture failed to compile");
    output
}

fn find_executable(name: &str) -> PathBuf {
    let path = env::var_os("PATH").expect("test process should have PATH");
    env::split_paths(&path)
        .map(|directory| {
            if directory.is_absolute() {
                directory.join(name)
            } else {
                env::current_dir()
                    .expect("test process should have a current directory")
                    .join(directory)
                    .join(name)
            }
        })
        .find(|candidate| candidate.is_file())
        .unwrap_or_else(|| panic!("required executable not found on PATH: {name}"))
}

fn path_text(path: &Path) -> &str {
    path.to_str().expect("fixture path should be UTF-8")
}
