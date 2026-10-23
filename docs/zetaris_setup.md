# Registering the three tables in Zetaris

The agent reads three tables through the Zetaris gateway with plain `SELECT` statements:

| table | file | content |
|---|---|---|
| `p53_interactions` | `data/p53_interactions.csv` | the 35 Boolean update rules (node, gene, role, rule, signed regulators) |
| `phenotypes` | `data/phenotypes.csv` | scenario definitions and what the unperturbed network does (no solutions) |
| `druggability` | `data/druggability.csv` | per-gene drug evidence (hand-curated, to be verified) |

## What is already done
- The platform runs locally (`docker compose up -d`; the `driver` container must be up, `docker ps` should list four
  healthy containers: postgres, driver, api, ui).
- The three CSV files were uploaded to the Zetaris file store under `file-store/p53/`.

## What you do once in the web UI (http://localhost:3000)
Zetaris only accepts `SELECT` through its REST gateway, so tables are created from the UI:

1. Create a database (ours is named `open_agent`; the agent reads it from `ZETARIS_DB`, default `open_agent`).
2. In it, create a table from each CSV in `file-store/p53/` (source: file store, format: CSV, first row is the header,
   delimiter `,`). Name the tables exactly as in the table above.
3. Check it from a terminal:

```bash
python -c "from agent.tools_zetaris import DataLayer; d=DataLayer(allow_fallback=False); print(len(d.network_rows()), d.source)"
```

It should print `35 zetaris` (verified: the three tables return 35, 13 and 23 rows, identical to the CSV files). Until then the agent uses the local CSV files and says
`data layer: local-csv (...)` at the top of every report, so nothing is silently faked.

## Gateway notes (found by inspection, not documented by Zetaris)
- `POST /api/auth/login` with `{"username","password"}` returns `idToken` and `orgId`.
- `POST /api/proxy/query/sql/start` with headers `Authorization: Bearer <idToken>`, `X-Org-ID`, `X-Request-ID`
  and body `{"select": "<SELECT ...>", "pageLimit": n}`. Only `SELECT` is accepted.
- The port 8888 mentioned in some notes is the internal API; the gateway lives on 3000.
