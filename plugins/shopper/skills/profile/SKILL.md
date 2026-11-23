---
name: profile
description: Use when the user wants to set up, see, review or change who the meal plan is for (household members, way of eating, allergies, dislikes, weight goals, their own daily calories, cooking time, equipment, budget, menu language), or when another shopper skill finds data/profile.md missing or incomplete.
---

# Profile

## Overview

The profile is the single record of who is being fed: eaters, limits, cooking and budget. It is store-independent: nothing in it comes from, or goes to, a grocery service. This skill is the only writer of `data/profile.md`. Every other skill reads it and never edits it.

## Where the file is

`data/profile.md` in the shopper project folder (the folder that contains `data/README.md`). If the working directory has no `data/README.md`, this is a new user: do the steps in `first-run.md` in this skill's folder first. With no file access at all, produce the file as a code block for the user to save.

## Pick the mode

| Situation | Mode |
| --- | --- |
| `data/profile.md` does not exist | Create |
| File exists and a field is empty or missing | Complete |
| User states a change ("budget is 5000 now", "add a nut allergy for Olena", "add my son", "set my calories to 2200") | Change |
| User asks to see the profile | Show |
| User asks to review it, or Show finds `updated` older than 90 days | Review |

When another skill sent the user here, finish the mode, say in one line that the profile is ready, then continue with that skill.

## Create

1. Read `questions.md` in this skill's folder. It is the complete, fixed question list. When the user asked for something else (a menu, an order) and the interview starts because there is no profile yet, first say in one line: `First, a few questions about who will eat from the plan.`
2. Ask one question per message, in list order, as "How to ask" in `questions.md` describes. Ask all eater questions for one eater before the next eater.
3. After the last question, send one plain message with two parts: first the profile in the Show format, as a preview, with today's date as the last-updated line; then the question in bold, **Save this profile?**, followed by the line `Reply yes or no.` Do not use a question tool for this question, even when one is available: its dialog can cover the preview, and the user must see the preview while answering. The preview appears once, right above the question. Never ask to save without it.
4. On yes, write the file in the shape of `profile-template.md` (its values are examples), with `updated` set to today and a change log holding one line: `- YYYY-MM-DD: created`. Then say in one line that it is saved.
5. Run the dietitian, as "The dietitian" below describes.

## Complete

1. Ask only the fields that are empty or missing, one at a time, in list order, with the same wording and options. A field holding `skipped`, `none`, `n/a` or any other value is filled: do not ask it again.
2. Save without asking for confirmation. Set `updated` to today and append one change log line: `- YYYY-MM-DD: filled <field>, <field>`.
3. Say in one line what was saved, in words from `show-format.md`, with the eater's name before an eater field: `Saved: Olena · Way of eating: balanced; Food budget: 6000 UAH per 2 weeks.`
4. If a filled field is on the dietitian's list below, run the dietitian.

## Change

1. Map what the user said to field ids. If it is unclear which eater is meant, ask which one.
2. Apply the change. For a list field, add or remove the item the user names; replace the whole list only when the user gives the whole list. Ask nothing else.
3. Show each change on its own line, as plain lines outside any frame, in words from `show-format.md`, never as field names. Fields that share one shown line, such as the budget amount and period, are shown as one change. A household field: `Food budget: 4000 UAH per week → 5000 UAH per week`. An eater field starts with the eater's name: `Olena · Foods never allowed: peanuts → peanuts, tree nuts`.
4. Set `updated` to today and append one change log line per changed field to the file, in field names: `- YYYY-MM-DD: budget_uah: 4000 → 5000`, `- YYYY-MM-DD: Eater 1 (Olena) · hard_limits: peanuts → peanuts, tree nuts`.
5. Give every line from "After a change" that matches a changed field, each once, starting with what it is about in words, with the eater's name for an eater field: `Olena · Disliked foods: applies from the next menu.`
6. End with one line: `Saved.`
7. If a changed field is on the dietitian's list below, run the dietitian.

The user's own daily calories: "set my calories to 2200" stores `calories_override: 2200` for that eater; "use the calculated calories again" stores `none`. This field is never asked in the interview.

Adding an eater: ask the eater questions for the new eater only, one at a time, prefixed `Eater N of M` with M the new total. Save the new section, raise `eaters_count`, and log two lines: `eaters_count: 2 → 3` and `Eater 3 (Petro) added`. Show `People eating from the plan: 2 → 3`, then the new eater's section alone in a frame, give the "After a change" line for `meals_at_home`, end with `Saved.`, and run the dietitian.

Removing an eater: confirm once with `Remove Petro from the plan?` and the options yes / no. On yes, delete the section, renumber the rest, lower `eaters_count`, and log `eaters_count: 3 → 2` and `Eater 3 (Petro) removed`. Show `People eating from the plan: 3 → 2` and `Petro: removed from the plan`, end with `Saved.`, and run the dietitian.

## Show

Print the profile in plain words, exactly as `show-format.md` lays it out. The user never sees field names such as `cook_time_weekday_min` or stored markers such as `skipped` and `n/a`; those exist only in the file. Leave out the change log. Do not ask questions.

## Review

Show the profile, ask once "What has changed?", apply the answer as a Change, and set `updated` to today even when nothing changed.

## Rules

- The questions in `questions.md` are the only questions. Same wording, same order, same options, every time, one question per message. A follow-up is allowed only for the cases listed under "Follow-ups" in that file.
- Values come only from the user's answers. A value suggested by another skill or source is shown to the user and saved only after they say yes.
- Store the food rule, never the diagnosis behind it.
- These do not belong in the profile: address, payment or store logins, diet targets, pantry contents, one-off events such as guests or travel.

## The dietitian

The dietitian calculates each eater's daily targets from the profile and keeps them in `data/diet.md`. Run it after Create, and after any save that touched one of these fields: `eaters_count`, `label`, `birth_year`, `sex`, `height_cm`, `weight_kg`, `activity`, `meals_at_home`, `goal`, `goal_pace`, `way_of_eating`, `calories_override`.

To run it: when a subagent named `shopper:dietitian` is available, give it the Calculate job, the path of the shopper project folder and the language the user writes in. Otherwise load the `dietitian` skill and do its Calculate here. Either way, show the user its report word for word, as a message of its own after the `Saved` line. The profile skill never calculates targets itself and never writes `data/diet.md`.

## After a change

| Changed field | Tell the user |
| --- | --- |
| `hard_limits` | If a saved menu exists (`data/menu/menu.json`): that menu and its shopping list may contain that food and need rechecking. |
| `meals_at_home`, `dislikes`, `favourites`, any Cooking field, `language` | Applies from the next menu. |
| Any Budget field | Applies from the next shopping list. |
