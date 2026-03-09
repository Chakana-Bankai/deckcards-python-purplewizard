from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.qa_phase9_supervision import *  # noqa: F401,F403
else:
    runpy.run_module("tools.qa_phase9_supervision", run_name="__main__")
