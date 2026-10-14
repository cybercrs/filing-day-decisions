# Filing Day Decisions — native browser app

The final student-facing app uses HTML/CSS/JavaScript with no Python, Streamlit, Pyodide, WebAssembly, runtime package, external asset request, npm runtime dependency, shared storage or new service. The isolated source branch is `native/html-js`; publication adds only `/js/` on the existing `stlite-browser` branch. Main, original Python/Streamlit code, the published stlite root and Pages settings remain unchanged.

## Original teaching and calculations

All six connected rounds, nineteen decisions, fifty-seven options and their feedback, five reporting gauges, reflection questions/model answers, disclosure/fact panels, concepts, three final statuses and complete decision trail remain. Original renderers and case content are exported during development; no Receivables-specific curriculum changes are applied.

The independent native model matches every Python option outcome and eighty complete random trajectories. Gauge changes apply in decision order and clamp after each decision to 0–100, preserving actual gained/lost traces and per-round baselines. Summary percentage display uses Python-compatible ties-to-even rounding. Options reproduce CPython's integer-seeded MT19937 and full small-population random.sample exactly, preserving the saved 32-bit option seed and every old answer permutation.

The original gates remain: choose every answer before submitting; submission locks the round and changes gauges once; wrong choices still unlock Continue. Reflection answers can be deliberately revealed after submission. The ordinary Continue action earns the next page. Start over retains its original behavior: it opens a fresh round one directly, with a new seed and empty results/reveals, rather than returning to the welcome page. The initial welcome page still appears for an independent fresh session.

## Review and compatible saving

Original compact, compressed version-1 `progress` links remain compatible in both directions. To use an old Python/stlite bookmark, preserve its query parameters and change only the path to `/filing-day-decisions/js/`. Draft choices, submitted results, option seed, reveal flags and completion survive refresh/bookmarks. Extra query values, repeated parameters and fragments are retained. No names, free text, localStorage, sessionStorage or central score store are introduced.

Subtle boxed Back/Forward buttons have native accessible names, visible keyboard focus and 44px targets. Back is strictly view-only: no answers, submit/continue actions, new reveals, scoring, resets or changed canonical progress. Review gauges are projected from that round's original baseline and results. A previously unrevealed reflection answer stays hidden; an answer already revealed remains visible. Forward visits reached pages only and stops at the actual frontier, including after submitting the current round. Engine guards enforce these rules independently of the controls. Older copied links remain independent saved cases; tabs and contexts share no storage.

The lesson defines no downloads or dataframes. The ordinary instructional phrase “Test your thinking” and report-quality outcome “Promising draft” are preserved; they describe the lesson, not provisional app branding. The browser title is “Filing Day Decisions”.

## Build and verification

```bash
/workspace/.cloud-setup/venvs/main/bin/python native/export.py
node --test native/tests/*.test.mjs
/workspace/.cloud-setup/venvs/main/bin/python -m unittest discover -s tests -v
/workspace/.cloud-setup/venvs/main/bin/python native/build.py
/workspace/.cloud-setup/venvs/main/bin/python native/tests/browser.py
```

The build copies seven native assets and a hash manifest only. `--site-output PATH` writes only `PATH/js/`. Serve over HTTP(S); `file://` is unsupported. Current ES-module browsers with BigInt, Web Crypto, structured cloning and Compression Streams are required. Chromium is tested; other browsers and physical devices remain unmeasured.

Screenshots, Python parity, browser results and source-protection evidence are in `review/` and `VALIDATION.md`. Publication verifies unchanged non-js static blobs, exact source/static commits and successful Pages deployment. Hosted browser QA remains blocked by the known Pages-hostname proxy denial; no alternate access route is used. Local initialization measurements do not promise school-network speed or classroom capacity.
