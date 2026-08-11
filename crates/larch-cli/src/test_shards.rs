//! `larch test-shard` command composition.

use clap::{Args, Subcommand};
use larch_adapters::{ConfinedPath, atomic_write_utf8, read_utf8};
use larch_core::{
    TestShardMap, TestShardTiming, pack_test_shards_with_fixed_startup, read_makefile_shards,
    rewrite_makefile_shards,
};
use serde::Serialize;
use std::{
    fs,
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

const DEFAULT_GUARD: &str = "";
const DEFAULT_MAKEFILE_PATH: &str = "Makefile";

#[derive(Subcommand)]
pub enum TestShardCommand {
    /// Pack timing rows from stdin into deterministic LPT shard assignments.
    Pack(PackArguments),
    /// Read literal `test-harnesses-N:` Makefile rules as JSON.
    ReadMakefile(MakefileArguments),
    /// Rewrite selected literal `test-harnesses-N:` Makefile rules from stdin JSON.
    WriteMakefile(WriteMakefileArguments),
}

#[derive(Args)]
pub struct PackArguments {
    /// Number of one-based output shards.
    #[arg(long, value_parser = parse_shard_count)]
    n_shards: u32,
    /// Target that must be first in its assigned shard. An empty value disables it.
    #[arg(long, default_value = DEFAULT_GUARD)]
    guard: String,
    /// Unmeasured target to place with zero weight. Repeat for multiple targets.
    #[arg(long = "extra")]
    extras: Vec<String>,
    /// Fixed startup cost charged to every shard for packing estimates.
    #[arg(long, default_value_t = 0.0, value_parser = parse_nonnegative_seconds)]
    fixed_startup_seconds: f64,
    /// JSON timing rows. Reads stdin when omitted.
    #[arg(long)]
    input: Option<PathBuf>,
}

#[derive(Args)]
pub struct MakefileArguments {
    /// Makefile to read or rewrite.
    #[arg(long, default_value = DEFAULT_MAKEFILE_PATH)]
    path: PathBuf,
}

#[derive(Args)]
pub struct WriteMakefileArguments {
    /// Makefile to rewrite.
    #[arg(long, default_value = DEFAULT_MAKEFILE_PATH)]
    path: PathBuf,
    /// JSON shard map. Reads stdin when omitted.
    #[arg(long)]
    input: Option<PathBuf>,
}

pub fn run(command: TestShardCommand) -> ExitCode {
    match run_inner(command) {
        Ok(Some(output)) => {
            if let Err(error) = std::io::stdout().lock().write_all(&output) {
                eprintln!("test-shard: cannot write output: {error}");
                return ExitCode::from(1);
            }
            ExitCode::SUCCESS
        }
        Ok(None) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("test-shard: {error}");
            ExitCode::from(1)
        }
    }
}

fn run_inner(command: TestShardCommand) -> Result<Option<Vec<u8>>, String> {
    match command {
        TestShardCommand::Pack(arguments) => {
            let timings = read_json_input::<Vec<TestShardTiming>>(arguments.input.as_deref())?;
            let shards = pack_test_shards_with_fixed_startup(
                &timings,
                arguments.n_shards,
                &arguments.guard,
                &arguments.extras,
                arguments.fixed_startup_seconds,
            )?;
            serialize_json(&shards).map(Some)
        }
        TestShardCommand::ReadMakefile(arguments) => {
            let source = read_makefile(&arguments.path)?;
            serialize_json(&read_makefile_shards(&source)).map(Some)
        }
        TestShardCommand::WriteMakefile(arguments) => {
            let shards = read_json_input::<TestShardMap>(arguments.input.as_deref())?;
            if shards.keys().any(|shard| *shard == 0) {
                return Err("shard identifiers must be at least 1".to_owned());
            }
            let source = read_makefile(&arguments.path)?;
            let rewritten = rewrite_makefile_shards(&source, &shards);
            write_makefile_atomically(&arguments.path, &rewritten)?;
            Ok(None)
        }
    }
}

fn parse_shard_count(value: &str) -> Result<u32, String> {
    value
        .parse::<u32>()
        .ok()
        .filter(|count| *count > 0)
        .ok_or_else(|| format!("expected a positive integer, got {value:?}"))
}

fn parse_nonnegative_seconds(value: &str) -> Result<f64, String> {
    value
        .parse::<f64>()
        .ok()
        .filter(|seconds| seconds.is_finite() && *seconds >= 0.0)
        .ok_or_else(|| format!("expected a non-negative finite number, got {value:?}"))
}

fn read_json_input<T: serde::de::DeserializeOwned>(path: Option<&Path>) -> Result<T, String> {
    let input = if let Some(path) = path {
        fs::read(path)
            .map_err(|error| format!("cannot read JSON input {}: {error}", path.display()))?
    } else {
        let mut input = Vec::new();
        std::io::stdin()
            .lock()
            .read_to_end(&mut input)
            .map_err(|error| format!("cannot read stdin: {error}"))?;
        input
    };
    let source = path.map_or_else(|| "stdin".to_owned(), |path| path.display().to_string());
    serde_json::from_slice(&input).map_err(|error| format!("invalid JSON from {source}: {error}"))
}

fn serialize_json(value: &impl Serialize) -> Result<Vec<u8>, String> {
    let mut output = serde_json::to_vec(value)
        .map_err(|error| format!("cannot serialize test-shard output: {error}"))?;
    output.push(b'\n');
    Ok(output)
}

fn read_makefile(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| format!("cannot read {}: {error}", path.display()))
}

pub fn read_makefile_shard_map(path: &ConfinedPath) -> Result<TestShardMap, String> {
    let source = read_utf8(path).map_err(|error| error.to_string())?;
    Ok(read_makefile_shards(&source))
}

pub fn write_makefile_shard_map(
    source: &ConfinedPath,
    target: &ConfinedPath,
    shards: &TestShardMap,
) -> Result<(), String> {
    if shards.keys().any(|shard| *shard == 0) {
        return Err("shard identifiers must be at least 1".to_owned());
    }
    let source = read_utf8(source).map_err(|error| error.to_string())?;
    let rewritten = rewrite_makefile_shards(&source, shards);
    atomic_write_utf8(target, &rewritten, 0o644).map_err(|error| error.to_string())
}

/// Prove a rewritten harness map preserves the candidate's partition contract.
///
/// The full repository lint owns validation of the rest of the Makefile.  This
/// narrower check is the mutation-time contract: the rewriter can change only
/// shard prerequisites, so it must retain the exact target set and the guard
/// must remain the first prerequisite in exactly one shard.
pub fn validate_rebalanced_harness_shards(
    before: &TestShardMap,
    after: &TestShardMap,
) -> Result<(), String> {
    if before.is_empty() || before.len() != after.len() {
        return Err("harness shard count changed during candidate rewrite".to_owned());
    }
    let expected = u32::try_from(before.len())
        .map_err(|_| "harness shard count exceeds supported range".to_owned())?;
    if after.keys().copied().ne(1..=expected) {
        return Err("harness shard identifiers must remain contiguous from 1".to_owned());
    }
    let mut before_targets = std::collections::BTreeSet::new();
    let mut after_targets = std::collections::BTreeSet::new();
    let mut guard_shards = Vec::new();
    for targets in before.values() {
        for target in targets {
            if target.is_empty() || !before_targets.insert(target) {
                return Err("current harness shard map has an empty or duplicate target".to_owned());
            }
        }
    }
    for (shard, targets) in after {
        for target in targets {
            if target.is_empty() || !after_targets.insert(target) {
                return Err(
                    "candidate harness shard map has an empty or duplicate target".to_owned(),
                );
            }
        }
        if targets
            .iter()
            .any(|target| target == "test-harness-shards-coverage")
        {
            guard_shards.push((*shard, targets.first().map(String::as_str)));
        }
    }
    if before_targets != after_targets {
        return Err("candidate harness shard map changed the target inventory".to_owned());
    }
    match guard_shards.as_slice() {
        [(_shard, Some("test-harness-shards-coverage"))] => Ok(()),
        [_] => Err("test-harness-shards-coverage must be the first shard prerequisite".to_owned()),
        _ => Err("test-harness-shards-coverage must occur in exactly one shard".to_owned()),
    }
}

pub fn write_makefile_atomically(path: &Path, contents: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let permissions = fs::metadata(path)
        .ok()
        .map(|metadata| metadata.permissions());
    let mut temporary = tempfile::NamedTempFile::new_in(parent).map_err(|error| {
        format!(
            "cannot create temporary Makefile beside {}: {error}",
            path.display()
        )
    })?;
    temporary
        .write_all(contents.as_bytes())
        .map_err(|error| format!("cannot write temporary Makefile: {error}"))?;
    temporary
        .flush()
        .map_err(|error| format!("cannot flush temporary Makefile: {error}"))?;
    if let Some(permissions) = permissions {
        temporary
            .as_file()
            .set_permissions(permissions)
            .map_err(|error| format!("cannot preserve Makefile permissions: {error}"))?;
    }
    temporary
        .persist(path)
        .map_err(|error| format!("cannot atomically replace {}: {error}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::validate_rebalanced_harness_shards;
    use super::{parse_nonnegative_seconds, parse_shard_count};

    #[test]
    fn shard_count_parser_rejects_zero_and_non_numbers() {
        assert_eq!(parse_shard_count("3"), Ok(3));
        assert!(parse_shard_count("0").is_err());
        assert!(parse_shard_count("nope").is_err());
    }

    #[test]
    fn fixed_startup_parser_rejects_negative_and_non_finite_values() {
        assert_eq!(parse_nonnegative_seconds("3.5"), Ok(3.5));
        assert!(parse_nonnegative_seconds("-1").is_err());
        assert!(parse_nonnegative_seconds("NaN").is_err());
    }

    #[test]
    fn candidate_validator_rejects_a_moved_coverage_guard() {
        let before = larch_core::TestShardMap::from([
            (1, vec!["test-harness-shards-coverage".into(), "a".into()]),
            (2, vec!["b".into()]),
        ]);
        let mut after = before.clone();
        after
            .get_mut(&1)
            .expect("first shard exists")
            .rotate_left(1);
        assert!(validate_rebalanced_harness_shards(&before, &before).is_ok());
        assert!(validate_rebalanced_harness_shards(&before, &after).is_err());
    }
}
