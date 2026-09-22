# OpenClaw TOS 7 Tools

Read-only OpenClaw tools for TerraMaster TOS 7.

This project exposes TOS 7 system information to OpenClaw through typed tools, using the official `tos ... --json` CLI where available and narrow, read-only host fallbacks for metrics not exposed by the CLI.

## Goals

- Read-only by default.
- No arbitrary shell execution.
- Prefer official TOS 7 CLI JSON output.
- Keep host-specific configuration outside the repository.
- Work through a small allowlisted host bridge.

## Tools

- `tos_system` — system info, CPU/RAM/load, uptime, temperatures
- `tos_power` — fan, buzzer, UPS/NUT status
- `tos_storage` — storage overview, disks, arrays, volumes
- `tos_network` — network configuration and counters
- `tos_services` — TOS services, file services, SSH, failed units
- `tos_apps` — application inventory/status
- `tos_users` — users, groups, online sessions
- `tos_shares` — shared-folder inventory/detail
- `tos_security` — firewall status/rules and listeners
- `tos_logs` — bounded TOS log queries
- `tos_docker` — container status/health/restart metadata
- `tos_health_snapshot` — aggregated NAS health summary

## Architecture

```text
OpenClaw -> typed tools -> TOS 7 bridge -> /usr/bin/tos --json
                                      -> /proc + /sys (read-only)
                                      -> NUT/upsc
                                      -> Docker inspect
```

The bridge intentionally has no arbitrary `exec` endpoint.

## Requirements

- TerraMaster TOS 7
- `/usr/bin/tos`
- Python 3.11+
- OpenClaw 2026.5.17+
- Optional: NUT `upsc`, Docker CLI, `smartctl`

Some TOS CLI queries require an authenticated TOS session/token. Configure that on the host; never embed credentials in the plugin or repository.

## Bridge

```bash
export TOS7_BRIDGE_TOKEN='replace-with-a-random-secret'
python3 bridge/tos7_bridge.py --listen 127.0.0.1 --port 5077
```

The bridge refuses non-loopback binding without a bearer token.

## OpenClaw config

```json
{
  "baseUrl": "http://host.example.internal:5077",
  "tokenEnv": "TOS7_BRIDGE_TOKEN",
  "timeoutMs": 8000
}
```

The token value is read from the named environment variable at runtime.

## Build and test

```bash
npm install
npm run build
npm test
npm run audit:public
```

## Security

This public repository intentionally contains no NAS hostnames, LAN IPs, usernames, credentials, production paths, or private runtime configuration.

v0.1 is read-only. Write operations should be designed separately with explicit authorization and stronger gating.

## License

MIT
