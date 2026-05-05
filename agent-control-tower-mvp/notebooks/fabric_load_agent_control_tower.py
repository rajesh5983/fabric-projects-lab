# Fabric notebook-ready PySpark loader for the AI Agent Control Tower MVP.
#
# Attach this notebook to the target Fabric Lakehouse before running.
# Expected raw file location:
#   Files/agent_control_tower/raw/

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType, TimestampType


RAW_PATH = "Files/agent_control_tower/raw"


schemas = {
    "dim_agent": StructType(
        [
            StructField("agent_id", StringType(), False),
            StructField("agent_name", StringType(), False),
            StructField("business_domain", StringType(), False),
            StructField("owner_team", StringType(), False),
            StructField("active_flag", StringType(), False),
        ]
    ),
    "dim_model": StructType(
        [
            StructField("model_id", StringType(), False),
            StructField("model_name", StringType(), False),
            StructField("provider", StringType(), False),
            StructField("cost_per_1k_input_tokens_aud", DoubleType(), False),
            StructField("cost_per_1k_output_tokens_aud", DoubleType(), False),
        ]
    ),
    "fact_agent_run": StructType(
        [
            StructField("run_id", StringType(), False),
            StructField("timestamp", TimestampType(), False),
            StructField("agent_id", StringType(), False),
            StructField("agent_name", StringType(), False),
            StructField("business_domain", StringType(), False),
            StructField("model_used", StringType(), False),
            StructField("input_tokens", IntegerType(), False),
            StructField("output_tokens", IntegerType(), False),
            StructField("estimated_cost_aud", DoubleType(), False),
            StructField("latency_ms", IntegerType(), False),
            StructField("status", StringType(), False),
            StructField("risk_level", StringType(), False),
            StructField("groundedness_score", DoubleType(), False),
            StructField("user_feedback", StringType(), False),
            StructField("policy_breach_type", StringType(), True),
            StructField("tool_calls_count", IntegerType(), False),
            StructField("data_source_used", StringType(), False),
            StructField("environment", StringType(), False),
        ]
    ),
    "fact_policy_breach": StructType(
        [
            StructField("breach_id", StringType(), False),
            StructField("run_id", StringType(), False),
            StructField("timestamp", TimestampType(), False),
            StructField("agent_id", StringType(), False),
            StructField("policy_breach_type", StringType(), False),
            StructField("severity", StringType(), False),
            StructField("breach_description", StringType(), False),
            StructField("requires_review", StringType(), False),
            StructField("environment", StringType(), False),
        ]
    ),
    "fact_feedback": StructType(
        [
            StructField("feedback_id", StringType(), False),
            StructField("run_id", StringType(), False),
            StructField("timestamp", TimestampType(), False),
            StructField("agent_id", StringType(), False),
            StructField("user_feedback", StringType(), False),
            StructField("feedback_score", IntegerType(), False),
            StructField("feedback_comment", StringType(), False),
        ]
    ),
}


def read_csv_table(table_name):
    return (
        spark.read.format("csv")
        .option("header", "true")
        .option("mode", "FAILFAST")
        .schema(schemas[table_name])
        .load(f"{RAW_PATH}/{table_name}.csv")
    )


tables = {table_name: read_csv_table(table_name) for table_name in schemas}

tables["dim_agent"] = tables["dim_agent"].withColumn(
    "active_flag", F.col("active_flag").cast("boolean")
)
tables["fact_policy_breach"] = tables["fact_policy_breach"].withColumn(
    "requires_review", F.col("requires_review").cast("boolean")
)

for table_name, dataframe in tables.items():
    dataframe.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        table_name
    )

fact_agent_run = tables["fact_agent_run"].withColumn("run_date", F.to_date("timestamp"))
fact_policy_breach = tables["fact_policy_breach"].withColumn("breach_date", F.to_date("timestamp"))

agg_agent_daily = (
    fact_agent_run.groupBy("run_date", "agent_id", "agent_name", "business_domain", "environment")
    .agg(
        F.count("*").alias("run_count"),
        F.sum(F.when(F.col("status") == "success", 1).otherwise(0)).alias("success_count"),
        F.sum(F.when(F.col("status") != "success", 1).otherwise(0)).alias("failure_count"),
        F.avg("latency_ms").alias("avg_latency_ms"),
        F.avg("groundedness_score").alias("avg_groundedness_score"),
        F.sum("estimated_cost_aud").alias("total_cost_aud"),
        F.sum("input_tokens").alias("input_tokens"),
        F.sum("output_tokens").alias("output_tokens"),
    )
    .withColumn("success_rate", F.col("success_count") / F.col("run_count"))
)

agg_model_cost = (
    fact_agent_run.groupBy("model_used", "environment")
    .agg(
        F.count("*").alias("run_count"),
        F.sum("estimated_cost_aud").alias("total_cost_aud"),
        F.avg("estimated_cost_aud").alias("avg_cost_per_run_aud"),
        F.sum("input_tokens").alias("input_tokens"),
        F.sum("output_tokens").alias("output_tokens"),
    )
    .orderBy(F.desc("total_cost_aud"))
)

agg_policy_breach_daily = (
    fact_policy_breach.groupBy("breach_date", "agent_id", "policy_breach_type", "severity", "environment")
    .agg(
        F.count("*").alias("breach_count"),
        F.sum(F.when(F.col("requires_review"), 1).otherwise(0)).alias("review_required_count"),
    )
)

aggregate_tables = {
    "agg_agent_daily": agg_agent_daily,
    "agg_model_cost": agg_model_cost,
    "agg_policy_breach_daily": agg_policy_breach_daily,
}

for table_name, dataframe in aggregate_tables.items():
    dataframe.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        table_name
    )

row_counts = {table_name: dataframe.count() for table_name, dataframe in tables.items()}
aggregate_row_counts = {
    table_name: dataframe.count() for table_name, dataframe in aggregate_tables.items()
}
total_cost = fact_agent_run.agg(F.round(F.sum("estimated_cost_aud"), 4).alias("total_cost_aud")).collect()[
    0
]["total_cost_aud"]

print("Source table row counts:")
for table_name, count in row_counts.items():
    print(f"{table_name}: {count}")

print("Aggregate table row counts:")
for table_name, count in aggregate_row_counts.items():
    print(f"{table_name}: {count}")

print(f"Validated total estimated cost AUD: {total_cost}")

if row_counts["fact_agent_run"] != 2000:
    raise ValueError(f"Expected 2000 fact_agent_run rows, found {row_counts['fact_agent_run']}")

if total_cost is None or total_cost <= 0:
    raise ValueError("Total estimated cost validation failed.")
