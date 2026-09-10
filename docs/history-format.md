# Historical format

RegScope history is stored as one UTF-8 JSONL file per function. The filename
is derived from the first 16 hexadecimal characters of the SHA-256 hash of the
fully qualified function name.

Each line is a versioned `TrendPoint` object:

```json
{"call_count":0,"duration_ns":1234,"exceptions":0,"fingerprint":"...","function":"pkg.fn","recorded_at":"2026-01-01T00:00:00+00:00","schema_version":1}
```

The history record contains aggregate metrics and a derived fingerprint only;
it does not contain arguments, SQL text, request data, Redis keys, or results.
Records without `schema_version` are read as version 1 for migration from the
initial format. New records always include the field. `HistoryStore(max_points=N)`
retains only the newest N records for each function.

## CI artifact usage

GitHub Actions stores generated baseline and history files in the
`regscope-baseline-master` artifact rather than committing them to the
repository. The artifact is published only by successful pushes to trusted
`master` and retained for 30 days. Pull-request jobs consume the latest
successful artifact and never update it.

Malformed history or baseline files produce an explicit storage error. They
are not silently discarded or treated as an empty baseline.
