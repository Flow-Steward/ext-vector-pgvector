# PostgreSQL pgvector for Flow Steward

Standalone `flowsteward.pgvector` 1.0.0, repository `Flow-Steward/ext-vector-pgvector`.
Provides dense vector storage through a minimal Google MCP Toolbox PostgreSQL build.
Linux AMD64 and ARM64 archives each contain only their matching native binary.
No triggers, embedding model, LLM, arbitrary SQL, connection URL overrides, or automatic retries.

## Connect

Create an explicit project connection of type `pgvector`. Set `host`, optional `port`
(default 5432), `database` (default `postgres`), `schema` (default `fs_vectors`),
`tls` (default true), and `request_timeout_seconds` (1–30, default 15).
Store `username` and `password` in the host secret fields. Each workflow step must
select this project connection and supply its exact ID as `connection_ref`.
The server administrator must install pgvector in `public` before use
(`CREATE EXTENSION vector`). Tested against pgvector 0.8.5.

Public endpoints require TLS with certificate and hostname verification. Endpoint
addresses are resolved by the host SDK and pinned in the native dialer while the
original hostname remains available for TLS verification. Private endpoints need
host-administrator `FS_ALLOW_PRIVATE_REMOTE_URLS=true`; only private endpoints may
disable TLS. Fallback endpoints are disabled. Credentials are never returned in
errors or emitted as diagnostics.

## Actions

| Action | Purpose |
| --- | --- |
| `ensure_collection` | Create schema, collection table, HNSW and document indexes; verify dimensions/metric. |
| `get_collection` | Inspect collection dimensions, metric, and index readiness. |
| `drop_collection` | Drop collection table and indexes; requires `confirm=true`. |
| `upsert_chunk` | Upsert a chunk by stable `chunk_id`, `document_id`, and supplied vector. |
| `upsert_document` | Atomically upsert 1–100 explicitly identified chunks for a document. |
| `get_chunk` | Fetch a chunk and optional vector by stable ID. |
| `update_chunk` | Replace supplied content, metadata, source, or vector fields by stable chunk ID. |
| `delete_chunk` | Delete a chunk by stable ID. |
| `delete_document` | Delete all chunks for a stable document ID, returning only a deletion count. |
| `query` | Bounded nearest neighbors, optional JSON metadata containment filter and minimum score. |

A collection is a table inside the selected schema. Use ASCII identifiers up to 48
characters. Collection dimensions are fixed at creation (1–2000). Metric is
`cosine` (default), `l2`, or `inner_product`. Existing collections with differing
index dimensions or metric fail verification instead of being silently reused.
An ensure operation consists of separate DDL statements and may partially complete
if a later statement fails. Re-run only after inspecting the failure and schema.
Dropping a collection removes that table, its indexes, and its rows.

Chunks require nonempty stable IDs up to 256 UTF-8 bytes, a finite nonzero dense
vector with matching dimensions, optional `content` (64 KiB), JSON object
`metadata` (32 KiB), and JSON object `source` (32 KiB). In `upsert_document`, provide
`document_id`, shared `source`, and `chunks` with `chunk_id`, `vector`, optional
`content`, and `metadata`. Omitted old chunks remain; use `delete_document` to
remove all chunks. Upserts replace supplied chunk data. Updates replace only the
fields supplied, including entire metadata/source objects. Stable chunk IDs are
unique within a collection and can be reassigned to another document by upsert.

Query accepts `vector`, `limit` (1–100, default 20), `metadata_filter` (JSON object
containment), optional finite `min_score`, and `include_vector` (default false).
Every match includes chunk/document IDs, content, metadata, source and score.
Cosine score is `1 - cosine_distance`; L2 score is `1/(1 + euclidean_distance)`;
inner-product score is the dot product. Scores are ordered descending. HNSW is an
approximate index; selective filters may return fewer than the requested limit.
The extension does not perform text search, vectorization, or chat generation.

## Effect and resource contract

Every write requires the host's durable `external_effect_id` claim. Test-mode
writes are suppressed before any endpoint lookup, process launch, or provider I/O.
Claims are host-managed; the connector does not provide server-side deduplication
of claims. Failed dispatched writes report an uncertain external effect and never
claim to be safely retryable. A shared deadline covers every provider call in the
action. A killed write may already have applied on the server.

Host input is capped at 256 KiB, final results at 480 KiB. The native layer limits
rows to 100, serialized result JSON to 480 KiB, each PostgreSQL message body to
512 KiB, and total connection reads to 2 MiB. Python also bounds and drains
subprocess stdout/stderr and tears down its process group. Responses over a limit
fail rather than being truncated; choose smaller query limits or shorter content.
Statement and lock timeouts bound provider work. Values are driver-bound;
identifier interpolation uses a closed ASCII grammar and quoting.

## Build and verify

`scripts/build_toolbox.sh` builds the two native targets in the pinned Go Docker
image from Toolbox v1.3.0, commit
`b0010060a939455d91e4f8ba62dc3e72b1892469`. The bundled source patch and
`toolbox-provenance.json` record the exact native hashes, sizes, packages and pins.
The only registered source/tool types are `postgres` and `postgres-sql`.

From the Flow Steward repository, run the disposable Docker checks:

```sh
./core/entrypoints/cli/scripts/lint.sh --checks extension-static,extension-tests \
  --extension-root /absolute/path/to/ext-vector-pgvector
```

Live tests are opt-in via `PGVECTOR_LIVE_HOST` or a local untracked
`tests/live-pgvector.local.json` containing `{"host":"disposable-container-name"}`.
Use exclusively a disposable
pgvector fixture database named `vectors`, with fixture user `vector_test` and
fixture password `fixture-only-pgvector`. Never point this fixture mode at a
production database. The tests create and drop randomly named collection tables.

Create deterministic archives with:

```sh
python3 scripts/package_extension.py --runtime-target linux-amd64
python3 scripts/package_extension.py --runtime-target linux-arm64
```

The packager verifies ELF architecture, executable mode, SHA-256 provenance,
installer size limits, package metadata, and excludes foreign binaries and local
artifacts. The installed Python runtime supplies Flow Steward Extension SDK 0.4.0.
