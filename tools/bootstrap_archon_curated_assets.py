from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.assets.bootstrap_archon_curated_assets import *  # noqa: F401,F403
else:
    runpy.run_module("tools.assets.bootstrap_archon_curated_assets", run_name="__main__")
