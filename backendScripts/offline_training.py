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

# --- Wrist IMU Scrolling ---
SCROLL_WATCH = BASE_DIR / ".." / "data" / "New_Scrolling_Data" / "WristMotion.csv"
SCROLL_WATCH = SCROLL_WATCH.resolve()
print(SCROLL_WATCH)

# --- Wrist IMU Studying ---
STUDY_WATCH = BASE_DIR / ".." / "data" / "New_Studying_Data" / "WristMotion.csv"
STUDY_WATCH = STUDY_WATCH.resolve()

# --- Phone IMU (studying) ---
STUDY_PHONE_ACCEL   = (BASE_DIR / ".." / "data" / "New_Studying_Data" / "Accelerometer.csv").resolve()
STUDY_PHONE_GYRO    = (BASE_DIR / ".." / "data" / "New_Studying_Data" / "Gyroscope.csv").resolve()
STUDY_PHONE_GRAVITY = (BASE_DIR / ".." / "data" / "New_Studying_Data" / "Gravity.csv").resolve()
STUDY_PHONE_ORIENT  = (BASE_DIR / ".." / "data" / "New_Studying_Data" / "Orientation.csv").resolve()

# --- Phone IMU (scrolling) ---
SCROLL_PHONE_ACCEL   = (BASE_DIR / ".." / "data" / "New_Scrolling_Data" / "Accelerometer.csv").resolve()
SCROLL_PHONE_GYRO    = (BASE_DIR / ".." / "data" / "New_Scrolling_Data" / "Gyroscope.csv").resolve()
SCROLL_PHONE_GRAVITY = (BASE_DIR / ".." / "data" / "New_Scrolling_Data" / "Gravity.csv").resolve()
SCROLL_PHONE_ORIENT  = (BASE_DIR / ".." / "data" / "New_Scrolling_Data" / "Orientation.csv").resolve()

# --- Window Sizes for grouping data points
WINDOW_SEC = 1
STEP_SEC = 0.5

# -----------------------------------------
# Watch and Phone IMU Extraction
# Input: Paths
# Output: Single Dataframe containing data
# ------------------------------------------
def load_watch_imu(path: Path) -> pd.DataFrame:
    """
    Load wrist motion CSV exported from Sensor Logger.

    Expected columns (at least):
        time, seconds_elapsed,
        rotationRateX, rotationRateY, rotationRateZ,
        gravityX, gravityY, gravityZ,
        accelerationX, accelerationY, accelerationZ,
        quaternionW, quaternionX, quaternionY, quaternionZ,
        pitch, roll, yaw
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

    # Read CSV
    df = pd.read_csv(path)

    # Make sure key columns exist
    required_cols = [
        "time", "seconds_elapsed",
        "rotationRateX", "rotationRateY", "rotationRateZ",
        "gravityX", "gravityY", "gravityZ",
        "accelerationX", "accelerationY", "accelerationZ",
        "quaternionW", "quaternionX", "quaternionY", "quaternionZ",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in {path.name}: {missing}")

    # Sort by time axis (we'll use seconds_elapsed everywhere else)
    df = df.sort_values("seconds_elapsed").reset_index(drop=True)

    # Ensure numeric dtypes (sometimes CSVs come in as strings)
    num_cols = required_cols  # all of these should be numeric
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

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

def load_phone_imu(
    accel_path: Path,
    gyro_path: Path,
    grav_path: Path,
    orient_path: Path,
) -> pd.DataFrame:
    # --- Read all CSVs ---
    acc = pd.read_csv(accel_path)
    gyr = pd.read_csv(gyro_path)
    grav = pd.read_csv(grav_path)
    ori = pd.read_csv(orient_path)

    # Ensure sorted
    for df in (acc, gyr, grav, ori):
        df.sort_values("seconds_elapsed", inplace=True)
        df.reset_index(drop=True, inplace=True)

    # --- Rename axes to match watch schema ---
    acc = acc.rename(columns={
        "x": "accelerationX",
        "y": "accelerationY",
        "z": "accelerationZ",
    })

    gyr = gyr.rename(columns={
        "x": "rotationRateX",
        "y": "rotationRateY",
        "z": "rotationRateZ",
    })

    grav = grav.rename(columns={
        "x": "gravityX",
        "y": "gravityY",
        "z": "gravityZ",
    })

    ori = ori.rename(columns={
        "qw": "quaternionW",
        "qx": "quaternionX",
        "qy": "quaternionY",
        "qz": "quaternionZ",
    })
    # yaw / pitch / roll already have the same names you used

    # --- Merge on time + seconds_elapsed ---
    phone_df = acc.merge(
        gyr[["time", "seconds_elapsed", "rotationRateX", "rotationRateY", "rotationRateZ"]],
        on=["time", "seconds_elapsed"],
        how="inner",
    ).merge(
        grav[["time", "seconds_elapsed", "gravityX", "gravityY", "gravityZ"]],
        on=["time", "seconds_elapsed"],
        how="inner",
    ).merge(
        ori[[
            "time", "seconds_elapsed",
            "quaternionW", "quaternionX", "quaternionY", "quaternionZ"
        ]],
        on=["time", "seconds_elapsed"],
        how="inner",
    )

    # Add t (seconds) and axis aliases, to mirror the watch loader
    phone_df["t"] = phone_df["time"] / 1_000_000_000.0

    phone_df["ax"] = phone_df["accelerationX"]
    phone_df["ay"] = phone_df["accelerationY"]
    phone_df["az"] = phone_df["accelerationZ"]
    phone_df["rx"] = phone_df["rotationRateX"]
    phone_df["ry"] = phone_df["rotationRateY"]
    phone_df["rz"] = phone_df["rotationRateZ"]

    return phone_df

# ----------------------------
# Window Feature extraction
# Input: Rows from a dataframe belonging to a window
# Output: Features for that window
# ----------------------------
def extract_features_from_window(window_df: pd.DataFrame) -> Dict:
    """
    Compute numerical features for a pandas DataFrame window.

    Expects columns (from load_wrist_df_from_csv):
      time, seconds_elapsed,
      rotationRateX/Y/Z, gravityX/Y/Z,
      accelerationX/Y/Z,
      quaternionW/X/Y/Z,
      pitch, roll, yaw,
      plus t, ax/ay/az, rx/ry/rz aliases.
    """
    if window_df is None or window_df.empty:
        return {}

    # --- Time axis (use seconds_elapsed as relative time) ---
    t = window_df["seconds_elapsed"].to_numpy()

    # --- Raw components ---
    ax = window_df["accelerationX"].to_numpy()
    ay = window_df["accelerationY"].to_numpy()
    az = window_df["accelerationZ"].to_numpy()

    rx = window_df["rotationRateX"].to_numpy()
    ry = window_df["rotationRateY"].to_numpy()
    rz = window_df["rotationRateZ"].to_numpy()

    gx = window_df["gravityX"].to_numpy()
    gy = window_df["gravityY"].to_numpy()
    gz = window_df["gravityZ"].to_numpy()

    # qw = window_df["quaternionW"].to_numpy()
    # qx = window_df["quaternionX"].to_numpy()
    # qy = window_df["quaternionY"].to_numpy()
    # qz = window_df["quaternionZ"].to_numpy()

    # pitch = window_df["pitch"].to_numpy()
    # roll  = window_df["roll"].to_numpy()
    # yaw   = window_df["yaw"].to_numpy()

    # --- Magnitudes ---
    acc_mag  = np.sqrt(ax**2 + ay**2 + az**2)
    rot_mag  = np.sqrt(rx**2 + ry**2 + rz**2)
    grav_mag = np.sqrt(gx**2 + gy**2 + gz**2)

    feats = {
        # keep for debugging; you can drop these when building X
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

        # # orientation (simple stats — good enough for a first pass)
        # "pitch_mean": float(pitch.mean()),
        # "roll_mean":  float(roll.mean()),
        # "yaw_mean":   float(yaw.mean()),

        # "pitch_std":  float(pitch.std()),
        # "roll_std":   float(roll.std()),
        # "yaw_std":    float(yaw.std()),

        # # quaternion components (averaged; model can learn patterns)
        # "qw_mean": float(qw.mean()),
        # "qx_mean": float(qx.mean()),
        # "qy_mean": float(qy.mean()),
        # "qz_mean": float(qz.mean()),
    }

    return feats


# ----------------------------
# Window Creation
# Input: Watch and Phone data frames, label (scroll or study), Window step size
# Output: List of  Features per window, Labels per window 
# ----------------------------
def windows_from_watch_and_phone(
    watch_df: pd.DataFrame,
    phone_df: pd.DataFrame,
    label: str,
    window_sec: float,
    step_sec: float,
):
    if watch_df.empty or phone_df.empty:
        return [], []

    times = watch_df["seconds_elapsed"].to_numpy()
    start_time = times[0]
    end_time = times[-1]

    feature_rows = []
    labels = []

    cur_start = start_time
    while cur_start + window_sec <= end_time:
        cur_end = cur_start + window_sec

        # Window from the watch
        mask_watch = (watch_df["seconds_elapsed"] >= cur_start) & (watch_df["seconds_elapsed"] <= cur_end)
        watch_win = watch_df.loc[mask_watch]

        # Window from the phone
        mask_phone = (phone_df["seconds_elapsed"] >= cur_start) & (phone_df["seconds_elapsed"] <= cur_end)
        phone_win = phone_df.loc[mask_phone]

        if not watch_win.empty and not phone_win.empty:
            watch_feats = extract_features_from_window(watch_win)
            phone_feats = extract_features_from_window(phone_win)

            if watch_feats and phone_feats:
                # Prefix keys so they don’t collide
                row = {}
                for k, v in watch_feats.items():
                    if k.startswith("t_"):
                        # Optional: keep a single t_start/t_end from watch
                        row[f"watch_{k}"] = v
                    else:
                        row[f"watch_{k}"] = v

                for k, v in phone_feats.items():
                    if not k.startswith("t_"):  # we already have times from the watch
                        row[f"phone_{k}"] = v

                feature_rows.append(row)
                labels.append(label)

        cur_start += step_sec

    return feature_rows, labels


#---------------------------
# Calls all the functions above
# Input: Paths
# Outputs: Features
#---------------------------
def build_windows(
    label: str,
    watch_path: Path,
    phone_accel: Path,
    phone_gyro: Path,
    phone_grav: Path,
    phone_orient: Path,
    window_sec: float,
    step_sec: float,
) -> Tuple[List[Dict], List[str]]:
    """
    Given 5 paths (1 watch, 4 phone CSVs) build sliding-window
    feature rows + labels for one condition (e.g. 'scrolling').
    """
    # load watch
    watch_df = load_watch_imu(watch_path)        # your existing loader

    # load + merge phone IMU
    phone_df = load_phone_imu(
        accel_path=phone_accel,
        gyro_path=phone_gyro,
        grav_path=phone_grav,
        orient_path=phone_orient,
    )

    # create windows with combined features
    feats, labels = windows_from_watch_and_phone(
        watch_df=watch_df,
        phone_df=phone_df,
        label=label,
        window_sec=window_sec,
        step_sec=step_sec,
    )

    return feats, labels




# ----------------------------
# Main training pipeline
# ----------------------------

def main():
    scroll_feats, scroll_labels = build_windows(
        label="scrolling",
        watch_path=SCROLL_WATCH,
        phone_accel=SCROLL_PHONE_ACCEL,
        phone_gyro=SCROLL_PHONE_GYRO,
        phone_grav=SCROLL_PHONE_GRAVITY,
        phone_orient=SCROLL_PHONE_ORIENT,
        window_sec=WINDOW_SEC,
        step_sec=STEP_SEC,
    )

    study_feats, study_labels = build_windows(
        label="studying",
        watch_path=STUDY_WATCH,
        phone_accel=STUDY_PHONE_ACCEL,
        phone_gyro=STUDY_PHONE_GYRO,
        phone_grav=STUDY_PHONE_GRAVITY,
        phone_orient=STUDY_PHONE_ORIENT,
        window_sec=WINDOW_SEC,
        step_sec=STEP_SEC,
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
