//! Standalone developer and CI entrypoint for the lightweight harness timer.

use std::{env, process::ExitCode};

#[cfg(not(test))]
mod harness_mark;
#[cfg(test)]
use larch_harness_mark as harness_mark;

fn main() -> ExitCode {
    let arguments: Vec<_> = env::args_os().skip(1).collect();
    harness_mark::harness_mark(&arguments)
}
