# run.pyw — no-console launcher for PromptImprover.
# Double-click this file (or right-click → Open) to start the app.
# pythonw.exe runs .pyw files with no terminal window.
import sys
import os

# Ensure the project root is on sys.path regardless of where this file
# is invoked from (e.g. double-clicked from Desktop shortcut).
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
os.chdir(_here)

import main
main.main()
