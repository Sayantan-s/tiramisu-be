"""Parity tests: the Python split engine must produce the same shares as the
TS engine for the same inputs. Fixtures mirror src/lib/split/__tests__."""

from app.lib.split import split_by_rule, validate_split


def test_equal_no_remainder():
    shares = split_by_rule(1000, {"type": "equal", "participantIds": ["a", "b", "c", "d"]})
    assert shares == {"a": 250, "b": 250, "c": 250, "d": 250}


def test_equal_remainder_deterministic():
    # Same expected output as TS test: sorted by id, leftover distributed round-robin.
    shares = split_by_rule(100, {"type": "equal", "participantIds": ["carol", "alice", "bob"]})
    assert sum(shares.values()) == 100
    assert shares["alice"] == 34
    assert shares["bob"] == 33
    assert shares["carol"] == 33


def test_shares_weighted_exact():
    shares = split_by_rule(
        4000, {"type": "shares", "shares": {"alice": 2, "bob": 1, "carol": 1}}
    )
    assert shares == {"alice": 2000, "bob": 1000, "carol": 1000}


def test_percent_summing_to_100():
    shares = split_by_rule(
        10000, {"type": "percent", "percents": {"alice": 50, "bob": 30, "carol": 20}}
    )
    assert sum(shares.values()) == 10000
    assert shares["alice"] == 5000
    assert shares["bob"] == 3000
    assert shares["carol"] == 2000


def test_exact_returns_amounts_as_is():
    shares = split_by_rule(1000, {"type": "exact", "amounts": {"alice": 600, "bob": 400}})
    assert shares == {"alice": 600, "bob": 400}


def test_itemized_aggregates_line_items():
    shares = split_by_rule(
        2100,
        {
            "type": "itemized",
            "items": [
                {
                    "id": "i1",
                    "description": "Bob's beer",
                    "amount": 400,
                    "split": {"type": "exact", "amounts": {"bob": 400}},
                },
                {
                    "id": "i2",
                    "description": "Shared food",
                    "amount": 1700,
                    "split": {
                        "type": "equal",
                        "participantIds": ["alice", "bob", "carol", "dev"],
                    },
                },
            ],
        },
    )
    assert sum(shares.values()) == 2100
    assert shares["bob"] == 400 + 425
    assert shares["alice"] == 425


def test_validate_rejects_zero_amount():
    ok, _ = validate_split(0, {"type": "equal", "participantIds": ["a"]})
    assert ok is False


def test_validate_rejects_bad_percent_sum():
    ok, _ = validate_split(1000, {"type": "percent", "percents": {"a": 50, "b": 30}})
    assert ok is False


def test_validate_rejects_exact_mismatch():
    ok, _ = validate_split(1000, {"type": "exact", "amounts": {"a": 400, "b": 400}})
    assert ok is False


def test_validate_accepts_well_formed():
    ok, _ = validate_split(1000, {"type": "exact", "amounts": {"a": 400, "b": 600}})
    assert ok is True


def test_property_total_preserved_random_equal():
    rand_seed = 1
    for _ in range(100):
        rand_seed = (rand_seed * 9301 + 49297) % 233280
        total = (rand_seed % 1_000_000) + 1
        n = (rand_seed % 5) + 1
        ids = [f"m{i}" for i in range(n)]
        shares = split_by_rule(total, {"type": "equal", "participantIds": ids})
        assert sum(shares.values()) == total
