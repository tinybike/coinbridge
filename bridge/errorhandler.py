import os, sys, traceback
from datetime import datetime
from functools import wraps
import config

log = os.path.join("log", "bridge.log")
if not os.path.isfile(log):
    open(log, 'a').close()

def error_handler(task=""):
    def decorate(task_func):
        @wraps(task_func)
        def wrapper(self, *args, **kwargs):
            try:
                return task_func(self, *args, **kwargs)
            except Exception as e:
                self.connected = False
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                erroroutput = (
                    "Error in task \"" + task + "\" (" +
                    fname + "/" + str(exc_tb.tb_lineno) +
                    "):\n@ " + str(datetime.now()) + e.message
                )
                with open(self.log, 'a') as logfile:
                    print >>logfile, erroroutput + "\nTraceback:"
                    traceback.print_tb(exc_tb, limit=5, file=logfile)
                if config.DEBUG:
                    raise
                else:
                    print "Error [%s]: %s RPC instruction failed" % (task,
                                                                     self.coin)
                    print "Traceback logged to", log
        return wrapper
    return decorate
