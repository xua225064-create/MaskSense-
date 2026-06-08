import faulthandler, threading, time, sys
faulthandler.enable()
def dump():
    time.sleep(3)
    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
threading.Thread(target=dump, daemon=True).start()
import main
