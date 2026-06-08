import faulthandler, threading, time, sys
faulthandler.enable()
def dump():
    time.sleep(3)
    with open('dump.txt', 'w') as f:
        faulthandler.dump_traceback(file=f, all_threads=True)
threading.Thread(target=dump, daemon=True).start()
import main
