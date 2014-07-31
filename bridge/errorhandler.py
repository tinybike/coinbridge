import os, sys, traceback
from datetime import datetime
from functools import wraps

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
                "[" + str(datetime.now()) + "] Error in task \"" +
                task.__name__ + "\" (" +
                fname + "/" + str(exc_tb.tb_lineno) +
                "):" + e.message
            )
            self.logger.error("%s %s RPC instruction failed" % (erroroutput,
                                                                self.coin))
    return wrapper
