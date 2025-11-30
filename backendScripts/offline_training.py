


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
BASE_DIR = Path(__file__).parent
STUDY_DATA = BASE_DIR / ".." / "data" / "Scrolling_Data" / "WristMotion.csv"
STUDY_DATA = STUDY_DATA.resolve()  # optional but nice
WRIST_DATA = BASE_DIR / ".." / "data" / "Studying_Data" / "WristMotion.csv"
WRIST_DATA = WRIST_DATA.resolve()  # optional but nice

WINDOW_SEC = 1
STEP_SEC = 0.5

# ----------------------------
# Loading & parsing helpers
# ----------------------------

def load_wrist_samples_from_csv(path: Path) -> pd.DataFrame:
    """
    Load wrist motion CSV exported from Sensor Logger.

    Returns a DataFrame with at least:
        t   : float seconds (UTC, from 'time' ns)
        ax  : accelerationX
        ay  : accelerationY
        az  : accelerationZ
        rx  : rotationRateX
        ry  : rotationRateY
        rz  : rotationRateZ
    and all the original columns in case we want them later.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

    # Read CSV
    df = pd.read_csv(path)

    # Ensure sorted by time
    df = df.sort_values("time")  # TODO: Validate that time is sorted correctly

    # Add 't' in seconds (ns → s)
    df["t"] = df["time"] / 1_000_000_000.0

    # For convenience, add short aliases expected by later code
    df["ax"] = df["accelerationX"]
    df["ay"] = df["accelerationY"]
    df["az"] = df["accelerationZ"]
    df["rx"] = df["rotationRateX"]
    df["ry"] = df["rotationRateY"]
    df["rz"] = df["rotationRateZ"]

    return df


# ----------------------------
# Feature extraction
# ----------------------------

def extract_features_from_window(window_df: pd.DataFrame) -> Dict:
    """Compute numerical features for a pandas DataFrame window."""
    if window_df is None or window_df.empty:
        return {}

    # Use seconds_elapsed (relative time) or convert time ns -> seconds
    t = window_df["seconds_elapsed"].to_numpy()    # shape (N,)
    # or: t = window_df["time"].to_numpy() / 1e9

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
        # keep for debugging; we’ll drop later when training
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


def windows_from_df(
    df: pd.DataFrame,
    label: str,
    window_sec: float,
    step_sec: float,
) -> tuple[list[dict], list[str]]:
    if df is None or df.empty:
        return [], []

    # use seconds_elapsed as our time axis
    times = df["seconds_elapsed"].to_numpy()
    start_time = times[0]
    end_time = times[-1]

    feature_rows = []
    labels = []

    cur_start = start_time
    while cur_start + window_sec <= end_time:
        cur_end = cur_start + window_sec

        # boolean mask: which rows lie in [cur_start, cur_end]
        mask = (df["seconds_elapsed"] >= cur_start) & (df["seconds_elapsed"] <= cur_end)
        window_df = df.loc[mask]

        if not window_df.empty:
            feats = extract_features_from_window(window_df)
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
    scrolling_df = load_wrist_samples_from_csv(STUDY_DATA)      
    print(f"  Loaded {len(scrolling_df)} rows")
    print(scrolling_df.head(5))

    print("Loading studying samples...")
    studying_df = load_wrist_samples_from_csv(WRIST_DATA)    
    print(f"  Loaded {len(studying_df)} rows")
    print(studying_df.head(5))

    # Generate sliding-window features for each class
    scroll_feats, scroll_labels = windows_from_df(
        df=scrolling_df, label="scrolling", window_sec=WINDOW_SEC, step_sec=STEP_SEC
    )

    study_feats, study_labels = windows_from_df(
        df=studying_df, label="studying", window_sec=WINDOW_SEC, step_sec=STEP_SEC
    )

    all_feats = scroll_feats + study_feats
    all_labels = scroll_labels + study_labels

    if not all_feats:
        raise RuntimeError("No windows were generated – check your data and timestamps.")

    # Build dataframes (faster for following ML training)
    df = pd.DataFrame(all_feats)
    y = pd.Series(all_labels, name="label")    
    print(df.head(4))


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


    # Save model in current directory
    SCRIPT_DIR = Path(__file__).parent.resolve()
    MODEL_OUT = (SCRIPT_DIR.parent / "wrist_rf_model.joblib").resolve()
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
