# X0 transport v0

Commons transport is explicit local follow/pull, not mesh discovery. A home
stores loopback peer URLs in `peers.json`; `follow` adds one and `unfollow`
removes it. `pull` fetches signed packets and submits each through the normal
constitution and policy gate. `import-published` performs the same operation
once from a local public snapshot file. The default server binds only to
`127.0.0.1`; no DNS, bootstrap list, mDNS, QUIC, or evidence fetching exists.
