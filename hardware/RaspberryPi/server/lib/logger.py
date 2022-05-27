from datetime import datetime

class logger(object):

    '''
    LOGGER FOR DEBUGING

    @params

    level of debugging, 
    logs all messages with priority of >0 debug_level
    -debug_level : int [1, 2, 3, 4, 5]

    If it is running silently set to False to disable console output
    -print_console : bool

    Beginning of file name under which the log is stored, if None no file will be written
    -log_prefix : str
    '''
    def __init__(self, debug_level : int, print_console: bool, log_prefix : str) -> None:
        super().__init__()
        self.debug_level = debug_level
        self.print = print_console
        self.prefix = log_prefix

        self.file_name = "%s_%s" % (self.prefix, datetime.now().strftime("%m%d%Y_%H%M") )
        self.current_day = int( datetime.now().strftime("%d") )
        self.log_file = None

        # flush timer
        # interval in ms
        self.flush_interval = 1000*60
        # last flush
        self.last_flush = self.get_time() + self.flush_interval

        self.open_file()
    
    def log(self, message, level=2, disable_print=False):
        
        if(self.debug_level >= level):

            timestamp = datetime.fromtimestamp(self.get_time()/1000).strftime("%H:%M:%S.%f")[:-3]

            if(not self.log_file is None):
                self.log_file.write("(%i)  [%s] %s" % (level, timestamp, message))
                self.log_file.write("\n")

            if(self.print and not disable_print):
                print("(%i)  [%s] %s" % (level, timestamp, message))

    '''
    Update the state of the logger instance
    - flush buffer to file every minute
    - change file at 0:00 am to new date
    '''
    def update(self) -> None:

        # check if day changed
        if(int( datetime.now().strftime("%d") )  != self.current_day):

            self.log("DAY CHANGE", 1)
            self.log("  continuing log in file: %s.txt" % "%s_%s" % (self.prefix, datetime.now().strftime("%m%d%Y_%H%M") ), 1)
            self.close_file()

            old_file = self.file_name
            self.file_name = "%s_%s" % (self.prefix, datetime.now().strftime("%m%d%Y_%H%M") )
            self.current_day = int( datetime.now().strftime("%d") )

            self.open_file()
            self.log("CONTINUING LOG", 1)
            self.log("  from file: %s.txt" % old_file, 1)

        elif(self.get_time() > self.last_flush + 1000*60*1):
            self.log_file.flush()
            self.last_flush = self.get_time()


    def close_file(self) -> None:
        self.log_file.flush()
        self.log_file.close()

    def open_file(self) -> None:
        if(self.file_name is None):
            self.log_file = None
        else:
            self.log_file = open("logs/%s.txt" % self.file_name, "w")
            print("Started writing log: \"%s.txt\"" % self.file_name)

    def finish(self):
        if(not self.log_file is None):
            self.close_file()

    def get_time(self) -> int:
        return round(datetime.now().timestamp() * 1000)
