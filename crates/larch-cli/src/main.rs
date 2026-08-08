use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    io::ErrorKind,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::Duration,
};

use clap::{Args, CommandFactory, FromArgMatches, Parser, Subcommand};
use larch_cli::object_store_commands::{self, GcsArguments};
use larch_core::{ChangeKind, RepositoryStatus, StatusOptions, private_atomic_write};

mod admission_commands;
mod agent_commands;
mod agent_review;
mod argparse_compat;
mod bgjob_adapt;
mod bgjob_commands;
mod blocker_commands;
mod child_process;
mod ci_launcher_commands;
mod ci_timing;
pub(crate) mod claude_commands;
mod collector_commands;
mod complete_umbrella_commands;
mod dirty_tree_commands;
mod drafter_commands;
mod external_agent;
mod external_defaults_commands;
mod git_commands;
mod github_repository_resolution;
mod github_service;
mod gitleaks;
mod implement_launcher_commands;
mod issue_commands;
mod issue_create_commands;
mod issue_dependency_commands;
mod issue_input_commands;
mod issue_mutation_support;
mod issue_wire_commands;
mod kill_background;
mod launcher_support;
mod progress_commands;
mod push_network;
mod push_rebase;
mod python_verb;
mod release_assets;
mod release_common;
mod release_plugin_runtime;
mod release_prepare;
mod release_publish;
mod release_stage;
mod release_version;
mod run_lifecycle_commands;
mod run_log_cleanup_commands;
mod run_log_commands;
mod run_log_entry_commands;
pub(crate) mod run_log_migration_commands;
mod run_log_publication_commands;
#[rustfmt::skip]
mod run_log_flush_commands;
mod report_tokens_commands;
mod session_env_commands;
mod session_gate_commands;
mod session_lifecycle_commands;
mod slack_commands;
mod slot_binding;
mod stall_recovery_commands;
mod stall_recovery_reporting;
mod state_commands;
mod test_shards;
mod timing_commands;
mod tracking_issue_commands;
mod triage_commands;
mod umbrella_commands;
mod voter_dispatch_commands;
mod waterfall_commands;

use agent_commands::AgentCommand;
use ci_timing::CiTimingCommand;
use complete_umbrella_commands::CompleteUmbrellaCommand;
use external_defaults_commands::ExternalDefaultsCommand;
use git_commands::GitCommand;
use slack_commands::SlackCommand;
use test_shards::TestShardCommand;

#[derive(Parser)]
#[command(
    name = "larch",
    about = "Larch workflow automation",
    arg_required_else_help = true,
    subcommand_required = true
)]
struct Cli {
    #[command(subcommand)]
    domain: Domain,
}

#[derive(Subcommand)]
enum Domain {
    /// `/implement` entry admission, preflight, and fork bootstrap.
    #[command(subcommand)]
    Admission(AdmissionCommand),
    /// Vendor-agent launch and diagnostic commands.
    #[command(subcommand)]
    Agent(AgentCommand),
    /// Issue blocker discovery.
    #[command(subcommand)]
    Blocker(BlockerCommand),
    /// Native issue blocked-by dependency mutations.
    #[command(subcommand, name = "block-issue")]
    BlockIssue(BlockIssueCommand),
    /// Internal bootstrap commands used before installation completes.
    #[command(subcommand, hide = true)]
    Bootstrap(BootstrapCommand),
    /// Durable background-job compatibility commands.
    #[command(subcommand)]
    Bgjob(BgjobCommand),
    /// Collect GitHub Actions timing inputs for test rebalancing.
    #[command(subcommand)]
    CiTiming(CiTimingCommand),
    /// Serially complete and audit every direct leaf of one umbrella issue.
    #[command(subcommand)]
    CompleteUmbrella(CompleteUmbrellaCommand),
    /// Working-tree checkpoint and scope compatibility commands.
    #[command(subcommand)]
    DirtyTree(DirtyTreeCommand),
    /// External tool default readers.
    #[command(subcommand, name = "external-defaults")]
    ExternalDefaults(ExternalDefaultsCommand),
    /// Non-production commands that exercise dispatcher wiring.
    #[command(subcommand)]
    Example(ExampleCommand),
    /// Local Git repository commands.
    #[command(subcommand)]
    Git(GitSubcommand),
    /// GitHub issue reads and issue-body wire helpers.
    #[command(subcommand)]
    Issue(IssueCommand),
    /// The `larch:plan` issue-body block carrying the `/design` handoff.
    #[command(subcommand, name = "plan-block")]
    PlanBlock(PlanBlockCommand),
    /// One named `larch:<marker>` issue-body block.
    #[command(subcommand, name = "named-block")]
    NamedBlock(NamedBlockCommand),
    /// Implementation-plan readers.
    #[command(subcommand)]
    Plan(PlanCommand),
    /// The tracking issue's lifecycle: reads, comments, titles, and summaries.
    #[command(subcommand, name = "tracking-issue")]
    TrackingIssue(TrackingIssueCommand),
    /// Pre-`/design` issue verification: evidence, probes, and the one write.
    #[command(subcommand)]
    Triage(TriageCommand),
    /// Durable `/umbrella` preparation, record state, and completion proof.
    #[command(subcommand)]
    Umbrella(UmbrellaCommand),
    /// Envelopes that mark fetched text as data, never instructions.
    #[command(subcommand)]
    Untrusted(UntrustedCommand),
    /// Exact `KEY=value` stream readers.
    #[command(subcommand)]
    Kv(KvCommand),
    /// Repository policy lint commands.
    Lint(larch_lint::LintArguments),
    /// Plugin metadata commands.
    #[command(subcommand)]
    Plugin(PluginCommand),
    /// Clone-scoped progress breadcrumbs and the larch statusline.
    #[command(subcommand)]
    Progress(ProgressCommand),
    /// Narrow provider transports used by Python-owned run-log workflows.
    #[command(subcommand)]
    ObjectStore(ObjectStoreCommand),
    /// Release-maintenance commands.
    #[command(subcommand)]
    Release(ReleaseCommand),
    /// Token-cost analysis over the synchronized run-log corpus.
    #[command(subcommand, name = "report-tokens")]
    ReportTokens(ReportTokensCommand),
    /// Session state compatibility commands.
    #[command(subcommand)]
    Session(SessionCommand),
    /// Slack announcement helpers.
    #[command(subcommand)]
    Slack(SlackCommand),
    /// Stall-recovery state and validation commands.
    #[command(name = "stall-recovery", disable_help_flag = true)]
    StallRecovery(RawCompatibilityArguments),
    /// Pack and rewrite deterministic test-shard assignments.
    #[command(subcommand)]
    TestShard(TestShardCommand),
    /// Timing-ledger marks, records, dumps, and reports.
    #[command(subcommand)]
    Timing(TimingCommand),
    /// GitHub workflow helper commands.
    #[command(subcommand)]
    Gh(GhCommand),
    /// Push commands with typed Git network operations.
    #[command(subcommand)]
    Push(PushSubcommand),
    /// Committed run-log identity and layout helpers.
    #[command(subcommand, name = "run-log")]
    RunLog(RunLogCommand),
    /// Upgrade the installed larch plugin and executable.
    #[command(subcommand)]
    UpgradeLarch(UpgradeLarchCommand),
}

#[derive(Subcommand)]
enum RunLogCommand {
    /// Package one completed run-log staging tree as a deterministic archive.
    #[command(name = "archive", disable_help_flag = true)]
    Archive(RawCompatibilityArguments),
    /// Refresh recoverable artifacts after one implementation checkpoint.
    #[command(name = "checkpoint", disable_help_flag = true)]
    Checkpoint(RawCompatibilityArguments),
    /// Render and stage one filtered session transcript.
    #[command(name = "capture-transcript", disable_help_flag = true)]
    CaptureTranscript(RawCompatibilityArguments),
    /// Synthesize a v2 run manifest for one skill and run id.
    #[command(name = "init", disable_help_flag = true)]
    Init(RawCompatibilityArguments),
    /// Replace one batch artifact from a redacted, validated payload.
    #[command(name = "write", disable_help_flag = true)]
    Write(RawCompatibilityArguments),
    /// Publish one review round's included artifacts.
    #[command(name = "write-round", disable_help_flag = true)]
    WriteRound(RawCompatibilityArguments),
    /// Append one record to an append-mode batch artifact.
    #[command(name = "append", disable_help_flag = true)]
    Append(RawCompatibilityArguments),
    /// Append one execution-issue entry under a category heading.
    #[command(name = "append-entry", disable_help_flag = true)]
    AppendEntry(RawCompatibilityArguments),
    /// Append one formatted tool-failure entry with captured diagnostics.
    #[command(name = "append-failure", disable_help_flag = true)]
    AppendFailure(RawCompatibilityArguments),
    /// Report whether a known batch artifact exists.
    #[command(name = "exists", disable_help_flag = true)]
    Exists(RawCompatibilityArguments),
    /// Verify a published run directory against the required-files manifest.
    #[command(name = "verify-completeness", disable_help_flag = true)]
    VerifyCompleteness(RawCompatibilityArguments),
    /// Update one versioned run-log manifest with durable atomic publication.
    #[command(name = "manifest", disable_help_flag = true)]
    Manifest(RawCompatibilityArguments),
    /// Verify and atomically materialize one archived run-log tree.
    #[command(name = "materialize", disable_help_flag = true)]
    Materialize(RawCompatibilityArguments),
    /// Plan, apply, and independently verify the one-time run-log layout migration.
    #[command(name = "migrate-layout", disable_help_flag = true)]
    MigrateLayout(RawCompatibilityArguments),
    /// Clean redundant artifacts from completed historical implement run logs.
    #[command(name = "cleanup-implement-logs", disable_help_flag = true)]
    CleanupImplementLogs(RawCompatibilityArguments),
    /// Publish one immutable completed run archive and verified local cache.
    #[command(name = "publish", disable_help_flag = true)]
    Publish(RawCompatibilityArguments),
    /// Publish the session's redacted quiet logs as a run's breadcrumbs.
    #[command(name = "publish-breadcrumbs", disable_help_flag = true)]
    PublishBreadcrumbs(RawCompatibilityArguments),
    /// Synchronize the immutable remote run-log corpus into the local cache.
    #[command(name = "sync", disable_help_flag = true)]
    Sync(RawCompatibilityArguments),
    /// Correct historical Cursor cost lines in committed run summaries.
    #[command(name = "retro-fix-cursor", disable_help_flag = true)]
    RetroFixCursor(RawCompatibilityArguments),
    /// Rewrite historical session transcripts to the v3 redaction policy.
    #[command(name = "retro-v3-sweep", disable_help_flag = true)]
    RetroV3Sweep(RawCompatibilityArguments),
    /// Prepare the complete mutable snapshot immediately before publication.
    #[command(name = "prepare-terminal-snapshot", disable_help_flag = true)]
    PrepareTerminalSnapshot(RawCompatibilityArguments),
    /// Refresh the mutable implement run-log staging tree.
    #[command(name = "refresh", disable_help_flag = true)]
    Refresh(RawCompatibilityArguments),
    /// Terminalize a run as operator-cancelled.
    #[command(name = "lifecycle-cancel")]
    LifecycleCancel(run_lifecycle_commands::LifecycleTerminalArguments),
    /// Terminalize a run after a non-error early return.
    #[command(name = "lifecycle-early-return")]
    LifecycleEarlyReturn(run_lifecycle_commands::LifecycleTerminalArguments),
    /// Terminalize a failed run.
    #[command(name = "lifecycle-failure")]
    LifecycleFailure(run_lifecycle_commands::LifecycleTerminalArguments),
    /// Terminalize a successful run.
    #[command(name = "lifecycle-finalize")]
    LifecycleFinalize(run_lifecycle_commands::LifecycleTerminalArguments),
    /// Admit and persist one shared lifecycle run.
    #[command(name = "lifecycle-start")]
    LifecycleStart(run_lifecycle_commands::LifecycleStartArguments),
    /// Resolve storage configuration and run provider prefix preflight.
    #[command(name = "storage-preflight", disable_help_flag = true)]
    StoragePreflight(RawCompatibilityArguments),
    /// Emit `VALID=true|false` for a run-log path slug.
    #[command(name = "validate-run-id", disable_help_flag = true)]
    ValidateRunId(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum BgjobCommand {
    /// Start or reattach to a durable background job.
    #[command(disable_help_flag = true)]
    Adapt(RawCompatibilityArguments),
    /// Launch a detached background job for one workflow step.
    #[command(disable_help_flag = true)]
    Start(RawCompatibilityArguments),
    /// Wait one bounded chunk for a background job to finish.
    #[command(disable_help_flag = true)]
    Wait(RawCompatibilityArguments),
    /// Print one row per durable background-job registry entry.
    #[command(disable_help_flag = true)]
    Status(RawCompatibilityArguments),
    /// Remove finished, unreadable, and expired registry entries.
    #[command(disable_help_flag = true)]
    Reap(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum ReportTokensCommand {
    /// Price the synchronized run-log corpus and render the token report.
    #[command(disable_help_flag = true)]
    Analyze(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum TimingCommand {
    /// Record one step mark in the resolved timing ledger.
    #[command(disable_help_flag = true)]
    Mark(RawCompatibilityArguments),
    /// Record one vendor task in the resolved timing ledger.
    #[command(name = "record-vendor-task", disable_help_flag = true)]
    RecordVendorTask(RawCompatibilityArguments),
    /// Record one review round in the resolved timing ledger.
    #[command(name = "record-round", disable_help_flag = true)]
    RecordRound(RawCompatibilityArguments),
    /// Print the resolved ledger path and its raw rows.
    #[command(disable_help_flag = true)]
    Dump(RawCompatibilityArguments),
    /// Render the timing report for the resolved ledger.
    #[command(disable_help_flag = true)]
    Report(RawCompatibilityArguments),
    /// Run one command and publish its wall-clock duration.
    #[command(name = "harness-mark", disable_help_flag = true)]
    HarnessMark(RawCompatibilityArguments),
    /// Mark one `/implement` step in the token and timing ledgers.
    #[command(name = "telemetry-mark", disable_help_flag = true)]
    TelemetryMark(RawCompatibilityArguments),
    /// Print the canonical `--timing-task-kind` allow-list.
    #[command(name = "task-kinds", disable_help_flag = true)]
    TaskKinds(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum ProgressCommand {
    /// Point the clone's active-run pointer at one run.
    #[command(disable_help_flag = true)]
    Activate(RawCompatibilityArguments),
    /// Clear the active-run pointer when the named run still owns it.
    #[command(disable_help_flag = true)]
    Deactivate(RawCompatibilityArguments),
    /// Clear the active-run pointer regardless of its prior owner.
    #[command(disable_help_flag = true)]
    Clear(RawCompatibilityArguments),
    /// Append one breadcrumb to the active run or a named run.
    #[command(disable_help_flag = true)]
    Note(RawCompatibilityArguments),
    /// Render the larch statusline for the payload on stdin.
    #[command(disable_help_flag = true)]
    Statusline(RawCompatibilityArguments),
    /// Clear a stale active-run pointer when a fresh session starts.
    #[command(disable_help_flag = true)]
    SessionReset(RawCompatibilityArguments),
    /// Install the larch statusline into clone-local Claude settings.
    #[command(disable_help_flag = true)]
    InstallStatusline(RawCompatibilityArguments),
    /// Render the review-phase detail section for a completed workflow.
    #[command(name = "render-phase-detail", disable_help_flag = true)]
    RenderPhaseDetail(RawCompatibilityArguments),
    /// Write one `/design` review round's metadata artifact.
    #[command(name = "write-design-round-meta", disable_help_flag = true)]
    WriteDesignRoundMeta(RawCompatibilityArguments),
    /// Write one `/implement` review round's metadata artifact.
    #[command(name = "write-implement-round-meta", disable_help_flag = true)]
    WriteImplementRoundMeta(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum AdmissionCommand {
    /// Publish the fork metadata a `--forked` run consumes before Step 0.
    #[command(disable_help_flag = true)]
    ForkEnv(RawCompatibilityArguments),
    /// Decide whether one issue may enter a `/implement` run.
    #[command(disable_help_flag = true)]
    Gate(RawCompatibilityArguments),
    /// Enforce the clean-main entry contract and sync with `origin/main`.
    #[command(disable_help_flag = true)]
    Preflight(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum BlockerCommand {
    /// Emit the space-joined open blockers for one issue.
    #[command(disable_help_flag = true)]
    AllOpen(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum BlockIssueCommand {
    /// Record `ISSUE_A` as blocked by `ISSUE_B` and verify the relation.
    #[command(name = "add-blocked-by", disable_help_flag = true)]
    AddBlockedBy(RawCompatibilityArguments),
    /// Drop the `ISSUE_A` blocked-by `ISSUE_B` relation and verify its absence.
    #[command(name = "remove-blocked-by", disable_help_flag = true)]
    RemoveBlockedBy(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum IssueCommand {
    /// Record one issue as blocked by another and prove the edge by read-back.
    #[command(name = "add-blocked-by", disable_help_flag = true)]
    AddBlockedBy(RawCompatibilityArguments),
    /// Attach one direct native sub-issue and prove it by read-back.
    #[command(name = "add-sub-issue", disable_help_flag = true)]
    AddSubIssue(RawCompatibilityArguments),
    /// Allocate the bounded Phase 2 dedup candidate set from stdin rows.
    #[command(name = "allocate-candidates", disable_help_flag = true)]
    AllocateCandidates(RawCompatibilityArguments),
    /// Close one orphaned issue left by a partially created batch.
    #[command(name = "cleanup-failed", disable_help_flag = true)]
    CleanupFailed(RawCompatibilityArguments),
    /// Materialize one issue's title and body into a caller-named directory.
    #[command(disable_help_flag = true)]
    Context(RawCompatibilityArguments),
    /// File one GitHub issue and publish its number, URL, and node id.
    #[command(name = "create-one", disable_help_flag = true)]
    CreateOne(RawCompatibilityArguments),
    /// Write the untrusted candidate corpus Phase 2 reasons over.
    #[command(name = "fetch-issue-details", disable_help_flag = true)]
    FetchIssueDetails(RawCompatibilityArguments),
    /// Emit one issue field as the single `VALUE` row.
    #[command(disable_help_flag = true)]
    Info(RawCompatibilityArguments),
    /// Insert one bracketed signal marker into an issue title.
    #[command(name = "insert-signal-marker", disable_help_flag = true)]
    InsertSignalMarker(RawCompatibilityArguments),
    /// Publish the open and recently closed issue snapshot as a TSV.
    #[command(name = "list-issues", disable_help_flag = true)]
    ListIssues(RawCompatibilityArguments),
    /// Parse one batch-input file into per-item rows and body files.
    #[command(name = "parse-input", disable_help_flag = true)]
    ParseInput(RawCompatibilityArguments),
    /// Emit one issue's state, URL, and pull-request discrimination.
    #[command(disable_help_flag = true)]
    State(RawCompatibilityArguments),
    /// Print the `jq` archival-eligibility filter.
    #[command(name = "title-archival-jq", disable_help_flag = true)]
    TitleArchivalJq(RawCompatibilityArguments),
    /// Report the archival-eligibility predicates for one issue title.
    #[command(name = "title-eligibility", disable_help_flag = true)]
    TitleEligibility(RawCompatibilityArguments),
    /// Record that one `/issue` run reached its end.
    #[command(name = "write-sentinel", disable_help_flag = true)]
    WriteSentinel(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum PlanBlockCommand {
    /// Materialize one issue's `larch:plan` inner text into a file.
    #[command(disable_help_flag = true)]
    Read(RawCompatibilityArguments),
    /// Remove the `larch:plan` block from a body file or stdin.
    #[command(name = "strip-body", disable_help_flag = true)]
    StripBody(RawCompatibilityArguments),
    /// Write, replace, or delete one issue's `larch:plan` block.
    #[command(disable_help_flag = true)]
    Write(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum NamedBlockCommand {
    /// Write, replace, or delete one named issue-body block.
    #[command(disable_help_flag = true)]
    Write(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum PlanCommand {
    /// Publish the scope paths one implementation plan declares.
    #[command(name = "scope-paths", disable_help_flag = true)]
    ScopePaths(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum TrackingIssueCommand {
    /// Render one issue and its human comments into a task file.
    #[command(disable_help_flag = true)]
    Read(RawCompatibilityArguments),
    /// File one tracking issue from a drafted title and body file.
    #[command(name = "create-issue", disable_help_flag = true)]
    CreateIssue(RawCompatibilityArguments),
    /// Append one comment, optionally tagged with a lifecycle marker.
    #[command(name = "append-comment", disable_help_flag = true)]
    AppendComment(RawCompatibilityArguments),
    /// Move one tracking title to the prefix a lifecycle state names.
    #[command(disable_help_flag = true)]
    Rename(RawCompatibilityArguments),
    /// Tag one title as a disproved finding.
    #[command(name = "mark-false-positive", disable_help_flag = true)]
    MarkFalsePositive(RawCompatibilityArguments),
    /// Keep exactly one marker-keyed summary comment on the issue.
    #[command(name = "upsert-summary", disable_help_flag = true)]
    UpsertSummary(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum TriageCommand {
    /// Read evidence only through an immutable fixed-origin object.
    #[command(disable_help_flag = true)]
    Inspect(RawCompatibilityArguments),
    /// Run one fixed, bounded, no-shell reproduction probe.
    #[command(disable_help_flag = true)]
    Probe(RawCompatibilityArguments),
    /// Apply one verified verdict with compare-and-swap checks.
    #[command(disable_help_flag = true)]
    Apply(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum UmbrellaCommand {
    /// Validate one source issue and publish its bounded snapshot.
    #[command(disable_help_flag = true)]
    Prepare(RawCompatibilityArguments),
    /// Publish the durable proposal record before any leaf is filed.
    #[command(name = "persist-proposal", disable_help_flag = true)]
    PersistProposal(RawCompatibilityArguments),
    /// Record that one named leaf was handed to `/issue`.
    #[command(name = "mark-in-flight", disable_help_flag = true)]
    MarkInFlight(RawCompatibilityArguments),
    /// Bind one named leaf to the issue `/issue` created for it.
    #[command(name = "record-resolved", disable_help_flag = true)]
    RecordResolved(RawCompatibilityArguments),
    /// Bind one in-flight leaf to the single remote issue carrying it.
    #[command(name = "reconcile-in-flight", disable_help_flag = true)]
    ReconcileInFlight(RawCompatibilityArguments),
    /// Convert the source issue into its final `[UMBRELLA]` title and body.
    #[command(disable_help_flag = true)]
    Mutate(RawCompatibilityArguments),
    /// Prove the recorded graph landed, then publish the completion sentinel.
    #[command(disable_help_flag = true)]
    Verify(RawCompatibilityArguments),
    /// Prove one child's completion sentinel against the approved partition.
    #[command(name = "verify-completion", disable_help_flag = true)]
    VerifyCompletion(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum UntrustedCommand {
    /// Wrap `--text` or stdin in a labelled, redacted content block.
    #[command(name = "content-block", disable_help_flag = true)]
    ContentBlock(RawCompatibilityArguments),
    /// Wrap one file's contents in a labelled, redacted content block.
    #[command(name = "file-block", disable_help_flag = true)]
    FileBlock(RawCompatibilityArguments),
    /// Redact stdin and escape its markup delimiters.
    #[command(name = "redact-stream", disable_help_flag = true)]
    RedactStream(RawCompatibilityArguments),
    /// Escape stdin for an XML attribute.
    #[command(name = "xml-escape-attr", disable_help_flag = true)]
    XmlEscapeAttr(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum KvCommand {
    /// Extract one value from `KEY=value` input.
    #[command(disable_help_flag = true)]
    Get(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum SessionCommand {
    /// Remove a session temporary directory confined to the session roots.
    #[command(disable_help_flag = true)]
    CleanupTmpdir(RawCompatibilityArguments),
    /// Authorize one live GitHub issue mutation for a session-backed caller.
    #[command(disable_help_flag = true)]
    CheckLiveMutationAuth(RawCompatibilityArguments),
    /// Resolve the `/implement` or `/design` entry gate from branch facts.
    #[command(disable_help_flag = true)]
    EntryGate(RawCompatibilityArguments),
    /// Terminate background processes scoped to a session tmpdir.
    #[command(disable_help_flag = true)]
    KillBackgroundProcesses(RawCompatibilityArguments),
    /// Read one value from a session environment file.
    #[command(disable_help_flag = true)]
    ReadKey(RawCompatibilityArguments),
    /// Read several values from one session environment file.
    #[command(disable_help_flag = true)]
    ReadKeys(RawCompatibilityArguments),
    /// Fail closed when `CLAUDE_PLUGIN_ROOT` is unset or unexpanded.
    #[command(disable_help_flag = true)]
    RequirePluginRoot(RawCompatibilityArguments),
    /// Print the live implement temporary directory for one clone.
    #[command(disable_help_flag = true)]
    ResolveImplementTmpdir(RawCompatibilityArguments),
    /// Validate a design temporary directory against the session allowlist.
    #[command(disable_help_flag = true)]
    ValidateDesignTmpdir(RawCompatibilityArguments),
    /// Idempotently publish a session identity file.
    #[command(disable_help_flag = true)]
    WriteId(RawCompatibilityArguments),
    /// Write the implement session environment file.
    #[command(disable_help_flag = true)]
    WriteEnv(RawCompatibilityArguments),
    /// Write the design session environment file and its PID-keyed pointer.
    #[command(disable_help_flag = true)]
    WriteDesignEnv(RawCompatibilityArguments),
    /// Write the implement current-env pointer and stable launcher.
    #[command(disable_help_flag = true)]
    WriteImplementEnv(RawCompatibilityArguments),
    /// Remove the implement current-env pointer.
    #[command(disable_help_flag = true)]
    ClearImplementPointer(RawCompatibilityArguments),
    /// Persist validated implement run flags.
    #[command(disable_help_flag = true)]
    PersistRunFlags(RawCompatibilityArguments),
    /// Write the design run-params document.
    #[command(disable_help_flag = true)]
    WriteRunParams(RawCompatibilityArguments),
    /// Rebuild finalize state from the durable ship-pr state file.
    #[command(disable_help_flag = true)]
    RestoreFinalizeState(RawCompatibilityArguments),
    /// Resolve a design session-env pointer to its trusted target.
    #[command(disable_help_flag = true)]
    ResolveTrustedDesignEnv(RawCompatibilityArguments),
}

#[derive(Subcommand)]
enum DirtyTreeCommand {
    /// Classify tracked and new untracked paths against a baseline.
    #[command(disable_help_flag = true)]
    Baseline(RawCompatibilityArguments),
    /// Report whether a consumer worktree is clean.
    #[command(disable_help_flag = true)]
    Checkpoint(RawCompatibilityArguments),
    /// Reject recovered paths that are outside the plan scope.
    #[command(disable_help_flag = true)]
    ScopeCheck(RawCompatibilityArguments),
    /// Detect a scope-reduction review marker.
    #[command(disable_help_flag = true)]
    ScopeMarker(RawCompatibilityArguments),
}

#[derive(Args)]
#[command(trailing_var_arg = true)]
struct RawCompatibilityArguments {
    /// Raw arguments parsed by the legacy-compatible command boundary.
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

#[derive(Subcommand)]
enum GitSubcommand {
    /// Stage paths and amend them into the current commit.
    AmendAdd(MutationPathsArguments),
    /// Emit `HEAD_SHA` and `CURRENT_BRANCH` for the cwd repository.
    BranchInfo(TrailingArguments),
    /// Classify repository changes against an untracked-path baseline.
    CheckPhantomDirty(CheckPhantomDirtyArguments),
    /// Probe whether a remote branch exists via typed ls-remote.
    CheckRemoteBranch(TrailingArguments),
    /// Classify local main synchronization against origin/main.
    CheckMainSync(TrailingArguments),
    /// Check out the current side of conflicted paths.
    CheckoutOurs(CheckoutOursArguments),
    /// Report whether the worktree is clean using machine-readable key/value rows.
    CleanTree(CleanTreeArguments),
    /// Stage optional paths and create a commit.
    Commit(CommitArguments),
    /// Print the files and index stages that are currently conflicted.
    ConflictFiles,
    /// Count commits on `HEAD` since `origin/main` or `main`.
    CountCommits(TrailingArguments),
    /// Emit `BRANCH` for the current symbolic `HEAD`.
    CurrentBranch(TrailingArguments),
    /// Classify phantom paths and append advisory warnings to the run ledger.
    PhantomProbe(PhantomProbeArguments),
    /// Abort an in-progress rebase, succeeding when no rebase is active.
    RebaseAbort(RebaseControlArguments),
    /// Skip the current commit in an in-progress rebase.
    RebaseSkip(RebaseControlArguments),
    /// Print the blob at an index conflict stage.
    ShowStage(TrailingArguments),
    /// Update a non-checked-out local main branch from its remote-tracking ref.
    SyncLocalMain(TrailingArguments),
    /// Atomically write the sorted untracked-path baseline to an output file.
    SnapshotUntracked(SnapshotUntrackedArguments),
    /// Stage one or more paths.
    Stage(MutationPathsArguments),
}

#[derive(Args)]
struct MutationPathsArguments {
    #[arg(allow_hyphen_values = true)]
    paths: Vec<PathBuf>,
}

#[derive(Args)]
struct CommitArguments {
    #[arg(short = 'm', default_value = "")]
    message: String,
    #[arg(long)]
    no_trailer: bool,
    #[arg(long)]
    only: bool,
    #[arg(long)]
    pathspec_from_file: Option<PathBuf>,
    #[arg(long)]
    pathspec_file_nul: bool,
    #[arg(allow_hyphen_values = true)]
    files: Vec<PathBuf>,
}

#[derive(Args)]
#[command(trailing_var_arg = true, disable_help_flag = true)]
struct CheckPhantomDirtyArguments {
    /// Raw compatibility arguments; parse errors are advisory command results.
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

#[derive(Args)]
struct CheckoutOursArguments {
    /// Conflicted paths to replace with the current side.
    #[arg(allow_hyphen_values = true)]
    paths: Vec<PathBuf>,
}

#[derive(Args)]
struct RebaseControlArguments {
    #[arg(allow_hyphen_values = true)]
    extra: Vec<OsString>,
}

#[derive(Args, Clone, Copy)]
struct CleanTreeArguments {
    /// Treat a repository probe failure as an error instead of a clean tree.
    #[arg(long)]
    fail_closed: bool,
}

#[derive(Args)]
struct SnapshotUntrackedArguments {
    /// File that receives the sorted untracked-path baseline.
    #[arg(long)]
    output: Option<std::path::PathBuf>,
    /// Separate output paths with NUL bytes rather than line feeds.
    #[arg(long)]
    nul: bool,
}

#[derive(Args)]
struct PhantomProbeArguments {
    /// Stable token identifying the checkpoint that invoked the probe.
    #[arg(long)]
    step: String,
    /// Override the session's untracked-path baseline.
    #[arg(long)]
    baseline_file: Option<PathBuf>,
}

#[derive(Args)]
struct TrailingArguments {
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    args: Vec<String>,
}

#[derive(Subcommand)]
enum BootstrapCommand {
    /// Print the compiled version and target as machine-readable JSON.
    SelfCheck,
}

#[derive(Subcommand)]
enum ExampleCommand {
    /// Print a message through the core library.
    Echo(EchoArguments),
}

#[derive(Subcommand)]
enum ObjectStoreCommand {
    /// Use Google Cloud Storage through validated Application Default Credentials.
    Gcs(GcsArguments),
}

#[derive(Subcommand)]
enum ReleaseCommand {
    /// Validate the tagged release identity against plugin and Cargo versions.
    AssetCandidate(AssetCandidateArguments),
    /// Resolve the exact tag-triggered release asset workflow run.
    AssetRun(AssetRunArguments),
    /// Classify the semantic version bump for the public plugin surface.
    ClassifyBump(ClassifyBumpArguments),
    /// Collect matrix archives into the final release asset set.
    CollectAssets(CollectAssetsArguments),
    /// Enable and verify release repository policy.
    EnsurePolicy(EnsurePolicyArguments),
    /// Publish, attest, and promote the merged release candidate.
    Finish(FinishReleaseArguments),
    /// Package one target archive and metadata fragment.
    PackageAsset(PackageAssetArguments),
    /// Prepare the release window, PR list, and aggregate bump.
    Prepare(PrepareReleaseArguments),
    /// Promote one immutable release to Latest.
    Promote(PromoteReleaseArguments),
    /// Promote the newest immutable non-draft release to Latest.
    PromoteLatest(PromoteLatestArguments),
    /// Generate or validate the runtime-only plugin projection.
    PluginRuntime(PluginRuntimeArguments),
    /// Update every synchronized release version surface.
    SetVersion(SetVersionArguments),
    /// Tag the candidate and create or resume its mutable draft.
    Stage(StageReleaseArguments),
    /// Validate the final release asset allowlist.
    ValidateAssets(ValidateAssetsArguments),
    /// Validate the candidate-bound draft and complete asset set.
    ValidateDraft(ValidateDraftArguments),
}

#[derive(Subcommand)]
enum PluginCommand {
    /// Print the active plugin version as a machine-readable row.
    ReadVersion(TrailingArguments),
}

#[derive(Args)]
struct AssetCandidateArguments {
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    tag: String,
    #[arg(long)]
    source_commit: String,
}

#[derive(Args)]
struct AssetRunArguments {
    #[arg(long = "repo")]
    repository: String,
    #[arg(long)]
    tag: String,
    #[arg(long)]
    source_commit: String,
}

#[derive(Args)]
struct EnsurePolicyArguments {
    #[arg(long = "repo")]
    repository: String,
}

#[derive(Args)]
struct FinishReleaseArguments {
    #[arg(long)]
    version: String,
    #[arg(long = "repo")]
    repository: String,
    #[arg(long)]
    pr: String,
    #[arg(long)]
    source_commit: String,
}

#[derive(Args)]
struct PromoteReleaseArguments {
    version: String,
    #[arg(long = "repo")]
    repository: Option<String>,
}

#[derive(Args)]
struct PromoteLatestArguments {
    #[arg(long = "repo", default_value = "character-ai/larch")]
    repository: String,
    #[arg(long)]
    dry_run: bool,
}

#[derive(Args)]
struct StageReleaseArguments {
    #[arg(long)]
    version: String,
    #[arg(long)]
    notes_file: PathBuf,
    #[arg(long = "repo")]
    repository: String,
    #[arg(long)]
    pr: String,
}

#[derive(Args)]
struct ValidateDraftArguments {
    #[arg(long)]
    version: String,
    #[arg(long = "repo")]
    repository: String,
    #[arg(long)]
    pr: String,
    #[arg(long)]
    source_commit: String,
}

#[derive(Args)]
struct PackageAssetArguments {
    #[arg(long)]
    version: String,
    #[arg(long)]
    tag: String,
    #[arg(long)]
    source_commit: String,
    #[arg(long)]
    target: String,
    #[arg(long)]
    binary: PathBuf,
    #[arg(long = "license")]
    license: PathBuf,
    #[arg(long)]
    output_dir: PathBuf,
}

#[derive(Args)]
struct CollectAssetsArguments {
    #[arg(long)]
    version: String,
    #[arg(long)]
    tag: String,
    #[arg(long)]
    source_commit: String,
    #[arg(long)]
    input_dir: PathBuf,
    #[arg(long)]
    output_dir: PathBuf,
    #[arg(long = "license")]
    license: PathBuf,
}

#[derive(Args)]
struct ValidateAssetsArguments {
    #[arg(long)]
    version: String,
    #[arg(long)]
    tag: String,
    #[arg(long)]
    source_commit: String,
    #[arg(long)]
    asset_dir: PathBuf,
    #[arg(long = "license")]
    license: PathBuf,
    #[arg(long)]
    verify_attestations: bool,
}

#[derive(Args)]
struct ClassifyBumpArguments {
    #[arg(long)]
    base: Option<String>,
    #[arg(long)]
    head: Option<String>,
}

#[derive(Args)]
struct PrepareReleaseArguments {
    #[arg(long = "repo", default_value = "character-ai/larch", value_parser = parse_repository)]
    repository: larch_core::GitHubRepositoryRef,
    #[arg(long, value_parser = ["major", "minor", "patch"])]
    bump: Option<String>,
    #[arg(long, required = true)]
    out_dir: PathBuf,
}

#[derive(Args)]
struct SetVersionArguments {
    version: String,
}

#[derive(Subcommand)]
enum UpgradeLarchCommand {
    /// Resolve the cache root used by release Step 7.
    ReleaseStep7Root(ReleaseStep7Arguments),
    /// Upgrade to the latest verified stable release.
    Run(UpgradeLarchRunArguments),
    /// Print the legacy sparse-checkout allowlist.
    SparseDirs,
}

#[derive(Args)]
struct UpgradeLarchRunArguments {
    /// Use one validated installed root for release Step 7.
    #[arg(long, hide = true)]
    plugin_root: Option<PathBuf>,
}

#[derive(Args)]
struct ReleaseStep7Arguments {
    /// Current version used only to disambiguate one cache directory.
    #[arg(long, conflicts_with = "positional_current_version")]
    current_version: Option<String>,
    /// Backward-compatible positional spelling of the current version.
    #[arg(conflicts_with = "current_version")]
    positional_current_version: Option<String>,
}

#[derive(Args)]
struct PluginRuntimeArguments {
    /// Validate projection drift without changing the worktree.
    #[arg(long)]
    check: bool,
}

#[derive(Subcommand)]
enum GhCommand {
    /// Parse a remote name or URL into OWNER/REPO.
    RemoteRepo(TrailingArguments),
    /// Resolve the ambient GitHub repository slug for the cwd.
    ResolveRepo(TrailingArguments),
    /// Print the complete log archive for a workflow run.
    RunLogs(RunLogsArguments),
    /// Print the retained workflow-path placeholder.
    WorkflowPath,
}

#[derive(Subcommand)]
enum PushSubcommand {
    /// Push the current branch to its explicit origin branch ref.
    Branch(TrailingArguments),
    /// Force-push the current branch with a lease.
    Force(PushForceArguments),
    /// Rebase the current branch onto its base, then optionally force-push.
    Rebase(TrailingArguments),
    /// Rebase checkpoint probe with trivial-conflict pre-pass and phantom tail.
    CheckpointProbe(TrailingArguments),
}

#[derive(Args)]
struct PushForceArguments {
    #[arg(long)]
    expected_remote_oid: Option<String>,
}

#[derive(Args)]
struct RunLogsArguments {
    /// Numeric GitHub Actions workflow run identifier.
    #[arg(long)]
    run_id: u64,
    /// GitHub repository in OWNER/REPO form.
    #[arg(long = "repo", value_parser = parse_repository)]
    repository: larch_core::GitHubRepositoryRef,
}

#[derive(Args)]
struct EchoArguments {
    /// Message to print.
    message: String,
}

/// Dispatch one `session` verb to its command module.
fn run_session(command: SessionCommand) -> ExitCode {
    match command {
        SessionCommand::CheckLiveMutationAuth(arguments) => {
            session_gate_commands::check_live_mutation_auth_command(&arguments.arguments)
        }
        SessionCommand::EntryGate(arguments) => {
            session_gate_commands::entry_gate(&arguments.arguments)
        }
        SessionCommand::KillBackgroundProcesses(arguments) => {
            kill_background::kill_background_processes(&arguments.arguments)
        }
        SessionCommand::ReadKey(arguments) => state_commands::read_key(&arguments.arguments),
        SessionCommand::ReadKeys(arguments) => state_commands::read_keys(&arguments.arguments),
        SessionCommand::CleanupTmpdir(arguments) => {
            session_lifecycle_commands::cleanup_tmpdir(&arguments.arguments)
        }
        SessionCommand::RequirePluginRoot(arguments) => {
            session_lifecycle_commands::require_plugin_root(&arguments.arguments)
        }
        SessionCommand::ResolveImplementTmpdir(arguments) => {
            session_lifecycle_commands::resolve_implement_tmpdir_command(&arguments.arguments)
        }
        SessionCommand::ValidateDesignTmpdir(arguments) => {
            session_lifecycle_commands::validate_design_tmpdir_command(&arguments.arguments)
        }
        SessionCommand::WriteId(arguments) => {
            session_lifecycle_commands::write_id(&arguments.arguments)
        }
        SessionCommand::WriteEnv(arguments) => {
            session_env_commands::write_env(&arguments.arguments)
        }
        SessionCommand::WriteDesignEnv(arguments) => {
            session_env_commands::write_design_env(&arguments.arguments)
        }
        SessionCommand::WriteImplementEnv(arguments) => {
            session_env_commands::write_implement_env(&arguments.arguments)
        }
        SessionCommand::ClearImplementPointer(arguments) => {
            session_env_commands::clear_implement_pointer(&arguments.arguments)
        }
        SessionCommand::PersistRunFlags(arguments) => {
            session_env_commands::persist_run_flags(&arguments.arguments)
        }
        SessionCommand::WriteRunParams(arguments) => {
            session_env_commands::write_run_params(&arguments.arguments)
        }
        SessionCommand::RestoreFinalizeState(arguments) => {
            session_env_commands::restore_finalize_state(&arguments.arguments)
        }
        SessionCommand::ResolveTrustedDesignEnv(arguments) => {
            session_env_commands::resolve_trusted_design_env(&arguments.arguments)
        }
    }
}

#[allow(clippy::too_many_lines)] // Domain dispatch enumerates every Rust-owned command pair.
fn run(
    cli: Cli,
    metadata: larch_core::BuildMetadata,
) -> Result<ExitCode, larch_adapters::upgrade_larch::Failure> {
    match cli.domain {
        Domain::Agent(command) => Ok(agent_commands::run(command)),
        Domain::Bootstrap(BootstrapCommand::SelfCheck) => {
            println!("{}", larch_core::bootstrap_self_check(metadata));
            Ok(ExitCode::SUCCESS)
        }
        Domain::Bgjob(BgjobCommand::Adapt(arguments)) => {
            Ok(bgjob_adapt::adapt(&arguments.arguments))
        }
        Domain::Bgjob(BgjobCommand::Start(arguments)) => {
            Ok(bgjob_commands::start(&arguments.arguments))
        }
        Domain::Bgjob(BgjobCommand::Wait(arguments)) => {
            Ok(bgjob_commands::wait(&arguments.arguments))
        }
        Domain::Bgjob(BgjobCommand::Status(arguments)) => {
            Ok(bgjob_commands::status(&arguments.arguments))
        }
        Domain::Bgjob(BgjobCommand::Reap(arguments)) => {
            Ok(bgjob_commands::reap(&arguments.arguments))
        }
        Domain::CiTiming(command) => Ok(ci_timing::run(command)),
        Domain::CompleteUmbrella(command) => Ok(complete_umbrella_commands::run(command)),
        Domain::DirtyTree(command) => Ok(match command {
            DirtyTreeCommand::Baseline(arguments) => {
                let raw = dirty_tree_raw_arguments("baseline");
                dirty_tree_commands::baseline(raw.as_deref().unwrap_or(&arguments.arguments))
            }
            DirtyTreeCommand::Checkpoint(arguments) => {
                let raw = dirty_tree_raw_arguments("checkpoint");
                dirty_tree_commands::checkpoint(raw.as_deref().unwrap_or(&arguments.arguments))
            }
            DirtyTreeCommand::ScopeCheck(arguments) => {
                let raw = dirty_tree_raw_arguments("scope-check");
                dirty_tree_commands::scope_check(raw.as_deref().unwrap_or(&arguments.arguments))
            }
            DirtyTreeCommand::ScopeMarker(arguments) => {
                let raw = dirty_tree_raw_arguments("scope-marker");
                dirty_tree_commands::scope_marker(raw.as_deref().unwrap_or(&arguments.arguments))
            }
        }),
        Domain::ExternalDefaults(command) => Ok(external_defaults_commands::run(command)),
        Domain::Example(ExampleCommand::Echo(arguments)) => {
            println!("{}", larch_core::example::echo(&arguments.message));
            Ok(ExitCode::SUCCESS)
        }
        Domain::Admission(AdmissionCommand::ForkEnv(arguments)) => {
            Ok(admission_commands::fork_env(&arguments.arguments))
        }
        Domain::Admission(AdmissionCommand::Gate(arguments)) => {
            Ok(admission_commands::gate(&arguments.arguments))
        }
        Domain::Admission(AdmissionCommand::Preflight(arguments)) => {
            Ok(admission_commands::preflight(&arguments.arguments))
        }
        Domain::Blocker(BlockerCommand::AllOpen(arguments)) => {
            Ok(blocker_commands::all_open(&arguments.arguments))
        }
        Domain::BlockIssue(BlockIssueCommand::AddBlockedBy(arguments)) => Ok(
            issue_dependency_commands::block_issue_add(&arguments.arguments),
        ),
        Domain::BlockIssue(BlockIssueCommand::RemoveBlockedBy(arguments)) => Ok(
            issue_dependency_commands::block_issue_remove(&arguments.arguments),
        ),
        Domain::Git(command) => run_git(command).map_err(command_failure),
        Domain::Issue(command) => Ok(match command {
            IssueCommand::AddBlockedBy(arguments) => {
                issue_dependency_commands::add_blocked_by(&arguments.arguments)
            }
            IssueCommand::AddSubIssue(arguments) => {
                issue_dependency_commands::add_sub_issue(&arguments.arguments)
            }
            IssueCommand::AllocateCandidates(arguments) => {
                issue_input_commands::allocate_candidates(&arguments.arguments)
            }
            IssueCommand::CleanupFailed(arguments) => {
                issue_create_commands::cleanup_failed(&arguments.arguments)
            }
            IssueCommand::Context(arguments) => issue_commands::context(&arguments.arguments),
            IssueCommand::CreateOne(arguments) => {
                issue_create_commands::create_one(&arguments.arguments)
            }
            IssueCommand::FetchIssueDetails(arguments) => {
                issue_input_commands::fetch_issue_details(&arguments.arguments)
            }
            IssueCommand::Info(arguments) => issue_commands::info(&arguments.arguments),
            IssueCommand::InsertSignalMarker(arguments) => {
                issue_wire_commands::insert_signal_marker_command(&arguments.arguments)
            }
            IssueCommand::TitleArchivalJq(arguments) => {
                issue_wire_commands::title_archival_jq(&arguments.arguments)
            }
            IssueCommand::TitleEligibility(arguments) => {
                issue_wire_commands::title_eligibility(&arguments.arguments)
            }
            IssueCommand::ListIssues(arguments) => {
                issue_input_commands::list_issues(&arguments.arguments)
            }
            IssueCommand::ParseInput(arguments) => {
                issue_input_commands::parse_input(&arguments.arguments)
            }
            IssueCommand::State(arguments) => issue_commands::state(&arguments.arguments),
            IssueCommand::WriteSentinel(arguments) => {
                issue_create_commands::write_sentinel(&arguments.arguments)
            }
        }),
        Domain::PlanBlock(command) => Ok(match command {
            PlanBlockCommand::Read(arguments) => {
                issue_wire_commands::plan_block_read(&arguments.arguments)
            }
            PlanBlockCommand::StripBody(arguments) => {
                issue_wire_commands::plan_block_strip_body(&arguments.arguments)
            }
            PlanBlockCommand::Write(arguments) => {
                issue_wire_commands::plan_block_write(&arguments.arguments)
            }
        }),
        Domain::NamedBlock(NamedBlockCommand::Write(arguments)) => {
            Ok(issue_wire_commands::named_block_write(&arguments.arguments))
        }
        Domain::Plan(PlanCommand::ScopePaths(arguments)) => {
            Ok(issue_wire_commands::scope_paths(&arguments.arguments))
        }
        Domain::TrackingIssue(command) => Ok(match command {
            TrackingIssueCommand::Read(arguments) => {
                tracking_issue_commands::read(&arguments.arguments)
            }
            TrackingIssueCommand::CreateIssue(arguments) => {
                tracking_issue_commands::create_issue(&arguments.arguments)
            }
            TrackingIssueCommand::AppendComment(arguments) => {
                tracking_issue_commands::append_comment(&arguments.arguments)
            }
            TrackingIssueCommand::Rename(arguments) => {
                tracking_issue_commands::rename(&arguments.arguments)
            }
            TrackingIssueCommand::MarkFalsePositive(arguments) => {
                tracking_issue_commands::mark_false_positive(&arguments.arguments)
            }
            TrackingIssueCommand::UpsertSummary(arguments) => {
                tracking_issue_commands::upsert_summary(&arguments.arguments)
            }
        }),
        Domain::Triage(command) => Ok(match command {
            TriageCommand::Inspect(arguments) => triage_commands::inspect(&arguments.arguments),
            TriageCommand::Probe(arguments) => triage_commands::probe(&arguments.arguments),
            TriageCommand::Apply(arguments) => triage_commands::apply(&arguments.arguments),
        }),
        Domain::Umbrella(command) => Ok(match command {
            UmbrellaCommand::Prepare(arguments) => umbrella_commands::prepare(&arguments.arguments),
            UmbrellaCommand::PersistProposal(arguments) => {
                umbrella_commands::persist_proposal(&arguments.arguments)
            }
            UmbrellaCommand::MarkInFlight(arguments) => {
                umbrella_commands::mark_in_flight(&arguments.arguments)
            }
            UmbrellaCommand::RecordResolved(arguments) => {
                umbrella_commands::record_resolved(&arguments.arguments)
            }
            UmbrellaCommand::ReconcileInFlight(arguments) => {
                umbrella_commands::reconcile_in_flight_command(&arguments.arguments)
            }
            UmbrellaCommand::Mutate(arguments) => umbrella_commands::mutate(&arguments.arguments),
            UmbrellaCommand::Verify(arguments) => umbrella_commands::verify(&arguments.arguments),
            UmbrellaCommand::VerifyCompletion(arguments) => {
                umbrella_commands::verify_completion(&arguments.arguments)
            }
        }),
        Domain::Untrusted(command) => Ok(match command {
            UntrustedCommand::ContentBlock(arguments) => {
                issue_wire_commands::untrusted_content_block(&arguments.arguments)
            }
            UntrustedCommand::FileBlock(arguments) => {
                issue_wire_commands::untrusted_file_block(&arguments.arguments)
            }
            UntrustedCommand::RedactStream(arguments) => {
                issue_wire_commands::untrusted_redact_stream(&arguments.arguments)
            }
            UntrustedCommand::XmlEscapeAttr(arguments) => {
                issue_wire_commands::untrusted_xml_escape_attr(&arguments.arguments)
            }
        }),
        Domain::Kv(KvCommand::Get(arguments)) => Ok(state_commands::kv_get(&arguments.arguments)),
        Domain::Lint(arguments) => match arguments.into_dispatch() {
            larch_lint::LintDispatch::Gitleaks(arguments) => Ok(gitleaks::run(&arguments)),
            larch_lint::LintDispatch::Native(arguments) => {
                Ok(ExitCode::from(larch_lint::run_cli(arguments).as_u8()))
            }
        },
        Domain::Plugin(PluginCommand::ReadVersion(arguments)) => {
            Ok(release_prepare::read_plugin_version(&arguments.args))
        }
        Domain::ObjectStore(ObjectStoreCommand::Gcs(arguments)) => {
            Ok(object_store_commands::run(&arguments))
        }
        Domain::Progress(command) => Ok(match command {
            ProgressCommand::Activate(arguments) => {
                progress_commands::activate(&arguments.arguments)
            }
            ProgressCommand::Deactivate(arguments) => {
                progress_commands::deactivate(&arguments.arguments)
            }
            ProgressCommand::Clear(arguments) => progress_commands::clear(&arguments.arguments),
            ProgressCommand::Note(arguments) => progress_commands::note(&arguments.arguments),
            ProgressCommand::Statusline(arguments) => {
                progress_commands::render_statusline(&arguments.arguments)
            }
            ProgressCommand::SessionReset(arguments) => {
                progress_commands::session_reset(&arguments.arguments)
            }
            ProgressCommand::InstallStatusline(arguments) => {
                progress_commands::install_statusline(&arguments.arguments)
            }
            ProgressCommand::RenderPhaseDetail(arguments) => {
                progress_commands::render_phase_detail(&arguments.arguments)
            }
            ProgressCommand::WriteDesignRoundMeta(arguments) => {
                progress_commands::write_design_round_meta(&arguments.arguments)
            }
            ProgressCommand::WriteImplementRoundMeta(arguments) => {
                progress_commands::write_implement_round_meta(&arguments.arguments)
            }
        }),
        Domain::Release(command) => run_release(command),
        Domain::ReportTokens(command) => Ok(match command {
            ReportTokensCommand::Analyze(arguments) => {
                report_tokens_commands::analyze(&arguments.arguments)
            }
        }),
        Domain::Session(command) => Ok(run_session(command)),
        Domain::Slack(command) => Ok(slack_commands::run(command)),
        Domain::StallRecovery(arguments) => Ok(stall_recovery_commands::run(&arguments.arguments)),
        Domain::TestShard(command) => Ok(test_shards::run(command)),
        Domain::Timing(command) => Ok(match command {
            TimingCommand::Mark(arguments) => timing_commands::mark(&arguments.arguments),
            TimingCommand::RecordVendorTask(arguments) => {
                timing_commands::record_vendor_task(&arguments.arguments)
            }
            TimingCommand::RecordRound(arguments) => {
                timing_commands::record_round(&arguments.arguments)
            }
            TimingCommand::Dump(arguments) => timing_commands::dump(&arguments.arguments),
            TimingCommand::Report(arguments) => timing_commands::report(&arguments.arguments),
            TimingCommand::HarnessMark(arguments) => {
                timing_commands::harness_mark(&arguments.arguments)
            }
            TimingCommand::TelemetryMark(arguments) => {
                timing_commands::telemetry_mark(&arguments.arguments)
            }
            TimingCommand::TaskKinds(arguments) => {
                timing_commands::task_kinds(&arguments.arguments)
            }
        }),
        Domain::Gh(GhCommand::WorkflowPath) => {
            print!("{}", larch_core::workflow_path());
            Ok(ExitCode::SUCCESS)
        }
        Domain::Gh(GhCommand::RemoteRepo(arguments)) => Ok(run_remote_repo(&arguments)),
        Domain::Gh(GhCommand::ResolveRepo(arguments)) => Ok(run_resolve_repo(&arguments)),
        Domain::Gh(GhCommand::RunLogs(arguments)) => Ok(run_logs(&arguments)),
        Domain::Push(PushSubcommand::Branch(arguments)) => {
            Ok(push_network::branch(&arguments.args))
        }
        Domain::Push(PushSubcommand::Force(arguments)) => Ok(push_network::force(
            arguments.expected_remote_oid.as_deref(),
        )),
        Domain::Push(PushSubcommand::Rebase(arguments)) => Ok(push_rebase::rebase(&arguments.args)),
        Domain::Push(PushSubcommand::CheckpointProbe(arguments)) => {
            Ok(push_rebase::checkpoint_probe(&arguments.args))
        }
        Domain::RunLog(RunLogCommand::StoragePreflight(arguments)) => {
            Ok(run_log_commands::storage_preflight(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Archive(arguments)) => {
            Ok(run_log_commands::archive(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Manifest(arguments)) => {
            Ok(run_log_commands::manifest(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Materialize(arguments)) => {
            Ok(run_log_commands::materialize(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::MigrateLayout(arguments)) => Ok(
            run_log_migration_commands::migrate_layout(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::CleanupImplementLogs(arguments)) => Ok(
            run_log_cleanup_commands::cleanup_implement_logs(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::Publish(arguments)) => {
            Ok(run_log_publication_commands::publish(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::LifecycleStart(arguments)) => {
            Ok(run_lifecycle_commands::start(&arguments))
        }
        Domain::RunLog(RunLogCommand::LifecycleFinalize(arguments)) => {
            Ok(run_lifecycle_commands::terminal(
                &arguments,
                "finalize",
                larch_core::LifecycleOutcome::Success,
            ))
        }
        Domain::RunLog(RunLogCommand::LifecycleFailure(arguments)) => {
            Ok(run_lifecycle_commands::terminal(
                &arguments,
                "failure",
                larch_core::LifecycleOutcome::Failure,
            ))
        }
        Domain::RunLog(RunLogCommand::LifecycleCancel(arguments)) => {
            Ok(run_lifecycle_commands::terminal(
                &arguments,
                "cancel",
                larch_core::LifecycleOutcome::Cancelled,
            ))
        }
        Domain::RunLog(RunLogCommand::LifecycleEarlyReturn(arguments)) => {
            Ok(run_lifecycle_commands::terminal(
                &arguments,
                "early-return",
                larch_core::LifecycleOutcome::EarlyReturn,
            ))
        }
        Domain::RunLog(RunLogCommand::Init(arguments)) => {
            Ok(run_log_entry_commands::init(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Write(arguments)) => {
            Ok(run_log_entry_commands::write(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::WriteRound(arguments)) => {
            Ok(run_log_entry_commands::write_round(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Append(arguments)) => {
            Ok(run_log_entry_commands::append(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::AppendEntry(arguments)) => {
            Ok(run_log_entry_commands::append_entry(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::AppendFailure(arguments)) => {
            Ok(run_log_entry_commands::append_failure(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Exists(arguments)) => {
            Ok(run_log_entry_commands::exists(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::VerifyCompleteness(arguments)) => Ok(
            run_log_entry_commands::verify_completeness(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::ValidateRunId(arguments)) => {
            Ok(run_log_commands::validate_run_id(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::PublishBreadcrumbs(arguments)) => {
            Ok(run_log_commands::publish_breadcrumbs(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::Sync(arguments)) => {
            Ok(run_log_publication_commands::sync(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::RetroFixCursor(arguments)) => Ok(
            run_log_migration_commands::retro_fix_cursor(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::RetroV3Sweep(arguments)) => Ok(
            run_log_migration_commands::retro_v3_sweep(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::Checkpoint(arguments)) => {
            Ok(run_log_flush_commands::checkpoint(&arguments.arguments))
        }
        Domain::RunLog(RunLogCommand::CaptureTranscript(arguments)) => Ok(
            run_log_flush_commands::capture_transcript(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::PrepareTerminalSnapshot(arguments)) => Ok(
            run_log_flush_commands::prepare_terminal_snapshot(&arguments.arguments),
        ),
        Domain::RunLog(RunLogCommand::Refresh(arguments)) => {
            Ok(run_log_flush_commands::refresh(&arguments.arguments))
        }
        Domain::UpgradeLarch(command) => match command {
            UpgradeLarchCommand::ReleaseStep7Root(arguments) => {
                let version = arguments
                    .current_version
                    .as_deref()
                    .or(arguments.positional_current_version.as_deref());
                larch_adapters::upgrade_larch::release_step7_root(version)
                    .map(|()| ExitCode::SUCCESS)
            }
            UpgradeLarchCommand::Run(arguments) => {
                larch_adapters::upgrade_larch::run(arguments.plugin_root.as_deref())
                    .map(|()| ExitCode::SUCCESS)
            }
            UpgradeLarchCommand::SparseDirs => {
                larch_adapters::upgrade_larch::sparse_dirs();
                Ok(ExitCode::SUCCESS)
            }
        },
    }
}

fn dirty_tree_raw_arguments(command: &str) -> Option<Vec<OsString>> {
    let mut values = env::args_os().skip(1);
    (values.next()?.as_os_str() == OsStr::new("dirty-tree")).then_some(())?;
    (values.next()?.as_os_str() == OsStr::new(command)).then_some(())?;
    Some(values.collect())
}

fn run_release(
    command: ReleaseCommand,
) -> Result<ExitCode, larch_adapters::upgrade_larch::Failure> {
    match command {
        ReleaseCommand::AssetCandidate(arguments) => Ok(release_assets::asset_candidate(
            &release_assets::CandidateArguments {
                repo_root: arguments.repo_root,
                tag: arguments.tag,
                source_commit: arguments.source_commit,
            },
        )),
        ReleaseCommand::AssetRun(arguments) => Ok(release_stage::asset_run(
            &arguments.repository,
            &arguments.tag,
            &arguments.source_commit,
        )),
        ReleaseCommand::ClassifyBump(arguments) => Ok(release_prepare::classify_bump(
            &release_prepare::ClassifyArguments {
                base: arguments.base,
                head: arguments.head,
            },
        )),
        ReleaseCommand::CollectAssets(arguments) => Ok(release_assets::collect_assets(
            &release_assets::CollectArguments {
                version: arguments.version,
                tag: arguments.tag,
                source_commit: arguments.source_commit,
                input_dir: arguments.input_dir,
                output_dir: arguments.output_dir,
                license: arguments.license,
            },
        )),
        ReleaseCommand::EnsurePolicy(arguments) => {
            Ok(release_stage::ensure_policy(&arguments.repository))
        }
        ReleaseCommand::Finish(arguments) => Ok(release_publish::finish(
            &arguments.version,
            &arguments.repository,
            &arguments.pr,
            &arguments.source_commit,
        )),
        ReleaseCommand::PackageAsset(arguments) => Ok(release_assets::package_asset(
            &release_assets::PackageArguments {
                version: arguments.version,
                tag: arguments.tag,
                source_commit: arguments.source_commit,
                target: arguments.target,
                binary: arguments.binary,
                license: arguments.license,
                output_dir: arguments.output_dir,
            },
        )),
        ReleaseCommand::Prepare(arguments) => {
            let bump = arguments.bump.as_deref().map(|value| match value {
                "major" => release_prepare::BumpType::Major,
                "minor" => release_prepare::BumpType::Minor,
                _ => release_prepare::BumpType::Patch,
            });
            Ok(release_prepare::prepare(
                &release_prepare::PrepareArguments {
                    repository: arguments.repository,
                    bump,
                    out_dir: arguments.out_dir,
                },
            ))
        }
        ReleaseCommand::Promote(arguments) => Ok(release_publish::promote(
            &arguments.version,
            arguments.repository.as_deref(),
        )),
        ReleaseCommand::PromoteLatest(arguments) => Ok(release_publish::promote_latest(
            &arguments.repository,
            arguments.dry_run,
        )),
        ReleaseCommand::PluginRuntime(arguments) => release_plugin_runtime::run(arguments.check)
            .map(|()| ExitCode::SUCCESS)
            .map_err(command_failure),
        ReleaseCommand::SetVersion(arguments) => Ok(release_version::run(&arguments.version)),
        ReleaseCommand::Stage(arguments) => Ok(release_stage::stage(
            &arguments.version,
            &arguments.notes_file,
            &arguments.repository,
            &arguments.pr,
        )),
        ReleaseCommand::ValidateAssets(arguments) => Ok(release_assets::validate_assets(
            &release_assets::ValidateArguments {
                version: arguments.version,
                tag: arguments.tag,
                source_commit: arguments.source_commit,
                asset_dir: arguments.asset_dir,
                license: arguments.license,
                verify_attestations: arguments.verify_attestations,
            },
        )),
        ReleaseCommand::ValidateDraft(arguments) => Ok(release_stage::validate_draft(
            &arguments.version,
            &arguments.repository,
            &arguments.pr,
            &arguments.source_commit,
        )),
    }
}

const fn command_failure(message: String) -> larch_adapters::upgrade_larch::Failure {
    larch_adapters::upgrade_larch::Failure { code: 1, message }
}

fn run_remote_repo(arguments: &TrailingArguments) -> ExitCode {
    github_repository_resolution::run_remote_repo(&arguments.args)
}

fn run_resolve_repo(arguments: &TrailingArguments) -> ExitCode {
    github_repository_resolution::run_resolve_repo(&arguments.args)
}

fn run_logs(arguments: &RunLogsArguments) -> ExitCode {
    let output = match larch_adapters::runtime::LarchRuntime::new() {
        Ok(runtime) => runtime.block_on(async {
            let cancellation = larch_adapters::runtime::Cancellation::new();
            let runner = larch_adapters::TokioProcessRunner::default();
            let working_directory = match std::env::current_dir() {
                Ok(path) => path,
                Err(error) => {
                    return larch_core::run_logs_setup_failure(
                        &arguments.repository,
                        arguments.run_id,
                        format!("cannot resolve current directory: {error}"),
                    );
                }
            };
            let service = match larch_adapters::github::OctocrabGitHubService::from_gh(
                &runner,
                &working_directory,
                &cancellation,
            )
            .await
            {
                Ok(service) => service,
                Err(error) => {
                    return larch_core::run_logs_setup_failure(
                        &arguments.repository,
                        arguments.run_id,
                        &error,
                    );
                }
            };
            larch_core::run_logs(
                &service,
                &arguments.repository,
                arguments.run_id,
                &cancellation,
            )
            .await
        }),
        Err(error) => larch_core::run_logs_setup_failure(
            &arguments.repository,
            arguments.run_id,
            format!("cannot initialize larch runtime: {error}"),
        ),
    };
    std::io::stdout()
        .write_all(output.stdout())
        .expect("write command output");
    ExitCode::from(output.exit_code())
}

pub(crate) fn parse_repository(value: &str) -> Result<larch_core::GitHubRepositoryRef, String> {
    let Some((owner, name)) = value.split_once('/') else {
        return Err(String::from("repository must use OWNER/REPO form"));
    };
    if name.contains('/') {
        return Err(String::from("repository must use OWNER/REPO form"));
    }
    larch_core::GitHubRepositoryRef::new(owner, name).map_err(|error| error.to_string())
}

fn run_git(command: GitSubcommand) -> Result<ExitCode, String> {
    match command {
        GitSubcommand::AmendAdd(arguments) => Ok(git_commands::run(GitCommand::AmendAdd {
            paths: arguments.paths,
        })),
        GitSubcommand::CheckPhantomDirty(arguments) => {
            check_phantom_dirty_command(&arguments);
            Ok(ExitCode::SUCCESS)
        }
        GitSubcommand::CheckoutOurs(arguments) => checkout_ours(arguments),
        GitSubcommand::ConflictFiles => {
            conflict_files()?;
            Ok(ExitCode::SUCCESS)
        }
        GitSubcommand::CleanTree(arguments) => clean_tree(arguments),
        GitSubcommand::Commit(arguments) => Ok(git_commands::run(GitCommand::Commit {
            message: arguments.message,
            no_trailer: arguments.no_trailer,
            only: arguments.only,
            pathspec_from_file: arguments.pathspec_from_file,
            pathspec_file_nul: arguments.pathspec_file_nul,
            paths: arguments.files,
        })),
        GitSubcommand::SnapshotUntracked(arguments) => {
            snapshot_untracked(arguments);
            Ok(ExitCode::SUCCESS)
        }
        GitSubcommand::PhantomProbe(arguments) => {
            phantom_probe(&arguments);
            Ok(ExitCode::SUCCESS)
        }
        GitSubcommand::RebaseAbort(arguments) => Ok(rebase_abort(&arguments)),
        GitSubcommand::RebaseSkip(arguments) => rebase_skip(&arguments),
        GitSubcommand::BranchInfo(arguments) => Ok(git_commands::run(GitCommand::BranchInfo {
            args: arguments.args,
        })),
        GitSubcommand::CheckMainSync(arguments) => {
            Ok(git_commands::run(GitCommand::CheckMainSync {
                args: arguments.args,
            }))
        }
        GitSubcommand::CheckRemoteBranch(arguments) => {
            Ok(git_commands::run(GitCommand::CheckRemoteBranch {
                args: arguments.args,
            }))
        }
        GitSubcommand::CountCommits(arguments) => Ok(git_commands::run(GitCommand::CountCommits {
            args: arguments.args,
        })),
        GitSubcommand::CurrentBranch(arguments) => {
            Ok(git_commands::run(GitCommand::CurrentBranch {
                args: arguments.args,
            }))
        }
        GitSubcommand::ShowStage(arguments) => Ok(git_commands::run(GitCommand::ShowStage {
            args: arguments.args,
        })),
        GitSubcommand::SyncLocalMain(arguments) => {
            Ok(git_commands::run(GitCommand::SyncLocalMain {
                args: arguments.args,
            }))
        }
        GitSubcommand::Stage(arguments) => Ok(git_commands::run(GitCommand::Stage {
            paths: arguments.paths,
        })),
    }
}

#[derive(Debug, Eq, PartialEq)]
struct PhantomDirtyResult {
    status: &'static str,
    reason: Option<&'static str>,
    count: usize,
    paths_file: Option<PathBuf>,
}

impl PhantomDirtyResult {
    const fn status(status: &'static str) -> Self {
        Self {
            status,
            reason: None,
            count: 0,
            paths_file: None,
        }
    }

    const fn unknown(reason: &'static str) -> Self {
        Self {
            status: "unknown",
            reason: Some(reason),
            count: 0,
            paths_file: None,
        }
    }
}

fn check_phantom_dirty_command(arguments: &CheckPhantomDirtyArguments) {
    let parsed = parse_check_phantom_arguments(&arguments.arguments);
    let result = match parsed {
        Ok((baseline, step, paths_dir)) => check_phantom_dirty(&baseline, &step, &paths_dir),
        Err(reason) => PhantomDirtyResult::unknown(reason),
    };
    emit_phantom_dirty(&result, "");
}

fn parse_check_phantom_arguments(
    arguments: &[OsString],
) -> Result<(PathBuf, String, PathBuf), &'static str> {
    let mut baseline = None;
    let mut step = None;
    let mut paths_dir = None;
    let mut index = 0;
    while index < arguments.len() {
        let argument = arguments[index].as_os_str();
        let (target, missing_reason) = if argument == "--baseline" {
            (&mut baseline, "baseline-missing-value")
        } else if argument == "--step" {
            if index + 1 >= arguments.len() {
                return Err("step-missing-value");
            }
            step = arguments[index + 1].to_str().map(str::to_owned);
            if step.is_none() {
                return Err("bad-step");
            }
            index += 2;
            continue;
        } else if argument == "--phantom-paths-dir" {
            (&mut paths_dir, "phantom-paths-dir-missing-value")
        } else {
            return Err("unknown-flag");
        };
        if index + 1 >= arguments.len() {
            return Err(missing_reason);
        }
        *target = Some(PathBuf::from(&arguments[index + 1]));
        index += 2;
    }
    let baseline = baseline
        .filter(|value| !value.as_os_str().is_empty())
        .ok_or("baseline-required")?;
    let step = step
        .filter(|value| !value.is_empty())
        .ok_or("step-required")?;
    let paths_dir = paths_dir
        .filter(|value| !value.as_os_str().is_empty())
        .ok_or("phantom-paths-dir-required")?;
    Ok((baseline, step, paths_dir))
}

fn check_phantom_dirty(baseline: &Path, step: &str, paths_dir: &Path) -> PhantomDirtyResult {
    if !valid_step(step) {
        return PhantomDirtyResult::unknown("bad-step");
    }
    if !valid_meta_path(baseline.as_os_str()) {
        return PhantomDirtyResult::unknown("bad-baseline-path");
    }
    let Ok(status) = repository_status() else {
        return PhantomDirtyResult::unknown("git-status-failed");
    };
    let current_untracked = untracked_paths(&status);
    let baseline_paths = if baseline.is_file() {
        match fs::read(baseline) {
            Ok(data) => split_nul(&data),
            Err(_) => return PhantomDirtyResult::unknown("baseline-sort-failed"),
        }
    } else if current_untracked.is_empty() {
        BTreeSet::new()
    } else {
        return PhantomDirtyResult::unknown("baseline-missing-untracked-ambiguous");
    };
    let new_untracked = current_untracked
        .difference(&baseline_paths)
        .cloned()
        .collect::<Vec<_>>();
    if new_untracked.is_empty() {
        return if status.tree_to_index.entries().is_empty()
            && status.index_to_worktree.entries().is_empty()
            && status.unmerged.is_empty()
        {
            PhantomDirtyResult::status("clean")
        } else {
            PhantomDirtyResult::status("tracked-only")
        };
    }
    if fs::create_dir_all(paths_dir).is_err() {
        return PhantomDirtyResult::unknown("phantom-paths-dir-create-failed");
    }
    let paths_file = paths_dir.join(format!("phantom-paths-{step}.z"));
    let mut data = Vec::new();
    for path in &new_untracked {
        data.extend(path);
        data.push(0);
    }
    if fs::write(&paths_file, data).is_err() {
        return PhantomDirtyResult::unknown("phantom-paths-write-failed");
    }
    let count = match fs::read(&paths_file) {
        Ok(data) => data
            .iter()
            .fold(0, |count, byte| count + usize::from(*byte == 0)),
        Err(_) => return PhantomDirtyResult::unknown("phantom-count-failed"),
    };
    PhantomDirtyResult {
        status: "phantom",
        reason: None,
        count,
        paths_file: Some(paths_file),
    }
}

fn phantom_probe(arguments: &PhantomProbeArguments) {
    for line in phantom_probe_lines(&arguments.step, arguments.baseline_file.as_deref(), true) {
        println!("{line}");
    }
}

/// Produce the `PHANTOM_*` advisory rows for a checkpoint step. Shared by the
/// `git phantom-probe` command and the `push checkpoint-probe` success tail so
/// both compose the #7757 phantom inspection through one owner. `announce`
/// mirrors the command's stderr banner; the checkpoint tail suppresses it
/// because Python swallowed the probe subprocess's stderr.
pub(crate) fn phantom_probe_lines(
    step: &str,
    baseline_override: Option<&Path>,
    announce: bool,
) -> Vec<String> {
    if announce {
        eprintln!("→ phantom-probe: {step}");
    }
    let Some(implement_tmpdir) = env::var_os("IMPLEMENT_TMPDIR").filter(|value| !value.is_empty())
    else {
        return phantom_dirty_lines(
            &PhantomDirtyResult::unknown("IMPLEMENT_TMPDIR-unset"),
            "PHANTOM_",
        );
    };
    let implement_tmpdir = PathBuf::from(implement_tmpdir);
    let baseline = baseline_override.map_or_else(
        || implement_tmpdir.join("untracked-baseline.z"),
        Path::to_path_buf,
    );
    let result = check_phantom_dirty(&baseline, step, &implement_tmpdir);
    let append_error = append_phantom_warning(&implement_tmpdir, step, &result);
    let mut lines = phantom_dirty_lines(&result, "PHANTOM_");
    if let Some(error) = append_error {
        lines.push(format!(
            "PHANTOM_APPEND_WARN_ERROR={}",
            fold_whitespace(&error)
        ));
    }
    lines
}

fn append_phantom_warning(
    implement_tmpdir: &Path,
    step: &str,
    result: &PhantomDirtyResult,
) -> Option<String> {
    let entry = match result.status {
        "phantom" => format!(
            "- **Step {step} — phantom untracked files:** {} file(s) appeared since session baseline (inspect {}/phantom-paths-{step}.z locally)",
            result.count,
            implement_tmpdir.display()
        ),
        "unknown" => format!(
            "- **Step {step} — phantom detection inconclusive:** STATUS=unknown REASON={}",
            result.reason.unwrap_or("unknown")
        ),
        _ => return None,
    };
    let log = implement_tmpdir.join("execution-issues.md");
    match write_execution_warning(&log, &entry) {
        Ok(()) => None,
        Err(error) => {
            let folded = fold_whitespace(&error);
            let fallback = format!("- **Step {step} — phantom warning append failed: {folded}**");
            let _ = write_execution_warning(&log, &fallback);
            Some(folded)
        }
    }
}

fn write_execution_warning(log: &Path, entry: &str) -> Result<(), String> {
    reject_symlink_path_or_ancestors(log)?;
    let parent = log
        .parent()
        .ok_or_else(|| String::from("log path has no parent"))?;
    fs::create_dir_all(parent).map_err(|error| python_io_error(&error, parent))?;
    reject_symlink_path_or_ancestors(log)?;
    let lock = log.with_file_name(format!(
        "{}.lock.d",
        log.file_name().unwrap_or_default().to_string_lossy()
    ));
    let mut acquired = false;
    for attempt in 0..100 {
        match fs::create_dir(&lock) {
            Ok(()) => {
                acquired = true;
                break;
            }
            Err(error) if error.kind() == ErrorKind::AlreadyExists && attempt < 99 => {
                thread::sleep(Duration::from_millis(50));
            }
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                return Err(format!("could not acquire lock: {}", lock.display()));
            }
            Err(error) => return Err(python_io_error(&error, &lock)),
        }
    }
    if !acquired {
        return Err(format!("could not acquire lock: {}", lock.display()));
    }
    let result = (|| {
        let bytes = match fs::read(log) {
            Ok(bytes) => bytes,
            Err(error) if error.kind() == ErrorKind::NotFound => Vec::new(),
            Err(error) => return Err(python_io_error(&error, log)),
        };
        let text = String::from_utf8_lossy(&bytes).into_owned();
        let new_text = insert_warning_entry(&text, entry);
        reject_symlink_path_or_ancestors(log)?;
        private_atomic_write(log, &new_text, parent).map_err(|error| error.to_string())
    })();
    let _ = fs::remove_dir(&lock);
    result
}

fn insert_warning_entry(text: &str, entry: &str) -> String {
    const HEADER: &str = "### Warnings";
    if !text.lines().any(|line| line == HEADER) {
        let prefix = if text.is_empty() { "" } else { "\n" };
        return format!(
            "{}{prefix}{HEADER}\n\n{}\n",
            text.trim_end_matches('\n'),
            entry.trim_end_matches('\n')
        );
    }
    let lines = text.lines().collect::<Vec<_>>();
    let mut output = Vec::new();
    let mut inserted = false;
    let mut in_target = false;
    for line in lines {
        if line == HEADER {
            in_target = true;
            output.push(line);
            continue;
        }
        if in_target && line.starts_with("### ") {
            if !inserted {
                output.extend(["", entry.trim_end_matches('\n')]);
                inserted = true;
            }
            in_target = false;
        }
        output.push(line);
    }
    if in_target && !inserted {
        output.extend(["", entry.trim_end_matches('\n')]);
    }
    output.join("\n") + "\n"
}

fn phantom_dirty_lines(result: &PhantomDirtyResult, prefix: &str) -> Vec<String> {
    let mut lines = vec![format!("{prefix}STATUS={}", result.status)];
    if let Some(reason) = result.reason {
        lines.push(format!("{prefix}REASON={reason}"));
    }
    if result.status == "phantom" {
        lines.push(format!("PHANTOM_COUNT={}", result.count));
        if let Some(paths_file) = &result.paths_file {
            lines.push(format!("PHANTOM_PATHS_FILE={}", paths_file.display()));
        }
    }
    lines
}

fn emit_phantom_dirty(result: &PhantomDirtyResult, prefix: &str) {
    for line in phantom_dirty_lines(result, prefix) {
        println!("{line}");
    }
}

fn split_nul(data: &[u8]) -> BTreeSet<Vec<u8>> {
    data.split(|byte| *byte == 0)
        .filter(|path| !path.is_empty())
        .map(<[u8]>::to_vec)
        .collect()
}

fn untracked_paths(status: &RepositoryStatus) -> BTreeSet<Vec<u8>> {
    status
        .untracked
        .iter()
        .map(|path| path.as_bytes().to_vec())
        .collect()
}

fn fold_whitespace(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn python_io_error(error: &std::io::Error, path: &Path) -> String {
    let Some(code) = error.raw_os_error() else {
        return error.to_string();
    };
    let rendered = error.to_string();
    let detail = rendered.split(" (os error ").next().unwrap_or("I/O error");
    format!("[Errno {code}] {detail}: '{}'", path.display())
}

/// Refuse a phantom-warning log path whose leaf or any ancestor is a symlink.
///
/// The log lives under `$IMPLEMENT_TMPDIR`, which the `/tmp` session fallback can
/// place beneath a root-owned platform alias, so the same exemption as
/// [`larch_adapters::assert_no_symlink_path_or_ancestors`] applies.
fn reject_symlink_path_or_ancestors(path: &Path) -> Result<(), String> {
    use larch_adapters::refuses_symlink;
    use std::os::unix::fs::MetadataExt as _;

    let mut current = Some(path);
    while let Some(candidate) = current {
        match fs::symlink_metadata(candidate) {
            Ok(metadata) if refuses_symlink(metadata.file_type().is_symlink(), metadata.uid()) => {
                return Err(format!(
                    "refusing symlinked path or ancestor: {}",
                    candidate.display()
                ));
            }
            Ok(_) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => return Err(python_io_error(&error, candidate)),
        }
        current = candidate.parent();
    }
    Ok(())
}

fn valid_step(step: &str) -> bool {
    !step.is_empty()
        && step
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-'))
}

pub(crate) fn valid_meta_path(path: &OsStr) -> bool {
    let bytes = path.as_encoded_bytes();
    !bytes.is_empty()
        && bytes
            .iter()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'/' | b'_' | b'-'))
}

enum GitControl {
    CheckoutOurs(Vec<larch_adapters::git::GitPath>),
    RebaseAbort,
    RebaseSkip,
}

fn checkout_ours(arguments: CheckoutOursArguments) -> Result<ExitCode, String> {
    if arguments.paths.is_empty() {
        eprintln!("git-checkout-ours.sh: at least one file argument is required");
        eprintln!("usage: git-checkout-ours.sh <file> [<file> ...]");
        return Ok(ExitCode::from(1));
    }
    let paths = arguments
        .paths
        .into_iter()
        .map(|path| larch_adapters::git::GitPath::new(path.into_os_string()))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;
    run_git_control(GitControl::CheckoutOurs(paths))
}

fn rebase_abort(arguments: &RebaseControlArguments) -> ExitCode {
    if let Some(argument) = arguments.extra.first() {
        eprintln!(
            "git-rebase-abort.sh: unknown argument: {}",
            argument.to_string_lossy()
        );
        return ExitCode::SUCCESS;
    }
    let _ = run_git_control(GitControl::RebaseAbort);
    ExitCode::SUCCESS
}

fn rebase_skip(arguments: &RebaseControlArguments) -> Result<ExitCode, String> {
    if let Some(argument) = arguments.extra.first() {
        eprintln!(
            "git-rebase-skip.sh: unknown argument: {}",
            argument.to_string_lossy()
        );
        return Ok(ExitCode::from(1));
    }
    run_git_control(GitControl::RebaseSkip)
}

fn run_git_control(control: GitControl) -> Result<ExitCode, String> {
    use larch_adapters::git::{CheckoutRequest, GitCli, GitCliError, GitCliPolicy, RebaseRequest};

    let idempotent_abort = matches!(control, GitControl::RebaseAbort);
    let working_directory = std::env::current_dir()
        .map_err(|error| format!("cannot resolve Git working directory: {error}"))?;
    let policy = GitCliPolicy::new(working_directory).map_err(|error| error.to_string())?;
    let runner = larch_adapters::TokioProcessRunner::default();
    let runtime = larch_adapters::runtime::LarchRuntime::new()
        .map_err(|error| format!("cannot initialize larch runtime: {error}"))?;
    let cancellation = larch_adapters::runtime::Cancellation::new();
    let git = GitCli::new(&runner, policy);
    let result = runtime.block_on(async {
        match control {
            GitControl::CheckoutOurs(paths) => {
                git.checkout(
                    CheckoutRequest::Paths {
                        ours: true,
                        theirs: false,
                        paths,
                    },
                    &cancellation,
                )
                .await
            }
            GitControl::RebaseAbort => git.rebase(RebaseRequest::Abort, &cancellation).await,
            GitControl::RebaseSkip => git.rebase(RebaseRequest::Skip, &cancellation).await,
        }
    });
    if idempotent_abort {
        return Ok(ExitCode::SUCCESS);
    }
    match result {
        Ok(result) | Err(GitCliError::Failed(result)) => emit_git_result(result.output()),
        Err(GitCliError::Process(error)) => {
            if let Some(output) = error.output() {
                let _ = emit_git_result(output)?;
            }
            Err(error.to_string())
        }
        Err(error) => Err(error.to_string()),
    }
}

fn emit_git_result(output: &larch_core::ProcessOutput) -> Result<ExitCode, String> {
    std::io::stdout()
        .write_all(output.stdout())
        .map_err(|error| format!("cannot write Git stdout: {error}"))?;
    std::io::stderr()
        .write_all(output.stderr())
        .map_err(|error| format!("cannot write Git stderr: {error}"))?;
    let code = output
        .status()
        .code()
        .and_then(|code| u8::try_from(code).ok())
        .unwrap_or(1);
    Ok(ExitCode::from(code))
}

fn repository_status() -> Result<RepositoryStatus, larch_core::RepositoryError> {
    larch_adapters::git::GixRepository::discover(".")?.local_status(&StatusOptions::default())
}

fn conflict_files() -> Result<(), String> {
    let status = repository_status().map_err(|error| error.to_string())?;
    for entry in status.unmerged {
        println!("FILE={}", display_path(entry.path.as_bytes()));
        for stage in 1..=3 {
            println!(
                "STAGE_{stage}={}",
                entry.stages.iter().any(|item| item.stage == stage)
            );
        }
        println!();
    }
    Ok(())
}

fn clean_tree(arguments: CleanTreeArguments) -> Result<ExitCode, String> {
    match repository_status() {
        Ok(status) => {
            if status.is_dirty() {
                println!("CLEAN=false");
                println!("DIRTY_OUT={}", one_line(&porcelain(&status)));
            } else {
                println!("CLEAN=true");
            }
            Ok(ExitCode::SUCCESS)
        }
        Err(_error) if !arguments.fail_closed => {
            println!("CLEAN=true");
            Ok(ExitCode::SUCCESS)
        }
        Err(error) => {
            println!("CLEAN=unknown");
            println!(
                "PROBE_ERROR=git exited 1 ({})",
                one_line(&error.to_string())
            );
            Err(String::new())
        }
    }
}

fn snapshot_untracked(arguments: SnapshotUntrackedArguments) {
    let Some(output) = arguments.output else {
        eprintln!("snapshot-untracked.sh: --output is required");
        return;
    };
    let mut temporary_name = output
        .file_name()
        .map_or_else(OsString::new, OsString::from);
    temporary_name.push(".tmp");
    let temporary = output.with_file_name(temporary_name);
    let result = repository_status();
    let cleanup = || {
        remove_if_present(&output);
        remove_if_present(&temporary);
    };
    let Ok(status) = result else {
        cleanup();
        return;
    };
    let paths = untracked_paths(&status);
    let separator = if arguments.nul { 0 } else { b'\n' };
    let mut data = Vec::new();
    for path in paths {
        data.extend(path);
        data.push(separator);
    }
    if fs::write(&temporary, data).is_err() || fs::rename(&temporary, &output).is_err() {
        cleanup();
    }
}

fn remove_if_present(path: &Path) {
    let _ = fs::remove_file(path).or_else(|error| {
        if error.kind() == ErrorKind::NotFound {
            Ok(())
        } else {
            Err(error)
        }
    });
}

fn display_path(path: &[u8]) -> String {
    String::from_utf8_lossy(path).into_owned()
}

fn one_line(value: &str) -> String {
    value
        .replace(['\n', '\r', '\t'], " ")
        .chars()
        .take(256)
        .collect()
}

/// Render `git status --porcelain` text for one repository work tree.
pub(crate) fn repository_porcelain(repo: &Path) -> Option<String> {
    let status = larch_adapters::git::GixRepository::discover(repo)
        .ok()?
        .local_status(&StatusOptions::default())
        .ok()?;
    Some(porcelain(&status))
}

fn porcelain(status: &RepositoryStatus) -> String {
    let mut rows = BTreeMap::<Vec<u8>, [char; 2]>::new();
    for change in status.tree_to_index.entries() {
        rows.entry(change.path.as_bytes().to_vec())
            .or_insert([' ', ' '])[0] = status_code(change.kind);
    }
    for change in status.index_to_worktree.entries() {
        rows.entry(change.path.as_bytes().to_vec())
            .or_insert([' ', ' '])[1] = status_code(change.kind);
    }
    for entry in &status.unmerged {
        rows.insert(
            entry.path.as_bytes().to_vec(),
            conflict_code(entry.kind)
                .chars()
                .collect::<Vec<_>>()
                .try_into()
                .expect("two-byte conflict code"),
        );
    }
    for path in &status.untracked {
        rows.insert(path.as_bytes().to_vec(), ['?', '?']);
    }
    let mut output = String::new();
    for (path, code) in rows {
        let _ = writeln!(output, "{}{} {}", code[0], code[1], display_path(&path));
    }
    output
}

const fn status_code(kind: ChangeKind) -> char {
    match kind {
        ChangeKind::Added => 'A',
        ChangeKind::Deleted => 'D',
        ChangeKind::Modified | ChangeKind::SubmoduleModified => 'M',
        ChangeKind::TypeChanged => 'T',
        ChangeKind::Renamed => 'R',
        ChangeKind::Copied => 'C',
    }
}

const fn conflict_code(kind: larch_core::ConflictKind) -> &'static str {
    match kind {
        larch_core::ConflictKind::BothDeleted => "DD",
        larch_core::ConflictKind::AddedByUs => "AU",
        larch_core::ConflictKind::DeletedByThem => "UD",
        larch_core::ConflictKind::AddedByThem => "UA",
        larch_core::ConflictKind::DeletedByUs => "DU",
        larch_core::ConflictKind::BothAdded => "AA",
        larch_core::ConflictKind::BothModified => "UU",
    }
}

fn main() -> ExitCode {
    let metadata = larch_adapters::build_metadata();
    let matches = Cli::command().version(metadata.version()).get_matches();
    let cli = Cli::from_arg_matches(&matches)
        .expect("arguments already validated by the generated Clap command");
    match run(cli, metadata) {
        Ok(exit_code) => exit_code,
        Err(error) => {
            if !error.message.is_empty() {
                eprintln!("{}", error.message);
            }
            ExitCode::from(error.code)
        }
    }
}
