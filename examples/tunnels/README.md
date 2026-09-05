# v0.3 Tunnel Templates

The files under `v03-evidence/tunnel-A.sh`, `tunnel-B.sh`, and `tunnel-C.sh`
are **local loopback only** templates shipped with the v0.3 evidence set.

## Intent

In v0.3 these scripts existed to forward a remote `localhost:8081` observer
endpoint onto local `908x` ports so a multi-node evidence run could be
inspected from one machine. The shipped templates no longer carry any real
remote endpoint. They use explicit placeholders:

- `HOST_A` / `PORT_A`
- `HOST_B` / `PORT_B`
- `HOST_C` / `PORT_C`

Each placeholder defaults to `localhost` / `22`. With the defaults the
scripts will not establish a useful remote tunnel; they exist only as a
structural reference for how the v0.3 evidence topology was wired.

## Placeholders are intentionally not configured for remote use

Do **not** fill these placeholders with real hosts or ports unless you are
re-running the v0.3 evidence topology and understand the forwarding layout.
The tracked repository must never contain real endpoint data, credential
strings, or live remote commands. If you need a remote run, keep the real values outside
the repository (e.g. in a gitignored local env file or a secret store) and
export them before invoking the template.

## Forwarding map (structural only)

| Template | Local forwards | Placeholders |
| --- | --- | --- |
| `tunnel-A.sh` | `9082`, `9083` → `localhost:8081` | `HOST_A/PORT_A`, `HOST_B/PORT_B` |
| `tunnel-B.sh` | `9081`, `9083` → `localhost:8081` | `HOST_B/PORT_B`, `HOST_C/PORT_C` |
| `tunnel-C.sh` | `9081`, `9082` → `localhost:8081` | `HOST_B/PORT_B`, `HOST_A/PORT_A` |

The `localhost:8081` target matches the `commons serve` loopback observer
from the W1 contract. Nothing here reaches a remote host by default.
