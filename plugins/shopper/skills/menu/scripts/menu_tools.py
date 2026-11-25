#!/usr/bin/env python3
"""Menu tools for the shopper project.

    python3 menu_tools.py check --project <shopper folder>
                                [--judged-ok] [--add-fix TEXT] [--add-improve TEXT]
    python3 menu_tools.py show  --project <shopper folder> [--which draft|menu]
                                [--day YYYY-MM-DD] [--recipe <dish id or name>]
    python3 menu_tools.py save  --project <shopper folder> [--accept-problems]
    python3 menu_tools.py prices-needed --project <shopper folder> [--all] [--limit N]
    python3 menu_tools.py buy-list --project <shopper folder> [--which draft|menu]
    python3 menu_tools.py page --project <shopper folder> [--which draft|menu] [--out FILE]
    python3 menu_tools.py cart-plan --project <shopper folder>

check  sizes every portion to the eater's calorie target, adds up the nutrition
       and checks the draft against the profile and the diet. It writes
       data/menu/draft-check.json and prints the result. Lines it cannot
       decide are listed under "judge"; after reading the menu, run check
       again with --judged-ok, adding what was found with --add-fix or
       --add-improve.
show   prints the menu, one day, or one recipe in plain words.
save   makes the checked draft the saved menu.
buy-list  prints what has to be bought for the menu: products, amounts, cost.
page   writes the menu as one web page (data/menu/<which>.html): the days, each
       dish a link to its recipe with grams and steps.
cart-plan  prints, as JSON, what the saved menu needs bought, for the store skill
       to order: each food with its product code and grams, and the budget.
prices-needed  lists the foods whose price the store skill has to look up:
       foods of the draft with no price yet, and prices older than a week.
       With --all, every food of the food table that has no price yet.

The same files always give the same result.
"""
import argparse
import datetime
import hashlib
import html
import json
import math
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
MEALS = ("breakfast", "lunch", "dinner", "snacks")
EMPTY = {"", "none", "skipped", "n/a"}
MIN_PORTION, MAX_PORTION = 0.6, 1.8
KCAL_TOLERANCE = 0.10
PROTEIN_SHARE = 0.90
RECENT_DAYS = 14
PERIOD_DAYS = {"week": 7, "2 weeks": 14, "month": 30}
FREE_FOODS = {"water", "spices"}
DEFAULT_STEP_GRAMS = 100
PRICE_MAX_AGE_DAYS = 7
# The largest amount of a food, or of a soup, on one plate: twice the reference amount per eating occasion (portions.json).
PORTIONS = json.loads((SKILL_DIR / "portions.json").read_text("utf-8"))
PLATE_MAX = {food: grams * PORTIONS["max_share"] for food, grams in PORTIONS["foods"].items()}
SOUP_MAX = PORTIONS["soup_g"] * PORTIONS["max_share"]
SOUP_WORDS = re.compile(r"\b(борщ|суп|щи\b|уха\b|юшка|рассольник|розсольник|солянка|капустняк|бульон|бульйон|soup|broth|borscht)", re.I)
COOKED_KEEPS_DAYS = 2  # a cooked food at home has to be eaten in the first days of the menu
# Foods that count towards WHO's "at least 400 g of fruits and vegetables a day";
# potatoes and other starchy roots are in "starchy" and do not count.
FRUIT_VEG = {"vegetables", "fruit", "berries"}
LEFTOVER_DAYS = {"no": -1, "next day": 1, "up to 3 days": 3}
# Grams of a food group in one sized portion for the meal to count as having it.
THRESHOLD = {
    "vegetables": 70, "fruit": 70, "berries": 40, "fish": 60, "fatty_fish": 60,
    "red_meat": 50, "poultry": 50, "processed_meat": 15, "legumes": 30,
    "plant_protein": 30, "protein_food": 40, "whole_grain": 25, "grains": 25,
    "starchy": 40, "nuts_seeds": 10, "healthy_fat": 8, "olive_oil": 5,
    "sweets": 10, "sugar": 10, "sweet_drink": 100, "juice": 100, "eggs": 40,
    "dairy": 30, "honey": 5, "spicy": 1, "b12_fortified": 100,
}
GROUP_WORDS = {
    "vegetables": "vegetables", "fruit": "fruit", "berries": "berries", "fish": "fish or seafood",
    "fruit_veg": "vegetables and fruit", "fatty_fish": "fatty fish", "red_meat": "red meat", "poultry": "poultry",
    "processed_meat": "processed meat", "legumes": "beans, lentils or chickpeas",
    "plant_protein": "a plant protein", "protein_food": "a protein food",
    "whole_grain": "whole grains", "grains": "grain foods", "starchy": "starchy food",
    "nuts_seeds": "nuts or seeds", "healthy_fat": "nuts, seeds, olive oil or avocado",
    "olive_oil": "olive oil", "sweets": "sweets", "sugar": "sugar", "sweet_drink": "sweet drinks",
    "juice": "juice", "eggs": "eggs", "dairy": "dairy", "honey": "honey",
    "b12_fortified": "a food with added vitamin B12",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

PHRASES_UK = {
    "g": "г", "ml": "мл", "to taste": "за смаком", "eaten out": "поза домом", "no cooking": "без готування",
    "leftover": "залишки", "from {day}": "{day}", "leftover from {day}": "залишки {day}", "{n} min": "{n} хв",
    "cook, {n} min": "готувати, {n} хв", ", for {names}": ", для {names}", " and ": " і ",
    "{share} of what is cooked: ": "{share} приготованого: ",
    "{label}: {kcal} of {target} kcal, protein {protein} of {protein_target} g":
        "{label}: {kcal} з {target} ккал, білок {protein} з {protein_target} г",
    "Cooking: {minutes} min hands-on (limit {limit})": "Готування: {minutes} хв біля плити (ліміт {limit})",
    "Food eaten: {cost} UAH": "Зʼїдено продуктів на: {cost} грн",
    "Draft menu": "Чернетка меню", "Menu": "Меню",
    "{kind} for {days}: {first} to {last}": "{kind} на {days}: {first} — {last}",
    "Cost": "Вартість", "  To buy: {buy} UAH{budget}": "  Купити: {buy} грн{budget}",
    " (budget {cap} UAH for {days})": " (бюджет {cap} грн на {days})",
    "  Of that, eaten in these days: {eaten} UAH; left over for later: {left} UAH":
        "  З цього зʼїдається за ці дні: {eaten} грн; лишається на потім: {left} грн",
    "  Prices: {store}, {date}": "  Ціни: {store}, {date}", "store": "магазин", "date unknown": "дата невідома",
    "  From home, not bought: {home}": "  З дому, не купується: {home}",
    "Check": "Перевірка", "  No problems found.": "  Проблем не знайдено.", "To fix": "Виправити",
    "To improve": "Покращити", "To judge by reading": "Оцінити, прочитавши меню",
    "  This dish is not on the menu.": "  Цієї страви немає в меню.",
    "  Cooked on: {day}": "  Готується: {day}", "  Hands-on time: {n} min": "  Біля плити: {n} хв",
    "  Ready in: {n} min": "  Готово через: {n} хв", "  Equipment: {items}": "  Техніка: {items}",
    "  Ingredients (for everything cooked this time, {portions})": "  Інгредієнти (на все, що готується цього разу, {portions})",
    "  Servings": "  Порції", "  Steps": "  Кроки", "{day} {meal}: {who}{portion}": "{day}, {meal}: {who}{portion}",
    "Buy list for {kind}: {days} from {first}": "Список покупок для {kind}: {days}, початок — {first}",
    "the draft menu": "чернетки меню", "the menu": "меню",
    "Total: {buy} UAH{budget}": "Разом: {buy} грн{budget}", " (budget {cap} UAH)": " (бюджет {cap} грн)",
    "Prices: {store}, {date}": "Ціни: {store}, {date}",
    "Not on the list, no price known: {names}": "Немає в списку, ціна невідома: {names}",
    "From home, not bought": "З дому, не купується", "{cost} UAH": "{cost} грн",
    "{days} days": "{days}", "{name}: {kcal} kcal, protein {protein} g a day": "{name}: {kcal} ккал, білок {protein} г на день",
    "To buy: {buy}{budget}": "Купити: {buy}{budget}", " of {cap} budget": " з бюджету {cap}",
    "Click a dish to open its recipe.": "Натисніть на страву, щоб відкрити рецепт.", "Days": "Дні", "Recipes": "Рецепти",
    "{label}: {kcal} kcal, protein {protein} g": "{label}: {kcal} ккал, білок {protein} г",
    "cooking {n} min": "готування {n} хв", "Cooked {day}": "Готується {day}", "{n} min hands-on": "{n} хв біля плити",
    "ready in {n} min": "готово через {n} хв", "Ingredients": "Інгредієнти", "Eaten": "Коли їсти", "Steps": "Кроки",
    "Back to the week": "Назад до тижня",
}

PHRASES_RU = {
    "g": "г", "ml": "мл", "to taste": "по вкусу", "eaten out": "вне дома", "no cooking": "без готовки",
    "leftover": "остатки", "from {day}": "{day}", "leftover from {day}": "остатки {day}", "{n} min": "{n} мин",
    "cook, {n} min": "готовить, {n} мин", ", for {names}": ", для {names}", " and ": " и ",
    "{share} of what is cooked: ": "{share} приготовленного: ",
    "{label}: {kcal} of {target} kcal, protein {protein} of {protein_target} g":
        "{label}: {kcal} из {target} ккал, белок {protein} из {protein_target} г",
    "Cooking: {minutes} min hands-on (limit {limit})": "Готовка: {minutes} мин у плиты (лимит {limit})",
    "Food eaten: {cost} UAH": "Съедено продуктов на: {cost} грн",
    "Draft menu": "Черновик меню", "Menu": "Меню",
    "{kind} for {days}: {first} to {last}": "{kind} на {days}: {first} — {last}",
    "Cost": "Стоимость", "  To buy: {buy} UAH{budget}": "  Купить: {buy} грн{budget}",
    " (budget {cap} UAH for {days})": " (бюджет {cap} грн на {days})",
    "  Of that, eaten in these days: {eaten} UAH; left over for later: {left} UAH":
        "  Из этого съедается за эти дни: {eaten} грн; остаётся на потом: {left} грн",
    "  Prices: {store}, {date}": "  Цены: {store}, {date}", "store": "магазин", "date unknown": "дата неизвестна",
    "  From home, not bought: {home}": "  Из дома, не покупается: {home}",
    "Check": "Проверка", "  No problems found.": "  Проблем не найдено.", "To fix": "Исправить",
    "To improve": "Улучшить", "To judge by reading": "Оценить, прочитав меню",
    "  This dish is not on the menu.": "  Этого блюда нет в меню.",
    "  Cooked on: {day}": "  Готовится: {day}", "  Hands-on time: {n} min": "  У плиты: {n} мин",
    "  Ready in: {n} min": "  Готово через: {n} мин", "  Equipment: {items}": "  Техника: {items}",
    "  Ingredients (for everything cooked this time, {portions})": "  Ингредиенты (на всё, что готовится в этот раз, {portions})",
    "  Servings": "  Порции", "  Steps": "  Шаги", "{day} {meal}: {who}{portion}": "{day}, {meal}: {who}{portion}",
    "Buy list for {kind}: {days} from {first}": "Список покупок для {kind}: {days}, начало — {first}",
    "the draft menu": "черновика меню", "the menu": "меню",
    "Total: {buy} UAH{budget}": "Итого: {buy} грн{budget}", " (budget {cap} UAH)": " (бюджет {cap} грн)",
    "Prices: {store}, {date}": "Цены: {store}, {date}",
    "Not on the list, no price known: {names}": "Нет в списке, цена неизвестна: {names}",
    "From home, not bought": "Из дома, не покупается", "{cost} UAH": "{cost} грн",
    "{days} days": "{days}", "{name}: {kcal} kcal, protein {protein} g a day": "{name}: {kcal} ккал, белок {protein} г в день",
    "To buy: {buy}{budget}": "Купить: {buy}{budget}", " of {cap} budget": " из бюджета {cap}",
    "Click a dish to open its recipe.": "Нажмите на блюдо, чтобы открыть рецепт.", "Days": "Дни", "Recipes": "Рецепты",
    "{label}: {kcal} kcal, protein {protein} g": "{label}: {kcal} ккал, белок {protein} г",
    "cooking {n} min": "готовка {n} мин", "Cooked {day}": "Готовится {day}", "{n} min hands-on": "{n} мин у плиты",
    "ready in {n} min": "готово через {n} мин", "Ingredients": "Ингредиенты", "Eaten": "Когда есть", "Steps": "Шаги",
    "Back to the week": "Назад к неделе",
}

# What the user reads is written in the menu's language. Lines of the check stay in English:
# they are for the chef and the dietitian. Word forms for counts are (one, two to four, five and more,
# a part of one), the same pattern in Ukrainian and Russian.
LANGS = {
    "uk": {
        "months": ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня",
                   "вересня", "жовтня", "листопада", "грудня"],
        "short_months": ["січ", "лют", "бер", "кві", "тра", "чер", "лип", "сер", "вер", "жов", "лис", "гру"],
        "weekdays": ["понеділок", "вівторок", "середа", "четвер", "пʼятниця", "субота", "неділя"],
        "weekdays_from": ["з понеділка", "з вівторка", "з середи", "з четверга", "з пʼятниці", "з суботи", "з неділі"],
        "short_weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
        "meals": {"breakfast": "сніданок", "lunch": "обід", "dinner": "вечеря", "snacks": "перекуси"},
        "equipment": {"stove": "плита", "oven": "духовка", "microwave": "мікрохвильовка", "multicooker": "мультиварка",
                      "air fryer": "аерогриль", "blender": "блендер", "grill": "гриль"},
        "stores": {"silpo": "Сільпо"},
        "units": {"pcs": ("шт.",) * 4, "clove": ("зубчик", "зубчики", "зубчиків", "зубчика"),
                  "slice": ("скибка", "скибки", "скибок", "скибки"), "can": ("банка", "банки", "банок", "банки"),
                  "tbsp": ("ст. л.",) * 4, "tsp": ("ч. л.",) * 4},
        "day": ("день", "дні", "днів", "дня"),
        "portion": ("порція", "порції", "порцій", "порції"),
        "phrases": PHRASES_UK,
    },
    "ru": {
        "months": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
                   "сентября", "октября", "ноября", "декабря"],
        "short_months": ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
        "weekdays": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
        "weekdays_from": ["с понедельника", "со вторника", "со среды", "с четверга", "с пятницы", "с субботы", "с воскресенья"],
        "short_weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        "meals": {"breakfast": "завтрак", "lunch": "обед", "dinner": "ужин", "snacks": "перекусы"},
        "equipment": {"stove": "плита", "oven": "духовка", "microwave": "микроволновка", "multicooker": "мультиварка",
                      "air fryer": "аэрогриль", "blender": "блендер", "grill": "гриль"},
        "stores": {"silpo": "Сильпо"},
        "units": {"pcs": ("шт.",) * 4, "clove": ("зубчик", "зубчика", "зубчиков", "зубчика"),
                  "slice": ("ломтик", "ломтика", "ломтиков", "ломтика"), "can": ("банка", "банки", "банок", "банки"),
                  "tbsp": ("ст. л.",) * 4, "tsp": ("ч. л.",) * 4},
        "day": ("день", "дня", "дней", "дня"),
        "portion": ("порция", "порции", "порций", "порции"),
        "phrases": PHRASES_RU,
    },
}


def lang(ctx):
    """'uk', 'ru' or 'en', from the menu's language."""
    language = (((ctx or {}).get("menu") or {}).get("language") or "").lower()
    return "uk" if language.startswith("ukr") else "ru" if language.startswith("rus") else "en"


def words_for(ctx):
    """The word table of the menu's language, or None for English."""
    return LANGS.get(lang(ctx))


def tr(ctx, text, **values):
    """A phrase in the menu's language, with its values filled in."""
    table = words_for(ctx)
    return (table["phrases"].get(text, text) if table else text).format(**values)


def uk_form(n, forms):
    """Word form for a count in Ukrainian or Russian: forms are (one, two to four, five and more, a part of one)."""
    if n != int(n):
        return forms[3]
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def days_words(ctx, n):
    table = words_for(ctx)
    return f"{n} {uk_form(n, table['day'])}" if table else f"{n} days"


def number(ctx, value, digits=None):
    text = f"{value:.{digits}f}" if digits is not None else f"{value:g}"
    return text.replace(".", ",") if words_for(ctx) else text


def portion_words(ctx, size, digits=None):
    """'1 of a portion', '2.15 portions' or, in Ukrainian, '1 порція', '2,15 порції'."""
    table = words_for(ctx)
    if table:
        return f"{number(ctx, size, digits)} {uk_form(size if digits is None else float(f'{size:.{digits}f}'), table['portion'])}"
    if digits is not None:
        return f"{size:.{digits}f} portions"
    return f"{size:g} of a portion"


def meal_word(ctx, meal):
    table = words_for(ctx)
    return table["meals"].get(meal, meal) if table else meal


def weekday_from(ctx, date):
    """The day for 'from {day}': 'Monday', or 'з понеділка' / 'с понедельника' with the preposition."""
    table = words_for(ctx)
    return table["weekdays_from"][date.weekday()] if table else WEEKDAYS[date.weekday()]


def equipment_words(ctx, items):
    table = words_for(ctx)
    return ", ".join(table["equipment"].get(x.lower(), x) if table else x for x in items)


def store_words(ctx, store):
    table = words_for(ctx)
    return table["stores"].get(store, store) if table and store else (store or tr(ctx, "store"))


# ---------- reading the project ----------

def parse_md(text):
    """Sections of a shopper data file: {'': top fields, 'Eater 1': {...}, ...}."""
    sections, current = {"": {}}, ""
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            current = heading.group(1).strip()
            sections.setdefault(current, {})
            continue
        if line.startswith("###"):
            current = None
            continue
        field = re.match(r"^-\s+([a-z_]+):\s*(.*)$", line)
        if field and current is not None:
            sections[current][field.group(1)] = field.group(2).strip()
    return sections


def words(value):
    if value is None or value.strip().lower() in EMPTY:
        return []
    return [w.strip().lower() for w in value.split(",") if w.strip()]


def num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def meal_targets(target):
    """Calories per meal, scaled so that the whole day adds up to the daily calories exactly."""
    split = {m: num(target.get(f"{m}_kcal"), 0) for m in MEALS}
    whole = sum(split.values()) + num(target.get("outside_plan_kcal"), 0)
    calories = num(target.get("calories_kcal"), 0)
    factor = calories / whole if whole else 1
    return {m: kcal * factor for m, kcal in split.items()}


def fail(message):
    raise SystemExit(message)


def load_project(project, which="draft"):
    data = pathlib.Path(project) / "data"
    profile_path, diet_path = data / "profile.md", data / "diet.md"
    if not profile_path.exists():
        fail("There is no profile yet: data/profile.md is missing.")
    if not diet_path.exists():
        fail("There are no diet targets yet: data/diet.md is missing.")
    profile, diet = parse_md(profile_path.read_text("utf-8")), parse_md(diet_path.read_text("utf-8"))
    menu_path = data / "menu" / f"{which}.json"
    if not menu_path.exists():
        fail(f"There is no {'draft menu' if which == 'draft' else 'saved menu'}: {menu_path} is missing.")
    raw = menu_path.read_text("utf-8")
    try:
        menu = json.loads(raw)
    except json.JSONDecodeError as error:
        fail(f"{menu_path.name} is not valid JSON: {error}")
    foods = json.loads((SKILL_DIR / "foods.json").read_text("utf-8"))
    for key, food in (menu.get("extra_foods") or {}).items():
        foods[key] = dict(food, estimate=True)
    patterns = json.loads((SKILL_DIR.parent / "dietitian" / "patterns.json").read_text("utf-8"))
    patterns.pop("_aliases", None)
    history_path = data / "history.json"
    history = json.loads(history_path.read_text("utf-8")) if history_path.exists() else {"meals": []}

    eaters = []
    for name, section in profile.items():
        match = re.match(r"^Eater (\d+)$", name)
        if not match:
            continue
        target = diet.get(name, {})
        if "calories_kcal" not in target:
            continue  # not planned, for example a child under one year
        eaters.append({
            "index": int(match.group(1)),
            "label": section.get("label", name),
            "meals": [m for m in words(section.get("meals_at_home")) if m in MEALS] or list(MEALS[:3]),
            "hard_limits": words(section.get("hard_limits")),
            "dislikes": words(section.get("dislikes")),
            "targets": meal_targets(target),
            "calories": num(target.get("calories_kcal"), 0),
            "protein": num(target.get("protein_g"), 0),
            "age": num(target.get("age")),
            "pattern": target.get("based_on", "balanced"),
            "way": target.get("way_of_eating", "balanced"),
        })
    if not eaters:
        fail("The diet has no targets for any eater. Run the dietitian's Calculate first.")
    cooking = profile.get("Cooking", {})
    budget = profile.get("Budget", {})
    prices_path = data / "prices.json"
    prices = json.loads(prices_path.read_text("utf-8")) if prices_path.exists() else None
    if prices is not None:
        prices["foods"] = {k: with_per_kg(v) for k, v in (prices.get("foods") or {}).items() if with_per_kg(v)}
    pantry_path = data / "pantry.json"
    pantry = (json.loads(pantry_path.read_text("utf-8")).get("items") or []) if pantry_path.exists() else []
    return {
        "pantry": [i for i in pantry if i.get("food") and isinstance(i.get("grams"), (int, float)) and i["grams"] > 0],
        "prices": prices,
        "budget": num(budget.get("budget_uah")),
        "budget_period": (budget.get("budget_period") or "week").strip().lower(),
        "data": data, "menu": menu, "menu_path": menu_path, "raw": raw, "foods": foods,
        "patterns": patterns, "history": history, "eaters": eaters,
        "weekday_limit": num(cooking.get("cook_time_weekday_min"), 60),
        "weekend_limit": num(cooking.get("cook_time_weekend_min"), 60),
        "equipment": set(words(cooking.get("equipment"))),
        "leftovers": (cooking.get("leftovers") or "next day").strip().lower(),
    }


# ---------- dates and words ----------

def as_date(text):
    return datetime.date.fromisoformat(text)


def day_words(date, year=False, ctx=None):
    table = words_for(ctx)
    if table:
        text = f"{table['weekdays'][date.weekday()].capitalize()} {date.day} {table['months'][date.month - 1]}"
    else:
        text = f"{WEEKDAYS[date.weekday()]} {date.day} {MONTHS[date.month - 1]}"
    return f"{text} {date.year}" if year else text


def inside(ctx, text):
    """A day's words in the middle of a Ukrainian or Russian sentence start with a small letter."""
    return text[:1].lower() + text[1:] if words_for(ctx) else text


def short_day(date, ctx=None):
    table = words_for(ctx)
    if table:
        return f"{table['short_weekdays'][date.weekday()]} {date.day} {table['short_months'][date.month - 1]}"
    return f"{WEEKDAYS[date.weekday()]} {date.day} {MONTHS[date.month - 1][:3]}"


def half_up(value, step=1):
    return math.floor(value / step + 0.5) * step


def plain(food):
    return str(food).replace("_", " ")


def norm(text):
    text = re.sub(r"[_\-]+", " ", text.strip().lower())
    return text[:-1] if text.endswith("s") and len(text) > 3 else text


# ---------- nutrition ----------

def dish_nutrition(dish, foods):
    total = [0.0] * 5
    for item in dish.get("ingredients", []):
        food = foods.get(item.get("food"))
        if not food:
            continue
        for i in range(5):
            total[i] += food["n"][i] * item.get("grams", 0) / 100
    return total


def group_grams(dish, foods, multiplier=1.0):
    grams = {}
    for item in dish.get("ingredients", []):
        food = foods.get(item.get("food"))
        if not food:
            continue
        for group in food.get("g", []):
            grams[group] = grams.get(group, 0) + item.get("grams", 0) * multiplier
        if set(food.get("g", [])) & FRUIT_VEG:
            grams["fruit_veg"] = grams.get("fruit_veg", 0) + item.get("grams", 0) * multiplier
    return grams


def has_group(grams, group):
    return grams.get(group, 0) >= THRESHOLD.get(group, 1)


def food_matches(term, key, food):
    """Does a user's word for a food ('nuts', 'pork', 'spicy food') mean this food?"""
    term = norm(term)
    for extra in (" food", " product"):
        if term.endswith(extra):
            term = term[: -len(extra)]
    names = [norm(key), norm(food.get("uk", "")), norm(food.get("ru", ""))]
    names += [norm(x) for x in food.get("also", [])]
    names += [norm(x) for x in food.get("a", [])]
    names += [norm(x) for x in food.get("g", [])]
    names += [norm(GROUP_WORDS[g]) for g in food.get("g", []) if g in GROUP_WORDS]
    return any(term == name or (len(term) > 3 and term in name.split()) for name in names if name)


# ---------- cost ----------

def with_per_kg(entry):
    """A price entry with its price per kilogram worked out; None when it has no usable price."""
    if entry.get("missing") or not isinstance(entry.get("price"), (int, float)):
        return entry if isinstance(entry.get("per_kg"), (int, float)) else None
    entry = dict(entry)
    if entry.get("pack_grams"):
        entry["per_kg"] = entry["price"] / entry["pack_grams"] * 1000
    else:
        entry["per_kg"] = entry["price"]  # sold by weight: the price is for a kilogram
        entry.pop("pack_grams", None)
    return entry


def buy_cost(price, grams):
    """What has to be paid to get this many grams: whole packs, or the store's weight step."""
    if grams <= 0:
        return 0.0
    if price.get("pack_grams"):
        return math.ceil(grams / price["pack_grams"] - 1e-9) * price["price"]
    step = price.get("step_grams") or DEFAULT_STEP_GRAMS
    return math.ceil(grams / step - 1e-9) * step * price["per_kg"] / 1000


def cost_report(ctx, days, dishes, portions):
    """Cost of the menu: per day by the grams eaten, and in total by what must be bought."""
    prices = (ctx["prices"] or {}).get("foods") or {}
    need, per_day, per_dish, unpriced = {}, {}, {}, set()
    early = {}  # grams of each food eaten in the first days, for cooked food at home
    for index, day in enumerate(days):
        total = 0.0
        for meal in MEALS:
            sizes = (portions.get(day["date"]) or {}).get(meal) or {}
            multiplier = sum(sizes.values())
            for entry in (day.get("meals") or {}).get(meal) or []:
                allowed = entry.get("eaters")
                factor = multiplier if allowed is None else sum(v for k, v in sizes.items() if int(k) in allowed)
                serving = 0.0
                for item in dishes[entry["dish"]]["ingredients"]:
                    food = item["food"]
                    if food in FREE_FOODS:
                        continue
                    grams = item["grams"] * factor
                    need[food] = need.get(food, 0) + grams
                    if index < COOKED_KEEPS_DAYS:
                        early[food] = early.get(food, 0) + grams
                    if food in prices:
                        serving += grams * prices[food]["per_kg"] / 1000
                    else:
                        unpriced.add(food)
                total += serving
                per_dish[entry["dish"]] = max(per_dish.get(entry["dish"], 0), serving)
        per_day[day["date"]] = total
    used = sum(per_day.values())
    # food already at home is used first and not bought
    at_home = {}
    for item in ctx.get("pantry") or []:
        at_home[item["food"]] = at_home.get(item["food"], 0) + item["grams"]
    from_home = {f: min(g, at_home[f]) for f, g in need.items() if at_home.get(f)}
    # under half a gram left to buy is rounding, not a purchase
    to_buy = {f: (g - from_home.get(f, 0) if g - from_home.get(f, 0) >= 0.5 else 0) for f, g in need.items()}
    buy = sum(buy_cost(prices[f], g) for f, g in to_buy.items() if f in prices)
    purchases = []
    for food, grams in sorted(to_buy.items()):
        if grams <= 0 or food not in prices:
            continue
        price = prices[food]
        if price.get("pack_grams"):
            packs = math.ceil(grams / price["pack_grams"] - 1e-9)
            amount = f"{packs} x {price['pack_grams']:g} g"
        else:
            step = price.get("step_grams") or DEFAULT_STEP_GRAMS
            amount = f"{math.ceil(grams / step - 1e-9) * step:g} g"
        purchases.append({"food": food, "title": price.get("title") or food, "code": price.get("code"),
                          "amount": amount, "needed_grams": int(half_up(grams)),
                          "cost": round(buy_cost(price, grams), 2)})
    # what is paid for but not eaten in these days, dearest first
    leftover = sorted(((buy_cost(prices[f], g) - g * prices[f]["per_kg"] / 1000, f, g) for f, g in to_buy.items()
                       if f in prices and g > 0), reverse=True)
    cap = None
    if ctx["budget"] and ctx["budget_period"] in PERIOD_DAYS:
        cap = ctx["budget"] * len(days) / PERIOD_DAYS[ctx["budget_period"]]
    home_value = sum(g * prices[f]["per_kg"] / 1000 for f, g in from_home.items() if f in prices)
    return {"buy": buy, "used": used, "bought_eaten": used - home_value, "cap": cap, "per_day": per_day, "per_dish": per_dish,
            "unpriced": sorted(f for f in unpriced if to_buy.get(f, 0) > 0), "need": need, "leftover": leftover,
            "from_home": from_home, "at_home": at_home, "early": early, "purchases": purchases}


# ---------- the check ----------

def plate_limit(entries, dishes, foods):
    """The largest multiplier that keeps every food and every soup of a meal within one plate, and what sets it."""
    grams, limits = {}, []
    for entry in entries:
        dish = dishes[entry["dish"]]
        for item in dish["ingredients"]:
            grams[item["food"]] = grams.get(item["food"], 0) + item["grams"]
        if dish.get("soup"):
            weight = sum(item["grams"] for item in dish["ingredients"] if not item["food"].startswith("bread_"))
            limits.append((SOUP_MAX / weight, f"{dish['name']} is a soup of {weight:.0f} g a portion, "
                                              f"and a plate holds at most {SOUP_MAX:g} g"))
    for food, amount in grams.items():
        if amount > 0 and food in PLATE_MAX:
            limits.append((PLATE_MAX[food] / amount, f"{plain(food)} is {amount:.0f} g a portion, "
                                                     f"and a plate holds at most {PLATE_MAX[food]:g} g"))
    return min(limits, key=lambda x: x[0], default=(math.inf, ""))


def entries_for(day, meal, eater, menu):
    result = []
    for entry in (day.get("meals") or {}).get(meal) or []:
        allowed = entry.get("eaters")
        if allowed is None or eater["index"] in allowed:
            result.append(entry)
    return result


def check(ctx, today):
    menu, foods, eaters = ctx["menu"], ctx["foods"], ctx["eaters"]
    fix, improve, judge = [], [], []
    dishes = menu.get("dishes") or {}
    days = menu.get("days") or []
    span = menu.get("range") or {}

    # structure
    if not span.get("start") or not span.get("days"):
        fix.append("The draft has no range: it needs range.start and range.days.")
        return {"fix": fix, "improve": improve, "judge": judge, "portions": {}, "days": {}, "cost": None}
    start = as_date(span["start"])
    if len(days) != int(span["days"]):
        fix.append(f"The range says {span['days']} days but the draft lists {len(days)}.")
    for i, day in enumerate(days):
        expected = (start + datetime.timedelta(days=i)).isoformat()
        if day.get("date") != expected:
            fix.append(f"Day {i + 1} should be dated {expected}, not {day.get('date')}.")
    used = set()
    for day in days:
        for meal in day.get("out") or []:
            if meal not in MEALS:
                fix.append(f"{day.get('date')}: \"{meal}\" under out is not a meal.")
            elif (day.get("meals") or {}).get(meal):
                fix.append(f"{day.get('date')}: {meal} is marked as eaten out but has dishes.")
        for meal, entries in (day.get("meals") or {}).items():
            if meal not in MEALS:
                fix.append(f"{day.get('date')}: \"{meal}\" is not a meal. Use breakfast, lunch, dinner or snacks.")
            for entry in entries or []:
                if entry.get("dish") not in dishes:
                    fix.append(f"{day.get('date')} {meal}: dish \"{entry.get('dish')}\" is not in the dishes list.")
                else:
                    used.add(entry["dish"])
    for dish_id in sorted(used):
        dish = dishes[dish_id]
        if not dish.get("name") or not dish.get("ingredients") or not dish.get("steps"):
            fix.append(f"Dish \"{dish_id}\" needs a name, ingredients and steps.")
        for item in dish.get("ingredients", []):
            if item.get("food") not in foods:
                fix.append(f"{dish.get('name', dish_id)}: ingredient \"{item.get('food')}\" is not in the food table. "
                           "Use a listed food, or add it under extra_foods with estimated values.")
            elif not isinstance(item.get("grams"), (int, float)) or item["grams"] <= 0:
                fix.append(f"{dish.get('name', dish_id)}: \"{item.get('food')}\" needs an amount in grams.")
        if dish.get("total_minutes") is not None and dish["total_minutes"] < dish.get("cook_minutes", 0):
            fix.append(f"{dish.get('name', dish_id)}: total_minutes cannot be less than cook_minutes.")
        water = sum(i.get("grams", 0) for i in dish.get("ingredients", []) if i.get("food") == "water")
        if SOUP_WORDS.search(dish.get("name", "")) and not dish.get("soup"):
            fix.append(f"{dish['name']} looks like a soup: set \"soup\" to true in it.")
        elif dish.get("soup") and water <= 0:
            fix.append(f"{dish.get('name', dish_id)} is a soup: list its water under ingredients, in grams for one portion.")
        missing = set(x.lower() for x in dish.get("equipment", [])) - ctx["equipment"]
        if missing:
            fix.append(f"{dish.get('name', dish_id)} needs {', '.join(sorted(missing))}, which is not in the kitchen.")
    if fix:
        return {"fix": fix, "improve": improve, "judge": judge, "portions": {}, "days": {}, "cost": None}

    nutrition = {dish_id: dish_nutrition(dishes[dish_id], foods) for dish_id in used}
    portions, numbers = {}, {}
    span_days = len(days)
    week_factor = span_days / 7

    for day in days:
        date = as_date(day["date"])
        portions[day["date"]], numbers[day["date"]] = {}, {"eaters": {}}
        # cooking time
        cooked = {(meal, e["dish"]) for meal in MEALS for e in (day["meals"].get(meal) or []) if e.get("cook", True)}
        minutes = sum(dishes[d].get("cook_minutes", 0) for _, d in cooked)
        limit = ctx["weekend_limit"] if date.weekday() >= 5 else ctx["weekday_limit"]
        numbers[day["date"]].update(cook_minutes=minutes, cook_limit=limit)
        if minutes > limit:
            fix.append(f"{short_day(date)}: {minutes:g} minutes of cooking, the limit is {limit:g}.")

    for eater in eaters:
        key = str(eater["index"])
        meal_groups = []  # (date, meal, {group: grams})
        servings = {}
        for day in days:
            date = as_date(day["date"])
            total = [0.0] * 5
            target = 0.0
            tight = []
            for meal in MEALS:
                entries = entries_for(day, meal, eater, menu)
                if meal not in eater["meals"] or meal in (day.get("out") or []):
                    continue
                goal = eater["targets"].get(meal, 0)
                target += goal
                if not entries:
                    fix.append(f"{short_day(date)}: {eater['label']} has no {meal}.")
                    continue
                base = sum(nutrition[e["dish"]][0] for e in entries)
                if base <= 0:
                    fix.append(f"{short_day(date)} {meal}: the dishes have no calories.")
                    continue
                wanted = goal / base
                limit, why_limit = plate_limit(entries, dishes, foods)
                multiplier = min(MAX_PORTION, max(MIN_PORTION, wanted))
                multiplier = half_up(multiplier, 0.05)
                if multiplier > limit + 1e-9:
                    multiplier = max(MIN_PORTION, math.floor(limit / 0.05 + 1e-9) * 0.05)
                if limit < MIN_PORTION:
                    fix.append(f"{short_day(date)} {meal}: {why_limit}, so even the smallest portion is too big. "
                               "Write the recipe for a smaller portion and add another dish to the meal.")
                elif min(wanted, MAX_PORTION) > limit + 0.025:
                    tight.append(f"{meal} gives {base * multiplier:.0f} of {goal:.0f} kcal because {why_limit}: "
                                 "add another dish to the meal")
                elif wanted > MAX_PORTION:
                    tight.append(f"{meal} is too light ({base * MAX_PORTION:.0f} kcal at the largest portion, {goal:.0f} needed)")
                elif wanted < MIN_PORTION:
                    tight.append(f"{meal} is too heavy ({base * MIN_PORTION:.0f} kcal at the smallest portion, {goal:.0f} needed)")
                portions[day["date"]].setdefault(meal, {})[key] = round(multiplier, 2)
                grams = {}
                for entry in entries:
                    for i in range(5):
                        total[i] += nutrition[entry["dish"]][i] * multiplier
                    for group, amount in group_grams(dishes[entry["dish"]], foods, multiplier).items():
                        grams[group] = grams.get(group, 0) + amount
                    if meal in ("lunch", "dinner"):
                        servings[entry["dish"]] = servings.get(entry["dish"], 0) + 1
                meal_groups.append((date, meal, grams))
            protein_target = eater["protein"] * target / eater["calories"] if eater["calories"] else 0
            numbers[day["date"]]["eaters"][key] = {
                "label": eater["label"], "kcal": int(half_up(total[0], 10)), "kcal_target": int(half_up(target, 10)),
                "protein": int(half_up(total[1])), "protein_target": int(half_up(protein_target)),
                "fat": int(half_up(total[2])), "carbs": int(half_up(total[3])), "fibre": int(half_up(total[4])),
            }
            if target and abs(total[0] - target) > KCAL_TOLERANCE * target:
                why = "; ".join(tight) if tight else "the portions cannot be sized to fit"
                fix.append(f"{short_day(date)}: {eater['label']} gets {total[0]:.0f} of {target:.0f} kcal: {why}.")
            elif tight:
                improve.append(f"{short_day(date)}: {eater['label']}'s {'; '.join(tight)}.")
            if protein_target and total[1] < PROTEIN_SHARE * protein_target:
                fix.append(f"{short_day(date)}: {eater['label']} gets {total[1]:.0f} g of protein, the target is {protein_target:.0f} g.")

        # foods never allowed, disliked foods
        table_terms = {}
        for kind, terms in (("never", eater["hard_limits"]), ("dislike", eater["dislikes"])):
            for term in terms:
                known = [k for k, f in foods.items() if food_matches(term, k, f)]
                table_terms[(kind, term)] = known
                if not known:
                    judge.append(f"{eater['label']}: \"{term}\" ({'never allowed' if kind == 'never' else 'disliked'}) "
                                 "cannot be checked automatically. Read the dishes and ingredients for it.")
        eaten = set()
        for day in days:
            for meal in MEALS:
                if meal in eater["meals"] and meal not in (day.get("out") or []):
                    eaten.update(e["dish"] for e in entries_for(day, meal, eater, menu))
        for (kind, term), known in table_terms.items():
            for dish_id in sorted(eaten):
                hits = [i["food"] for i in dishes[dish_id]["ingredients"] if i["food"] in known]
                if hits:
                    line = (f"{dishes[dish_id]['name']} contains {', '.join(plain(h) for h in sorted(set(hits)))}, "
                            f"which {eater['label']} {'must never get' if kind == 'never' else 'dislikes'} (\"{term}\").")
                    (fix if kind == "never" else improve).append(line)

        # the rules of the way of eating
        pattern = ctx["patterns"].get(eater["pattern"], {})
        for rule in pattern.get("checks", []):
            kind, group = rule["type"], rule.get("group")
            name = GROUP_WORDS.get(group, group)
            if kind == "never":
                for dish_id in sorted(eaten):
                    hits = [i["food"] for i in dishes[dish_id]["ingredients"]
                            if set(foods[i["food"]].get("g", [])) & set(rule["groups"])
                            and i["food"] not in rule.get("except_foods", [])
                            and not set(foods[i["food"]].get("g", [])) & set(rule.get("except_groups", []))]
                    if hits:
                        fix.append(f"{dishes[dish_id]['name']} contains {', '.join(plain(h) for h in sorted(set(hits)))}, "
                                   f"which a {eater['way']} way of eating leaves out.")
            elif kind == "every_meal":
                missing = [f"{short_day(d)} {m}" for d, m, g in meal_groups if m in rule["meals"] and not has_group(g, group)]
                if missing:
                    more = f" and {len(missing) - 3} more" if len(missing) > 3 else ""
                    fix.append(f"{eater['label']}: {name} missing at {', '.join(missing[:3])}{more}.")
            elif kind in ("daily_min", "daily_max"):
                bad = []
                for day in days:
                    date = as_date(day["date"])
                    count = sum(1 for d, m, g in meal_groups if d == date and has_group(g, group))
                    if (kind == "daily_min" and count < rule["min"]) or (kind == "daily_max" and count > rule["max"]):
                        bad.append(short_day(date))
                if bad:
                    more = f" and {len(bad) - 3} more" if len(bad) > 3 else ""
                    need = f"at least {rule['min']} a day" if kind == "daily_min" else f"at most {rule['max']} a day"
                    fix.append(f"{eater['label']}: {name} should come {need}; not so on {', '.join(bad[:3])}{more}.")
            elif kind in ("weekly_min", "weekly_max"):
                count = sum(1 for d, m, g in meal_groups if has_group(g, group))
                if kind == "weekly_min":
                    need = max(1, math.floor(rule["min"] * week_factor)) if span_days >= 4 else 0
                    if count < need:
                        fix.append(f"{eater['label']}: {name} {count} times in {span_days} days, at least {need} needed.")
                else:
                    most = math.ceil(rule["max"] * week_factor)
                    if count > most:
                        fix.append(f"{eater['label']}: {name} {count} times in {span_days} days, at most {most} allowed.")
            elif kind == "daily_grams_min":
                if eater["age"] is not None and eater["age"] < rule.get("min_age", 0):
                    continue
                short = []
                for day in days:
                    date = as_date(day["date"])
                    planned = numbers[day["date"]]["eaters"][key]["kcal_target"]
                    need = rule["min"] * planned / eater["calories"] if eater["calories"] else 0
                    got = sum(g.get(group, 0) for d, m, g in meal_groups if d == date)
                    if got < need - 0.5:
                        short.append(f"{short_day(date)} {got:.0f} of {need:.0f} g")
                if short:
                    more = f" and {len(short) - 3} more" if len(short) > 3 else ""
                    fix.append(f"{eater['label']}: {name} at least {rule['min']} g a day; "
                               f"{', '.join(short[:3])}{more}.")
            elif kind == "share_min":
                base = [g for d, m, g in meal_groups if has_group(g, rule["of"])]
                good = [g for g in base if has_group(g, group)]
                if base and len(good) / len(base) < rule["min"]:
                    fix.append(f"{eater['label']}: {name} in {len(good)} of {len(base)} meals with {GROUP_WORDS.get(rule['of'], rule['of'])}; "
                               f"at least {math.ceil(rule['min'] * len(base))} needed.")
        for text in pattern.get("judge", []):
            judge.append(f"{eater['label']}: judge by reading the menu: {text}")

        # variety
        most = max(2, math.ceil(2 * week_factor))
        for dish_id, count in sorted(servings.items()):
            if count > most:
                improve.append(f"{dishes[dish_id]['name']} is served {count} times for lunch or dinner; at most {most} keeps the menu varied.")

    # leftovers
    allowed = LEFTOVER_DAYS.get(ctx["leftovers"], 1)
    last_cooked = {}
    for index, day in enumerate(days):
        for meal in MEALS:
            for entry in day["meals"].get(meal) or []:
                if entry.get("cook", True):
                    last_cooked[entry["dish"]] = index
                    continue
                name = dishes[entry["dish"]]["name"]
                when = short_day(as_date(day["date"]))
                if allowed < 0:
                    fix.append(f"{when} {meal}: {name} is planned as a leftover, but dishes may not repeat.")
                elif entry["dish"] not in last_cooked:
                    fix.append(f"{when} {meal}: {name} is planned as a leftover but was not cooked before.")
                elif index - last_cooked[entry["dish"]] > allowed:
                    fix.append(f"{when} {meal}: {name} was cooked {index - last_cooked[entry['dish']]} days earlier; "
                               f"a dish may come back within {allowed} day{'s' if allowed > 1 else ''}.")

    # repeats of earlier menus
    main_names = {dishes[e["dish"]]["name"] for day in days for meal in ("lunch", "dinner") for e in day["meals"].get(meal) or []}
    again = sorted(main_names & set(menu.get("avoid") or []))
    if again:
        improve.append(f"Repeats dishes of the previous menu: {', '.join(again)}.")
    recent = {m.get("dish") for m in ctx["history"].get("meals", [])
              if m.get("date") and 0 <= (start - as_date(m["date"])).days <= RECENT_DAYS}
    again = sorted((main_names & recent) - set(menu.get("avoid") or []))
    if again:
        improve.append(f"Eaten in the last {RECENT_DAYS} days: {', '.join(again)}.")
    estimated = sorted({i["food"] for d in used for i in dishes[d]["ingredients"] if foods[i["food"]].get("estimate")})
    if estimated:
        improve.append(f"Nutrition values are estimates for: {', '.join(plain(e) for e in estimated)}.")

    cost = None
    if ctx["prices"] is None:
        improve.append("There is no price list (data/prices.json), so the cost was not checked.")
    else:
        report = cost_report(ctx, days, dishes, portions)
        for date, value in report["per_day"].items():
            numbers[date]["cost"] = int(half_up(value))
        cost = {"buy": int(half_up(report["buy"])), "used": int(half_up(report["used"])),
                "bought_eaten": int(half_up(report["bought_eaten"])),
                "cap": int(half_up(report["cap"])) if report["cap"] else None,
                "store": ctx["prices"].get("store"), "prices_updated": ctx["prices"].get("updated"),
                "unpriced": report["unpriced"], "purchases": report["purchases"],
                "unpriced_grams": {f: int(half_up(report["need"][f] - report["from_home"].get(f, 0)))
                                   for f in report["unpriced"]},
                "from_home": {f: int(half_up(g)) for f, g in sorted(report["from_home"].items())}}
        for food, have in sorted(report["at_home"].items()):
            taken = report["from_home"].get(food, 0)
            if taken < 0.8 * have:
                improve.append(f"At home but not used up: {plain(food)} ({taken:.0f} g of {have:.0f} g used).")
        cooked = {}
        for item in ctx.get("pantry") or []:
            if (item.get("state") or "").lower() == "cooked":
                cooked[item["food"]] = cooked.get(item["food"], 0) + item["grams"]
        for food, have in sorted(cooked.items()):
            soon = report["early"].get(food, 0)
            if soon < 0.9 * have:
                fix.append(f"The cooked {plain(food)} at home ({have:.0f} g) has to be eaten in the first {COOKED_KEEPS_DAYS} days; "
                           f"the menu uses {soon:.0f} g of {plain(food)} in those days.")
        if report["unpriced"]:
            improve.append(f"No price is known for: {', '.join(plain(u) for u in report['unpriced'])}. The cost leaves them out.")
        if report["cap"] and report["buy"] > report["cap"]:
            dear = sorted(report["per_dish"].items(), key=lambda x: -x[1])[:4]
            names = ", ".join(f"{dishes[d]['name']} ({v:.0f} UAH a serving)" for d, v in dear)
            fix.append(f"The menu costs {report['buy']:.0f} UAH to buy; the budget for {span_days} days is "
                       f"{report['cap']:.0f} UAH. Dearest dishes: {names}.")
            waste = [(v, f, g) for v, f, g in report["leftover"] if v >= 20][:5]
            if waste:
                parts = ", ".join(f"{plain(f)} ({v:.0f} UAH of the pack is not eaten; {g:.0f} g used)" for v, f, g in waste)
                fix.append(f"Paid for but left over: {parts}. Use more of these foods across dishes, or drop them.")

    def unique(lines):
        return list(dict.fromkeys(lines))

    return {"fix": unique(fix), "improve": unique(improve), "judge": unique(judge), "portions": portions,
            "days": numbers, "cost": cost}


def fingerprint(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def command_check(args):
    ctx = load_project(args.project, "draft")
    result = check(ctx, args.today)
    result["fix"] += [text for text in args.add_fix if text not in result["fix"]]
    result["improve"] += [text for text in args.add_improve if text not in result["improve"]]
    if args.judged_ok:
        result["judge"] = []
    result = {"checked": args.today, "draft_fingerprint": fingerprint(ctx["raw"]), **result}
    (ctx["data"] / "menu" / "draft-check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"fix": result["fix"], "improve": result["improve"], "judge": result["judge"]},
                     ensure_ascii=False, indent=1))


# ---------- showing ----------

def load_check(ctx, which, today):
    path = ctx["data"] / "menu" / f"{which}-check.json"
    if path.exists():
        saved = json.loads(path.read_text("utf-8"))
        if saved.get("draft_fingerprint") == fingerprint(ctx["raw"]):
            return saved, True
    return check(ctx, today), False


def find_dish(menu, wanted):
    dishes = menu.get("dishes") or {}
    if wanted in dishes:
        return wanted
    low = wanted.strip().lower()
    for dish_id, dish in dishes.items():
        if dish.get("name", "").lower() == low:
            return dish_id
    hits = [d for d, dish in dishes.items() if low in dish.get("name", "").lower()]
    if len(hits) == 1:
        return hits[0]
    fail(f"No single dish matches \"{wanted}\". Dishes: {', '.join(d.get('name', i) for i, d in dishes.items())}.")


def meal_line(day, meal, ctx, first_cook):
    menu, eaters = ctx["menu"], ctx["eaters"]
    parts = []
    for entry in (day.get("meals") or {}).get(meal) or []:
        dish = menu["dishes"][entry["dish"]]
        if entry.get("cook", True):
            minutes = dish.get("cook_minutes", 0)
            note = tr(ctx, "{n} min", n=f"{minutes:g}") if minutes else tr(ctx, "no cooking")
        else:
            origin = first_cook.get((entry["dish"], day["date"]))
            note = tr(ctx, "from {day}", day=weekday_from(ctx, as_date(origin))) if origin else tr(ctx, "leftover")
        who = ""
        if entry.get("eaters") is not None and len(eaters) > 1:
            names = [e["label"] for e in eaters if e["index"] in entry["eaters"]]
            who = tr(ctx, ", for {names}", names=tr(ctx, " and ").join(names))
        parts.append(f"{dish['name']} ({note}{who})")
    return ", ".join(parts)


def cook_origins(menu):
    """For every leftover serving, the date its dish was cooked."""
    origins, last = {}, {}
    for day in menu.get("days") or []:
        for meal in MEALS:
            for entry in (day.get("meals") or {}).get(meal) or []:
                if entry.get("cook", True):
                    last[entry["dish"]] = day["date"]
                elif entry["dish"] in last:
                    origins[(entry["dish"], day["date"])] = last[entry["dish"]]
    return origins


def show_day(day, ctx, result, origins, lines):
    menu, date = ctx["menu"], as_date(day["date"])
    batches = {d: recipe_batches(ctx, result, d) for d in menu.get("dishes") or {}}
    lines.append(day_words(date, ctx=ctx))
    for meal in MEALS:
        if meal in (day.get("out") or []):
            lines.append(f"  {meal_word(ctx, meal).capitalize()}: {tr(ctx, 'eaten out')}")
            continue
        text = meal_line(day, meal, ctx, origins)
        if text:
            lines.append(f"  {meal_word(ctx, meal).capitalize()}: {text}")
            entries = (day.get("meals") or {}).get(meal) or []
            for entry in entries:
                for label, amounts in plate_amounts(ctx, result, batches, day, meal, entry):
                    who = f"{label}: " if len(ctx["eaters"]) > 1 else ""
                    dish_name = f"{menu['dishes'][entry['dish']]['name']}: " if len(entries) > 1 else ""
                    lines.append(f"    {who}{dish_name}{amounts}")
    numbers = (result.get("days") or {}).get(day["date"], {})
    for key, n in sorted((numbers.get("eaters") or {}).items()):
        lines.append("  " + tr(ctx, "{label}: {kcal} of {target} kcal, protein {protein} of {protein_target} g",
                               label=n["label"], kcal=n["kcal"], target=n["kcal_target"], protein=n["protein"],
                               protein_target=n["protein_target"]))
    if "cook_minutes" in numbers:
        lines.append("  " + tr(ctx, "Cooking: {minutes} min hands-on (limit {limit})",
                               minutes=f"{numbers['cook_minutes']:g}", limit=f"{numbers['cook_limit']:g}"))
    if "cost" in numbers:
        lines.append("  " + tr(ctx, "Food eaten: {cost} UAH", cost=numbers["cost"]))


def recipe_batches(ctx, result, dish_id):
    """Each cooking of a dish: the day it is cooked and the servings eaten from it, leftovers included."""
    menu = ctx["menu"]
    batches, current = [], None
    for day in menu.get("days") or []:
        for meal in MEALS:
            for entry in (day.get("meals") or {}).get(meal) or []:
                if entry["dish"] != dish_id:
                    continue
                if entry.get("cook", True) or current is None:
                    current = {"cooked": day["date"], "servings": []}
                    batches.append(current)
                sizes = ((result.get("portions") or {}).get(day["date"], {}) or {}).get(meal, {})
                allowed = entry.get("eaters")
                for eater in ctx["eaters"]:
                    if (allowed is None or eater["index"] in allowed) and str(eater["index"]) in sizes:
                        current["servings"].append((day["date"], meal, eater["label"], sizes[str(eater["index"])]))
    return batches


def ingredient_rows(ctx, dish, total):
    """Ingredient names and grams for a batch of `total` portions."""
    rows = []
    for item in dish["ingredients"]:
        food = ctx["foods"].get(item["food"]) or {}
        name = item.get("name") or local_name(ctx, food, item["food"])
        grams = item["grams"] * total
        rows.append((name, half_up(grams, 5) if grams >= 20 else half_up(grams, 1)))
    return rows


LIQUID_FOODS = {"milk", "kefir", "plant_milk_fortified", "apple_juice", "tomato_juice", "water"}
FRACTIONS = ((1 / 2, "1/2"), (1 / 3, "1/3"), (2 / 3, "2/3"), (1 / 4, "1/4"), (3 / 4, "3/4"))


def count_words(count, quarters=True):
    """A count to the nearest half: 1/2, 1, 1 1/2, 2. Pieces under one go by quarters (1/4, 3/4); spoons do not."""
    step = 0.25 if quarters and count < 0.875 else 0.5
    value = max(step, half_up(count / step) * step)
    whole, part = int(value), value - int(value)
    tail = {0.25: "1/4", 0.5: "1/2", 0.75: "3/4"}.get(round(part, 2), "")
    if not whole:
        return tail
    return f"{whole} {tail}" if tail else f"{whole}"


def unit_words(ctx, count, unit, quarters):
    """'1 1/2 clove' or, in Ukrainian, '1 1/2 зубчика'."""
    step = 0.25 if quarters and count < 0.875 else 0.5
    rounded = max(step, half_up(count / step) * step)
    words = count_words(count, quarters)
    table = words_for(ctx)
    if table:
        return f"{words} {uk_form(rounded, table['units'][unit])}"
    return f"{words} {unit}"


def amount_words(ctx, food, grams):
    """The amount in the measure a cook uses: pieces, cloves, slices, cans, spoons, millilitres or grams."""
    measure = (ctx["foods"].get(food) or {}).get("m")
    if not measure:
        return f"{grams:g} {tr(ctx, 'ml' if food in LIQUID_FOODS else 'g')}"
    unit = measure["unit"]
    if unit == "taste":
        return tr(ctx, "to taste")
    if unit == "tbsp":
        if grams < measure["g"] * 0.75:
            return unit_words(ctx, grams / (measure["g"] / 3), "tsp", False)
        return unit_words(ctx, grams / measure["g"], "tbsp", False)
    words = unit_words(ctx, grams / measure["g"], unit, unit == "pcs" and measure.get("weigh") is not False)
    return words if measure.get("weigh") is False else f"{words} ({grams:g} {tr(ctx, 'g')})"


def share_words(share):
    for value, words in FRACTIONS:
        if abs(share - value) < 0.01:
            return words
    return f"{half_up(share * 100):g}%"


def plate_amounts(ctx, result, batches, day, meal, entry):
    """What each eater eats of one dish at one meal: ingredient amounts, and the share of a pot cooked for several servings."""
    dish = ctx["menu"]["dishes"][entry["dish"]]
    sizes = ((result.get("portions") or {}).get(day["date"], {}) or {}).get(meal, {})
    batch = None
    for candidate in batches.get(entry["dish"]) or []:
        if any(s[0] == day["date"] and s[1] == meal for s in candidate["servings"]):
            batch = candidate
    total = sum(s[3] for s in batch["servings"]) if batch else 0
    allowed = entry.get("eaters")
    rows = []
    for eater in ctx["eaters"]:
        size = sizes.get(str(eater["index"]))
        if size is None or (allowed is not None and eater["index"] not in allowed):
            continue
        parts = [f"{name} {amount_words(ctx, item['food'], grams)}"
                 for item, (name, grams) in zip(dish["ingredients"], ingredient_rows(ctx, dish, size))]
        share = ""
        if batch and len(batch["servings"]) > 1 and total:
            share = tr(ctx, "{share} of what is cooked: ", share=share_words(size / total))
        rows.append((eater["label"], share + ", ".join(parts)))
    return rows


def show_recipe(ctx, result, dish_id, day_filter, lines):
    dish = ctx["menu"]["dishes"][dish_id]
    batches = recipe_batches(ctx, result, dish_id)
    lines.append(dish["name"])
    if not batches:
        lines.append(tr(ctx, "  This dish is not on the menu."))
        return
    batch = batches[0]
    if day_filter:
        match = [b for b in batches if b["cooked"] == day_filter or any(s[0] == day_filter for s in b["servings"])]
        batch = match[0] if match else batch
    total = sum(s[3] for s in batch["servings"]) or 1.0
    lines.append(tr(ctx, "  Cooked on: {day}", day=inside(ctx, day_words(as_date(batch["cooked"]), ctx=ctx))))
    lines.append(tr(ctx, "  Hands-on time: {n} min", n=f"{dish.get('cook_minutes', 0):g}"))
    if dish.get("total_minutes"):
        lines.append(tr(ctx, "  Ready in: {n} min", n=f"{dish['total_minutes']:g}"))
    if dish.get("equipment"):
        lines.append(tr(ctx, "  Equipment: {items}", items=equipment_words(ctx, dish["equipment"])))
    lines.append(tr(ctx, "  Ingredients (for everything cooked this time, {portions})", portions=portion_words(ctx, total, 2)))
    for item, (name, grams) in zip(dish["ingredients"], ingredient_rows(ctx, dish, total)):
        lines.append(f"    {name}: {amount_words(ctx, item['food'], grams)}")
    lines.append(tr(ctx, "  Servings"))
    for date, meal, label, size in batch["servings"]:
        lines.append("    " + tr(ctx, "{day} {meal}: {who}{portion}", day=short_day(as_date(date), ctx), meal=meal_word(ctx, meal),
                                   who=f"{label}, ", portion=portion_words(ctx, size)))
    lines.append(tr(ctx, "  Steps"))
    for i, step in enumerate(dish.get("steps", []), start=1):
        lines.append(f"    {i}. {step}")


def food_name(ctx, food):
    entry = ctx["foods"].get(food) or {}
    return local_name(ctx, entry, food)


def local_name(ctx, entry, food):
    """A food's name in the menu's language ('uk' or 'ru' in the food table), else its key in plain words."""
    return entry.get(lang(ctx)) or food.replace("_", " ")


def command_buy_list(args):
    ctx = load_project(args.project, args.which)
    result, _ = load_check(ctx, args.which, args.today)
    cost = result.get("cost")
    if not cost or "purchases" not in cost:
        result = check(ctx, args.today)
        cost = result.get("cost")
    if not cost:
        fail("There is no price list (data/prices.json), so there is no buy list.")
    menu = ctx["menu"]
    first = as_date(menu["days"][0]["date"])
    kind = tr(ctx, "the draft menu" if args.which == "draft" else "the menu")
    lines = [tr(ctx, "Buy list for {kind}: {days} from {first}", kind=kind, days=days_words(ctx, len(menu["days"])),
                first=inside(ctx, day_words(first, year=True, ctx=ctx))), ""]
    for item in sorted(cost["purchases"], key=lambda x: -x["cost"]):
        amount = item["amount"].replace(" x ", " × ").replace(" g", " " + tr(ctx, "g")) if words_for(ctx) else item["amount"]
        lines.append(f"  {item['title']}: {amount}, {tr(ctx, '{cost} UAH', cost=number(ctx, item['cost'], 2))}")
    budget = tr(ctx, " (budget {cap} UAH)", cap=cost["cap"]) if cost.get("cap") else ""
    lines += ["", tr(ctx, "Total: {buy} UAH{budget}", buy=cost["buy"], budget=budget),
              tr(ctx, "Prices: {store}, {date}", store=store_words(ctx, cost.get("store")),
                 date=cost.get("prices_updated") or tr(ctx, "date unknown"))]
    if cost.get("unpriced"):
        lines.append(tr(ctx, "Not on the list, no price known: {names}", names=", ".join(food_name(ctx, f) for f in cost["unpriced"])))
    if cost.get("from_home"):
        lines += ["", tr(ctx, "From home, not bought")]
        lines += [f"  {food_name(ctx, f)}: {g} {tr(ctx, 'g')}" for f, g in cost["from_home"].items()]
    print("\n".join(lines))


# ---------- the cart ----------

def menu_purchases(ctx, today):
    """The saved menu's cost as checked when it was saved: its food from home was taken off the pantry then."""
    result, _ = load_check(ctx, "menu", today)
    cost = result.get("cost")
    if not cost:
        fail("There is no price list (data/prices.json), so there is nothing to order.")
    return cost


def command_cart_plan(args):
    ctx = load_project(args.project, "menu")
    cost = menu_purchases(ctx, args.today)
    # amounts as saved with the menu; the product as the price list holds it now (it may have been replaced since)
    current = (ctx["prices"] or {}).get("foods") or {}
    def product(food, code, title):
        entry = current.get(food) or {}
        return (entry.get("code"), entry.get("title") or title) if entry.get("code") else (code, title)
    def search_name(food):
        # the store is Ukrainian: search it by the Ukrainian name, whatever the menu's language
        return (ctx["foods"].get(food) or {}).get("uk") or food_name(ctx, food)
    items = []
    for x in cost["purchases"]:
        if x["needed_grams"] <= 0:  # a menu saved before rounding was handled can list well under a gram
            continue
        code, title = product(x["food"], x.get("code"), x["title"])
        items.append({"food": x["food"], "code": code, "title": title, "search_name": search_name(x["food"]),
                      "needed_grams": x["needed_grams"]})
    for food, grams in (cost.get("unpriced_grams") or {}).items():
        if grams > 0:
            code, title = product(food, None, None)
            items.append({"food": food, "code": code, "title": title, "search_name": search_name(food),
                          "needed_grams": grams})
    cap = cost.get("cap")
    print(json.dumps({"first_day": ctx["menu"]["days"][0]["date"], "days": len(ctx["menu"]["days"]),
                      "budget_uah": int(half_up(cap)) if cap else None, "menu_cost": cost.get("buy"),
                      "from_home": [{"food": f, "name": food_name(ctx, f), "grams": g} for f, g in cost["from_home"].items()],
                      "items": items}, ensure_ascii=False, indent=1))


def command_show(args):
    ctx = load_project(args.project, args.which)
    result, _ = load_check(ctx, args.which, args.today)
    menu, lines = ctx["menu"], []
    if args.recipe:
        show_recipe(ctx, result, find_dish(menu, args.recipe), args.day, lines)
        print("\n".join(lines))
        return
    days = menu.get("days") or []
    origins = cook_origins(menu)
    if args.day:
        days = [d for d in days if d.get("date") == args.day]
        if not days:
            fail(f"{args.day} is not in the menu.")
    else:
        first, last = as_date(menu["days"][0]["date"]), as_date(menu["days"][-1]["date"])
        kind = tr(ctx, "Draft menu" if args.which == "draft" else "Menu")
        lines += [tr(ctx, "{kind} for {days}: {first} to {last}", kind=kind, days=days_words(ctx, len(menu["days"])),
                     first=inside(ctx, day_words(first, ctx=ctx)), last=inside(ctx, day_words(last, year=True, ctx=ctx))), ""]
    for day in days:
        show_day(day, ctx, result, origins, lines)
        lines.append("")
    if not args.day:
        cost = result.get("cost")
        if cost:
            budget = tr(ctx, " (budget {cap} UAH for {days})", cap=cost["cap"], days=days_words(ctx, len(menu["days"]))) \
                if cost.get("cap") else ""
            eaten = cost.get("bought_eaten", cost["used"])
            lines += [tr(ctx, "Cost"), tr(ctx, "  To buy: {buy} UAH{budget}", buy=cost["buy"], budget=budget),
                      tr(ctx, "  Of that, eaten in these days: {eaten} UAH; left over for later: {left} UAH",
                         eaten=eaten, left=cost["buy"] - eaten),
                      tr(ctx, "  Prices: {store}, {date}", store=store_words(ctx, cost.get("store")),
                         date=cost.get("prices_updated") or tr(ctx, "date unknown"))]
            if cost.get("from_home"):
                home = ", ".join(f"{food_name(ctx, f)} {g} {tr(ctx, 'g')}" for f, g in cost["from_home"].items())
                lines.append(tr(ctx, "  From home, not bought: {home}", home=home))
            lines.append("")
        lines.append(tr(ctx, "Check"))
        if not (result["fix"] or result["improve"] or result["judge"]):
            lines.append(tr(ctx, "  No problems found."))
        for title, key in (("To fix", "fix"), ("To improve", "improve"), ("To judge by reading", "judge")):
            if result[key]:
                lines.append(f"  {tr(ctx, title)}")
                lines += [f"    {line}" for line in result[key]]
    print("\n".join(lines).rstrip())



# ---------- the web page ----------

PAGE_STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: the week as a grid of day cards; below it one recipe card per cooking, reached by clicking a dish. */
:root {
  --bg: #f6f7f2; --surface: #ffffff; --fg: #1d231c; --muted: #5d6658; --line: #dde2d5;
  --accent: #2f6b3c; --accent-soft: #e3efe2; --mark: #b5651d;
  --display: "Unbounded", "Segoe UI", system-ui, sans-serif;
  --body: "Inter", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #141813; --surface: #1c221b; --fg: #e8ece3; --muted: #a2ab9b; --line: #2f382d;
  --accent: #8cc79a; --accent-soft: #24352a; --mark: #e0a35e; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #141813; --surface: #1c221b; --fg: #e8ece3; --muted: #a2ab9b; --line: #2f382d;
  --accent: #8cc79a; --accent-soft: #24352a; --mark: #e0a35e; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15px; line-height: 1.5; }
.page { max-width: 1080px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 36px; }
h1, h2, h3 { font-family: var(--display); font-weight: 700; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(24px, 4vw, 34px); letter-spacing: -0.01em; }
h2 { font-size: 18px; }
h3 { font-size: 17px; font-weight: 500; line-height: 1.3; }
a { color: var(--accent); text-underline-offset: 3px; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
.head { display: flex; flex-direction: column; gap: 8px; }
.facts { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--muted); font-size: 14px; }
.facts b { color: var(--fg); font-weight: 600; font-variant-numeric: tabular-nums; }
.label { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.week { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.day { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.day h2 { font-size: 15px; }
.meal { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.meal a { font-weight: 500; }
.note { color: var(--muted); font-size: 13px; }
.amounts { font-size: 13px; line-height: 1.45; margin-bottom: 4px; }
.out { color: var(--muted); font-style: italic; }
.daynums { border-top: 1px solid var(--line); padding-top: 8px; font-family: var(--mono); font-size: 12px; color: var(--muted);
  font-variant-numeric: tabular-nums; display: flex; flex-direction: column; gap: 2px; }
.recipes { display: flex; flex-direction: column; gap: 14px; }
.recipe { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px;
  display: flex; flex-direction: column; gap: 14px; scroll-margin-top: 16px; }
.recipe:target { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.meta { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { background: var(--accent-soft); color: var(--fg); border-radius: 999px; padding: 2px 10px; font-size: 13px; }
.cols { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); gap: 20px; }
@media (max-width: 640px) { .cols { grid-template-columns: minmax(0, 1fr); } }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
td { padding: 5px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
td.g { text-align: right; font-family: var(--mono); font-size: 13px; white-space: nowrap; padding-left: 12px;
  font-variant-numeric: tabular-nums; color: var(--mark); }
ol { margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 8px; }
ol li::marker { color: var(--accent); font-weight: 600; }
.servings { margin: 0; padding: 0; list-style: none; font-size: 13px; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }
.back { font-size: 13px; align-self: flex-start; }
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
</style>
"""


def recipe_anchor(dish_id, cooked):
    return "r-" + re.sub(r"[^A-Za-z0-9-]", "-", f"{dish_id}-{cooked}")


def render_page(ctx, result, which):
    menu, esc = ctx["menu"], html.escape
    days = menu.get("days") or []
    first, last = as_date(days[0]["date"]), as_date(days[-1]["date"])
    months = words_for(ctx)["months"] if words_for(ctx) else MONTHS
    span = f"{first.day}–{last.day} {months[last.month - 1]}" if first.month == last.month else \
        f"{first.day} {months[first.month - 1]} – {last.day} {months[last.month - 1]}"
    title = f"{tr(ctx, 'Draft menu' if which == 'draft' else 'Menu')} {span}"
    batches = {d: recipe_batches(ctx, result, d) for d in menu.get("dishes") or {}}

    def batch_of(dish_id, date):
        chosen = None
        for batch in batches.get(dish_id) or []:
            if batch["cooked"] <= date:
                chosen = batch
        return chosen or (batches.get(dish_id) or [None])[0]

    out = [f"<title>{esc(title)}</title>", '<meta name="claude:viewport-fit-sides" content="cover">', PAGE_STYLE,
           '<main class="page">', '<header class="head" id="week">', f'<span class="label">{esc(days_words(ctx, len(days)))}</span>',
           f"<h1>{esc(title)} {last.year}</h1>", '<div class="facts">']
    for eater in ctx["eaters"]:
        out.append("<span>" + tr(ctx, "{name}: {kcal} kcal, protein {protein} g a day", name=esc(eater["label"]),
                                 kcal=f"<b>{eater['calories']:g}", protein=f"<b>{eater['protein']:g}")
                   .replace(" kcal", " kcal</b>").replace(" ккал", " ккал</b>").replace(" g a day", " g</b> a day")
                   .replace(" г на день", " г</b> на день") + "</span>")
    cost = result.get("cost") or {}
    if cost.get("buy") is not None:
        money = lambda v: "<b>" + tr(ctx, "{cost} UAH", cost=v) + "</b>"
        budget = tr(ctx, " of {cap} budget", cap=money(cost["cap"])) if cost.get("cap") else ""
        out.append("<span>" + tr(ctx, "To buy: {buy}{budget}", buy=money(cost["buy"]), budget=budget) + "</span>")
    out += ["</div>", f"<span class=\"note\">{tr(ctx, 'Click a dish to open its recipe.')}</span>", "</header>",
            f'<section class="week" aria-label="{tr(ctx, "Days")}">']
    for day in days:
        date = as_date(day["date"])
        out += ['<article class="day">', f"<h2>{esc(day_words(date, ctx=ctx))}</h2>"]
        for meal in MEALS:
            if meal in (day.get("out") or []):
                out.append(f'<div class="meal"><span class="label">{meal_word(ctx, meal)}</span><span class="out">{tr(ctx, "eaten out")}</span></div>')
                continue
            entries = (day.get("meals") or {}).get(meal) or []
            if not entries:
                continue
            out.append(f'<div class="meal"><span class="label">{meal_word(ctx, meal)}</span>')
            for entry in entries:
                dish = menu["dishes"][entry["dish"]]
                batch = batch_of(entry["dish"], day["date"])
                href = f"#{recipe_anchor(entry['dish'], batch['cooked'])}" if batch else "#"
                if entry.get("cook", True):
                    minutes = dish.get("cook_minutes", 0)
                    note = tr(ctx, "cook, {n} min", n=f"{minutes:g}") if minutes else tr(ctx, "no cooking")
                else:
                    note = tr(ctx, "leftover from {day}", day=weekday_from(ctx, as_date(batch["cooked"]))) if batch else tr(ctx, "leftover")
                out.append(f'<a href="{href}">{esc(dish["name"])}</a><span class="note">{esc(note)}</span>')
                for label, amounts in plate_amounts(ctx, result, batches, day, meal, entry):
                    who = f"{esc(label)}: " if len(ctx["eaters"]) > 1 else ""
                    out.append(f'<span class="amounts">{who}{esc(amounts)}</span>')
            out.append("</div>")
        numbers = (result.get("days") or {}).get(day["date"], {})
        lines = [tr(ctx, "{label}: {kcal} kcal, protein {protein} g", label=esc(n["label"]), kcal=n["kcal"], protein=n["protein"])
                 for _, n in sorted((numbers.get("eaters") or {}).items())]
        if "cook_minutes" in numbers:
            lines.append(tr(ctx, "cooking {n} min", n=f"{numbers['cook_minutes']:g}"))
        if lines:
            out.append('<div class="daynums">' + "".join(f"<span>{line}</span>" for line in lines) + "</div>")
        out.append("</article>")
    out += ["</section>", f'<section class="recipes" aria-label="{tr(ctx, "Recipes")}">', f'<span class="label">{tr(ctx, "Recipes")}</span>']
    ordered = sorted(((b["cooked"], d, b) for d, bs in batches.items() for b in bs), key=lambda x: (x[0], x[1]))
    for cooked, dish_id, batch in ordered:
        dish = menu["dishes"][dish_id]
        total = sum(s[3] for s in batch["servings"]) or 1.0
        chips = [tr(ctx, "Cooked {day}", day=inside(ctx, day_words(as_date(cooked), ctx=ctx))),
                 tr(ctx, "{n} min hands-on", n=f"{dish.get('cook_minutes', 0):g}")]
        if dish.get("total_minutes"):
            chips.append(tr(ctx, "ready in {n} min", n=f"{dish['total_minutes']:g}"))
        if dish.get("equipment"):
            chips.append(equipment_words(ctx, dish["equipment"]))
        if abs(total - round(total)) > 0.005:
            chips.append(portion_words(ctx, total, 2))
        elif words_for(ctx):
            chips.append(portion_words(ctx, round(total)))
        else:
            chips.append(f"{total:.0f} portion{'s' if round(total) != 1 else ''}")
        out += [f'<article class="recipe" id="{recipe_anchor(dish_id, cooked)}">', f"<h3>{esc(dish['name'])}</h3>",
                '<div class="meta">' + "".join(f'<span class="chip">{esc(c)}</span>' for c in chips) + "</div>",
                '<div class="cols">', f'<div><span class="label">{tr(ctx, "Ingredients")}</span><table>']
        for item, (name, grams) in zip(dish["ingredients"], ingredient_rows(ctx, dish, total)):
            out.append(f'<tr><td>{esc(name)}</td><td class="g">{esc(amount_words(ctx, item["food"], grams))}</td></tr>')
        out.append("</table>")
        out.append(f'<span class="label">{tr(ctx, "Eaten")}</span><ul class="servings">')
        for date, meal, label, size in batch["servings"]:
            who = f"{label}, " if len(ctx["eaters"]) > 1 else ""
            out.append("<li>" + esc(tr(ctx, "{day} {meal}: {who}{portion}", day=short_day(as_date(date), ctx),
                                       meal=meal_word(ctx, meal), who=who, portion=portion_words(ctx, size))) + "</li>")
        out += ["</ul></div>", f'<div><span class="label">{tr(ctx, "Steps")}</span><ol>']
        out += [f"<li>{esc(step)}</li>" for step in dish.get("steps", [])]
        out += ["</ol></div>", "</div>", f'<a class="back" href="#week">{tr(ctx, "Back to the week")}</a>', "</article>"]
    out += ["</section>", "</main>"]
    return "\n".join(out) + "\n"


def command_page(args):
    ctx = load_project(args.project, args.which)
    result, _ = load_check(ctx, args.which, args.today)
    path = pathlib.Path(args.out) if args.out else ctx["data"] / "menu" / f"{args.which}.html"
    path.write_text(render_page(ctx, result, args.which), encoding="utf-8")
    dishes = sum(len(recipe_batches(ctx, result, d)) for d in ctx["menu"].get("dishes") or {})
    print(f"Page written: {path} ({len(ctx['menu'].get('days') or [])} days, {dishes} recipes)")


# ---------- saving ----------

def take_from_pantry(ctx, result, old_path, today):
    """Food at home that the saved menu uses is taken off the pantry record.

    If the menu being replaced had not started yet, what it had taken is put back first.
    """
    path = ctx["data"] / "pantry.json"
    if not path.exists():
        return
    pantry = json.loads(path.read_text("utf-8"))
    items = pantry.get("items") or []
    old_check = ctx["data"] / "menu" / "menu-check.json"
    if old_path.exists() and old_check.exists():
        old = json.loads(old_path.read_text("utf-8"))
        days = old.get("days") or []
        if days and days[0].get("date", "") > today:
            for food, grams in ((json.loads(old_check.read_text("utf-8")).get("cost") or {}).get("from_home") or {}).items():
                for item in items:
                    if item.get("food") == food and (item.get("state") or "raw") == "raw":
                        item["grams"] += grams
                        break
                else:
                    items.append({"food": food, "grams": grams, "state": "raw"})
    for food, grams in ((result.get("cost") or {}).get("from_home") or {}).items():
        left = grams
        for item in sorted((i for i in items if i.get("food") == food), key=lambda i: (i.get("state") or "raw") != "cooked"):
            used = min(left, item.get("grams", 0))
            item["grams"] = item.get("grams", 0) - used
            left -= used
    pantry["items"] = [i for i in items if i.get("grams", 0) >= 1]
    pantry["updated"] = today
    path.write_text(json.dumps(pantry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def command_save(args):
    ctx = load_project(args.project, "draft")
    folder = ctx["data"] / "menu"
    check_path = folder / "draft-check.json"
    if not check_path.exists():
        fail("The draft has not been checked. Run check first.")
    result = json.loads(check_path.read_text("utf-8"))
    if result.get("draft_fingerprint") != fingerprint(ctx["raw"]):
        fail("The draft changed after it was checked. Run check again.")
    if result.get("fix") and not args.accept_problems:
        fail(f"The draft still has {len(result['fix'])} problem(s) to fix. Fix them, or save with --accept-problems when the user accepts them.")
    old_path = folder / "menu.json"
    added = 0
    if old_path.exists():
        old = json.loads(old_path.read_text("utf-8"))
        history = ctx["history"]
        known = {(m.get("date"), m.get("meal"), m.get("dish")) for m in history.get("meals", [])}
        for day in old.get("days") or []:
            if day.get("date", "9999") >= args.today:
                continue
            for meal in MEALS:
                for entry in (day.get("meals") or {}).get(meal) or []:
                    name = (old.get("dishes") or {}).get(entry.get("dish"), {}).get("name")
                    if name and (day["date"], meal, name) not in known:
                        history.setdefault("meals", []).append({"date": day["date"], "meal": meal, "dish": name})
                        known.add((day["date"], meal, name))
                        added += 1
        (ctx["data"] / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    take_from_pantry(ctx, result, old_path, args.today)
    old_path.write_text(ctx["raw"], encoding="utf-8")
    (folder / "menu-check.json").write_text(check_path.read_text("utf-8"), encoding="utf-8")
    ctx["menu_path"].unlink()
    check_path.unlink()
    print(json.dumps({"saved": str(old_path), "days": len(ctx["menu"].get("days") or []),
                      "history_lines_added": added}, ensure_ascii=False))


def command_prices_needed(args):
    data = pathlib.Path(args.project) / "data"
    foods = json.loads((SKILL_DIR / "foods.json").read_text("utf-8"))
    path = data / "prices.json"
    known = (json.loads(path.read_text("utf-8")).get("foods") or {}) if path.exists() else {}
    today = as_date(args.today)

    def old(entry):
        checked = entry.get("checked")
        return not checked or (today - as_date(checked)).days > PRICE_MAX_AGE_DAYS

    new, stale = [], []
    draft_path = data / "menu" / "draft.json"
    if args.all:
        for food in sorted(set(foods) - FREE_FOODS):
            entry = known.get(food)
            if entry is None or (entry.get("missing") and old(entry)):
                new.append({"food": food, "name": foods[food].get("uk") or food.replace("_", " ")})
    elif draft_path.exists():
        draft = json.loads(draft_path.read_text("utf-8"))
        extra = draft.get("extra_foods") or {}
        used = {i.get("food") for d in (draft.get("dishes") or {}).values() for i in d.get("ingredients", [])}
        for food in sorted(used - FREE_FOODS):
            entry = known.get(food)
            if entry is None or (entry.get("missing") and old(entry)):
                source = foods.get(food) or extra.get(food) or {}
                new.append({"food": food, "name": source.get("uk") or food.replace("_", " ")})
    for food, entry in sorted(known.items()):
        if not entry.get("missing") and old(entry):
            stale.append({"food": food, "code": entry.get("code"), "title": entry.get("title")}
                         | ({"place": entry["place"]} if entry.get("place") else {}))
    remaining = 0
    if args.limit and len(new) > args.limit:
        remaining = len(new) - args.limit
        new = new[: args.limit]
    priced = sum(1 for e in known.values() if not e.get("missing"))
    print(json.dumps({"new": new, "stale": stale, "new_remaining": remaining, "priced_foods": priced,
                      "foods_in_table": len(set(foods) - FREE_FOODS)}, ensure_ascii=False, indent=1))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Menu tools for the shopper project.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "show", "save", "prices-needed", "buy-list", "cart-plan", "page"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--today", default=datetime.date.today().isoformat())
        if name == "check":
            p.add_argument("--judged-ok", action="store_true")
            p.add_argument("--add-fix", action="append", default=[])
            p.add_argument("--add-improve", action="append", default=[])
        if name == "buy-list":
            p.add_argument("--which", choices=("draft", "menu"), default="draft")
        if name == "page":
            p.add_argument("--which", choices=("draft", "menu"), default="menu")
            p.add_argument("--out")
        if name == "show":
            p.add_argument("--which", choices=("draft", "menu"), default="draft")
            p.add_argument("--day")
            p.add_argument("--recipe")
        if name == "prices-needed":
            p.add_argument("--all", action="store_true")
            p.add_argument("--limit", type=int)
        if name == "save":
            p.add_argument("--accept-problems", action="store_true")
    args = parser.parse_args(argv)
    {"check": command_check, "show": command_show, "save": command_save,
     "prices-needed": command_prices_needed, "buy-list": command_buy_list,
     "cart-plan": command_cart_plan, "page": command_page}[args.command](args)


if __name__ == "__main__":
    main()
