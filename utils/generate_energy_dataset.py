import csv
import random
import math
from datetime import datetime, timedelta

# ========== 定義白天 & 夜晚的狀態空間與馬可夫鏈參數 ==========

day_states = ["Sunny", "Cloudy", "Rainy", "Stormy"]
night_states = ["Night", "Cloudy", "Rainy", "Stormy"]

day_initial_dist = [0.50, 0.30, 0.17, 0.03]
night_initial_dist = [0.50, 0.30, 0.17, 0.03]

day_transition_matrix = [
    [0.70, 0.20, 0.07, 0.03],  # from Sunny
    [0.20, 0.50, 0.25, 0.05],  # from Cloudy
    [0.10, 0.25, 0.60, 0.05],  # from Rainy
    [0.10, 0.20, 0.20, 0.50]   # from Stormy
]

night_transition_matrix = [
    [0.75, 0.15, 0.07, 0.03],  # from Night
    [0.30, 0.50, 0.15, 0.05],  # from Cloudy
    [0.20, 0.20, 0.55, 0.05],  # from Rainy
    [0.10, 0.20, 0.20, 0.50]   # from Stormy
]

def markov_chain_next_state(current_state, states, transition_matrix):
    idx = states.index(current_state)
    probs = transition_matrix[idx]
    next_s = random.choices(states, weights=probs, k=1)[0]
    return next_s

def init_day_state():
    return random.choices(day_states, weights=day_initial_dist, k=1)[0]

def init_night_state():
    return random.choices(night_states, weights=night_initial_dist, k=1)[0]

def generate_energy_data(num_rows=9000, 
                         start_time=datetime(2024, 1, 1, 0, 0)):
    """
    產生虛擬家庭用電 & 太陽能發電小時資料 (共 num_rows 筆)。
    調整：
      1) 面板面積 40 -> 25 m²，效率 0.22 -> 0.18 (降低發電量)
      2) 夜間耗電再降低一些
    """
    data = []
    current_time = start_time
    
    # ==== 太陽能板的輸出 ====
    panel_area_m2 = 23.0      # 原本40，現在25
    panel_efficiency = 0.20   # 原本0.22，現在0.18

    current_day_state = None
    current_night_state = None
    
    for _ in range(num_rows):
        hour_of_day = current_time.hour
        day_of_week = current_time.weekday()
        day_of_year = current_time.timetuple().tm_yday
        
        # ========== 白天 or 夜晚 馬可夫鏈 ==========
        if 6 <= hour_of_day <= 17:
            # 白天
            if current_day_state is None:
                current_day_state = init_day_state()
            else:
                current_day_state = markov_chain_next_state(
                    current_day_state, day_states, day_transition_matrix
                )
            chosen_weather = current_day_state
            current_night_state = None
        else:
            # 夜晚
            if current_night_state is None:
                current_night_state = init_night_state()
            else:
                current_night_state = markov_chain_next_state(
                    current_night_state, night_states, night_transition_matrix
                )
            chosen_weather = current_night_state
            current_day_state = None
        
        # ========== 用電量 (kWh) (平日 vs. 週末 + 時段) ==========

        if day_of_week < 5:
            # 平日 (週一～週五)
            if 0 <= hour_of_day <= 4:
                # *原本 0.5~1.0，現改為更低 0.3~0.7
                power_consumption = random.uniform(0.3, 0.7)
            elif 5 <= hour_of_day <= 6:
                power_consumption = random.uniform(1.0, 1.5)
            elif 7 <= hour_of_day <= 8:
                power_consumption = random.uniform(1.0, 2.0)
            elif 9 <= hour_of_day <= 16:
                power_consumption = random.uniform(0.5, 0.9)
            elif 17 <= hour_of_day <= 22:
                power_consumption = random.uniform(1.5, 3.0)
            else:  # 23點
                # 原本 1.0~1.5 -> 稍微再低一點 0.7~1.2
                power_consumption = random.uniform(0.7, 1.2)
        else:
            # 週末 (週六、週日)
            if 0 <= hour_of_day <= 5:
                # *原本 0.8~1.4，現改為 0.5~1.0
                power_consumption = random.uniform(0.5, 1.0)
            elif 6 <= hour_of_day <= 8:
                power_consumption = random.uniform(1.2, 2.0)
            elif 9 <= hour_of_day <= 16:
                power_consumption = random.uniform(1.0, 2.0)
            elif 17 <= hour_of_day <= 22:
                power_consumption = random.uniform(1.8, 3.2)
            else:  # 23點
                # 原本 1.2~1.8 -> 略降到 1.0~1.5
                power_consumption = random.uniform(1.0, 1.5)
        
        # ========== 太陽輻照度 & 發電量計算 ==========

        # 白天 6~17 才有日照，夜間=0
        if 6 <= hour_of_day <= 8:
            base_irradiance = random.uniform(200, 400)
        elif 9 <= hour_of_day <= 11:
            base_irradiance = random.uniform(400, 600)
        elif 12 <= hour_of_day <= 14:
            base_irradiance = random.uniform(600, 800)
        elif 15 <= hour_of_day <= 17:
            base_irradiance = random.uniform(300, 600)
        else:
            base_irradiance = 0.0
        
        # 季節性因子 (夏至約在一年中第172天)
        seasonal_factor = 1.0 + 0.3 * math.sin(2 * math.pi * (day_of_year - 172) / 365.0)
        
        # 大幅拉低 Cloudy/Rainy/Stormy
        weather_factor_map = {
            "Sunny": 1.0,   # 晴天100%
            "Cloudy": 0.4,  # 陰天40%
            "Rainy": 0.1,   # 雨天10%
            "Stormy": 0.0,  # 暴風0%
            "Night": 1.0    # 夜晚 (基礎輻照度=0，實際=0)
        }
        
        weather_factor = weather_factor_map[chosen_weather]
        
        solar_irradiance = base_irradiance * seasonal_factor * weather_factor
        # 隨機再 ±10%
        solar_irradiance *= (1 + 0.1 * random.uniform(-1, 1))
        
        # 發電量 (kWh) = (W/m^2 × 面積 × 1hr)/1000 × 效率
        power_in_Wh = solar_irradiance * panel_area_m2
        power_in_kWh = power_in_Wh / 1000.0
        solar_generation = power_in_kWh * panel_efficiency
        
        power_consumption = round(power_consumption, 2)
        solar_irradiance = round(solar_irradiance, 2)
        solar_generation = round(solar_generation, 3)
        
        data.append([
            current_time.strftime('%Y-%m-%d %H:%M'),
            day_of_week,
            chosen_weather,
            power_consumption,
            solar_irradiance,
            solar_generation
        ])
        
        current_time += timedelta(hours=1)
    
    return data

def write_to_csv(data, filename='energy_dataset.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "time",
            "day_of_week",
            "weather",
            "power_consumption_kWh",
            "solar_irradiance_Wm2",
            "solar_generation_kWh"
        ])
        writer.writerows(data)

if __name__ == "__main__":
    dataset = generate_energy_data(num_rows=9000)
    write_to_csv(dataset, 'energy_dataset.csv')
    print("已產生 energy_dataset.csv，太陽能板面積降為25m²、效率0.18，夜間耗電也略為降低。")
