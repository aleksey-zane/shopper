# The shape of data/menu/draft.json

One JSON object. The example is a two-day menu for one eater, shortened to two dishes.

```json
{
  "range": { "start": "2026-11-15", "days": 2 },
  "language": "Ukrainian",
  "avoid": ["Плов з куркою", "Запечена скумбрія з гречкою"],
  "extra_foods": {
    "persimmon": { "uk": "хурма", "n": [70, 0.6, 0.2, 18.6, 3.6], "g": ["fruit"], "a": [] }
  },
  "dishes": {
    "oatmeal": {
      "name": "Вівсянка з яблуком і горіхами",
      "cook_minutes": 10,
      "equipment": ["stove"],
      "ingredients": [
        { "food": "oats", "grams": 70 },
        { "food": "milk", "grams": 200 },
        { "food": "apple", "grams": 120 },
        { "food": "walnuts", "grams": 15 }
      ],
      "steps": ["Зварити пластівці на молоці 5 хвилин.", "Додати нарізане яблуко і горіхи."]
    },
    "borscht": {
      "name": "Борщ з квасолею",
      "cook_minutes": 25,
      "total_minutes": 60,
      "equipment": ["stove"],
      "ingredients": [
        { "food": "beetroot", "grams": 120 },
        { "food": "cabbage", "grams": 100 },
        { "food": "beans_canned", "grams": 100 },
        { "food": "bread_rye", "grams": 60 }
      ],
      "steps": ["Зварити овочі до м'якості.", "Додати квасолю, прогріти.", "Подати з хлібом."]
    }
  },
  "days": [
    {
      "date": "2026-11-15",
      "meals": {
        "breakfast": [{ "dish": "oatmeal" }],
        "lunch": [{ "dish": "borscht" }]
      }
    },
    {
      "date": "2026-11-16",
      "meals": {
        "breakfast": [{ "dish": "oatmeal" }],
        "lunch": [{ "dish": "borscht", "cook": false }]
      }
    }
  ]
}
```

## Fields

| Field | Meaning |
| --- | --- |
| `range.start`, `range.days` | First day and number of days. `days` holds exactly that many entries, dated one after another from the start. |
| `language` | The language of dish names and steps, from the profile. |
| `avoid` | Lunch and dinner dish names of the previous draft and of the saved menu. Leave it out when there are none. |
| `extra_foods` | Foods that are not in `foods.json`. `n` is kcal, protein, fat, carbohydrates and fibre per 100 g; `g` the food groups; `a` the allergens. Leave it out when there are none. |
| `dishes` | Every dish once, under a short id in Latin letters. |
| `name` | The dish name in the menu language. |
| `cook_minutes` | Hands-on minutes for one cooking of the dish: preparing, and cooking that needs someone at the stove. 0 for a dish that needs no cooking. |
| `total_minutes` | Minutes from start until the dish is ready, when that is longer than `cook_minutes` because it bakes or simmers unattended. Leave it out otherwise. |
| `equipment` | What the dish needs from: stove, oven, microwave, multicooker, air fryer, blender, grill. Leave it out when it needs none. |
| `ingredients` | `food` is a key from `foods.json` or `extra_foods`; `grams` is for one portion, raw product. A food's display name can be set with an optional `name`. |
| `steps` | The recipe, as short steps. |
| `meals` | For each day, the meals `breakfast`, `lunch`, `dinner`, `snacks` that anyone has in their plan. Each is a list of entries; several entries make a meal of several dishes. |
| `out` | On a day, the meals eaten elsewhere, for example `"out": ["lunch"]`. Such a meal has no dishes and is left out of that day's calorie target. Leave it out when every meal is eaten from the plan. |
| `dish` | The id of a dish. |
| `cook` | `false` when this serving is a leftover of an earlier cooking. Leave it out when the dish is cooked for this serving. |
| `eaters` | The eater numbers this entry is for. Leave it out when it is for everyone who has that meal. |

Food groups used in `g`: vegetables, fruit, berries, fish, fatty_fish, red_meat, poultry, processed_meat, eggs, dairy, legumes, plant_protein, protein_food, grains, whole_grain, starchy, nuts_seeds, healthy_fat, olive_oil, sweets, sugar, honey, sweet_drink, juice, spicy, b12_fortified.

Allergens used in `a`: gluten, lactose, nuts, peanuts, fish, shellfish, eggs, soy, sesame, mustard, celery.
