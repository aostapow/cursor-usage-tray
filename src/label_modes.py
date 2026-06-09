from __future__ import annotations



from dataclasses import dataclass

from enum import Enum

from typing import TYPE_CHECKING



from .usage_basis import UsageBasis, basis_percent_label, basis_usd_label, usage_percent



if TYPE_CHECKING:

    from .api import UsageSnapshot

    from .config import AppConfig





class LabelMode(str, Enum):

    USD = "usd"

    TOKENS_CYCLE = "tokens_cycle"

    TOKENS_DAILY = "tokens_daily"

    PLAN = "plan"





@dataclass(frozen=True)

class LabelDisplay:

    text: str

    mode: LabelMode

    usage_percent: float | None

    use_threshold_colors: bool





def format_tokens(count: int | None, *, suffix: str) -> str:

    if count is None:

        return f"— tk/{suffix}"

    if count >= 1_000_000:

        value = count / 1_000_000

        text = f"{value:.1f}M tk/{suffix}".replace(".0M", "M")

        return text

    if count >= 10_000:

        value = count / 1_000

        text = f"{value:.1f}K tk/{suffix}".replace(".0K", "K")

        return text

    return f"{count:,} tk/{suffix}".replace(",", ".")





def format_plan(snapshot: "UsageSnapshot", basis: UsageBasis) -> str:
    return basis_percent_label(snapshot, basis)





def enabled_modes(config: "AppConfig", snapshot: "UsageSnapshot | None") -> list[LabelMode]:

    modes: list[LabelMode] = []

    if config.label_show_usd:

        modes.append(LabelMode.USD)

    if config.label_show_tokens:

        if snapshot is None or snapshot.cycle_tokens is not None:

            modes.append(LabelMode.TOKENS_CYCLE)

    if config.label_show_daily_tokens:

        if snapshot is None or snapshot.daily_tokens is not None:

            modes.append(LabelMode.TOKENS_DAILY)

    if config.label_show_plan:

        modes.append(LabelMode.PLAN)

    if not modes:

        modes.append(LabelMode.USD)

    return modes





def display_for_mode(

    mode: LabelMode,

    snapshot: "UsageSnapshot | None",

    *,

    error: bool,

    usage_basis: UsageBasis | None = None,

) -> LabelDisplay:

    if error or snapshot is None:

        if mode == LabelMode.USD:

            return LabelDisplay("$!", LabelMode.USD, None, True)

        if mode in (LabelMode.TOKENS_CYCLE, LabelMode.TOKENS_DAILY):

            suffix = "c" if mode == LabelMode.TOKENS_CYCLE else "d"

            return LabelDisplay(f"— tk/{suffix}", mode, None, False)

        return LabelDisplay("—%", LabelMode.PLAN, None, False)



    if mode == LabelMode.USD:

        basis = usage_basis or UsageBasis.ON_DEMAND

        return LabelDisplay(

            basis_usd_label(snapshot, basis),

            LabelMode.USD,

            usage_percent(snapshot, basis),

            True,

        )

    if mode == LabelMode.TOKENS_CYCLE:

        return LabelDisplay(

            format_tokens(snapshot.cycle_tokens, suffix="c"),

            LabelMode.TOKENS_CYCLE,

            None,

            False,

        )

    if mode == LabelMode.TOKENS_DAILY:

        return LabelDisplay(

            format_tokens(snapshot.daily_tokens, suffix="d"),

            LabelMode.TOKENS_DAILY,

            None,

            False,

        )

    basis = usage_basis or UsageBasis.ON_DEMAND
    return LabelDisplay(

        format_plan(snapshot, basis),

        LabelMode.PLAN,

        usage_percent(snapshot, basis),

        True,

    )





def current_display(

    config: "AppConfig",

    snapshot: "UsageSnapshot | None",

    *,

    mode_index: int,

    error: bool,

) -> LabelDisplay:

    modes = enabled_modes(config, snapshot)

    if not modes:

        return LabelDisplay("—%", LabelMode.USD, None, True)

    if config.label_alternate_seconds <= 0:

        mode_index = 0

    mode = modes[mode_index % len(modes)]

    return display_for_mode(mode, snapshot, error=error, usage_basis=config.usage_basis_enum())


