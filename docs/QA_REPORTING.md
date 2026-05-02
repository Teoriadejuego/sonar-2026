# QA Reporting

## Schema

Every test result is stored with the following normalized fields:

- `schema_version`
- `test_id`
- `timestamp`
- `scenario`
- `input`
- `expected_result`
- `actual_result`
- `status`
- `impact`
- `notes`

Allowed values:

- `status`: `OK`, `FAIL`, `WARNING`
- `impact`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

## Storage

Default persistent outputs:

- JSONL append log: [outputs/qa_reports/test_results.jsonl](</C:/Users/Usuario/Desktop/AAC/codex/2026 SONAR/outputs/qa_reports/test_results.jsonl>)
- CSV export: [outputs/qa_reports/test_results.csv](</C:/Users/Usuario/Desktop/AAC/codex/2026 SONAR/outputs/qa_reports/test_results.csv>)

JSONL is the source of truth because it appends safely over time and preserves one record per line.

## Helper

Implementation lives in [ops/qa_reporting.py](</C:/Users/Usuario/Desktop/AAC/codex/2026 SONAR/ops/qa_reporting.py>).

Main functions:

- `build_test_result(...)`: validates and normalizes one result record.
- `log_test_result(...)`: builds and appends a record to the JSONL log.
- `load_test_results(...)`: reads the accumulated JSONL history.
- `export_results_csv(...)`: regenerates a spreadsheet-friendly CSV snapshot from JSONL.

## Example

```python
from ops.qa_reporting import export_results_csv, log_test_result

log_test_result(
    test_id="PERF-001",
    scenario="Landing carga en 4G lenta",
    input_data={
        "network_profile": "slow-4g",
        "url": "http://127.0.0.1:5173",
    },
    expected_result="La landing aparece y el CTA principal es usable en menos de 2 s.",
    actual_result="La landing apareció en 1.7 s y el CTA respondió al primer toque.",
    status="OK",
    impact="MEDIUM",
    notes="Medido en build local con caché vacía.",
)

export_results_csv()
```

The helper will keep accumulating new entries in the JSONL file across runs, and the CSV can be regenerated at any time from that history.
