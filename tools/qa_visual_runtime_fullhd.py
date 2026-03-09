from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.qa.qa_visual_runtime_fullhd import *  # noqa: F401,F403
else:
    runpy.run_module("tools.qa.qa_visual_runtime_fullhd", run_name="__main__")
