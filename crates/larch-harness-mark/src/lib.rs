//! Dependency-free inherited-stdio timing wrapper for developer and CI harnesses.
//!
//! This is deliberately separate from the released CLI so a fresh harness runner
//! does not compile the full product just to begin measuring a child command.

mod harness_mark;

pub use harness_mark::{
    HARNESS_BOOTSTRAP_KIND_ENV, HARNESS_BOOTSTRAP_SENTINEL, HARNESS_BOOTSTRAP_START_NS_ENV,
    HARNESS_TIMING_SENTINEL, harness_mark,
};
