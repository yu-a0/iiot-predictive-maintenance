import os
import time
import pandas as pd
import numpy as np
from collections import deque
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- 1. CONFIGURATION ---
load_dotenv()
URL = os.getenv("INFLUX_URL", "http://localhost:8086")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

# Target Threshold for the simulation
THRESHOLD = 48.8 

client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# --- 2. ANALYTICS GLOBALS ---
fleet_memory = {}
WINDOW_SIZE = 10 
dead_units = set()

def stream_to_pipeline(file_path):
    cols = {0: 'unit', 1: 'cycle', 6: 'LPC_temp', 8: 'HPC_temp', 15: 'LPT_temp'}
    
    try:
        df = pd.read_csv(file_path, sep='\s+', header=None).rename(columns=cols)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return

    # Simulation Variables
    SABOTAGE_UNIT = "5"
    heat_soak = 0.0 

    print(f"\n🚀 PREDICTIVE GATEWAY ONLINE")
    print(f"🛡️ KILL SWITCH: {THRESHOLD}°R")
    print(f"🔮 PREDICTING FAILURE FOR: Unit {SABOTAGE_UNIT}\n")

    for _, row in df.iterrows():
        unit_id = str(int(row['unit']))
        lpt_raw = float(row['LPT_temp'])
        cycle = int(row['cycle'])

        if unit_id in dead_units:
            continue

        # 1. FAULT INJECTION (Sabotage Unit 5)
        if unit_id == SABOTAGE_UNIT:
            heat_soak += 0.05 
            lpt_raw += heat_soak
        
        # 2. DATA BUFFERING
        if unit_id not in fleet_memory:
            fleet_memory[unit_id] = deque(maxlen=WINDOW_SIZE)
        fleet_memory[unit_id].append(lpt_raw)

        # 3. EDGE ANALYTICS
        rolling_avg = sum(fleet_memory[unit_id]) / len(fleet_memory[unit_id])
        
        # --- 3b. LINEAR REGRESSION (PREDICTION) ---
        ttf_estimate = 999.0  # Default to 'Safe'
        
        if len(fleet_memory[unit_id]) == WINDOW_SIZE:
            # X = [0,1,2...9], Y = recent temperatures
            x = np.arange(WINDOW_SIZE)
            y = np.array(fleet_memory[unit_id])
            
            # Perform linear fit: y = mx + c
            slope, intercept = np.polyfit(x, y, 1)
            
            if slope > 0:
                # Calculate how many steps until y hits THRESHOLD
                # Steps = (Target - Current Intercept) / Slope
                # Then subtract current index to get 'Remaining'
                steps_to_fail = (THRESHOLD - intercept) / slope
                ttf_estimate = max(0.0, steps_to_fail - (WINDOW_SIZE - 1))

        # 4. KILL SWITCH & STATUS
        status = "NOMINAL"
        if rolling_avg > THRESHOLD:
            print(f"\n[!!!] EMERGENCY SHUTDOWN: Unit {unit_id} at Cycle {cycle}!")
            status = "CRITICAL_SHUTDOWN"
            dead_units.add(unit_id)
        elif ttf_estimate < 15:
            status = "PREDICTED_FAILURE_WARNING"

        # 5. PUSH TO DASHBOARD
        point = Point("engine_vitals") \
            .tag("unit_id", unit_id) \
            .tag("status", status) \
            .field("LPT_temp_raw", lpt_raw) \
            .field("LPT_temp_rolling", rolling_avg) \
            .field("TTF_estimate", float(ttf_estimate)) # Our new predictive field
        
        write_api.write(BUCKET, ORG, point)
        
        # Heartbeat
        print(f"📡 Unit {unit_id} | Temp: {rolling_avg:.2f} | TTF: {ttf_estimate:.1f} cycles  ", end='\r')
        time.sleep(0.01)

if __name__ == "__main__":
    stream_to_pipeline('train_FD001.txt')