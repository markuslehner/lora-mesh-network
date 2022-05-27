from flask import Flask, render_template
from pathlib import Path
from lib import database

app = Flask(__name__, root_path=str(Path(__file__).parent.parent) + "/hardware/RaspberryPi/server/", )

@app.route('/')
def index():

    database_file = str(Path(__file__).parent.parent) + "/hardware/RaspberryPi/db_saves/data_db_04_01.db"
    db = database.create_connection(database_file)

    cursor = db.execute('SELECT id, sender, type, temp, acc_x, acc_y, acc_z, battery, time_received FROM packets')
    items = cursor.fetchall()

    return render_template("index.html", items=items)

if __name__ == '__main__':
    app.run(host='0.0.0.0')