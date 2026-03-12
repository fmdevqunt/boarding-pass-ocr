

import json
from datetime import datetime
from typing import List, Optional
from google.cloud import bigquery
from .config import settings
from .models import Lounge

bq = bigquery.Client()

def fetch_lounges_from_bq(airport_iata: str) -> List[Lounge]:
    """Fetch all lounges for a given airport from BigQuery (nested schema)."""
    sql = f"""
    SELECT
        airport_code,
        lounge.lounge_id,
        lounge.name,
        lounge.terminal,
        lounge.opening_hours,
        lounge.amenities,
        lounge.access_notes,
        lounge.conditions,
        lounge.image_url,
        lounge.detail_url
    FROM `{settings.gcp_project}.{settings.bq_dataset}.{settings.bq_lounges_table}`,
    UNNEST(lounges) AS lounge
    WHERE airport_code = @airport
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("airport", "STRING", airport_iata)]
    )
    rows = bq.query(sql, job_config=job_config).result()
    lounges = []
    for r in rows:
        lounges.append(Lounge(
            lounge_id=r.lounge_id,
            name=r.name,
            airport_code=r.airport_code,
            terminal=r.terminal,
            opening_hours=r.opening_hours,
            amenities=r.amenities or "",
            access_notes=r.access_notes,
            conditions=r.conditions or [],
            image_url=r.image_url,
            detail_url=r.detail_url
        ))
    return lounges


