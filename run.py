# run.py
from multiprocessing import Process, Queue
from agents.data_collection_agent import DataCollectionAgent
from agents.prediction_agent import run_prediction_agent
import runpy
from utils.data_loader import json_to_dataframe, dataframe_to_json
from agents.p2p_trading_agent.app import run_p2p_agent_app
from agents.energy_manage_agent.app import run_ems_app
import threading


def execute_file(filepath):
    """
    Execute the given Python file in the current thread.
    
    Parameters:
        filepath (str): Path to the Python (.py) file.
    """
    try:
        # Run the Python file as __main__
        runpy.run_path(filepath, run_name="__main__")
    except Exception as e:
        print(f"Error executing file {filepath}: {e}")


def main():
    data_queue = Queue()
    prediction_queue = Queue()

    # Instantiate Agents
    data_agent = DataCollectionAgent(
        broker_host="localhost",
        broker_port=1883,
        topic="energy_data",
        data_queue=data_queue
    )


    
    # Define process wrappers
    def data_collection_process():
        data_agent.add_listener(prediction_process)
        data_agent.run()

    def prediction_process(json_weather_data):
        weather_df = json_to_dataframe(json_weather_data)
        df_7days = run_prediction_agent(weather_df)
        prediction_queue.put(dataframe_to_json(df_7days))

    
    def ems_process():
        flask_thread = threading.Thread(target=run_ems_app)
        flask_thread.start()

    def p2ptrading_process():
        flask_thread = threading.Thread(target=run_p2p_agent_app)
        flask_thread.start()

    # Start processes
    ems_process()
    p2ptrading_process()
    data_collection_process()

    # Optionally join them or keep them as daemons

if __name__ == "__main__":
    main()
