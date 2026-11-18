"""Pricing engine for Aprende y Planea."""
import json

import db


def load_settings(key="pricing"):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    if not rows:
        return None
    return json.loads(rows[0][0])  # raises on bad JSON


DOC_CODES = {"will", "trust", "poa", "ahcd"}


def quote(settings, facts, codes, earned=None):
    """settings: the `pricing` setting; facts: the journey's facts; codes: document codes;
    earned: {(document, event): cents} recorded when each discount was earned (it keeps that amount)."""
    settings = settings or {}
    base = settings.get("base") or {}
    packages = settings.get("packages") or {}
    discounts_cfg = settings.get("discounts") or {}
    currency = settings.get("currency", "USD")
    test_mode = settings.get("test_mode", True)
    placeholders = set(settings.get("placeholder_codes") or [])

    earned = earned or {}

    items = []
    total = 0

    # package: a key "will,poa" matches exactly that set of documents
    package = next((v for k, v in packages.items() if frozenset(k.split(",")) == frozenset(codes)), None)

    for code in codes:
        base_price = int(base.get(code, 0) or 0)

        cfg = discounts_cfg.get(code) or {}
        amount = int(cfg.get("amount", 0) or 0)
        events = list(cfg.get("events") or [])
        floor = cfg.get("floor")

        discount_list = []
        subtotal_discount = 0
        for ev in events:
            if ev in facts:
                locked = earned.get((code, ev))
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
