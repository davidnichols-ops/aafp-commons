# Local transport

GitHub files are snapshots, not node ingestion. Follow is explicit and local:

```bash
COMMONS_HOME=/tmp/commons-tx-a commons follow http://127.0.0.1:8081
COMMONS_HOME=/tmp/commons-tx-a commons pull
COMMONS_HOME=/tmp/commons-tx-a commons unfollow http://127.0.0.1:8081
COMMONS_HOME=/tmp/commons-tx-b commons import-published ./published.json
```

Only loopback HTTP peers are accepted. Packets are verified and submitted
through the recipient's existing admission policy. Arrival never makes a
claim true or trusted, and status still applies conflict and rely policy.
Evidence bundles are never fetched by world, status, or pull.
