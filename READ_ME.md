# IIO-Predictive-Gateway: Turbofan Thermal Health Monitor
An Industrial IoT (IIoT) edge-computing pipeline designed to monitor a fleet of turbofan engines, predict impending thermal runaway, and trigger automated safety protocols. This project utilizes the NASA CMAPSS dataset to simulate real-world engine degradation.

## System Architecture
1. **Edge Data Ingestion:** Python-based gateway reads raw sensor telemetry.
2. **Signal Processing:** Real-time noise reduction via a 10-cycle sliding window rolling mean.
3. **Predictive Analytics:** Linear regression modeling to estimate Remaining Useful Life (RUL).
4. **Time-Series Persistence:** Processed metrics pushed to InfluxDB via synchronous API.
5. **Operational Observability:** Grafana dashboard for real-time fleet health and failure countdowns.

## Features
* **Fault Injection Simulation:** Includes a "Sabotage" logic module to simulate a thermal runaway event on a target unit.
* **Automated Kill Switch:** Logic-driven emergency shutdown when predictive thresholds are breached.
* **Dynamic Leaderboard:** Real-time sorting of the fleet based on current thermal stress.
* **Predictive Countdown:** Live "Cycles to Failure" estimate based on the slope of temperature degradation.

## System Evolution: Reactive vs. Predictive
Below is the architectural comparison between the initial build (edge_monitor.py) and the current production version (monitor.py).

| Feature | Phase 1: Reactive Monitor (`edge_monitor.py`) | Phase 2: Predictive Gateway (`monitor.py`) |
| :--- | :--- | :--- |
| **Logic Type** | **Threshold-Based**: Triggers only when the limit is breached. | **Trend-Based**: Forecasts failure before the limit is reached. |
| **Signal Integrity** | **Raw Data**: Sensitive to sensor noise and transient spikes. | **Digital Signal Processing**: Implements a 10-cycle Rolling Mean filter. |
| **Math Engine** | Simple Boolean Comparison ($Current > Limit$). | **Linear Regression**: Uses `numpy.polyfit` for slope-intercept analysis. |
| **Key Metric** | Current Temperature (°R). | **RUL (Remaining Useful Life)**: Estimated cycles until failure. |
| **Safety Protocol** | Binary (Nominal / Shutdown). | **Tiered Alerts**: Nominal $\rightarrow$ Warning $\rightarrow$ Shutdown. |
| **Fault Injection** | Passive observation of historical data. | **Active Simulation**: Real-time "heat soak" injection on target units. |
---

## Installation & Setup
1. **Prerequisites**
    * Python 3.9+
    * InfluxDB OSS 2.x
    * Grafana (Local or Cloud)

2. **Environment Configuration** <br> Create a .env file in the root directory:
    ```
    INFLUX_URL=http://localhost:8086
    INFLUX_TOKEN=your-super-secret-token
    INFLUX_ORG=your-org
    INFLUX_BUCKET=Turbine_Metrics
    TEMP_THRESHOLD=48.8
    ```

3. **Install Dependencies**

    ```
    pip install pandas numpy influxdb-client python-dotenv
    ```

4. **Run the Simulation** <br>
Ensure `train_FD001.txt` is in the directory and launch the gateway:

    ```
    python predictive_monitor.py
    ```

## Dashboard Configuration
To recreate the Command Center, import the provided Flux queries into Grafana panels:

A. **Fleet Pulse (Time-Series)**
```bash
from(bucket: "Turbine_Metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "engine_vitals")
  |> filter(fn: (r) => r["_field"] == "LPT_temp_rolling")
  |> group(columns: ["unit_id"])
```
B. **Failure Countdown (Stat Panel)**
```bash
from(bucket: "Turbine_Metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["unit_id"] == "5")
  |> filter(fn: (r) => r["_field"] == "TTF_estimate")
  |> last()
```
## Technical Highlights
* **Linear Regression Model**: Utilizes `numpy.polyfit` to calculate the rate of temperature change ($\Delta T / \Delta cycle$).
* **Data Transformation**: Uses Flux `pivot()` and Grafana `Labels to fields` transformations to handle dynamic status tagging.
* **Concurrency**: Synchronous write-heavy workload simulation with precise timing delays.

---

## Raw Data Headers

| Column Index | Field Name | Description |
| :--- | :--- | :--- |
| 0 | Unit Number | The specific engine ID (1 to 100) |
| 1 | Time (Cycles) | The "odometer" of the engine |
| 2-4 | Operational Settings | Altitude, Mach Number, etc. |
| 5-25 | Sensors 1 - 21 | The "Vitals" (Temp, Pressure, Fan Speed) |

### "High-Value" Sensors
* Sensor 2 (Index 6): Total Temperature at LPC outlet
* Sensor 11 (Index 15): Total Temperature at LPT outlet
* Sensor 4 (Index 8): Total Temperature at HPC outlet