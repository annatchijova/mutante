# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
bigquery_sink.py — Graceful degradation telemetry sink for analytical persistence.
"""

import os
import json
import logging
from typing import Any
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MUTANTE.BigQuerySink")

class BigQuerySink:
    """
    Handles async insertion of forensic audits into BigQuery with partitioned tables.
    """
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.dataset_id = os.getenv("BIGQUERY_DATASET", "mutante_analytics")
        self.table_id = os.getenv("BIGQUERY_TABLE", "mutante_audits")
        self.client = bigquery.Client(project=self.project_id)
        
        self.table_ref = bigquery.TableReference(
            bigquery.DatasetReference(self.project_id, self.dataset_id),
            self.table_id
        )
        self._ensure_infrastructure()

    def _ensure_infrastructure(self) -> None:
        schema = [
            bigquery.SchemaField("prompt_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("mutation_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("jcs", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("final_verdict", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("indicators", "STRING", mode="REPEATED"),
            bigquery.SchemaField("raw_response", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("jcs_breakdown", "JSON", mode="REQUIRED")
        ]
        try:
            self.client.get_table(self.table_ref)
        except Exception:
            table = bigquery.Table(self.table_ref, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(type_="DAY", field="timestamp")
            self.client.create_table(table)

    def stream_verdict(self, verdict: Any) -> bool:
        """
        Streams a BypassVerdict DTO to BigQuery.
        """
        try:
            row_data = {
                "prompt_id": str(verdict.prompt_id),
                "mutation_type": str(verdict.mutation_type),
                "jcs": float(verdict.jcs),
                "final_verdict": str(verdict.final_verdict),
                "indicators": list(verdict.indicators),
                "raw_response": str(verdict.raw_response),
                "timestamp": verdict.timestamp,
                "model_version": str(verdict.model_version),
                "jcs_breakdown": json.dumps(verdict.jcs_breakdown)
            }
            errors = self.client.insert_rows_json(self.table_ref, [row_data])
            if errors:
                logger.error(f"BigQuery insertion errors: {errors}")
            return not errors
        except Exception as exc:
            logger.error(f"BigQuery streaming exception: {exc}")
            return False
