# Printer Setup

For v0.1, `bambu-pipe` uses Bambu LAN + Developer Mode.

1. Put the printer on the same LAN as the API/CLI host.
2. Enable LAN/Developer Mode on the printer.
3. Copy printer IP, serial, and access code into `.env`.
4. Run `bambu-pipe status`.

The project checks TCP ports `8883` (MQTT) and `990` (FTPS) before printing.
If those ports are closed, printing will fail before a job is created.
