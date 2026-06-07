# IronWatch v1 — Data Model Reference

## Bronze Layer (`ironwatch-bronze` Lakehouse)

### `raw_telemetry`
One row per sensor reading, exactly as received. Append-only.

| Column | Type | Notes |
|---|---|---|
| `event_id` | STRING | UUID assigned by generator |
| `machine_id` | STRING | e.g. `CAT-EX-001` |
| `event_ts` | TIMESTAMP | UTC, millisecond precision |
| `event_date` | DATE | Partition key |
| `sensor` | STRING | Sensor channel name |
| `value` | DOUBLE | Raw sensor reading |
| `unit` | STRING | e.g. `degC`, `bar`, `%` |
| `_ingested_utc` | TIMESTAMP | Lakehouse write time |
| `_source_file` | STRING | ADLS path of source file |

### `raw_fault_code`
| Column | Type | Notes |
|---|---|---|
| `fault_id` | STRING | UUID |
| `machine_id` | STRING | |
| `fault_ts` | TIMESTAMP | UTC |
| `fault_date` | DATE | Partition key |
| `fault_code` | STRING | e.g. `E0420` |
| `severity` | STRING | LOW / MEDIUM / HIGH / CRITICAL |
| `raw_payload` | STRING | Full JSON as received |
| `_ingested_utc` | TIMESTAMP | |

---

## Silver Layer (`ironwatch-silver` Lakehouse)

### `machine_telemetry`
1-minute averages per machine per sensor. Deduplicated on `(machine_id, sensor, minute_ts)`.

| Column | Type | Notes |
|---|---|---|
| `machine_id` | STRING | |
| `minute_ts` | TIMESTAMP | Truncated to minute |
| `telemetry_date` | DATE | Partition key |
| `engine_temp` | DOUBLE | °C |
| `hydraulic_pressure` | DOUBLE | bar |
| `fuel_level` | DOUBLE | % |
| `vibration_rms` | DOUBLE | Derived: sqrt(x²+y²+z²) |
| `oil_pressure` | DOUBLE | bar |
| `coolant_temp` | DOUBLE | °C |
| `load_percent` | DOUBLE | % |
| `rpm` | DOUBLE | |
| `hours_operated` | DOUBLE | Cumulative |
| `_loaded_utc` | TIMESTAMP | Watermark |

### `machine_fault`
| Column | Type | Notes |
|---|---|---|
| `fault_id` | STRING | From Bronze |
| `machine_id` | STRING | |
| `fault_ts` | TIMESTAMP | |
| `fault_date` | DATE | Partition key |
| `fault_code` | STRING | |
| `fault_category` | STRING | Enriched from lookup |
| `severity` | STRING | |
| `resolved_ts` | TIMESTAMP | NULL if open |
| `_loaded_utc` | TIMESTAMP | Watermark |

---

## Gold Layer (`ironwatch-gold` Warehouse)

### `fact_equipment_health`
Hourly health score per machine. Primary analytics table.

| Column | Type | Notes |
|---|---|---|
| `health_key` | BIGINT IDENTITY | Surrogate key |
| `machine_key` | INT | FK → `dim_machine` |
| `date_key` | INT | FK → `dim_date` (YYYYMMDD) |
| `hour_ts` | DATETIME2 | Hour start UTC |
| `health_score` | DECIMAL(5,2) | 0–100 |
| `health_band` | VARCHAR(10) | Healthy/Watch/Warning/Critical |
| `avg_engine_temp` | DECIMAL(6,2) | |
| `avg_vibration_rms` | DECIMAL(6,4) | |
| `fault_count_7d` | INT | Rolling 7-day window |
| `hours_since_service` | DECIMAL(8,2) | |
| `_loaded_utc` | DATETIME2 | Watermark |

### `dim_machine`
| Column | Type | Notes |
|---|---|---|
| `machine_key` | INT IDENTITY | Surrogate key |
| `machine_id` | VARCHAR(20) | Natural key |
| `machine_type` | VARCHAR(50) | Excavator / Haul Truck / Bulldozer |
| `model` | VARCHAR(50) | e.g. CAT 390F |
| `manufacture_year` | SMALLINT | |
| `site_code` | VARCHAR(10) | Operating site |
| `region` | VARCHAR(50) | |
| `service_interval_hours` | INT | Scheduled maintenance interval |
| `_valid_from` | DATE | SCD Type 2 |
| `_valid_to` | DATE | NULL = current |

### `dim_date`
Standard date dimension: date_key (YYYYMMDD), full_date, year, quarter, month, week, day_of_week, is_weekend.

### `dim_fault_type`
| Column | Type |
|---|---|
| `fault_code` | VARCHAR(10) |
| `fault_description` | VARCHAR(200) |
| `fault_category` | VARCHAR(50) |
| `default_severity` | VARCHAR(10) |
