import queue
from agents.data_collection_agent import DataCollectionAgent

some_queue = queue.Queue()

data_agent = DataCollectionAgent(
    broker_host="localhost",
    broker_port=1883,
    topic="energy_data",
    data_queue=some_queue
)
data_agent.run()  # This blocks inside loop_forever()