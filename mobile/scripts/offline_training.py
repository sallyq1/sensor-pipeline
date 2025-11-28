


# offline_train.py
#
# Train a RandomForest classifier offline using wrist motion data
# collected via Sensor Logger HTTP push and saved as .jsonl files.

import json
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# ----------------------------
# CONFIG – adjust these
# ----------------------------

# Paths to your JSONL log files (one sample per line from HTTP push)
SCROLLING_FILE = Path("scrolling.jsonl")
STUDYING_FILE = Path("studying.jsonl")

# Labels to assign to each file
LABEL_SCROLLING = "scrolling"
LABEL_STUDYING = "studying"

# Sliding window settings (seconds)
WINDOW_SEC = 1.0    # window length
STEP_SEC = 0.5      # stride between windows

# Output model file
MODEL_OUT = Path("wrist_rf_model.joblib")


# ----------------------------
# Loading & parsing helpers
# ----------------------------

def load_wrist_samples_from_jsonl(path: Path) -> List[Dict]:
    """
    Load all 'wrist motion' samples from a jsonl log file.

    Returns a list of samples:
    {
        "t":   float seconds (UTC),
        "ax":  float,
        "ay":  float,
        "az":  float,
        "rx":  float,
        "ry":  float,
        "rz":  float,
    }
    """
    samples = []
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            payload = msg.get("payload", [])
            for rec in payload:
                if rec.get("name") == "wrist motion":
                    t_sec = rec["time"] / 1_000_000_000.0  # ns → seconds
                    vals = rec.get("values", {})
                    samples.append(
                        {
                            "t": t_sec,
                            "ax": float(vals.get("accelerationX", 0.0)),
                            "ay": float(vals.get("accelerationY", 0.0)),
                            "az": float(vals.get("accelerationZ", 0.0)),
                            "rx": float(vals.get("rotationRateX", 0.0)),
                            "ry": float(vals.get("rotationRateY", 0.0)),
                            "rz": float(vals.get("rotationRateZ", 0.0)),
                        }
                    )

    # Ensure sorted by time
    samples.sort(key=lambda s: s["t"])
    return samples


# ----------------------------
# Feature extraction
# ----------------------------

def extract_features_from_window(window_samples: List[Dict]) -> Dict:
    """Compute numerical features for a list of sample dicts."""
    if not window_samples:
        return {}

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
        # we keep these mainly for debugging; will drop them before training
        "t_start": float(t[0]),
        "t_end": float(t[-1]),

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


def windows_from_samples(
    samples: List[Dict],
    label: str,
    window_sec: float,
    step_sec: float,
) -> Tuple[List[Dict], List[str]]:
    """
    Turn a sequence of samples into sliding-window feature rows + labels.

    Returns:
        feature_rows: list of feature dicts
        labels:       list of labels (same length)
    """
    if not samples:
        return [], []

    times = np.array([s["t"] for s in samples])
    start_time = times[0]
    end_time = times[-1]

    feature_rows = []
    labels = []

    cur_start = start_time
    while cur_start + window_sec <= end_time:
        cur_end = cur_start + window_sec
        # Pick samples in this window
        w = [s for s in samples if cur_start <= s["t"] <= cur_end]

        if len(w) > 0:
            feats = extract_features_from_window(w)
            if feats:
                feature_rows.append(feats)
                labels.append(label)

        cur_start += step_sec

    return feature_rows, labels


# ----------------------------
# Main training pipeline
# ----------------------------

def main():
    print("Loading scrolling samples...")
    scrolling_samples = load_wrist_samples_from_jsonl(SCROLLING_FILE)
    print(f"  Loaded {len(scrolling_samples)} samples")

    print("Loading studying samples...")
    studying_samples = load_wrist_samples_from_jsonl(STUDYING_FILE)
    print(f"  Loaded {len(studying_samples)} samples")

    # Generate sliding-window features for each class
    print("Creating windows for scrolling...")
    scroll_feats, scroll_labels = windows_from_samples(
        scrolling_samples, LABEL_SCROLLING, WINDOW_SEC, STEP_SEC
    )
    print(f"  {len(scroll_feats)} windows")

    print("Creating windows for studying...")
    study_feats, study_labels = windows_from_samples(
        studying_samples, LABEL_STUDYING, WINDOW_SEC, STEP_SEC
    )
    print(f"  {len(study_feats)} windows")

    all_feats = scroll_feats + study_feats
    all_labels = scroll_labels + study_labels

    if not all_feats:
        raise RuntimeError("No windows were generated – check your data and timestamps.")

    # Build DataFrame
    df = pd.DataFrame(all_feats)
    y = pd.Series(all_labels, name="label")

    # Drop time columns from training features
    feature_cols = [c for c in df.columns if not c.startswith("t_")]
    X = df[feature_cols].values

    print("Feature columns:", feature_cols)
    print("X shape:", X.shape, "y shape:", y.shape)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
    )

    print("Training RandomForest...")
    clf.fit(X_train, y_train)

    print("Evaluating...")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))

    # Save model + feature ordering
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": clf,
            "feature_order": feature_cols,
            "window_sec": WINDOW_SEC,
            "step_sec": STEP_SEC,
        },
        MODEL_OUT,
    )
    print(f"Saved model to {MODEL_OUT.resolve()}")


if __name__ == "__main__":
    main()
