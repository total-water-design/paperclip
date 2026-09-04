# TOT-1880 managed-runtime browser matrix

- Tested website source SHA: `4097676eaf9c8f616c873e09d499198ed9885b76`
- Evidence successor SHA: the immutable Git commit containing this directory;
  recorded in the Paperclip handoff and work product
- Execution workspace: `f2083ed4-c306-4b7a-ac24-2cdad22efb0c`
- Managed runtime service: `a55466d2-af9d-4cb8-98d5-d5b0ab83e028` (`twds-public-website`)
- Managed runtime URL during capture: `http://127.0.0.1:45479`
- Paperclip run: `c49ed2af-d875-4adf-8b0a-09ea685a664e`
- Managed start operation: `6e9e5ffa-728d-4a21-892f-b72bb46831ca`
- Browser: Chromium `151.0.7922.34`
- Matrix: 10 routes × 5 widths × 2 themes = 100 cases and 100 screenshots
- Result: PASS; minimum measured normal-text contrast `5.266206160481123:1`

`browser-matrix.json` is the exact machine-readable record. Every case includes
the top-level navigation response, final URL, failed HTTP responses, failed
requests, console errors, page errors, overflow result, keyboard-focus visibility
and indicator details, reduced-motion media result and motion violations, favicon
URL/status, all rendered text contrast samples, and normal-text contrast failures.
All failure/error arrays are retained even when empty.

Aggregate results: zero failed cases, failed responses, failed requests, console
errors, page errors, overflow cases, focus failures, favicon failures, motion
violations, and contrast failures.

The browser used only the Paperclip-managed service identified above. Earlier
managed start attempts failed before readiness and were retained in Paperclip
workspace operations `29d8bc36-9c10-46e7-96de-afde3661eddb`,
`df496d5a-522e-42a0-8184-79d82b94263f`, and
`a3bad0fb-e268-4fc8-a851-de486e5404b6`. No unmanaged server was used for this
successor run.
