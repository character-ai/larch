### NS-retry temp prompt cleanup omitted in Python collector port

**Surfaced by**: Cursor-Innovation
**Phase**: design
**Vote tally**: 2 YES / 0 NO (accepted)

## Description

NS-retry temp prompt cleanup omitted. Outer-launcher NS retries create `mktemp .../larch-ns-retry-prompt.*` files tracked in `NS_RETRY_PROMPTS` and removed in bulk at `scripts/collect-agent-results.sh:1472`. The plan covers prepend/`preserve_and_publish_ns_retry` behavior but not unlinking those temp prompts after the NS-retry batch. The port to `python/collect_results.py` must include equivalent cleanup of the NS-retry prompt temp files after the NS-retry batch settles.

- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/collect_results.py (NS-retry batch settle)
