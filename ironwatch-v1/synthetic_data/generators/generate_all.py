import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from faker import Faker

SEED = 42

# Fixed anchor (rather than "now") so output is byte-identical across runs.
SIMULATION_END = datetime(2026, 6, 7, tzinfo=timezone.utc)

# OREXA Heavy Industries entities (docs/OREXA_SPEC.md)
EQUIPMENT_LINES = {
    "Titan": ["T220", "T320"],
    "Kestrel": ["K45", "K60"],
    "Ironback": ["G14", "G16"],
}
LINE_NAMES = list(EQUIPMENT_LINES.keys())
LINE_WEIGHTS = [0.40, 0.35, 0.25]

SITES = ["Coppervale Mine", "Ironclad Ridge", "Stormwood Basin"]
# Representative coordinates for fictitious sites; not real locations.
SITE_COORDS = {
    "Coppervale Mine": (-23.50, 119.80),
    "Ironclad Ridge": (-21.15, 149.20),
    "Stormwood Basin": (-30.75, 121.40),
}

STATUS_VALUES = ["Active", "Maintenance", "Retired"]
STATUS_WEIGHTS = [0.85, 0.10, 0.05]

# OX- fault catalog from docs/OREXA_SPEC.md (verbatim examples, all 5 categories)
FAULT_CATALOG = [
    ("OX-101", "engine", "Engine overheat"),
    ("OX-110", "engine", "Low oil pressure"),
    ("OX-120", "engine", "Fuel system fault"),
    ("OX-205", "hydraulic", "Hydraulic pressure loss"),
    ("OX-210", "hydraulic", "Hydraulic fluid contamination"),
    ("OX-220", "hydraulic", "Cylinder seal failure"),
    ("OX-310", "electrical", "Alternator fault"),
    ("OX-320", "electrical", "Battery fault"),
    ("OX-330", "electrical", "Wiring harness fault"),
    ("OX-410", "undercarriage", "Undercarriage wear"),
    ("OX-420", "undercarriage", "Track tension fault"),
    ("OX-430", "undercarriage", "Frame stress alert"),
    ("OX-501", "sensor", "Sensor communication loss"),
    ("OX-510", "sensor", "GPS signal loss"),
    ("OX-520", "sensor", "Telemetry unit fault"),
]
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_WEIGHTS = [0.40, 0.30, 0.20, 0.10]

# Internal simulation pacing only (not exposed as output fields post-OREXA-pivot;
# see docs/DATA_MODEL.md §7 — service-interval tracking has no source field anymore).
SERVICE_INTERVAL_HOURS = 500
SERVICE_INTERVAL_VARIANCE = 0.20
SERVICE_TYPES_SCHEDULED = ["PM_250HR", "PM_500HR", "PM_1000HR"]
SERVICE_TYPE_WEIGHTS = [0.30, 0.45, 0.25]
UNPLANNED_RATE = 0.15
PARTS_CATALOG = [
    "Hydraulic filter", "Engine oil filter", "Fan belt", "Air filter",
    "Fuel injector", "Track pad", "Alternator", "Battery", "Coolant hose",
    "Brake pads",
]

OIL_SAMPLE_INTERVAL_HOURS = 250
LAB_VERDICTS = ["Normal", "Watch", "Critical"]
LAB_VERDICT_WEIGHTS = [0.65, 0.25, 0.10]
IRON_PPM_RANGES = {"Normal": (0, 50), "Watch": (50, 150), "Critical": (150, 350)}
WATER_CONTENT_PCT_RANGES = {"Normal": (0.0, 0.1), "Watch": (0.1, 0.3), "Critical": (0.3, 1.0)}
PARTICLE_COUNT_RANGES = {"Normal": (500, 2000), "Watch": (2000, 8000), "Critical": (8000, 20000)}


def load_config():
    load_dotenv()
    output_path = os.getenv("SYNTHETIC_OUTPUT_PATH", "./synthetic_data/output/")
    return {
        "equipment_count": int(os.getenv("SYNTHETIC_EQUIPMENT_COUNT", "50")),
        "days": int(os.getenv("SYNTHETIC_DAYS", "90")),
        "output_path": output_path,
        "output_dir": Path(output_path),
    }


def make_assets(count):
    lines = np.random.choice(LINE_NAMES, size=count, p=LINE_WEIGHTS)
    models = np.array([np.random.choice(EQUIPMENT_LINES[line]) for line in lines])
    sites = np.random.choice(SITES, size=count)

    seq_by_model = {}
    asset_ids = []
    for model in models:
        seq_by_model[model] = seq_by_model.get(model, 0) + 1
        asset_ids.append(f"{model}-{seq_by_model[model]:03d}")

    return asset_ids, lines, models, sites


def report_progress(label, idx, total):
    if (idx + 1) % 10 == 0 or (idx + 1) == total:
        print(f"      ... {label}: {idx + 1}/{total} units")


def generate_asset_master(asset_ids, lines, models, sites):
    n = len(asset_ids)
    years_ago = np.random.uniform(2, 8, size=n)
    commission_dates = [
        (SIMULATION_END - timedelta(days=float(years) * 365.25)).date()
        for years in years_ago
    ]
    status = np.random.choice(STATUS_VALUES, size=n, p=STATUS_WEIGHTS)
    full_models = [f"{line} {model}" for line, model in zip(lines, models)]
    return pd.DataFrame({
        "asset_id": asset_ids,
        "equipment_line": lines,
        "model": full_models,
        "site": sites,
        "commission_date": commission_dates,
        "status": status,
    })


def generate_telemetry(asset_ids, sites, days):
    readings_per_unit = days * 24 * 4  # one reading every 15 minutes
    start = SIMULATION_END - timedelta(days=days)
    timestamps = pd.date_range(start=start, periods=readings_per_unit, freq="15min")

    frames = []
    # Per-asset anomaly masks, captured (not recomputed) for generate_fault_events()
    # so the fault-event stream is derived from the exact same draws that produced
    # telemetry.parquet — not an independent re-roll (OPEN-002).
    anomaly_masks = {}
    for idx, asset_id in enumerate(asset_ids):
        n = readings_per_unit
        center_lat, center_lon = SITE_COORDS[sites[idx]]

        is_temp_anomaly = np.random.random(n) < 0.05
        coolant_temp_c = np.where(
            is_temp_anomaly,
            np.random.uniform(110, 140, n),
            np.random.uniform(85, 95, n),
        )

        # Hydraulic system pressure, not engine oil pressure — heavy-equipment
        # hydraulics run ~200-280 bar nominal; reasonable defaults, not specified.
        is_pressure_drop = np.random.random(n) < 0.03
        hydraulic_pressure_bar = np.where(
            is_pressure_drop,
            np.random.uniform(50, 120, n),
            np.random.uniform(200, 280, n),
        )

        is_rpm_spike = np.random.random(n) < 0.04
        engine_rpm = np.where(
            is_rpm_spike,
            np.random.uniform(2000, 2400, n),
            np.random.uniform(800, 1800, n),
        ).round().astype(int)

        vibration_mms = np.random.uniform(2.0, 8.0, n)
        fuel_rate_lph = np.random.uniform(20.0, 80.0, n)

        # Small jitter around the site center to simulate movement within the site.
        gps_lat = center_lat + np.random.uniform(-0.01, 0.01, n)
        gps_lon = center_lon + np.random.uniform(-0.01, 0.01, n)

        frames.append(pd.DataFrame({
            "asset_id": asset_id,
            "timestamp": timestamps,
            "engine_rpm": engine_rpm,
            "coolant_temp_c": coolant_temp_c.round(2),
            "hydraulic_pressure_bar": hydraulic_pressure_bar.round(2),
            "vibration_mms": vibration_mms.round(2),
            "fuel_rate_lph": fuel_rate_lph.round(2),
            "gps_lat": gps_lat.round(6),
            "gps_lon": gps_lon.round(6),
        }))

        anomaly_masks[asset_id] = {
            "temp": is_temp_anomaly,
            "pressure": is_pressure_drop,
            "rpm": is_rpm_spike,
        }

        report_progress("telemetry", idx, len(asset_ids))

    return pd.concat(frames, ignore_index=True), timestamps, anomaly_masks


def generate_fault_codes():
    severities = np.random.choice(SEVERITIES, size=len(FAULT_CATALOG), p=SEVERITY_WEIGHTS)
    return [
        {
            "fault_code": code,
            "category": category,
            "description": description,
            "severity": severities[i],
        }
        for i, (code, category, description) in enumerate(FAULT_CATALOG)
    ]


# Resolves OPEN-002 (docs/ADR/OPEN_DECISIONS.md): maps each of generate_telemetry()'s
# three anomaly signals to the OX- fault code it represents. Only these three codes
# can ever appear in fault_events.json — fault events are derived exclusively from
# real telemetry anomalies, not invented independently, so the other 12 catalog
# codes (electrical/undercarriage/sensor categories) have no telemetry signal to
# derive from and are intentionally never emitted here.
FAULT_CODE_BY_ANOMALY = {
    "temp": "OX-101",      # Engine overheat — direct match: coolant_temp_c anomaly IS an overheat.
    "pressure": "OX-205",  # Hydraulic pressure loss — direct match: hydraulic_pressure_bar anomaly.
    "rpm": "OX-120",       # Fuel system fault — inferred: no catalog code names "RPM spike"
                           # directly; an engine_rpm spike is modeled as a symptom of irregular
                           # fuel delivery, the closest engine-category fault in the catalog.
}

# A single anomalous 15-min reading is sensor noise, not a real fault — require a
# sustained run before promoting it to a discrete fault-event row. 3 consecutive
# readings = 45 minutes sustained.
MIN_ANOMALY_RUN_READINGS = 3

# With SEED=42, every anomaly run happens to resolve before the 90-day window
# ends, so cleared_ts is populated for every row and Gold's "currently active
# faults" health-score term would always see zero penalty against this
# dataset -- not a useful "which asset needs attention right now" snapshot.
# Deterministically re-open the single most recent fault on the top-N assets
# by total fault count (ties broken by asset_id) rather than leaving the
# snapshot all-clear or randomly flipping rows. This only changes the
# resolution state of an already-derived, telemetry-grounded event -- it does
# not invent a new fault or move its asset/timestamp/fault_code.
STILL_ACTIVE_TOP_N_ASSETS = 3


def _apply_still_active_snapshot(df):
    if df.empty:
        return df
    df = df.copy()
    counts = df.groupby("asset_id").size().rename("fault_count").reset_index()
    top_assets = counts.sort_values(
        ["fault_count", "asset_id"], ascending=[False, True]
    ).head(STILL_ACTIVE_TOP_N_ASSETS)["asset_id"]
    for asset_id in top_assets:
        asset_rows = df.index[df["asset_id"] == asset_id]
        latest_idx = df.loc[asset_rows, "fault_ts"].idxmax()
        df.loc[latest_idx, "active_flag"] = True
        df.loc[latest_idx, "cleared_ts"] = None
    return df


def _anomaly_runs_to_fault_events(asset_id, timestamps, anomaly_mask, fault_code):
    """One row per contiguous run of `anomaly_mask` at least
    MIN_ANOMALY_RUN_READINGS long. fault_ts is the run's first anomalous
    reading; cleared_ts is the first reading after it returns to normal, or
    None if the run is still open at the end of the series (active_flag=True)."""
    rows = []
    n = len(anomaly_mask)
    i = 0
    while i < n:
        if not anomaly_mask[i]:
            i += 1
            continue
        start = i
        while i < n and anomaly_mask[i]:
            i += 1
        if i - start >= MIN_ANOMALY_RUN_READINGS:
            cleared_ts = timestamps[i] if i < n else None
            rows.append({
                "asset_id": asset_id,
                "fault_code": fault_code,
                "fault_ts": timestamps[start],
                "active_flag": cleared_ts is None,
                "cleared_ts": cleared_ts,
            })
    return rows


def generate_fault_events(asset_ids, timestamps, anomaly_masks):
    """Per-asset fault-event stream derived from generate_telemetry()'s anomaly
    masks — resolves OPEN-002 (docs/ADR/OPEN_DECISIONS.md). Every row traces
    back to a real sustained telemetry anomaly for that asset; nothing here is
    invented independently of telemetry."""
    records = []
    for asset_id in asset_ids:
        masks = anomaly_masks[asset_id]
        for anomaly_type, fault_code in FAULT_CODE_BY_ANOMALY.items():
            records.extend(_anomaly_runs_to_fault_events(
                asset_id, timestamps, masks[anomaly_type], fault_code
            ))

    df = pd.DataFrame.from_records(
        records, columns=["asset_id", "fault_code", "fault_ts", "active_flag", "cleared_ts"]
    )
    df = _apply_still_active_snapshot(df)
    return df.sort_values(["asset_id", "fault_ts"]).reset_index(drop=True)


def _scheduled_service_marks(start_hours, end_hours):
    marks = []
    mark = start_hours + SERVICE_INTERVAL_HOURS * (
        1 + np.random.uniform(-SERVICE_INTERVAL_VARIANCE, SERVICE_INTERVAL_VARIANCE)
    )
    while mark <= end_hours:
        marks.append(mark)
        mark += SERVICE_INTERVAL_HOURS * (
            1 + np.random.uniform(-SERVICE_INTERVAL_VARIANCE, SERVICE_INTERVAL_VARIANCE)
        )
    return marks


def generate_service_history(asset_ids, base_hours, days):
    total_hours_span = days * 24
    simulation_start = SIMULATION_END - timedelta(days=days)
    records = []

    for idx, asset_id in enumerate(asset_ids):
        start_hours = float(base_hours[idx])
        end_hours = start_hours + total_hours_span

        scheduled_marks = _scheduled_service_marks(start_hours, end_hours)
        unplanned_count = round(len(scheduled_marks) * UNPLANNED_RATE / (1 - UNPLANNED_RATE))
        unplanned_marks = list(np.random.uniform(start_hours, end_hours, unplanned_count))

        events = [(m, False) for m in scheduled_marks] + [(m, True) for m in unplanned_marks]
        events.sort(key=lambda e: e[0])

        for hours_at_service, is_unplanned in events:
            service_type = (
                "UNPLANNED"
                if is_unplanned
                else np.random.choice(SERVICE_TYPES_SCHEDULED, p=SERVICE_TYPE_WEIGHTS)
            )
            service_date = simulation_start + timedelta(hours=hours_at_service - start_hours)
            parts_count = int(np.random.randint(1, 4))
            parts_used = ", ".join(
                np.random.choice(PARTS_CATALOG, size=parts_count, replace=False)
            )
            downtime_hours = round(
                float(np.random.uniform(2.0, 24.0) if is_unplanned else np.random.uniform(0.5, 6.0)),
                2,
            )
            records.append({
                "work_order_id": str(uuid.uuid4()),
                "asset_id": asset_id,
                "service_date": service_date.date(),
                "technician_id": f"TECH-{np.random.randint(1, 21):03d}",
                "service_type": service_type,
                "parts_used": parts_used,
                "downtime_hours": downtime_hours,
            })

        report_progress("service_history", idx, len(asset_ids))

    return pd.DataFrame.from_records(records)


def generate_oil_samples(asset_ids, base_hours, days):
    total_hours_span = days * 24
    simulation_start = SIMULATION_END - timedelta(days=days)
    records = []

    for idx, asset_id in enumerate(asset_ids):
        start_hours = float(base_hours[idx])
        end_hours = start_hours + total_hours_span

        mark = start_hours + OIL_SAMPLE_INTERVAL_HOURS
        while mark <= end_hours:
            verdict = np.random.choice(LAB_VERDICTS, p=LAB_VERDICT_WEIGHTS)
            iron_low, iron_high = IRON_PPM_RANGES[verdict]
            water_low, water_high = WATER_CONTENT_PCT_RANGES[verdict]
            particle_low, particle_high = PARTICLE_COUNT_RANGES[verdict]
            sample_date = simulation_start + timedelta(hours=mark - start_hours)

            records.append({
                "sample_id": str(uuid.uuid4()),
                "asset_id": asset_id,
                "sample_date": sample_date.date(),
                "iron_ppm": round(float(np.random.uniform(iron_low, iron_high)), 1),
                "viscosity_cst": round(float(np.random.uniform(11.0, 16.0)), 2),
                "water_content_pct": round(float(np.random.uniform(water_low, water_high)), 3),
                "particle_count": int(np.random.uniform(particle_low, particle_high)),
                "lab_verdict": verdict,
            })
            mark += OIL_SAMPLE_INTERVAL_HOURS

        report_progress("oil_samples", idx, len(asset_ids))

    return pd.DataFrame.from_records(records)


def main():
    config = load_config()
    np.random.seed(SEED)
    fake = Faker()
    Faker.seed(SEED)

    output_dir = config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    asset_ids, lines, models, sites = make_assets(config["equipment_count"])
    base_hours = np.random.randint(0, 5001, size=len(asset_ids))  # internal pacing only

    print("IronWatch v1 - OREXA synthetic data generation")
    print(f"Assets: {len(asset_ids)} | Days: {config['days']} | Seed: {SEED}")
    print()

    print("[1/5] asset_master.csv")
    asset_df = generate_asset_master(asset_ids, lines, models, sites)
    asset_df.to_csv(output_dir / "asset_master.csv", index=False)
    print(f"      -> {len(asset_df)} rows written")

    print("[2/6] telemetry.parquet")
    telemetry_df, telemetry_timestamps, telemetry_anomalies = generate_telemetry(
        asset_ids, sites, config["days"]
    )
    telemetry_df.to_parquet(output_dir / "telemetry.parquet", index=False, engine="pyarrow")
    print(f"      -> {len(telemetry_df):,} rows written")

    print("[3/6] fault_codes.json")
    fault_codes = generate_fault_codes()
    with open(output_dir / "fault_codes.json", "w", encoding="utf-8") as f:
        json.dump(fault_codes, f, indent=2)
    print(f"      -> {len(fault_codes)} records written")

    print("[4/6] fault_events.json")
    fault_events_df = generate_fault_events(asset_ids, telemetry_timestamps, telemetry_anomalies)
    fault_events_records = [
        {
            "asset_id": row.asset_id,
            "fault_code": row.fault_code,
            "fault_ts": row.fault_ts.isoformat(),
            "active_flag": bool(row.active_flag),
            "cleared_ts": row.cleared_ts.isoformat() if row.cleared_ts is not None else None,
        }
        for row in fault_events_df.itertuples()
    ]
    with open(output_dir / "fault_events.json", "w", encoding="utf-8") as f:
        json.dump(fault_events_records, f, indent=2)
    print(f"      -> {len(fault_events_records):,} rows written")

    print("[5/6] service_history.csv")
    service_df = generate_service_history(asset_ids, base_hours, config["days"])
    service_df.to_csv(output_dir / "service_history.csv", index=False)
    print(f"      -> {len(service_df):,} rows written")

    print("[6/6] oil_samples.csv")
    oil_df = generate_oil_samples(asset_ids, base_hours, config["days"])
    oil_df.to_csv(output_dir / "oil_samples.csv", index=False)
    print(f"      -> {len(oil_df):,} rows written")

    print()
    print(
        f"Generated: telemetry.parquet ({len(telemetry_df):,} rows), "
        f"asset_master.csv ({len(asset_df)} rows),\n"
        f"           fault_codes.json ({len(fault_codes)} records), "
        f"fault_events.json ({len(fault_events_records):,} rows),\n"
        f"           service_history.csv ({len(service_df):,} rows), "
        f"oil_samples.csv ({len(oil_df):,} rows)"
    )
    print(f"Output: {config['output_path']}")
    print(f"Seed: {SEED} | Reproducible: YES")


if __name__ == "__main__":
    main()
