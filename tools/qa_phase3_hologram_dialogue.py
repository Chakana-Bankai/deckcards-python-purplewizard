from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.qa.qa_phase3_hologram_dialogue import *  # noqa: F401,F403
else:
    runpy.run_module("tools.qa.qa_phase3_hologram_dialogue", run_name="__main__")
