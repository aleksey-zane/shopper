# How the diet is shown to the user

Print the whole diet inside one fenced code block, so it appears in a frame. Use the words below, never the field names. Translate every word in the frame, the rules included, into the language of the report. No Markdown marks (`**`, `-`, `#`) inside the frame.

## Layout

One block per eater, in this order:

1. A first line with the name and the way of eating.
2. The fields, one per line, indented two spaces, in the order of the example below.
3. An empty line, the heading `Weekly rules` indented two spaces, then every weekly rule in the file, one per line, indented four spaces.
4. Only when the file has extra rules for that eater: an empty line, the heading `Extra rules (these win over the weekly rules)` indented two spaces, then every extra rule, indented four spaces.

One empty line between blocks. After the last block, an empty line and the calculation date.

The example below is shortened: it shows only two or three rules per eater. A real report shows all of them.

```
Olena · Mediterranean
  Daily calories: 1550 kcal
  Based on: measured weight (64 kg)
  Protein: 70 g
  Fat: 65 g
  Carbohydrates: 175 g
  Fibre: 22 g
  Breakfast: 430 kcal
  Lunch: 600 kcal
  Dinner: 520 kcal

  Weekly rules
    Vegetables at lunch and dinner every day
    Fish or seafood at least 2 times a week
    Red meat at most once a week

Taras · paleo
  Daily calories: 1450 kcal
  Shares taken from: balanced
  Based on: reference values for a child of this age
  Protein: 75 g
  Fat: 50 g
  Carbohydrates: 180 g
  Fibre: 20 g
  Breakfast: 400 kcal
  Dinner: 480 kcal
  Eaten outside the plan: 560 kcal
  Note: weight goal not applied under 18

  Weekly rules
    Vegetables or salad at lunch and dinner every day
    Fruit every day

  Extra rules (these win over the weekly rules)
    No bread, pasta or other grain foods
    No milk, cheese or yoghurt

Calculated: 12 November 2026
```

## Words for each field

| Field | Shown as |
| --- | --- |
| `label` and `way_of_eating` | the first line of the block: `<name> · <way of eating>`, both exactly as in the file |
| `calories_kcal` | `Daily calories: N kcal` |
| `calories_basis` | changes the lines as "Calories and their basis" below describes |
| `based_on` | only when the file has an Extra rules section for that eater: `Shares taken from: <based_on>` |
| `weight_basis`, `weight_used_kg` | the `Based on:` line, as below |
| `protein_g` | `Protein: N g` |
| `fat_g` | `Fat: N g` |
| `carbs_g` | `Carbohydrates: N g` |
| `fibre_g` | `Fibre: N g` |
| `breakfast_kcal`, `lunch_kcal`, `dinner_kcal`, `snacks_kcal` | `Breakfast: N kcal`, `Lunch: N kcal`, `Dinner: N kcal`, `Snacks: N kcal`. Leave out a line whose value is 0. |
| `outside_plan_kcal` | `Eaten outside the plan: N kcal`. Leave it out when it is 0. |
| `notes` | one `Note: ...` line per note; notes are separated by `;` in the file. Leave it out when it is `none`. |
| `calculated` | the last line: `Calculated:` and the date written out |

`age`, `height_used_cm`, `height_basis`, `profile_updated` and `profile_fingerprint` are not shown. Numbers are shown as they are in the file.

## Calories and their basis

| `calories_basis` | Calories line | `Based on:` line |
| --- | --- | --- |
| `calculated` | `Daily calories: N kcal` | from `weight_basis`, as below |
| `reference for age` | `Daily calories: N kcal` | `Based on: reference values for a child of this age` |
| `set by user` | `Daily calories: N kcal (set in the profile)` | `Based on: the number set in the profile` |
| `minimum safe level` | `Daily calories: N kcal (raised to the minimum safe level)` | from `weight_basis`, as below |

| `weight_basis` | `Based on:` line |
| --- | --- |
| `measured` | `Based on: measured weight (N kg)` |
| `healthy weight for height` | `Based on: a healthy weight for this height (N kg), because no weight was given` |
| `typical for age and sex` | `Based on: a typical healthy height and weight for this age, because none were given` |
