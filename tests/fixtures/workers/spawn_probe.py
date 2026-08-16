from pathlib import Path
import sys

Path(sys.argv[1]).write_text("started", encoding="utf-8")
