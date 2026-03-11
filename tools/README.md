# Chakana Studio Tools

Canonical entrypoint:
- `python tools/chakana_studio.py <command>`

Preferred commands:
- `project-audit`
- `manifest-audit`
- `art-audit`
- `audio-audit`
- `qa-smoke`
- `reports-build`

Legacy root scripts are preserved only as compatibility wrappers when they already forward into:
- `tools/assets/`
- `tools/qa/`
- `tools/maintenance/`

Consolidation rule:
- new operational workflows should go through `chakana_studio.py`
- direct wrapper scripts remain for backward compatibility until a later archive pass
