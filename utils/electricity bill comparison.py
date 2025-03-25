import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Set the electricity cost per kWh (CAD)
cost_per_kWh = 0.147  # Example rate for Ontario, Canada

# Read the CSV file
df = pd.read_csv("predicted_7days.csv")
df["time"] = pd.to_datetime(df["time"])

# Calculate the original bill (without solar offset)
df["original_cost"] = df["consumption_pred"] * cost_per_kWh

# Calculate the new bill (consumption minus generation, if negative then zero)
df["new_cost"] = ((df["consumption_pred"] - df["generation_pred"]).clip(lower=0)) * cost_per_kWh

# ---- Compute Cumulative Costs ----
df["original_cumulative_cost"] = df["original_cost"].cumsum()
df["new_cumulative_cost"] = df["new_cost"].cumsum()

# Create the plot
fig, ax = plt.subplots(figsize=(12, 6))

# Plot cumulative costs: original vs new
ax.plot(
    df["time"], 
    df["original_cumulative_cost"], 
    label="Cumulative Original Bill (CAD)", 
    color="darkgreen", 
    marker="o"
)
ax.plot(
    df["time"], 
    df["new_cumulative_cost"], 
    label="Cumulative New Bill (CAD)", 
    color="orange", 
    marker="o"
)

# Set title and labels in English
ax.set_title("7-Day Cumulative Electricity Bill (CAD)")
ax.set_xlabel("Time")
ax.set_ylabel("Cumulative Bill (CAD)")
ax.legend()

# Format the x-axis to show ticks every 6 hours
ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()
