# TOT-1878 browser matrix evidence

- Tested source SHA: `31eb19e59dd9cb65128e2fd33a1ce6d87627ff3a`
- Base candidate SHA: `5f7e899694c4d9c7c5bd6de4149a08d19ec22678`
- Execution workspace ID: `f2083ed4-c306-4b7a-ac24-2cdad22efb0c`
- Paperclip run ID: `01abd812-4ccd-4057-a4f3-6740b8c6ec06`
- Browser: Chromium `151.0.7922.34`
- Matrix: 10 routes × 5 widths × 2 themes = 100 cases and 100 full-page screenshots
- Result: PASS; minimum measured normal-text contrast `5.266206160481123:1`

`browser-matrix.json` contains every computed contrast sample and the page status,
overflow, keyboard/focus, favicon, console error, page error, failed HTTP response,
failed request, and reduced-motion observations for each case. `raw-verification.log`
and `server.log` preserve command/test and server output.

The project workspace does not define a managed runtime service. A start request
returned HTTP 422, so the browser run used a bounded Flask process inside the
claimed Paperclip execution workspace; the process was terminated by the same
command's exit trap. This is the only runtime limitation.
