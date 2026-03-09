from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.assets.curated_regen_cache_reset import *  # noqa: F401,F403
else:
    runpy.run_module("tools.assets.curated_regen_cache_reset", run_name="__main__")
