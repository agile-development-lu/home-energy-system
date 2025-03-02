from flask import Flask, jsonify, render_template, request
from agent import BehavioralSegmentationAgent
import time

app = Flask(__name__)

# 模拟设备数据（包含使用次数和总使用时长）
appliance_data = {
    "Washing Machine": {"start_time": None, "usage": 0, "current_usage": 0, "usage_count": 0},
    "Refrigerator": {"start_time": None, "usage": 0, "current_usage": 0, "usage_count": 0},
    "Oven": {"start_time": None, "usage": 0, "current_usage": 0, "usage_count": 0},
    "Air Conditioner": {"start_time": None, "usage": 0, "current_usage": 0, "usage_count": 0},
    "Heater": {"start_time": None, "usage": 0, "current_usage": 0, "usage_count": 0},
    "Dishwasher": {"start_time": None, "usage": 0, "current_usage": 0, "usage_count": 0},
}

# 初始化行为分割算法实例
agent = BehavioralSegmentationAgent()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_appliance():
    appliance = request.json.get("appliance")
    if appliance in appliance_data and appliance_data[appliance]["start_time"] is None:
        appliance_data[appliance]["start_time"] = time.time()
        appliance_data[appliance]["usage_count"] += 1  # 增加使用次数
    return jsonify({"message": f"{appliance} started", "appliance_data": appliance_data})


@app.route("/stop", methods=["POST"])
def stop_appliance():
    appliance = request.json.get("appliance")
    if appliance in appliance_data and appliance_data[appliance]["start_time"] is not None:
        elapsed_time = time.time() - appliance_data[appliance]["start_time"]
        appliance_data[appliance]["usage"] += elapsed_time / 60  # 转换为分钟
        appliance_data[appliance]["start_time"] = None
    return jsonify({"message": f"{appliance} stopped", "appliance_data": appliance_data})


@app.route("/get-priority", methods=["GET"])
def get_priority():
    """
    Use usage and usage_count from appliance_data to update agent and calculate priority.
    """
    new_data = [
        {
            "appliance": key,
            "usage": value["usage"],
            "usage_count": value["usage_count"],
        }
        for key, value in appliance_data.items()
    ]
    agent.update_data(new_data)
    agent.prioritize_appliances()

    # 返回优先级结果
    priorities = [{"appliance": k, "priority": v} for k, v in agent.appliance_priority.items()]
    return jsonify(priorities)


@app.route("/get-status", methods=["GET"])
def get_status():
    """
    Return the real-time status of all appliances, including usage time and count.
    """
    for appliance, data in appliance_data.items():
        if data["start_time"] is not None:
            elapsed_time = time.time() - data["start_time"]
            appliance_data[appliance]["current_usage"] = elapsed_time / 60  # 当前使用时间（分钟）
        else:
            appliance_data[appliance]["current_usage"] = 0
    return jsonify(appliance_data)


if __name__ == "__main__":
    app.run(debug=True)


