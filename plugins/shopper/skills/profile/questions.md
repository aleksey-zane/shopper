# Profile questions

This is the complete question list. Ask the questions in this order, with this wording and these options. If the user writes in another language, translate the wording and options faithfully and keep the same questions, order and options.

## How to ask

- One question per message. Wait for the answer before asking the next one.
- Every eater question starts with `Eater N of M: `, for example `Eater 1 of 2: Year of birth?`.
- An option marked `(default)` is shown with that mark and listed first.
- Some options have a short explanation, listed under their table. With a tool, it is the option's description. Without a tool, it follows the option after a dash: `b) high-protein - more meat, fish, eggs, dairy and beans`.
- An answer the user already gave in this conversation for the same field and the same eater is listed first, marked `(your earlier answer)`. For a typed-only question it goes on the second line instead: `Type a name or nickname, or "yes" to keep Ira.`

A question has one of three forms, decided by its Options and Free text columns.

**Typed only** (Options says `typed only`): two lines, the question in bold, then `Type <the Free text column>.` When Options says `typed only, or skip`, the second line ends with `Type "skip" to leave it empty.`

```
**Eater 1 of 2: Height in cm? (only used to estimate calories)**
Type a number, 50 to 230. Type "skip" to leave it empty.
```

**Options with a tool:** when a tool for asking the user a question with selectable options is available, use it: one question per call, the listed options as its choices, multiple selection on for `many` questions. The tool supplies the free-text choice itself.

**Options without a tool:** the question in bold, the options as a lettered list, then one closing line. Letters, not numbers, because some answers are numbers.

```
**Most you want to spend on food per week, in UAH?**

a) 2000
b) 3000
c) 4000
d) 5000

Reply with a letter, or type your own answer.
```

The closing line is built from the Pick and Free text columns:

| Pick | Free text | Closing line |
| --- | --- | --- |
| one | accepted | Reply with a letter, or type your own answer. |
| one | not accepted | Reply with a letter. |
| many | accepted | Reply with one or more letters, and type anything that is missing. |
| many | not accepted | Reply with one or more letters. |

Typing an option's own words counts as picking that option. So does typing "default" for the option marked `(default)`.

## How answers are stored

- A picked option is stored as its text, without the `(default)` mark.
- A typed answer is stored as typed when it fits the Free text column. When it does not, ask the follow-up below.
- The `skip` option stores `skipped`.
- Several picked options are stored comma-separated, in the order of the Options column, followed by anything typed.
- `none` is stored as `none`.

## Block 1: Household

| Id | Field | Question | Options | Free text | Pick |
| --- | --- | --- | --- | --- | --- |
| H1 | `eaters_count` | How many people eat from this plan? | 1 / 2 / 3 / 4 | whole number, 1 to 10 | one |

## Block 2: Eater (all questions once per eater)

| Id | Field | Question | Options | Free text | Pick |
| --- | --- | --- | --- | --- | --- |
| E1 | `label` | What should I call this person? | typed only | a name or nickname | one |
| E2 | `birth_year` | Year of birth? | typed only | four-digit year | one |
| E3 | `sex` | Sex? (only used to estimate calories) | male / female / skip | not accepted | one |
| E4 | `height_cm` | Height in cm? (only used to estimate calories) | typed only, or skip | number, 50 to 230 | one |
| E5 | `weight_kg` | Weight in kg? (only used to estimate calories) | typed only, or skip | number, 3 to 300 | one |
| E6 | `activity` | Activity level? | light (default) / sedentary / moderate / active | not accepted | one |
| E7 | `meals_at_home` | Which times of day should the plan give this person food? Leave out a time when this person eats somewhere else, for example lunch at work. | breakfast (morning) / lunch (midday) / dinner (evening) / snacks (in between) | not accepted | many |
| E8 | `goal` | Weight goal? | maintain (default) / lose / gain | not accepted | one |
| E9 | `goal_pace` | How fast? | slow (default) / moderate | not accepted | one |
| E10 | `way_of_eating` | Which way of eating do you want for this person? | balanced (default) / high-protein / Mediterranean / vegetarian | another way of eating, in your own words, for example vegan, pescatarian, low-carb or keto | one |
| E11 | `hard_limits` | Which foods must this person never get: allergies, intolerances, religious or ethical exclusions? | none / gluten / lactose / nuts | list of foods | many |
| E12 | `dislikes` | Which foods does this person dislike? | none (default) / fish / mushrooms / spicy food | list of foods | many |
| E13 | `favourites` | Favourite foods or cuisines? | none (default) / Ukrainian / Italian / Asian | list of foods or cuisines | many |

E7 is stored without the words in brackets: `breakfast, lunch, dinner`.

Ask E9 only when `goal` is `lose` or `gain`. When `goal` is `maintain`, do not ask it and store `goal_pace` as `n/a`.

Explanations for the E10 options:

| Option | Explanation |
| --- | --- |
| balanced | a mix of all foods, nothing left out |
| high-protein | more meat, fish, eggs, dairy and beans |
| Mediterranean | many vegetables, fish, olive oil and beans, little red meat |
| vegetarian | no meat and no fish; eggs and dairy stay |

`calories_override` is an eater field that is never asked. It is stored as `none` in a new profile and changes only when the user asks to set their own daily calories. When it is missing from an existing profile, add it as `none` without asking and without mentioning it.

## Block 3: Cooking

| Id | Field | Question | Options | Free text | Pick |
| --- | --- | --- | --- | --- | --- |
| C1 | `cook_time_weekday_min` | On a working day (Monday to Friday), how many minutes per day do you want to spend cooking, at most? | 30 (default) / 15 / 45 / 60 | whole number, 0 to 240 | one |
| C2 | `cook_time_weekend_min` | On Saturday or Sunday, how many minutes per day do you want to spend cooking, at most? Longer times here allow bigger recipes and cooking ahead for the week. | same as working days / 60 / 90 / 120 | whole number, 0 to 240 | one |
| C3 | `equipment` | Which of these do you have? | stove / oven / microwave / multicooker | other equipment, such as air fryer, blender, grill | many |
| C4 | `leftovers` | Can the plan repeat a cooked dish on later days, so that you cook once and eat it again? | next day (default) / no / up to 3 days | not accepted | one |
| C5 | `cooking_skill` | Cooking skill? | comfortable (default) / beginner / advanced | not accepted | one |

For C2, `same as working days` stores the number given for C1.

## Block 4: Budget

| Id | Field | Question | Options | Free text | Pick |
| --- | --- | --- | --- | --- | --- |
| B1 | `budget_period` | For which period do you want to set a food budget? | week (default) / 2 weeks / month | not accepted | one |
| B2 | `budget_uah` | Most you want to spend on food per <period>, in UAH? | see below | whole number above 0 | one |
| B3 | `favourite_brands` | Which food brands do you trust? When the budget has room, they are bought instead of the cheapest product. | none (default) | brand names, separated by commas; a brand meant for some foods only gets those foods in brackets after it | one |

In B2, `<period>` is the answer to B1, and the options depend on it:

| B1 answer | B2 options |
| --- | --- |
| week | 2000 / 3000 / 4000 / 5000 |
| 2 weeks | 4000 / 6000 / 8000 / 10000 |
| month | 8000 / 12000 / 16000 / 20000 |

The budget always covers food only. Do not ask what it covers. There is no price level question: products are the cheapest that fit, and the favourite brands of B3 replace them while the period's total stays within the budget. B3 stores the brands as typed, comma-separated, or `none`. A brand the user wants for some foods only is stored with those foods in brackets: "Яготинське only for kefir" is `Яготинське (кефір)`.

## Block 5: Language

| Id | Field | Question | Options | Free text | Pick |
| --- | --- | --- | --- | --- | --- |
| L1 | `language` | Which language for menus and recipes? | Ukrainian / Russian / English | not accepted | one |

## Follow-ups

Ask a follow-up only in these cases, once per answer. A follow-up says in a few words what was wrong with the answer, then repeats the question with its options. Example:

`2031 is in the future. Eater 1 of 2: Year of birth?`

| Case | Follow-up |
| --- | --- |
| A typed answer where the Free text column says "not accepted", or outside the stated range | Repeat that question. |
| `none` picked together with other options | Repeat that question. |
| No option picked on a `many` question that has no `none` option | Repeat that question. |
| E11 names a diagnosis or condition instead of foods | Send only this sentence, with no options: "Which foods should be excluded or limited because of that?" Store the foods, not the condition. |
| `birth_year` is in the future or more than 110 years ago | Repeat E2. |
