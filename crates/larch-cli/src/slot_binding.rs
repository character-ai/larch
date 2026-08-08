//! Bind waterfall outputs back to the slot manifest that produced them.
//!
//! `agent dispatch-waterfall` publishes a compressed result list: dropped slots
//! leave no entry, and a slot that fell through to a later phase writes a
//! phase-suffixed path. Position in that list is therefore not slot identity,
//! so a panel consumer that reads results by index can attribute one voter's
//! output to another slot. Matching on each manifest row's own output path,
//! across all three phase spellings, is the only safe binding.

use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::Path,
};

use serde_json::Value;

/// The three phase spellings one slot output can land under.
const PHASES: [&str; 3] = ["phase1", "phase2", "phase3"];

/// Where one named slot's result landed, or why it has none.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct SlotOutputBinding {
    /// Resolved result path, empty when the slot produced none.
    pub path: String,
    /// Vendor the waterfall reported for that result.
    pub tool: String,
    /// Whether the dispatcher recorded an explicit drop for the slot.
    pub dropped: bool,
}

/// One manifest row, reduced to the fields output binding reads.
struct SlotRow {
    name: String,
    output: String,
}

/// Bind waterfall outputs by manifest slot, not by compressed stdout position.
///
/// A manifest that cannot be read or that carries no usable row binds nothing,
/// which the caller reports as a fully failed panel rather than a silent pass.
pub fn bind_manifest_slot_outputs(
    manifest: &Path,
    values: &BTreeMap<String, String>,
) -> BTreeMap<String, SlotOutputBinding> {
    let resolved = resolved_paths(values);
    let tools: Vec<&str> = values
        .get("ALL_OUTPUT_TOOLS")
        .map(|value| value.split_whitespace().collect())
        .unwrap_or_default();
    let dropped = dropped_slots(values);
    let mut bound: BTreeSet<usize> = BTreeSet::new();
    let mut bindings = BTreeMap::new();
    for row in slot_rows(manifest) {
        let candidates = phase_candidates(&row.output);
        let matched = resolved.iter().enumerate().position(|(index, candidate)| {
            !bound.contains(&index) && matches_output(candidate, &candidates)
        });
        let Some(index) = matched else {
            bindings.insert(
                row.name.clone(),
                SlotOutputBinding {
                    dropped: dropped.contains(&row.name),
                    ..SlotOutputBinding::default()
                },
            );
            continue;
        };
        let _inserted = bound.insert(index);
        bindings.insert(
            row.name.clone(),
            SlotOutputBinding {
                path: resolved[index].clone(),
                tool: tools.get(index).copied().unwrap_or_default().to_owned(),
                dropped: false,
            },
        );
    }
    bindings
}

/// Prefer the published path file, which survives a truncated stdout capture.
fn resolved_paths(values: &BTreeMap<String, String>) -> Vec<String> {
    let path_file = values
        .get("ALL_OUTPUT_FILES_PATH")
        .filter(|value| !value.is_empty());
    if let Some(file) = path_file
        && let Ok(text) = fs::read_to_string(file)
    {
        return text
            .lines()
            .filter(|line| !line.is_empty())
            .map(str::to_owned)
            .collect();
    }
    values
        .get("ALL_OUTPUT_FILES")
        .map(|value| value.split_whitespace().map(str::to_owned).collect())
        .unwrap_or_default()
}

fn dropped_slots(values: &BTreeMap<String, String>) -> BTreeSet<String> {
    let Some(file) = values
        .get("DROPPED_SLOTS_FILE")
        .filter(|value| !value.is_empty())
    else {
        return BTreeSet::new();
    };
    let Ok(text) = fs::read_to_string(file) else {
        return BTreeSet::new();
    };
    text.lines()
        .filter(|line| !line.is_empty())
        .map(|line| line.split('\t').next().unwrap_or(line).to_owned())
        .collect()
}

fn slot_rows(manifest: &Path) -> Vec<SlotRow> {
    let Ok(text) = fs::read_to_string(manifest) else {
        return Vec::new();
    };
    text.lines()
        .filter(|line| !line.is_empty())
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter_map(|row| {
            let name = row.get("slot")?.as_str()?.to_owned();
            let tool = row.get("tool")?.as_str()?;
            let output = row.get("output")?.as_str()?.to_owned();
            let valid = !name.is_empty()
                && matches!(tool, "codex" | "cursor")
                && !output.is_empty()
                && !output.contains(['\n', '\r']);
            valid.then_some(SlotRow { name, output })
        })
        .collect()
}

/// Every path spelling one slot's base output can appear under.
fn phase_candidates(output: &str) -> Vec<String> {
    PHASES
        .iter()
        .map(|phase| {
            if *phase == "phase1" {
                output.to_owned()
            } else if let Some(stem) = output.strip_suffix(".txt") {
                format!("{stem}-{phase}.txt")
            } else {
                format!("{output}-{phase}")
            }
        })
        .collect()
}

/// A candidate matches by full path, or by basename when roots differ.
fn matches_output(candidate: &str, expected: &[String]) -> bool {
    if expected.iter().any(|value| value == candidate) {
        return true;
    }
    let name = Path::new(candidate).file_name();
    name.is_some_and(|name| {
        expected
            .iter()
            .any(|value| Path::new(value).file_name() == Some(name))
    })
}

#[cfg(test)]
mod tests {
    use super::{bind_manifest_slot_outputs, phase_candidates};
    use std::collections::BTreeMap;

    fn manifest(directory: &std::path::Path, rows: &[&str]) -> std::path::PathBuf {
        let path = directory.join("slots.ndjson");
        std::fs::write(&path, format!("{}\n", rows.join("\n"))).expect("write manifest");
        path
    }

    #[test]
    fn phase_candidates_cover_every_spelling() {
        assert_eq!(
            phase_candidates("/tmp/out.txt"),
            ["/tmp/out.txt", "/tmp/out-phase2.txt", "/tmp/out-phase3.txt"]
        );
        assert_eq!(
            phase_candidates("/tmp/out"),
            ["/tmp/out", "/tmp/out-phase2", "/tmp/out-phase3"]
        );
    }

    #[test]
    fn a_fallback_result_binds_to_its_own_slot() {
        let directory = tempfile::tempdir().expect("fixture");
        let path = manifest(
            directory.path(),
            &[
                r#"{"slot":"voter-1","tool":"codex","output":"/tmp/one.txt"}"#,
                r#"{"slot":"voter-2","tool":"codex","output":"/tmp/two.txt"}"#,
            ],
        );
        let mut values = BTreeMap::new();
        let _replaced = values.insert(
            "ALL_OUTPUT_FILES".to_owned(),
            "/tmp/two-phase3.txt".to_owned(),
        );
        let _replaced = values.insert("ALL_OUTPUT_TOOLS".to_owned(), "claude".to_owned());
        let bindings = bind_manifest_slot_outputs(&path, &values);
        assert_eq!(bindings["voter-1"].path, "");
        assert_eq!(bindings["voter-2"].path, "/tmp/two-phase3.txt");
        assert_eq!(bindings["voter-2"].tool, "claude");
    }

    #[test]
    fn a_dropped_slot_reports_its_drop() {
        let directory = tempfile::tempdir().expect("fixture");
        let path = manifest(
            directory.path(),
            &[r#"{"slot":"voter-3","tool":"codex","output":"/tmp/three.txt"}"#],
        );
        let dropped = directory.path().join("drops");
        std::fs::write(&dropped, "voter-3\tcodex\tstraggler-dropped\tcut\n").expect("write drops");
        let mut values = BTreeMap::new();
        let _replaced = values.insert(
            "DROPPED_SLOTS_FILE".to_owned(),
            dropped.display().to_string(),
        );
        let bindings = bind_manifest_slot_outputs(&path, &values);
        assert!(bindings["voter-3"].dropped);
    }
}
