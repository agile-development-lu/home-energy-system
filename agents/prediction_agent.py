# agents/prediction_agent.py

import pickle
import numpy as np
import pandas as pd
import time

class PredictionAgent:
    def __init__(self, consumption_model_path, production_model_path):
        with open(consumption_model_path, 'rb') as f:
            self.consumption_model = pickle.load(f)
        with open(production_model_path, 'rb') as f:
            self.production_model = pickle.load(f)

    def predict(self, latest_data):
        # Suppose the model expects features: [hour_of_day, day_of_week, temperature]
        # This is just a placeholder feature set
        hour_of_day = time.localtime(latest_data['timestamp']).tm_hour
        day_of_week = time.localtime(latest_data['timestamp']).tm_wday
        temperature = latest_data['weather_forecast']['main']['temp']

        input_vector = np.array([[hour_of_day, day_of_week, temperature]])
        
        consumption_pred = self.consumption_model.predict(input_vector)[0]
        production_pred = self.production_model.predict(input_vector)[0]
        
        return {
            'consumption_pred': consumption_pred,
            'production_pred': production_pred
        }

    def run(self, data_queue, prediction_queue):
        """
        - data_queue: queue of real-time sensor/weather data
        - prediction_queue: output queue to pass predictions to EMS agent
        """
        while True:
            if not data_queue.empty():
                latest_data = data_queue.get()
                prediction = self.predict(latest_data)
                print(f"[PredictionAgent] Predictions: {prediction}")
                prediction_queue.put({
                    'timestamp': latest_data['timestamp'],
                    'prediction': prediction
                })
            time.sleep(1)
