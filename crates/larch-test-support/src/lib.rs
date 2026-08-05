//! Shared, deterministic fixtures for Rust tests in the larch workspace.

mod clock;
mod environment;
mod filesystem;
mod git;
mod http;
mod process;
mod run_log;

pub use clock::TestClock;
pub use environment::TestEnvironment;
pub use filesystem::TestWorkspace;
pub use git::{
    BoundedBytes, ExecutionSnapshot, ExitClass, FixtureCapability, FixtureSkip, GitCommandOutput,
    GitFixture, GitFixtureError, GitObjectFormat, GitRepository, GitRepositoryBuilder,
    ProbeSnapshot, SemanticSnapshot, SnapshotEntry, SnapshotEntryKind,
};
pub use http::{HttpResponse, HttpResponseBuilder, HttpResponseError};
pub use process::{FakeProcessRunner, NeverCancelled, ProcessOutputBuilder};
pub use run_log::{
    DurabilityState, LocalObjectStore, ObjectMetadata, ObjectStoreError, ObjectStoreErrorKind,
    ParityDifference, ReportSnapshot, ReportingParityOracle, RunLogFixture, RunLogSnapshot,
    RunLogTree, RunLogTreeBuilder,
};
