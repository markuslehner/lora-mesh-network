import pi_interface
from datetime import datetime

if __name__ == '__main__':

    pi_interface.set_raspberry_name("MasterarbeitPi")

    pi_interface.download("project/server/logs/log_start_04022022_*.txt", "\\logs")

    pi_interface.download("project/server/data_db.db", "\\db_saves\\download\\data_db_%s.db" % datetime.now().strftime("%m_%d"))

    # pi_interface.download("project/server/last_state.pkl", '')