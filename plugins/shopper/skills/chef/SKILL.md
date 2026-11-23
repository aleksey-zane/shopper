---
name: chef
description: Use when a menu draft has to be composed, fixed or changed for the shopper project - choosing a dish for each meal of each day and writing the recipes. The menu skill calls it; the user does not talk to the chef directly.
---

# Chef

## Overview

The chef chooses the dishes for every meal and day and writes their recipes into `data/menu/draft.json`. It is the only writer of that file.

The chef does not size portions and does not calculate calories or costs: a script does that. The chef knows no store; it only reads a plain price list.

## Who does the work

- **As a subagent:** do the job and return a short report as your final answer: for Draft, how many dishes; for Fix and Change, which dishes you changed, added or removed; and in every case anything you could not satisfy or that the dietitian should know. You cannot reach the user.
- **In the main conversation** (no subagent available): do the job here, then go on with the menu skill.

## What to read first

All in the shopper project folder, except the food table.

| File | What to take from it |
| --- | --- |
| `data/profile.md` | Per eater: meals in the plan, foods never allowed, dislikes, favourites. Cooking: time limits, equipment, skill, leftovers. Budget: the amount and its period. Language. |
| `data/diet.md` | Per eater: way of eating, calories per meal, weekly rules, extra rules. |
| `data/menu/draft.json`, `data/menu/menu.json` | The lunch and dinner dish names already used, to avoid them. |
| `data/history.json` | Dishes eaten in the last 14 days, to avoid them. |
| `data/pantry.json` | Food already at home: the food, its grams as bought, and whether it is raw or cooked. |
| `data/prices.json` | For each priced food: the price, and the pack it is sold in. A food that is not listed has no price yet; one marked `missing` cannot be bought. |
| `foods.json` in the `menu` skill's folder (next to this skill's folder) | The foods a recipe may use, by key. |

The exact shape of the draft is in `draft-format.md` in this skill's folder.

## Draft

You are given a start date and a number of days, and sometimes special wishes in the user's words.

1. Read the files above. Make the avoid list: every lunch and dinner dish name in the existing `draft.json` and `menu.json`.
2. Choose the dishes, following "How to compose" below.
3. Write `data/menu/draft.json` in the shape of `draft-format.md`, with the avoid list in it.
4. Check that the file is valid JSON.

## Fix

You are given two lists from the dietitian: to fix and to improve.

Change as few dishes as possible so that every line to fix is cleared. A budget line is cleared by replacing the dishes and foods it names with cheaper ones, never by shrinking portions. Act on a line to improve when it is cheap. Leave everything else exactly as it is, and rewrite `data/menu/draft.json`. "After any job" below applies.

## Change

You are given the user's words about what to change.

If there is no `data/menu/draft.json`, start from a copy of `data/menu/menu.json`. Change only the meals the user named, and rewrite `data/menu/draft.json`. A day named by its weekday is the first such day in the menu. "After any job" below applies.

When the user asks for the menu in another language, or the menu's `language` differs from the profile's: set `language` to the profile's and rewrite every dish name and step in it, following "Words" below. Dishes, ids, ingredients, grams, days and minutes stay exactly as they are.

When the user asks to move the menu to another start date: set `range.start` to that date and move every day's `date` by the same number of days. Dishes, meals, their order, names and steps stay exactly as they are.

## After any job

- A new or changed dish follows "How to compose", and so does the day it lands on.
- A dish that keeps its name keeps its id. A new dish gets a new id that fits it.
- A dish with no serving left is removed from `dishes`.
- `range` and `avoid` stay as they are in Fix and Change, and so does `language`, except when a Change sets them.
- The file must be valid JSON: check it.

## How to compose

- **Special wishes.** What the user asked for this time comes before the other rules here, except foods never allowed. A meal the user will eat elsewhere gets no dish: leave its list empty and name the meal in that day's `out`.
- **Meals.** Each eater gets every meal that is in their plan, on every day, except meals in `out`. Eaters share dishes. When a food never allowed for one eater is in a shared dish, give that eater another dish for that meal, with `"eaters": [n]` on both entries.
- **One portion.** Write every recipe for one portion of an ordinary adult meal: breakfast about 450 to 600 kcal, lunch 600 to 800, dinner 550 to 750, snacks 150 to 250. The dietitian's script scales each eater's portion between 0.6 and 1.8 of it, so a dish far outside these sizes cannot be made to fit.
- **The way of eating.** Follow each eater's weekly rules and extra rules from `data/diet.md`. For a menu shorter or longer than a week, keep the same proportion: "fish at least 2 times a week" means about once in three days. A food never allowed must not appear at all, under any name or in any form. Leave out disliked foods.
- **Cooking time.** `cook_minutes` is the honest hands-on time of a dish: preparing, and cooking that needs someone at the stove. Time when the food cooks without anyone watching it, such as baking, simmering under a lid or a multicooker programme, does not count, and goes into `total_minutes`. The hands-on minutes of everything cooked on one day must fit that day's limit; working days and weekend days have separate limits. Never lower a dish's minutes to make a day fit: choose a quicker dish.
- **Leftovers.** Follow `leftovers` in the profile. When a dish may come back, cook it once and serve it again with `"cook": false`, to save cooking.
- **Breakfasts and snacks.** Two breakfasts that alternate. Snacks need no cooking: `cook_minutes` 0.
- **Variety.** A lunch or dinner dish is served at most twice in seven days. Nothing from the avoid list or from the last 14 days of the history.
- **Food at home.** Use the foods in `data/pantry.json` first, and as much of them as the days and the other rules allow: they are already paid for and do not count against the budget. A cooked food at home is eaten in the first two days of the menu, in dishes whose steps take it ready-cooked; count hands-on minutes only for the rest of the dish. Ingredient grams stay the raw weight.
- **Budget.** The whole menu, bought in whole packs, must cost no more than the budget for its number of days: the budget amount times the days, divided by 7 for a weekly budget, 14 for two weeks, 30 for a month. Three habits keep it there:
    - Build dishes from the cheaper foods in the price list: per kilogram, a pack price divided by its `pack_grams`, or the `price` itself for a food sold by weight.
    - Use few different foods, and use each one in several dishes, so that packs are finished. A food needed in a small amount from a dear pack is a bad choice.
    - Prefer foods that have a price. A food marked `missing` cannot be bought: do not use it.
- **Kitchen.** Only the equipment in the profile, and nothing beyond the cooking skill in it.
- **Cuisine.** The eaters' favourites first. With none, everyday home cooking of the country whose language the menu is in.
- **Ingredients.** Only food keys from `foods.json`, in grams of the raw product as bought. When a food is missing, use the closest listed one, or add it under `extra_foods` with honest estimates.
- **Words.** Dish names and steps in the language from the profile, in everyday words a home cook knows. One to eight short steps per recipe. A step that uses only part of a food names its share ("half of the oil", "the rest of the oil", never "part of the oil"): the script scales amounts to the pot, so steps never carry spoons or grams. A step that cuts says how thick or how big the pieces are; a step that tops or coats says what goes on what.
