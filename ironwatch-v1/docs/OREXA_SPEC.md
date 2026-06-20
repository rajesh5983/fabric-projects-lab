# OREXA Heavy Industries — Synthetic Data Spec

## Company
OREXA Heavy Industries — fictitious heavy equipment OEM/fleet operator.
Entirely fictitious entity names; no real manufacturer model numbers used.

## Equipment lines
- Titan — haul trucks. Models: Titan T220, Titan T320
- Kestrel — excavators. Models: Kestrel K45, Kestrel K60
- Ironback — graders. Models: Ironback G14, Ironback G16

## Sites
Three fictitious mine sites (no real Australian town names, to keep clear
separation from any real dealer territory):
- Coppervale Mine
- Ironclad Ridge
- Stormwood Basin

## Subsystems and file mapping

### PulseNet (telemetry) → telemetry.parquet
Fields: asset_id, timestamp, engine_rpm, coolant_temp_c, hydraulic_pressure_bar,
vibration_mms, fuel_rate_lph, gps_lat, gps_lon
All units metric.

### FluidLab (oil condition monitoring) → oil_samples.csv
Fields: sample_id, asset_id, sample_date, iron_ppm, viscosity_cst,
water_content_pct, particle_count, lab_verdict (Normal/Watch/Critical)

### FleetCare (maintenance history) → service_history.csv
Fields: work_order_id, asset_id, service_date, technician_id, service_type,
parts_used, downtime_hours

### Asset registry → asset_master.csv
Fields: asset_id, equipment_line (Titan/Kestrel/Ironback), model, site,
commission_date, status (Active/Maintenance/Retired)

### Fault codes → fault_codes.json
OX- prefix, numbered by category:
- OX-1xx: Engine (e.g. OX-101 Engine overheat, OX-110 Low oil pressure,
  OX-120 Fuel system fault)
- OX-2xx: Hydraulic (e.g. OX-205 Hydraulic pressure loss, OX-210 Hydraulic
  fluid contamination, OX-220 Cylinder seal failure)
- OX-3xx: Electrical (e.g. OX-310 Alternator fault, OX-320 Battery fault,
  OX-330 Wiring harness fault)
- OX-4xx: Undercarriage / structural (e.g. OX-410 Undercarriage wear,
  OX-420 Track tension fault, OX-430 Frame stress alert)
- OX-5xx: Sensor / telemetry (e.g. OX-501 Sensor communication loss,
  OX-510 GPS signal loss, OX-520 Telemetry unit fault)

Generator should produce a representative spread across all five categories,
not just one or two.
