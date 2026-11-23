#!/usr/bin/env python3
"""Silpo cart tools for the shopper project.

    python3 cart_tools.py need   --project <shopper folder>
    python3 cart_tools.py slot   --project <shopper folder> [--place wide] [--start <slot start>]
    python3 cart_tools.py match  --project <shopper folder> [--place wide]
    python3 cart_tools.py brands --project <shopper folder>
    python3 cart_tools.py price  --project <shopper folder>
    python3 cart_tools.py verify --project <shopper folder>

All files are in data/cart/ of the shopper folder. Silpo ships an order to the
door from one place: the regular store (home) or the bigger warehouse (wide).
One cart holds products of one place only. The store's searches, slots and
choices are in data/cart/, the warehouse's in data/cart/wide/; --place wide
makes slot and match work there.

need    asks the menu script what the saved menu needs bought and writes need.json.
        It clears the files of an earlier order and prints the time slot request.
slot    chooses the delivery time from slots.json (the time slot tool's result):
        the first free slot in the usual part of the day on the day before the
        menu starts, else the latest free slot before that day, else the first
        free slot. With --start, it takes that free slot instead (a time the
        user asked for). It writes slot.json, clears saved searches (they hold
        stock for one delivery time) and prints the timeslot and what to search.
match   finds each food's product in search-*.json (the search tool's results):
        the one named in choices.json, else the one with the food's code. At the
        warehouse a food chosen at the store is looked for by that product's code.
        In choices.json a food maps to a product code, to null (Silpo has no
        fitting product) or to "out" (the user left it out; set in the store's
        choices.json, it counts at both places).
        It prints the foods still to choose. When the store lacks a food or has
        too little of it, it prints check_warehouse: the warehouse's time slot request.
brands  prints the user's favourite brands (favourite_brands in data/profile.md),
        the place the order ships from with its branch and timeslot, and the
        foods of the order that may take a favourite brand (not pinned ones).
price   works out the order: amounts, costs, the total against the budget,
        delivery. The order ships from the store, unless the store lacks
        something and the warehouse has more of the foods in full. Products of
        a favourite brand (brands.json: food to article codes, found in that
        place's saved searches) replace the chosen ones while the food total
        stays within the budget: those costing no more first, then the
        smallest extra cost first. It writes order.json and prints the preview.
verify  compares after.json (the cart read back after adding) with order.json
        and prints the report for the user.

The same files always give the same result.
"""

import argparse
import datetime
import json
import math
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
MENU_TOOLS = SKILL_DIR.parent / "menu" / "scripts" / "menu_tools.py"
PARTS = {"morning": (0, 12), "midday": (12, 15), "afternoon": (15, 18), "evening": (18, 24)}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
OLD_FILES = ("need.json", "slots.json", "slot.json", "choices.json", "brands.json", "before.json", "order.json",
             "after.json")
# where an order ships from: the store skill's field for the branch, and Silpo's delivery type
PLACES = {"home": ("home_branch_id", "DeliveryHome"), "wide": ("wide_branch_id", "WideAssortDelivery")}
VALIDATION_WORDS = {
    "timeslot.not_found": "The delivery time is not available any more.",
    "timeslot.not_available": "The delivery time is not available any more.",
    "order.min_cost": "The order is below Silpo's minimum order.",
    "order.cost.min": "The order is below Silpo's minimum order.",
}


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


# ---------- reading ----------

def cart_folder(project):
    folder = pathlib.Path(project) / "data" / "cart"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def read_json(path, what):
    if not path.exists():
        fail(f"{path.name} is missing: {what}")
    try:
        return json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{path.name} is not valid JSON: {error}")


def read_store(project):
    path = pathlib.Path(project) / "data" / "stores" / "silpo.md"
    if not path.exists():
        fail("data/stores/silpo.md is missing: do the Delivery setup first.")
    fields = {}
    for line in path.read_text("utf-8").splitlines():
        match = re.match(r"^- (\w+): (.*)$", line.strip())
        if match:
            fields.setdefault(match.group(1), match.group(2).strip())
    return fields


def branch_of(store, place):
    value = (store.get(PLACES[place][0]) or "").strip()
    return None if value.lower() in ("", "none") else value


def place_folder(folder, place):
    if place == "home":
        return folder
    inner = folder / place
    inner.mkdir(exist_ok=True)
    return inner


def read_choices(folder):
    path = folder / "choices.json"
    return read_json(path, "") if path.exists() else {}


def as_code(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def walk(value):
    """Every dict inside a tool result, at any depth."""
    if isinstance(value, dict):
        yield value
        for inner in value.values():
            yield from walk(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from walk(inner)


def found_products(folder):
    """Products from all saved search results, by article code."""
    products = {}
    for path in sorted(folder.glob("search-*.json")):
        for item in walk(read_json(path, "a saved search result")):
            if "externalProductId" in item and "id" in item and "price" in item:
                products.setdefault(int(item["externalProductId"]), item)
    return products


def cart_of(raw):
    """The cart object of a saved cart read, and its products."""
    cart = raw.get("cart", raw) if isinstance(raw, dict) else {}
    products = [p for s in cart.get("shipments") or [] for p in s.get("products") or []]
    return cart, products


def links_of(raw):
    links = {}
    for item in walk(raw):
        for key in ("checkoutWebLink", "checkoutMobileLink"):
            if isinstance(item.get(key), str) and item[key]:
                links.setdefault(key, item[key])
    return links


# ---------- time ----------

def utc(text):
    return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def kyiv_zone():
    try:
        from zoneinfo import ZoneInfo
        for name in ("Europe/Kyiv", "Europe/Kiev"):
            try:
                return ZoneInfo(name)
            except Exception:
                continue
    except ImportError:
        pass
    return datetime.timezone(datetime.timedelta(hours=2))


KYIV = kyiv_zone()


def kyiv(text):
    return utc(text).astimezone(KYIV)


def part_of_day(moment):
    for name, (start, end) in PARTS.items():
        if start <= moment.hour < end:
            return name
    return "evening"


def day_words(date, year=False):
    text = f"{WEEKDAYS[date.weekday()]} {date.day} {MONTHS[date.month - 1]}"
    return f"{text} {date.year}" if year else text


def slot_words(start, end):
    a, b = kyiv(start), kyiv(end)
    return f"{day_words(a.date())}, {a:%H:%M} to {b:%H:%M}"


def kyiv_midnight_utc(date):
    return datetime.datetime(date.year, date.month, date.day, tzinfo=KYIV).astimezone(datetime.timezone.utc).isoformat()


# ---------- words ----------

def money(value):
    return f"{value:.2f}"


def whole(value):
    return int(math.floor(value + 0.5))


def amount_words(weighted, quantity, pack=None):
    if weighted:
        grams = quantity * 1000
        return f"{quantity:g} kg" if grams >= 1000 else f"{grams:g} g"
    return f"{quantity:g} x {pack:g} g" if pack else f"{quantity:g}"


def pack_grams(product, food, saved):
    """Grams in one unit of a packaged product, from displayRatio; else from the price list for the same code."""
    match = re.match(r"^\s*([\d.,]+)\s*(кг|г|л|мл|шт)", str(product.get("displayRatio") or ""))
    if match:
        amount = float(match.group(1).replace(",", "."))
        unit = match.group(2)
        if unit in ("кг", "л"):
            return amount * 1000
        if unit in ("г", "мл"):
            return amount
        if food == "egg":
            return amount * 55
    if saved.get("code") == product.get("externalProductId") and saved.get("pack_grams"):
        return saved["pack_grams"]
    return None


def delivery_cost(slot, order_total):
    cost = slot.get("deliveryCost")
    for step in sorted(slot.get("deliveryCostMap") or [], key=lambda s: s.get("fromOrderCost", 0)):
        if order_total >= step.get("fromOrderCost", math.inf):
            cost = step.get("cost", cost)
    return cost


# ---------- commands ----------

def command_need(args):
    folder = cart_folder(args.project)
    store = read_store(args.project)
    done = subprocess.run([sys.executable, str(MENU_TOOLS), "cart-plan", "--project", args.project,
                           "--today", args.today], capture_output=True, text=True)
    if done.returncode:
        fail(done.stderr.strip() or done.stdout.strip())
    need = json.loads(done.stdout)
    for name in OLD_FILES:
        (folder / name).unlink(missing_ok=True)
    for path in folder.glob("search-*.json"):
        path.unlink()
    for place in PLACES:
        if place != "home" and (folder / place).is_dir():
            for path in (folder / place).glob("*.json"):
                path.unlink()
    today = datetime.date.fromisoformat(args.today)
    first = datetime.date.fromisoformat(need["first_day"])
    last = max(first, today + datetime.timedelta(days=2))
    need["made"] = args.today

    def request(place):
        return {"branchId": branch_of(store, place) if place != "home" else store.get("home_branch_id"),
                "deliveryTypes": [PLACES[place][1]], "start": kyiv_midnight_utc(today),
                "end": kyiv_midnight_utc(last + datetime.timedelta(days=1)), "limit": 100}

    need["time_slots"] = request("home")
    if branch_of(store, "wide"):
        need["wide_time_slots"] = request("wide")
    (folder / "need.json").write_text(json.dumps(need, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"foods": len(need["items"]), "time_slots": need["time_slots"]}, ensure_ascii=False, indent=1))


def requests_of(need, place):
    return need.get("time_slots" if place == "home" else f"{place}_time_slots")


def command_slot(args):
    folder = cart_folder(args.project)
    need = read_json(folder / "need.json", "run need first.")
    store = read_store(args.project)
    if args.place != "home" and not requests_of(need, args.place):
        fail("Silpo has no bigger warehouse for this address.")
    here = place_folder(folder, args.place)
    raw = read_json(here / "slots.json", "save the time slot tool's result there first.")
    slots = raw if isinstance(raw, list) else raw.get("slots") or []
    preferred = (store.get("preferred_time") or "evening").split()[0].lower()
    first = datetime.date.fromisoformat(need["first_day"])
    today = datetime.date.fromisoformat(args.today)
    window = (requests_of(need, args.place) or {}).get("start") or kyiv_midnight_utc(today)
    free = sorted((s for s in slots if s.get("available") and s.get("start") and s.get("end")
                   and utc(s["start"]) >= utc(window) and kyiv(s["start"]).date() >= today),
                  key=lambda s: utc(s["start"]))
    if not free:
        fail("Silpo has no free delivery time in the slots that were fetched.")
    eve = first - datetime.timedelta(days=1)
    if args.start:
        chosen = next((s for s in free if utc(s["start"]) == utc(args.start)), None)
        if chosen is None:
            fail(f"No free slot starts at {args.start}. Free: " + "; ".join(slot_words(s["start"], s["end"]) for s in free))
    else:
        chosen = next((s for s in free if kyiv(s["start"]).date() == eve and part_of_day(kyiv(s["start"])) == preferred), None)
        if chosen is None:
            before = [s for s in free if kyiv(s["start"]).date() < first]
            chosen = before[-1] if before else free[0]
    late = kyiv(chosen["start"]).date() >= first
    slot = {key: chosen.get(key) for key in ("start", "end", "deliveryCost", "deliveryCostMap", "minOrderCost", "maxWeight")}
    slot.update(words=slot_words(chosen["start"], chosen["end"]), late=late, menu_started=first <= today,
                asked=bool(args.start), place=args.place)
    (here / "slot.json").write_text(json.dumps(slot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for path in here.glob("search-*.json"):
        path.unlink()
    codes, names = [], []
    plan = plan_of(folder, need, args.place)
    for item in need["items"]:
        kind, value = plan[item["food"]]
        if kind in ("code", "own") and as_code(value):
            codes.append(str(as_code(value)))
        elif kind == "name":
            names.append({"food": item["food"], "search_name": item["search_name"]})
    branch = (requests_of(need, args.place) or {}).get("branchId")
    print(json.dumps({"branchId": branch, "deliveryType": PLACES[args.place][1],
                      "timeslotStart": chosen["start"], "timeslotEnd": chosen["end"], "delivery": slot["words"],
                      "late": late, "code_batches": [codes[i:i + 30] for i in range(0, len(codes), 30)],
                      "name_searches": names}, ensure_ascii=False, indent=1))


def plan_of(folder, need, place):
    """What decides each food's product at a place: ("out", None) left out by the user; ("own", choice)
    a choice made at this place; ("code", code) the product with that article code; ("name", None) a name search.
    At the warehouse, a product chosen at the store is looked for by its code."""
    home = read_choices(folder)
    own = home if place == "home" else read_choices(place_folder(folder, place))
    plan = {}
    for item in need["items"]:
        food = item["food"]
        if home.get(food) == "out":
            plan[food] = ("out", None)
        elif food in own:
            plan[food] = ("own", own[food])
        else:
            code = (as_code(home.get(food)) if place != "home" else None) or as_code(item.get("code"))
            plan[food] = ("code", code) if code else ("name", None)
    return plan


def matches(folder, need, place="home"):
    """Each food's product at a place: by its code, else as chosen in choices.json. None means not available."""
    products = found_products(place_folder(folder, place))
    plan = plan_of(folder, need, place)
    chosen, to_choose, unknown = {}, [], []
    for item in need["items"]:
        food = item["food"]
        kind, value = plan[food]
        if kind == "out":
            chosen[food] = "out"
        elif kind == "own":
            if value is None or value == "out":
                chosen[food] = value
            elif as_code(value) in products:
                chosen[food] = products[as_code(value)]
            else:
                unknown.append(f"{food}: code {value} is in no saved search result")
        else:
            live = products.get(value) if kind == "code" else None
            if live and live.get("available", True) and (live.get("stock") or 0) > 0:
                chosen[food] = live
            else:
                to_choose.append({"food": food, "search_name": item["search_name"], "was": item.get("title"),
                                  "needed_grams": item["needed_grams"]})
    return chosen, to_choose, unknown


def context(args, folder):
    prices_path = pathlib.Path(args.project) / "data" / "prices.json"
    saved_prices = (json.loads(prices_path.read_text("utf-8")).get("foods") or {}) if prices_path.exists() else {}
    before_path = folder / "before.json"
    _, in_cart = cart_of(read_json(before_path, "")) if before_path.exists() else ({}, [])
    return saved_prices, in_cart


def cart_branch(folder):
    """The branch the cart was set to before this order, from before.json."""
    path = folder / "before.json"
    cart, _ = cart_of(read_json(path, "")) if path.exists() else ({}, [])
    return next((s.get("branchId") for s in cart.get("shipments") or [] if s.get("branchId")), None)


def command_match(args):
    folder = cart_folder(args.project)
    need = read_json(folder / "need.json", "run need first.")
    if args.place != "home" and not requests_of(need, args.place):
        fail("Silpo has no bigger warehouse for this address.")
    chosen, to_choose, unknown = matches(folder, need, args.place)
    out = {"found": sum(1 for v in chosen.values() if isinstance(v, dict)),
           "not_available": sorted(f for f, v in chosen.items() if v is None),
           "left_out": sorted(f for f, v in chosen.items() if v == "out"),
           "to_choose": to_choose, "problems": unknown}
    if args.place == "home" and not to_choose and not unknown and requests_of(need, "wide") \
            and not (folder / "wide" / "slots.json").exists() and (folder / "slot.json").exists():
        lacking = order_at(folder, need, "home", *context(args, folder))["lacking"]
        if lacking:
            out["store_lacks"] = lacking
            out["check_warehouse"] = requests_of(need, "wide")
    print(json.dumps(out, ensure_ascii=False, indent=1))


def price_line(item, live, saved_prices):
    """What buying this product for the food takes: amount and cost, and whether the stock covers the menu."""
    food = item["food"]
    name = live.get("name") or live.get("title") or item.get("title") or item["search_name"]
    grams = item["needed_grams"]
    stock = live.get("stock")
    flags = []
    if live.get("weighted"):
        step = live.get("step") or live.get("addToBasketStep") or 0.1
        quantity = round(math.ceil(grams / 1000 / step - 1e-9) * step, 3)
        if isinstance(stock, (int, float)) and stock < quantity:
            flags.append(f"only {stock:g} kg in stock; the menu needs {amount_words(True, quantity)}")
            quantity = round(math.floor(stock / step + 1e-9) * step, 3)
        pack, kilos = None, quantity
    else:
        pack = pack_grams(live, food, saved_prices.get(food) or {})
        if not pack:
            return {"name": name, "status": "pack unknown"}
        quantity = math.ceil(grams / pack - 1e-9)
        if isinstance(stock, (int, float)) and stock < quantity:
            flags.append(f"only {stock:g} in stock; the menu needs {quantity}")
            quantity = int(stock)
        kilos = quantity * pack / 1000
    if quantity <= 0:
        return {"name": name, "status": "none"}
    return {"name": name, "status": "short" if flags else "ok", "quantity": quantity, "kilos": kilos, "flags": flags,
            "amount": amount_words(live.get("weighted"), quantity, pack), "cost": round(quantity * live["price"], 2)}


def order_at(folder, need, place, saved_prices, in_cart, swaps=None):
    """The order if it ships from this place: lines, what to add, what is missing, and how many foods are covered.
    swaps: food to a product of a favourite brand that replaces the chosen one."""
    chosen, to_choose, unknown = matches(folder, need, place)
    if to_choose or unknown:
        where = "" if place == "home" else f" (--place {place})"
        fail(f"Not every food has a product yet. Run match{where} and choose: "
             + "; ".join([t["food"] for t in to_choose] + unknown))
    swaps = swaps or {}
    in_cart_ids = {p.get("productId") for p in in_cart}
    lines, add, missing, left_out, kept_twice, lacking = [], [], [], [], [], []
    total, weight, covered = 0.0, 0.0, 0
    for item in need["items"]:
        food = item["food"]
        live = swaps.get(food) or chosen.get(food)
        label = item.get("title") or item["search_name"]
        if live == "out":
            left_out.append(label)
            continue
        if not live:
            missing.append(label)
            lacking.append(label)
            continue
        line = price_line(item, live, saved_prices)
        if line["status"] in ("pack unknown", "none"):
            missing.append(f"{line['name']} (pack size unknown)" if line["status"] == "pack unknown" else line["name"])
            lacking.append(label)
            continue
        name, flags = line["name"], line["flags"]
        if line["status"] == "short":
            lacking.append(label)
        else:
            covered += 1
        if food in swaps:
            flags.append("your brand")
        elif item.get("code") and live.get("externalProductId") != item["code"]:
            flags.append(f"instead of {item['title']}")
        elif not item.get("code"):
            flags.append("new on the list")
        if live["id"] in in_cart_ids:
            kept_twice.append(f"{name}: already in your cart, not added again (the menu needs {line['amount']})")
            continue
        total += line["cost"]
        weight += line["kilos"]
        lines.append({"food": food, "name": name, "code": live.get("externalProductId"), "amount": line["amount"],
                      "quantity": line["quantity"], "price": live["price"], "cost": line["cost"], "flags": flags})
        add.append({"productId": live["id"], "companyId": live.get("companyId"), "branchId": live.get("branchId"),
                    "quantity": line["quantity"]})
    return {"place": place, "lines": lines, "add": add, "missing": missing, "left_out": left_out,
            "kept_twice": kept_twice, "lacking": lacking, "covered": covered, "total": total, "weight": weight}


def decide_place(folder, need, saved_prices, in_cart):
    """The order from the store, or from the warehouse when the store lacks something and the warehouse has more."""
    best = order_at(folder, need, "home", saved_prices, in_cart)
    if best["lacking"] and requests_of(need, "wide"):
        wide = folder / "wide"
        if not (wide / "slots.json").exists():
            fail("The store does not have everything: " + ", ".join(best["lacking"])
                 + ". Check the warehouse first: run match and follow its check_warehouse.")
        if (wide / "slot.json").exists():
            other = order_at(folder, need, "wide", saved_prices, in_cart)
            if other["covered"] > best["covered"]:
                best = other
    return best


def favourite_brands(project):
    """The user's favourite brands, as (name, only): only is the foods in brackets the brand is meant for, or None.
    "Яготинське (кефір), Галичина" gives [("Яготинське", "кефір"), ("Галичина", None)]."""
    path = pathlib.Path(project) / "data" / "profile.md"
    if not path.exists():
        return []
    for line in path.read_text("utf-8").splitlines():
        match = re.match(r"^- favourite_brands: (.*)$", line.strip())
        if match:
            value = match.group(1).strip()
            if value.lower() in ("", "none", "skipped", "n/a"):
                return []
            brands = []
            for part in re.findall(r"[^,(]+(?:\([^)]*\))?", value):
                name, _, only = part.partition("(")
                if name.strip():
                    brands.append((name.strip(), only.rstrip(") ").strip() or None))
            return brands
    return []


def pinned_foods(project):
    path = pathlib.Path(project) / "data" / "pins.json"
    if not path.exists():
        return set()
    return {p.get("food") for p in (json.loads(path.read_text("utf-8")).get("pins") or []) if p.get("store", "silpo") == "silpo"}


def brand_swaps(args, folder, need, base, saved_prices):
    """Products of the user's favourite brands (brands.json: food to article codes), taken while the food stays
    within the budget: those that cost no more first, then the smallest extra cost first."""
    path = folder / "brands.json"
    if not path.exists() or not favourite_brands(args.project):
        return {}
    wanted = read_json(path, "")
    pinned = pinned_foods(args.project)
    products = found_products(place_folder(folder, base["place"]))
    now = {line["food"]: line for line in base["lines"]}
    items = {i["food"]: i for i in need["items"]}
    options = []
    for food, codes in sorted(wanted.items()):
        if food in pinned or food not in now or food not in items:
            continue
        best = None
        for code in codes if isinstance(codes, list) else [codes]:
            live = products.get(as_code(code))
            if not live or not live.get("available", True) or (live.get("stock") or 0) <= 0 \
                    or live.get("externalProductId") == now[food]["code"]:
                continue
            line = price_line(items[food], live, saved_prices)
            if line["status"] == "ok" and (best is None or line["cost"] < best[0]):
                best = (line["cost"], live)
        if best:
            options.append((round(best[0] - now[food]["cost"], 2), food, best[1]))
    budget = need.get("budget_uah")
    total, swaps = base["total"], {}
    for extra, food, live in sorted(options, key=lambda o: (o[0], o[1])):
        if extra <= 0 or budget is None or total + extra <= budget + 1e-9:
            swaps[food] = live
            total += extra
    return swaps


def command_brands(args):
    folder = cart_folder(args.project)
    need = read_json(folder / "need.json", "run need first.")
    brands = favourite_brands(args.project)
    if not brands:
        print(json.dumps({"brands": []}, ensure_ascii=False, indent=1))
        return
    saved_prices, in_cart = context(args, folder)
    base = decide_place(folder, need, saved_prices, in_cart)
    place = base["place"]
    slot = read_json(place_folder(folder, place) / "slot.json", "run slot first.")
    pinned = pinned_foods(args.project)
    print(json.dumps({"brands": [name for name, _ in brands],
                      "only": {name: only for name, only in brands if only}, "place": place, "branchId": (requests_of(need, place) or {}).get("branchId"),
                      "deliveryType": PLACES[place][1], "timeslotStart": slot["start"], "timeslotEnd": slot["end"],
                      "foods": [{"food": line["food"], "now": line["name"]} for line in base["lines"]
                                if line["food"] not in pinned]}, ensure_ascii=False, indent=1))


def command_price(args):
    folder = cart_folder(args.project)
    need = read_json(folder / "need.json", "run need first.")
    store = read_store(args.project)
    saved_prices, in_cart = context(args, folder)
    best = decide_place(folder, need, saved_prices, in_cart)
    swaps = brand_swaps(args, folder, need, best, saved_prices)
    if swaps:
        best = order_at(folder, need, best["place"], saved_prices, in_cart, swaps)
    place = best["place"]
    slot = read_json(place_folder(folder, place) / "slot.json", "run slot first.")
    lines, add, missing, left_out, kept_twice = (best[k] for k in ("lines", "add", "missing", "left_out", "kept_twice"))
    total, weight = best["total"], best["weight"]

    kept = [{"productId": p.get("productId"), "name": p.get("name"), "quantity": p.get("quantity"),
             "weighted": p.get("weighted"), "total": p.get("total") or 0} for p in in_cart]
    kept_total = sum(k["total"] for k in kept)
    delivery = delivery_cost(slot, total + kept_total)
    budget = need.get("budget_uah")
    branch = (requests_of(need, place) or {}).get("branchId") or branch_of(store, place)
    order = {"made": args.today, "first_day": need["first_day"], "days": need["days"],
             "place": place, "branch_id": branch, "delivery_type": PLACES[place][1],
             "slot": {"start": slot["start"], "end": slot["end"], "words": slot["words"]},
             "add": add, "lines": lines, "missing": missing, "left_out": left_out, "kept": kept, "menu_total": round(total, 2),
             "budget_uah": budget, "delivery_cost": delivery, "weight_kg": round(weight + sum(
                 (k["quantity"] or 0) for k in kept if k.get("weighted")), 1)}
    (folder / "order.json").write_text(json.dumps(order, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    first = datetime.date.fromisoformat(need["first_day"])
    out = [f"Silpo order for the menu: {need['days']} days from {day_words(first, year=True)}",
           f"Delivery: {slot['words']}"]
    if place == "wide":
        out.append("  From the bigger Silpo warehouse: the store does not have everything on the list.")
    if slot.get("menu_started") and not slot.get("asked"):
        out.append("  The menu has already started; this is the first free delivery time.")
    elif slot.get("late") and slot.get("asked"):
        out.append("  This delivery comes after the menu starts.")
    elif slot.get("late"):
        out.append("  This delivery comes after the menu starts: no earlier time is free.")
    out.append("")
    for line in sorted(lines, key=lambda x: -x["cost"]):
        extra = f" ({'; '.join(line['flags'])})" if line["flags"] else ""
        out.append(f"  {line['name']}: {line['amount']}, {money(line['cost'])} UAH{extra}")
    out += ["", f"Food for the menu: {whole(total)} UAH" + (f" (budget {budget} UAH)" if budget else "")]
    if budget and total > budget:
        out.append(f"Over the budget by {whole(total - budget)} UAH.")
    if delivery is not None:
        out.append(f"Delivery cost: {delivery:g} UAH")
    if slot.get("minOrderCost") and total + kept_total < slot["minOrderCost"]:
        out.append(f"Below Silpo's minimum order of {slot['minOrderCost']:g} UAH.")
    if slot.get("maxWeight") and order["weight_kg"] > slot["maxWeight"]:
        out.append(f"About {order['weight_kg']:g} kg: more than Silpo delivers at once ({slot['maxWeight']:g} kg).")
    if missing:
        out += ["", "Not at the store, not ordered"] + [f"  {m}" for m in missing]
    if left_out:
        out += ["", "Left out, as you asked"] + [f"  {m}" for m in left_out]
    if kept_twice:
        out += [""] + kept_twice
    if kept:
        out += ["", f"Already in your cart, kept as they are: {money(kept_total)} UAH"]
        out += [f"  {k['name']}: {amount_words(k.get('weighted'), k['quantity'] or 0)}" for k in kept]
        if cart_branch(folder) not in (None, branch):
            out.append("  They were put in at the regular store; the bigger warehouse may not have all of them."
                       if place == "wide" else
                       "  They were put in at the bigger warehouse; the regular store may not have all of them.")
        out.append(f"Whole cart with the menu's food: {whole(total + kept_total)} UAH")
    if need.get("from_home"):
        out += ["", "From home, not bought"] + [f"  {h['name']}: {h['grams']} g" for h in need["from_home"]]
    print("\n".join(out))


def command_verify(args):
    folder = cart_folder(args.project)
    order = read_json(folder / "order.json", "run price first.")
    raw = read_json(folder / "after.json", "save the cart read after adding there first.")
    cart, products = cart_of(raw)
    present = {p.get("productId"): p for p in products}
    validations = ((cart.get("calculation") or {}).get("validations")) or []
    errors = [v for v in validations if v.get("level") == "error"]
    by_product = {}
    other = []
    for v in errors:
        context = v.get("context") if isinstance(v.get("context"), dict) else {}
        if context.get("productId"):
            by_product[context["productId"]] = v
        else:
            other.append(v)
    names = {a["productId"]: line["name"] for a, line in zip(order["add"], order["lines"])}

    added, not_added, short, changed = 0, [], [], []
    for want, line in zip(order["add"], order["lines"]):
        got = present.get(want["productId"])
        if not got:
            not_added.append(line["name"])
            continue
        added += 1
        problem = by_product.get(want["productId"])
        if problem:
            stock = (problem.get("context") or {}).get("stock")
            if isinstance(stock, (int, float)):
                short.append(f"{line['name']}: out of stock" if stock <= 0 else f"{line['name']}: only {stock:g} in stock")
            else:
                short.append(f"{line['name']}: {problem.get('message')}")
        elif abs((got.get("quantity") or 0) - want["quantity"]) > 1e-6:
            changed.append(f"{line['name']}: {got.get('quantity'):g} instead of {want['quantity']:g}")
    earlier = [names.get(pid) or (present.get(pid) or {}).get("name") or pid
               for pid in by_product if pid not in {a["productId"] for a in order["add"]}]

    out = ["Your Silpo cart", f"  Added: {added} of {len(order['add'])} products"]
    if not_added:
        out.append(f"  Not added: {', '.join(not_added)}")
    if short:
        out += ["  Not enough in stock:"] + [f"    {s}" for s in short]
    if changed:
        out += ["  Amount changed by Silpo:"] + [f"    {c}" for c in changed]
    if earlier:
        out.append(f"  Your earlier items Silpo cannot deliver now: {', '.join(earlier)}."
                   " Remove them in the Silpo app or on silpo.ua before paying.")
    timeslot = cart.get("timeslot") or {}
    if timeslot.get("start") and timeslot.get("end"):
        out.append(f"  Delivery: {slot_words(timeslot['start'], timeslot['end'])}")
        if utc(timeslot["start"]) != utc(order["slot"]["start"]):
            out.append(f"  This is not the delivery time agreed ({order['slot']['words']}).")
    for v in other:
        out.append(f"  Silpo reports: {VALIDATION_WORDS.get(v.get('message'), v.get('message'))}")
    calc = cart.get("calculation") or {}
    if isinstance(calc.get("totalAfterDiscounts"), (int, float)):
        delivery = (calc.get("delivery") or {}).get("total")
        extra = f", delivery {delivery:g} UAH included" if isinstance(delivery, (int, float)) else ""
        out.append(f"  To pay: {money(calc['totalAfterDiscounts'])} UAH{extra}")
    links = links_of(raw)
    if links:
        if links.get("checkoutWebLink"):
            out.append(f"  Pay on the site: {links['checkoutWebLink']}")
        if links.get("checkoutMobileLink"):
            out.append(f"  Pay in the app: {links['checkoutMobileLink']}")
    else:
        out.append("  To pay, open your cart in the Silpo app or on silpo.ua.")
    print("\n".join(out))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Silpo cart tools for the shopper project.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("need", "slot", "match", "brands", "price", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--today", default=datetime.date.today().isoformat())
        if name == "slot":
            p.add_argument("--start")
        if name in ("slot", "match"):
            p.add_argument("--place", choices=sorted(PLACES), default="home")
    args = parser.parse_args(argv)
    {"need": command_need, "slot": command_slot, "match": command_match, "brands": command_brands,
     "price": command_price, "verify": command_verify}[args.command](args)


if __name__ == "__main__":
    main()
