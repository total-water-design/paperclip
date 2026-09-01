# TOT-1445 intended commit manifest

- Protected Alpha parent: `346b65a8a4ac9b6ce80c37125051f59155f2a3bc`
- Independently certified Economics source: `4ea04e94a5906d1b2bc1c75045d2753ea72981ef`
- Source parent: `3df3fe63103def304f9eb2631ac363c3a9a9041b`
- Intended history: exactly one candidate commit directly above the protected Alpha parent.
- Intended content: the certified Economics source commit delta, plus this TOT-1445 manifest pair.
- Shared dependency reconciliation: preserve Alpha's `referencing>=0.36,<1` entry and add the certified Economics `openpyxl`, `pypdf`, and `reportlab` entries. No Alpha-owned dependency was removed or modified.
- Excluded history: all commits other than protected Alpha ancestry and the single new candidate commit. The source commit is content provenance only and is not an ancestor of the refreshed candidate.
- Prohibited actions: no merge, deployment, promotion, force-push, or mutation of protected Alpha.

The immutable candidate SHA is recorded after commit creation in the TOT-1445 issue evidence and remote branch reference because a commit cannot contain its own SHA.
