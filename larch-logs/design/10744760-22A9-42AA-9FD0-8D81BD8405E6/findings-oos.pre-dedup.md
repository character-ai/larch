### OOS_1: Design transcript capture is wired only through `publish_core`, not clarify or pause `log-publish`
- **Description**: Design transcript capture is wired only through `publish_core`, not clarify or pause `log-publish`. Scenario: Clarify and pause call `design log-publish` directly and bypass `publish_core`, so successful clarify/pause publishes still lack `session-transcript.jsonl` and stay zero-reference in heatmap/realized-cost even after the main Gate C hook lands.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Clarify and pause design log-publish paths bypass publish_core transcript capture.
- **Description**: [OUT_OF_SCOPE] Clarify and pause design log-publish paths bypass publish_core transcript capture.. Scenario: Those flows call design log-publish directly without the planned design_publish publish_core hook, so resumed or clarify-published design runs still lack session-transcript.jsonl and stay unmeasured.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py; python/larch/design/design_pause.py
- **Phase**: design



