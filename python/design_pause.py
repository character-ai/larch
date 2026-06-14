"""Python CLI entrypoints for /design pause save/load."""

from __future__ import annotations

from collections.abc import Sequence

import design_legacy


def pause_save_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("scripts/design-pause-save.sh", argv)


def pause_load_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("scripts/design-pause-load.sh", argv)
