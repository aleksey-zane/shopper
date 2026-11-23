---
name: pantry
description: Use when the user says what food they already have at home, that something at home is used up or gone, or asks what is recorded as being at home, for the shopper project - so that menus use that food and shopping does not buy it again.
---

# Pantry

## Overview

`data/pantry.json` records the food that is already at home. The chef uses it first, and the menu script does not put it on the buy list. This skill is the only writer of that file, with one exception: when a menu is saved, the menu script takes the food that menu uses off the record.

## Where the file is

`data/pantry.json` in the shopper project folder (the folder that contains `data/README.md`). If the working directory has no `data/README.md`, this is a new user: do the steps in `first-run.md` of the `profile` skill, a folder next to this skill's folder, first. The foods it may name are the keys of `foods.json` in the `menu` skill's folder, which sits next to this skill's folder.

## The file

```json
{
  "updated": "2026-11-12",
  "items": [
    { "food": "chicken_breast", "grams": 1320, "state": "raw" },
    { "food": "chicken_breast", "grams": 660, "state": "cooked", "note": "cooked on 12 November" }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `food` | A key from `foods.json`. |
| `grams` | The weight as bought, of the raw product. A 660 g pack of chicken that has since been cooked still counts as 660. |
| `state` | `raw` or `cooked`. A cooked food has to be eaten in the first two days of the next menu. |
| `note` | Optional, a few words in the user's sense. |

One entry per food and state: add to its grams when the user has more of the same.

## Pick the job

| The user | Job |
| --- | --- |
| says what they have at home | Add |
| says something is used up, gone or spoiled | Remove |
| asks what is recorded as being at home | Show |

## Add

1. Match each food the user named to a key in `foods.json`. A food that is not in the table is not recorded: say so in one line and go on.
2. Work out the grams: `3 x 660 g` is 1980; a litre of milk or oil is 1000; an egg is 55. If the user gave no amount and it cannot be worked out, ask once, as a plain message with nothing else in it: **About how many grams of <food> do you have?**
3. Set `state` to `cooked` only for what the user said is already cooked; everything else is `raw`.
4. Write the file, with `updated` set to today.
5. Show what is now recorded for the foods that changed, one line per entry, in plain words in the user's language, then end with `Saved.` Example lines: `At home: chicken fillet 1320 g` and `At home: chicken fillet, cooked 660 g`.

## Remove

Lower the grams of the entry, or delete it when nothing is left. With no amount named, delete the entry. Show the change in plain words and end with `Saved.`

## Show

Print inside one fenced code block, in plain words, the food names in the language from the profile, then ask nothing:

```
At home
  куряче філе: 1320 g
  куряче філе, cooked: 660 g
Last updated: 12 November 2026
```

When nothing is recorded, the block holds `At home` and `  nothing recorded`.

## Rules

- Record only what the user said. Never guess what else is in the kitchen, and never read it from a store account.
- After Add or Remove, when a menu or a draft exists and the user did not already ask for the menu to be changed, add one line: `The menu was made before this change. Ask for the menu again to have it adjusted.`
