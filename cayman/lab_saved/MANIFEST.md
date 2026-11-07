# Cayman qBraid Lab recovery manifest (definitive gap report)
Collected: Sat Nov 7 2026, 08:44–08:47 MST (UTC-7)
Connector: user-qbraid list_files (read-only). Descriptor refetched live at ~08:46 MST; unchanged, so no retry was made (per instructions).

## Calls and results (verbatim)
- list_files orgSlug=intermountain_quantum_competition, path="" -> {"entries":[],"count":0}
- list_files orgSlug=intermountain_quantum_competition, path="iqc-pinned-dashboard" -> {"entries":[],"count":0}
- list_files (no orgSlug; tool chose default org "qbraid_default"), path="" -> {"entries":[],"count":0}
No errors were returned.

## Files recovered: 0
No checksums (nothing to hash). An empty result does NOT prove no saved files exist; the cause is undetermined.

## Documented facts (docs.qbraid.com, read 2026-11-07)
- Lab files can be downloaded without starting a session: Dashboard > Usage Overview > Download Files (https://docs.qbraid.com/v2/account/dashboard, /v2/account/usage).
- On-demand instances keep their own disk; changes there "do not sync back to cloud storage" (https://docs.qbraid.com/v2/lab/user-guide/on-demand-instances).
- In JupyterLab, single files: right-click > Download; folders: zip in terminal first (https://docs.qbraid.com/v2/lab/user-guide/files).
Whether list_files reads cloud storage or on-demand disks is not documented in the tool description.

## Gaps
- No saved Lab files were obtainable through the connector.
- Cells left unsaved in a browser tab cannot be recovered by file tools.
