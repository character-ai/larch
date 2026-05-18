## Goal
Extend prefix_records() and content_to_text() to include tool_result/tool_use/attachment content blocks in stable-prefix fingerprinting

## Implementation Plan

### Goal
Fix false-negative EXPECTED-GROWTH classifications in `scripts/cache-key-runtime-audit.py` by including prompt-bearing attachment content blocks in the stable-prefix set. Currently, user entries containing `tool_result`, `tool_use`, or non-text content subtypes (image, document, file) are excluded from prefix fingerprinting, causing cache-invalidating attachment mutations to be silently misclassified.

### Files to Modify
1. `scripts/cache-key-runtime-audit.py` — core logic
2. `scripts/test-cache-key-runtime-audit.sh` — regression fixtures
3. `scripts/cache-key-runtime-audit.md` — update invariants doc
4. `scripts/test-cache-key-runtime-audit.md` — note new test cases

### Changes

#### 1. `content_to_text()` (lines 108–119)
Add explicit handling for `tool_result` and `tool_use` content blocks. Currently the function recurses into the "content" key, losing structural metadata (especially `tool_use_id`). New behavior: serialize these blocks as full JSON to preserve all fields.

Before (in the `isinstance(item, dict)` branch):
```python
if "text" in item and isinstance(item["text"], str):
    parts.append(item["text"])
elif "content" in item:
    parts.append(content_to_text(item["content"]))
else:
    parts.append(json.dumps(item, sort_keys=True, ensure_ascii=False))
```

After:
```python
block_type = str(item.get("type") or "")
if "text" in item and isinstance(item["text"], str):
    parts.append(item["text"])
elif block_type in ("tool_result", "tool_use"):
    parts.append(json.dumps(item, sort_keys=True, ensure_ascii=False))
elif "content" in item:
    parts.append(content_to_text(item["content"]))
else:
    parts.append(json.dumps(item, sort_keys=True, ensure_ascii=False))
```

Side effect: `is_initial_user_message()`'s check `"tool_use_id" in content` now correctly fires for entries with tool_result blocks, since the full JSON includes "tool_use_id".

#### 2. New helper `_is_attachment_bearing()` (after `is_initial_user_message`)
Returns True if any content block in the entry has a type other than "text" (i.e., tool_result, tool_use, image, document, file, etc.).

```python
def _is_attachment_bearing(entry: TranscriptEntry) -> bool:
    raw = entry.raw
    message = raw.get("message")
    content = (
        message.get("content") if isinstance(message, dict)
        else raw.get("content")
    )
    if not isinstance(content, list):
        return False
    for block in content:
        if isinstance(block, dict) and str(block.get("type") or "") not in ("", "text"):
            return True
    return False
```

#### 3. `prefix_records()` — new elif branch
Add before `is_initial_user_message` check:
```python
elif entry.entry_type == "user" and _is_attachment_bearing(entry):
    include = True
    reason = "user:attachment"
```

This captures:
- User entries with `tool_result` blocks (tool output context)
- User entries with `tool_use` blocks (unusual but possible)
- User entries with image/document/file blocks (direct attachments)

#### 4. Test fixtures (new, in `test-cache-key-runtime-audit.sh`)
Add `write_tool_result_mutation_fixture()`:
- Turn 1: user message with `tool_result` containing text "result-A"
- Turn 2: user message with `tool_result` containing text "result-B"
- Expected: BASELINE → CACHE-INVALIDATING

Add `write_image_mutation_fixture()`:
- Turn 1: user message with image block (url img1.png)
- Turn 2: user message with different image block (url img2.png)
- Expected: BASELINE → CACHE-INVALIDATING

Add `write_attachment_stable_fixture()`:
- Two turns with SAME tool_result content
- Expected: BASELINE → EXPECTED-GROWTH

### Testing Strategy
Run `make test-cache-key-runtime-audit` (invokes `scripts/test-cache-key-runtime-audit.sh`) after changes. The harness is self-contained and runs without external dependencies.

### Edge Cases
- `included_initial` guard: The new `user:attachment` path does NOT set `included_initial`, so a plain text initial message (if present before any attachment entry) is still captured separately.
- Chain ordering: attachment entries later in the chain (after the initial message) ARE included, fixing the multi-turn case.
- Empty content: `_is_attachment_bearing()` returns False for string content, None content, or empty lists — no regression on simple fixtures.

## Test plan
(no test plan section in plan-file)
