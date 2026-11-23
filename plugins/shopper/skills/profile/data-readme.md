# Data

Everything the skills remember lives here, outside the plugin, so reinstalling
the plugin never touches it. Field lists below are a first draft; each roadmap
step refines the file it owns.

| File | Owner step | Holds |
| --- | --- | --- |
| `profile.md` | 2 Profile | Eaters, goals, way of eating, hard limits, dislikes, cooking, budget, language. Store-independent. Written only by the `profile` skill; its shape is `plugins/shopper/skills/profile/profile-template.md`. Created the first time the profile interview runs. |
| `diet.md` | 3 Diet | Per eater: daily calories, protein, fat, carbohydrates, fibre, calories per meal, weekly food rules. Written only by the dietitian, by running `plugins/shopper/skills/dietitian/scripts/targets.py`; recalculated whenever the profile changes. Nobody else edits it. The only lines the dietitian writes by hand are the extra rules for a way of eating that is not on the list. |
| `stores/silpo.md` | 4 Delivery setup | Per-store delivery settings for Silpo: address label, the regular and the wide-assortment branch for that address, usual day and time of day. Written only by the `silpo-store` skill. Each further store gets its own file in `stores/`. |
| `pantry.json` | 5 Menu and 9 Pantry | Food already at home: per food, grams as bought and whether raw or cooked. Written only by the `pantry` skill. |
| `prices.json` | 5 Menu | The store's price list for the foods the chef uses: per food, the chosen product's code, title, price and pack size, or `missing`; `place: wide` for a product only the bigger warehouse has. Written only by the store skill; read by the chef and the menu script. |
| `pins.json` | 7 Product matching | The user's own product choices for a food, by store article code. Written only by the `silpo-store` skill; they override the cheapest product in the price list. |
| `history.json` | 5 and 9 | Dishes already eaten, added when a saved menu is replaced; later also ratings and notes. |
| `menu/draft.json` | 5 Menu | The draft menu the chef wrote: range, dishes with recipes, and which dish is eaten at each meal of each day. |
| `menu/draft-check.json` | 5 Menu | The dietitian's check of the draft: portion sizes, nutrition per day, what to fix or improve. Written by the menu script. |
| `menu/menu.json`, `menu/menu-check.json` | 5 Menu | The one saved menu and its check. Replaced when a new draft is saved. |
| `menu/menu.html` | 5 Menu | The saved menu as a web page: the days, each dish a link to its recipe. Written by the menu script's `page` command and published as a page after each save. |
| `cart/` | 8 Cart | The working files of the last Silpo order, written only by the `silpo-store` skill and cleared when a new order starts: `need.json` (what the saved menu needs bought), `slots.json`, `before.json`, `search-N.json`, `after.json` (Silpo's answers, saved as returned but never with the address), `choices.json` (the product chosen for a food), `brands.json` (products of the user's favourite brands that fit a food), `slot.json` and `order.json` (the delivery time and the priced order, by `scripts/cart_tools.py`). When the store lacks something, the bigger warehouse's `slots.json`, `slot.json`, `search-N.json` and `choices.json` go into `cart/wide/`, and `order.json` says which place the order ships from. |

## Shapes

`pantry.json`

```json
{ "updated": "2026-11-12", "items": [ { "food": "chicken_breast", "grams": 1320, "state": "raw" } ] }
```

`pins.json`

```json
{ "pins": [ { "food": "apple", "store": "silpo", "code": 58480, "title": "Яблуко Голден", "since": "2026-11-14" } ] }
```

`history.json`

```json
{ "meals": [ { "date": "2026-11-11", "meal": "dinner", "dish": "baked salmon with rice", "rating": 4, "note": "" } ] }
```

## Rules

- Quantities use metric units: `g`, `kg`, `ml`, `l`, `pcs`.
- Dates are `YYYY-MM-DD`.
- Money is in UAH.
- Never store Silpo logins, tokens or card details here. Of a delivery address, only city, street and building are stored: no flat, entrance, floor, phone, courier comment or coordinates. Cart results are saved without their `address` object.
