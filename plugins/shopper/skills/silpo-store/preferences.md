# Product preferences

The user can name the product they want for a food ("I prefer Golden apples", "always buy Galychyna milk"). The preference is kept in `data/pins.json` and wins over the cheapest product: the price list, the menu cost and every order use it. This skill is the only writer of `data/pins.json`.

## Steps

1. **The food.** Find the food in `foods.json` of the `menu` skill (its `uk` name and `also` words help: apples are `apple`, milk is `milk`). If no food fits, say in one line that the menu has no such food, and stop.
2. **The product.** Read `home_branch_id` from `data/stores/silpo.md`, call `silpo_get_time_slots` with that branch and `deliveryTypes: ["DeliveryHome"]`, and take the first slot with `available: true` that has not started yet. Call `silpo_find_products_batch` with that branch, `deliveryType: "DeliveryHome"`, the slot, `products` the user's words in Ukrainian (for "Golden apples", `яблуко голден`) and `limit` 8.
   - Keep the products whose name contains what the user named and that are in stock.
   - Of those, take the one whose name adds the fewest other words (`Яблуко Голден` before `Яблуко Голден, Закарпаття`).
   - If two are still equally close, ask which one, with them as the options (at most four) and their price as the option text.
   - If none fits, say in one line that Silpo has no such product now, and stop.
3. **Preview and save question.** Send one plain message: first, inside one fenced code block,

   ```
   Your product for <food in plain words>
     <product name>: <price> UAH per kg
   ```

   (for a packed product: `<price> UAH for <pack weight>`). Write the frame's words, the question and the closing line in the language the user writes in; product names stay as Silpo gives them. When the food already has a preference, add a line `  Replaces: <old product name>`; then the question in bold, **Save this preference?**, followed by `Reply yes or no.` Do not use a question tool for this question.
4. **yes:** write `data/pins.json`, replacing an earlier preference for the same food:

   ```json
   { "pins": [ { "food": "apple", "store": "silpo", "code": 58480, "title": "Яблуко Голден", "since": "2026-11-14" } ] }
   ```

   Then write the food's entry in `data/prices.json` from the same search result, as `prices.md` describes, so the menu and orders use it at once. Say in one line: `Saved: <product name> for <food in plain words>. It is used from the next order.`
   **no:** say in one line that nothing changed.
5. **Removing a preference** ("buy any apples again"): if the food has none, say so in one line and stop. Otherwise show `Your product for <food>: no preference (was <product name>)` in a frame with the same save question. On yes, remove the entry from `data/pins.json` and remove the food's entry from `data/prices.json`, so the next price list chooses the cheapest product again. Say in one line: `Saved: no preference for <food in plain words>. The cheapest is chosen again from the next menu.`

A cart that is already filled keeps what it has. The preference changes it only when the user asks, through the Order job.
