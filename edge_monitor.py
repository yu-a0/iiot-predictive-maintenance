import os
import time
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# --- 1. INITIALIZATION & SECRETS ---
load_dotenv()

# Load credentials from .env
URL = os.getenv("INFLUX_URL")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

# Load operational thresholds
# NASA CMAPSS Sensor 11 (LPT Temp) usually operates around 150-160
THRESHOLD = float(os.getenv("TEMP_THRESHOLD", 155.0))

# Initialize InfluxDB Client
client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# --- 2. CORE LOGIC ---

def stream_to_pipeline(file_path):
    """
    Fleet-Wide Edge Agent:
    - Reads industrial telemetry line-by-line to simulate real-time.
    - Implements Edge Logic: Local 'Kill Switch' for each unit.
    - Pushes tagged data to InfluxDB for Fleet-Wide observability.
    """
    # Mapping the industry-standard NASA columns
    # 0: Unit ID, 1: Cycle, 6: LPC Temp, 8: HPC Temp, 15: LPT Temp
    cols = {0: 'unit', 1: 'cycle', 6: 'LPC_temp', 8: 'HPC_temp', 15: 'LPT_temp'}
    
    try:
        # Load the NASA dataset (Fleet View)
        # Using sep='\s+' because the NASA files are space-delimited
        df = pd.read_csv(file_path, sep='\s+', header=None).rename(columns=cols)
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Ensure the file is in the root directory.")
        return

    # 'The Foreman's Memory': Track which units have been shut down locally
    dead_units = set()

    print(f"--- EDGE GATEWAY ONLINE | MONITORING FLEET ---")
    print(f"--- THRESHOLD SET TO: {THRESHOLD} | BUCKET: {BUCKET} ---\n")

    for _, row in df.iterrows():
        unit_id = str(int(row['unit']))
        lpt_val = float(row['LPT_temp'])
        cycle = int(row['cycle'])

        # Skip telemetry if the machine has already been "killed" by Edge Logic
        if unit_id in dead_units:
            continue

        # 1. THE 2026 TWIST: PER-UNIT EDGE ANALYTICS
        # This decision happens locally, immediately.
        status = "NOMINAL"
        if lpt_val > THRESHOLD:
            print(f"[!] EMERGENCY SHUTDOWN: Unit {unit_id} | Cycle {cycle} | Temp {lpt_val} exceeds limit!")
            status = "CRITICAL_SHUTDOWN"
            dead_units.add(unit_id)
            # Logic for physical shutdown (GPIO/PLC) would trigger here

        # 2. TELEMETRY PIPELINE (Pushing to InfluxDB)
        # We tag by unit_id and status for easy filtering in Grafana
        point = Point("engine_vitals") \
            .tag("unit_id", unit_id) \
            .tag("status", status) \
            .field("LPT_temp", lpt_val) \
            .field("HPC_temp", float(row['HPC_temp'])) \
            .field("cycle", cycle)
        
        try:
            write_api.write(BUCKET, ORG, point)
        except Exception as e:
            print(f"\n[!] Connection Error: {e}")
            break

        # Heartbeat monitor for the console
        print(f"Monitoring Fleet... Units Active: {100 - len(dead_units)} | Current Unit: {unit_id} ", end='\r')
        
        # Simulation speed: 0.02s creates a fast-moving live dashboard
        time.sleep(0.02) 

    print(f"\n\n--- SIMULATION COMPLETE ---")
    print(f"Total Fleet Units: 100")
    print(f"Total Critical Failures Prevented: {len(dead_units)}")

# --- 3. EXECUTION ---

if __name__ == "__main__":
    # Ensure you have downloaded train_FD001.txt from NASA
    stream_to_pipeline('train_FD001.txt')