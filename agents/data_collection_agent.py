import time
import json
import paho.mqtt.client as mqtt
from queue import Queue

class DataCollectionAgent:
    def __init__(self, broker_host, broker_port, topic, data_queue: Queue):
        """
        :param broker_host: MQTT broker host address
        :param broker_port: MQTT broker port
        :param topic: MQTT topic on which sensor data is published
        :param data_queue: A multiprocessing or threading Queue for sending data to other agents
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.data_queue = data_queue

        # List to hold additional listeners (callbacks)
        self.listeners = []

        # Set up MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def add_listener(self, callback):
        """
        Register a listener callback that will be executed when a message is received.
        
        :param callback: A function that accepts a single argument (the data dictionary).
        """
        self.listeners.append(callback)
        print(f"[DataCollectionAgent] Listener {callback.__name__} added.")

    def on_connect(self, client, userdata, flags, rc):
        """Callback when the client connects to the broker."""
        if rc == 0:
            print("[DataCollectionAgent] Connected to MQTT Broker!")
            client.subscribe(self.topic)
            print(f"[DataCollectionAgent] Subscribed to topic: {self.topic}")
        else:
            print(f"[DataCollectionAgent] Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        """Callback when a message is received on the subscribed topic."""
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)
            # Publish to the shared queue so other agents can consume
            self.data_queue.put(data)
            print(f"[DataCollectionAgent] Received MQTT data: {data}")

            # Execute any additional listener callbacks
            for listener in self.listeners:
                try:
                    listener(data)
                except Exception as e:
                    print(f"[DataCollectionAgent] Error executing listener {listener.__name__}: {e}")

        except json.JSONDecodeError as e:
            print(f"[DataCollectionAgent] JSON Decode Error: {e}")

    def run(self):
        """
        Connect to MQTT broker and keep listening for incoming messages.
        This will block (loop_forever) until the process is killed.
        """
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        print(f"[DataCollectionAgent] Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
        self.client.loop_forever()
