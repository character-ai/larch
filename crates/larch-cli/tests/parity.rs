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

use larch_core::{ClassifyTextInput, classify_text};
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

    /// Exit status a clean dispatch of this case produces.
    ///
    /// A verb whose only offline-deterministic invocation is a refusal still
    /// proves the dispatch reached it; the case pins that refusal's code rather
    /// than reaching the network or mutating a repository to reach `0`.
    fn expected_exit(self) -> i32 {
        match self.id {
            "clean-install-issue-state" => 1,
            "clean-install-admission-preflight" => 3,
            "clean-install-session-check-live-mutation-auth" => 5,
            "clean-install-run-log-prepare-terminal-snapshot" => 2,
            _ => 0,
        }
    }

    fn arguments(self) -> &'static [&'static str] {
        if let Some(arguments) = phase_detail_clean_install_arguments(self.id) {
            return arguments;
        }
        if let Some(arguments) = admission_clean_install_arguments(self.id) {
            return arguments;
        }
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
            // `require-plugin-root` rejects every argument, and the three
            // progress stdin readers see an empty payload, so all four dispatch
            // with no arguments at all.
            "clean-install-session-require-plugin-root"
            | "clean-install-progress-statusline"
            | "clean-install-progress-session-reset"
            | "clean-install-progress-install-statusline" => &[],
            "clean-install-session-resolve-implement-tmpdir" => {
                &["--cwd", "/larch-clean-install-clone-missing"]
            }
            "clean-install-session-validate-design-tmpdir" => {
                &["/tmp/larch-clean-install-design-tmpdir-missing"]
            }
            id if id.starts_with("clean-install-run-log-") => run_log_arguments(id),
            "clean-install-progress-activate" | "clean-install-progress-deactivate" => &[
                "--repo-root",
                "/larch-clean-install-clone-missing",
                "--run-id",
                "clean-install",
            ],
            "clean-install-progress-clear" => {
                &["--repo-root", "/larch-clean-install-clone-missing"]
            }
            "clean-install-progress-note" => &[
                "--repo-root",
                "/larch-clean-install-clone-missing",
                "--skill",
                "clean",
                "--step",
                "install",
                "dispatch",
            ],
            // Every writer below runs against the fixture's seeded session
            // directory, so a clean install proves the whole route, not just
            // the argument rejection in front of it.
            "clean-install-session-write-env" => &[
                "--output",
                "%SESSION%/session-env.sh",
                "--repo-unavailable",
                "false",
            ],
            "clean-install-session-write-design-env" => &[
                "--output",
                "%SESSION%/source-env.sh",
                "--design-tmpdir",
                "%SESSION%",
                "--session-id",
                "clean-install",
            ],
            "clean-install-session-write-implement-env" => &[
                "--claude-pid",
                "4242",
                "--implement-tmpdir",
                "%SESSION%",
                "--cwd",
                "%SESSION%",
            ],
            "clean-install-session-clear-implement-pointer" => &["--claude-pid", "4242"],
            "clean-install-session-persist-run-flags" => {
                &["--implement-tmpdir", "%SESSION%", "--no-issues", "false"]
            }
            "clean-install-session-restore-finalize-state" => &["--implement-tmpdir", "%SESSION%"],
            "clean-install-session-write-run-params" => &["--output", "%SESSION%/run-params.json"],
            "clean-install-session-resolve-trusted-design-env" => &[
                "--session-env-path",
                "%HOME%/.cache/larch/sessions/current-design-env-4242.sh",
                "--claude-pid",
                "4242",
            ],
            _ => &["--help"],
        }
    }
}

/// Arguments for the `/implement` admission, gate, and blocker verbs.
///
/// A free helper for the same reason `phase_detail_clean_install_arguments` is
/// one: it keeps `arguments` inside the per-function line cap.
fn admission_clean_install_arguments(id: &str) -> Option<&'static [&'static str]> {
    match id {
        "clean-install-admission-preflight" => Some(&["--larch-clean-install-probe"]),
        "clean-install-session-check-live-mutation-auth" => Some(&[
            "--context-file",
            "/larch-clean-install-context-missing",
            "--run-id",
            "clean-install",
            "--trusted-root",
            "/larch-clean-install-root-missing",
        ]),
        "clean-install-session-entry-gate" => Some(&[
            "--mode",
            "implement",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "clean-install",
        ]),
        // `all-open` needs no arguments to reach its empty-result path.
        "clean-install-blocker-all-open" => Some(&[]),
        // Neither issue verb has a `--help` action. `state` proves dispatch
        // through its argument refusal, and `info` through the empty value it
        // reports for a field it does not serve; neither reaches the network.
        "clean-install-issue-state" => Some(&["--issue"]),
        "clean-install-issue-info" => Some(&["--issue", "1", "--field", "title"]),
        _ => None,
    }
}

fn phase_detail_clean_install_arguments(id: &str) -> Option<&'static [&'static str]> {
    match id {
        "clean-install-progress-render-phase-detail" => Some(&[
            "--rounds-root",
            "/larch-clean-install-rounds-missing",
            "--no-gantt",
        ]),
        "clean-install-progress-write-design-round-meta"
        | "clean-install-progress-write-implement-round-meta" => {
            Some(&["--round-dir", "/larch-clean-install-round-missing"])
        }
        _ => None,
    }
}

/// Argument sets for every Rust-owned `run-log` clean-install case.
///
/// The entry-write verbs run against the fixture's seeded session inputs, so a
/// clean install proves each whole route rather than only the argument
/// rejection in front of it. Split out of `CleanInstallCase::arguments` so that
/// matcher stays readable.
#[rustfmt::skip]
fn run_log_arguments(id: &str) -> &'static [&'static str] {
    match id {
        "clean-install-run-log-manifest" => &[
            "--log-root", "manifest-logs", "--skill", "clean",
            "--run-id", "clean-install", "--field", "steps_ran.install=true",
        ],
        "clean-install-run-log-validate-run-id" => &["--run-id", "clean-install"],
        "clean-install-run-log-init" => &[
            "--log-root", "%SESSION%/larch-logs", "--skill", "clean",
            "--run-id", "clean-install",
        ],
        "clean-install-run-log-write" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--batch",
            "review-context",
            "--input-file",
            "%SESSION%/payload.md",
        ],
        "clean-install-run-log-write-round" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--round",
            "1",
            "--source-dir",
            "%SESSION%/round-src",
        ],
        "clean-install-run-log-append" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--batch",
            "execution-issues",
            "--record-file",
            "%SESSION%/record.ndjson",
        ],
        "clean-install-run-log-exists" => &[
            "--log-root",
            "%SESSION%/larch-logs",
            "--skill",
            "clean",
            "--run-id",
            "clean-install",
            "--batch",
            "run-statistics",
        ],
        "clean-install-run-log-append-entry" => &[
            "--log",
            "%SESSION%/execution-issues.md",
            "--category",
            "Warnings",
            "--entry",
            "clean-install",
        ],
        "clean-install-run-log-append-failure" => &[
            "--log",
            "%SESSION%/execution-issues.md",
            "--site",
            "clean",
            "--tool",
            "install",
            "--exit-code",
            "0",
            "--category",
            "Warnings",
            "--output-file",
            "%SESSION%/payload.md",
        ],
        "clean-install-run-log-verify-completeness" => &["%SESSION%/verify-run"],
        "clean-install-run-log-publish-breadcrumbs" => &[
            "--source-dir",
            "%SESSION%/breadcrumbs",
            "--dest-dir",
            "%SESSION%/larch-logs/clean/clean-install/breadcrumbs",
        ],
        "clean-install-run-log-checkpoint" => &[],
        "clean-install-run-log-capture-transcript" => &[
            "--log-root", "%SESSION%/larch-logs", "--skill", "implement",
            "--run-id", "clean-install", "--source-file", "%SESSION%/missing-source.env",
        ],
        "clean-install-run-log-refresh" => &["--implement-tmpdir", "%SESSION%"],
        "clean-install-run-log-prepare-terminal-snapshot" => &[
            "--implement-tmpdir", "/larch-clean-install-session-missing",
            "--run-id", "clean-install",
        ],
        _ => &["--help"],
    }
}

#[rustfmt::skip]
const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[
    CleanInstallCase::new("clean-install-admission-fork-env", "admission", "fork-env"),
    CleanInstallCase::new("clean-install-admission-gate", "admission", "gate"),
    CleanInstallCase::new(
        "clean-install-admission-preflight",
        "admission",
        "preflight",
    ),
    CleanInstallCase::new("clean-install-blocker-all-open", "blocker", "all-open"),
    CleanInstallCase::new("clean-install-issue-info", "issue", "info"),
    CleanInstallCase::new("clean-install-issue-state", "issue", "state"),
    CleanInstallCase::new(
        "clean-install-session-check-live-mutation-auth",
        "session",
        "check-live-mutation-auth",
    ),
    CleanInstallCase::new("clean-install-session-entry-gate", "session", "entry-gate"),
    CleanInstallCase::new(
        "clean-install-agent-classify-diff",
        "agent",
        "classify-diff",
    ),
    CleanInstallCase::new(
        "clean-install-agent-check-reviewers",
        "agent",
        "check-reviewers",
    ),
    CleanInstallCase::new(
        "clean-install-agent-compose-collector-failure-log",
        "agent",
        "compose-collector-failure-log",
    ),
    CleanInstallCase::new(
        "clean-install-agent-cursor-auth-preflight",
        "agent",
        "cursor-auth-preflight",
    ),
    CleanInstallCase::new(
        "clean-install-agent-cursor-wrap-prompt",
        "agent",
        "cursor-wrap-prompt",
    ),
    CleanInstallCase::new(
        "clean-install-agent-degraded-tools-gate",
        "agent",
        "degraded-tools-gate",
    ),
    CleanInstallCase::new(
        "clean-install-agent-external-tool-registry",
        "agent",
        "external-tool-registry",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-review",
        "agent",
        "launch-review",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-ci",
        "agent",
        "launch-codex-ci",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-cursor-ci",
        "agent",
        "launch-cursor-ci",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-ci",
        "agent",
        "launch-claude-ci",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-implement",
        "agent",
        "launch-codex-implement",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-cursor-implement",
        "agent",
        "launch-cursor-implement",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-lint-fix",
        "agent",
        "launch-claude-lint-fix",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-review-fix",
        "agent",
        "launch-claude-review-fix",
    ),
    CleanInstallCase::new(
        "clean-install-agent-dispatch-waterfall",
        "agent",
        "dispatch-waterfall",
    ),
    CleanInstallCase::new("clean-install-agent-model-args", "agent", "model-args"),
    CleanInstallCase::new(
        "clean-install-agent-read-claude-model",
        "agent",
        "read-claude-model",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-review",
        "agent",
        "launch-claude-review",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-subprocess",
        "agent",
        "launch-claude-subprocess",
    ),
    CleanInstallCase::new(
        "clean-install-agent-resolve-model-pins",
        "agent",
        "resolve-model-pins",
    ),
    CleanInstallCase::new(
        "clean-install-external-defaults-docs",
        "external-defaults",
        "docs",
    ),
    CleanInstallCase::new(
        "clean-install-external-defaults-resolve-vendor",
        "external-defaults",
        "resolve-vendor",
    ),
    CleanInstallCase::new(
        "clean-install-external-defaults-role",
        "external-defaults",
        "role",
    ),
    CleanInstallCase::new(
        "clean-install-slack-issue-announce",
        "slack",
        "issue-announce",
    ),
    CleanInstallCase::new(
        "clean-install-agent-gather-branch-context",
        "agent",
        "gather-branch-context",
    ),
    CleanInstallCase::new(
        "clean-install-agent-parse-codex-usage",
        "agent",
        "parse-codex-usage",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-claude-drafter",
        "agent",
        "launch-claude-drafter",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-drafter",
        "agent",
        "launch-codex-drafter",
    ),
    CleanInstallCase::new(
        "clean-install-agent-launch-codex-exec",
        "agent",
        "launch-codex-exec",
    ),
    CleanInstallCase::new(
        "clean-install-agent-run-negotiation-round",
        "agent",
        "run-negotiation-round",
    ),
    CleanInstallCase::new(
        "clean-install-agent-run-external-agent",
        "agent",
        "run-external-agent",
    ),
    CleanInstallCase::new(
        "clean-install-agent-wait-reviewers",
        "agent",
        "wait-reviewers",
    ),
    CleanInstallCase::new("clean-install-lint-gitleaks", "lint", "gitleaks"),
    CleanInstallCase::new("clean-install-bgjob-adapt", "bgjob", "adapt"),
    CleanInstallCase::new("clean-install-bgjob-reap", "bgjob", "reap"),
    CleanInstallCase::new("clean-install-bgjob-start", "bgjob", "start"),
    CleanInstallCase::new("clean-install-bgjob-status", "bgjob", "status"),
    CleanInstallCase::new("clean-install-bgjob-wait", "bgjob", "wait"),
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
    CleanInstallCase::new("clean-install-session-write-env", "session", "write-env"),
    CleanInstallCase::new(
        "clean-install-session-write-design-env",
        "session",
        "write-design-env",
    ),
    CleanInstallCase::new(
        "clean-install-session-write-implement-env",
        "session",
        "write-implement-env",
    ),
    CleanInstallCase::new(
        "clean-install-session-clear-implement-pointer",
        "session",
        "clear-implement-pointer",
    ),
    CleanInstallCase::new(
        "clean-install-session-persist-run-flags",
        "session",
        "persist-run-flags",
    ),
    CleanInstallCase::new(
        "clean-install-session-write-run-params",
        "session",
        "write-run-params",
    ),
    CleanInstallCase::new(
        "clean-install-session-restore-finalize-state",
        "session",
        "restore-finalize-state",
    ),
    CleanInstallCase::new(
        "clean-install-session-resolve-trusted-design-env",
        "session",
        "resolve-trusted-design-env",
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
    CleanInstallCase::new("clean-install-run-log-archive", "run-log", "archive"),
    CleanInstallCase::new("clean-install-run-log-manifest", "run-log", "manifest"),
    CleanInstallCase::new("clean-install-run-log-publish", "run-log", "publish"),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-cancel",
        "run-log",
        "lifecycle-cancel",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-early-return",
        "run-log",
        "lifecycle-early-return",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-failure",
        "run-log",
        "lifecycle-failure",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-finalize",
        "run-log",
        "lifecycle-finalize",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-lifecycle-start",
        "run-log",
        "lifecycle-start",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-materialize",
        "run-log",
        "materialize",
    ),
    CleanInstallCase::new("clean-install-run-log-sync", "run-log", "sync"),
    CleanInstallCase::new(
        "clean-install-run-log-validate-run-id",
        "run-log",
        "validate-run-id",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-chat-print",
        "stall-recovery",
        "chat-print",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-clear-stall",
        "stall-recovery",
        "clear-stall",
    ),
    CleanInstallCase::new("clean-install-stall-recovery-classify", "stall-recovery", "classify"),
    CleanInstallCase::new("clean-install-stall-recovery-init-attempts", "stall-recovery", "init-attempts"),
    CleanInstallCase::new("clean-install-stall-recovery-normalize-file-failure-report-env", "stall-recovery", "normalize-file-failure-report-env"),
    CleanInstallCase::new("clean-install-stall-recovery-normalize-issue-env", "stall-recovery", "normalize-issue-env"),
    CleanInstallCase::new("clean-install-stall-recovery-normalize-outcome", "stall-recovery", "normalize-outcome"),
    CleanInstallCase::new("clean-install-stall-recovery-record-attempt", "stall-recovery", "record-attempt"),
    CleanInstallCase::new("clean-install-stall-recovery-record-escalation", "stall-recovery", "record-escalation"),
    CleanInstallCase::new("clean-install-stall-recovery-retry-policy", "stall-recovery", "retry-policy"),
    CleanInstallCase::new(
        "clean-install-stall-recovery-compose-report",
        "stall-recovery",
        "compose-report",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-dedup-tier-a-report",
        "stall-recovery",
        "dedup-tier-a-report",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-is-larch-dev-clone",
        "stall-recovery",
        "is-larch-dev-clone",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-populate-sensitive-corpus",
        "stall-recovery",
        "populate-sensitive-corpus",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-seed-terminal-state",
        "stall-recovery",
        "seed-terminal-state",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-validate-terminal-state",
        "stall-recovery",
        "validate-terminal-state",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-validate-tier-b-public-file",
        "stall-recovery",
        "validate-tier-b-public-file",
    ),
    CleanInstallCase::new(
        "clean-install-stall-recovery-validate-token",
        "stall-recovery",
        "validate-token",
    ),
    CleanInstallCase::new("clean-install-run-log-init", "run-log", "init"),
    CleanInstallCase::new("clean-install-run-log-write", "run-log", "write"),
    CleanInstallCase::new(
        "clean-install-run-log-write-round",
        "run-log",
        "write-round",
    ),
    CleanInstallCase::new("clean-install-run-log-append", "run-log", "append"),
    CleanInstallCase::new("clean-install-run-log-exists", "run-log", "exists"),
    CleanInstallCase::new(
        "clean-install-run-log-append-entry",
        "run-log",
        "append-entry",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-append-failure",
        "run-log",
        "append-failure",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-verify-completeness",
        "run-log",
        "verify-completeness",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-publish-breadcrumbs",
        "run-log",
        "publish-breadcrumbs",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-capture-transcript",
        "run-log",
        "capture-transcript",
    ),
    CleanInstallCase::new("clean-install-run-log-checkpoint", "run-log", "checkpoint"),
    CleanInstallCase::new(
        "clean-install-run-log-prepare-terminal-snapshot",
        "run-log",
        "prepare-terminal-snapshot",
    ),
    CleanInstallCase::new("clean-install-run-log-refresh", "run-log", "refresh"),
    CleanInstallCase::new("clean-install-progress-activate", "progress", "activate"),
    CleanInstallCase::new("clean-install-progress-clear", "progress", "clear"),
    CleanInstallCase::new(
        "clean-install-progress-deactivate",
        "progress",
        "deactivate",
    ),
    CleanInstallCase::new(
        "clean-install-progress-install-statusline",
        "progress",
        "install-statusline",
    ),
    CleanInstallCase::new("clean-install-progress-note", "progress", "note"),
    CleanInstallCase::new(
        "clean-install-progress-render-phase-detail",
        "progress",
        "render-phase-detail",
    ),
    CleanInstallCase::new(
        "clean-install-progress-session-reset",
        "progress",
        "session-reset",
    ),
    CleanInstallCase::new(
        "clean-install-progress-statusline",
        "progress",
        "statusline",
    ),
    CleanInstallCase::new(
        "clean-install-progress-write-design-round-meta",
        "progress",
        "write-design-round-meta",
    ),
    CleanInstallCase::new(
        "clean-install-progress-write-implement-round-meta",
        "progress",
        "write-implement-round-meta",
    ),
    CleanInstallCase::new(
        "clean-install-run-log-storage-preflight",
        "run-log",
        "storage-preflight",
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

struct StallRecoveryFixture {
    name: &'static str,
    verb: &'static str,
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
    environment: &'static [(&'static str, &'static str)],
}

impl StallRecoveryFixture {
    const fn new(
        name: &'static str,
        verb: &'static str,
        arguments: &'static [&'static str],
        seeds: &'static [(&'static str, &'static str)],
    ) -> Self {
        Self {
            name,
            verb,
            arguments,
            seeds,
            environment: &[],
        }
    }

    const fn with_environment(
        mut self,
        environment: &'static [(&'static str, &'static str)],
    ) -> Self {
        self.environment = environment;
        self
    }

    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.verb))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust = Program::new(rust).args(
            ["stall-recovery", self.verb]
                .into_iter()
                .chain(self.arguments.iter().copied()),
        );
        for (key, value) in self.environment {
            python = python.env(key, value);
            rust = rust.env(key, value);
        }
        ParityCase {
            name: self.name,
            python,
            rust,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        }
    }
}

const STALL_TERMINAL: &str = "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=approved\nSTALL_STEP=8a\nPHASE=ship-pr\nSITE=ship-pr\nTRIGGER=main-agent-required\nBAIL_REASON=review-required\nEXIT_CODE=4\nFAILURE_DETAIL_LOG=\nSOURCE_SCRIPT=ship-pr\n";
const STALL_TERMINAL_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--primary-state-file",
    "{sandbox}/terminal.env",
];
const STALL_PUBLIC_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--public-file",
    "{sandbox}/public.md",
    "--sensitive-corpus-file",
    "{sandbox}/stall-recovery-sensitive-corpus.env",
];
const STALL_DEV_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--working-tree-root",
    "{sandbox}",
];
const STALL_REPORT_ENVIRONMENT: &[(&str, &str)] = &[
    ("CLAUDE_PROJECT_DIR", "{sandbox}"),
    ("LARCH_STALL_RECOVERY_DRY_RUN", "1"),
];
const STALL_DRY_RUN_ENVIRONMENT: &[(&str, &str)] = &[("LARCH_STALL_RECOVERY_DRY_RUN", "1")];
const STALL_REPORT_COMPOSE_ARGS: &[&str] = &[
    "--implement-tmpdir",
    "{sandbox}",
    "--surface",
    "issue-input",
    "--report-kind",
    "terminal-failure",
];
const STALL_REPORT_COMPOSE_SEEDS: &[(&str, &str)] = &[
    ("skills/implement/SKILL.md", "fixture\n"),
    (
        "stall-recovery-classification.env",
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nBAIL_REASON=review-required\nRESUME_HINT=none\nEXIT_CODE=1\n",
    ),
    (
        "stall-recovery-attempts.env",
        "version=1\nattempt_count=0\n",
    ),
    (
        "stall-recovery-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe title\n\nProse.\n",
    ),
    ("session-env.sh", "LARCH_RUN_ID=run-1\nBRANCH_NAME=topic\n"),
];
const STALL_REPORT_CORPUS_ARGS: &[&str] = &["--implement-tmpdir", "{sandbox}"];
const STALL_REPORT_CORPUS_SEEDS: &[(&str, &str)] = &[
    ("stall-recovery-sensitive-corpus.env", "existing-token\n"),
    (
        "stall-recovery-classification.env",
        "FAILURE_CLASS=lint-failure\nSTALL_STEP=5\n",
    ),
    (
        "plan.txt",
        "https://client.example.test/private\nexample raw line\n",
    ),
];
const STALL_REPORT_CHAT_SEEDS: &[(&str, &str)] = &[
    (
        "stall-recovery-classification.env",
        "FAILURE_CLASS=lint-failure\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
    ),
    (
        "stall-recovery-attempts.env",
        "version=1\nattempt_count=0\n",
    ),
    (
        "stall-recovery-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe title\n\nProse.\n",
    ),
    (
        "stall-recovery-sensitive-corpus.env",
        "client-secret-value\n",
    ),
    (
        "stall-recovery-bounded-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe summary\n\nclient-secret-value\n",
    ),
];
#[rustfmt::skip]
const STALL_RECOVERY_CASES: &[StallRecoveryFixture] = &[
    StallRecoveryFixture::new(
        "stall-token-generic",
        "validate-token",
        &[
            "--profile",
            "generic",
            "--token-kind",
            "step",
            "--value",
            "step2b",
        ],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-token-raw-rejected",
        "validate-token",
        &["--token", "bad value"],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-token-implement-bail",
        "validate-token",
        &["--token-kind", "bail", "--token", "review-required"],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-terminal-valid",
        "validate-terminal-state",
        STALL_TERMINAL_ARGS,
        &[("terminal.env", STALL_TERMINAL)],
    ),
    StallRecoveryFixture::new(
        "stall-terminal-partial",
        "validate-terminal-state",
        STALL_TERMINAL_ARGS,
        &[(
            "terminal.env",
            "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\n",
        )],
    ),
    StallRecoveryFixture::new(
        "stall-seed-fresh",
        "seed-terminal-state",
        &["--implement-tmpdir", "{sandbox}"],
        &[],
    ),
    StallRecoveryFixture::new(
        "stall-seed-rewrite",
        "seed-terminal-state",
        &[
            "--implement-tmpdir",
            "{sandbox}",
            "--stall-step",
            "8a",
            "--phase",
            "ci-initial",
        ],
        &[("ship-pr-state.sh", "KEEP=yes\nSTALL_STEP=9\nPHASE=merge\n")],
    ),
    StallRecoveryFixture::new(
        "stall-clear",
        "clear-stall",
        &["--implement-tmpdir", "{sandbox}"],
        &[(
            "ship-pr-state.sh",
            "KEEP=yes\nSTALL_TRACKING=true\nSTALL_STEP=8\n",
        )],
    ),
    StallRecoveryFixture::new(
        "stall-public-valid",
        "validate-tier-b-public-file",
        STALL_PUBLIC_ARGS,
        &[
            ("public.md", "Sanitized report\n"),
            ("stall-recovery-sensitive-corpus.env", "secret-value\n"),
        ],
    ),
    StallRecoveryFixture::new(
        "stall-public-sensitive",
        "validate-tier-b-public-file",
        STALL_PUBLIC_ARGS,
        &[
            ("public.md", "Found secret-value\n"),
            ("stall-recovery-sensitive-corpus.env", "secret-value\n"),
        ],
    ),
    StallRecoveryFixture::new(
        "stall-dev-clone",
        "is-larch-dev-clone",
        STALL_DEV_ARGS,
        &[("skills/implement/SKILL.md", "fixture\n")],
    ),
    StallRecoveryFixture::new(
        "stall-dev-clone-forked",
        "is-larch-dev-clone",
        STALL_DEV_ARGS,
        &[
            ("skills/implement/SKILL.md", "fixture\n"),
            ("ship-pr-state.sh", "FORKED_TARGET=true\n"),
        ],
    ),
    StallRecoveryFixture::new(
        "stall-report-compose-tier-a",
        "compose-report",
        STALL_REPORT_COMPOSE_ARGS,
        STALL_REPORT_COMPOSE_SEEDS,
    )
    .with_environment(STALL_REPORT_ENVIRONMENT),
    StallRecoveryFixture::new(
        "stall-report-populate-sensitive-corpus",
        "populate-sensitive-corpus",
        STALL_REPORT_CORPUS_ARGS,
        STALL_REPORT_CORPUS_SEEDS,
    ),
    StallRecoveryFixture::new(
        "stall-report-chat-sensitive",
        "chat-print",
        STALL_REPORT_CORPUS_ARGS,
        STALL_REPORT_CHAT_SEEDS,
    ),
    StallRecoveryFixture::new(
        "stall-report-dedup-dry-run",
        "dedup-tier-a-report",
        STALL_REPORT_CORPUS_ARGS,
        &[],
    )
    .with_environment(STALL_DRY_RUN_ENVIRONMENT),
    StallRecoveryFixture::new("stall-classify-checks-signal", "classify", &["--implement-tmpdir", "{sandbox}", "--attempts-file", "{sandbox}/missing-attempts.env", "--bail-reason", "checks-child-failed", "--stall-step", "3", "--exit-code", "-15"], &[("ship-pr-state.sh", "STALL_TRACKING=true\nPHASE=checks\n")]),
    StallRecoveryFixture::new("stall-init-attempts", "init-attempts", &["--implement-tmpdir", "{sandbox}"], &[]),
    StallRecoveryFixture::new("stall-record-attempt", "record-attempt", &["--implement-tmpdir", "{sandbox}", "--class", "test-failure", "--signature", "sig-1", "--resume-hint", "step2-impl"], &[("stall-recovery-attempts.env", "version=1\r\ncreated_utc=2026-01-01T00:00:00+00:00\r\n")]),
    StallRecoveryFixture::new("stall-retry-policy", "retry-policy", &["--class", "transient-infra"], &[]),
    StallRecoveryFixture::new("stall-normalize-outcome", "normalize-outcome", &["--implement-tmpdir", "{sandbox}"], &[("ship-pr-state.sh", "STALL_TRACKING=false\nMERGE_RESULT=merged\nPR_NUMBER=42\n")]),
    StallRecoveryFixture::new("stall-normalize-issue", "normalize-issue-env", &["--implement-tmpdir", "{sandbox}", "--issue-stdout-file", "{sandbox}/issue.out", "--issue-exit-code", "0"], &[("issue.out", "ISSUES_FAILED=0\nISSUE_1_NUMBER=42\nISSUE_1_URL=https://github.com/o/r/issues/42\n")]),
    StallRecoveryFixture::new("stall-normalize-file-report", "normalize-file-failure-report-env", &["--implement-tmpdir", "{sandbox}", "--file-failure-report-env", "{sandbox}/file.env"], &[("file.env", "FILE_FAILURE_REPORT_STATUS=filed\nFILE_FAILURE_REPORT_URL=https://github.com/o/r/issues/42\n")]),
    StallRecoveryFixture::new("stall-record-escalation", "record-escalation", &["--implement-tmpdir", "{sandbox}", "--site", "step2", "--trigger", "step2-impl", "--step", "2", "--phase", "implementation", "--dispatcher", "codex", "--exit-code", "1"], &[]),
];

#[test]
#[rustfmt::skip]
fn every_classifier_branch_matches_the_frozen_python_table() {
    let python = find_executable("python3");
    let fixture = fixture_directory().join("stall_recovery_reference.py");
    for line in include_str!("../../../fixtures/rust-parity/stall-classifier-cases.tsv").lines().skip(1) {
        let [name, text, bail, step, detail, exit, implement] = line.split('\t').collect::<Vec<_>>().try_into().expect("seven columns");
        let detail = detail == "true";
        let implement = implement == "true";
        let output = Command::new(&python)
            .args([path_text(&fixture), "classify-text", "--text", text, "--bail", bail, "--step", step,
                "--detail-valid", if detail { "true" } else { "false" }, "--exit-code", exit,
                "--implement", if implement { "true" } else { "false" }])
            .output().expect("run frozen classifier");
        assert!(output.status.success(), "Python classifier failed for {name}");
        let result = classify_text(ClassifyTextInput { text, bail, step, detail_log_valid: detail, exit_code: exit, implement });
        let expected = format!("FAILURE_CLASS={}\nCLASSIFIED_HINT={}\nPATTERN={}\n", result.failure_class, result.resume_hint, result.pattern);
        assert_eq!(String::from_utf8(output.stdout).expect("UTF-8"), expected, "classifier parity case {name}");
    }
}

#[test]
fn stall_recovery_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("stall_recovery_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");
    for fixture in STALL_RECOVERY_CASES {
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

/// One `progress` verb compared against the frozen Python reference.
///
/// Every case pins `--repo-root` to a path that cannot exist, so the clone hash
/// and therefore every seeded and asserted cache path stay sandbox independent.
struct ProgressFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    stdin: Option<&'static str>,
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl ProgressFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python)
            .args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.command))
                    .chain(self.arguments.iter().copied()),
            )
            .env("LARCH_TEST_CACHE_HOME", PROGRESS_CACHE_HOME);
        let mut rust_program = Program::new(rust)
            .args(
                ["progress", self.command]
                    .into_iter()
                    .chain(self.arguments.iter().copied()),
            )
            .env("LARCH_TEST_CACHE_HOME", PROGRESS_CACHE_HOME);
        if let Some(input) = self.stdin {
            python_program = python_program.stdin(input.as_bytes());
            rust_program = rust_program.stdin(input.as_bytes());
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

const PROGRESS_CACHE_HOME: &str = "{sandbox}/cache";
/// A clone path that cannot exist, so its hash is identical in every sandbox.
const PROGRESS_CLONE: &str = "/larch-parity-clone";
/// `sha256("/larch-parity-clone")[:16]`, the clone directory both owners derive.
const PROGRESS_CLONE_DIR: &str = "cache/larch/progress/d8b96cde3cb3f56e";
const PROGRESS_POINTER: &str = "cache/larch/progress/d8b96cde3cb3f56e/current";
const PROGRESS_LOG: &str = "cache/larch/progress/d8b96cde3cb3f56e/run-1/breadcrumbs.log";
const PROGRESS_ACTIVE_SEED: &[(&str, &str)] = &[
    (PROGRESS_POINTER, "run-1\n"),
    (PROGRESS_LOG, "[design 1] first\n[implement 5] second\n"),
];
const STAMP_ONLY: &[NormalizationRule] = &[NormalizationRule::StatuslineStamp];
const STARTUP_PAYLOAD: &str =
    r#"{"workspace": {"current_dir": "/larch-parity-clone"}, "source": "startup"}"#;
const RESUME_PAYLOAD: &str =
    r#"{"workspace": {"current_dir": "/larch-parity-clone"}, "source": "resume"}"#;
const STATUSLINE_PAYLOAD: &str = r#"{"workspace": {"current_dir": "/larch-parity-clone"}}"#;

const PROGRESS_CASES: &[ProgressFixture] = &[
    ProgressFixture {
        name: "progress-activate",
        command: "activate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "run-1"],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-activate-missing-run-id",
        command: "activate",
        arguments: &["--repo-root", PROGRESS_CLONE],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-activate-reserved-run-id",
        command: "activate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "current"],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-active-run",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--skill",
            "implement",
            "--step",
            "5",
            "code",
            "review",
            "started",
        ],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-rejects-a-url",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--skill",
            "implement",
            "--step",
            "5",
            "see",
            "https://example.invalid/pr",
        ],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-missing-skill",
        command: "note",
        arguments: &["--repo-root", PROGRESS_CLONE, "--step", "5", "text"],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-explicit-run",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--run-id",
            "run-2",
            "--skill",
            "design",
            "--step",
            "3",
            "other",
            "run",
        ],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-note-without-an-active-pointer",
        command: "note",
        arguments: &[
            "--repo-root",
            PROGRESS_CLONE,
            "--skill",
            "design",
            "--step",
            "3",
            "no",
            "pointer",
        ],
        stdin: None,
        seeds: &[(PROGRESS_LOG, "[design 1] first\n")],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-deactivate-wrong-owner",
        command: "deactivate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "run-2"],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-deactivate-owner",
        command: "deactivate",
        arguments: &["--repo-root", PROGRESS_CLONE, "--run-id", "run-1"],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-clear",
        command: "clear",
        arguments: &["--repo-root", PROGRESS_CLONE],
        stdin: None,
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-clear-without-state",
        command: "clear",
        arguments: &["--repo-root", PROGRESS_CLONE],
        stdin: None,
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-active",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: STAMP_ONLY,
    },
    ProgressFixture {
        name: "progress-statusline-torn-log",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[
            (PROGRESS_POINTER, "run-1\n"),
            (
                PROGRESS_LOG,
                "[design 1] first\n[implement 5] partial without a newline",
            ),
        ],
        normalization: STAMP_ONLY,
    },
    ProgressFixture {
        name: "progress-statusline-non-breadcrumb-log",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[
            (PROGRESS_POINTER, "run-1\n"),
            (PROGRESS_LOG, "garbage without a marker\n"),
        ],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-missing-state",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-torn-pointer",
        command: "statusline",
        arguments: &[],
        stdin: Some(STATUSLINE_PAYLOAD),
        seeds: &[
            (PROGRESS_POINTER, "run"),
            (PROGRESS_LOG, "[design 1] first\n"),
        ],
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-statusline-empty-payload",
        command: "statusline",
        arguments: &[],
        stdin: Some(""),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-session-reset-startup",
        command: "session-reset",
        arguments: &[],
        stdin: Some(STARTUP_PAYLOAD),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
    ProgressFixture {
        name: "progress-session-reset-resume",
        command: "session-reset",
        arguments: &[],
        stdin: Some(RESUME_PAYLOAD),
        seeds: PROGRESS_ACTIVE_SEED,
        normalization: &[],
    },
];

#[test]
fn progress_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("progress_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in PROGRESS_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

struct PhaseDetailFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    seeds: &'static [(&'static str, &'static str)],
    environment: &'static [(&'static str, &'static str)],
}

impl PhaseDetailFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path, python_path: &str) -> ParityCase {
        let python = self.environment.iter().fold(
            Program::new(python)
                .args(
                    std::iter::once(path_text(fixture))
                        .chain(std::iter::once(self.command))
                        .chain(self.arguments.iter().copied()),
                )
                .env("PYTHONPATH", python_path),
            |program, (key, value)| program.env(key, value),
        );
        let rust = self.environment.iter().fold(
            Program::new(rust).args(
                ["progress", self.command]
                    .into_iter()
                    .chain(self.arguments.iter().copied()),
            ),
            |program, (key, value)| program.env(key, value),
        );
        ParityCase {
            name: self.name,
            python,
            rust,
            seed_files: self
                .seeds
                .iter()
                .map(|(path, contents)| SeedFile::text(path, contents))
                .collect(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        }
    }
}

const PHASE_DETAIL_CASES: &[PhaseDetailFixture] = &[
    PhaseDetailFixture {
        name: "progress-phase-detail-missing-rounds-root",
        command: "render-phase-detail",
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-no-gantt-explicit-value",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/rounds", "--no-gantt=unexpected"],
        seeds: &[("rounds/.keep", "")],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-help",
        command: "render-phase-detail",
        arguments: &["--help"],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-design-round-meta-missing-round-dir",
        command: "write-design-round-meta",
        arguments: &[],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta-help",
        command: "write-implement-round-meta",
        arguments: &["--help"],
        seeds: &[],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-no-rounds",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/rounds", "--no-gantt"],
        seeds: &[("rounds/.keep", "")],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-rendered-round",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/rounds",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--findings-file",
            "{sandbox}/findings.jsonl",
            "--no-gantt",
        ],
        seeds: &[
            (
                "rounds/round-1/round-meta.json",
                "{\n  \"tally\": {\"ACCEPTED_COUNT\": \"2\", \"REJECTED_COUNT\": \"1\", \"EXONERATED_COUNT\": \"0\", \"NEUTRAL_COUNT\": \"1\", \"OOS_PROPOSED_COUNT\": \"1\", \"OOS_ACCEPTED_COUNT\": \"1\", \"OOS_REJECTED_COUNT\": \"0\"},\n  \"summary\": {\"panel\": {\"total_slot_count\": 3}},\n  \"collector\": \"TOOL=codex\\nSTATUS=FAILED\\nREVIEWER_FILE=codex-specialist-arch-output.txt\"\n}\n",
            ),
            (
                "rounds/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"codex-specialist-arch-output.txt\"}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t-\timplement\t-\t1\t100\t200\nv1\tvendor\t-\t-\t-\tcodex\tcodex-review\t110\t190\t-\tcodex-specialist-arch-output.txt\t-\tcomplete\n",
            ),
            (
                "findings.jsonl",
                "{\"outcome\":\"accepted\",\"reviewer_slots\":[\"codex-specialist-arch-output.txt\"]}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-top-n-zero",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/rounds",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--findings-file",
            "{sandbox}/findings.jsonl",
            "--top-n",
            "0",
            "--no-gantt",
        ],
        seeds: &[
            (
                "rounds/round-1/round-meta.json",
                "{\n  \"tally\": {\"ACCEPTED_COUNT\": \"2\", \"REJECTED_COUNT\": \"1\", \"EXONERATED_COUNT\": \"0\", \"NEUTRAL_COUNT\": \"1\", \"OOS_PROPOSED_COUNT\": \"1\", \"OOS_ACCEPTED_COUNT\": \"1\", \"OOS_REJECTED_COUNT\": \"0\"},\n  \"summary\": {\"panel\": {\"total_slot_count\": 3}},\n  \"collector\": \"TOOL=codex\\nSTATUS=FAILED\\nREVIEWER_FILE=codex-specialist-arch-output.txt\"\n}\n",
            ),
            (
                "rounds/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"codex-specialist-arch-output.txt\"}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t-\timplement\t-\t1\t100\t200\nv1\tvendor\t-\t-\t-\tcodex\tcodex-review\t110\t190\t-\tcodex-specialist-arch-output.txt\t-\tcomplete\n",
            ),
            (
                "findings.jsonl",
                "{\"outcome\":\"accepted\",\"reviewer_slots\":[\"codex-specialist-arch-output.txt\"]}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-design-round-meta",
        command: "write-design-round-meta",
        arguments: &["--round-dir", "{sandbox}/design/plan-review/round-1"],
        seeds: &[
            (
                "design/plan-review/round-1/voting-tally.md",
                "## Findings\n| FINDING_1 | detail | accepted |\n| OOS_1 | detail | rejected |\n",
            ),
            (
                "design/plan-review/round-1/plan-review-slots.ndjson",
                "{\"slot\":\"cursor-plan-arch\",\"tool\":\"cursor\",\"output\":\"cursor-plan-arch-output.txt\",\"vendor\":\"cursor\"}\n",
            ),
            (
                "design/plan-review/round-1/revise/revise.env",
                "REVISE_STATUS=clean\nREVISE_TIER=major\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta",
        command: "write-implement-round-meta",
        arguments: &["--round-dir", "{sandbox}/review/round-1"],
        seeds: &[
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\tvoting_result\tscope\tv1_vote\tv1_severity\nFINDING_1\taccepted\tin_scope\tYES\tmajor\nOOS_1\taccepted\toos\tYES\tmajor\n",
            ),
            (
                "review/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"codex-specialist-arch-output.txt\"}\n",
            ),
            ("review/round-1/prune-nit.env", "PRUNED_COUNT=1\n"),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-classification-bonus-and-fallback",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/plan-review",
            "--skill",
            "design",
            "--no-gantt",
        ],
        seeds: &[
            (
                "plan-review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"3\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"1\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":3}}}\n",
            ),
            (
                "plan-review/round-1/plan-review-prune-label-map.tsv",
                "slot\thuman_label\nplan-requirements\tCursor-Pragmatic\nplan-architecture\tCodex-Arch\n",
            ),
            (
                "plan-review/round-1/findings-classification.tsv",
                "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_severity\tscope\nFINDING_SOLE\tSolo-Reviewer\taccepted\tYES\tminor\tin_scope\nFINDING_MULTI\tMulti-A, Multi-B\taccepted\tYES\tminor\tin_scope\nFINDING_WHITESPACE\tCursor-Pragmatic Codex-Arch\taccepted\tYES\tminor\tin_scope\nOOS_1\tOos-Reviewer\taccepted\tYES\tmajor\toos\n",
            ),
        ],
        environment: &[("LARCH_UNIQUE_FINDER_BONUS", "0.25")],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-attribution-historical-shapes",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/plan-review",
            "--skill",
            "design",
            "--no-gantt",
        ],
        seeds: &[
            (
                "plan-review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"3\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "plan-review/round-1/plan-review-prune-label-map.tsv",
                "slot\thuman_label\nknown\tKnown\n",
            ),
            (
                "plan-review/round-1/findings-classification.tsv",
                "finding_id\tfinding_reviewers\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nFINDING_1\t\tcodex-specialist-ignored-output.txt\taccepted\tYES\tminor\tin_scope\nFINDING_2\tKnown Known\tignored\taccepted\tYES\tminor\tin_scope\nFINDING_3\tUnknown Reviewer\tignored\taccepted\tYES\tminor\tin_scope\n",
            ),
            (
                "plan-review/round-1/review.output-files.dropped-slots",
                "dyn-custom-codex\tcodex\ttransport-failed\n",
            ),
        ],
        environment: &[("LARCH_UNIQUE_FINDER_BONUS", "0.25")],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-attempts-and-token-costs",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--token-ledger",
            "{sandbox}/tokens.jsonl",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"1\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t1782345600\timplement\t-\t1\t1782345600\t1782345610\t10\t0\t0\t0\t1\nv1\tround\t1782345620\timplement\t-\t1\t1782345620\t1782345640\t20\t0\t0\t0\t2\nv1\tvendor\t1782345608\timplement\t-\tcodex\tcodex-review\t1782345602\t1782345608\t6\tcodex-specialist-arch-output.txt\t0\tcomplete\nv1\tvendor\t1782345638\timplement\t-\tcursor\tcursor-review\t1782345622\t1782345638\t16\tcursor-specialist-edge-output.txt\t0\tsignal\n",
            ),
            (
                "tokens.jsonl",
                "{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.6-terra\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:05Z\"}\n{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.6-luna\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:06Z\"}\n{\"type\":\"vendor\",\"vendor\":\"cursor\",\"model\":\"cursor-grok-4.5-high\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:07Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-sonnet-4-6\",\"input\":1000000,\"output\":0,\"cache_read\":0,\"ts\":\"2026-06-25T00:00:08Z\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-gantt-hostile-width",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"1\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t-\timplement\t-\t1\t100\t200\nv1\tvendor\t-\t-\t-\tcursor\tcursor-review\t110\t190\t80\tcursor-specialist-very-long-review-focus-name-for-layout-output-retry.txt\t-\tcomplete\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-security-oos-zero-artifact",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/review", "--no-gantt"],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"1\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nOOS_1\tarch.txt\taccepted\tYES\tmajor\toos\n",
            ),
            (
                "review/round-1/findings-oos.md",
                "### OOS_1: [OUT_OF_SCOPE] [security] private item\n- **Focus area**: security\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-security-oos-id-boundary",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/review", "--no-gantt"],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"1\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nOOS_1\tarch.txt\taccepted\tYES\tminor\toos\n",
            ),
            (
                "review/round-1/findings-oos.md",
                "### OOS_10: [OUT_OF_SCOPE] [security] unrelated item\n- **Focus area**: security\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-security-oos-unclosed-fence",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/review", "--no-gantt"],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"1\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nOOS_1\tarch.txt\taccepted\tYES\tmajor\toos\n",
            ),
            (
                "review/round-1/findings-oos.md",
                "### OOS_1: [OUT_OF_SCOPE] unclosed fenced field\n```\nfocus-area=security\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-token-rate-overrides",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--token-ledger",
            "{sandbox}/tokens.jsonl",
            "--no-gantt",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t1782345600\timplement\t-\t1\t1782345600\t1782345610\t10\t0\t0\t0\t-\n",
            ),
            (
                "tokens.jsonl",
                "{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.6-sol\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:05Z\"}\n{\"type\":\"vendor\",\"vendor\":\"codex\",\"model\":\"gpt-5.4-mini\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:06Z\"}\n{\"type\":\"vendor\",\"vendor\":\"cursor\",\"model\":\"composer-2.5\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:07Z\"}\n{\"type\":\"vendor\",\"vendor\":\"cursor\",\"model\":\"grok-4.5\",\"input\":1000000,\"cache_read\":1000000,\"ts\":\"2026-06-25T00:00:08Z\"}\n",
            ),
        ],
        environment: &[
            ("LARCH_CODEX_INPUT_RATE_PER_M", "bad"),
            ("LARCH_RATE_CODEX_INPUT", "8.25"),
            ("LARCH_RATE_CODEX_CACHE_READ", "0.90"),
            ("LARCH_RATE_CODEX_MINI_INPUT", "1.75"),
            ("LARCH_RATE_CODEX_MINI_CACHE_READ", "0.20"),
            ("LARCH_RATE_CURSOR_INPUT", "3.25"),
            ("LARCH_RATE_CURSOR_CACHE_READ", "0.80"),
            ("LARCH_CURSOR_GROK_INPUT_RATE_PER_M", "7.25"),
            ("LARCH_CURSOR_GROK_CACHE_READ_RATE_PER_M", "0.70"),
        ],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-claude-sub-model-buckets",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/review",
            "--timing-ledger",
            "{sandbox}/timing.tsv",
            "--token-ledger",
            "{sandbox}/tokens.jsonl",
            "--no-gantt",
        ],
        seeds: &[
            (
                "review/round-1/round-meta.json",
                "{\"tally\":{\"ACCEPTED_COUNT\":\"0\",\"REJECTED_COUNT\":\"0\",\"EXONERATED_COUNT\":\"0\",\"NEUTRAL_COUNT\":\"0\",\"OOS_PROPOSED_COUNT\":\"0\",\"OOS_ACCEPTED_COUNT\":\"0\",\"OOS_REJECTED_COUNT\":\"0\"},\"summary\":{\"panel\":{\"total_slot_count\":1}}}\n",
            ),
            (
                "timing.tsv",
                "v1\tround\t1782345600\timplement\t-\t1\t1782345600\t1782345610\t10\t0\t0\t0\t-\n",
            ),
            (
                "tokens.jsonl",
                "{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-sonnet-4-6\",\"input\":1000000,\"cache_create\":1000000,\"ts\":\"2026-06-25T00:00:05Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-haiku-4-5\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:06Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-fable-5\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:07Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"model\":\"claude-sonnet-4-6[1m]\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:08Z\"}\n{\"type\":\"vendor\",\"vendor\":\"claude_sub\",\"raw\":\"claude_review\",\"input\":1000000,\"ts\":\"2026-06-25T00:00:09Z\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-partial-and-historical-rounds",
        command: "render-phase-detail",
        arguments: &["--rounds-root", "{sandbox}/rounds", "--no-gantt"],
        seeds: &[
            ("rounds/round-0/round-meta.json", "{}\n"),
            ("rounds/round-01/round-meta.json", "{}\n"),
            ("rounds/round-1/inflight.txt", "still running\n"),
            ("rounds/round-2/round-meta.json", "{not valid JSON\n"),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-design-round-meta-security-and-collector",
        command: "write-design-round-meta",
        arguments: &["--round-dir", "{sandbox}/design/plan-review/round-1"],
        seeds: &[
            (
                "design/plan-review/round-1/voting-tally.md",
                "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n| OOS_1 | accepted |\n",
            ),
            (
                "design/plan-review/round-1/findings-oos.md",
                "### OOS_1: security item\nfocus-area=security\n",
            ),
            (
                "design/plan-review/round-1/plan-review-slots.ndjson",
                "{\"slot\":\"cursor-plan-requirements\",\"tool\":\"cursor\",\"output\":\"cursor-plan-requirements-output.txt\",\"vendor\":\"cursor\",\"resolved_model\":\"cursor-model\",\"focus_area\":\"rêview 😀\"}\n",
            ),
            (
                "design/plan-review/round-1/round-summary.env",
                "COLLECT_FAILURE_COUNT=1\n",
            ),
            (
                "design/collector-results.env",
                "REVIEWER_FILE=ok-output.txt\nTOOL=cursor\nSTATUS=OK\n\nREVIEWER_FILE=cursor-plan-requirements-output.txt\nTOOL=cursor\nSTATUS=FAILED\n",
            ),
            (
                "design/plan-review/round-1/revise/revise.env",
                "REVISE_STATUS=ok-fallback\nREVISE_TIER=primary\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta-canonical-and-difficulty",
        command: "write-implement-round-meta",
        arguments: &["--round-dir", "{sandbox}/review/round-1"],
        seeds: &[
            (
                "review/round-1/voting-tally.md",
                "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n| FINDING_2 | rejected |\n| FINDING_3 | rejected |\n",
            ),
            (
                "review/round-1/findings-classification.tsv",
                "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tscope\nFINDING_1\tarch.txt\taccepted\tYES\tminor\tin_scope\nFINDING_2\tarch.txt\trejected\tNO\tminor\tin_scope\nFINDING_3\tarch.txt\trejected\tNO\tminor\toos\nOOS_1\tarch.txt\taccepted\tYES\tminor\toos\n",
            ),
            (
                "review/round-1/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"arch.txt\"}\n",
            ),
            ("review/round-1/review-tally.env", "OOS_ACCEPTED_COUNT=2\n"),
            ("review/round-1/prune-nit.env", "PRUNED_COUNT=1\n"),
            (
                "review/round-1/difficulty-rating.json",
                "{\"panel_tier\":\"HARD\",\"applied_tier\":\"HARD\",\"round_cap\":3,\"codex_model_role\":\"default\",\"override_source\":\"operator\",\"audit_evaluated\":true,\"audit_upgrade\":\"true\",\"escalated_round\":true,\"escalations\":[{\"round\":2,\"from_tier\":\"MODERATE\",\"to_tier\":\"HARD\"}]}\n",
            ),
            (
                "review/round-1/scout-difficulty-rating.raw.json",
                "{\"predicted_tier\":\"TRIVIAL\",\"confidence\":\"low\",\"rationale\":\"unclear small diff\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-write-implement-round-meta-relative-path",
        command: "write-implement-round-meta",
        arguments: &["--round-dir", "round"],
        seeds: &[
            (
                "round/voting-tally.md",
                "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n",
            ),
            (
                "round/panel-manifest.ndjson",
                "{\"slot\":\"arch\",\"tool\":\"codex\",\"output\":\"arch.txt\"}\n",
            ),
            (
                "round/scout-difficulty-rating.raw.json",
                "{\"predicted_tier\":\"TRIVIAL\",\"confidence\":\"low\",\"rationale\":\"small scope\"}\n",
            ),
        ],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-output-file",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "{sandbox}/rounds",
            "--no-gantt",
            "--output",
            "{sandbox}/output/review-detail.md",
        ],
        seeds: &[("rounds/.keep", ""), ("output/.keep", "")],
        environment: &[],
    },
    PhaseDetailFixture {
        name: "progress-phase-detail-output-file-relative-path",
        command: "render-phase-detail",
        arguments: &[
            "--rounds-root",
            "rounds",
            "--no-gantt",
            "--output",
            "output/review-detail.md",
        ],
        seeds: &[("rounds/.keep", ""), ("output/.keep", "")],
        environment: &[],
    },
];

#[test]
fn phase_detail_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("progress_phase_detail_reference.py");
    let python_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../python")
        .canonicalize()
        .expect("python source path")
        .to_string_lossy()
        .into_owned();
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in PHASE_DETAIL_CASES {
        let case = fixture.build(&python, &python_fixture, &rust, &python_path);
        let golden = golden_directory.join(format!("{}.golden.json", fixture.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[cfg(unix)]
#[test]
fn phase_detail_public_artifacts_keep_the_legacy_writer_mode() {
    let sandbox = TempDir::new().expect("sandbox");
    let round = sandbox.path().join("round");
    fs::create_dir(&round).expect("round directory");
    let binary = env!("CARGO_BIN_EXE_larch");

    let metadata = Command::new(binary)
        .args([
            "progress",
            "write-implement-round-meta",
            "--round-dir",
            round.to_str().expect("round path"),
        ])
        .status()
        .expect("write metadata");
    assert!(metadata.success());

    let rounds = sandbox.path().join("rounds");
    fs::create_dir(&rounds).expect("rounds directory");
    let output = sandbox.path().join("phase-detail.md");
    let rendered = Command::new(binary)
        .args([
            "progress",
            "render-phase-detail",
            "--rounds-root",
            rounds.to_str().expect("rounds path"),
            "--no-gantt",
            "--output",
            output.to_str().expect("output path"),
        ])
        .status()
        .expect("write phase detail");
    assert!(rendered.success());

    for artifact in [round.join("round-meta.json"), output] {
        let mode = fs::metadata(&artifact)
            .expect("artifact metadata")
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o644, "{}", artifact.display());
    }
}

#[test]
fn the_parity_clone_hash_is_pinned_to_its_path() {
    assert!(
        PROGRESS_CLONE_DIR.ends_with(&larch_core::progress_clone_digest(PROGRESS_CLONE)),
        "the pinned parity clone directory no longer matches its clone hash"
    );
    assert!(!Path::new(PROGRESS_CLONE).exists());
}

struct SessionEnvFixture {
    name: &'static str,
    command: &'static str,
    arguments: &'static [&'static str],
    environment: &'static [(&'static str, &'static str)],
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl SessionEnvFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        // Session writer targets seeded directly under the fixture root are
        // valid temporary-session paths. Pin TMPDIR to that root so macOS and
        // Linux exercise the same allowlist boundary.
        let mut python_program = Program::new(python)
            .args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.command))
                    .chain(self.arguments.iter().copied()),
            )
            .env("TMPDIR", "{sandbox}");
        let mut rust_program = Program::new(rust)
            .args(
                ["session", self.command]
                    .into_iter()
                    .chain(self.arguments.iter().copied()),
            )
            .env("TMPDIR", "{sandbox}");
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

/// A seeded session directory whose name never matches the tmpdir redaction rules.
const WRITER_SESSION: &str = "writer-session/.keep";
/// One prior `/implement` session-env the overwrite cases must not lose.
const PRIOR_SESSION_ENV: &str = "REPO=prior/repo\n";
/// A durable ship-pr state with no bail reason, so no run-log delegation runs.
const SHIP_PR_STATE: &str = concat!(
    "# comment\n",
    "BRANCH_NAME=feature/x\n",
    "PR_NUMBER=42\n",
    "PR_TITLE=Some title with spaces\n",
    "PR_URL=https://example.invalid/pr/42\n",
    "ISSUE_NUMBER=8058\n",
    "REPO=character-ai/larch\n",
    "MERGE=true\n",
    "RUN_ID=run-abc\n",
    "NOT_A_KEY\n",
);
/// A prior finalize state whose stall tracking outranks the durable state.
const PRIOR_FINALIZE_STATE: &str =
    "STALL_TRACKING=true\nSTALL_STEP=Step 5\nEXPECTED_SESSION_ID=sid-1\n";
/// A prior design env the refresh path recovers values from.
const PRIOR_DESIGN_ENV: &str = concat!(
    "#!/usr/bin/env bash\n",
    "export REPO_ROOT=/prior/root\n",
    "export LARCH_RUN_ID=prior-run\n",
    "export CODEX_BINARY_FOUND=true\n",
    "export LARCH_LIVE_MUTATION_OK=true\n",
);
const PLUGIN_ROOT_SANDBOX: &[(&str, &str)] = &[("CLAUDE_PLUGIN_ROOT", "{sandbox}")];

const SESSION_ENV_CASES: &[SessionEnvFixture] = &[
    SessionEnvFixture {
        name: "session-write-env-missing-arguments",
        command: "write-env",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-unrecognized",
        command: "write-env",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    // A missing required flag outranks an unexpanded plugin root, so the two
    // must not be reordered when the flag validations are grouped.
    SessionEnvFixture {
        name: "session-write-env-missing-repo-unavailable-outranks-plugin-root",
        command: "write-env",
        arguments: &["--output", "{sandbox}/writer-session/session-env.sh"],
        environment: &[("CLAUDE_PLUGIN_ROOT", "${CLAUDE_PLUGIN_ROOT}")],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-invalid-plugin-root",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
        ],
        environment: &[("CLAUDE_PLUGIN_ROOT", "${CLAUDE_PLUGIN_ROOT}")],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-dev-null",
        command: "write-env",
        arguments: &["--output", "/dev/null", "--repo-unavailable", "false"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-invalid-boolean",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
            "--auto-mode",
            "maybe",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-outside-allowed-root",
        command: "write-env",
        arguments: &[
            "--output",
            "/larch-parity-not-a-session/session-env.sh",
            "--repo-unavailable",
            "false",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-env-full",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo",
            "character-ai/larch",
            "--repo-root",
            "/repo/root",
            "--repo-unavailable",
            "false",
            "--claude-binary-found",
            "true",
            "--codex-binary-found",
            "false",
            "--cursor-binary-found",
            "true",
            "--auto-mode",
            "true",
            "--forked-target",
            "true",
            "--timing-ledger",
            "/tmp/ledger.tsv",
            "--token-session-id",
            "abc.123",
            "--claude-source-file",
            "/tmp/claude-source.env",
            "--prev-implement-tmpdir",
            "/tmp/prev",
            "--dynamic-archetypes",
            "1",
            "--run-id",
            "run-9",
            "--live-mutation-ok",
            "true",
        ],
        environment: PLUGIN_ROOT_SANDBOX,
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-write-env-plugin-root-only",
        command: "write-env",
        arguments: &[
            "--plugin-root-only",
            "--output",
            "{sandbox}/writer-session/plugin-root.env",
            "--value",
            "/opt/larch",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-write-env-rejects-and-keeps-prior",
        command: "write-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
            "--run-id",
            "bad/id",
        ],
        environment: &[],
        seeds: &[
            (WRITER_SESSION, ""),
            ("writer-session/session-env.sh", PRIOR_SESSION_ENV),
        ],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-design-env-missing-arguments",
        command: "write-design-env",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-design-env-invalid-repo",
        command: "write-design-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/source-env.sh",
            "--design-tmpdir",
            "{sandbox}/writer-session",
            "--session-id",
            "sid.1",
            "--repo",
            "/bad",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    // Not a sandbox path: every platform's temporary root is itself allowlisted,
    // on Linux through `/tmp` and on macOS through `TMPDIR`. `/usr` is a real
    // directory on both, so the rejected path resolves to itself either way.
    SessionEnvFixture {
        name: "session-write-design-env-outside-allowlist",
        command: "write-design-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/source-env.sh",
            "--design-tmpdir",
            "/usr",
            "--session-id",
            "sid.1",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-design-env-requires-plugin-root-with-pid",
        command: "write-design-env",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/source-env.sh",
            "--design-tmpdir",
            "{sandbox}/writer-session",
            "--session-id",
            "sid.1",
            "--claude-pid",
            "4242",
        ],
        environment: &[],
        seeds: &[
            (WRITER_SESSION, ""),
            ("writer-session/source-env.sh", PRIOR_DESIGN_ENV),
        ],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-implement-env-invalid-pid",
        command: "write-implement-env",
        arguments: &["--claude-pid", "0", "--cwd", "/"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-implement-env-publishes-pointer",
        command: "write-implement-env",
        arguments: &[
            "--claude-pid",
            "4242",
            "--implement-tmpdir",
            "{sandbox}/writer-session",
            "--cwd",
            "/",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-clear-implement-pointer-invalid-pid",
        command: "clear-implement-pointer",
        arguments: &["--claude-pid", "abc"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-clear-implement-pointer-removes-pointer",
        command: "clear-implement-pointer",
        arguments: &["--claude-pid", "4242"],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/current-implement-env-4242.sh",
            "IMPLEMENT_TMPDIR=/tmp/writer-session\n",
        )],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-unrecognized",
        command: "persist-run-flags",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-missing-directory",
        command: "persist-run-flags",
        arguments: &["--implement-tmpdir", "{sandbox}/absent-session"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-invalid-boolean",
        command: "persist-run-flags",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-persist-run-flags-full",
        command: "persist-run-flags",
        arguments: &[
            "--implement-tmpdir",
            "{sandbox}/writer-session",
            "--quick-mode",
            "true",
            "--no-issues",
            "false",
            "--force-requested",
            "true",
            "--self-review-requested",
            "false",
            "--self-implement-requested",
            "true",
            "--difficulty-override",
            "MODERATE",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-unrecognized",
        command: "write-run-params",
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-relative-output",
        command: "write-run-params",
        arguments: &["--output", "relative.json"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-invalid-difficulty",
        command: "write-run-params",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/run-params.json",
            "--difficulty",
            "NOPE",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-write-run-params-missing-directory",
        command: "write-run-params",
        arguments: &["--output", "{sandbox}/absent-session/run-params.json"],
        environment: &[],
        seeds: &[],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-write-run-params-full",
        command: "write-run-params",
        arguments: &[
            "--output",
            "{sandbox}/writer-session/run-params.json",
            "--partition-requested",
            "true",
            "--brainstorm-requested",
            "false",
            "--approve-requested",
            "true",
            "--skip-approve-requested",
            "false",
            "--difficulty",
            "HARD",
        ],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-missing-state-file",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[(WRITER_SESSION, "")],
        normalization: SANDBOX_ONLY,
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-outside-allowed-root",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "/usr"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-fresh",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[("writer-session/ship-pr-state.sh", SHIP_PR_STATE)],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-restore-finalize-state-keeps-stall-tracking",
        command: "restore-finalize-state",
        arguments: &["--implement-tmpdir", "{sandbox}/writer-session"],
        environment: &[],
        seeds: &[
            ("writer-session/ship-pr-state.sh", SHIP_PR_STATE),
            ("writer-session/finalize-state.sh", PRIOR_FINALIZE_STATE),
        ],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-resolve-trusted-design-env-missing-required",
        command: "resolve-trusted-design-env",
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-resolve-trusted-design-env-invalid-pid",
        command: "resolve-trusted-design-env",
        arguments: &[
            "--session-env-path",
            "{sandbox}/absent.sh",
            "--claude-pid",
            "0",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    SessionEnvFixture {
        name: "session-resolve-trusted-design-env-no-pointer",
        command: "resolve-trusted-design-env",
        arguments: &[
            "--session-env-path",
            "{sandbox}/absent.sh",
            "--claude-pid",
            "4242",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
];

#[test]
fn session_env_writer_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("session_env_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in SESSION_ENV_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

/// One admission or gate case, addressed by its reference sub-verb and its
/// real `DOMAIN VERB` selector.
struct AdmissionFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
    environment: &'static [(&'static str, &'static str)],
    seeds: &'static [(&'static str, &'static str)],
    normalization: &'static [NormalizationRule],
}

impl AdmissionFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        let mut python_program = Program::new(python).args(
            std::iter::once(path_text(fixture))
                .chain(std::iter::once(self.reference))
                .chain(self.arguments.iter().copied()),
        );
        let mut rust_program = Program::new(rust).args(
            self.selector
                .iter()
                .copied()
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

/// A session context file whose authorization key and run id both match.
const MUTATION_CONTEXT: &str = "export LARCH_LIVE_MUTATION_OK='true'\nLARCH_RUN_ID=\"run1\"\n";
const ADMISSION_CASES: &[AdmissionFixture] = &[
    AdmissionFixture {
        name: "session-entry-gate-strict",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode",
            "implement",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-design-branch-info-continues",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode",
            "design",
            "--current-branch",
            "feature",
            "--is-main",
            "false",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
            "--branch-info-supplied",
            "true",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-invalid-mode",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode",
            "review",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-inline-spelling-reads-as-missing",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &[
            "--mode=implement",
            "--current-branch",
            "main",
            "--is-main",
            "true",
            "--is-user-branch",
            "false",
            "--user-prefix",
            "parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-unknown-argument",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-entry-gate-missing-value",
        reference: "entry-gate",
        selector: &["session", "entry-gate"],
        arguments: &["--mode"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-authorized",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1",
        ],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-run-id-mismatch",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            "--run-id",
            "run2",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1",
        ],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-non-session-root-name",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/not-a-session/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/not-a-session",
        ],
        environment: &[],
        seeds: &[(
            ".home/.cache/larch/sessions/not-a-session/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-root-outside-allowlist",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "/usr/claude-implement-parity/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "/usr/claude-implement-parity",
        ],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-test-deny",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &[
            "--context-file",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            "--run-id",
            "run1",
            "--trusted-root",
            "{sandbox}/.home/.cache/larch/sessions/claude-implement-run1",
        ],
        environment: &[("LARCH_ISSUE_MUTATION_DENY", "true")],
        seeds: &[(
            ".home/.cache/larch/sessions/claude-implement-run1/source-env.sh",
            MUTATION_CONTEXT,
        )],
        normalization: &[],
    },
    AdmissionFixture {
        name: "session-check-live-mutation-auth-missing-required",
        reference: "check-live-mutation-auth",
        selector: &["session", "check-live-mutation-auth"],
        arguments: &["--run-id", "run1"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-help",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--help"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-help-consumed-as-issue-value",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "-h"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-help-after-issue",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "5", "--help"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-missing-issue",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-non-positive-issue",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "0"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-gate-unresolvable-repo",
        reference: "admission-gate",
        selector: &["admission", "gate"],
        arguments: &["--issue", "8059"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-preflight-unknown-option",
        reference: "admission-preflight",
        selector: &["admission", "preflight"],
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-preflight-stray-positional",
        reference: "admission-preflight",
        selector: &["admission", "preflight"],
        arguments: &["--skip-branch-check", "extra"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-preflight-not-on-main",
        reference: "admission-preflight",
        selector: &["admission", "preflight"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-help",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &["--help"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-help-consumed-as-tmpdir-value",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &["--tmpdir", "-h"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-unrecognized",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &["--bogus"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "admission-fork-env-missing-upstream",
        reference: "admission-fork-env",
        selector: &["admission", "fork-env"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "blocker-all-open-no-issue",
        reference: "blocker-all-open",
        selector: &["blocker", "all-open"],
        arguments: &[],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
    AdmissionFixture {
        name: "blocker-all-open-trailing-issue-flag",
        reference: "blocker-all-open",
        selector: &["blocker", "all-open"],
        arguments: &["--repo", "o/r", "--issue"],
        environment: &[],
        seeds: &[],
        normalization: &[],
    },
];

#[test]
fn admission_and_gate_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("admission_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ADMISSION_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

/// One issue-query case, addressed by its reference sub-verb and its real
/// `DOMAIN VERB` selector.
struct IssueQueryFixture {
    name: &'static str,
    reference: &'static str,
    selector: &'static [&'static str],
    arguments: &'static [&'static str],
}

impl IssueQueryFixture {
    fn build(&self, python: &Path, fixture: &Path, rust: &Path) -> ParityCase {
        ParityCase {
            name: self.name,
            python: Program::new(python).args(
                std::iter::once(path_text(fixture))
                    .chain(std::iter::once(self.reference))
                    .chain(self.arguments.iter().copied()),
            ),
            rust: Program::new(rust).args(
                self.selector
                    .iter()
                    .copied()
                    .chain(self.arguments.iter().copied()),
            ),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        }
    }
}

/// Every case stops before a GitHub client is built. The sandbox has no `gh`,
/// no `git`, and no network, so repository resolution is absent and the reads
/// these verbs would otherwise perform never start.
const ISSUE_QUERY_CASES: &[IssueQueryFixture] = &[
    IssueQueryFixture {
        name: "issue-state-missing-issue",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &[],
    },
    IssueQueryFixture {
        name: "issue-state-non-numeric-issue",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "12a"],
    },
    IssueQueryFixture {
        name: "issue-state-unknown-flag",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--bogus"],
    },
    // The scanner matches exact spellings only, so the inline form is unknown
    // rather than an `--issue` assignment.
    IssueQueryFixture {
        name: "issue-state-inline-spelling-reads-as-unknown",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue=42"],
    },
    IssueQueryFixture {
        name: "issue-state-trailing-issue-flag",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue"],
    },
    // A transposed line must not read `--repo` as the issue number.
    IssueQueryFixture {
        name: "issue-state-option-shaped-issue-value",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "--repo", "o/r"],
    },
    IssueQueryFixture {
        name: "issue-state-trailing-repo-flag",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "42", "--repo"],
    },
    IssueQueryFixture {
        name: "issue-state-unresolvable-repo",
        reference: "issue-state",
        selector: &["issue", "state"],
        arguments: &["--issue", "8167"],
    },
    IssueQueryFixture {
        name: "issue-info-trailing-field-flag",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field"],
    },
    IssueQueryFixture {
        name: "issue-info-unsupported-field",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field", "title"],
    },
    // An unrecognized token suppresses the read without stopping the scan.
    IssueQueryFixture {
        name: "issue-info-unknown-token",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["noise", "--issue", "7", "--field", "state"],
    },
    IssueQueryFixture {
        name: "issue-info-missing-issue",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--field", "state"],
    },
    IssueQueryFixture {
        name: "issue-info-unresolvable-repo",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field", "state"],
    },
    // An explicit repository still reaches an unreachable API, and this verb
    // reports that the same way it reports every other refusal.
    IssueQueryFixture {
        name: "issue-info-unreachable-explicit-repo",
        reference: "issue-info",
        selector: &["issue", "info"],
        arguments: &["--issue", "7", "--field", "url", "--repo", "o/r"],
    },
    IssueQueryFixture {
        name: "issue-context-help",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--help"],
    },
    // `--help` after a value-taking option is that option's value, not help.
    IssueQueryFixture {
        name: "issue-context-help-consumed-as-issue-value",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "--help"],
    },
    IssueQueryFixture {
        name: "issue-context-trailing-issue-flag",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue"],
    },
    IssueQueryFixture {
        name: "issue-context-unknown-token",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--bogus", "x"],
    },
    IssueQueryFixture {
        name: "issue-context-missing-tmpdir",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "7", "--repo", "o/r"],
    },
    IssueQueryFixture {
        name: "issue-context-non-positive-issue",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "0", "--repo", "o/r", "--tmpdir", "{sandbox}/ctx"],
    },
    IssueQueryFixture {
        name: "issue-context-invalid-repo",
        reference: "issue-context",
        selector: &["issue", "context"],
        arguments: &["--issue", "7", "--repo", "bad", "--tmpdir", "{sandbox}/ctx"],
    },
];

#[test]
fn issue_query_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let python_fixture = fixture_directory.join("issue_query_reference.py");
    let rust = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let golden_directory = fixture_directory.join("goldens");

    for fixture in ISSUE_QUERY_CASES {
        let case = fixture.build(&python, &python_fixture, &rust);
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

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

const CLEAN_INSTALL_PARTITION_COUNT: usize = 4;

#[test]
fn rust_owned_selector_matrix_partition_0_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(0);
}

#[test]
fn rust_owned_selector_matrix_partition_1_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(1);
}

#[test]
fn rust_owned_selector_matrix_partition_2_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(2);
}

#[test]
fn rust_owned_selector_matrix_partition_3_enters_through_verified_clean_install_script() {
    assert_clean_install_partition(3);
}

fn assert_clean_install_partition(partition: usize) {
    let fixture = clean_install_fixture();
    for (index, case) in CLEAN_INSTALL_CASES.iter().copied().enumerate() {
        if index % CLEAN_INSTALL_PARTITION_COUNT != partition {
            continue;
        }
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, case, None);
        assert_eq!(
            output.status.code(),
            Some(case.expected_exit()),
            "{} failed: {}",
            case.id,
            String::from_utf8_lossy(&output.stderr)
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        let lines: Vec<&str> = events.lines().collect();
        let expected_dispatch = clean_install_dispatch(&fixture, case);
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
                .any(|line| line == clean_install_dispatch(&fixture, case)),
            "{failure} reached selector dispatch"
        );
    }
}

/// Argument placeholder each clean-install case expands to the seeded session.
const CLEAN_INSTALL_SESSION_TOKEN: &str = "%SESSION%";
/// Argument placeholder each clean-install case expands to the isolated home.
const CLEAN_INSTALL_HOME_TOKEN: &str = "%HOME%";

struct CleanInstallFixture {
    _temporary: TempDir,
    root: PathBuf,
    /// Isolated home, so a verb that publishes a PID-keyed pointer stays contained.
    home: PathBuf,
    /// Seeded session directory every writer verb targets.
    session: PathBuf,
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
    let home = temporary_root.join("home");
    let session = temporary_root.join("session");
    let sessions_cache = home.join(".cache/larch/sessions");
    fs::create_dir_all(&sessions_cache).expect("create clean-install home");
    fs::create_dir_all(&session).expect("create clean-install session directory");
    // `restore-finalize-state` reports a missing durable state file as a warning
    // exit, so the seeded state is what lets a clean dispatch complete.
    fs::write(
        session.join("ship-pr-state.sh"),
        "BRANCH_NAME=clean-install\n",
    )
    .expect("seed clean-install ship-pr state");
    // `resolve-trusted-design-env` resolves an existing pointer or exits 1, so the
    // seeded link and target are what let a clean dispatch complete.
    fs::write(
        session.join("design-env.sh"),
        "export SESSION_ID=clean-install\n",
    )
    .expect("seed clean-install design env");
    #[cfg(unix)]
    std::os::unix::fs::symlink(
        session.join("design-env.sh"),
        sessions_cache.join("current-design-env-4242.sh"),
    )
    .expect("seed clean-install design pointer");
    seed_clean_install_run_log_inputs(&root, &session);
    CleanInstallFixture {
        events: temporary_root.join("events.log"),
        binary: PathBuf::from(env!("CARGO_BIN_EXE_larch")),
        _temporary: temporary,
        root,
        home,
        session,
        wrapper,
    }
}

/// Seed the payloads, quiet log, round source, run directory, and required-files
/// manifest the `run-log` entry-write and breadcrumb verbs read on a clean install.
fn seed_clean_install_run_log_inputs(root: &Path, session: &Path) {
    fs::write(session.join("payload.md"), "clean-install payload\n")
        .expect("seed clean-install batch payload");
    fs::write(
        session.join("larch-quiet-clean-install.sh-1.log"),
        "clean-install breadcrumb\n",
    )
    .expect("seed clean-install quiet log");
    fs::write(session.join("record.ndjson"), "{\"clean\":\"install\"}\n")
        .expect("seed clean-install append record");
    let round_source = session.join("round-src");
    fs::create_dir_all(&round_source).expect("create clean-install round source");
    fs::write(round_source.join("coder-prompt.md"), "prompt\n")
        .expect("seed clean-install round artifact");
    let run_directory = session.join("verify-run");
    fs::create_dir_all(&run_directory).expect("create clean-install verify run directory");
    fs::write(
        run_directory.join("manifest.json"),
        "{\"schema_version\":2,\"status\":\"merged\",\"run_id\":\"clean-install\",\"steps_ran\":{}}\n",
    )
    .expect("seed clean-install verify manifest");
    let documents = root.join("docs");
    fs::create_dir_all(&documents).expect("create clean-install docs directory");
    fs::write(
        documents.join("run-logs-required-files.tsv"),
        "relative_path\tcondition\nmanifest.json\talways\n",
    )
    .expect("seed clean-install required-files manifest");
}

/// Expand one case's static arguments against the fixture's seeded session.
fn clean_install_arguments(fixture: &CleanInstallFixture, case: CleanInstallCase) -> Vec<String> {
    let session = fixture.session.to_string_lossy().into_owned();
    let home = fixture.home.to_string_lossy().into_owned();
    case.arguments()
        .iter()
        .map(|argument| {
            argument
                .replace(CLEAN_INSTALL_SESSION_TOKEN, &session)
                .replace(CLEAN_INSTALL_HOME_TOKEN, &home)
        })
        .collect()
}

/// Render the argv line the verified bootstrap wrapper records for one case.
///
/// An argument-free verb records only its domain and verb, with no trailing
/// separator, because the wrapper logs the shell's joined argument list.
fn clean_install_dispatch(fixture: &CleanInstallFixture, case: CleanInstallCase) -> String {
    std::iter::once(case.domain.to_owned())
        .chain(std::iter::once(case.verb.to_owned()))
        .chain(clean_install_arguments(fixture, case))
        .collect::<Vec<_>>()
        .join(" ")
}

fn run_clean_install_case(
    fixture: &CleanInstallFixture,
    case: CleanInstallCase,
    failure: Option<&str>,
) -> std::process::Output {
    let manifest_root = if case.id == "clean-install-run-log-manifest" {
        let path = fixture
            .root
            .join("manifest-logs/clean/clean-install/manifest.json");
        fs::create_dir_all(path.parent().expect("manifest parent"))
            .expect("create clean-install manifest parent");
        fs::write(
            &path,
            "{\"schema_version\":2,\"status\":\"partial\",\"run_id\":\"clean-install\",\"steps_ran\":{}}\n",
        )
        .expect("write clean-install manifest");
        Some(fixture.root.as_path())
    } else {
        None
    };
    let mut command = Command::new("/bin/bash");
    command
        .arg(fixture.root.join("scripts/larch.sh"))
        .args([case.domain, case.verb])
        .args(clean_install_arguments(fixture, case))
        .env("HOME", &fixture.home)
        .env("TMPDIR", &fixture.session)
        .env_remove("XDG_CACHE_HOME")
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        // Progress verbs write clone-scoped cache state; confine it to the fixture.
        .env("LARCH_TEST_CACHE_HOME", &fixture.root)
        .env("CLEAN_INSTALL_FAILURE", failure.unwrap_or_default());
    if let Some(root) = manifest_root {
        command.env("IMPLEMENT_TMPDIR", root);
    }
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
