from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.maintenance.final_gameplay_integration_fix import *  # noqa: F401,F403
else:
    runpy.run_module("tools.maintenance.final_gameplay_integration_fix", run_name="__main__")
