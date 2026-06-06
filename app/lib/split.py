"""Port of `src/lib/split/splitExpense.ts` from the frontend.

Mirror semantics exactly: integer paise math, deterministic remainder paise
distribution by sorted member id. Any change here MUST be paired with a change
in the TS engine and a passing parity test (`tests/test_split_parity.py`).
"""

from __future__ import annotations

from typing import Literal, TypedDict


SplitType = Literal["equal", "shares", "percent", "exact", "itemized"]


class EqualRule(TypedDict):
    type: Literal["equal"]
    participantIds: list[str]


class SharesRule(TypedDict):
    type: Literal["shares"]
    shares: dict[str, int]


class PercentRule(TypedDict):
    type: Literal["percent"]
    percents: dict[str, float]


class ExactRule(TypedDict):
    type: Literal["exact"]
    amounts: dict[str, int]


class LineItem(TypedDict):
    id: str
    description: str
    amount: int
    split: dict  # one of the non-itemized rules


class ItemizedRule(TypedDict):
    type: Literal["itemized"]
    items: list[LineItem]


SplitRule = dict


def split_by_rule(total: int, rule: SplitRule) -> dict[str, int]:
    kind = rule["type"]
    if kind == "itemized":
        shares: dict[str, int] = {}
        for item in rule["items"]:
            item_shares = split_by_rule(item["amount"], item["split"])
            for mid, amount in item_shares.items():
                shares[mid] = shares.get(mid, 0) + amount
        return shares
    return _split_non_itemized(total, rule)


def _split_non_itemized(total: int, rule: SplitRule) -> dict[str, int]:
    kind = rule["type"]
    if kind == "equal":
        return _divide_evenly(total, rule["participantIds"])
    if kind == "shares":
        return _divide_by_weights(total, rule["shares"])
    if kind == "percent":
        return _divide_by_weights(total, rule["percents"])
    if kind == "exact":
        return dict(rule["amounts"])
    raise ValueError(f"Unknown split rule: {kind!r}")


def _divide_evenly(total: int, ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}
    weights = {mid: 1 for mid in sorted(ids)}
    return _divide_by_weights(total, weights)


def _divide_by_weights(total: int, weights: dict[str, float]) -> dict[str, int]:
    ids = sorted(weights.keys())
    total_weight = sum(weights[mid] for mid in ids)
    if total_weight <= 0:
        return {}

    shares: dict[str, int] = {}
    allocated = 0
    for mid in ids:
        share = int((total * weights[mid]) // total_weight)
        shares[mid] = share
        allocated += share

    remainder = total - allocated
    i = 0
    while remainder > 0:
        mid = ids[i % len(ids)]
        shares[mid] += 1
        remainder -= 1
        i += 1
    return shares


def validate_split(total: int, rule: SplitRule) -> tuple[bool, str | None]:
    if total <= 0:
        return False, "Amount must be greater than zero"

    kind = rule["type"]
    if kind == "equal":
        if not rule["participantIds"]:
            return False, "Pick at least one participant"
        return True, None
    if kind == "shares":
        weights = rule["shares"]
        if any(v < 0 for v in weights.values()):
            return False, "Shares cannot be negative"
        if sum(weights.values()) <= 0:
            return False, "Shares must sum to more than zero"
        return True, None
    if kind == "percent":
        percents = rule["percents"]
        if any(v < 0 for v in percents.values()):
            return False, "Percents cannot be negative"
        total_pct = sum(percents.values())
        if round(total_pct * 100) != 10000:
            return False, f"Percents must sum to 100 (got {total_pct})"
        return True, None
    if kind == "exact":
        amounts = rule["amounts"]
        if any(v < 0 for v in amounts.values()):
            return False, "Amounts cannot be negative"
        if sum(amounts.values()) != total:
            return False, f"Amounts must sum to {total} (got {sum(amounts.values())})"
        return True, None
    if kind == "itemized":
        items = rule["items"]
        if not items:
            return False, "Add at least one line item"
        if sum(it["amount"] for it in items) != total:
            return False, f"Line items must sum to {total}"
        for item in items:
            ok, reason = validate_split(item["amount"], item["split"])
            if not ok:
                return False, f"Item '{item['description']}': {reason}"
        return True, None
    return False, f"Unknown split rule: {kind!r}"


def compute_balances(
    expenses: list[dict],
    settlements: list[dict],
    member_ids: list[str],
) -> dict[str, int]:
    balances = {mid: 0 for mid in member_ids}
    for e in expenses:
        balances[e["payerId"]] = balances.get(e["payerId"], 0) + e["amount"]
        shares = split_by_rule(e["amount"], e["split"])
        for mid, owed in shares.items():
            balances[mid] = balances.get(mid, 0) - owed

    for s in settlements:
        balances[s["fromId"]] = balances.get(s["fromId"], 0) + s["amount"]
        balances[s["toId"]] = balances.get(s["toId"], 0) - s["amount"]

    return balances
