# TOT-689 intended-commit manifest

Candidate ref: `task/tot-689-current-alpha-tweco-h-v6`

Base and exact first parent: protected Alpha commit `3df3fe63103def304f9eb2631ac363c3a9a9041b`.

Reconciled source candidate: TOT-435 `f028b00ea74572cdb5f226875f1e8ebe4974ea3a`.
Original frozen package inputs: A `0b40dbc30856ae3e403bfa164b2ca835c0afed3f`; B `140e948f65dde9e58f4efbe67412e767f1239ce4`; C `cb680b325547d77322d3744e0647b10aefde5087`; D `450ab1579e35603a2c524ab644dded119450b949`; E `7fb925c812011a2f13d42ff9e98f7e073654b18d`; E remediation `c6c686c8e5ab35fe30f76a2b35cd9d7338104695`; F `81c11a25251dee9c68d2402ed3c25224109f1e51`; G `ae2b04475194f202acf4910a80a30557f62f8312`.

The source reconciliation patch from the prior candidate was reapplied without conflicts to the exact protected Alpha base above. Every resulting path was regenerated from this base and is recorded in `validation/TOT-689-changed-file-manifest.txt`; prior path lists were not presumed valid. Required Economics reporting packages (`openpyxl`, `pypdf`, and `reportlab`) are declared in the application requirements and installed by the scoped validation workflow. The workflow propagates pytest failures through `tee`, checks out the exact PR head rather than a synthetic merge ref, and fails if the recorded candidate differs from the workflow event's exact head. Tests that exercise desktop preview explicitly set desktop deployment mode, so server-mode CI no longer leaks into that case. The workflow and authenticated browser integration test are candidate evidence infrastructure and do not alter application behavior. Unrelated input history is excluded. No protected branch is modified; no merge, deploy, or promotion is performed.
