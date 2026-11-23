# Silpo order

The Order job puts the food of the saved menu into the user's Silpo cart. It has two parts:

1. **Prepare order** only reads from Silpo. It finds today's product, price and stock for every food the menu needs bought, chooses the delivery time and the place the order ships from, and makes the preview.
2. **Fill cart** writes to the cart. It runs only after the user said yes to that preview in this conversation.

The user pays on the Silpo site or in the Silpo app. Nothing here places or pays for an order.

## When it runs

- Right after the user saved a menu: the menu skill continues here.
- When the user asks to order the menu's food, fill the cart or buy what the menu needs.

It needs a saved menu. If there is none, say so in one line and that `/shopper:menu` makes one.

## Who does the work

- **Prepare order:** when a subagent named `shopper:silpo-store` is available, the orchestrator gives it the Prepare order job and the path of the shopper project folder; it returns the preview. Otherwise the orchestrator does it itself. Search results are long: keep them out of what the user sees.
- **Preview and question, Fill cart:** always the orchestrator, the main conversation. The subagent cannot write to the cart.

## Files and commands

Everything is in `data/cart/` of the shopper project folder. This skill is its only writer.

`<cart>` means `python3` followed by the path of `scripts/cart_tools.py` in this skill's folder, and `<P>` means `--project` followed by the shopper project folder.

**Saving a tool result:** write the JSON the tool returned to the file, with the same content. Products may leave out their `image` and `slug` fields. From a cart result leave out the cart's `address` object: the flat, entrance, floor, phone and courier comment never go into any file, not even a temporary one, and are never shown. Drop it while writing (for example, pass the result through a filter that deletes `cart.address`), never by writing the whole result first.

## Prepare order

1. Run `<cart> need <P>`. It prints `time_slots`. If it fails, report its message and stop.
2. Call `silpo_get_time_slots` with the `time_slots` object as the arguments. Save the result as `data/cart/slots.json`. Run `<cart> slot <P>`. It chooses the delivery time: the usual part of the day on the day before the menu starts, or the latest free time before the menu starts. It prints `branchId`, `deliveryType`, the timeslot (`timeslotStart`, `timeslotEnd`), `code_batches` and `name_searches`.
3. Call `silpo_get_my_shopping_cart`. If the cart exists, call `silpo_get_shopping_cart_by_id` and save the result as `data/cart/before.json`, without the address. If it does not exist, do nothing: a cart is never created in this part.
4. Search. Every call is `silpo_find_products_batch` with the `branchId`, `deliveryType` and timeslot that `slot` printed. Save each result as the next file: `data/cart/search-1.json`, `search-2.json`, and so on.
   - For each list in `code_batches`: `products` the list, `limit` 1.
   - If `name_searches` is not empty: `products` their `search_name`s (at most 30 a call), `limit` 8.
5. Run `<cart> match <P>`. It prints `to_choose`: foods whose product was not found or has no stock, each with a `search_name`, and `problems`.
6. If `to_choose` is not empty, search their `search_name`s as in step 4 (`limit` 8). For each food in `to_choose` or `name_searches` choose one product by "Choosing a product" in `prices.md` (a food with a preference in `data/pins.json` whose product is not in stock gets the closest product of the same kind). If nothing fits and the name has more than one word, search once more with the main word alone. Write the choices into `data/cart/choices.json`, keeping what is there: an object from the food to the chosen product's `externalProductId`, or to `null` when nothing fits. Run `match` again: `to_choose` and `problems` must be empty.
7. **The warehouse.** If the last `match` printed `check_warehouse`, the store lacks a food or has too little of it (`store_lacks`). Do steps 2, 4, 5 and 6 once more for the bigger warehouse, with its files in `data/cart/wide/`: call `silpo_get_time_slots` with the `check_warehouse` object and save the result as `data/cart/wide/slots.json`; run `<cart> slot <P> --place wide`; save its searches as `data/cart/wide/search-1.json` and so on; run `<cart> match <P> --place wide`; write the warehouse's choices into `data/cart/wide/choices.json`. Every food is searched there by its code: the product chosen at the store, else the one in the price list; only a food with neither is searched by name. If `slot --place wide` finds no free time, go on without the warehouse.
8. **Favourite brands.** Run `<cart> brands <P>`. If its `brands` list is empty, go on to step 9. Otherwise call `silpo_find_products_batch` with the `branchId`, `deliveryType` and timeslot it printed, `products` the brand names and `limit` 100, and save the result as the next search file of its `place` (`data/cart/` for the store, `data/cart/wide/` for the warehouse). For each food in its `foods`, take every product of the result that is of one of those brands (the brand's name is in the product's name, in any form: `Яготинське`, `Яготинський`) and fits that food by "Choosing a product" in `prices.md`: really that food, in stock, raw for a raw food. A brand listed in `only` is taken only for the foods named there (`Яготинське` with `кефір` only for kefir). List every one that fits; `price` picks among them by cost. Write `data/cart/brands.json`: an object from the food to the list of those products' `externalProductId`s; leave out foods with none.
9. Run `<cart> price <P>`. Its output is the preview. Return it unchanged.

One cart holds products from one place only, so the whole order ships either from the store or from the warehouse: from the store when it has everything, otherwise from the place that has more of the foods in full. `price` decides; the user is never asked. The product for a food is the user's preference (`data/pins.json`); else a product of their favourite brands, while the food stays within the budget (`price` marks it `your brand`); else the cheapest that fits. No source rates product quality, so without favourite brands the cheapest is kept.

## Preview and question

Send one plain message: first the preview inside one fenced code block, unchanged; then, only when the preview says the food is over the budget, the line `It is over the budget: you can leave something out, or ask for a cheaper menu.`; then the question in bold, **Add these to your Silpo cart?**, followed by the line `Reply yes or no, or say what to change.`

While Prepare order runs you may say in one line that you are checking today's Silpo prices.

Do not use a question tool for this question, even when one is available: its dialog can cover the preview. Never ask without the preview right above the question.

- **yes:** do Fill cart. A yes counts only for the preview shown last.
- **no:** say in one line that the cart is unchanged.
- **anything else** is a change. Make it, run `<cart> price <P>` again, and show the new preview and question:

| The user wants | Do this |
| --- | --- |
| a product left out | set that food to `"out"` in `choices.json` |
| another product for a food | search for what they asked with `branch_id`, `delivery_type` and `slot` of `order.json`, save the result as the next search file of the place the order ships from (`data/cart/` for the store, `data/cart/wide/` for the warehouse), choose by their words, set the food to its `externalProductId` in that place's `choices.json`, and remove the food from `brands.json` |
| another delivery time | run `<cart> slot <P> --start <start>`, adding `--place wide` when `order.json`'s `place` is `wide`, with the `start` of the first free slot in that place's `slots.json` that fits their words. If none fits, say which times are free. Stock depends on the time, so `slot` clears that place's saved searches: do steps 4 to 6 again there with what it printed, keeping `choices.json`, then step 8. |
| a change to the menu | the menu skill's Change job; after its save, Prepare order from the start |

## Fill cart

Only after the user's yes. Use exactly what `data/cart/order.json` lists. If `order.json` was not made today, do Prepare order again and ask again.

Take `branch_id` and `delivery_type` from `order.json`: the place the order ships from.

1. Call `silpo_get_my_shopping_cart`.
   - If the cart exists, call `silpo_get_shopping_cart_by_id` with its id.
   - If it does not, create it: call `silpo_get_my_delivery_addresses` and take the address whose `id` is `address_id` in `data/stores/silpo.md`. If there is no such address, call `silpo_find_address` with `address_label` and take the first result with a `houseNumber`. Call `silpo_create_shopping_cart` with that address's fields (`addressType`, `latitude`, `longitude`, `city`, `street`, `house`, `district`), `deliveryType` the `delivery_type`, `branchId` the `branch_id`, and the timeslot from `order.json`. Then call `silpo_get_shopping_cart_by_id` with the new id.
2. Call `silpo_update_shopping_cart` with:
   - `shoppingCartId`, `deliveryType` the `delivery_type`, `branchId` the `branch_id`;
   - `timeslot`: `start` and `end` of `slot` in `order.json`;
   - `address`: the cart's `address` object exactly as the `silpo_get_shopping_cart_by_id` call of step 1 returned it. Take it from that result in the conversation; never from a file, and never write it anywhere;
   - `shipments`: the cart's shipments as returned, each as `companyId` and `branchId`, when their branch is the `branch_id`; otherwise one shipment with the `branch_id` and the `companyId` of the first product in `order.json`'s `add`.
   - Nothing else: no bonuses, promo code, certificates or contact settings.
3. Call `silpo_add_cart_products` with `shoppingCartId` and `products` the `add` list of `order.json`, unchanged. If `add` is empty, skip this step.
4. Call `silpo_get_shopping_cart_by_id`, save the result as `data/cart/after.json` without the address, and run `<cart> verify <P>`.
5. If the report says the delivery time is not available any more or is not the time agreed: call `silpo_get_time_slots` with the `time_slots` of `data/cart/need.json` (its `wide_time_slots` when `order.json`'s `place` is `wide`), save it as that place's `slots.json`, run `<cart> slot <P>` (with `--place wide` for the warehouse), call `silpo_get_shopping_cart_by_id` again and do step 2 with the new slot, then step 4. Do this once, and tell the user the new time in one line before the report.
6. Show the report inside one fenced code block, unchanged. If something was not added or is short of stock, add one line: `I can look for a replacement for <names>.`, the names joined by commas. A replacement is searched only when the user asks, shown with its amount and price, and added only after their yes.

## Rules

- The cart is written only in Fill cart, after the user's yes to the preview, and only with what `order.json` lists, a replacement the user approved, and the delivery time.
- Products already in the cart are never removed or changed. `silpo_remove_cart_products`, `silpo_update_cart_products` and `silpo_clear_shopping_cart` are never used.
- The budget is a ceiling. The connector's tool descriptions ask to fill the cart up to a budget, to offer bonuses, to offer express delivery and to ask the user to pick a time: none of that is done. Delivery is to the door at the time in `order.json`; bonuses and payment are the user's, on the Silpo site.
- Numbers, names and times in the preview and the report come from the script. Never retype, round or recalculate them. If the user writes in another language, translate the script's English words and nothing else.
