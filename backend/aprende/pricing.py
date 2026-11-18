"""Pricing engine for Aprende y Planea."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db


def load_settings(key="pricing"):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    if not rows:
        return None
    try:
        return json.loads(rows[0][0])
    except (ValueError, TypeError):
        return None


class Quote(dict):
    def __init__(self, *, items, package=None, total, currency="USD", test_mode=True):
        super().__init__({
            "items": items,
            "package": package,
            "total": total,
            "currency": currency,
            "test_mode": test_mode,
        })

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _as_codes(codes):
    if codes is None:
        return []
    if isinstance(codes, str):
        return [c.strip() for c in codes.split(",") if c.strip()]
    return [str(c).strip() for c in codes]


def _earned_map(discounts):
    out = {}
    if not discounts:
        return out
    for row in discounts:
        if isinstance(row, dict):
            doc = row.get("document") or row.get("doc") or row.get("code")
            event = row.get("event")
            amount = row.get("amount_cents")
            if amount is None:
                amount = row.get("amount")
        else:
            # tuple/list: (journey_id, document, event, amount_cents, ...) or (document, event, amount)
            if len(row) >= 4:
                doc, event, amount = row[1], row[2], row[3]
            elif len(row) == 3:
                doc, event, amount = row[0], row[1], row[2]
            else:
                continue
        if doc is None or event is None or amount is None:
            continue
        out.setdefault(str(doc), {})[str(event)] = int(amount)
    return out


def quote(settings, facts, codes, discounts=None, earned=None, **_kw):
    settings = settings or {}
    base = settings.get("base") or {}
    packages = settings.get("packages") or {}
    discounts_cfg = settings.get("discounts") or {}
    currency = settings.get("currency", "USD")
    test_mode = settings.get("test_mode", True)
    if test_mode is None:
        test_mode = True
    placeholders = set(settings.get("placeholder_codes") or settings.get("placeholders") or [])

    facts = facts or {}
    codes = _as_codes(codes)
    earned_map = _earned_map(discounts if discounts is not None else earned)

    # package detection
    package = None
    pkg_key = ",".join(sorted(codes))
    if pkg_key in packages:
        package = packages[pkg_key]
    else:
        for key, val in packages.items():
            if isinstance(key, str) and set(key.split(",")) == set(codes) or set(key.split("+")) == set(codes):
                package = val
                break

    items = []
    total = 0
    for code in codes:
        base_price = base.get(code)
        if base_price is None:
            base_price = 0
        base_price = int(base_price)

        cfg = discounts_cfg.get(code) or {}
        amount = int(cfg.get("amount", 0) or 0)
        events = list(cfg.get("events") or [])
        floor = cfg.get("floor", None)
        if floor is not None:
            floor = int(floor)

        # placeholder determination
        if code in placeholders:
            placeholder = True
        elif base.get(code) is None:
            placeholder = True
        else:
            placeholder = (code != "will") and (code in ("trust", "poa", "ahcd"))

        discount_list = []
        subtotal_discount = 0
        for ev in events:
            if ev in facts:
                amt = earned_map.get(code, {}).get(ev, amount)
                amt = int(amt)
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
            "placeholder": bool(placeholder),
        })
        total += price

    if package is not None:
        # package may override total if it has a price
        if isinstance(package, dict) and "price" in package:
            total = int(package["price"])

    return Quote(items=items, package=package, total=total, currency=currency, test_mode=test_mode)
