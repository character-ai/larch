//! Effect-free PR summary composition.

use std::{collections::BTreeSet, error::Error, fmt};

/// A semantic failure while extracting the plan goal.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PrSummaryError {
    /// The `## Goal` section had no content line before the next heading.
    MissingGoal,
}

impl fmt::Display for PrSummaryError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingGoal => formatter.write_str("no Goal line found"),
        }
    }
}

impl Error for PrSummaryError {}

/// Compose the goal, test-file, and cross-directory PR summary bullets.
///
/// `changed_paths` is the exact name-only diff from the merge base to `HEAD`.
/// Keeping extraction and classification here makes the Git adapter in the CLI
/// a replaceable effect boundary.
///
/// # Errors
///
/// Returns [`PrSummaryError::MissingGoal`] when the plan has no nonblank goal
/// line before the next Markdown heading.
pub fn compose_pr_summary<'a>(
    plan_goals: &str,
    changed_paths: impl IntoIterator<Item = &'a str>,
) -> Result<String, PrSummaryError> {
    let mut in_goal = false;
    let mut goal = None;
    for line in plan_goals.lines() {
        if line.starts_with("## Goal") {
            in_goal = true;
            continue;
        }
        if in_goal && line.starts_with('#') {
            break;
        }
        if in_goal && !line.trim().is_empty() {
            goal = Some(line.trim());
            break;
        }
    }
    let goal = goal.ok_or(PrSummaryError::MissingGoal)?;

    let changed: Vec<&str> = changed_paths
        .into_iter()
        .filter(|path| !path.is_empty())
        .collect();
    let mut bullets = vec![format!("- {goal}")];
    if !changed.is_empty() {
        let test_count = changed
            .iter()
            .filter(|path| is_shell_test_path(path))
            .count();
        if test_count > 0 {
            bullets.push(format!("- Added or updated {test_count} test file(s)."));
        }
        let directories: BTreeSet<&str> = changed
            .iter()
            .map(|path| path.split_once('/').map_or(".", |(directory, _)| directory))
            .collect();
        if directories.len() > 2 {
            bullets.push(format!(
                "- Cross-cutting changes across: {}.",
                directories.into_iter().collect::<Vec<_>>().join(",")
            ));
        }
    }
    Ok(bullets.join("\n") + "\n")
}

fn is_shell_test_path(path: &str) -> bool {
    path.rsplit('/').next().is_some_and(|name| {
        name.strip_prefix("test-")
            .and_then(|tail| tail.strip_suffix(".sh"))
            .is_some_and(|middle| !middle.is_empty())
    })
}

#[cfg(test)]
mod tests {
    use super::{PrSummaryError, compose_pr_summary};

    #[test]
    fn extracts_the_first_nonblank_goal_line() {
        assert_eq!(
            compose_pr_summary(
                "# Plan\n\n## Goal\n\n  Preserve the public wire.  \n## Scope\nLater\n",
                std::iter::empty(),
            ),
            Ok("- Preserve the public wire.\n".to_owned())
        );
    }

    #[test]
    fn accepts_the_frozen_goal_heading_prefix() {
        assert_eq!(
            compose_pr_summary("## Goals and non-goals\nShip it\n", std::iter::empty()),
            Ok("- Ship it\n".to_owned())
        );
    }

    #[test]
    fn refuses_a_missing_or_empty_goal_section() {
        assert_eq!(
            compose_pr_summary("# Plan\n## Scope\nNo goal\n", std::iter::empty()),
            Err(PrSummaryError::MissingGoal)
        );
        assert_eq!(
            compose_pr_summary("## Goal\n\n## Scope\nNo goal\n", std::iter::empty()),
            Err(PrSummaryError::MissingGoal)
        );
    }

    #[test]
    fn counts_only_test_dash_shell_basenames() {
        let paths = [
            "test-root.sh",
            "scripts/test-nested.sh",
            "scripts/test-.sh",
            "scripts/not-test.sh",
            "scripts/test-python.py",
        ];
        assert_eq!(
            compose_pr_summary("## Goal\nPort it\n", paths),
            Ok(concat!("- Port it\n", "- Added or updated 2 test file(s).\n").to_owned())
        );
    }

    #[test]
    fn adds_a_sorted_cross_cutting_bullet_after_three_directories() {
        let paths = ["z/file", "root.md", "a/file", "z/other"];
        assert_eq!(
            compose_pr_summary("## Goal\nPort it\n", paths),
            Ok(concat!("- Port it\n", "- Cross-cutting changes across: .,a,z.\n").to_owned())
        );
    }

    #[test]
    fn omits_change_bullets_when_the_diff_is_empty() {
        assert_eq!(
            compose_pr_summary("## Goal\nPort it\n", ["", ""]),
            Ok("- Port it\n".to_owned())
        );
    }
}
