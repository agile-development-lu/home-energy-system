import csv
import random
from datetime import datetime, timedelta

# === 1) 定義「日間」與「夜間」的狀態空間 ===
day_states = ["Sunny", "Cloudy", "Rainy", "Stormy"]
night_states = ["Night", "Cloudy", "Rainy", "Stormy"]

# 依舊保持「Sunny/Night=50%, Cloudy=30%, Rainy=17%, Stormy=3%」做初始抽樣(不是絕對精準)
day_initial_dist = [0.50, 0.30, 0.17, 0.03]
night_initial_dist = [0.50, 0.30, 0.17, 0.03]

# === 2) 更新後的轉移矩陣 (提高自我轉移機率) ===
# day_transition_matrix: 4x4 對應 [Sunny, Cloudy, Rainy, Stormy]
day_transition_matrix = [
    [0.85, 0.10, 0.04, 0.01],  # from Sunny
    [0.10, 0.70, 0.15, 0.05],  # from Cloudy
    [0.05, 0.10, 0.80, 0.05],  # from Rainy
    [0.05, 0.10, 0.10, 0.75]   # from Stormy
]

# night_transition_matrix: 4x4 對應 [Night, Cloudy, Rainy, Stormy]
night_transition_matrix = [
    [0.85, 0.10, 0.04, 0.01],  # from Night
    [0.10, 0.70, 0.15, 0.05],  # from Cloudy
    [0.05, 0.10, 0.80, 0.05],  # from Rainy
    [0.05, 0.10, 0.10, 0.75]   # from Stormy
]

def markov_chain_next_state(current_state, states, transition_matrix):
    """
    從馬可夫鏈中計算「下一狀態」。
    current_state: 當前天氣 (需在 states 裡)
    states: 狀態列表 (day_states or night_states)
    transition_matrix: 對應的4x4轉移機率
    """
    idx = states.index(current_state)
    probs = transition_matrix[idx]
    next_s = random.choices(states, weights=probs, k=1)[0]
    return next_s

def generate_day_block(num_hours=12):
    """ 產生「日間」12小時的天氣序列 (馬可夫鏈)。 """
    if num_hours <= 0:
        return []
    # 第 1 小時: 用 initial_dist 抽
    first_state = random.choices(day_states, weights=day_initial_dist, k=1)[0]
    seq = [first_state]
    current = first_state
    for _ in range(num_hours - 1):
        next_s = markov_chain_next_state(current, day_states, day_transition_matrix)
        seq.append(next_s)
        current = next_s
    return seq

def generate_night_block(num_hours=12):
    """ 產生「夜間」12小時的天氣序列 (馬可夫鏈)。 """
    if num_hours <= 0:
        return []
    # 第 1 小時: 用 initial_dist 抽
    first_state = random.choices(night_states, weights=night_initial_dist, k=1)[0]
    seq = [first_state]
    current = first_state
    for _ in range(num_hours - 1):
        next_s = markov_chain_next_state(current, night_states, night_transition_matrix)
        seq.append(next_s)
        current = next_s
    return seq


def generate_7day_forecast_with_night_state(start_time=None):
    """
    產生未來 7 天(168小時)的天氣：
    - 每天拆成三段:
      [0~5夜間(6hr), 6~17日間(12hr), 18~23夜間(6hr)]
    - 每段用一個馬可夫鏈序列，從頭初始化
    - day_of_week = current_time.weekday()
    - weather = "Sunny"/"Cloudy"/"Rainy"/"Stormy"/"Night"
    """
    if start_time is None:
        start_time = datetime(2025, 1, 1, 0, 0)
    
    result_data = []
    current_time = start_time
    
    for _day in range(7):  # 7 天
        # 夜間 0~5 (6小時)
        night_seq_1 = generate_night_block(num_hours=6)
        for w in night_seq_1:
            result_data.append([
                current_time.strftime('%Y-%m-%d %H:%M'),
                current_time.weekday(),
                w
            ])
            current_time += timedelta(hours=1)
        
        # 日間 6~17 (12小時)
        day_seq = generate_day_block(num_hours=12)
        for w in day_seq:
            result_data.append([
                current_time.strftime('%Y-%m-%d %H:%M'),
                current_time.weekday(),
                w
            ])
            current_time += timedelta(hours=1)
        
        # 夜間 18~23 (6小時)
        night_seq_2 = generate_night_block(num_hours=6)
        for w in night_seq_2:
            result_data.append([
                current_time.strftime('%Y-%m-%d %H:%M'),
                current_time.weekday(),
                w
            ])
            current_time += timedelta(hours=1)
    
    return result_data

def write_to_csv(data, filename='weather_forecast_7days.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["time", "day_of_week", "weather"])
        writer.writerows(data)


if __name__ == "__main__":
    # 產生 7 天 (168 小時) 的天氣預報 CSV
    start_time = datetime(2025, 1, 1, 0, 0)
    forecast_data = generate_7day_forecast_with_night_state(start_time=start_time)
    write_to_csv(forecast_data, "weather_forecast_7days.csv")
    print("已產生 weather_forecast_7days.csv（168筆），提高自我轉移概率以增加天氣的連續性。")
