"""Python CLI entrypoint for committed /design run-log publishing."""

from __future__ import annotations

from collections.abc import Sequence

import design_legacy


def log_publish_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("scripts/design-log-publish.sh", argv)
