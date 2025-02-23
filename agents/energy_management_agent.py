# agents/energy_management_agent.py

import time

class EnergyManagementAgent:
    def __init__(self, battery_capacity, p2p_trader=None):
        self.battery_capacity = battery_capacity
        self.current_battery_soc = 0.5 * battery_capacity
        self.p2p_trader = p2p_trader

    def optimize_usage(self, real_data, prediction):
        """
        Example rule-based approach:
        1. Use solar generation to supply load first.
        2. Store excess in battery if not full.
        3. If still surplus, offer to P2P market.
        4. If not enough generation, discharge battery if available or buy from grid.
        """
        load = real_data['sensor_reading']
        solar_gen = real_data['panel_output']
        battery_soc = real_data['battery_soc']  # or track internally if more realistic
        # This is a simplistic approach - you’d do more advanced optimization here.

        net_surplus = solar_gen - load
        action = "idle"

        if net_surplus > 0:
            # Surplus
            space_in_battery = self.battery_capacity - battery_soc
            if space_in_battery > 0:
                # Charge battery
                action = f"charge_battery_{min(space_in_battery, net_surplus)}"
            else:
                # Sell to P2P
                if self.p2p_trader:
                    self.p2p_trader.post_energy_surplus(net_surplus)
                action = "sell_surplus"
        else:
            # Deficit
            if battery_soc > abs(net_surplus):
                # Discharge battery
                action = f"discharge_battery_{abs(net_surplus)}"
            else:
                # Buy from grid or P2P
                if self.p2p_trader:
                    # Attempt to buy from P2P
                    if self.p2p_trader.request_energy(abs(net_surplus)):
                        action = "buy_from_p2p"
                    else:
                        action = "buy_from_grid"
                else:
                    action = "buy_from_grid"

        return action

    def run(self, data_queue, prediction_queue):
        while True:
            if not data_queue.empty() and not prediction_queue.empty():
                real_data = data_queue.get()
                pred_data = prediction_queue.get()
                decision = self.optimize_usage(real_data, pred_data['prediction'])
                print(f"[EnergyManagementAgent] Decision: {decision}")
            time.sleep(1)
