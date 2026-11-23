---
name: menu
description: Use when the user asks for a menu or meal plan for a week, a month or any number of days, asks for another variant of the menu, wants to change a meal in it, asks what is on the menu, how to cook a dish from it or for the recipes page, or asks whether the menu's food is available at the store.
---

# Menu

## Overview

There is one menu at a time. This command makes a draft, the user sees a preview, and saving it replaces the saved menu. Calling the command again gives another variant; the saved menu stays in place until a new one is saved.

These roles do the work, and the user talks only to the orchestrator, the main conversation:

| Who | Does |
| --- | --- |
| Orchestrator | Works out the range, hands out the jobs, shows the preview, asks the save question |
| Store skill | Keeps the price list of the foods, from the store, and fills the cart for a saved menu |
| Chef | Chooses the dishes within the budget and writes the recipes |
| Dietitian | Sizes the portions and checks the draft against the diet and the budget |

For each role: when a subagent named `shopper:chef`, `shopper:dietitian` or `shopper:silpo-store` is available, give it the job, the path of the shopper project folder and the language the user writes in. Otherwise load the `chef`, `dietitian` or `silpo-store` skill and do the job here.

## Where things are

`data/menu/` in the shopper project folder (the folder that contains `data/README.md`): `draft.json` and `draft-check.json` for the draft, `menu.json` and `menu-check.json` for the saved menu. The orchestrator never edits these files. If the working directory has no `data/README.md`, this is a new user: do the steps in `first-run.md` of the `profile` skill, a folder next to this skill's folder, first.

The script is `scripts/menu_tools.py` in this skill's folder: `${CLAUDE_SKILL_DIR}/scripts/menu_tools.py`. If `${CLAUDE_SKILL_DIR}` appears unreplaced, use the path of this skill's folder. Below, `<tools>` means `python3` followed by that path, and `<P>` means `--project` followed by the shopper project folder.

## Pick the job

| The user | Job |
| --- | --- |
| asks for a menu, or for another variant | New menu |
| wants something in the menu changed ("swap Tuesday dinner", "something quicker on Wednesday") | Change |
| asks what is on the menu, what to eat on a day, for a recipe, for the recipes page, or what to buy | Show |
| asks whether the menu's food is at the store, or to check the menu against the store | Store check |

When the user's message also says what food they already have at home, run the `pantry` skill first, then the job. The chef and the cost calculation then use that food and it is not bought.

## New menu

Ask the user nothing until the save question, except what a missing profile or delivery setup asks (a new user).

1. **Diet.** Run `python3 <dietitian skill folder>/scripts/targets.py --profile <project>/data/profile.md --out <project>/data/diet.md --check`. If it says the profile is not found, run the `profile` skill first, then run the check again. If the answer is `stale`, give the dietitian the Calculate job and show its report.
2. **Range.** From the user's words: a week is 7 days, 2 weeks 14, a month 30, "N days" N. If the user named none, use `budget_period` from `data/profile.md` in the same way.
3. **Start date.** The date the user named; a weekday means the next such day, counting from tomorrow. Otherwise the day after the next `preferred_day` found in a file in `data/stores/`, counting from tomorrow. If `data/stores/` has no file yet, do the store skill's Delivery setup first.
4. **Store: Price list.** The chef must have prices before it composes. Run `<tools> prices-needed <P> --all`: when `priced_foods` is less than three quarters of `foods_in_table`, give the store the Price list job for the whole food table, and repeat it until its report says no foods remain. Otherwise give it the job once, to refresh prices older than a week.
5. **Chef: Draft.** Pass the start date, the number of days, and anything special the user said, in their words.
6. **Store: Price list** again, this time not for the whole table. It prices the foods of the draft that had no price yet.
7. **Dietitian: Check menu.** It returns two lists, to fix and to improve, or says that the menu passes. A menu over the budget is a line to fix.
8. **Fix rounds.** While there is something to fix, and at most three times: give the chef the Fix job with both lists, then the store Price list, then the dietitian Check menu again. Points to improve alone never start a round.
9. **Preview and save question,** as below.

## Preview and save question

Run `<tools> show <P> --which draft` and send one plain message with two parts: first the script's output inside one fenced code block, unchanged except for the lines under Check, which are translated as the Rules below say; then the question in bold, **Save this menu?**, followed by the line `Reply yes or no, or say what to change.`

Do not use a question tool for this question, even when one is available: its dialog can cover the preview. Never ask to save without the preview right above the question.

- **yes:** run `<tools> save <P>`. If the preview listed things to fix and the user said yes anyway, add `--accept-problems`. Say in one line that the menu is saved, give the recipes page as below, and continue with the store skill's Order job (`cart.md` in the `silpo-store` skill's folder): it prepares the priced list and asks before anything goes into the cart.
- **no:** say in one line that the saved menu is unchanged. The draft stays.
- **anything else** is a change: do the Change job.

## Recipes page

Every saved menu gets a web page: the days at the top, each dish a link that opens its recipe (ingredients for the portions cooked, in the measures below, steps, cooking time) further down the page.

1. Run `<tools> page <P>`. It writes `data/menu/menu.html`.
2. Publish that file as a page the user can open: in Claude, an Artifact, with the icon `recipe` and the description `Dishes for each day, with recipes.` A newly saved menu gets a new page; publishing again for the same menu in the same conversation updates its page. Where no page can be published, send the file itself.
3. Send one line with the link: `Recipes for this menu: <link>`.

## Store check

The user wants to know whether the saved menu's food is at the store now. Only look; nothing goes into the cart in this job.

1. Do the Prepare order part of the store skill's Order job (`cart.md` in the `silpo-store` skill's folder). It only reads from Silpo, and its preview lists every product with today's price, products that replace one no longer sold (`instead of`), short stock (`only ... in stock`), and under `Not at the store` what Silpo does not have.
2. Send one plain message: the preview inside one fenced code block, unchanged; then:
   - if the preview shows foods not at the store or short of stock: the question in bold, **Change the dishes that use them?**, followed by `Reply yes or no.`
   - otherwise: the line `Everything the menu needs is at the store. Say "fill my cart" to order it.` and no question.
3. **yes:** do the Change job, telling the chef which foods are missing or short and that the dishes using them must change. After the user saves the changed menu, the Order job runs as after any save.
   **no:** say in one line that the menu is unchanged.

## Change

1. Give the chef the Change job with the user's words.
2. Store: Price list, then dietitian: Check menu, then fix rounds as in New menu.
3. Preview and save question.

## Show

| The user asks | Run |
| --- | --- |
| the whole menu | `<tools> show <P> --which menu` |
| one day ("what's for dinner tomorrow?") | `<tools> show <P> --which menu --day YYYY-MM-DD` |
| a recipe | `<tools> show <P> --which menu --recipe "<dish name>"`, with `--day` when the user named a day |
| how much of a food or dish to eat or drink ("how much kefir at a time?", "how much plov on Monday?") | `<tools> show <P>` with `--which` as below, and `--day` when the user named a day; answer in plain lines, without a code block: one short line per different amount, with the days it is on, taken from the lines under the meals. For a cooked dish give the share of the pot and the grams in that line. This row wins over the one-meal rule below. |
| how much of a food to put in when cooking a dish ("how much oil goes into the plov?") | `<tools> show <P>` with `--recipe` as above; answer in plain lines, without a code block, from the recipe's ingredient lines: those are for the whole pot. This row wins over the how-much row above. |
| what to buy | `<tools> buy-list <P> --which menu` |
| the recipes page, or all the recipes | the Recipes page steps above |

To order what the saved menu needs ("fill my cart", "order the food"), use the store skill's Order job.

Except for the how-much rows, print the output inside one fenced code block, unchanged except for the lines under Check, and ask nothing. If there is no saved menu but there is a draft, say so in one line and use `--which draft`. While a draft preview waits for the user's answer to the save question, a question about the menu is about that draft: use `--which draft`, and say in one line that the draft is not saved yet.

- A day named by its weekday is the first such day in the menu from today on; if there is none, the first such day in the menu.
- A question about one meal ("what's for dinner on Monday?") is answered with that whole day.
- A recipe asked for by its meal ("the recipe for Monday's dinner") is found by reading that day's output for the dish name first.

## Rules

- Under every meal the script prints what each eater puts on the plate: the amount of each ingredient, and for a dish cooked for several servings, the share of the pot. Weights are raw, before cooking; for a cooked dish the share of the pot is what goes on the plate. When the user asks how much of something to eat or drink, answer from these lines.
- Amounts, there and in recipes, are in the measure a cook uses: eggs and garlic in pieces and cloves; fruit, vegetables, bread and canned food in pieces, slices or cans, with the grams in brackets; oil, sauces and pastes in spoons (`tbsp` a tablespoon, `tsp` a teaspoon); salt and spices `to taste`; drinks in millilitres; everything else in grams. The script writes them in the menu's language.
- Numbers and dish names always come from the script's output. Never retype, round or recalculate them.
- The menu is in one language: the menu's language, set in the profile, whatever language the user writes in. The script prints days, meals, amounts, units, dish and food names, recipes and the page in it; keep them as printed. A how-much answer quotes them, so it is written wholly in the menu's language, its own words included. Only the lines under Check are in English, for the chef and the dietitian: when showing them, translate them into the menu's language, with their numbers and dish names unchanged; a food named in English there takes the name the menu uses for it. Your own sentences around the menu are in the language the user writes in.
- One menu is saved at a time. Nothing is saved without the user's yes. Saving takes the food the menu uses from home off the pantry record.
- The store's and the dietitian's reports are for the orchestrator; the user sees the preview.
- The budget is checked on what has to be bought, in whole packs, for the days of the menu. Only the store skill talks to a store; this skill and the chef see prices as a plain list.
