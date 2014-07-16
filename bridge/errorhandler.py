import os, sys, traceback
from functools import wraps

def error_handler(task=""):
    def decorate(task_func):
        @wraps(task_func)
        def wrapper(self, *args, **kwargs):
            try:
                return task_func(self, *args, **kwargs)
            except urllib2.HTTPError, urllib2.URLError:
                self.connected = False
                lognote = "Error [%s]: %s RPC instruction failed" % (task, self.coin)
                if config.DEBUG:
                    print lognote
                with open(self.log, 'a') as logfile:
                    print >>logfile, lognote
                if config.TESTING:
                    raise
            except Exception as e:
                self.connected = False
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                erroroutput = (
                    "Error in task \"" + task + "\" (" +
                    fname + "/" + str(exc_tb.tb_lineno) + "):\n--> " + e.message
                )
                with open(self.log, 'a') as logfile:
                    print >>logfile, erroroutput + "\nTraceback:"
                    traceback.print_tb(exc_tb, limit=5, file=logfile)
                raise
        return wrapper
    return decorate
