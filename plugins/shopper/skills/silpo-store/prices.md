# Silpo price list

`data/prices.json` holds, for each food the chef uses, the Silpo product chosen for it and its price. The chef reads it to compose within the budget, and the menu script uses it to add up what a menu costs. This skill is the only writer of that file. The job only searches Silpo; it never touches the cart.

## When it runs

The menu skill calls this job while making a menu: before the chef drafts, to refresh old prices and, the first time, to price the whole food table; and after the chef drafts, to price foods that still have none. The user can also ask to update the prices. Its report is for the orchestrator and is not shown to the user.

## Who does the work

When a subagent named `shopper:silpo-store` is available, the orchestrator gives it this job and the path of the shopper project folder, and it returns a short report. Otherwise the orchestrator does the job itself. Search results are long: keep them out of what the user sees.

## Steps

`<tools>` means `python3` followed by the path of `scripts/menu_tools.py` in the `menu` skill's folder, which sits next to this skill's folder.

1. Run `<tools> prices-needed --project <project> --limit 60`, adding `--all` when the menu skill asked for the whole food table. It prints two lists: `new`, foods without a price, each with a search name; and `stale`, prices older than a week, each with its product code (and `place: "wide"` for a product of the bigger warehouse). It also prints `new_remaining`, the foods that did not fit into this run. If both lists are empty, the job is done: report `Prices are up to date.`
2. Read `home_branch_id` and `wide_branch_id` from `data/stores/silpo.md`. If that file is missing, do Delivery setup first. Every food and code is searched at the regular store first; the bigger warehouse (`wide_branch_id`, delivery type `WideAssortDelivery`) is searched only for what the store does not have, and only when its branch is not `none`.
3. Call `silpo_get_time_slots` with that branch and `deliveryTypes: ["DeliveryHome"]`. Take the first slot with `available: true` that has not started yet; its `start` and `end` are the timeslot for the searches. If no slot is available, take the first slot and say so in the report.
4. Search with `silpo_find_products_batch`: `branchId`, `deliveryType: "DeliveryHome"`, `timeslotStart`, `timeslotEnd`, `products` (at most 30 a call) and `limit`. Stale codes and new names go in separate calls.
   - **Stale prices:** `products` are the product codes as text, `limit` 1. A code that comes back with `stock` above 0 keeps its product: write its entry again from the result, with the new price. A code that does not come back, or has no stock, is treated as a new food, except a code with `place: "wide"`: it is searched by its code at the warehouse, as in step 6, and only if it does not come back there either is it treated as a new food. A `place: "wide"` code that comes back in stock at the store is written without `place`.
   - **New foods:** `products` are the search names, `limit` 8. If nothing fits and the name has more than one word, search once more with the main word alone (for `сочевиця червона`, `сочевиця`).
5. For each new food choose one product, by the rules below.
6. **The warehouse.** For the foods that still fit nothing at the store: call `silpo_get_time_slots` with `wide_branch_id` and `deliveryTypes: ["WideAssortDelivery"]`, and take a slot as in step 3. Search their names there as in step 4, with that branch and `deliveryType: "WideAssortDelivery"`, and choose by the rules below. A product found there gets `"place": "wide"` in its entry: an order that needs it ships from the warehouse. Skip this step when `wide_branch_id` is `none`.
7. Write the entries into `data/prices.json`, in the shape below, set `updated` to today, and check that the file is valid JSON.
8. Report in a few lines: how many prices were refreshed, how many foods were newly priced and how many of them only at the warehouse, which foods Silpo does not have, and `new_remaining`, the number of foods still waiting for another run. The whole table is done when `new_remaining` is 0.

## Choosing a product

- A food with an entry in `data/pins.json` takes that product: search its `code` (as a stale price), and write its entry whatever the price. Only when it does not come back in stock, choose by the rules below and say so in the report.
- It really is that food: plain, not flavoured, not a ready meal, not a gift or premium edition.
- It is in stock: `stock` above 0.
- Among those that fit, the cheapest per kilogram. A promotional price counts as the price. The price list is the floor the menu is costed at; the user's favourite brands replace the cheapest later, at shopping time, while the budget has room (Order job).
- A raw food is matched by a raw product: a marinated, smoked, grilled or breaded product does not fit a plain meat or fish.
- If nothing fits at the store or at the warehouse, record the food as missing.

## The file

```json
{
  "store": "silpo",
  "updated": "2026-11-12",
  "foods": {
    "potato": { "code": 531296, "title": "Картопля біла", "price": 15.99, "weighted": true, "step_grams": 1000, "checked": "2026-11-12" },
    "beans_canned": { "code": 700123, "title": "Квасоля червона консервована", "price": 49.9, "pack_grams": 400, "checked": "2026-11-12" },
    "squid": { "missing": true, "checked": "2026-11-12" }
  }
}
```

| Field | Taken from the search result |
| --- | --- |
| `code` | `externalProductId` |
| `title` | the product's name: `name`, or `title` in results that call it so |
| `price` | `price`: for a product sold by weight, the price of a kilogram; otherwise the price of one pack |
| `weighted`, `step_grams` | only for a product with `weighted: true`: `step_grams` is the product's `step` (called `addToBasketStep` in some results) times 1000, as a whole number. Such a product gets no `pack_grams`, whatever its `displayRatio` says. |
| `pack_grams` | only for a packaged product: the weight of one pack in grams, read from `displayRatio` (`400г` is 400, `1кг` 1000, `900мл` 900, `1л` 1000). For eggs, `10 шт` is 550. |
| `place` | only for a product of the bigger warehouse: `"wide"`. A product of the regular store has no `place`. |
| `checked` | today |
| `missing` | `true` when Silpo has no fitting product; then the entry has only `missing` and `checked` |

A product sold by the piece with no weight in the result is a last resort: prefer one with a weight. If it is the only fit, write your estimate of its weight as `pack_grams` and add `"estimate": true`.

Write the numbers exactly as Silpo returned them. Do not calculate a price per kilogram: the menu script does that. Entries of foods that were not searched this time stay as they are.
