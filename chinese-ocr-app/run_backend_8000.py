from pathlib import Path
import traceback

LOG = Path(__file__).with_name("run_backend_8000.log")


if __name__ == "__main__":
    try:
      LOG.write_text("launcher started\n", encoding="utf-8")
      import uvicorn
      with LOG.open("a", encoding="utf-8") as f:
          f.write("uvicorn imported\n")
      uvicorn.run("main:app", host="0.0.0.0", port=8000)
    except Exception:
      with LOG.open("a", encoding="utf-8") as f:
          f.write(traceback.format_exc())
      raise
