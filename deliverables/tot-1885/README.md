# TOT-1885 light-only managed-runtime browser matrix

- Execution workspace: `f2083ed4-c306-4b7a-ac24-2cdad22efb0c`
- Managed service: `a55466d2-af9d-4cb8-98d5-d5b0ab83e028` (`twds-public-website`)
- Managed URL during capture: `http://127.0.0.1:45479`
- Start operation: `be2b4b60-7d7f-4aa8-991e-316e02dcd51e`
- Paperclip run: `f38466fe-2bde-4656-8612-d5355c61c3b1`
- Matrix: 10 routes × 5 widths × 2 OS color preferences = 100 cases/screenshots
- Result: PASS; minimum normal-text contrast `5.266206160481123:1`

The public pages expose no theme control, persistence, switching logic, dark-theme CSS,
or OS-preference activation. Both OS preference conditions render the same light UI.
The JSON retains per-case navigation/network failures, HTTP error responses, console
and page errors, overflow, focus indication, reduced-motion, favicon status, contrast
samples/failures, and screenshot hashes.
