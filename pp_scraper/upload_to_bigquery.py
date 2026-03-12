import json
import os
from google.cloud import bigquery

# ===== CONFIGURATION =====

PROJECT_ID = os.getenv("GCP_PROJECT")
DATASET_ID = os.getenv("BQ_DATASET")
TABLE_ID  = os.getenv("BQ_LOUNGES_TABLE")
JSON_FILE = "selected_countries_lounges.json"      # existing JSON file


# Path to service account key (optional – if not set, uses default credentials)
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/key.json"

# ===== CONVERT TO NDJSON =====
ndjson_file = "temp_ndjson.json"
print("📄 Converting to newline-delimited JSON...")
with open(JSON_FILE, "r", encoding="utf-8") as infile:
    data = json.load(infile)          # expects a list of airport objects

with open(ndjson_file, "w", encoding="utf-8") as outfile:
    for record in data:
        outfile.write(json.dumps(record) + "\n")

print(f"✅ Created {ndjson_file} with {len(data)} records.")

# ===== BIGQUERY UPLOAD =====
client = bigquery.Client(project=PROJECT_ID)

# Create dataset if it doesn't exist
dataset_ref = client.dataset(DATASET_ID)
try:
    client.get_dataset(dataset_ref)
    print(f"ℹ️ Dataset {DATASET_ID} already exists.")
except Exception:
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"            # or "EU", etc.
    dataset = client.create_dataset(dataset)
    print(f"✅ Dataset {DATASET_ID} created.")

# Configure load job
job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    autodetect=True,                    # let BigQuery infer schema
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # overwrite table if exists
)

table_ref = dataset_ref.table(TABLE_ID)

print(f"⏳ Loading data into {PROJECT_ID}.{DATASET_ID}.{TABLE_ID} ...")
with open(ndjson_file, "rb") as source_file:
    load_job = client.load_table_from_file(
        source_file,
        table_ref,
        job_config=job_config,
    )

load_job.result()  # Wait for job completion

# Get table info
table = client.get_table(table_ref)
print(f"✅ Loaded {table.num_rows} rows into {table_ref.path}.")

# Clean up temporary file
os.remove(ndjson_file)
print("🧹 Temporary file cleaned up.")