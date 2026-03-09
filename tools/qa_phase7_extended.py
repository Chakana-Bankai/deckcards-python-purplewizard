from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.qa.qa_phase7_extended import *  # noqa: F401,F403
else:
    runpy.run_module("tools.qa.qa_phase7_extended", run_name="__main__")
