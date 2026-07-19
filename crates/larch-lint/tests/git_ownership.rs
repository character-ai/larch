mod support;

use std::fmt::Write as _;

use predicates::prelude::*;
use support::TempRepo;

const COMMANDS: [(&str, &str, u64); 22] = [
    ("git", "amend-add", 7735),
    ("git", "branch-info", 7734),
    ("git", "check-main-sync", 7758),
    ("git", "check-phantom-dirty", 7757),
    ("git", "check-remote-branch", 7734),
    ("git", "checkout-ours", 7759),
    ("git", "clean-tree", 7756),
    ("git", "commit", 7735),
    ("git", "conflict-files", 7756),
    ("git", "count-commits", 7734),
    ("git", "current-branch", 7734),
    ("git", "phantom-probe", 7757),
    ("git", "rebase-abort", 7759),
    ("git", "rebase-skip", 7759),
    ("git", "show-stage", 7734),
    ("git", "snapshot-untracked", 7756),
    ("git", "stage", 7735),
    ("git", "sync-local-main", 7758),
    ("push", "branch", 7760),
    ("push", "checkpoint-probe", 7762),
    ("push", "force", 7760),
    ("push", "rebase", 7762),
];

const OPERATIONS: &str = r"pub enum GitCliOperation {
    Add,
    Apply,
    BranchMutation,
    Checkout,
    Clean,
    Clone,
    Commit,
    ConfigMutation,
    ExactDiff,
    Fetch,
    Init,
    InterpretTrailers,
    LsRemote,
    Merge,
    Pull,
    Push,
    Rebase,
    RemoteMutation,
    Reset,
    Restore,
    Rm,
    SparseCheckout,
    Stash,
    SubmoduleUpdate,
    TagMutation,
    Version,
    Worktree,
}
";

const REQUESTS: &str = r"
git_op!(AddRequest, Add);
git_op!(ApplyRequest, Apply);
git_op!(BranchMutationRequest, BranchMutation);
git_op!(CheckoutRequest, Checkout);
git_op!(CleanRequest, Clean);
git_op!(CloneRequest, Clone);
git_op!(CommitRequest, Commit);
git_op!(ConfigMutationRequest, ConfigMutation);
git_op!(ExactDiffRequest, ExactDiff);
git_op!(FetchRequest, Fetch);
git_op!(InitRequest, Init);
impl GitOperation for InterpretTrailersRequest {
}
git_op!(LsRemoteRequest, LsRemote);
git_op!(MergeRequest, Merge);
git_op!(PullRequest, Pull);
git_op!(PushRequest, Push);
git_op!(RebaseRequest, Rebase);
git_op!(RemoteMutationRequest, RemoteMutation);
git_op!(ResetRequest, Reset);
git_op!(RestoreRequest, Restore);
git_op!(RmRequest, Rm);
git_op!(SparseCheckoutRequest, SparseCheckout);
git_op!(StashRequest, Stash);
git_op!(SubmoduleRequest, SubmoduleUpdate);
git_op!(TagMutationRequest, TagMutation);
git_op!(VersionRequest, Version);
git_op!(WorktreeRequest, Worktree);
";

fn command_registry() -> String {
    let mut output = String::from("schema_version = 1\n");
    for (domain, verb, issue) in COMMANDS {
        let _ = write!(
            output,
            r#"
[[commands]]
domain = "{domain}"
verb = "{verb}"
owner = "rust"
implementation_parity = "complete"
consumer_cutover = "complete"
python_removal = "complete"
migration_issue = {issue}
"#,
        );
    }
    output
}

fn inventory(extra: &str) -> String {
    format!(
        "# Git operation inventory\n\n<!-- git-ownership-matrix:start -->\n```text\nsurface\towner\tissue\toperations\ncrates/larch-adapters/src/git/mod.rs\tgit-cli\t#7671\tclosed-cli-owner\ncrates/larch-adapters/src/git/repository.rs\tgix-read\t#7671\tconcrete-gix-owner\ncrates/larch-lint/src/repository.rs\tbootstrap\t#7736\trepository-discovery,tracked-paths\n{extra}```\n<!-- git-ownership-matrix:end -->\n"
    )
}

fn prepare_repository(repository: &TempRepo) {
    repository.write("crates/larch-core/src/process.rs", OPERATIONS.as_bytes());
    repository.write(
        "crates/larch-adapters/src/git/mod.rs",
        b"pub struct GitCli;\n",
    );
    repository.write(
        "crates/larch-adapters/src/git/repository.rs",
        b"pub struct GixRepository;\nuse gix::Repository;\n",
    );
    repository.write("crates/larch-adapters/src/git/ops.rs", REQUESTS.as_bytes());
    repository.write(
        "crates/larch-lint/src/repository.rs",
        b"// repository discovery bootstrap\n",
    );
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        command_registry().as_bytes(),
    );
    repository.write("docs/git-operation-inventory.md", inventory("").as_bytes());
}

#[test]
fn accepts_the_closed_owned_boundary() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn rejects_concrete_gix_bypass_and_duplicate_owners() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-core/src/leak.rs",
        b"use gix::Repository;\npub struct GitCli;\npub struct GixRepository;\n",
    );
    repository.write(
        "crates/larch-core/Cargo.toml",
        b"[dependencies]\ngix = { workspace = true }\n",
    );
    repository.write(
        "crates/larch-lint/src/leak.rs",
        b"use gix::ThreadSafeRepository;\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "concrete gix use outside crates/larch-adapters",
        ))
        .stdout(predicate::str::contains(
            "duplicate Git implementation outside crates/larch-adapters",
        ))
        .stderr("");
}

#[test]
fn rejects_direct_processes_and_arbitrary_git_argv_surfaces() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-core/src/leak.rs",
        b"use std::process::Command;\npub fn run_git(args: &[String]) { let _ = Command::new(\"git\").args(args); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "arbitrary Git operation surface outside the closed adapter",
        ))
        .stdout(predicate::str::contains(
            "direct production Git process; use the typed Git adapter",
        ))
        .stderr("");
}

#[test]
fn rejects_new_cli_subcommands_and_request_families() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-core/src/process.rs",
        OPERATIONS
            .replace("    Worktree,", "    UnsafeEscape,\n    Worktree,")
            .as_bytes(),
    );
    repository.write(
        "crates/larch-adapters/src/git/ops.rs",
        format!("{REQUESTS}git_op!(RawRequest, ExactDiff);\n").as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "GitCliOperation drifted from the closed #7671 exception set",
        ))
        .stdout(predicate::str::contains("UnsafeEscape"))
        .stdout(predicate::str::contains(
            "Git CLI request families drifted from the closed #7671 set",
        ))
        .stdout(predicate::str::contains("RawRequest"))
        .stderr("");
}

#[test]
fn rejects_non_atomic_command_registry_state() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    let stale = command_registry().replacen("owner = \"rust\"", "owner = \"python\"", 1);
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        stale.as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "non-atomic final Git command row: git amend-add",
        ))
        .stderr("");
}

#[test]
fn rejects_operation_matrix_drift_without_a_baseline() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "python/larch/state/git_probe.py",
        b"import subprocess\nsubprocess.run([\"git\", \"status\"], check=False)\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "production Git surface is missing from the matrix: python/larch/state/git_probe.py",
        ))
        .stdout(predicate::str::contains("later-domain\t#7677\tstatus"))
        .stderr("");
}

#[test]
fn rejects_stale_matrix_rows() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "docs/git-operation-inventory.md",
        inventory("missing.py\tlater-domain\t#7681\tstatus\n").as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "matrix row is no longer a detected production Git surface: missing.py",
        ))
        .stderr("");
}
