from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.assets.build_chakana_master_from_reference import *  # noqa: F401,F403
else:
    runpy.run_module("tools.assets.build_chakana_master_from_reference", run_name="__main__")
