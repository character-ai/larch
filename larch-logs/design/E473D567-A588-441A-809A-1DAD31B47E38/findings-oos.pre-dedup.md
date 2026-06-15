### OOS_1:
- **Description**: NS-retry temp prompt cleanup omitted. Scenario: Outer-launcher NS retries create `mktemp .../larch-ns-retry-prompt.*` files tracked in `NS_RETRY_PROMPTS` and removed in bulk at `scripts/collect-agent-results.sh:1472`. The plan covers prepend/`preserve_and_publish_ns_retry` behavior but not unlinking those temp prompts after the NS-retry batch.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/collect_results.py:206-216
- **Phase**: design

### OOS_1:
- **Description**: LARCH_PLAN_REVIEW_COLLECT_SH stub is never read by production code. Scenario: The integration test exports a collect-agent-results.sh stub path that plan_review run does not consume; updating the stub name alone does not exercise collector behavior and may give false confidence about plan-review collection
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-design-multi-round-integration.sh:40-81
- **Phase**: design

