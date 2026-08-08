//! The implementation-lease line one `/implement` run writes into an issue body.
//!
//! A lease is a single unfenced HTML comment naming the run that owns the
//! issue, the branch it is building, the base commit it started from, the plan
//! it was admitted against, and when it was last refreshed. The mutation owner
//! decides whether a lease change is authorized; this module decides only what
//! the line looks like and where it sits in a body.
//!
//! Fence awareness matters because a design plan may quote an example lease
//! inside a fenced block. A quoted line is documentation, so only the unfenced
//! line binds a run, and a body carrying two of them binds nobody.

use crate::text::{balanced_fence_line_indices, split_lines_keep_ends};
use regex::Regex;
use std::sync::LazyLock;

/// Token every lease line opens with, fenced or not.
const LEASE_OPENING: &str = "<!-- larch:implementation-lease";

static LEASE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^<!-- larch:implementation-lease v1 run_id=([A-Za-z0-9][A-Za-z0-9._-]{0,127}) branch=([^\s]+) base=([0-9a-f]{40}) plan=([0-9a-f]{64}) updated_at=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) -->$",
    )
    .expect("implementation lease expression is valid")
});
static BRANCH_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$").expect("branch expression"));

/// One parsed or composed implementation lease.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImplementationLease {
    pub run_id: String,
    pub branch: String,
    pub base: String,
    pub plan: String,
    pub updated_at: String,
}

/// Why a lease could not be rendered or upserted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LeaseDefect {
    /// The composed line does not match the frozen v1 grammar.
    Invalid,
    /// The body already carries a lease line that is not exactly one valid one.
    Malformed,
}

impl LeaseDefect {
    /// Return the stable reason token a caller republishes.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        match self {
            Self::Invalid => "invalid-implementation-lease",
            Self::Malformed => "malformed-implementation-lease",
        }
    }
}

/// Return the sole unfenced lease in `body`, or `None`.
///
/// Two lease lines, a malformed one, or none at all all read as "no lease":
/// the caller's next step is to refuse a run mismatch, and an ambiguous body
/// never proves the caller owns the issue.
#[must_use]
pub fn parse_implementation_lease(body: &str) -> Option<ImplementationLease> {
    let lines: Vec<&str> = body.lines().collect();
    let fenced = balanced_fence_line_indices(&lines);
    let mut candidates = lines
        .iter()
        .enumerate()
        .filter(|(index, line)| !fenced.contains(index) && line.starts_with(LEASE_OPENING))
        .map(|(_, line)| *line);
    let only = candidates.next()?;
    if candidates.next().is_some() {
        return None;
    }
    let captures = LEASE_RE.captures(only)?;
    Some(ImplementationLease {
        run_id: captures[1].to_owned(),
        branch: captures[2].to_owned(),
        base: captures[3].to_owned(),
        plan: captures[4].to_owned(),
        updated_at: captures[5].to_owned(),
    })
}

/// Render the exact v1 bytes for `lease`, refusing any invalid field.
///
/// # Errors
///
/// Returns [`LeaseDefect::Invalid`] when the composed line leaves the grammar
/// or when the branch is not a name Git would accept.
pub fn render_implementation_lease(lease: &ImplementationLease) -> Result<String, LeaseDefect> {
    let line = format!(
        "<!-- larch:implementation-lease v1 run_id={} branch={} base={} plan={} updated_at={} -->",
        lease.run_id, lease.branch, lease.base, lease.plan, lease.updated_at
    );
    if !LEASE_RE.is_match(&line)
        || !valid_branch(&lease.branch)
        || !valid_timestamp(&lease.updated_at)
    {
        return Err(LeaseDefect::Invalid);
    }
    Ok(line)
}

/// Replace the sole unfenced lease in `body`, or append one.
///
/// # Errors
///
/// Returns [`LeaseDefect::Invalid`] for an unrenderable lease and
/// [`LeaseDefect::Malformed`] when the body carries a lease-shaped line that is
/// not exactly one valid lease.
pub fn upsert_implementation_lease(
    body: &str,
    lease: &ImplementationLease,
) -> Result<String, LeaseDefect> {
    let rendered = render_implementation_lease(lease)?;
    let mut lines: Vec<String> = split_lines_keep_ends(body)
        .into_iter()
        .map(str::to_owned)
        .collect();
    let stripped: Vec<&str> = lines
        .iter()
        .map(|line| line.trim_end_matches(['\r', '\n']))
        .collect();
    let fenced = balanced_fence_line_indices(&stripped);
    let mut valid = Vec::new();
    for (index, content) in stripped.iter().enumerate() {
        if fenced.contains(&index) || !content.starts_with(LEASE_OPENING) {
            continue;
        }
        if LEASE_RE.is_match(content) {
            valid.push(index);
        } else {
            return Err(LeaseDefect::Malformed);
        }
    }
    if valid.len() > 1 {
        return Err(LeaseDefect::Malformed);
    }
    if let Some(&index) = valid.first() {
        let newline = if lines[index].ends_with("\r\n") {
            "\r\n"
        } else {
            "\n"
        };
        lines[index] = format!("{rendered}{newline}");
        return Ok(lines.concat());
    }
    let separator = if body.is_empty() || body.ends_with(['\n', '\r']) {
        ""
    } else {
        "\n"
    };
    Ok(format!("{body}{separator}{rendered}\n"))
}

/// Report whether `branch` is a Git ref name the lease grammar accepts.
#[allow(
    clippy::case_sensitive_file_extension_comparisons,
    reason = "Git's own `.lock` suffix rule is case sensitive"
)]
fn valid_branch(branch: &str) -> bool {
    BRANCH_RE.is_match(branch)
        && !branch.contains("..")
        && !branch.contains("@{")
        && !branch.contains("//")
        && branch.split('/').all(|part| {
            // A case-sensitive suffix check is the point: Git refuses exactly
            // `.lock`, so `.LOCK` is a legal branch name the grammar accepts.
            !part.is_empty() && !part.starts_with('.') && !part.ends_with(".lock")
        })
}

/// Report whether `value` is a real `%Y-%m-%dT%H:%M:%SZ` instant.
///
/// The expression above already fixes the shape, so this only rejects a
/// well-shaped impossibility such as month 13, exactly as `strptime` did.
fn valid_timestamp(value: &str) -> bool {
    chrono::NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%SZ").is_ok()
}

#[cfg(test)]
mod tests {
    use super::{
        ImplementationLease, LeaseDefect, parse_implementation_lease, render_implementation_lease,
        upsert_implementation_lease,
    };

    fn lease() -> ImplementationLease {
        ImplementationLease {
            run_id: "run-1".to_owned(),
            branch: "issue-1-work".to_owned(),
            base: "a".repeat(40),
            plan: "b".repeat(64),
            updated_at: "2026-08-08T00:00:00Z".to_owned(),
        }
    }

    #[test]
    fn a_rendered_lease_round_trips_and_an_invalid_field_refuses() {
        let rendered = render_implementation_lease(&lease()).expect("valid lease renders");
        assert_eq!(parse_implementation_lease(&rendered), Some(lease()));
        for (field, value) in [
            ("branch", "feature/.hidden"),
            ("branch", "a..b"),
            ("branch", "a//b"),
            ("branch", "a@{b"),
            ("branch", "work.lock"),
            ("run_id", "bad id"),
        ] {
            let mut broken = lease();
            if field == "branch" {
                broken.branch = value.to_owned();
            } else {
                broken.run_id = value.to_owned();
            }
            assert_eq!(
                render_implementation_lease(&broken),
                Err(LeaseDefect::Invalid),
                "{field}={value}"
            );
        }
        let mut impossible = lease();
        impossible.updated_at = "2026-13-08T00:00:00Z".to_owned();
        assert_eq!(
            render_implementation_lease(&impossible),
            Err(LeaseDefect::Invalid)
        );
    }

    #[test]
    fn a_fenced_lease_is_documentation_and_two_unfenced_leases_bind_nobody() {
        let rendered = render_implementation_lease(&lease()).expect("valid lease renders");
        let fenced = format!("intro\n\n```\n{rendered}\n```\n");
        assert_eq!(parse_implementation_lease(&fenced), None);
        let twice = format!("{rendered}\n{rendered}\n");
        assert_eq!(parse_implementation_lease(&twice), None);
        assert_eq!(
            upsert_implementation_lease(&twice, &lease()),
            Err(LeaseDefect::Malformed)
        );
        assert_eq!(
            upsert_implementation_lease("<!-- larch:implementation-lease v2 -->\n", &lease()),
            Err(LeaseDefect::Malformed)
        );
    }

    #[test]
    fn an_upsert_appends_once_and_then_replaces_in_place() {
        let rendered = render_implementation_lease(&lease()).expect("valid lease renders");
        assert_eq!(
            upsert_implementation_lease("body", &lease()),
            Ok(format!("body\n{rendered}\n"))
        );
        assert_eq!(
            upsert_implementation_lease("", &lease()),
            Ok(format!("{rendered}\n"))
        );
        let mut refreshed = lease();
        refreshed.updated_at = "2026-08-09T01:02:03Z".to_owned();
        let refreshed_line =
            render_implementation_lease(&refreshed).expect("refreshed lease renders");
        assert_eq!(
            upsert_implementation_lease(&format!("body\r\n{rendered}\r\ntail\r\n"), &refreshed),
            Ok(format!("body\r\n{refreshed_line}\r\ntail\r\n"))
        );
        // The fenced example above survives an upsert untouched.
        let fenced = format!("```\n{rendered}\n```\n");
        assert_eq!(
            upsert_implementation_lease(&fenced, &lease()),
            Ok(format!("{fenced}{rendered}\n"))
        );
    }
}
