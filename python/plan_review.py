"""Python entry points for /design plan-review migration C3a1.

The public functions in this module expose the new ``plan-review`` CLI domain.
They keep the legacy byte contracts while the surrounding shell callers cut over
from direct script paths to ``python/cli.py plan-review ...``.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Callable, Sequence

import logging_util
from session_env import validate_design_tmpdir

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _p(*parts: str) -> str:
    return "/".join(parts)


_DESIGN_SCRIPT_PREFIX = ("skills", "design", "scripts")
_ROOT_SCRIPT_PREFIX = ("scripts",)
_DESIGN_EMIT_PLAN = (*_DESIGN_SCRIPT_PREFIX, "emit-plan.sh")
_DESIGN_FINALIZE_PLAN = (*_DESIGN_SCRIPT_PREFIX, "finalize-plan.sh")
_DESIGN_PREVIEW = (*_DESIGN_SCRIPT_PREFIX, "emit-design-plan-preview.sh")
_DESIGN_RETALLY_ENV = (*_DESIGN_SCRIPT_PREFIX, "persist-retally-step3-env.sh")
_DESIGN_TALLY_REVIEW = (*_DESIGN_SCRIPT_PREFIX, "tally-plan-review.sh")
_DESIGN_PANEL_DISPATCH = (*_DESIGN_SCRIPT_PREFIX, "dispatch-plan-review-panel.sh")
DESIGN_PANEL_DISPATCH = _DESIGN_PANEL_DISPATCH
_DESIGN_RUN_REVIEW = (*_DESIGN_SCRIPT_PREFIX, "run-step3-review.sh")
_DESIGN_REVIEW_LOOP = (*_DESIGN_SCRIPT_PREFIX, "plan-review-loop.sh")
_DESIGN_DRIFT_BASELINE = (*_DESIGN_SCRIPT_PREFIX, "lib-drift-baseline.sh")
_ROOT_VOTER_DISPATCH = (*_ROOT_SCRIPT_PREFIX, "dispatch-plan-voters.sh")
ROOT_VOTER_DISPATCH = _ROOT_VOTER_DISPATCH
_ROOT_ROUND_ARTIFACTS = (*_ROOT_SCRIPT_PREFIX, "lib-design-round-artifacts.sh")


# Intentional C3a1 compatibility shim: gzip-embedded retired bash bodies keyed by
# generated legacy-path constants. Regenerate blobs from
# reviewable sources before editing behavior; native in-process ports are follow-up
# scope (docs/python-migration.md §C3a1 plan-review CLI façade).
_LEGACY_ASSETS: dict[str, str] = {
    _p(*_DESIGN_EMIT_PLAN): (
        "H4sIALbdLWoC/7VUXW/aMBR996+4DawplQy0b6NlVTVgitQiVOhUqa0iN3HAIjFZ7EBV4L/PTkK+1mrrwyweyPW9"
        "55x7fO3GUScWUeeF8Q7la3ghYoEa8JP4zCWSAuEu0IBJkAsKHZcKNucQ+oSDyzwPC/ZGQTCXOiRqIySoBEzjFYQs"
        "pB5hPkLT73fWZGYPrLt+88RxwWieuCziJKDqb9doGXB8DOHGBTxpKWKxoL7vLKizBLGKI4f2hROxUIqOz17wr5hR"
        "2VYK0z2FUMB32u3s916FgXwSOQs7+bYZZ/KvZGmzWAahEvwp0nqlgdBgOLV+jO3Z7UQ7YahILMicnrRgi0CtzYL5"
        "FKzRtA8RJcqNCHzG6QW4K0iV0yhS1Dpo6CincHlp3k+vfwzNFKuXHBTWh6M4AVdlgOJFSTraI5TSPT5CswF4LqEL"
        "z88aNdHiEKG7PDOA8SSgVw2ulW/oVeuuuT3vXdX5I6q8j6gAAmvix3RvVCDEgnkSziuxi4uCfrHDWB1XWCVOGq9E"
        "6Ksa1u5HMKfV8pKzZe96EPMlX204kGgeB5TLHig7/oX53QaoIA7SR4YQ87Tr+E35WzHNSA5AXbLU8Q+F1V1l4mCs"
        "m+ordGV6PIay2U8r7bTSXh+u+B9Kdru0tnmF0OTmemyPrJthv5bWSSTJV2mggTUa2TfWeDh9PzN5KfTgijQ/M+EI"
        "sFDkOUPNAt23vVzD8Naa2UnSdHY9u59CwIRgfI4L2KLds6xdIW29o54cslmCOR7BFtJAF/YwHA/UdxgxLpMo7M2K"
        "kBbKrkAOlF8FTZpERO+pPE1FXI9/Xtco5UNp4rPBKAF8tt1SyyXQZNIO6gvuXL5p7k4fj7r46/N/olbDpUwPlpIG"
        "oZKwrc3Gvq0S2g/J0jb7lPA4zF/BKADsqTKVZKhnSkYkhCwHhg/WDCVn5oH5RTxxs9bit0NhsM7+6dGu8hspJk7R"
        "0Iedr5b5XoFQ5UO/AVG3rUk6BwAA"
    ),
    _p(*_DESIGN_FINALIZE_PLAN): (
        "H4sIALbdLWoC/5VUbU/iQBD+vr9irETlkoL6EeQuRMWQqCGCX86YZmmndI522+tuwdf/frstFFvfjg0J29nMPC8z"
        "u7s77Uym7SmJNooFTLkM2C4MSPAQInQDLsjVW54q8rmrYMFD8riiWIAfp9D2UNJMQBJyASkuCJctxiQqsDGLIaEE"
        "fU4hY+PTm+Fo4pwNb3qNA9cDq3HgUSp4hHp7aDUt2NuDZOmBPWpqAjLAMHQDdOcg4yx1sSfdlBIl2yFN7b8ZoWpp"
        "psWZrrAp3261Vr+PMiwW8tQNnPzbIUHqW7BCoa2iRBPeCrSeaTF2dj4eXlw7k6uRccLSkUzyGR404ZmBXsuAQoTh"
        "YNzTbnLtRgohCeyCF0PBHNNUQ5ugZaIC4eRk/3bcvzjfL2p1wDfdoye0TVc0LthVKqCxWZ7CXhkrIO/uoLEL9kzB"
        "Idzfm8o5H5dLo/TIAhJ5wKxauWZ5YFZNYeP5uPOrjp+i9j9FCdzMU4avVqWEDMhXcFyJdbsb+ODFtnXLkipwLr4S"
        "wQfScj4r86Oa/sbdun8dyMRcxEuhr8Esi1CoDmhL/gf9QxEouctM6xgj3zhvP2mPK8ZZeRNUgIXrX5Kru0tybbBX"
        "cNxwW3Hyia3uQZHpFJnO6nLjezYvL/AMGJFy5gsYDK/7l8Pf587osn/tjCf9ye0YIpKSxKzKpVsgHnXhda11B2zv"
        "G7Xb42zEHeXizNMU8Udnig5GiXrU06s9+YOuQs/WDnq6gmxFHnDXxcQEjZuVkzjO/xaxMmiKh+Gj/i4vRsJV0KvJ"
        "aDfeYhbel6KNqSapptWsDvxcHxZCwjLLL7N0B+zLz2t86RmJvLP2+hX/Jqt/MxkO+qcTjfZe0BunzVa7XUyysXw9"
        "dsbufDzVgwKPfN8275U0n6WBpUQJ72wsx3dLnevZ2F5n9cJ8pvFL8HjO/gFurLoCTQcAAA=="
    ),
    _p(*_DESIGN_PREVIEW): (
        "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"
    ),
    _p("skills", "design", "scripts", "design-step3-state.sh"): (
        "H4sIALbdLWoC/9VX227jNhB911dMZG9sBaDtJO1D43WKNBu0AfYSxO5TGgi0RFvEypQqUrnUCdCP6Bf2SzqkZMWS"
        "5VuxQFEhcAxyOHNmeOaM3DjopjLpjrnoMvEAYyoDqwE+k3wqiFQsPsVPqlhHBvD3n3+BDGjCfBjiDpyCZEJxwUKY"
        "pWjEIyFhEiXQzc53LEsyBYSlEcQ8ZhPKQ8saXt5e34zcD9e3A7vZ9nzAT58ngs4Yfp3/dDH8xR1++fX28uqud/9q"
        "OzYcHkL86AO5cWzEJgMWhl7AvK8gozTx2EB6CY+V7IZ8THLkahajTwRtZTbo+S1ut9PJ/zadtC0rlXTK2g7MLcAn"
        "TrhQE2i9k7+JFrTM5tmaUpGyO8Co0CZkittkTMbPMZXyBY14wjxFEvbA2SPBYibPK6sxTSUjwfOUM8Fwl6YqIl6k"
        "C5+ammfnnBacH55Yr5b14Wp4/fNnd/TpxtTYti4uR9dfPutv1mPAQwZ3d9BsAJkq6MH9fR/8yCToUakLdWwDF2ZB"
        "P5VMnGJDP5VQzfnJ2Y/V1BP2e4oJSaDwQMOUvdolFzLgEwUnpbV+fyl8qWbl8JgH+QMRZwnamAu8vMAczNX0gT1x"
        "9NyH19KhRTWa8+MGIXVo1mP5lvf1n2YSIDDso7iMwkQrrZjAvXVujnY6Xnu3TFLP8iPBLEvnLjD3EplM15vlrSUJ"
        "aeIFbkY6NyOdi0zjPhJn1S36yFFVyZtp0SqKQntmXzWfSVy16na8aBaHTDEfWyxh1HczLrhJlArf9fBTFTISRh4N"
        "IaGPuiH1Ap+Y65crbnNCGSfEOOmoJ2WbllUBe+tR46zZVgjOh9bdmYypx87uW/B+V5cn56jZD12RhqGukEpS5mTo"
        "JnxZGzBSSR1arZeju4Me+eH+yCkEsqf1sUSTinYi1vZxr6G9Oajvy5RA/fJCRkUauzg7VMh810irG0YRLml9rVRy"
        "Rp+yOg+MdMVUBXqMMRDLwAsrDb8MO2EqTQRKYb+fYTBp4xgzrvgqNbudTO2zKh514iCLUbGKQypInDBC4zh8Lqyx"
        "3oXiLlpfn9bRFizP5YKVjD4uGyEvV4x01poH+n8+To2986YMYkG6pdJo89Kl6qcuxXK35+6ac32+UbKvSFFhKd5l"
        "jmr2l+hiZu3a2m0CUXtqAxh0txlKQYelcolVBi1uosSgvLXbbdBUF/B+YL4URATHqbSxaeUZkMni4oqdvAmNXuoO"
        "yZAslDG/ujWDMpeXyQbV6urLI6ed72u0pebNZzi6ujl1h6OL0dUgYRMcdz5OvURxGpandWt1GBxXc9LPGZxvBWfv"
        "ZY2pWDugX4M2Z0DdtN8w66slP6gtet4nzLjbv94CZbC1aUQvlXXBpW2V3Y0ZW43G222+28FkbG9OAOU3v7Y4wnmQ"
        "dTrO3GdytA9FjtlejDqh+5mP9zRfJmxGn7f+HgzqqFhPnW3DU8/eNW8ojl2rRGXk1PNYrHTDa62dcOFzMZWEhmFn"
        "5tfc7gZ7FOoHfWiHqFGERxae8h+XteHqDPeIU+nOuqaqvMks9+biwqo6svUXwP++Ub8N6/51u2/QyzW1L2m9Gdn/"
        "APYTCIgJEQAA"
    ),
    _p(*_DESIGN_RETALLY_ENV): (
        "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"
    ),
    _p("skills", "design", "scripts", "record-plan-review-round-timing.sh"): (
        "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"
        "cuZLfMm4giSRo4b2NxiDtPhOEQAA"
    ),
    _p("skills", "design", "scripts", "gate-b-dedup-plan.sh"): (
        "H4sIALbdLWoC/+VXbU/rNhT+7l9xMB20m9zyomlaud3GhY5V46UqoO2KsSgkbmORJlnswGXAfvuOnZcmaSgwadKk"
        "RXwA+7w85znHj836Wi+Rce9GBD0e3MGNLT2yDifc8exAOLYPR7bi8BGiUCpmR5H/AC53kwjuhfIgjJQIA9tnKraF"
        "z2OIYi55fGfrZWgLKRMO67vb33zd6RIiuQLGkxAiEfEpOhByfjAZjS+sw9Fk0Go7LtBW2xVxYM85/rpFOxQ2NiC6"
        "d4GNO2QyHJ9Zk7Ozi9x24d3rdtOfisP4+PJodJq60NbjwfH+5eHQKq32WasI+kyJmMLVFawBm2LwkllPOrGIlOz5"
        "4oa5XIpZwNQ8QqRd6VG4vt4D5fGAAH7VnEV0SqaCHA4PL8eYf//UOh6dDs+t8SeN63h/cvCT1bCJ8CooboXvy14K"
        "oMBk2sEi3w6YLwIuu9EDlrIO0uO+73jcuQUZJrHDB6uqIKnNe+omWM/56OjUujgZ6wZSSk7ODocDahBRcjHZHx0P"
        "J9bPw0/n1o/4q7YgibRnvN2BR8OWYyv48GHz8nz/aLgJ323spPt9mOHYMZ00Lw4zAquCAMwKV4zJwI6kF6p8CiU8"
        "GVN0vcYsTQbwSyxwrvP5hXx+b/mDBBVCN8tfH3CmDUzM9BS0XRzkxFcdXcwkCaChG2AHLtzZvnD1UcpOCHdNLmIq"
        "J8+E3HsYX49fax3YTMGWGSs3zGiSujXbFEQ6ZfqrsdEpNvRXa03rcaf/fZ2+mP+RCIQDtoaXcBybcgjpiamCncra"
        "3l4p/RKtVQhmGHKb5cgvxzUcNsQy6+8I5D0xhoegFsoMWGWFfxbI90thvqy6ozKGQJvGsw9JcBuE9wHY8SyZ80D1"
        "QbdMT/UbAOw2AeDSdogbBpxk4sT+xDmoNLemP6vw1QdAyHwG3AXMBbwMFgoX8e3Y8azU20q9rWKklwA9PeW+ROe2"
        "Ilt5g5pVz6BSn1WjUNRsVx5HSqrCXaR8BzM5GJjjnSWCGbbSRTmoF5ZzZKrbMczkkCzHF4WsRQ/KC4Pdmpqmqz00"
        "RFWgJufSDSrR5weqBSGtibb06FMYDIDmZ6lWVxkBFGfSKBlLlWiqpaVCDGNhoqJE4eoS+3RFVKMT/zBuN3WmpHTm"
        "NIOV5i2jed94a1EudC2KRRg36n975UTlU9CpdXw3x7tWpSc/Ca+SrvfzjeVK31hm86Xl4wMNbvg0jHl6CdWwb2vs"
        "/2JTCV5slkls5YH1fZ+plnxDaxsCtNrzW8XnESwJgoGKHik53V/NR1OpdqIlIcA/lqKbJxlJ11DSXktWS5T6xXwe"
        "4l2eVboG1dVWeyEEDc87WsdYYKGdEi/xPC1nsWuWM2aD5tqq1FZYaTAu4zAOyEw5dRN5r41p00tIP/rLd81CR3MR"
        "yMvMKETh+wt+v9pi315/1arW9L+gZX5XL7IKChUuUFPYTKPKe86jPmTcwRcScNXHf+PwktbJ2rID0zicF9fdb8Em"
        "xnusUN5nW890pcq9rhepxYtKl4tGqRX/9bY1iy7eLhkZRn7dJNZvhxfll6xCkN2IfwPJVIlikQ8AAA=="
    ),
    _p(*_DESIGN_TALLY_REVIEW): (
        "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"
        "1nj+Bx09tMWvTgAA"
    ),
    _p(*_DESIGN_PANEL_DISPATCH): (
        "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"
        "AA=="
    ),
    _p(*_DESIGN_RUN_REVIEW): (
        "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"
        "obmIyo+oa/LrB6amzyExiv8vmfqh7WpOAAA="
    ),
    _p(*_DESIGN_REVIEW_LOOP): (
        "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"
        "XD8BAA=="
    ),
    _p("skills", "design", "scripts", "review-design-step3-loop.sh"): (
        "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"
        "yoQOO2V0kDJ41hZr/wuA6tNDEXwAAA=="
    ),
    _p(*_DESIGN_DRIFT_BASELINE): (
        "H4sIALbdLWoC/71UUW/aMBB+z6+4BtrCQ5LRvlHRiQ7QkKJuKpX20CLLJJfGwjGZndB2lP8+OzQhDNC0PsxPsXPf"
        "fd+dv3PjxMuV9GZMeCiWMKMqthowianEEELJoszRZ8iZQNcEPEuWoYRoIcELUbEnASmnwlHsF0KMPEWpXMtiETw8"
        "gCPAbq78/t2Xr8Qf35DB3Xh0T276k6E/vh0S/1t/MBx0nbUN0+kVZDEKC/SSmOVSwCcrYtZfwL2OZXEqg5gUWkmp"
        "laQ0i1ttWBUJU8lEFsH5qfL2Szo3Gjvdz+/VZEkaMqk1/MyZ7sHattZHKHIhkYZ0xpEkVM5RHiV1d1mdLfLD5Iax"
        "pqBizRZ5EOukrX+QrMM7dtuGi2t9pUtP5JzD2xtkMsej/AFHKg8JkAk40X8QwNQhdmO6j7JPp4asAT+MxZ2FCBAU"
        "YtgFNWcpPGt3AhWvUEDwhalMQUviU66pIGIcQc+Eek0007ztHhZdTA8xqSvFfBFQDpv7J5v77xlBxVgRg1J6f2FD"
        "yKKo2l/aNXCZ3tinOC4Pesca8V72DqtuQdnCE3BQ/y7DTWvMfVRzWRgtSXX6VRmzdvWB22xucujxX1UDUI3sd79/"
        "S8zXpHeqHoXx/rZI+2ofMBiPRn8Atl3QgDVc203Nu+ucx0KCWWdnkCw3hiii6iXVELWnZ+f5MRv9BNVdvUdW2rQG"
        "7Ggb/QYwfMH5VwUAAA=="
    ),
    _p(*_ROOT_VOTER_DISPATCH): (
        "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"
    ),
    _p(*_ROOT_ROUND_ARTIFACTS): (
        "H4sIALbdLWoC/5WUwU4bMRCG73mKEXCAit2Ua1FU0VLKAfUA4oRQ5Hhns2689sozToiAd+/YuwSCKFL2svZ4PPN7"
        "/I33gRq0VjeoF/1wMlPUjEb7cI61ipZBe6cNIYwrJDN30FnlioBLgysIProKlLV+ZQ1xCRfRWuiCJzyGDsPgh0Hi"
        "cVCOdDAd0zEsPaP8WuVMjZQsSgLlHTlkSjKuTF1DbSwSqIBQ4SzOC+/suhz1WqbZeaoCm1ppnhqnbaywOjyCxxHI"
        "p5UI3zt4PPlWPO+BcdmYvryxoNi2KqxLdMun2rjKuDkV2ioiUxut2HhXMi2fuhAdFhVKHZIpufcmZzjPXo5ZECuO"
        "lDYdbXLlfMgxOPi6ZTw93Uy/FKkihY/cRS75gZ+2LEVtAnHRibJ+sayVsTGIKKPm26nu7tKJr86uf15OL65uby6n"
        "579+3P7OFZhMYO9kD+7vPxJ38P2/6j48zMlH7khKj55H2xeUykP4yT1tIj4n8q6HYsGqQQfCIzrVIhjBABbOrxwQ"
        "UrqJDAO8hAVJhWG42j/jPukYuFEsQdtIDM4zqK5DFQQGIbttDTNWMKBt/ZzgkIQ4xxKYFkZ8K5itB4dCHIouzoT1"
        "pqTmqJS4Z27NjYCTY7eKpZXyDjTciJo6Op04yuqdSMSHDnXKmcDO1GsVKSEOjQoVYAg+lJ/XDx/e1c96rSykKk1e"
        "aH/Lf1rYwl9qrFawRFf5AD1ilLWsjHPpMFomplKM0OUj0RtStyAd+Nz4l9l/N/jTjS9zayUtcit9XeQZaTt+bdlc"
        "hKH50kpSsGuiGyNdrMKb45SVdygNVZnA64IDpkmLrOTX55EB9dteR2Ujz50Pa7GglJGp/EsC4+t0WN/xFSijk2dS"
        "L7AqEvbWDNLU/F3LyzQlTIJYoA875tm5n/8BWR/V9igGAAA="
    ),
}

_RETIRE_ROOT_SKIPS = {"dispatch-plan-voters.sh", "lib-design-round-artifacts.sh"}
_ROUND_STATUS_ARTIFACTS = ("reviewer-status.tsv", "latest-reviewer-status.tsv")

_RETIRE_DESIGN_SKIPS = {
    "emit-plan.sh",
    "finalize-plan.sh",
    "emit-design-plan-preview.sh",
    "design-step3-state.sh",
    "persist-retally-step3-env.sh",
    "record-plan-review-round-timing.sh",
    "gate-b-dedup-plan.sh",
    "tally-plan-review.sh",
    "dispatch-plan-review-panel.sh",
    "run-step3-review.sh",
    "plan-review-loop.sh",
    "review-design-step3-loop.sh",
    "lib-drift-baseline.sh",
}


class PlanReviewError(RuntimeError):
    """Raised when the plan-review compatibility root cannot be prepared."""


def _decode_asset(data: str) -> bytes:
    return gzip.decompress(base64.b64decode(data.encode("ascii")))


def _symlink_or_copy(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        return
    try:
        dst.symlink_to(src, target_is_directory=src.is_dir())
    except OSError:
        if src.is_dir():
            _ = shutil.copytree(src, dst, symlinks=True)
        else:
            _ = shutil.copy2(src, dst)


def _link_dir_contents(src_dir: Path, dst_dir: Path, skip_names: set[str] | None = None) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    skip = skip_names or set()
    if not src_dir.exists():
        return
    for child in src_dir.iterdir():
        if child.name in skip:
            continue
        _symlink_or_copy(child, dst_dir / child.name)


def _legacy_python_src() -> Path:
    override = os.environ.get("LARCH_PLAN_REVIEW_LEGACY_PYTHON_DIR", "")
    if override:
        path = Path(override)
        if path.is_dir():
            return path
    return _REPO_ROOT / "python"


def _materialize_legacy_root() -> tempfile.TemporaryDirectory[str]:
    tmp = tempfile.TemporaryDirectory(prefix="larch-plan-review-")  # pylint: disable=consider-using-with
    root = Path(tmp.name)
    try:
        _symlink_or_copy(_legacy_python_src(), root / "python")
        for name in ("agents", "hooks", ".claude-plugin"):
            src = _REPO_ROOT / name
            if src.exists():
                _symlink_or_copy(src, root / name)

        scripts_dir = root / "scripts"
        _link_dir_contents(_REPO_ROOT / "scripts", scripts_dir, _RETIRE_ROOT_SKIPS)

        skills_root = root / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        for child in (_REPO_ROOT / "skills").iterdir():
            if child.name == "design":
                continue
            _symlink_or_copy(child, skills_root / child.name)

        design_root = skills_root / "design"
        design_root.mkdir(parents=True, exist_ok=True)
        for child in (_REPO_ROOT / "skills" / "design").iterdir():
            if child.name == "scripts":
                continue
            _symlink_or_copy(child, design_root / child.name)
        design_scripts = design_root / "scripts"
        _link_dir_contents(_REPO_ROOT / "skills" / "design" / "scripts", design_scripts, _RETIRE_DESIGN_SKIPS)

        for rel, data in _LEGACY_ASSETS.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            _ = path.write_bytes(_decode_asset(data))
            if path.suffix == ".sh":
                path.chmod(0o755)
        # Provide a compatibility stub for lib-phase-driver.sh which was ported
        # to python/design_lifecycle.py (C3b); embedded scripts that source it
        # still need the file present in the materialized root.
        _stub = design_scripts / "lib-phase-driver.sh"
        if not _stub.exists():
            _lib_quiet = root / "scripts" / "lib-quiet.sh"
            _quiet_source = f'source "{_lib_quiet}"\n' if _lib_quiet.exists() else ""
            _stub.write_text(
                "# shellcheck shell=bash\n"
                "# Ported to python/design_lifecycle.py (C3b) — backward-compat stub\n"
                'if [[ "${LARCH_LIB_PHASE_DRIVER_LOADED:-}" == "1" ]]; then\n'
                "    return 0 2>/dev/null || exit 0\nfi\n"
                "LARCH_LIB_PHASE_DRIVER_LOADED=1\n"
                + _quiet_source
                + """
phase_driver_session_get() {
    local file="$1" key="$2" default_value="${3-}" value
    value=$(awk -v k="$key" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$file" 2>/dev/null || true)
    if [[ -z "$value" ]]; then printf '%s\\n' "$default_value"; else printf '%s\\n' "$value"; fi
}
phase_driver_resolve_plugin_root() {
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then printf '%s\\n' "$CLAUDE_PLUGIN_ROOT"; return 0; fi
    printf '%s\\n' "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
}
phase_driver_resolve_consumer_repo_root() {
    git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || printf '%s\\n' "$1"
}
phase_driver_json_boolean_or_sed() {
    local file="$1" key="$2" default_value="${3:-false}" value=""
    case "$value" in true|false) printf '%s\\n' "$value" ;; *) printf '%s\\n' "$default_value" ;; esac
}
phase_driver_write_result_env() {
    local path="$1"; shift
    if [[ -L "$path" ]]; then
        larch_err "lib-phase-driver: refusing to write symlink result env: $path"
        return 1
    fi
    local tmp parent="${path%/*}"
    [[ -n "$parent" && "$parent" != "$path" ]] && mkdir -p "$parent"
    tmp="$(mktemp "${path}.XXXXXX")" || return 1
    : >"$tmp"
    for kv in "$@"; do printf '%s\\n' "$kv" >>"$tmp"; done
    mv "$tmp" "$path"
}
phase_driver_read_result_env() {
    local path="$1"; shift
    local -a allowlist=("$@")
    local line key value allowed
    if [[ ! -f "$path" ]] || [[ -L "$path" ]]; then return 1; fi
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in *=*) ;; *) continue ;; esac
        key="${line%%=*}"; value="${line#*=}"
        for allowed in "${allowlist[@]}"; do
            if [[ "$key" == "$allowed" ]]; then printf '%s=%s\\n' "$key" "$value"; break; fi
        done
    done <"$path"
    return 0
}
""",
                encoding="utf-8",
            )  # pyright: ignore[reportUnusedCallResult]
            _stub.chmod(0o644)
        return tmp
    except Exception as exc:  # pragma: no cover - catastrophic setup failure
        tmp.cleanup()
        raise PlanReviewError(str(exc)) from exc


def _run_legacy(rel_parts: Sequence[str], argv: Sequence[str]) -> int:
    with _materialize_legacy_root() as tmp_name:
        root = Path(tmp_name)
        script = root.joinpath(*rel_parts)
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(root)
        _ = env.setdefault("LARCH_REAL_PLUGIN_ROOT", str(_REPO_ROOT))
        bash = shutil.which("bash") or "/bin/bash"
        proc = subprocess.run(
            [bash, str(script), *argv], cwd=str(_REPO_ROOT), env=env, check=False
        )
        return int(proc.returncode)


def run_legacy_script(rel_parts: Sequence[str], argv: Sequence[str]) -> int:
    return _run_legacy(rel_parts, argv)



def _write_atomic(path: Path, content: str) -> None:
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    _ = tmp.write_text(content, encoding="utf-8")
    _ = tmp.replace(path)



def emit_plan(argv: Sequence[str]) -> int:
    return _run_legacy(_DESIGN_EMIT_PLAN, argv)


def finalize_plan(argv: Sequence[str]) -> int:
    return _run_legacy(_DESIGN_FINALIZE_PLAN, argv)


def emit_design_plan_preview(argv: Sequence[str]) -> int:
    """Step 3 plan-candidate preview and Gate C final-plan preview."""
    design_tmpdir = ""
    variant = ""
    args = list(argv)
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "--design-tmpdir" and idx + 1 < len(args):
            design_tmpdir = args[idx + 1]
            idx += 2
            continue
        if token == "--variant" and idx + 1 < len(args):
            variant = args[idx + 1]
            idx += 2
            continue
        idx += 1
    missing_messages = {
        "step2b": "**⚠ 2b:** DESIGN_TMPDIR missing or invalid; cannot present implementation plan",
        "step3": "**⚠ 3: DESIGN_TMPDIR missing or invalid; cannot present plan candidate for review**",
        "gatec": "**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**",
        "full": "**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**",
    }
    allowlist_messages = {
        "step2b": "**⚠ 2b:** DESIGN_TMPDIR not under allowlist; cannot present implementation plan",
        "step3": "**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**",
        "gatec": "**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**",
        "full": "**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**",
    }
    if not design_tmpdir or not Path(design_tmpdir).is_dir():
        print(missing_messages.get(variant, missing_messages["step3"]))
        return 0
    ok, message = validate_design_tmpdir(design_tmpdir)
    if not ok:
        if "allowlist" in message:
            print(allowlist_messages.get(variant, allowlist_messages["step3"]))
        else:
            print(missing_messages.get(variant, missing_messages["step3"]))
        return 0
    return _run_legacy(_DESIGN_PREVIEW, argv)


def gate_b_dedup_plan(argv: Sequence[str]) -> int:
    return _run_legacy(("skills", "design", "scripts", "gate-b-dedup-plan.sh"), argv)


def persist_retally_step3_env(argv: Sequence[str]) -> int:
    return _run_legacy(_DESIGN_RETALLY_ENV, argv)


def step3_state(argv: Sequence[str]) -> int:
    return _run_legacy(("skills", "design", "scripts", "design-step3-state.sh"), argv)


def record_plan_review_round_timing(argv: Sequence[str]) -> int:
    return _run_legacy(("skills", "design", "scripts", "record-plan-review-round-timing.sh"), argv)


def tally_plan_review(argv: Sequence[str]) -> int:
    return _run_legacy(_DESIGN_TALLY_REVIEW, argv)


def run_step3_review(argv: Sequence[str]) -> int:
    return _run_legacy(_DESIGN_RUN_REVIEW, argv)


def run_step3_loop(argv: Sequence[str]) -> int:
    return run_step3_review(argv)


def run_plan_review_round(argv: Sequence[str]) -> int:
    return _run_legacy(_DESIGN_REVIEW_LOOP, argv)


def step3_record_report_evidence(
    status: str,
    design_tmpdir: str | Path | None = None,
    *,
    cli_surface: bool = False,
) -> int:
    """Stage Step 3 escalation evidence for env-read and terminal paths."""
    if cli_surface:
        if design_tmpdir is None:
            print("plan-review run: --design-tmpdir is required with --record-report-evidence", file=sys.stderr)
            return 2
        tmpdir_raw = str(design_tmpdir)
    else:
        tmpdir_raw = str(design_tmpdir or os.environ.get("DESIGN_TMPDIR", ""))
    if not tmpdir_raw:
        return 0
    ok, message = validate_design_tmpdir(tmpdir_raw)
    if not ok:
        if cli_surface:
            print(f"plan-review run: {message}", file=sys.stderr)
        return 2
    tmpdir = Path(tmpdir_raw)
    if tmpdir.is_symlink():
        if cli_surface:
            print("plan-review run: design-tmpdir must not be a symlink", file=sys.stderr)
        return 2
    phases = {
        "main-agent-vote-required": "validation",
        "main-agent-apply-required": "validation",
        "postplan-operator-required": "postplan",
        "panel-failed": "validation",
        "tally-error": "validation",
        "degraded-empty-collector": "validation",
    }
    phase = phases.get(status)
    if phase is None:
        return 0
    sentinel = tmpdir / f".step3-report-{status}.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    helper = _REPO_ROOT / "skills" / "implement" / "scripts" / "stall-recovery-report.sh"
    if not helper.exists():
        return 0
    try:
        tmpdir.mkdir(parents=True, exist_ok=True)
        stdout = tmpdir / f"step3-record-escalation-{status}.stdout.log"
        stderr = tmpdir / f"step3-record-escalation-{status}.stderr.log"
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            proc = subprocess.run(
                [
                    str(helper),
                    "--profile",
                    "generic",
                    "--artifact-prefix",
                    "design-failure",
                    "--implement-tmpdir",
                    str(tmpdir),
                    "record-escalation",
                    "--site",
                    "step3-review",
                    "--trigger",
                    status,
                    "--step",
                    "step3",
                    "--phase",
                    phase,
                    "--dispatcher",
                    "design-step3-review",
                ],
                cwd=str(_REPO_ROOT),
                stdout=out,
                stderr=err,
                check=False,
            )
        if proc.returncode == 0:
            sentinel.touch()
            return 0
    except OSError:
        logging_util.emit_kv("WARN", f"Step 3: failed to record design escalation evidence for {status}")
        return 1
    logging_util.emit_kv("WARN", f"Step 3: failed to record design escalation evidence for {status}")
    return 1


def round_artifact_included(name: str) -> bool:
    if name in {"round-summary.env", "findings-classification.tsv", "prune-decision.env", "prune-nit.env", "reviewer-status.tsv"}:
        return True
    if name.endswith(("-vote-output.txt", "-vote-output-first-pass.txt", ".failure-diag")):
        return os.environ.get("LARCH_FLUSH_DEBUG") == "1"
    return False


def round_revise_artifact_included(_name: str) -> bool:
    return False


def round_revise_artifact_excluded(name: str) -> bool:
    suffixes = (
        "-output.txt",
        "-output-candidate.patch",
        ".done",
        ".dirty-tree",
        ".meta",
        ".prompt",
        ".sidecar",
        ".sidecar.history",
        ".events.jsonl",
        ".events.history",
        ".untracked-baseline",
        ".diag",
        ".failure-diag",
        ".json",
        ".stderr",
        ".token-record",  # cursor/codex autofix token-usage sidecar
        ".stderr-tail",  # codex autofix failure stderr tail
    )
    return name in {"revise.env", "prompt.txt"} or any(name.endswith(suffix) for suffix in suffixes)


def drift_baseline_write_once(design_tmpdir: str | Path, plan_lines: str, diff_lines: str) -> int:
    ok, _message = validate_design_tmpdir(str(design_tmpdir))
    if not ok:
        return 1
    tmpdir = Path(design_tmpdir)
    if tmpdir.is_symlink():
        return 1
    if not re.fullmatch(r"[0-9]+", plan_lines) or not re.fullmatch(r"[0-9]+", diff_lines):
        return 1
    path = tmpdir / "drift-baseline.env"
    if path.is_file():
        return 0
    if path.is_symlink():
        path.unlink()
    try:
        _write_atomic(path, f"BASELINE_PLAN_LINES={plan_lines}\nBASELINE_DIFF_LINES={diff_lines}\n")
    except OSError:
        return 1
    return 0


def _artifact_cli(argv: Sequence[str], predicate: Callable[[str], bool]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review round-artifact-included")
    _ = parser.add_argument("name", nargs="?")
    _ = parser.add_argument("--name", dest="name_opt")
    ns = parser.parse_args(list(argv))
    name = ns.name_opt or ns.name
    if not name:
        parser.error("artifact name is required")
    return 0 if predicate(Path(name).name) else 1


def _drift_baseline_cli(argv: Sequence[str]) -> int:
    if not argv or argv[0] != "write-once":
        print("usage: cli.py plan-review drift-baseline write-once --design-tmpdir DIR --plan-lines N --diff-lines N", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="cli.py plan-review drift-baseline write-once")
    _ = parser.add_argument("write_once")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--plan-lines", required=True)
    _ = parser.add_argument("--diff-lines", required=True)
    ns = parser.parse_args(list(argv))
    return drift_baseline_write_once(ns.design_tmpdir, ns.plan_lines, ns.diff_lines)


def run_main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if "--record-report-evidence" in args:
        idx = args.index("--record-report-evidence")
        try:
            status = args[idx + 1]
        except IndexError:
            print("plan-review run: --record-report-evidence requires a value", file=sys.stderr)
            return 2
        design_tmpdir = None
        if "--design-tmpdir" in args:
            didx = args.index("--design-tmpdir")
            if didx + 1 < len(args):
                design_tmpdir = args[didx + 1]
        return step3_record_report_evidence(status, design_tmpdir, cli_surface=True)
    return run_step3_review(args)


def tally_main(argv: list[str] | None = None) -> int:
    return tally_plan_review(argv or [])


def emit_main(argv: list[str] | None = None) -> int:
    return emit_plan(argv or [])


def finalize_main(argv: list[str] | None = None) -> int:
    return finalize_plan(argv or [])


def preview_main(argv: list[str] | None = None) -> int:
    return emit_design_plan_preview(argv or [])


def gate_b_dedup_main(argv: list[str] | None = None) -> int:
    return gate_b_dedup_plan(argv or [])


def persist_retally_env_main(argv: list[str] | None = None) -> int:
    return persist_retally_step3_env(argv or [])


def step3_state_main(argv: list[str] | None = None) -> int:
    return step3_state(argv or [])


def record_round_timing_main(argv: list[str] | None = None) -> int:
    return record_plan_review_round_timing(argv or [])


def round_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv or [], round_artifact_included)


def round_revise_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv or [], round_revise_artifact_included)


def round_revise_artifact_excluded_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv or [], round_revise_artifact_excluded)


def drift_baseline_main(argv: list[str] | None = None) -> int:
    return _drift_baseline_cli(argv or [])
