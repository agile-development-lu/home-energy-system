After 23:00 (until early morning), power consumption decreases to simulate that most people are asleep, leaving only essential appliances running (such as refrigerators and air conditioners in standby mode). In the morning, around 7–8 AM when people wake up, power consumption increases (for making breakfast, showering, turning on lights, using hair dryers, etc.). During work hours on weekdays (Monday to Friday from 9 AM to 5 PM), power consumption remains low (as no one is at home), and then rises again after 5 PM when people return home in the evening (for cooking, doing laundry, turning on lights, watching TV, etc.). On weekends (Saturday and Sunday), unlike weekdays, people are more likely to be at home all day, so daytime power consumption isn’t as low as on weekdays, though the evenings still see higher usage. Additionally, solar power generation during the day is increased (for example, the peak between 10 and 14 can be raised to 3.0–5.0 kWh), with slight boosts in other time periods as well.

**Add a new "day_of_week" column:**

This allows the model to know which day of the week each record belongs to (0 = Monday, 6 = Sunday), so that the subsequent LSTM can consider the influence of different days on power consumption habits.

**Add a new "solar_irradiance" column:**

This column represents the current period’s sunlight intensity (W/m²). The solar_generation_kWh is calculated by combining this with the photovoltaic area and efficiency, reflecting the impact of weather/sunlight on actual power generation. You can also use this column directly for predictions (for example, input future weather forecast irradiance to estimate generation).

**A more complete solar power generation calculation process:**

- Introduce a “seasonal_factor” to simulate the variations in sunlight intensity across the four seasons, along with some random fluctuations.
- The hourly irradiance is set with different baselines depending on the time segment (between 06:00 and 19:59), then multiplied by the seasonal factor and random variations.
- Finally, a simple formula is used to calculate the photovoltaic output for that hour.

**Retain and fine-tune the previous power consumption logic:**

Assign different power consumption ranges based on whether it’s a weekday or weekend, during the day versus nighttime, as well as early morning and late night periods. You can further adjust these ranges as needed.

**Daily weather determination:**

Assume that the “weather” remains relatively stable throughout the day (i.e., using a “daily” weather condition to simplify; if desired, you could change the weather every few hours for more detail). Each day, randomly select one weather type and assign a corresponding “weather_factor” to reduce or increase the solar irradiance:
- Sunny: factor ~1.0 (no reduction or a slight increase)
- Cloudy: factor ~0.6
- Rainy: factor ~0.3
- Stormy: factor ~0.1 (a significant drop in power generation)

You can customize the occurrence probabilities (weights) for each weather type to control the proportion of cloudy or rainy days in your dataset.

**Random assignment of weather:**

Use `random.choices(...)` to select the day’s weather based on the specified weights. Every time a new day (day_of_year) begins, re-select the weather and store it (in a dictionary or variable), ensuring that every hour within that day uses the same weather condition.

**Calculate power generation:**

Follow the original process:
- Calculate the baseline irradiance (with different possible ranges for the time period between 6 and 19).
- Multiply by the seasonal factor (seasonal fluctuation).
- Multiply by the weather reduction factor (weather_factor).
- Finally, add a random adjustment of ±10%.
- Apply the photovoltaic area and efficiency to obtain solar_generation_kWh.

At this point, the influence of weather will cause the power generation for all hours on the same day to increase or decrease proportionally.

**CSV columns:**

Add a “weather” column (string; e.g., "Sunny", "Cloudy", "Rainy", "Stormy"). The other columns remain as follows:
- time (timestamp)
- day_of_week (0–6)
- power_consumption_kWh (power consumption)
- solar_irradiance_Wm2 (solar irradiance)
- solar_generation_kWh (final power generation)

---