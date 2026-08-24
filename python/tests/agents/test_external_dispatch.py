# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from larch.core import config, external_defaults


def test_debate_roles_do_not_alter_existing_panels() -> None:
    review_slots = external_defaults.slot_defaults("review.panel")
    assert all(slot.slot in {"correctness", "edge-cases", "testing"} for slot in review_slots)
    assert "debate.panel" in config.ROLE_DEFAULTS
    assert "debate.synthesizer" in config.ROLE_DEFAULTS
    # Existing panels remain unchanged in size/shape after debate registration.
    assert len(review_slots) == 6
    assert external_defaults.tool_order("implement.step2_coder") == ("codex", "cursor", "claude")
