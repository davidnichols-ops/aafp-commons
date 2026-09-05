# Security policy

AAFP Commons is local-first and treats client ledgers as private by default.
Only packets explicitly marked `public` are eligible for snapshot export.
Snapshots, indexes, and constitution manifests are untrusted input until their
schemas, content addresses, and signatures have been verified.

The following are deliberately separate concerns:

- AAFP AgentId identifies an agent reference; it does not prove a claim.
- Ironclad signatures prove packet integrity; they do not grant authority.
- Constitutions constrain admission; they do not override provider or system
  rules.
- Public indexes provide discovery; they are not consensus or canonical truth.

Do not place credentials, private research, or sensitive personal information
in public packets or issue reports. If you find a vulnerability involving
signature verification, private-data export, path traversal, or policy
bypass, report it privately to the repository maintainers rather than opening
a public issue. Include a minimal reproduction and avoid sending real secrets.

The project is still pre-release: no security response-time or hosted-service
availability guarantee is made. Distributed replication, abuse controls,
revocation, and authorization remain beta gates.
