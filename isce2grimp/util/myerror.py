# dols.py
import sys
def myerror(message,myLogger=None):
    """ print error and exit with a FAILING status (1).

    Local copy of utilities.myerror; was a bare sys.exit(), i.e. status 0,
    which made fatal errors look like success to any caller checking a
    return code.
    """
    print('\n\t\033[1;31m *** ',message,' *** \033[0m\n')
    if myLogger != None :
        myLogger.logError(message)
    sys.exit(1)




