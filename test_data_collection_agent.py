import time
import queue
import pytest
from agents.data_collection_agent import DataCollectionAgent

def dummy_loop_forever():
    # Simulate a brief non-blocking loop.
    time.sleep(0.1)
    return

def test_data_collection_agent_run(monkeypatch):
    # Create a queue for passing data.
    some_queue = queue.Queue()

    # Instantiate the DataCollectionAgent.
    data_agent = DataCollectionAgent(
        broker_host="localhost",
        broker_port=1883,
        topic="energy_data",
        data_queue=some_queue
    )

    # Monkeypatch the MQTT client's loop_forever method so that it doesn't block.
    monkeypatch.setattr(data_agent.client, "loop_forever", dummy_loop_forever)

    # Record the start time.
    start_time = time.time()

    # Run the agent; this should now complete quickly.
    data_agent.run()

    # Calculate the elapsed time.
    elapsed_time = time.time() - start_time

    # Assert that run() returns quickly (e.g., within 1 second).
    assert elapsed_time < 1.0, "run() should not block when loop_forever is replaced with a dummy function."
