from __future__ import annotations

import runpy

if __name__ != "__main__":
    from tools.qa.check_deck_system import *  # noqa: F401,F403
else:
    runpy.run_module("tools.qa.check_deck_system", run_name="__main__")
