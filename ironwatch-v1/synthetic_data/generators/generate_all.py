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

MODELS = ["789D", "D11", "6060 Dozer", "16M Grader"]
MODEL_WEIGHTS = [0.30, 0.25, 0.25, 0.20]
SITES = ["Mackay", "Rockhampton", "Townsville"]

FAULT_CATEGORIES = ["engine", "hydraulics", "transmission", "electrical", "structural"]
FAULT_CODES_PER_CATEGORY = 5
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_WEIGHTS = [0.40, 0.30, 0.20, 0.10]

SERVICE_INTERVAL_HOURS = 500
SERVICE_INTERVAL_VARIANCE = 0.20
SERVICE_TYPES_SCHEDULED = ["PM_250HR", "PM_500HR", "PM_1000HR"]
SERVICE_TYPE_WEIGHTS = [0.30, 0.45, 0.25]
UNPLANNED_RATE = 0.15

OIL_COMPARTMENTS = ["engine", "transmission", "hydraulics"]
OIL_SAMPLE_INTERVAL_HOURS = 250
OIL_VERDICTS = ["NORMAL", "MONITOR", "CAUTION", "CRITICAL"]
OIL_VERDICT_WEIGHTS = [0.60, 0.20, 0.15, 0.05]
IRON_PPM_RANGES = {
    "NORMAL": (0, 50),
    "MONITOR": (50, 100),
    "CAUTION": (100, 200),
    "CRITICAL": (200, 350),
}


def load_config():
    load_dotenv()
    output_path = os.getenv("SYNTHETIC_OUTPUT_PATH", "./synthetic_data/output/")
    return {
        "equipment_count": int(os.getenv("SYNTHETIC_EQUIPMENT_COUNT", "50")),
        "days": int(os.getenv("SYNTHETIC_DAYS", "90")),
        "output_path": output_path,
        "output_dir": Path(output_path),
    }


def make_equipment_ids(count):
    return [f"EQ-{i:03d}" for i in range(1, count + 1)]


def report_progress(label, idx, total):
    if (idx + 1) % 10 == 0 or (idx + 1) == total:
        print(f"      ... {label}: {idx + 1}/{total} units")


def generate_asset_master(equipment_ids):
    n = len(equipment_ids)
    models = np.random.choice(MODELS, size=n, p=MODEL_WEIGHTS)
    sites = np.random.choice(SITES, size=n)
    years_ago = np.random.uniform(2, 8, size=n)
    commissioned_dates = [
        (SIMULATION_END - timedelta(days=float(years) * 365.25)).date()
        for years in years_ago
    ]
    return pd.DataFrame({
        "equipment_id": equipment_ids,
        "model": models,
        "site": sites,
        "commissioned_date": commissioned_dates,
    })


def generate_telemetry(equipment_ids, base_hours, days):
    readings_per_unit = days * 24 * 4  # one reading every 15 minutes
    start = SIMULATION_END - timedelta(days=days)
    timestamps = pd.date_range(start=start, periods=readings_per_unit, freq="15min")
    hours_increment = np.arange(readings_per_unit) * 0.25  # 15 min == 0.25 operating hr

    frames = []
    for idx, equipment_id in enumerate(equipment_ids):
        n = readings_per_unit

        is_temp_anomaly = np.random.random(n) < 0.05
        engine_temp_c = np.where(
            is_temp_anomaly,
            np.random.uniform(110, 140, n),
            np.random.uniform(85, 95, n),
        )

        is_pressure_drop = np.random.random(n) < 0.03
        oil_pressure_psi = np.where(
            is_pressure_drop,
            np.random.uniform(15, 30, n),
            np.random.uniform(40, 60, n),
        )

        # Ranges not specified in requirements; reasonable defaults for heavy equipment.
        vibration_mms = np.random.uniform(2.0, 8.0, n)
        fuel_rate_lph = np.random.uniform(20.0, 80.0, n)

        frames.append(pd.DataFrame({
            "equipment_id": equipment_id,
            "timestamp": timestamps,
            "engine_temp_c": engine_temp_c.round(2),
            "oil_pressure_psi": oil_pressure_psi.round(2),
            "vibration_mms": vibration_mms.round(2),
            "fuel_rate_lph": fuel_rate_lph.round(2),
            "hours_operated": (base_hours[idx] + hours_increment).round(2),
        }))

        report_progress("telemetry", idx, len(equipment_ids))

    return pd.concat(frames, ignore_index=True)


def generate_fault_codes(fake):
    severities = np.random.choice(
        SEVERITIES, size=len(FAULT_CATEGORIES) * FAULT_CODES_PER_CATEGORY, p=SEVERITY_WEIGHTS
    )
    codes = []
    seq = 0
    for category in FAULT_CATEGORIES:
        prefix = category[:3].upper()
        for _ in range(FAULT_CODES_PER_CATEGORY):
            seq += 1
            codes.append({
                "fault_code": f"{prefix}-{seq:03d}",
                "category": category,
                "description": fake.sentence(nb_words=8).rstrip("."),
                "severity": severities[seq - 1],
            })
    return codes


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


def generate_service_history(equipment_ids, base_hours, days, fake):
    total_hours_span = days * 24
    simulation_start = SIMULATION_END - timedelta(days=days)
    records = []

    for idx, equipment_id in enumerate(equipment_ids):
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
            records.append({
                "work_order_id": str(uuid.uuid4()),
                "equipment_id": equipment_id,
                "service_date": service_date.date(),
                "service_type": service_type,
                "hours_at_service": round(hours_at_service, 2),
                "technician_id": f"TECH-{np.random.randint(1, 21):03d}",
                "notes": fake.sentence(nb_words=6).rstrip("."),
            })

        report_progress("service_history", idx, len(equipment_ids))

    return pd.DataFrame.from_records(records)


def generate_oil_samples(equipment_ids, base_hours, days):
    total_hours_span = days * 24
    simulation_start = SIMULATION_END - timedelta(days=days)
    records = []

    for idx, equipment_id in enumerate(equipment_ids):
        start_hours = float(base_hours[idx])
        end_hours = start_hours + total_hours_span

        for compartment in OIL_COMPARTMENTS:
            mark = start_hours + OIL_SAMPLE_INTERVAL_HOURS
            while mark <= end_hours:
                verdict = np.random.choice(OIL_VERDICTS, p=OIL_VERDICT_WEIGHTS)
                low, high = IRON_PPM_RANGES[verdict]
                sample_date = simulation_start + timedelta(hours=mark - start_hours)

                records.append({
                    "sample_id": str(uuid.uuid4()),
                    "equipment_id": equipment_id,
                    "compartment": compartment,
                    "sample_date": sample_date.date(),
                    "hours_operated": round(mark, 2),
                    "iron_ppm": round(float(np.random.uniform(low, high)), 1),
                    "verdict": verdict,
                })
                mark += OIL_SAMPLE_INTERVAL_HOURS

        report_progress("oil_samples", idx, len(equipment_ids))

    return pd.DataFrame.from_records(records)


def main():
    config = load_config()
    np.random.seed(SEED)
    fake = Faker()
    Faker.seed(SEED)

    output_dir = config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    equipment_ids = make_equipment_ids(config["equipment_count"])
    base_hours = np.random.randint(0, 5001, size=len(equipment_ids))

    print("IronWatch v1 - synthetic data generation")
    print(f"Equipment units: {len(equipment_ids)} | Days: {config['days']} | Seed: {SEED}")
    print()

    print("[1/5] asset_master.csv")
    asset_df = generate_asset_master(equipment_ids)
    asset_df.to_csv(output_dir / "asset_master.csv", index=False)
    print(f"      -> {len(asset_df)} rows written")

    print("[2/5] telemetry.parquet")
    telemetry_df = generate_telemetry(equipment_ids, base_hours, config["days"])
    telemetry_df.to_parquet(output_dir / "telemetry.parquet", index=False, engine="pyarrow")
    print(f"      -> {len(telemetry_df):,} rows written")

    print("[3/5] fault_codes.json")
    fault_codes = generate_fault_codes(fake)
    with open(output_dir / "fault_codes.json", "w", encoding="utf-8") as f:
        json.dump(fault_codes, f, indent=2)
    print(f"      -> {len(fault_codes)} records written")

    print("[4/5] service_history.csv")
    service_df = generate_service_history(equipment_ids, base_hours, config["days"], fake)
    service_df.to_csv(output_dir / "service_history.csv", index=False)
    print(f"      -> {len(service_df):,} rows written")

    print("[5/5] oil_samples.csv")
    oil_df = generate_oil_samples(equipment_ids, base_hours, config["days"])
    oil_df.to_csv(output_dir / "oil_samples.csv", index=False)
    print(f"      -> {len(oil_df):,} rows written")

    print()
    print(
        f"Generated: telemetry.parquet ({len(telemetry_df):,} rows), "
        f"asset_master.csv ({len(asset_df)} rows),\n"
        f"           fault_codes.json ({len(fault_codes)} records), "
        f"service_history.csv ({len(service_df):,} rows),\n"
        f"           oil_samples.csv ({len(oil_df):,} rows)"
    )
    print(f"Output: {config['output_path']}")
    print(f"Seed: {SEED} | Reproducible: YES")


if __name__ == "__main__":
    main()
