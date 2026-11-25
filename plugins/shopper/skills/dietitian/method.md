# How the targets are calculated

`scripts/targets.py` does all of this. The description is here so the method can be read, checked and, when no code can be run, followed by hand. `scripts/test_targets.py` holds worked examples.

Each number names its source in square brackets; the sources are listed at the end. A number marked **[no source]** is the plan's own choice: no authoritative source for it was found.

Age is the current year minus the year of birth. Every rounding below goes to the nearest step, with halves rounded up: 72.5 g to the nearest 5 g is 75.

## Adults (18 and older)

1. **Height.** The height in the profile. If none: 176 cm for men, 163 cm for women, 170 cm when sex is not given **[no source]**.
2. **Weight.** The weight in the profile. If none: a healthy weight for the height, a body mass index of 21.0, the median of the normal range 18.5 to 24.9 [FAO/WHO/UNU 2004, 5.4.2]. Weight = 21.0 × (height in metres)².
3. **Resting energy** (Mifflin-St Jeor) [Mifflin 1990; Frankenfield 2005 found it the most reliable equation for healthy adults]: 10 × weight + 6.25 × height − 5 × age, then +5 for men, −161 for women, −78 (the midpoint) when sex is not given.
4. **Activity:** multiply by the physical activity level [FAO/WHO/UNU 2004, 5.3 and Tables 5.1, 5.3]:
   - sedentary 1.40, the lowest level of the sedentary or light band (1.40 to 1.69);
   - light 1.55, the level FAO gives for a sedentary lifestyle;
   - moderate 1.75, the level FAO gives for a sedentary lifestyle plus one hour a day of moderate to vigorous exercise;
   - active 2.25, FAO's example of a vigorous lifestyle (band 2.00 to 2.40).

   FAO applies these levels to its own resting-energy equations (Schofield); here they are applied to Mifflin-St Jeor, the equation Frankenfield 2005 found most reliable.
5. **Weight goal:** lose slowly −300 kcal, lose at a moderate pace −500, gain slowly +250, gain at a moderate pace +500, maintain 0 **[no source]**.
6. **The user's own number:** if the profile holds `calories_override`, it replaces the result of steps 3 to 5.
7. **Floor:** never below 1500 kcal for men, 1200 for women, 1350 when sex is not given **[no source]**: FAO/WHO/UNU 2004 defines no minimum.
8. Round to the nearest 50 kcal.

## Children (1 to 17)

Energy for a moderately active child, in kcal a day, by year of age [FAO/WHO/UNU 2004, Tables 4.5 and 4.6]. Age 1 is the row "1 to 2 years", and so on.

| Age | Boys | Girls | Age | Boys | Girls |
| --- | --- | --- | --- | --- | --- |
| 1 | 950 | 850 | 10 | 2150 | 2000 |
| 2 | 1125 | 1050 | 11 | 2350 | 2150 |
| 3 | 1250 | 1150 | 12 | 2550 | 2275 |
| 4 | 1350 | 1250 | 13 | 2775 | 2375 |
| 5 | 1475 | 1325 | 14 | 3000 | 2450 |
| 6 | 1575 | 1425 | 15 | 3175 | 2500 |
| 7 | 1700 | 1550 | 16 | 3325 | 2500 |
| 8 | 1825 | 1700 | 17 | 3400 | 2500 |
| 9 | 1975 | 1850 | | | |

When sex is not given, the average of the two. From 6 years old, sedentary and light activity are 15% lower (× 0.85) and active is 15% higher (× 1.15) [FAO/WHO/UNU 2004, 4.4.3]; under 6 the table value is used as it is. The result is rounded to the nearest 50 kcal, as for adults. A weight goal is never applied under 18. Children under 1 are not planned.

## Protein, fat, carbohydrates, fibre

Shares of daily calories come from `patterns.json`. They are worked out from the rounded daily calories. Grams of protein and carbohydrates are calories ÷ 4, grams of fat calories ÷ 9, each rounded to the nearest 5 g only at the end.

| Way of eating | Protein | Fat | Carbohydrates |
| --- | --- | --- | --- |
| balanced | 20% | 30% | 50% |
| high-protein | 2.0 g per kg of body weight, at most 30% | 25% | the rest |
| Mediterranean | 18% | 35% | 47% |
| vegetarian | 17% | 30% | 53% |
| vegan | 17% | 30% | 53% |
| pescatarian | 20% | 30% | 50% |
| low-carb | 25% | 45% | 30% |
| keto | 20% | 70% | 10% |

- The first six stay inside the reference ranges for adults: protein 10 to 35% [IOM 2005], fat 20 to 35% [EFSA 2017; IOM 2005], carbohydrates 45 to 60% [EFSA 2017]. Balanced, high-protein, vegetarian, vegan and pescatarian also keep fat at 30% or less [WHO healthy diet]; Mediterranean uses the top of the EFSA fat range, for its olive oil.
- High-protein: 2.0 g of protein per kg of body weight, the top of the range for people who exercise, 1.4 to 2.0 g [ISSN 2017], but at most 30% of calories, so that carbohydrates, the rest after protein and fat, stay at 45% or more [EFSA 2017].
- Low-carb and keto are outside the reference ranges on purpose, as ways of eating the user chose **[no source for their shares]**. Under 18, high-protein, low-carb and keto use the balanced shares.
- **Fibre:** 25 g a day for adults [EFSA 2017; WHO: at least 25 g]. Children 2 g per MJ [EFSA 2017]: 10 g at 1 to 3 years, 14 at 4 to 6, 16 at 7 to 10, 19 at 11 to 14, 21 at 15 to 17.

The interview offers the first four ways of eating; the others are recognised when typed, as are common other spellings (`_aliases` in `patterns.json`).

A way of eating that is not on the list uses the shares and weekly rules of the closest listed one, chosen once by the dietitian and remembered in `data/diet.md`, plus extra rules written by the dietitian from the user's words.

## Weekly rules

The rules of each way of eating are in `patterns.json`; the menu script checks them.

- At least 400 g of vegetables and fruit a day, potatoes not counted, from 10 years old [WHO healthy diet]. When a meal is eaten outside the plan, the amount is lowered in proportion to the calories planned that day.
- Red meat at most 3 times a week, about 350 to 500 g cooked [WCRF]; each way of eating stays at or below that.
- Processed meat at most once a week: WCRF advises "very little, if any" [WCRF].
- Fish at least 2 times a week: EFSA gives 1 to 2 fatty fish meals a week for adults [EFSA 2017, 3.3].
- How often to eat beans and lentils, the whole-grain share, how often sweets, fruit every day, nuts every day: **[no source]** for the numbers. WHO advises carbohydrates mainly from whole grains, vegetables, fruit and pulses, and free sugars below 10% of energy, without a count per week.

## Portion sizes

The menu script sizes each person's portions to the calories of the meal, but never above one plate:

- **A food:** at most twice the reference amount customarily consumed at one eating occasion, added over the dishes of the meal. The amounts are in `portions.json` of the `menu` skill [21 CFR 101.12; meat and poultry 9 CFR 317.312, 381.412].
- **A soup:** at most 2 × 245 g = 490 g, its water included [21 CFR 101.12].
- **Why twice:** less than 200 percent of the reference amount counts as one serving [21 CFR 101.9(b)(6)].
- Foods without a reference amount in the table have no limit of their own: fats, sweeteners, seasonings, whole fish and bone-in pieces.

When a meal within these limits has too few calories, the chef adds another dish to it. The user is never asked about portions.

## Knowing when the diet is out of date

`data/diet.md` holds a fingerprint of the profile fields the targets depend on, together with the calendar year. `targets.py --check` compares it with the profile: any change in those fields, or a new year, makes the diet stale. Changes elsewhere in the profile, such as cooking time or budget, do not.

## Split across the day

Breakfast 25%, lunch 35%, dinner 30%, snacks 10% **[no source]**. When the plan has no snacks for a person, the snack share is spread over the three main meals in proportion. A main meal that is not in the plan keeps its share and is counted as eaten outside the plan. Each meal is rounded to the nearest 10 kcal.

## Sources

- **FAO/WHO/UNU 2004.** Human energy requirements. Report of a Joint FAO/WHO/UNU Expert Consultation, Rome, 17–24 October 2001. FAO Food and Nutrition Technical Report Series 1. Children: http://www.fao.org/4/y5686e/y5686e06.htm (chapter 4); adults: http://www.fao.org/4/y5686e/y5686e07.htm and y5686e08.htm (chapter 5).
- **Mifflin 1990.** Mifflin MD, St Jeor ST et al. A new predictive equation for resting energy expenditure in healthy individuals. Am J Clin Nutr 1990;51:241–7. PubMed 2305711.
- **Frankenfield 2005.** Frankenfield D, Roth-Yousey L, Compher C. Comparison of predictive equations for resting metabolic rate in healthy nonobese and obese adults: a systematic review. J Am Diet Assoc 2005;105:775–89 (American Dietetic Association, now the Academy of Nutrition and Dietetics). PubMed 15883556.
- **EFSA 2017.** Dietary Reference Values for nutrients. Summary report. EFSA Supporting Publications 2017:e15121. https://www.efsa.europa.eu/sites/default/files/2017_09_DRVs_summary_report.pdf
- **IOM 2005.** Institute of Medicine. Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein, and Amino Acids. National Academies Press, 2005. doi:10.17226/10490. Acceptable Macronutrient Distribution Ranges.
- **ISSN 2017.** Jäger R et al. International Society of Sports Nutrition Position Stand: protein and exercise. J Int Soc Sports Nutr 2017;14:20. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5477153/
- **WHO healthy diet.** World Health Organization, Healthy diet fact sheet. https://www.who.int/news-room/fact-sheets/detail/healthy-diet
- **21 CFR 101.12, 101.9.** US Food and Drug Administration, Reference amounts customarily consumed per eating occasion; Nutrition labeling of food. https://www.govinfo.gov/content/pkg/CFR-2023-title21-vol2/xml/CFR-2023-title21-vol2-sec101-12.xml and sec101-9.
- **9 CFR 317.312, 381.412.** US Department of Agriculture, reference amounts for meat and for poultry products. https://www.govinfo.gov/content/pkg/CFR-2023-title9-vol2/xml/CFR-2023-title9-vol2-sec381-412.xml and sec317-312.
- **WCRF.** World Cancer Research Fund / American Institute for Cancer Research, Cancer Prevention Recommendations: Limit red and processed meat. https://www.wcrf.org/diet-activity-and-cancer/cancer-prevention-recommendations/limit-red-and-processed-meat/
