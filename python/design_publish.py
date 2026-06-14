"""Python CLI entrypoint for /design publish."""

from __future__ import annotations

from collections.abc import Sequence

import design_legacy


def publish_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("skills/design/scripts/design-publish.sh", argv)
