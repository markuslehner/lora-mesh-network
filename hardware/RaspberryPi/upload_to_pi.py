import pi_interface
import time
from datetime import datetime

if __name__ == '__main__':
    # change db file:
    # copy to pc and override local one on pi with empty template
    change_db = True
    upload_code = True

    if(upload_code):
        # main python files
        pi_interface.upload("server", "web_server.py web_server_control.py central_node_gps.py central_node_web.py", "project/server")
        time.sleep(1)
        pi_interface.upload("server/static", "*.css ", "project/server/static")
        time.sleep(1)
        pi_interface.upload("server/templates", "*.html", "project/server/templates")
        time.sleep(1)
        pi_interface.upload("server/lib", "*.py", "project/server/lib")

    if(change_db):
        time.sleep(1)
        pi_interface.download("project/server/data_db.db", "\\db_saves\\download\\data_db_%s.db" % datetime.now().strftime("%m_%d"))
        time.sleep(1)
        pi_interface.upload("", "data_db.db", "project/server")
