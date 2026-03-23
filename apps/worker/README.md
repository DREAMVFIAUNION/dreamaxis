# DreamAxis Worker

DreamAxis Worker is the Phase 1 execution-layer host for the CLI runtime slice.

Current responsibilities:

- register itself as a `cli` runtime with the API
- keep an online heartbeat
- create and reuse bounded CLI sessions
- execute safe commands inside the workspace root
- expose internal HTTP endpoints consumed by the API runtime dispatcher
