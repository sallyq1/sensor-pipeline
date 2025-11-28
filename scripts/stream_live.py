# wrist_server.py
import json
from flask import Flask, request
from collections import deque
from datetime import datetime
import numpy as np

app = Flask(__name__)


# Import model
import joblib

# MODEL_BUNDLE = joblib.load("wrist_rf_model.joblib")
# model = MODEL_BUNDLE["model"]
# feature_order = MODEL_BUNDLE["feature_order"]

# --- Sliding window configuration ---
WINDOW_SEC = 1.0      # length of each window in seconds
STEP_SEC = 0.5        # how far we slide between windows

# We store only recent samples (e.g. last 30 seconds)
MAX_BUFFER_SEC = 30
MAX_SAMPLES = 5000    # just a safety cap

# Buffer of samples: each entry is a dict:
# {"t": float_seconds, "ax":..., "ay":..., "az":..., "rx":..., "ry":..., "rz":...}
buffer = deque(maxlen=MAX_SAMPLES)

# Keep track of where we last ended a window
last_window_end = None


def extract_features(window_samples):
    """Compute simple features from a list of sample dicts."""
    if not window_samples:
        return None

    t = np.array([s["t"] for s in window_samples])

    ax = np.array([s["ax"] for s in window_samples])
    ay = np.array([s["ay"] for s in window_samples])
    az = np.array([s["az"] for s in window_samples])

    rx = np.array([s["rx"] for s in window_samples])
    ry = np.array([s["ry"] for s in window_samples])
    rz = np.array([s["rz"] for s in window_samples])

    acc_mag = np.sqrt(ax**2 + ay**2 + az**2)
    rot_mag = np.sqrt(rx**2 + ry**2 + rz**2)

    feats = {
        "t_start": t[0],
        "t_end": t[-1],
        "acc_mag_mean": float(np.mean(acc_mag)),
        "acc_mag_std": float(np.std(acc_mag)),
        "rot_mag_mean": float(np.mean(rot_mag)),
        "rot_mag_std": float(np.std(rot_mag)),
        "ax_mean": float(np.mean(ax)),
        "ay_mean": float(np.mean(ay)),
        "az_mean": float(np.mean(az)),
        "rx_mean": float(np.mean(rx)),
        "ry_mean": float(np.mean(ry)),
        "rz_mean": float(np.mean(rz)),
    }

    return feats


def process_sliding_windows():
    """Check if we can create new windows and print features for each."""
    global last_window_end

    if not buffer:
        return

    # Convert buffer to list for easier slicing
    buf = list(buffer)
    latest_time = buf[-1]["t"]

    if last_window_end is None:
        # Initialize so that the first window ends at the first full WINDOW_SEC
        last_window_end = buf[0]["t"] + WINDOW_SEC

    # Create as many windows as possible without skipping time
    # Each loop advances last_window_end by STEP_SEC
    while latest_time >= last_window_end:
        window_end = last_window_end
        window_start = window_end - WINDOW_SEC

        window_samples = [s for s in buf if window_start <= s["t"] <= window_end]

        feats = extract_features(window_samples)
        if feats is not None:
            start_dt = datetime.fromtimestamp(feats["t_start"])
            end_dt = datetime.fromtimestamp(feats["t_end"])
            print(
                f"[WINDOW] {start_dt.time()} - {end_dt.time()} "
                f"acc_mean={feats['acc_mag_mean']:.4f}, "
                f"acc_std={feats['acc_mag_std']:.4f}, "
                f"rot_mean={feats['rot_mag_mean']:.4f}, "
                f"rot_std={feats['rot_mag_std']:.4f}"
            )

            # build vector in the same feature order
            x_vec = np.array([[feats[col] for col in feature_order]])
            pred = model.predict(x_vec)[0]
            proba = model.predict_proba(x_vec).max()
            print(f"[PRED] {pred} (p={proba:.2f})")

        # Move to next window
        last_window_end += STEP_SEC

    # Also trim buffer by time (keep only last MAX_BUFFER_SEC seconds)
    cutoff = latest_time - MAX_BUFFER_SEC
    while buffer and buffer[0]["t"] < cutoff:
        buffer.popleft()


@app.route("/data", methods=["POST"])
def data_endpoint():
    """Endpoint Sensor Logger pushes to."""
    if request.method == "POST":
        raw = request.data
        print(f"[RAW] {raw[:200]}...")  # log first 200 bytes for sanity

        msg = json.loads(raw)
        payload = msg.get("payload", [])

        for rec in payload:
            if rec.get("name") == "wrist motion":
                # Sensor Logger time is in ns; convert to seconds
                t_sec = rec["time"] / 1_000_000_000.0
                vals = rec.get("values", {})

                sample = {
                    "t": t_sec,
                    "ax": float(vals.get("accelerationX", 0.0)),
                    "ay": float(vals.get("accelerationY", 0.0)),
                    "az": float(vals.get("accelerationZ", 0.0)),
                    "rx": float(vals.get("rotationRateX", 0.0)),
                    "ry": float(vals.get("rotationRateY", 0.0)),
                    "rz": float(vals.get("rotationRateZ", 0.0)),
                }
                buffer.append(sample)

        # After adding new samples, try to create windows
        process_sliding_windows()

    return "ok"


if __name__ == "__main__":
    # Run on all interfaces so your phone can reach it over WiFi
    app.run(host="0.0.0.0", port=8000, debug=True)


