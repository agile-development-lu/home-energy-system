import numpy as np
import pandas as pd
from math import sqrt
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

class EnergyPredictionAgent:
    """
    A bigger LSTM-based Agent that uses:
     - day_of_week (0~6) -> one-hot
     - hour_of_day (0~23) -> one-hot
     - weather (categorical) -> one-hot
     - past consumption, past generation
    to predict next-hour consumption & generation.

    Then we do iterative forecasting for 7 days.
    """

    def __init__(self, train_path, n_in=1):
        self.train_path = train_path
        self.n_in = n_in

        self.model = None
        self.scaler = None
        self.feature_columns = []
        # 记录训练时出现的 day_of_week, hour_of_day, weather 各自可能值
        # 方便在预测时保证 one-hot 维度一致
        self.day_of_week_values = list(range(7))       # 0..6
        self.hour_of_day_values = list(range(24))      # 0..23
        self.weather_categories = []                   # 动态收集

    def load_and_prepare_data(self):
        """
        1) 读取 CSV (time, day_of_week, weather, power_consumption_kWh, ...)
        2) 提取 day_of_week -> one-hot(7列)
           提取 hour_of_day -> one-hot(24列) [需从 time 列解析, 或 CSV 也可已有]
           weather -> one-hot
           consumption,generation -> 2列
        3) 构造 (X,y) for single-step => 预测下1小时 [cons,gen].
        """
        df = pd.read_csv(self.train_path)

        # 假设 CSV 包含列: 
        # [time, day_of_week, weather, power_consumption_kWh, solar_irradiance_Wm2, solar_generation_kWh]
        # 其中 hour_of_day 可能要从 time 解析 (若 CSV 里没有)
        if 'hour_of_day' not in df.columns:
            # 若 CSV 没有 hour_of_day，就从 time 解析
            df['parsed_time'] = pd.to_datetime(df['time'])
            df['hour_of_day'] = df['parsed_time'].dt.hour
        # day_of_week 已经在 CSV 里 (0..6)
        # weather 是字符串分类

        # ========== One-hot: day_of_week (0..6) ==========
        dow_dummies = pd.get_dummies(df['day_of_week'], prefix='dow', dtype='float32')
        # 这样会生成 dow_0..dow_6

        # ========== One-hot: hour_of_day (0..23) ==========
        hod_dummies = pd.get_dummies(df['hour_of_day'], prefix='hod', dtype='float32')

        # ========== One-hot: weather ==========
        weather_dummies = pd.get_dummies(df['weather'], prefix='w', dtype='float32')
        self.weather_categories = weather_dummies.columns.tolist()

        # ========== 数值列: consumption, generation ==========
        # 只演示 consumption + generation
        df_num = df[['power_consumption_kWh','solar_generation_kWh']].astype('float32')

        # ========== 拼接全部特征 (X) ==========
        final_df = pd.concat([dow_dummies, hod_dummies, weather_dummies, df_num], axis=1)

        self.feature_columns = final_df.columns.tolist()  # 记录列名顺序

        # 归一化
        values = final_df.values  # shape=(samples, F)
        self.scaler = MinMaxScaler(feature_range=(0,1))
        scaled = self.scaler.fit_transform(values)

        # 构造单步 (X->y) =>  y=[cons,gen] 下个时刻
        X, Y = self.make_supervised_single_step(scaled)

        # train/test split
        n_samples = len(X)
        n_train = int(n_samples*0.7)
        train_X, train_y = X[:n_train], Y[:n_train]
        test_X, test_y = X[n_train:], Y[n_train:]

        # reshape => (samples, timesteps=1, features=F)
        F = train_X.shape[1]
        train_X = train_X.reshape((train_X.shape[0], 1, F))
        test_X  = test_X.reshape((test_X.shape[0],  1, F))

        return train_X, train_y, test_X, test_y

    def make_supervised_single_step(self, scaled):
        """
        给定 scaled 数组 shape=(samples, F),
        构造单步预测: X[t] => Y[t+1]'s (cons,gene).
        consumption,generation 假设在 final_df 最后2列 => index = -2, -1
        """
        X, Y = [], []
        for i in range(len(scaled)-1):
            current_feat = scaled[i]    # shape=(F,)
            next_label   = scaled[i+1] # shape=(F,)
            # y => next_label[-2], next_label[-1]
            yrow = next_label[-2:]  # [cons, gen]
            X.append(current_feat)
            Y.append(yrow)
        return np.array(X), np.array(Y)

    def build_lstm_model(self, input_dim):
        """
        构建两层LSTM，每层128单元 + Dense(2)输出(单步cons,gen).
        """
        model = Sequential()
        model.add(LSTM(128, return_sequences=True, input_shape=(1, input_dim)))
        model.add(LSTM(128, return_sequences=False))
        model.add(Dense(2))
        model.compile(loss='mae', optimizer='adam')
        return model

    def train(self, epochs=50, batch_size=32):
        train_X, train_y, test_X, test_y = self.load_and_prepare_data()
        input_dim = train_X.shape[2]
        self.model = self.build_lstm_model(input_dim)

        history = self.model.fit(
            train_X, train_y,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(test_X, test_y),
            verbose=2,
            shuffle=False
        )
        # 评估
        preds = self.model.predict(test_X)
        # 反归一化 + clamp
        inv_preds, inv_true = [], []
        F = len(self.feature_columns)
        for i in range(len(preds)):
            dummy_pred = np.zeros(F, dtype='float32')
            dummy_true = np.zeros(F, dtype='float32')
            dummy_pred[-2:] = preds[i]
            dummy_true[-2:] = test_y[i]

            invp = self.scaler.inverse_transform([dummy_pred])[0]
            invt = self.scaler.inverse_transform([dummy_true])[0]

            cP = max(invp[-2], 0)
            gP = max(invp[-1], 0)
            cT = max(invt[-2], 0)
            gT = max(invt[-1], 0)

            inv_preds.append([cP,gP])
            inv_true.append([cT,gT])

        inv_preds = np.array(inv_preds)
        inv_true  = np.array(inv_true)

        rmse_cons = sqrt(mean_squared_error(inv_true[:,0], inv_preds[:,0]))
        rmse_gene = sqrt(mean_squared_error(inv_true[:,1], inv_preds[:,1]))
        print(f"Test RMSE consumption: {rmse_cons:.3f}, generation: {rmse_gene:.3f}")

    def predict_7days(self, weather_forecast_csv, start_consumption, start_generation, start_hour_of_day=0):
        """
        迭代预测未来168小时(7天). 只要给 "weather_forecast_7days.csv" [time, day_of_week, weather],
        还需要 hour_of_day (或从 time 解析).
        用上一小时的cons,gen预测下一小时, 直到推完168小时.
        """
        if self.model is None:
            print("Model not trained!")
            return None

        wf = pd.read_csv(weather_forecast_csv)
        # 假设它有: time, day_of_week, weather
        # 可能也需要 hour_of_day => 如果没有，也可 parse from time
        if 'hour_of_day' not in wf.columns:
            wf['parsed_time'] = pd.to_datetime(wf['time'])
            wf['hour_of_day'] = wf['parsed_time'].dt.hour

        results = []
        prev_cons = start_consumption
        prev_gene = start_generation

        for i in range(len(wf)):
            row = wf.iloc[i]
            # day_of_week => row["day_of_week"]
            # hour_of_day => row["hour_of_day"]
            # weather => row["weather"]

            # 1) day_of_week one-hot
            dow_vector = [0]*7
            if 0 <= row["day_of_week"] <= 6:
                dow_vector[int(row["day_of_week"])] = 1

            # 2) hour_of_day one-hot
            hod_vector = [0]*24
            h = row['hour_of_day']
            if 0 <= h <= 23:
                hod_vector[h] = 1

            # 3) weather one-hot
            #   我们知道 self.weather_categories 在训练中出现过 w_Cloudy, w_Sunny...
            #   先做 dict: cat->0
            weath_map = dict.fromkeys([c[2:] for c in self.weather_categories], 0)  
            #  c[2:] 去掉 "w_" 前缀
            w_label = row['weather']
            if w_label in weath_map:
                weath_map[w_label] = 1

            # 4) 拼成特征 = [dow_..., hod_..., w_..., consumption, generation]
            cat_vector = dow_vector + hod_vector + list(weath_map.values()) + [prev_cons, prev_gene]

            # 5) 归一化
            arr_2d = np.array([cat_vector], dtype='float32')
            scaled_2d = self.scaler.transform(arr_2d)
            # reshape => (1,1,F)
            input_lstm = scaled_2d.reshape((1,1, scaled_2d.shape[1]))

            # 6) 预测 => (1,2)
            yhat = self.model.predict(input_lstm)[0]
            # 7) 反归一化 + clamp
            F = len(self.feature_columns)
            dummy_pred = np.zeros(F, dtype='float32')
            dummy_pred[-2:] = yhat
            inv_ = self.scaler.inverse_transform([dummy_pred])[0]
            cons_pred = max(inv_[-2], 0)
            gene_pred = max(inv_[-1], 0)

            results.append({
                "time": row["time"],
                "day_of_week": row["day_of_week"],
                "weather": row["weather"],
                "consumption_pred": cons_pred,
                "generation_pred": gene_pred
            })

            # 8) 更新 prev_cons, prev_gene
            prev_cons = cons_pred
            prev_gene = gene_pred

        df_res = pd.DataFrame(results)
        return df_res


# ============ 使用举例 =============
if __name__=="__main__":
    """
    使用:
     1) 准备 `energy_dataset.csv` (包含 time, day_of_week, weather, power_consumption_kWh, solar_generation_kWh, hour_of_day)
        或者从 time 解析 hour_of_day.
     2) 训练 + 2层 LSTM(128) + epochs=50
     3) 读取 weather_forecast_7days.csv => [time, day_of_week, weather, hour_of_day], 
        迭代预测 7天(168小时).
    """
    agent = EnergyPredictionAgent(train_path="energy_dataset.csv", n_in=1)
    agent.train(epochs=50, batch_size=32)  # 训练更多轮，如 50,100

    # 假设当前时刻 consumption=1.0, generation=0.3
    df_7days = agent.predict_7days(
        weather_forecast_csv="weather_forecast_7days.csv",
        start_consumption=1.0,
        start_generation=0.3,
        start_hour_of_day=0
    )

    print(df_7days.head(48))

    df_7days.to_csv("predicted_7days.csv", index=False, float_format="%.3f")  #输出CSV文件给其他端口备用

    # 可视化:
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, time

def plot_7days_with_daily_split(csv_file):
    # 1) 读取预测结果 CSV
    df = pd.read_csv(csv_file)
    print("Columns:", df.columns.tolist())

    # 确保 time 转成 datetime
    df['time'] = pd.to_datetime(df['time'])

    # 2) 建立图表，画下方折线
    fig, ax = plt.subplots(figsize=(12,6))

    ax.plot(df['time'], df['consumption_pred'], label='Consumption', color='red')
    ax.plot(df['time'], df['generation_pred'], label='Generation', color='green')

    ax.set_title("Predicted Energy Consumption & Generation (Next 7 Days)")
    ax.set_ylabel("kWh")
    ax.legend()

    # 让下方 x 轴只在 0:00 和 12:00 打刻度
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12], interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
    plt.xticks(rotation=45)

    # 3) 在图中**每天 0:00**处画虚线(竖直)
    #   先取出日期 (df['time'].dt.date) 的 unique 列表
    df['date'] = df['time'].dt.date
    unique_dates = sorted(df['date'].unique())

    # 对于每一天, 找到该日期 0:00 的 datetime, 若 df 中恰好有 or 接近 0:00 行, 找到 x 值
    for d in unique_dates:
        # 构造"当天 0:00"
        day_start = datetime.combine(d, time(0,0))
        # 转成数值
        x_val = mdates.date2num(day_start)
        # 画竖线
        ax.axvline(x=x_val, color='gray', linestyle='--')

    # 4) 创建顶部 X 轴: 显示“周几+天气”，位置在**正午(12:00)**处
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.xaxis.set_ticks_position("top")

    # day_of_week 映射到英文
    # 假设 day_of_week=0 => Monday, 1=>Tuesday, ..., 6=>Sunday
    dow_map = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    # 对于每一天, 找该日期 12:00 => 取 weather, day_of_week
    top_positions = []
    top_labels = []

    for d in unique_dates:
        # 构造"当天 12:00"
        noon_dt = datetime.combine(d, time(12,0))
        # 在 df 找到与 noon_dt 完全匹配的行(如果 exactly有这行), 
        # 若数据每小时都有, 应该有一条, 否则我们找最接近12点的行
        row_noon = df.loc[df['time'] == noon_dt]
        if row_noon.empty:
            # 如果找不到, 可以选择跳过 or 找最近小时
            # 这里演示: 找距 12点最近的一行
            # abs(df['time'] - noon_dt).idxmin()
            idx_approx = (df['time'] - noon_dt).abs().idxmin()
            row_noon = df.loc[[idx_approx]]
        
        # 取 day_of_week, weather
        # 假设只有一行
        row_noon = row_noon.iloc[0]
        # day_of_week => int
        dow_int = int(row_noon['day_of_week'])
        dow_str = dow_map[dow_int] if (0 <= dow_int < 7) else str(dow_int)
        # weather => str
        weath = row_noon['weather']

        # x 位置
        x_noon = mdates.date2num(row_noon['time'])
        top_positions.append(x_noon)
        # 标签: "Mon\nSunny"
        top_labels.append(f"{dow_str}\n{weath}")

    ax2.set_xticks(top_positions)
    ax2.set_xticklabels(top_labels, rotation=0)
    ax2.set_xlabel("DayOfWeek & Weather (Top)")

    plt.tight_layout()
    plt.show()

if __name__=="__main__":
    # 假设 predicted_7days.csv 中包含:
    # ['time','day_of_week','weather','consumption_pred','generation_pred']
    plot_7days_with_daily_split("predicted_7days.csv")


