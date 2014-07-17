import os, sys, traceback
from datetime import datetime
from functools import wraps

log = os.path.join(os.path.dirname(__file__), os.pardir, "log", "bridge.log")
if not os.path.isfile(log):
    open(log, 'a').close()

def error_handler(task):
    @wraps(task)
    def wrapper(self, *args, **kwargs):
        try:
            return task(self, *args, **kwargs)
        except Exception as e:
            self.connected = False
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            erroroutput = (
                "Error in task \"" + task.__name__ + "\" (" +
                fname + "/" + str(exc_tb.tb_lineno) +
                "):\n@ " + str(datetime.now()) + e.message
            )
            with open(self.log, 'a') as logfile:
                print >>logfile, erroroutput + "\nTraceback:"
                traceback.print_tb(exc_tb, limit=5, file=logfile)
            print "Error [%s]: %s RPC instruction failed" % (task.__name__,
                                                             self.coin)
            print "Traceback sent to", log
    return wrapper
