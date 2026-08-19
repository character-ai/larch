//! Composition and CLI surface for bounded connectivity waits.

use std::{env, process::ExitCode, time::Duration};

use clap::{Args, Subcommand};
use larch_adapters::{
    clock::TokioClock,
    http_client::FixedConnectivityProbe,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    DEFAULT_NET_WAIT_CEILING, DEFAULT_NET_WAIT_INITIAL_BACKOFF, DEFAULT_NET_WAIT_MAX_BACKOFF,
    WaitOnlinePolicy, WaitOnlineResult, emit_kv, wait_online,
};

const TEST_FORCE_OFFLINE: &str = "LARCH_TEST_NET_FORCE_OFFLINE";

#[derive(Subcommand)]
pub enum NetCommand {
    /// Wait until the fixed Anthropic and GitHub endpoints are reachable.
    #[command(name = "wait-online")]
    WaitOnline(WaitOnlineArguments),
}

#[derive(Args)]
pub struct WaitOnlineArguments {
    /// Positive monotonic awake-time ceiling in seconds, up to the core limit.
    #[arg(long, default_value_t = DEFAULT_NET_WAIT_CEILING.as_secs())]
    ceiling_s: u64,
}

#[must_use]
pub fn run(command: NetCommand) -> ExitCode {
    match command {
        NetCommand::WaitOnline(arguments) => run_wait_online(&arguments),
    }
}

fn run_wait_online(arguments: &WaitOnlineArguments) -> ExitCode {
    match wait_online_for(Duration::from_secs(arguments.ceiling_s)) {
        Ok(result) => {
            emit_result(result);
            if result.online() {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            }
        }
        Err(error) => {
            eprintln!("net wait-online: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Run the shared fixed-endpoint wait with its production adapters.
pub fn wait_online_for(ceiling: Duration) -> Result<WaitOnlineResult, String> {
    let policy = wait_online_policy(ceiling)?;
    let force_offline = env::var(TEST_FORCE_OFFLINE).as_deref() == Ok("true");
    let probe = FixedConnectivityProbe::new(force_offline).map_err(|error| error.to_string())?;
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let clock = TokioClock::new();
    let cancellation = Cancellation::new();
    runtime
        .block_on(wait_online(&probe, &clock, &cancellation, policy))
        .map_err(|error| error.to_string())
}

/// Validate a caller's ceiling before any filesystem or network effect.
pub fn validate_wait_online_ceiling(ceiling: Duration) -> Result<(), String> {
    wait_online_policy(ceiling).map(|_policy| ())
}

fn wait_online_policy(ceiling: Duration) -> Result<WaitOnlinePolicy, String> {
    WaitOnlinePolicy::new(
        ceiling,
        DEFAULT_NET_WAIT_INITIAL_BACKOFF,
        DEFAULT_NET_WAIT_MAX_BACKOFF,
    )
    .map_err(|error| error.to_string())
}

fn emit_result(result: WaitOnlineResult) {
    emit_kv("NET_ONLINE", if result.online() { "true" } else { "false" });
    emit_kv(
        "NET_PROBE_ATTEMPT_COUNT",
        &result.probe_attempts().to_string(),
    );
    emit_kv("NET_WAIT_SECONDS", &result.waited().as_secs().to_string());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_ceiling_is_rejected_without_a_probe() {
        assert_eq!(
            run_wait_online(&WaitOnlineArguments { ceiling_s: 0 }),
            ExitCode::FAILURE
        );
    }
}
