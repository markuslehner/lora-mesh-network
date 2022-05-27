import pi_interface
import time

if __name__ == '__main__':
    
    up = False
    if(up):
        pi_interface.upload("gps", "gps_db_7.db web_server_gps.py", "project/server")
        time.sleep(1)
        pi_interface.upload("server", "central_node_gps.py", "project/server")
    else:
        pi_interface.download("project/server/gps_db_7.db", "\\db_saves\\download")
        pi_interface.download("project/server/logs/gps_log_start_*.txt", "\\logs")