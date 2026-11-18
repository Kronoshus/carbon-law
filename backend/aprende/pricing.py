"""Pricing engine for Aprende y Planea."""
import json

import db


def load_settings(key="pricing"):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    if not rows:
        return None
    return json.loads(rows[0][0])  # raises on bad JSON


DOC_CODES = {"will", "trust", "poa", "ahcd"}


def _as_codes(codes):
    if isinstance(codes, str):
        return [c.strip() for c in codes.split(",") if c.strip()]
    return list(codes or [])


def _earned_lookup(earned):
    """Normalize `earned` into {(doc, event): cents}."""
    out = {}
    if not earned:
        return out
    for key, val in (earned.items() if hasattr(earned, "items") else []):
        if isinstance(key, (tuple, list)) and len(key) == 2:
            doc, event = key
        elif isinstance(key, str) and "|" in key:
            doc, event = key.split("|", 1)
        else:
            continue
        out[(str(doc), str(event))] = int(val)
    return out


def quote(settings, facts, codes, earned=None):
    settings = settings or {}
    base = settings.get("base") or {}
    packages = settings.get("packages") or {}
    discounts_cfg = settings.get("discounts") or {}
    currency = settings.get("currency", "USD")
    test_mode = settings.get("test_mode", True)
    if test_mode is None:
        test_mode = True
    placeholders = set(settings.get("placeholder_codes") or [])

    facts = facts or {}
    codes = _as_codes(codes)
    earned_lookup = _earned_lookup(earned)

    items = []
    total = 0

    # package: exact set match only
    package = None
    code_set = frozenset(codes)
    for key, val in (packages or {}).items():
        if isinstance(key, str):
            key_set = frozenset(k.strip() for k in key.split(",") if k.strip())
        elif isinstance(key, (list, tuple, set, frozenset)):
            key_set = frozenset(key)
        else:
            key_set = None
        if key_set is not None and key_set == code_set:
            package = val
            break

    for code in codes:
        base_price = int(base.get(code, 0) or 0)

        cfg = discounts_cfg.get(code) or {}
        amount = int(cfg.get("amount", 0) or 0)
        events = list(cfg.get("events") or [])
        floor = cfg.get("floor", None)
        if floor is not None:
            floor = int(floor)

        discount_list = []
        subtotal_discount = 0
        for ev in events:
            if ev in facts:
                locked = earned_lookup.get((code, ev))
                amt = amount if locked is None else int(locked)
                discount_list.append({"event": ev, "amount": amt})
                subtotal_discount += amt

        price = base_price - subtotal_discount
        if floor is not None:
            price = max(price, floor)
        price = int(price)

        items.append({
            "code": code,
            "base": base_price,
            "discounts": discount_list,
            "price": price,
            "placeholder": bool(code in placeholders),
        })
        total += price

    if isinstance(package, dict) and "price" in package:
        total = int(package["price"])

    return {
        "items": items,
        "package": package,
        "total": total,
        "currency": currency,
        "test_mode": test_mode,
    }
