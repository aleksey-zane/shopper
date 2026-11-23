# Silpo delivery settings

Delivery is always to the user's door. The user is never asked how the order should reach them or where it ships from.

Silpo ships an order to the door from one of two places, each with its own branch: the regular store (`DeliveryHome`) or a bigger warehouse with a wider range (`WideAssortDelivery`). Delivery setup stores both branches for the address. Which one a given order ships from is decided at shopping time, by which covers the shopping list best. Pickup from a store, Nova Poshta and business delivery are not used.

## How to ask

- One question per message. Wait for the answer before asking the next one.
- The questions below are the only questions, in this order, with this wording. If the user writes in another language, translate faithfully.
- When a tool for asking the user a question with selectable options is available, use it: one question per call, the options as its choices.
- Without such a tool: the question in bold, the options as a lettered list (`a)`, `b)` ...), then the closing line given with the question. Typing an option's own words counts as picking it.
- A follow-up is allowed only where a question below names one. It says in a few words what was wrong, then repeats the question.

## Silpo tools used here

All of them only read.

| Tool | Arguments |
| --- | --- |
| `silpo_get_my_delivery_addresses` | none |
| `silpo_find_address` | `address`: the typed text |
| `silpo_get_available_delivery_types` | `latitude`, `longitude` |
| `silpo_get_time_slots` | `branchId`, `deliveryTypes`: a list holding the one Silpo type |

Within one job, slots already fetched for a branch and type are used again; do not fetch them twice. A new job fetches them again.

## Delivery setup

Ask D1 to D3 in order, then show the review and save.

### D1: address

Call `silpo_get_my_delivery_addresses`.

**Which address should Silpo deliver to?**

- Options: each saved address, at most four, as `<city>, <street>, <building>`. With a tool that needs at least two options and only one saved address, add the option `another address`.
- Typing is accepted: another address as city, street, building. Closing line: `Reply with a letter, or type another address: city, street, building.`
- With no saved addresses there are no options: the question in bold, then `Type the city, street and building.`
- For a typed address call `silpo_find_address`:

  | Result | Do this |
  | --- | --- |
  | one address with a `houseNumber` | Use it. Its label is `<city>, <street>, <houseNumber>` from the result. |
  | several addresses with a `houseNumber` | Ask the same question again with those as the options. |
  | only addresses whose `houseNumber` is null | Follow up once with `I could not confirm that building number.` and repeat the question. |
  | no addresses | Follow up once with `I could not find that address.` and repeat the question. |

Then call `silpo_get_available_delivery_types` with the address's coordinates and keep the `branchId` of `DeliveryHome` and of `WideAssortDelivery`. Ignore every other type. If it returned neither, follow up with `Silpo does not deliver to that address.` and repeat the question. Do not show coordinates or branch ids.

Call `silpo_get_time_slots` once for each of the two branches that exist.

### D2: usual day

**On which day of the week do you usually want your groceries?**

- Options: Saturday / Sunday / Friday / Monday.
- Typing is accepted: another day of the week. Closing line: `Reply with a letter, or type another day of the week.` Anything that is not a day of the week gets one follow-up, `Please name one day of the week.`

### D3: usual time of day

Take all the slots fetched for the address, from both branches. Count every slot, whether or not it is available now and whatever its day. Convert each slot's `start` to Kyiv time and put it in a part of the day:

| Part of the day | Slot starts |
| --- | --- |
| morning | before 12:00 |
| midday | from 12:00, before 15:00 |
| afternoon | from 15:00, before 18:00 |
| evening | from 18:00 |

**At what time of day?**

- Options: only the parts of the day that have at least one slot, in the order above, written as `morning (before 12:00)`, `midday (12:00 to 15:00)`, `afternoon (15:00 to 18:00)`, `evening (after 18:00)`.
- Typing is not accepted. Closing line: `Reply with a letter.`

### Review and save

Send one plain message with two parts: first the settings in the Show format, as a preview, then the question in bold, **Save these delivery settings?**, followed by the line `Reply yes or no.`

Do not use a question tool for this question, even when one is available: its dialog can cover the preview, and the user must see the preview while answering. The preview appears once, right above the question. Never ask to save without it.

On yes, write `data/stores/silpo.md` in the shape below and say in one line that it is saved.

On no, ask **Which answer do you want to change?** with the options address / usual day / time of day (closing line `Reply with a letter.`). Ask that question again. After a new address, check the chosen time of day against the new address's slots as in D3: if there are none in that part of the day, say `Silpo has no <part of the day> slots for that address.` and, in the next message, ask D3. Then show the review again.

```
# Silpo

- updated: 2026-11-12
- address_label: Київ, вулиця Хрещатик, 1
- address_id: 7b1e0c52-0000-4000-8000-000000000001
- home_branch_id: 1edee426-0000-4000-8000-000000000002
- wide_branch_id: 1f1739ad-0000-4000-8000-000000000003
- preferred_day: Saturday
- preferred_time: evening

## Change log

- 2026-11-12: created
```

- `address_id` is the `id` of a saved Silpo address, or `none` for a typed address.
- `home_branch_id` is the branch that came with `DeliveryHome`, `wide_branch_id` the one that came with `WideAssortDelivery`; `none` for one Silpo does not offer at the address.
- Coordinates, flat, entrance, floor, phone, courier comment, costs and time slots are not written to the file.

## Show format

Print the settings inside one fenced code block, so they appear in a frame, in these words. No Markdown marks inside the frame.

```
Silpo delivery
  Address: Київ, вулиця Хрещатик, 1
  Usual day: Saturday
  Usual time: evening (after 18:00)
  Delivery cost: 99 UAH, 69 UAH for orders from 1399 UAH, 1 UAH for orders from 1999 UAH
  Minimum order: 799 UAH, or 899 UAH when the order ships from the bigger warehouse
```

- `Delivery cost` comes from the first slot of the regular store's branch (the bigger warehouse's when there is no regular store): `deliveryCost` first, then each step of `deliveryCostMap` as `N UAH for orders from M UAH`.
- `Minimum order` is the `minOrderCost` of that same slot. Add `, or N UAH when the order ships from the bigger warehouse` only when both branches exist and their minimums differ.

## Change delivery

1. Map what the user said to the fields. Ask nothing that the change does not need.
2. A new day or time of day: set it. For the time of day, check as in D3 that Silpo has slots in that part of the day; if not, say `Silpo has no <part of the day> slots for that address.` and, in the next message, ask D3.
3. A new address: find it as in D1 (ask D1 if the user did not give it), store its label, id and the two branch ids, and check the saved time of day as in step 2.
4. A request for pickup, Nova Poshta, or a choice between the regular store and the bigger warehouse changes nothing. Answer: `Delivery is always to your door, and where the order ships from is chosen for you at shopping time.`
5. Show each change on its own line, as plain lines outside any frame, in the Show words: `Usual day: Saturday → Sunday`. After a new address, also show the `Delivery cost` and `Minimum order` lines. Fields without Show words, such as the branch ids and `address_id`, are logged but not shown.
6. Set `updated` to today, append one change log line per changed field, `- YYYY-MM-DD: preferred_day: Saturday → Sunday`, and end with `Saved.`

## Show delivery

Read `data/stores/silpo.md`, call `silpo_get_time_slots` for its branches to get today's cost and minimum order, and print the Show format. Ask nothing.
