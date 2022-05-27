import sys

# check environment
RASPBERRY = sys.platform == "linux"


from flask import Flask, render_template
if(not RASPBERRY):
    import os
import sqlite3
from sqlite3 import Error

app = Flask(__name__)

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn

@app.route('/')
def index():
    if(RASPBERRY):
        database = r"gps_db_7.db"
    else:
        database = os.getcwd() + "/gps/gps_db_7.db"
       
    db = create_connection(database)

    cursor = db.execute('SELECT id, sender, type, longitude, latitude, battery, time_received FROM packets')
    items = cursor.fetchall()

    return render_template('index_gps.html', items=items)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)