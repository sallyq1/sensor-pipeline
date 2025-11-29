# wrist_server.py
import json
from flask import Flask, request
from datetime import datetime
from collections import deque   # only if you still want it, but not required now
import numpy as np
import pandas as pd
import joblib

app = Flask(__name__)

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


# -----------------------------
# Streaming / sliding window config
# -----------------------------
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
    ]
)

# Keep track of where we last ended a window (in seconds, same units as t)
last_window_end = None


# -----------------------------
# Feature extraction (DataFrame)
# -----------------------------
def extract_features_from_window(window_df: pd.DataFrame) -> dict:
    """Compute numerical features for a pandas DataFrame window."""
    if window_df is None or window_df.empty:
        return {}

    # time in seconds (epoch) – only used for t_start/t_end (debug)
    t = window_df["t"].to_numpy()

    ax = window_df["accelerationX"].to_numpy()
    ay = window_df["accelerationY"].to_numpy()
    az = window_df["accelerationZ"].to_numpy()

    rx = window_df["rotationRateX"].to_numpy()
    ry = window_df["rotationRateY"].to_numpy()
    rz = window_df["rotationRateZ"].to_numpy()

    # magnitudes
    acc_mag = np.sqrt(ax**2 + ay**2 + az**2)
    rot_mag = np.sqrt(rx**2 + ry**2 + rz**2)

    feats = {
        # keep for debugging; we’ll ignore these when building x_vec (feature_order has no t_*)
        "t_start": float(t[0]),
        "t_end": float(t[-1]),

        "acc_mag_mean": float(acc_mag.mean()),
        "acc_mag_std": float(acc_mag.std()),
        "rot_mag_mean": float(rot_mag.mean()),
        "rot_mag_std": float(rot_mag.std()),

        "ax_mean": float(ax.mean()),
        "ay_mean": float(ay.mean()),
        "az_mean": float(az.mean()),

        "rx_mean": float(rx.mean()),
        "ry_mean": float(ry.mean()),
        "rz_mean": float(rz.mean()),
    }

    return feats


# -----------------------------
# Sliding window over df_buffer
# -----------------------------
def process_sliding_windows():
    """
    Check if we can create new windows over df_buffer and run the model
    for each window.
    """
    global last_window_end, df_buffer

    if df_buffer.empty:
        return

    times = df_buffer["t"].to_numpy()
    latest_time = times[-1]

    # initialize the first window end if needed
    if last_window_end is None:
        last_window_end = times[0] + WINDOW_SEC

    # generate as many windows as we can
    while latest_time >= last_window_end:
        window_end = last_window_end
        window_start = window_end - WINDOW_SEC

        # boolean mask for rows in this time range
        mask = (df_buffer["t"] >= window_start) & (df_buffer["t"] <= window_end)
        window_df = df_buffer.loc[mask]

        if not window_df.empty:
            feats = extract_features_from_window(window_df)
            if feats:
                # debug print of window stats
                start_dt = datetime.fromtimestamp(feats["t_start"])
                end_dt = datetime.fromtimestamp(feats["t_end"])
                print(
                    f"[WINDOW] {start_dt.time()} - {end_dt.time()} "
                    f"acc_mean={feats['acc_mag_mean']:.4f}, "
                    f"acc_std={feats['acc_mag_std']:.4f}, "
                    f"rot_mean={feats['rot_mag_mean']:.4f}, "
                    f"rot_std={feats['rot_mag_std']:.4f}"
                )

                # build feature vector in the same order used in training
                x_vec = np.array([[feats[col] for col in feature_order]])
                pred = model.predict(x_vec)[0]
                proba = model.predict_proba(x_vec).max()
                print(f"[PRED] {pred} (p={proba:.2f})")

        # move to next window
        last_window_end += STEP_SEC

    # Trim df_buffer to keep only the last MAX_BUFFER_SEC seconds
    cutoff = latest_time - MAX_BUFFER_SEC
    df_buffer = df_buffer[df_buffer["t"] >= cutoff].reset_index(drop=True)


# -----------------------------
# HTTP endpoint for Sensor Logger
# -----------------------------
@app.route("/data", methods=["POST"])
def data_endpoint():
    global df_buffer

    if request.method == "POST":
        raw = request.data
        print(f"[RAW] {raw[:200]}...")  # log first ~200 bytes

        msg = json.loads(raw)
        payload = msg.get("payload", [])

        new_rows = []

        for rec in payload:
            if rec.get("name") == "wrist motion":
                # Sensor Logger time is in ns; convert to seconds
                t_sec = rec["time"] / 1_000_000_000.0
                vals = rec.get("values", {})

                row = {
                    "t": t_sec,
                    "accelerationX": float(vals.get("accelerationX", 0.0)),
                    "accelerationY": float(vals.get("accelerationY", 0.0)),
                    "accelerationZ": float(vals.get("accelerationZ", 0.0)),
                    "rotationRateX": float(vals.get("rotationRateX", 0.0)),
                    "rotationRateY": float(vals.get("rotationRateY", 0.0)),
                    "rotationRateZ": float(vals.get("rotationRateZ", 0.0)),
                }
                new_rows.append(row)

        if new_rows:
            new_df = pd.DataFrame(new_rows)
            # Append to global buffer
            df_buffer = pd.concat([df_buffer, new_df], ignore_index=True)
            # Ensure sorted by time (just in case)
            df_buffer = df_buffer.sort_values("t").reset_index(drop=True)

            # After adding new samples, try to form windows
            process_sliding_windows()

    return "ok"


if __name__ == "__main__":
    # Run on all interfaces so your phone can reach it over WiFi
    app.run(host="0.0.0.0", port=8000, debug=True)
