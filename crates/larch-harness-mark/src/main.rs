//! Standalone developer and CI entrypoint for the lightweight harness timer.

use std::{env, process::ExitCode};

fn main() -> ExitCode {
    let arguments: Vec<_> = env::args_os().skip(1).collect();
    larch_harness_mark::harness_mark(&arguments)
}
