# How the profile is shown to the user

Whenever the profile, or a change to it, is shown to the user, use the words below, never the field names. If the user writes in another language, translate the words faithfully.

## Layout

Print the whole profile inside one fenced code block, so it appears in a frame. Inside the frame: a section name on its own line, then one line per field in the order below, indented two spaces: the words, a colon, the value. One empty line between sections. No Markdown marks (`**`, `-`, `#`) inside the frame.

```
Household
  People eating from the plan: 2

Olena
  Year of birth: 1991
  Sex: female
  Height: 168 cm
  Weight: 64 kg
  Activity level: light
  Times of day in the plan: breakfast, lunch, dinner
  Weight goal: lose, slowly
  Way of eating: Mediterranean
  Foods never allowed: peanuts
  Disliked foods: liver, olives
  Favourite foods or cuisines: Italian, soups

Taras
  Year of birth: 2019
  Sex: not given
  Height: not given
  Weight: not given
  Activity level: light
  Times of day in the plan: breakfast, dinner
  Weight goal: maintain
  Way of eating: balanced
  Foods never allowed: none
  Disliked foods: none
  Favourite foods or cuisines: none

Cooking
  Cooking time on working days: up to 30 minutes a day
  Cooking time on Saturday and Sunday: up to 60 minutes a day
  Kitchen equipment: stove, oven
  Repeating a cooked dish: the next day
  Cooking skill: comfortable

Budget
  Food budget: 4000 UAH per week
  Favourite brands: none

Language
  Menus and recipes: Ukrainian

Last updated: 11 November 2026
```

## Words for each field

| Field | Shown as | Value shown as |
| --- | --- | --- |
| `eaters_count` | People eating from the plan | the number |
| `label` | the name line of the eater's section | the name |
| `birth_year` | Year of birth | the year |
| `sex` | Sex | as stored |
| `height_cm` | Height | the number, then `cm` |
| `weight_kg` | Weight | the number, then `kg` |
| `activity` | Activity level | as stored |
| `meals_at_home` | Times of day in the plan | as stored |
| `goal` and `goal_pace` | Weight goal | `maintain`, or `lose, slowly`, `lose, at a moderate pace`, `gain, slowly`, `gain, at a moderate pace` |
| `way_of_eating` | Way of eating | as stored |
| `calories_override` | Daily calories set by you | `N kcal`; the line is left out when the value is `none` and comes right after Way of eating. In a change line, `none` is shown as `not set`: `Olena · Daily calories set by you: not set → 2400 kcal` |
| `hard_limits` | Foods never allowed | as stored |
| `dislikes` | Disliked foods | as stored |
| `favourites` | Favourite foods or cuisines | as stored |
| `cook_time_weekday_min` | Cooking time on working days | `up to N minutes a day` |
| `cook_time_weekend_min` | Cooking time on Saturday and Sunday | `up to N minutes a day` |
| `equipment` | Kitchen equipment | as stored |
| `leftovers` | Repeating a cooked dish | `no`, `the next day`, or `for up to 3 days` |
| `cooking_skill` | Cooking skill | as stored |
| `budget_period` and `budget_uah` | Food budget | `N UAH per week`, `per 2 weeks`, or `per month` |
| `favourite_brands` | Favourite brands | as stored |
| `language` | Menus and recipes | as stored |
| `updated` | Last updated | the date written out, as the last line |

A stored `skipped` is shown as `not given`. `goal_pace` never gets a line of its own.
