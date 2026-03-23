# DreamAxis Worker

DreamAxis Worker is the Phase 1 execution-layer host for the CLI runtime slice.

Current responsibilities:

- register itself as a `cli` runtime with the API
- keep an online heartbeat
- create and reuse bounded CLI sessions
- execute safe commands inside the workspace root
- expose internal HTTP endpoints consumed by the API runtime dispatcher

Runtime modes:

- **mounted worker**: the default Docker path, best for repos already mounted into `/workspace`
- **host worker**: a Windows-native path started with `scripts/start-host-worker.ps1`, best for arbitrary local repos such as `D:\paperclip`
