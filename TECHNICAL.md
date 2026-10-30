# Technical Overview — Python Edition

## Main pipeline

- `deob.py`: Python CLI, file discovery, detection dispatch, batch jobs and output handling.
- `bot.py`: Python Discord bot, attachment validation, queueing, status updates and result delivery.
- `fetch.py`: Python HTTP downloader and supported chained-payload retrieval.
- `core/harness.py`: Luau runtime orchestration, offline Roblox environment, trace capture, chunk extraction and watchdog.
- `core/obfuscators/luraph_v15/driver.py`: trace, anti-tamper reruns, instrumentation and devirtualization pipeline.
- `core/obfuscators/luraph_v15/vmmap.py`: AST-based VM dispatcher and closure mapping.
- `core/obfuscators/luraph_v15/devirt.py`: symbolic VM execution and source lifting.
- `core/obfuscators/luraph_v14/`: experimental v14 mapping and lifting support.

## Runtime boundary

The application and orchestration layer is Python-only. Luau source still requires the Luau compiler/runtime executables (`luau-ast` and `luau`) to parse and execute the protected program inside the offline sandbox. These are native runtime binaries, not a Node.js dependency.

## Safety

Treat unknown Lua scripts as untrusted input. Run the bot in an isolated container, restrict CPU/memory, avoid mounting secrets into the worker, and keep execution timeouts enabled.
