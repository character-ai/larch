"""Python entry points for /design plan-review migration C3a1.

The public functions in this module expose the new ``plan-review`` CLI domain.
They keep the legacy byte contracts while the surrounding shell callers cut over
from direct script paths to ``python/cli.py plan-review ...``.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
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
import plan_review_tally
import stall_recovery
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
        "H4sIAAAAAAACE7VU0W7aMBR991fcpqyUSgbaPY2WVdWAKlKLUKFTpbaK3MQhFonJYgfaAv8+26EJyYq0PcziIVzfe865x9c+PGil"
        "Imm9MN6ifAEvRAToEH6SkHlEUiDcAxoxCTKg0PKoYFMOcUg4eMz3sWDvFATzqEuSJkKCSsA0nUPMYuoTFiI0/nFnjyZOz77r1o5d"
        "D6zasccSTiKqPttWw4KjI4iXHuBRQxGLgIahG1B3BmKeJi7tCjdhsRStkL3gXymjsqkUZnsKoYBvNZvb32cVFkK9/ti+HjqT25EW"
        "Y6lIKsiUHjdghUCtZcBCCvZg3IWEEiUogZBxeg7eHEKSuIFDk0RR6qClo5zCxUX9fnx13a9nWB3jFdb+KE7AODMMyyhWTYPiRSYd"
        "bRDK6B4foXYIeCqhDc/PGtVocYnQ3Z1awLgJ6FWBa+QbelW6q63OOpdV/oQqOxIqgMCChCndWCUIETBfwlkpdn5e0AdrjNXxxGVi"
        "03gpQl/VvLT3wZyUy3ec3fWuAymf8fmSA0mmaUS57ICy42+YP22ACuIifWQIMV+7jt+VvyXTLHMAas4zx/cKq7rKxIexXqav0LXV"
        "4zOE4jcZzPnXPSOb7bbckDXjNwsEFYLNuT4lcw0rjH8IX68zqtolymSbsXcYZxKh0c3V0BnYN/1upa5lWpKv0kI9ezBwbuxhf/x5"
        "prnsevBFlr818QCwUGpyhoqF2jdntoD+rT1xTNJ4cjW5H0PEVH98igvYwq5TY1dIhHT0jno1yHIG9eEAVpAF2rCB/rCn/scJ49JE"
        "YVMvCWmg7RXKgfKrpElNRHSedqexiOvrk9cd7uTDzo3ZDtYOwL+2u9PyDqiZ1A/1BXcuv15fnzwetPG35/9ErYZMmR7NJI1iJWFV"
        "mY1NUyU0H8zSNoeU8DTOX9EkAuyrMpVkqWdOJiSGbQ70H+wJMmfmQ/2LeOL1SovfPwqjxfZLz3qZ38owcYaG9nY+n+V7BUKZD/0G"
        "39kYA/0GAAA="
    ),
    _p(*_DESIGN_FINALIZE_PLAN): (
        "H4sIAAAAAAACE5VUbU/bMBD+7l9xhAroJDfAvrV0UwUURWKoouXLEIrc5NJ4TZwsdlrKy3+fndCUBArDqlTnTnfPPc/deXfHzmVm"
        "T7mwUSxgymRIdmHIBYsgRi9kgnv6yjLFA+YpWLCI+0zxRECQZGD7KPlMQBoxARkuOC47hEhUQDFPIOUpBoxHhIxPr53RxD1zrvut"
        "A88Hq3Xg80ywGPX10GpbsLcH6dIHOmrrAmSIUeSF6M1BJnnmYV96GU+VtCM+pX9zjqqjKy19OsMmvd3pvPzei7AIOTsfOxdX7uTX"
        "yBRjaUsu2QwP2vBIQJ9lyCMEZzjua0JMF5RBxAX2wE8gYpkXuphlGtIYLWMVCCcn+zfjwcX5fpmrC4ERkD8gNcJoXKC0VIqqONXE"
        "QWOTIoQ8E1JC3t5CaxfoTMEh3N2ZzEU9HpOG4ZEFXBQGcxrp2pXDnAbD1uNx92cTP0MtSYYSmGlpjs9WLYUMeaDguGbr9Tbw4ROl"
        "ukVpHbggX7PgPdd0tqX5Vg9/pW5Tvy7kYi6SpdCTOMtjFKoLWpL/QX+XBErmEdM6QnhglKcPWuOacFbRBBViqfqHxTXV5XItsF/W"
        "uKntpaaAE5KuVJiI71vGt/TaXsQ76coCiVKarXtZQGwgvin+6QkeAWOu3PkChs7V4NL5fe6OLgdX7ngymNyMIeY6o5jVE/XKAo96"
        "8ExKysXquFxwtdZqB6j/iVpfB96Ic1SIY16XmK3cKboYp2qlp19r+gc9hT7VHfB1BtmJfWCeh6kxmm7UPElS/C0SZdAUi6KV/q4W"
        "K2Uq7Ddo2K3XmGXvKtJmDU1Qg6s5XfixdpZEoioqqKJ0S+jl9hwfasZF0Xi6fog/iRpcT5zh4HSi0d4SeqW0uWq1y00wkq/H1shd"
        "jLe6V+DzIKDmvZPmsxKwoijhjYzV+H+R53o2vs6zvnDbOH4InszJP0gymGUQBwAA"
    ),
    _p(*_DESIGN_PREVIEW): (
        "H4sIAAAAAAACE9VYX1PbRhB/16dYZBL/GWQbk3YmpqSTAZowJQmD6UMGqCJLZ+sm8knRnXEcYKYfok996mfLJ+nuSbZ1MjiQMJnG"
        "yYM47e3ub3d/e3uqrLXGMm31uWgxcQF9T4ZWBfZHXEFPsQQ6feCjJGIjJpSneCycJPIEJCm74GyykQltAS06vicCHniKLV7HKWp7"
        "QUu7MODCi4ztUJOhl7IAIi8dsuyVHI9GXjqFKB5yv96EHmMg3/Mokq2AST4Urd7vB4eHzVHQtCzJFDhsHEPCEzbweGRZvd3jg6MT"
        "d+/geGe95gdgr9cCngpvxPCxbddtePwYkkkAzlHdssbSG7JaHS4twF+ScqEGUH0kz0QVzvQa/aparAsMw+JkXmhnnRxHU4bgzF6o"
        "UYIGAR3AtQsv5Z5QIDFMW1dDDIR/Rc+dflH/s8cd69qyMgVupmDHts0FF8HutK1cI722JiGPGJyewnoFnKGCNpyfb0MQa8W+Jwny"
        "pg1czC2VvKzPX9CvZH/9suNc27dLaIc2jfcy5AMFHWNte7tgPffetDuHhBa7vy6ClrIPY54yCR6KRGNWcuZLxkK4QoshixLTnE6m"
        "scI+Yrm3b1PUMLebRWKvqIkujMV7EU8EYHmPiUFdoHxQuu/g0I3ImPR8K4gFsyw+oNTb60tJsZETH7AYrhD/JxTI42nr6lAhEzcU"
        "e3UljnJxI9ELxY0UnuUqqM7RLVDlaAbcskScjryIf2JuznNXhZjhMI6COQuj2PcicFNvAq7SK/RM1XH4/Hj3pbu33zt48do9Onz+"
        "2u398erV8+O37snL4/3eyzeHe11ns9POCyVnAO02SFCtYmVgeKBxutZ2np436mhoB/cVs94+vfVVtjhTXEyMGdcqNZ/aZruyfumq"
        "63rdJpJTbOfguXQHBL+EXcsMkNs7mr8z6XylY4OrJUaKY1ebK9N/ai1YFo5E48WNuu/p1bl2KggqkpSpcSogo3JBNTZQiU0fHB/R"
        "vK2aWzvPsB9ftMQ4ikhHJkiwR7cL1kmyaMDOEmVCWDZr4lht+VbZzLhpKbdP8RJUKQvXsnDpRWPLjTHTNCzLOUNWVnl+ThVATMuW"
        "+3EwXZn6wgt9RLoiVswdjJQugyJb9L6IC+yWue6pouclmoEbjxUJLt6ROauQfK0GszDxwYngFyObV6BScALAjlEvbNHW8i3+F7cs"
        "OYU7V3SGbBe2u1qtiPPZDYrq9UKHM2zlMS0MAwsX6y3d8XJRHC0WBw1avZGxZo0Xsq8XSk5kzUgtic0FWCTNAyBkXkDlt2nYufEc"
        "shqNHvNpNIM8s91Gw7KqhvAs6RjoYYoTm7MP1T8rl52NrWso8fVqbvyJPkJUOmbmCZgdPBk5cr2ls2XFebnYYp545QgUo7DVvj0M"
        "eKrc8Fgp8QW4BD8WKo2jCOfNkOGRVVOTGB5JGMQpkEMtKmKUGgslIRbRtN4s6JM4SER+yPz3EHDp9bGaerud9k9PrRJQ21q/NI1f"
        "W/a8E+jSXfypeZMBMiKQVUsJco5vnvgqdZMKHHLFUuwB79bzk/Hk1RFOn+8IM0ri2IG1ge9rcYJyKk6dgedzMYTEUyGEKLIB6Coe"
        "04knJMoi7lvxbv5suQV0eq7dqTYaJyHTRCGjF4zmdxKCGsZXQ96gSGu0ONO/weBSsYDiCgdYmiakWcJ6pkBG0+zUjy9YE8jAgFr+"
        "zApGyASsSdxUHxV8/utvkN4UbNKw2GWDitEQ06ap92J4wA9RUZ9hETC4iBXFpc+GXMhmo1G9cxz0ZP+/jEPC0XObblGFOKABMpuk"
        "8Sgh9BGGCVk9jccwoYkO5zVdZUiVUogC5vMAg3Sv6GQ3nnuH5zkMmaCSRTdm10LkajlEqOprI6RRWPmcOB+T81Ex87puldoeTdSX"
        "xszdxWsSdco1OuVK8/gtjbE0fDcan//5F+/a2LnB8BRGXEqqScTNBd6CeLCNzUEQX3FAl4ySZdzPNerqqutNoU0ipDVIpiqMxRZ6"
        "vrg7t5rN/H/2tuVHvJlMcRZlkloEaFcwM6WLQRn9t0AnjGMRMLxuRFigEZfqgbFjOteymdjwel4e90/enHqFvDHk2PQhPZ/ZPxOV"
        "ChyYeo5Qzxn+W+gyx80VWPFMWuLs4qzNrzm64X9HTmx1708IzfvFxyg637O7LLH9ByPGEv67sMIMwL1QPyQl0Pe78+EBkmbwgogA"
        "u4a+Y63vwdixtUQOPQV8R3I86X8FO/Rn2PxLno76D8iKZeB3ocW3IX9IZpD/d6fGN/htUOI3rWcv0/NgB4Uu+iUqFD6a3ueDaV60"
        "hY+LtTEOZ5puGxm/NvQMmM1mXVhMbcWvqqXvp+iT/jz3H0NiC4vtGAAA"
    ),
    _p("skills", "design", "scripts", "design-step3-state.sh"): (
        "H4sIAAAAAAACE+1X227jNhB911dMZG9sBaDtJO1D43WKdDdoA7S7Qew+pYFBS7RFVKa4IpXEdQL0I/qF/ZIOKdmxZPlWLNCXCoEikMO5njlD147aqUraIy7a"
        "TDzCiKrQqUHAFJ8IojST5/immrVUCH//+ReokCYsgD7uwDkoJjQXLIJpikI8FgrGcQLt7HzLcRTTQFgag+SSjSmPHKf/4e7mdjD8eHPXc+tNPwB8BzwRdMrw"
        "c/7DVf+nYf/zr3cfru87D6+u58LxMcinAMit5zqpohPW9GDuAD4y4UKPofFO/SYa0LCbFxu8JyRf11OJ9gAdgCYhE9wmIzKaSarUCwrxhPmaJOyRsyeC8SWz"
        "tVVJU8VIOJtwJhju0lTHxI9NLlKbhuyc14DL4zPn1XE+Xvdvfvw0HPxya8N2nasPg5vPn8yX8xTyiMH9PdRrQCYaOvDw0IUgtgH6VJmsnLrAhV0wTykSb7lh"
        "npKp+vzs4vty6An7kmJACig80ihlr25BhQr5WMNZYa3bXTFfyFnRPMZB/kCPswBdjAVeXmAOtjRdYM8cNXfhtXBokY36/LRGSJU3m335mvX6TyMJ0bGQRbLo"
        "hbVWWLGGO5vUnOx1vLK2TFHfCWLBHMfELjD2AphsI9rlnSmRMx3G4hxF37q93Wrlf9lu2494S85cJBGlsAYGijwwyCqCdc0LNJkHUcZ6xibrTi/ZY/q70Uhk"
        "Ward8uOpjJhmAXZkwmgwzKAzTOJUBEMf33rJOlHs0wgS+mT61yzwsUWLWlOb488qIVZJSz9r13a4DtlbS1tl9aZG5wJo3F8oSX128dCA9/uqPLtE1n1sizSK"
        "TIZ0kjIv827MV6kELRXIpNF4Obk/6pDvHk68JZ92DJ0WUFWiWvS1edqpGW0eMvQqgpDu/IhRkcohsr+OWDC0TDyM4hiXDB2XMjmlz1mee5bpJNWhGUQMxKrj"
        "SynjftHthOk0Ecic3W7mgw0bB5FVxdeR3G5lwyHL4klLhpmNkpSMqCAyYYRKGc2W0pjvJUEvmMKcNtYWTZGzCysI/bwqhLhcEzJRGxyY//lAtPLeG5GIBehW"
        "UmPEC0U1T1WIRXLI1dXn5nytIF9irqWkeJcpqthfgYsdzRtzt82JylNbnEF1211ZwmElXWIdQYtKFBCUt3azCQbqAt737McSiOB5pTa2rTwFMl4UbrmTN6Gl"
        "V9MhmScLIs1Lt2Gu5vQy3sJabVM8ct76toJbKi5K/cH17fmwP7gaXPcSNsbpGOCQTDSnUXG4N9Znx2k5JvNcwOVO59yDpDEUZw/vN3ibI6DqcrDlalBO+VFl"
        "0vM+YVbd4fkWSIONbRN9Ja0LLO3K7H7I2ClENEumXNDI3RT1QoBIliiOawHRIVckScUe+ke7Zb7ZQ2Tkbk8Q0nsOCxnjvMmYBGf6jJwcAsFTdhBiz+hh4qMD"
        "xVcbIoPnG3/0elVQr4bmruFsZvuGG5DnVjJd0XPq+0waYFguH3MRcDFRhEZRaxpUVHeLPA6CR3NoD6txjEcWmvKfn5XmqgQPsFPq/qqmLd2UVnt/UbAyT+38"
        "QfI/Eewggq+D6n9NJ1v4fkNtC7PKXjn+AQD9ufWLEQAA"
    ),
    _p(*_DESIGN_RETALLY_ENV): (
        "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"
        "nnfXBlkRf3mi/Bdv4WnwAycAAA=="
    ),
    _p("skills", "design", "scripts", "record-plan-review-round-timing.sh"): (
        "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"
    ),
    _p("skills", "design", "scripts", "gate-b-dedup-plan.sh"): (
        "H4sIAAAAAAACE+VXbU/rNhT+7l9xMB20m9zyomlauWzj0o5V46UqoO2KsSg0bmOROlnswGXAfvuOnaRN0lBg0qRJi/qhdexznvOc"
        "x4/d9bVOouLOjZAdLu/gxlU+WYcTPvZdKcZuAEeu5vARolBp5kZR8AAe95II7oX2IYy0CKUbMB27IuAxRDFXPL5zzTA0hVIJh/Xd"
        "7W++brUJUVwD40kIkYj4BBcQcn44GgwvnN5gtN9ojj2gjaYnYunOOH7doi0KGxsQ3XvAhi0y6g/PnNHZ2UU+d7G6026nn9KC4fHl"
        "0eA0XUIbj4fHB5e9vlMY7bLGPOgzJWICV1ewBmyCwQvTOtGD9kPZGQeiHT1QuL7eA+1zSQCfcpJ5OEomgvT6vcshJjw4dY4Hp/1z"
        "Z/jJADk+GB3+5NS8RDzFtOpWBIHqeFyJqeyocSwibX4i/ywKXMkCIblCSIgdc50Pjk6di5OhYZNScnLW6+9TO5uSi9HB4Lg/cn7u"
        "fzp3fsSvZgZJlDvlzRY82krGroYPHzYvzw+O+pvw3cZO+r4LU9QAu2GLxG3lA2MpLqZnEfYMMCtcMaakGyk/1LkkFDzZqbj0GrPU"
        "TYBfYoEiy8UEuZhu+YMCHUI7y19VGzMTbMxUkk0PVZUEumWKGSUSapgCV3pw5wbCM7rO5Mo9m4vYyskzIfc+xjdaaKwDm2rYsi33"
        "wowmZdS5TUGkCjBPhY3W/IV5Kq1pPO50v6/SF/M/EoFwwDXwEo4tLYZQvpho2CmN7e0V0i/RWoZgxZDPWY78clzLYU0sO/6OQP4T"
        "Yz4PKqGswEoj/LNAvl8K82V5OdpUCLROnl1I5K0M7yW48TSZcam7YFpmVP0GALt1ALhyx8QLJSeZU7A/UQel5la8YRW+qgCEyjXg"
        "LWAu4GWw0FRI6ka7qz1KcaWMCedar2Rbwv30lKcgBqITudrfr8zqWPD6s671k8rclbuWkrLZzlO+g8AcDMzwnBFyih330DWqheVU"
        "2up2LIE5JAfJmrvfm1g1OZdOPYVrfqDGN9KaaMPsEAr7+0DzLVepq4gA5lvXGh5LDWtiHKhEDGNhoqNE4+gS+3RFVGsn/zBuO11M"
        "SWFrGgZLzVtG875dYLx7bn9RLMK49phorlRUroJWpeO7Od61Mj3zffEa6eZ9/mK50jeWWX+2BXipghs+CWOenlUV7NsG+7/YVILn"
        "n2MTO3lgcy3IzE29obU1ARrN2a3mswiWDMFCxRUpOe1f7UNTRx9HS0aAP5ai21sVScfQyV5LVkmUrov5LMQjP6t0DcqjjebCCGpu"
        "aLSKcY6Ftgq8xLO0nMVbO5wxK+trK1NbYqVmchGHXYDMFFPXkfeaTOsuTOaiXjySFj6am0BeZkYhGt9f8PvVFvv2+qtGuab/BS2z"
        "u2qRZVDocFJPYDONqu45j7qQcQdfKMDRAP964fXUJGuqFkzicDY/7n6TmxjvsUR5l20905Uu97pfpDNedLrcNAqt+K+3rd508XTJ"
        "yLD26yWxuTu8aL9kFYLsRPwbyk2WbkUPAAA="
    ),
    _p(*_DESIGN_TALLY_REVIEW): (
        "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"
    ),
    _p(*_DESIGN_PANEL_DISPATCH): (
        "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"
        "OX6JCfhc8cNUdJ/JBk9K/xuhy6tbQ1UAAA=="
    ),
    _p(*_DESIGN_RUN_REVIEW): (
        "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"
    ),

    _p(*_DESIGN_REVIEW_LOOP): (
        "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"
    ),
    _p("skills", "design", "scripts", "review-design-step3-loop.sh"): (
        "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"
        "YM6QAAA="
    ),
    _p(*_ROOT_VOTER_DISPATCH): (
        "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"
        "2XWUOAAA"
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


def _prune_shell_helpers() -> str:
    return r"""
prune_window_evaluated() {
    case "${1:-}" in 3|4) printf 'true\n' ;; *) printf 'false\n' ;; esac
}

_prune_nonneg_int() {
    case "${1:-}" in ''|*[!0-9]*) printf '0' ;; *) printf '%s' "$((10#$1))" ;; esac
}

normalize_prune_eligible() {
    if [[ "${1:-false}" != "true" ]]; then printf '0\n'; else _prune_nonneg_int "${2:-0}"; printf '\n'; fi
}

derive_prune_status() {
    local prune_active="${1:-false}" filter_rc="${2:-0}" prune_fail_open="${3:-false}" pruned_count="${4:-0}" panel_pruned_empty="${5:-false}" prune_evaluated="${6:-false}"
    pruned_count="$(_prune_nonneg_int "$pruned_count")"
    case "$filter_rc" in ''|*[!0-9]*) filter_rc=1 ;; *) filter_rc=$((10#$filter_rc)) ;; esac
    if [[ "$filter_rc" -ne 0 || "$prune_fail_open" == "true" ]]; then printf 'failed\n'
    elif [[ "$panel_pruned_empty" == "true" ]]; then printf 'pruned-empty\n'
    elif [[ "$prune_active" != "true" || "$prune_evaluated" != "true" ]]; then printf 'skipped\n'
    elif [[ "$pruned_count" -gt 0 ]]; then printf 'active-dropped\n'
    else printf 'active-kept-all\n'; fi
}

ensure_reviewer_prune_ledger() {
    python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune --help >/dev/null 2>&1 || return 1
    PYTHONPATH="$PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$1" <<'PY'
from pathlib import Path
import sys
import review_pipeline
review_pipeline.ensure_reviewer_prune_ledger(Path(sys.argv[1]))
PY
}

write_prune_decision_env() {
    python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune --help >/dev/null 2>&1 || return 1
    PYTHONPATH="$PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$@" <<'PY'
from pathlib import Path
import sys
import review_pipeline
review_pipeline.write_prune_decision_env(Path(sys.argv[1]), *sys.argv[2:])
PY
}
"""


def _rewrite_prune_asset(text: str) -> str:
    text = text.replace(
        '    || [[ ! -f "$PLUGIN_ROOT/scripts/lib-prune-'
        'decision.sh" ]] \\\n',
        "",
    )
    text = text.replace(
        '# shellcheck source=scripts/lib-prune-'
        'decision.sh\nsource "$PLUGIN_ROOT/scripts/lib-prune-'
        'decision.sh"',
        _prune_shell_helpers(),
    )
    text = text.replace(
        'REVIEWER_PRUNE_SH="${REVIEWER_PRUNE_SH:-$PLUGIN_ROOT/scripts/reviewer-'
        'prune.sh}"',
        'REVIEWER_PRUNE_CLI=(python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune)',
    )
    text = text.replace(
        'LARCH_QUIET_DISABLE=1 "$REVIEWER_PRUNE_SH" filter',
        'LARCH_QUIET_DISABLE=1 "${REVIEWER_PRUNE_CLI[@]}" filter',
    )
    text = text.replace(
        '"$PLUGIN_ROOT/scripts/reviewer-'
        'prune.sh" record',
        'python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune record',
    )
    text = text.replace(
        'PLAN_REVIEW_PRUNE_NITS_SH="${LARCH_PLAN_REVIEW_PRUNE_NITS_SH:-$PLUGIN_ROOT/skills/review/scripts/'
        'prune-nit-findings.sh}"',
        'if [[ -n "${LARCH_PLAN_REVIEW_PRUNE_NITS_SH:-}" ]]; then\n'
        '    PLAN_REVIEW_PRUNE_NITS_CLI=("$LARCH_PLAN_REVIEW_PRUNE_NITS_SH")\n'
        'else\n'
        '    PLAN_REVIEW_PRUNE_NITS_CLI=(python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings)\n'
        'fi',
    )
    text = text.replace(
        '"$PLAN_REVIEW_PRUNE_NITS_SH"',
        '"${PLAN_REVIEW_PRUNE_NITS_CLI[@]}"',
    )
    text = text.replace(
        '"${PLAN_REVIEW_PRUNE_NITS_SH}"',
        '"${PLAN_REVIEW_PRUNE_NITS_CLI[@]}"',
    )
    text = text.replace(
        '"${PLAN_REVIEW_PRUNE_NITS_CLI[@]}" \\\n'
        '    --findings-file "$DESIGN_TMPDIR/findings-in-scope.md"',
        'LARCH_QUIET_DISABLE=1 "${PLAN_REVIEW_PRUNE_NITS_CLI[@]}" \\\n'
        '    --findings-file "$DESIGN_TMPDIR/findings-in-scope.md"',
    )
    text = text.replace(
        'if [[ "$_plan_prune_rc" -ne 0 ]]; then\n'
        '    emit_kv WARN "plan-review-prune-nit: subprocess exited with rc=$_plan_prune_rc (failing open)"\n'
        'fi',
        'if [[ "$_plan_prune_rc" -ne 0 ]]; then\n'
        '    emit_kv WARN "plan-review-prune-nit: subprocess exited with rc=$_plan_prune_rc (failing open)"\n'
        'fi\n'
        'if [[ "$_plan_prune_rc" -ne 0 || ! -s "$_plan_prune_out" ]]; then\n'
        "    printf 'PRUNED_COUNT=0\\nINSCOPE_REMAINING=0\\nSTATUS=skipped\\n' > \"$_plan_prune_out\"\n"
        'fi',
    )
    return text  # noqa: RET504


def _decode_legacy_asset(rel_path: str, data: str) -> bytes:
    body = _decode_asset(data)
    retired_waterfall = "dispatch-with-" + "waterfall.sh"
    if rel_path == _p(*_ROOT_VOTER_DISPATCH):
        text = body.decode("utf-8")
        text = text.replace(
            f'"$PLUGIN_ROOT/scripts/{retired_waterfall}"',
            'python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall',
        )
        text = text.replace(
            f"{retired_waterfall} exited $_waterfall_rc",
            "agent dispatch-waterfall exited $_waterfall_rc",
        )
        return text.encode("utf-8")
    if rel_path == _p(*_DESIGN_PANEL_DISPATCH):
        text = body.decode("utf-8")
        text = text.replace(
            'DISPATCH_WATERFALL_SH="${DISPATCH_PLAN_REVIEW_WATERFALL_SH:-$PLUGIN_ROOT/scripts/'
            f'{retired_waterfall}}}"',
            'if [[ -n "${DISPATCH_PLAN_REVIEW_WATERFALL_SH:-}" ]]; then\n'
            '    DISPATCH_WATERFALL_CMD=("$DISPATCH_PLAN_REVIEW_WATERFALL_SH")\n'
            "else\n"
            '    DISPATCH_WATERFALL_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall)\n'
            "fi",
        )
        text = text.replace(
            '"$DISPATCH_WATERFALL_SH"',
            '"${DISPATCH_WATERFALL_CMD[@]}"',
        )
        text = text.replace(
            "dispatch-with-waterfall exited rc=$_waterfall_rc",
            "agent dispatch-waterfall exited rc=$_waterfall_rc",
        )
        text = _rewrite_prune_asset(text)
        return text.encode("utf-8")
    if rel_path == _p("skills", "design", "scripts", "plan-review-" + "loop.sh"):
        return _rewrite_prune_asset(body.decode("utf-8")).encode("utf-8")
    return body


def legacy_asset_bytes(rel_path: str) -> bytes:
    """Return embedded legacy asset bytes for contract tests."""
    return _decode_legacy_asset(rel_path, _LEGACY_ASSETS[rel_path])


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
            _ = path.write_bytes(_decode_legacy_asset(rel, data))
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
        # Embedded scripts run with cwd=_REPO_ROOT (the plugin cache, not a git
        # repo). Expose the consumer repo (this process's CWD) so child `dirty-tree
        # checkpoint` calls can target it via LARCH_CONSUMER_REPO and avoid the
        # false-positive dirty-tree WARN from a failing `git status` (issue #4509).
        _ = env.setdefault("LARCH_CONSUMER_REPO", str(Path.cwd()))
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


def persist_design_round_start_s(design_tmpdir: str | Path, round_num: int, start_s: int) -> int:
    """Write plan-review/round-N/round-start-s once with O_EXCL|O_NOFOLLOW."""
    ok, _message = validate_design_tmpdir(str(design_tmpdir))
    if not ok:
        return 1
    tmpdir = Path(design_tmpdir)
    if tmpdir.is_symlink():
        return 1
    plan_review_dir = tmpdir / "plan-review"
    if plan_review_dir.is_symlink() or (plan_review_dir.exists() and not plan_review_dir.is_dir()):
        return 0
    round_dir = plan_review_dir / f"round-{round_num}"
    if round_dir.is_symlink():
        return 0
    try:
        round_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    if round_dir.is_symlink() or not round_dir.is_dir():
        return 0
    start_file = round_dir / "round-start-s"
    if start_file.is_symlink() or start_file.exists():
        return 0
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(start_file, flags, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            _ = handle.write(f"{start_s}\n")
    except OSError:
        return 0
    return 0



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
    # Ported in-process (docs/python-migration.md C3a1 follow-up): the retired
    # tally-plan-review.sh spawned ~F*(3V+5) cli.py subprocesses per tally. The
    # gzip-embedded body in _LEGACY_ASSETS is retained but no longer executed.
    return plan_review_tally.main(list(argv))


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
        "panel-init-failed": "validation",
        "tally-error": "validation",
        "degraded-empty-collector": "validation",
    }
    phase = phases.get(status)
    if phase is None:
        return 0
    sentinel = tmpdir / f".step3-report-{status}.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    try:
        tmpdir.mkdir(parents=True, exist_ok=True)
        stdout = tmpdir / f"step3-record-escalation-{status}.stdout.log"
        stderr = tmpdir / f"step3-record-escalation-{status}.stderr.log"
        ns = argparse.Namespace(
            implement_tmpdir=str(tmpdir),
            artifact_prefix="design-failure",
            profile="generic",
            site="step3-review",
            trigger=status,
            step="step3",
            phase=phase,
            dispatcher="design-step3-review",
            exit_code="unknown",
            failure_detail_log="",
        )
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = stall_recovery.record_escalation(ns)
        if rc == 0:
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


def persist_round_start_s_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review persist-round-start-s")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--round-num", type=int, required=True)
    _ = parser.add_argument("--start-s", type=int, required=True)
    ns = parser.parse_args(argv or [])
    return persist_design_round_start_s(ns.design_tmpdir, ns.round_num, ns.start_s)


def round_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv or [], round_artifact_included)


def round_revise_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv or [], round_revise_artifact_included)


def round_revise_artifact_excluded_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv or [], round_revise_artifact_excluded)


def drift_baseline_main(argv: list[str] | None = None) -> int:
    return _drift_baseline_cli(argv or [])
