from pathlib import Path
import time

Path("simple_sleep.log").write_text("started", encoding="utf-8")
time.sleep(120)
