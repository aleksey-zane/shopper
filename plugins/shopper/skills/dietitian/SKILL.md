---
name: dietitian
description: Use when daily food targets have to be calculated, recalculated or shown - after the shopper profile is created or changed, when data/diet.md is missing or no longer matches data/profile.md, when the user asks how many calories, how much protein, or which weekly food rules their plan uses, or when a menu draft has to be checked against the diet.
---

# Dietitian

## Overview

The dietitian turns the profile into daily targets and weekly food rules for each eater and saves them in `data/diet.md`. It is the only writer of that file. It reads `data/profile.md` and never edits it. It also checks every menu draft against those targets and rules.

Every number comes from the script, never from a calculation done by hand, so the same profile always gives the same targets.

Every number in the method has a named source, or is marked as having none: see `method.md`, which ends with the list of sources. When the user asks where a number comes from, answer from it.

## Where the files are

`data/profile.md` and `data/diet.md` in the shopper project folder (the folder that contains `data/README.md`). If the working directory has no `data/README.md`, this is a new user: do the steps in `first-run.md` of the `profile` skill, a folder next to this skill's folder, first.

The script is `scripts/targets.py` in this skill's folder: `${CLAUDE_SKILL_DIR}/scripts/targets.py`. If `${CLAUDE_SKILL_DIR}` appears unreplaced, use the path of this skill's folder. Below, `<script>` means `python3` followed by that path, and `<files>` means `--profile <project>/data/profile.md --out <project>/data/diet.md`.

## Who does the work

The main conversation is the orchestrator: the user talks only to it.

- **Orchestrator, when a subagent named `shopper:dietitian` is available:** give it the job, the path of the shopper project folder and the language the user writes in. For Correct extra rules, also the eater's name and the user's words. Show the user the report it returns, word for word.
- **Orchestrator, when no such subagent exists:** do the job here, following this skill.
- **As the subagent:** do the job and return the report as your final answer. You cannot reach the user or wait for an answer; anything the user must decide goes into the report.

There are four jobs: Calculate, Show, Correct extra rules, and Check menu.

## Calculate

1. If `data/diet.md` exists, note each eater's `calories_kcal` from it.
2. Run `<script> <files>`.
3. If it stops with `... is missing in the profile`, the report is one line, `The profile is incomplete: <field> for <eater>.`, and the job ends. The orchestrator runs the profile skill and then starts Calculate again.
4. If it stops asking for `--base N=<pattern>`, that eater's way of eating is not on the list. Pick the listed way of eating whose foods are closest to the user's words and run again with `--base N=<pattern>` added. This is needed only the first time: the script remembers the base afterwards.
5. If the output has `"extra_rules_needed": true` for an eater, open `data/diet.md` and replace that eater's line `- to be written by the dietitian` with 3 to 6 rules that express the user's own words. Each rule names a food and how often, like the weekly rules above it.
6. Read `data/diet.md` and write the report.

## Show

Run `<script> <files> --check`. If it prints `stale`, do Calculate. If it prints `fresh`, read `data/diet.md` and write the report without the change lines.

## Correct extra rules

The orchestrator passes on what the user answered about one eater's unlisted way of eating.

- The user wants other rules: rewrite that eater's extra-rule lines in `data/diet.md` to match, adding, removing or rewording rules. Any number of rules is fine. Do not run the script.
- The user wants the numbers taken from another listed way of eating: run `<script> <files> --base N=<pattern>`. The extra rules are kept.
- A plain "yes" changes nothing.

The report is the whole frame and the closing line, without change lines and without the question.

## Check menu

The chef wrote a draft menu in `data/menu/draft.json`. This job sizes the portions and checks the draft. It never edits the draft.

The menu script is `scripts/menu_tools.py` in the `menu` skill's folder, which sits next to this skill's folder: `${CLAUDE_SKILL_DIR}/../menu/scripts/menu_tools.py`. If `${CLAUDE_SKILL_DIR}` appears unreplaced, use the path of this skill's folder in its place. Below, `<tools>` means `python3` followed by that path.

1. Run `<tools> check --project <project>`. It sizes each eater's portions to their calories, adds up the nutrition and the cost, checks the rules and the budget, writes `data/menu/draft-check.json` and prints three lists: `fix`, `improve` and `judge`.
2. If `judge` is empty, go to step 4.
3. Each `judge` line names something the script cannot decide. Read the dish names, ingredients and steps in `data/menu/draft.json` and decide it yourself. Decide only what the `judge` lines name. Then run the check once more to record the result:

   `<tools> check --project <project> --judged-ok`

   adding `--add-fix "<what is wrong, naming the dish>"` for each food never allowed or rule that is broken, and `--add-improve "<what could be better>"` for each lesser point.
4. Return the lines the script printed last, as plain lines under the headings `To fix` and `To improve`, word for word; leave out a heading that has no lines. This is a report for the orchestrator and the chef, not for the user: no frame, no closing line. When both lists are empty, the report is `The menu passes the check.`

## The report

This section is about the Calculate, Show and Correct extra rules jobs.

The report is what the user sees, in the language the user writes in (English when not told). Its parts, in this order:

1. Only when step 1 of Calculate found earlier values, one line per eater whose daily calories changed: `Olena · Daily calories: 2250 → 2400 kcal`.
2. The diet in plain words inside a frame, laid out as `show-format.md` in this skill's folder describes. Field names never appear.
3. Only in a Calculate where step 5 wrote extra rules, for that eater: `"<way of eating>" is not on the list. For <name>, the numbers use the <based_on> shares and the extra rules were written from that word. Are both right?`
4. This line: `These are general estimates, not medical advice.`

## Rules

- Run the script for every number. If no code can be run at all, follow `method.md` by hand and say in the report that the numbers were calculated by hand.
- Change `data/diet.md` only by running the script, or by writing extra rules as described above. The script keeps extra rules and the chosen base on later runs.
- An extra rule wins over a weekly rule when the two disagree.
- Hard limits and dislikes stay in the profile and are not copied here. A hard limit always wins over any rule in the diet.
- To change a target, the profile changes (weight, goal, way of eating, or the user's own daily calories), and then Calculate runs again. Never edit a number in `data/diet.md`.
