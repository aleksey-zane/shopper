#!/usr/bin/env python3
"""Calculate daily diet targets from a shopper profile and write diet.md.

Usage:
    python3 targets.py --profile data/profile.md --out data/diet.md
                       [--today YYYY-MM-DD] [--base N=pattern ...]
    python3 targets.py --profile data/profile.md --out data/diet.md --check

The same profile always gives the same diet file. --check only says whether
the diet file still matches the profile ("fresh", exit 0) or not ("stale",
exit 1). The method is described in method.md next to the skill.
"""
import argparse
import datetime
import hashlib
import json
import math
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
EMPTY = {"", "skipped", "none", "n/a"}

# Sources are listed in method.md. FAO/WHO/UNU 2004 = "Human energy requirements".
# Physical activity level (PAL), FAO/WHO/UNU 2004, section 5.3 and Tables 5.1, 5.3:
# 1.40 is the lowest PAL of the sedentary or light band, 1.55 the sedentary
# lifestyle, 1.75 one hour of moderate to vigorous exercise a day, 2.25 the
# vigorous example.
ACTIVITY = {"sedentary": 1.40, "light": 1.55, "moderate": 1.75, "active": 2.25}
# Children from 6 years: light activity 15% below moderate, vigorous 15% above
# (FAO/WHO/UNU 2004, section 4.4.3). Under 6 the moderate value is used.
CHILD_ACTIVITY = {"sedentary": 0.85, "light": 0.85, "moderate": 1.0, "active": 1.15}
CHILD_ACTIVITY_FROM_AGE = 6
# No source: kept as the plan's own choice.
GOAL = {
    ("lose", "slow"): -300,
    ("lose", "moderate"): -500,
    ("gain", "slow"): 250,
    ("gain", "moderate"): 500,
}
# No source (FAO/WHO/UNU 2004 defines no minimum): a safety floor.
FLOOR = {"male": 1500, "female": 1200, None: 1350}
# Median BMI 21.0 of the joint WHO/FAO consultation (FAO/WHO/UNU 2004, 5.4.2).
HEALTHY_BMI = 21.0
# No source: used only when the height is not given.
REF_HEIGHT = {"male": 176.0, "female": 163.0, None: 170.0}
# Mifflin-St Jeor 1990; the -78 when sex is not given is the midpoint.
BMR_SEX = {"male": 5, "female": -161, None: -78}
# kcal a day at moderate activity, by year of age (FAO/WHO/UNU 2004, Tables 4.5
# and 4.6): age -> (boys, girls). Age 1 is the row "1-2 years".
CHILD_KCAL = {
    1: (950, 850), 2: (1125, 1050), 3: (1250, 1150), 4: (1350, 1250),
    5: (1475, 1325), 6: (1575, 1425), 7: (1700, 1550), 8: (1825, 1700),
    9: (1975, 1850), 10: (2150, 2000), 11: (2350, 2150), 12: (2550, 2275),
    13: (2775, 2375), 14: (3000, 2450), 15: (3175, 2500), 16: (3325, 2500),
    17: (3400, 2500),
}
# Fibre, adequate intake (EFSA 2017 summary report, section 3.2): 25 g a day
# for adults; children 2 g per MJ, by age group: (first age, last age, grams).
ADULT_FIBRE = 25
CHILD_FIBRE = [(1, 3, 10), (4, 6, 14), (7, 10, 16), (11, 14, 19), (15, 17, 21)]
# No source: the plan's own split of the day.
MEAL_SHARE = {"breakfast": 25, "lunch": 35, "dinner": 30, "snacks": 10}
MAIN_MEALS = ("breakfast", "lunch", "dinner")
PLACEHOLDER = "to be written by the dietitian"
# The profile fields the targets depend on. A change in any of them, or a new
# calendar year, makes the diet file stale.
USED_FIELDS = (
    "label", "birth_year", "sex", "height_cm", "weight_kg", "activity",
    "meals_at_home", "goal", "goal_pace", "way_of_eating", "calories_override",
)


def half_up(value, step):
    """Round to the nearest multiple of step, halves upward."""
    return int(math.floor(value / step + 0.5) * step)


def fibre(age):
    for first, last, grams in CHILD_FIBRE:
        if first <= age <= last:
            return grams
    return ADULT_FIBRE


def parse_profile(text):
    top, eaters, current = {}, [], None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            name = heading.group(1).strip()
            current = None
            if re.match(r"^Eater\s+\d+$", name):
                current = {}
                eaters.append(current)
            elif name != "Profile":
                current = {"_other": True}
            continue
        field = re.match(r"^-\s+([a-z_]+):\s*(.*)$", line)
        if not field:
            continue
        key, value = field.group(1), field.group(2).strip()
        if current is None:
            top[key] = value
        elif "_other" not in current:
            current[key] = value
    return top, eaters


def fingerprint(eaters, year):
    parts = [str(year)]
    for eater in eaters:
        parts.append("|".join((eater.get(key) or "").strip().lower() for key in USED_FIELDS))
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def number(value):
    if value is None or value.strip().lower() in EMPTY:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def word(value):
    if value is None or value.strip().lower() in EMPTY:
        return None
    return value.strip()


def normal(name):
    return re.sub(r"[\s_]+", "-", name.strip().lower())


def find_pattern(name, patterns, aliases):
    if name is None:
        return None
    wanted = normal(name)
    wanted = aliases.get(wanted, wanted)
    for key in patterns:
        if normal(key) == normal(wanted):
            return key
    return None


def calculate(eater, index, year, patterns, aliases, bases, remembered):
    label = word(eater.get("label")) or f"Eater {index}"
    notes = []
    result = {"label": label}

    birth_year = number(eater.get("birth_year"))
    if birth_year is None:
        raise SystemExit(f"Eater {index} ({label}): birth_year is missing in the profile.")
    age = year - int(birth_year)
    result["age"] = age

    way = word(eater.get("way_of_eating"))
    if way is None:
        raise SystemExit(f"Eater {index} ({label}): way_of_eating is missing in the profile.")
    pattern = find_pattern(way, patterns, aliases)
    if pattern is None:
        base = find_pattern(bases.get(index), patterns, aliases) or find_pattern(
            remembered.get((label, way)), patterns, aliases
        )
        if base is None:
            raise SystemExit(
                f'Eater {index} ({label}): way of eating "{way}" is not on the list. '
                f"Run again with --base {index}=<one of: {', '.join(patterns)}>."
            )
        pattern = base
        result["custom"] = True
    result["way_of_eating"] = way
    result["based_on"] = pattern

    if age < 1:
        result["skipped"] = "under 1 year old: not planned"
        return result

    sex = word(eater.get("sex"))
    sex = sex.lower() if sex and sex.lower() in ("male", "female") else None
    activity = (word(eater.get("activity")) or "light").lower()
    if activity not in ACTIVITY:
        activity = "light"

    split_pattern = pattern
    if age < 18:
        boys, girls = CHILD_KCAL[age]
        base_kcal = {"male": boys, "female": girls, None: (boys + girls) / 2}[sex]
        factor = CHILD_ACTIVITY[activity] if age >= CHILD_ACTIVITY_FROM_AGE else 1.0
        calories = base_kcal * factor
        basis = "reference for age"
        result["weight_used_kg"] = None
        result["weight_basis"] = "not used under 18"
        result["height_used_cm"] = None
        result["height_basis"] = "not used under 18"
        goal = word(eater.get("goal"))
        if goal and goal.lower() != "maintain":
            notes.append("weight goal not applied under 18")
        if patterns[pattern].get("adults_only_shares"):
            split_pattern = "balanced"
            notes.append("balanced shares of protein, fat and carbohydrates used under 18")
    else:
        height = number(eater.get("height_cm"))
        if height is None:
            height = REF_HEIGHT[sex]
            result["height_basis"] = "typical for age and sex"
        else:
            result["height_basis"] = "measured"
        weight = number(eater.get("weight_kg"))
        if weight is None:
            weight = round(HEALTHY_BMI * (height / 100) ** 2, 1)
            result["weight_basis"] = (
                "healthy weight for height"
                if result["height_basis"] == "measured"
                else "typical for age and sex"
            )
        else:
            result["weight_basis"] = "measured"
        result["weight_used_kg"] = weight
        result["height_used_cm"] = height

        bmr = 10 * weight + 6.25 * height - 5 * age + BMR_SEX[sex]
        calories = bmr * ACTIVITY[activity]
        goal = (word(eater.get("goal")) or "maintain").lower()
        pace = (word(eater.get("goal_pace")) or "slow").lower()
        calories += GOAL.get((goal, pace), 0)
        basis = "calculated"

    override = number(eater.get("calories_override"))
    if override is not None:
        calories = override
        basis = "set by user"

    if age >= 18 and calories < FLOOR[sex]:
        calories = FLOOR[sex]
        basis = "minimum safe level"
        notes.append("raised to the minimum safe level")

    if patterns[pattern].get("note"):
        notes.append(patterns[pattern]["note"])

    calories = half_up(calories, 50)
    shares = patterns[split_pattern]
    fat_kcal = calories * shares["fat_pct"] / 100
    if "protein_g_per_kg" in shares:
        # grams per kg of body weight, at most a share of the calories; carbohydrates are the rest
        protein_kcal = min(result["weight_used_kg"] * shares["protein_g_per_kg"] * 4,
                           calories * shares["protein_max_pct"] / 100)
        carbs_kcal = calories - protein_kcal - fat_kcal
    else:
        protein_kcal = calories * shares["protein_pct"] / 100
        carbs_kcal = calories * shares["carbs_pct"] / 100
    result.update(
        calories_kcal=calories,
        calories_basis=basis,
        protein_g=half_up(protein_kcal / 4, 5),
        fat_g=half_up(fat_kcal / 9, 5),
        carbs_g=half_up(carbs_kcal / 4, 5),
        fibre_g=fibre(age),
    )

    chosen = [m.strip().lower() for m in (word(eater.get("meals_at_home")) or "").split(",")]
    chosen = [m for m in chosen if m in MEAL_SHARE]
    if not chosen:
        chosen = list(MAIN_MEALS)
    share = dict(MEAL_SHARE)
    if "snacks" not in chosen:
        for meal in MAIN_MEALS:
            share[meal] += MEAL_SHARE["snacks"] * MEAL_SHARE[meal] / 90
        share["snacks"] = 0
    outside = 0
    for meal in ("breakfast", "lunch", "dinner", "snacks"):
        kcal = half_up(calories * share[meal] / 100, 10)
        if meal in chosen:
            result[f"{meal}_kcal"] = kcal
        else:
            result[f"{meal}_kcal"] = 0
            outside += kcal
    result["outside_plan_kcal"] = outside
    result["notes"] = notes
    result["rules"] = patterns[pattern]["rules"]
    return result


def read_existing(text):
    """What an existing diet file remembers, keyed by (label, way of eating)."""
    bases, extra = {}, {}
    for section in re.split(r"^## Eater \d+$", text, flags=re.M)[1:]:
        found = dict(re.findall(r"^- ([a-z_]+): (.*)$", section, flags=re.M))
        key = (found.get("label"), found.get("way_of_eating"))
        if found.get("based_on"):
            bases[key] = found["based_on"]
        match = re.search(r"^### Extra rules\n\n((?:- .*\n?)+)", section, flags=re.M)
        if match:
            rules = [line[2:].strip() for line in match.group(1).splitlines()]
            rules = [rule for rule in rules if rule and rule != PLACEHOLDER]
            if rules:
                extra[key] = rules
    stamp = re.search(r"^- profile_fingerprint: (\S+)$", text, flags=re.M)
    return bases, extra, stamp.group(1) if stamp else None


def fmt(value):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def render(top, results, today, stamp):
    lines = [
        "# Diet",
        "",
        f"- calculated: {today}",
        f"- profile_updated: {top.get('updated', 'unknown')}",
        f"- profile_fingerprint: {stamp}",
        "",
    ]
    for index, r in enumerate(results, start=1):
        lines += [f"## Eater {index}", "", f"- label: {r['label']}", f"- age: {r['age']}"]
        lines += [f"- way_of_eating: {r['way_of_eating']}", f"- based_on: {r['based_on']}"]
        if "skipped" in r:
            lines += [f"- notes: {r['skipped']}", ""]
            continue
        for key in (
            "weight_used_kg", "weight_basis", "height_used_cm", "height_basis",
            "calories_kcal", "calories_basis", "protein_g", "fat_g", "carbs_g", "fibre_g",
            "breakfast_kcal", "lunch_kcal", "dinner_kcal", "snacks_kcal", "outside_plan_kcal",
        ):
            lines.append(f"- {key}: {fmt(r[key])}")
        lines.append(f"- notes: {'; '.join(r['notes']) if r['notes'] else 'none'}")
        lines += ["", "### Weekly rules", ""]
        lines += [f"- {rule}" for rule in r["rules"]]
        if r.get("custom"):
            extra = r.get("extra_rules") or [PLACEHOLDER]
            lines += ["", "### Extra rules", ""]
            lines += [f"- {rule}" for rule in extra]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--today", default=datetime.date.today().isoformat())
    parser.add_argument("--base", action="append", default=[], metavar="N=pattern")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    patterns = json.loads((SKILL_DIR / "patterns.json").read_text(encoding="utf-8"))
    aliases = patterns.pop("_aliases", {})
    bases = {}
    for item in args.base:
        eater_no, _, name = item.partition("=")
        bases[int(eater_no)] = name.strip()

    profile_path = pathlib.Path(args.profile)
    if not profile_path.exists():
        raise SystemExit(f"Profile not found: {profile_path}")
    top, eaters = parse_profile(profile_path.read_text(encoding="utf-8"))
    if not eaters:
        raise SystemExit("The profile has no eaters.")

    year = int(args.today[:4])
    stamp = fingerprint(eaters, year)
    out_path = pathlib.Path(args.out)
    remembered, kept, old_stamp = ({}, {}, None)
    if out_path.exists():
        remembered, kept, old_stamp = read_existing(out_path.read_text(encoding="utf-8"))

    if args.check:
        if not out_path.exists():
            print("stale: there is no diet file")
            sys.exit(1)
        if old_stamp != stamp:
            print("stale: the profile changed after the diet was calculated")
            sys.exit(1)
        print("fresh")
        return

    results = [
        calculate(e, i, year, patterns, aliases, bases, remembered)
        for i, e in enumerate(eaters, start=1)
    ]
    for r in results:
        if r.get("custom"):
            r["extra_rules"] = kept.get((r["label"], r["way_of_eating"]))
    out_path.write_text(render(top, results, args.today, stamp), encoding="utf-8")
    summary = [
        {
            **{k: r.get(k) for k in ("label", "way_of_eating", "based_on", "calories_kcal", "calories_basis")},
            "extra_rules_needed": bool(r.get("custom")) and not r.get("extra_rules"),
        }
        for r in results
    ]
    print(json.dumps({"written": str(args.out), "eaters": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
