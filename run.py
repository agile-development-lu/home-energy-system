# run.py
from multiprocessing import Process, Queue
from agents.data_collection_agent import DataCollectionAgent
from agents.prediction_agent import PredictionAgent
from agents.energy_management_agent import EnergyManagementAgent
from agents.p2p_trading_agent import P2PTradingAgent

def main():
    data_queue = Queue()
    prediction_queue = Queue()

    # Instantiate Agents
    data_agent = DataCollectionAgent(sensor_api_url="xxx",
                                     weather_api_url="xxx")
    
    pred_agent = PredictionAgent(consumption_model_path="models/xxx.pkl",
                                 production_model_path="models/xxx.pkl")

    p2p_agent = P2PTradingAgent(peers=["house1", "house2"])
    ems_agent = EnergyManagementAgent(battery_capacity=10.0, p2p_trader=p2p_agent)

    # Define process wrappers
    def data_collection_process():
        while True:
            data = data_agent.collect_data()
            data_queue.put(data)

    def prediction_process():
        while True:
            if not data_queue.empty():
                latest_data = data_queue.get()
                prediction = pred_agent.predict(latest_data)
                prediction_queue.put({
                    'timestamp': latest_data['timestamp'],
                    'prediction': prediction
                })

    def ems_process():
        while True:
            if not prediction_queue.empty():
                # For demonstration, re-use the same data for "real_data".
                # In real use, you'd have separate real-time data + forecast data.
                pred_data = prediction_queue.get()
                real_data = pred_data.copy()
                decision = ems_agent.optimize_usage(real_data, pred_data['prediction'])
                print(f"[EMS Process] Decision: {decision}")

    # Create processes
    p_data = Process(target=data_collection_process)
    p_pred = Process(target=prediction_process)
    p_ems = Process(target=ems_process)

    # Start processes
    p_data.start()
    p_pred.start()
    p_ems.start()

    # Optionally join them or keep them as daemons

if __name__ == "__main__":
    main()
