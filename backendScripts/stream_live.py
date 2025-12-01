# wrist_server.py
import json
from flask import Flask, request, jsonify
from datetime import datetime
from collections import deque   # only if you still want it, but not required now
import numpy as np
import pandas as pd
import joblib
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# -----------------------------
# Load trained model bundle
# -----------------------------
from pathlib import Path
import joblib

SCRIPT_DIR = Path(__file__).parent.resolve()
MODEL_OUT = (SCRIPT_DIR.parent / "wrist_rf_model.joblib").resolve()

# Load the saved bundle
MODEL_BUNDLE = joblib.load(MODEL_OUT)
model = MODEL_BUNDLE["model"]
feature_order = MODEL_BUNDLE["feature_order"]
WINDOW_SEC = MODEL_BUNDLE.get("window_sec", 1.0)
STEP_SEC = MODEL_BUNDLE.get("step_sec", 0.5)

print(f"Loaded model from {MODEL_OUT}")



# --------------------------------------------
# Streaming / sliding window config
# --------------------------------------------
MAX_BUFFER_SEC = 30        # keep last 30 seconds of data
# Global DataFrame buffer; each row is one sample
# Columns will be: ["t", "accelerationX", "accelerationY", "accelerationZ",
#                   "rotationRateX", "rotationRateY", "rotationRateZ"]
df_buffer = pd.DataFrame(
    columns=[
        "t",
        "accelerationX",
        "accelerationY",
        "accelerationZ",
        "rotationRateX",
        "rotationRateY",
        "rotationRateZ",
        "gravityX",
        "gravityY",
        "gravityZ"
    ]
)

phone_df_buffer = pd.DataFrame(
    columns=[
        "t",

        # acceleration
        "accelerationX",
        "accelerationY",
        "accelerationZ",

        # rotation
        "rotationRateX",
        "rotationRateY",
        "rotationRateZ",

        # gravity
        "gravityX",
        "gravityY",
        "gravityZ",

        # quaternion (optional but your streaming code includes them)
        "quaternionW",
        "quaternionX",
        "quaternionY",
        "quaternionZ",
    ]
)


#-----------------------------------------------------------------------------------
# Keeps track of windows (After a window is created this function stores its class)
#-----------------------------------------------------------------------------------
from collections import deque
import time

WINDOW_HISTORY = deque(maxlen=2000)
NEXT_WINDOW_ID = 0

def record_window(label: str, proba: float):
    global NEXT_WINDOW_ID
    window = {
        "id": NEXT_WINDOW_ID,
        "timestamp": time.time(),
        "label": label,
        "proba": proba,   # single float
    }
    WINDOW_HISTORY.append(window)
    NEXT_WINDOW_ID += 1

#---------------------------------------------------------------------------------------------------------------------------------
# Return majority label in list of windows (Return majority label that occurs in a window - (grouped time period))
#------------------------------------------------------------------------------------------------------------------------------------------------
from collections import Counter

def summarize_windows(windows, threshold=0.7):
    """
    Given a list of window dicts, return a majority label
    if its fraction ≥ threshold, else None.
    """
    if not windows:
        return None, 0.0

    labels = [w["label"] for w in windows]
    counts = Counter(labels)
    label, count = counts.most_common(1)[0]
    frac = count / len(labels)

    if frac >= threshold:
        return label, frac
    else:
        return None, frac
    

#---------------------------------------------------------------------------------------------------
# API endpoint to store windows (Store newly processed windows (since last call) in endpoint for frontend)
#--------------------------------------- =----------------------------------------------------------
@app.route("/api/windows", methods=["GET"])
def get_windows():
    since = request.args.get("since", type=float)
    now = time.time()

    if since is None:
        new_windows = list(WINDOW_HISTORY)
    else:
        new_windows = [w for w in WINDOW_HISTORY if w["timestamp"] > since]

    summary_label, frac = summarize_windows(new_windows)

    return jsonify({
        "windows": new_windows,
        "summary": {
            "label": summary_label,
            "confidence": frac,      # fraction of windows that agree
            "window_count": len(new_windows),
        },
        "server_time": now,
    })

# -----------------------------------------------------------------------------
# Feature extraction (DataFrame) (Extract metrics for each window of 0.5 seconds)
# ------------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Feature extraction for a single device (watch OR phone)
# Mirrors offline_train.extract_features_from_window
# -----------------------------------------------------------------------------
def extract_features_from_window(window_df: pd.DataFrame) -> dict:
    """
    Compute numerical features for a pandas DataFrame window.

    Expects columns (ideally):
      seconds_elapsed or t,
      rotationRateX/Y/Z, gravityX/Y/Z,
      accelerationX/Y/Z,
      pitch, roll, yaw,
      plus any quaternion fields (ignored here).

    This matches the offline training extractor so that
    watch_* and phone_* features line up with feature_order.
    """
    if window_df is None or window_df.empty:
        return {}

    cols = window_df.columns

    # --- Time axis ---
    if "seconds_elapsed" in cols:
        t = window_df["seconds_elapsed"].to_numpy()
    elif "t" in cols:
        t = window_df["t"].to_numpy()
    else:
        # fallback: fake a simple 0..N-1 time axis
        t = np.arange(len(window_df), dtype=float)

    # helper: safely get a column, or zeros if missing
    def get_col(name: str):
        if name in cols:
            return window_df[name].to_numpy()
        # default to zeros with correct length
        return np.zeros(len(window_df), dtype=float)

    # --- Raw components ---
    ax = get_col("accelerationX")
    ay = get_col("accelerationY")
    az = get_col("accelerationZ")

    rx = get_col("rotationRateX")
    ry = get_col("rotationRateY")
    rz = get_col("rotationRateZ")

    gx = get_col("gravityX")
    gy = get_col("gravityY")
    gz = get_col("gravityZ")


    # --- Magnitudes ---
    acc_mag  = np.sqrt(ax**2 + ay**2 + az**2)
    rot_mag  = np.sqrt(rx**2 + ry**2 + rz**2)
    grav_mag = np.sqrt(gx**2 + gy**2 + gz**2)

    feats = {
        # keep for debugging; dropped when building X in offline training
        "t_start": float(t[0]),
        "t_end":   float(t[-1]),

        # magnitudes
        "acc_mag_mean":  float(acc_mag.mean()),
        "acc_mag_std":   float(acc_mag.std()),
        "rot_mag_mean":  float(rot_mag.mean()),
        "rot_mag_std":   float(rot_mag.std()),
        "grav_mag_mean": float(grav_mag.mean()),
        "grav_mag_std":  float(grav_mag.std()),

        # acceleration axes
        "ax_mean": float(ax.mean()),
        "ay_mean": float(ay.mean()),
        "az_mean": float(az.mean()),

        # rotation rate axes
        "rx_mean": float(rx.mean()),
        "ry_mean": float(ry.mean()),
        "rz_mean": float(rz.mean()),

        # gravity axes
        "gx_mean": float(gx.mean()),
        "gy_mean": float(gy.mean()),
        "gz_mean": float(gz.mean()),

    }

    return feats



# -----------------------------------------------------------------------------------------
# Sliding window over df_buffer (Group raw data over time periods of 0.5 sec)
# -----------------------------------------------------------------------------------------

# Keep track of where we last ended a window (in seconds, same units as t)
last_window_end = None
def process_sliding_windows():
    """
    Check if we can create new windows over df_buffer (watch)
    and phone_df_buffer (phone), and run the model for each window.

    This mirrors offline windows_from_watch_and_phone + training:
    - window over watch timeline
    - require both watch AND phone data in the window
    - build watch_* and phone_* feature dict
    - order features according to feature_order
    """
    global last_window_end, df_buffer, phone_df_buffer

    # Need both watch + phone data to classify like offline
    if df_buffer.empty or phone_df_buffer.empty:
        return

    # df_buffer is sorted by "t" when we append
    watch_times = df_buffer["t"].to_numpy(dtype=float)
    latest_time = watch_times[-1]

    # initialize the first window end if needed
    if last_window_end is None:
        # first window covers [t0, t0 + WINDOW_SEC]
        last_window_end = watch_times[0] + WINDOW_SEC

    # generate as many windows as we can
    while latest_time >= last_window_end:
        window_end = last_window_end
        window_start = window_end - WINDOW_SEC

        # --- Window from the watch (driver) ---
        mask_watch = (df_buffer["t"] >= window_start) & (df_buffer["t"] <= window_end)
        watch_win = df_buffer.loc[mask_watch]

        # --- Window from the phone ---
        mask_phone = (phone_df_buffer["t"] >= window_start) & (phone_df_buffer["t"] <= window_end)
        phone_win = phone_df_buffer.loc[mask_phone]

        if not watch_win.empty and not phone_win.empty:
            watch_feats = extract_features_from_window(watch_win)
            phone_feats = extract_features_from_window(phone_win)

            if watch_feats and phone_feats:
                # Build combined feature row with prefixes identical to offline
                row = {}

                # keep watch times as "watch_t_*"
                for k, v in watch_feats.items():
                    row[f"watch_{k}"] = v

                # only non-time features from phone (offline drops t_* from phone)
                for k, v in phone_feats.items():
                    if not k.startswith("t_"):
                        row[f"phone_{k}"] = v

                # Debug print
                start_ts = float(watch_win["t"].iloc[0])
                end_ts   = float(watch_win["t"].iloc[-1])
                start_dt = datetime.fromtimestamp(start_ts)
                end_dt   = datetime.fromtimestamp(end_ts)
                print(
                    f"[WINDOW] {start_dt.time()} - {end_dt.time()} "
                    f"watch_n={len(watch_win)}, phone_n={len(phone_win)}"
                )

                # Build feature vector in the same order used in training
                try:
                    x_vec = np.array([[row[col] for col in feature_order]])
                except KeyError as e:
                    # If anything is missing, log and skip this window
                    print(f"[ERROR] Missing feature {e} in online pipeline; skipping window.")
                    x_vec = None

                if x_vec is not None:
                    pred = model.predict(x_vec)[0]
                    proba = float(model.predict_proba(x_vec).max())
                    print(f"[PRED] {pred} (p={proba:.2f})")
                    record_window(pred, proba)

        # move to next window
        last_window_end += STEP_SEC

    # Trim both buffers to keep only the last MAX_BUFFER_SEC seconds (based on watch time)
    cutoff = latest_time - MAX_BUFFER_SEC
    df_buffer = df_buffer[df_buffer["t"] >= cutoff].reset_index(drop=True)
    phone_df_buffer = phone_df_buffer[phone_df_buffer["t"] >= cutoff].reset_index(drop=True)



# -----------------------------------------------------------
# HTTP endpoint for Sensor Logger (Get raw data)
# -----------------------------------------------------------
@app.route("/data", methods=["POST"])
def data_endpoint():
    # df_buffer: watch ("wrist motion") samples
    # phone_df_buffer: phone IMU samples (accelerometer/gyro/gravity/orientation)
    global df_buffer, phone_df_buffer

    if request.method == "POST":
        raw = request.data
        print(f"[RAW] {raw[:200]}...")  # log first ~200 bytes

        msg = json.loads(raw)
        payload = msg.get("payload", [])

        watch_rows = []
        phone_rows_by_time = {}  # key: time_ns, value: dict of merged phone sensors at that time

        for rec in payload:
            name = rec.get("name", "")
            t_ns = rec.get("time")
            vals = rec.get("values", {})

            # --- WATCH: wrist motion only ---
            if name == "wrist motion":
                # Sensor Logger time is in ns; convert to seconds
                t_sec = t_ns / 1_000_000_000.0

                row = {
                    "t": t_sec,
                    "accelerationX": float(vals.get("accelerationX", 0.0)),
                    "accelerationY": float(vals.get("accelerationY", 0.0)),
                    "accelerationZ": float(vals.get("accelerationZ", 0.0)),

                    "rotationRateX": float(vals.get("rotationRateX", 0.0)),
                    "rotationRateY": float(vals.get("rotationRateY", 0.0)),
                    "rotationRateZ": float(vals.get("rotationRateZ", 0.0)),

                    "gravityX": float(vals.get("gravityX", 0.0)),
                    "gravityY": float(vals.get("gravityY", 0.0)),
                    "gravityZ": float(vals.get("gravityZ", 0.0)),

                }
                watch_rows.append(row)

            # --- PHONE: accelerometer / gyroscope / gravity / orientation ---
            # Ignore uncalibrated variants and any "watch ..." sensors here.
            elif name in ("accelerometer", "gyroscope", "gravity", "orientation"):
                # Phone IMU
                t_sec = t_ns / 1_000_000_000.0
                row = phone_rows_by_time.setdefault(t_ns, {"t": t_sec}) # Gets value if key exists or uses rightmost argument for default value if t_ns does not exist

                if name == "accelerometer":
                    # Phone accel: x,y,z -> accelerationX/Y/Z
                    row["accelerationX"] = float(vals.get("x", 0.0))
                    row["accelerationY"] = float(vals.get("y", 0.0))
                    row["accelerationZ"] = float(vals.get("z", 0.0))

                elif name == "gyroscope":
                    # Phone gyro: x,y,z -> rotationRateX/Y/Z
                    row["rotationRateX"] = float(vals.get("x", 0.0))
                    row["rotationRateY"] = float(vals.get("y", 0.0))
                    row["rotationRateZ"] = float(vals.get("z", 0.0))

                elif name == "gravity":
                    # Phone gravity: x,y,z -> gravityX/Y/Z
                    row["gravityX"] = float(vals.get("x", 0.0))
                    row["gravityY"] = float(vals.get("y", 0.0))
                    row["gravityZ"] = float(vals.get("z", 0.0))

                elif name == "orientation":
                    # Phone orientation: yaw/pitch/roll + quaternion
                    row["yaw"]   = float(vals.get("yaw", 0.0))
                    row["pitch"] = float(vals.get("pitch", 0.0))
                    row["roll"]  = float(vals.get("roll", 0.0))

                    row["quaternionW"] = float(vals.get("qw", 0.0))
                    row["quaternionX"] = float(vals.get("qx", 0.0))
                    row["quaternionY"] = float(vals.get("qy", 0.0))
                    row["quaternionZ"] = float(vals.get("qz", 0.0))

        # --- Append watch rows to watch buffer ---
        if watch_rows:
            new_watch_df = pd.DataFrame(watch_rows)
            df_buffer = pd.concat([df_buffer, new_watch_df], ignore_index=True)
            df_buffer = df_buffer.sort_values("t").reset_index(drop=True)

        # --- Append phone rows to phone buffer ---
        if phone_rows_by_time:
            new_phone_df = pd.DataFrame(list(phone_rows_by_time.values()))
            phone_df_buffer = pd.concat([phone_df_buffer, new_phone_df], ignore_index=True)
            phone_df_buffer = phone_df_buffer.sort_values("t").reset_index(drop=True)

        # After adding new samples, try to form windows & classify
        process_sliding_windows()

    return "ok"



if __name__ == "__main__":
    # Run on all interfaces so your phone can reach it over WiFi
    app.run(host="0.0.0.0", port=8000, debug=True)
