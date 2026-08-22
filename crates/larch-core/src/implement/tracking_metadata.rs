//! Effect-free tracking-issue metadata composition.

/// Values rendered into the marker-keyed implementation metadata comment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TrackingMetadata<'a> {
    pub run_id: &'a str,
    pub run_log: &'a str,
    pub issue: &'a str,
    pub agent: &'a str,
    pub coder: &'a str,
    pub force_requested: bool,
    pub plugin_version: &'a str,
}

/// Render the exact metadata document consumed by `tracking-issue upsert-summary`.
#[must_use]
pub fn compose_tracking_metadata(input: &TrackingMetadata<'_>) -> String {
    let mut lines = vec![
        format!("Run ID: `{}`", input.run_id),
        format!("Run log: {}", input.run_log),
        format!("Tracking issue: #{}", input.issue),
        format!("Agent: `{}`", fallback(input.agent, "claude")),
        format!("Coder: `{}`", fallback(input.coder, "claude")),
    ];
    if input.force_requested {
        lines.push("Force: true".to_owned());
    }
    lines.push(format!("Larch version: `{}`", input.plugin_version));
    lines.join("\n") + "\n"
}

const fn fallback<'a>(value: &'a str, default: &'a str) -> &'a str {
    if value.is_empty() { default } else { value }
}

#[cfg(test)]
mod tests {
    use super::{TrackingMetadata, compose_tracking_metadata};

    #[test]
    fn renders_the_frozen_metadata_order_and_defaults() {
        assert_eq!(
            compose_tracking_metadata(&TrackingMetadata {
                run_id: "run-7",
                run_log: "provider `gcs`, run `run-7`",
                issue: "8789",
                agent: "",
                coder: "",
                force_requested: false,
                plugin_version: "1.2.3",
            }),
            concat!(
                "Run ID: `run-7`\n",
                "Run log: provider `gcs`, run `run-7`\n",
                "Tracking issue: #8789\n",
                "Agent: `claude`\n",
                "Coder: `claude`\n",
                "Larch version: `1.2.3`\n"
            )
        );
    }

    #[test]
    fn includes_force_and_explicit_roles() {
        assert_eq!(
            compose_tracking_metadata(&TrackingMetadata {
                run_id: "run.8",
                run_log: "N/A",
                issue: "9",
                agent: "codex",
                coder: "cursor",
                force_requested: true,
                plugin_version: "unknown",
            }),
            concat!(
                "Run ID: `run.8`\n",
                "Run log: N/A\n",
                "Tracking issue: #9\n",
                "Agent: `codex`\n",
                "Coder: `cursor`\n",
                "Force: true\n",
                "Larch version: `unknown`\n"
            )
        );
    }
}
