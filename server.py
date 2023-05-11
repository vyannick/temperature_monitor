import threading
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as md
import io
import time as Time
import datetime
from dateutil import parser
import requests


from flask import Flask, render_template, send_file, make_response, request
app = Flask(__name__)

from tinydb import TinyDB, Query
db = TinyDB('db.json')


def getDataFromEntry(entry):
    time = parser.parse(entry["time"])
    temp = entry["temp"] /100
    return time, temp

# Retrieve data from database
def getLastData():
    last_entry = db.get(doc_id=len(db))
    return getDataFromEntry(last_entry)

def getHistData (starttime,endtime):
    def between(val, dateTimeString1, dateTimeString2):
        valDateTime = parser.parse(val)
        dateTime1 = parser.parse(dateTimeString1)
        dateTime2 = parser.parse(dateTimeString2)
        return dateTime1 <= valDateTime <= dateTime2
    Temp = Query()
    
    results = db.search(Temp.time.test(between,starttime ,endtime))

    times = []
    temps = []
    for result in results:
        time,temp = getDataFromEntry(result)
        times.append(time)
        temps.append(temp)
    return times, temps


# main route
@app.route("/")
def index():
    time, temp = getLastData()
    templateData = {
          'time'	: time,
          'temp'	: temp,
          'starttime':  datetime.datetime.now() - datetime.timedelta(days=1),
          'endtime'	: datetime.datetime.now()
    }
    return render_template('index.html', **templateData)

@app.route('/', methods=['POST'])
def my_form_post():
    global numSamples
    starttime = parser.parse(request.form['starttime'])
    endtime = parser.parse(request.form['endtime'])
    time, temp = getLastData()
    templateData = {
          'time'	 : time,
          'temp'	 : temp,
          'starttime': starttime,
          'endtime'  : endtime
    }
    return render_template('index.html', **templateData)

@app.route('/plot/temp')
def plot_temp():
    args = request.args
    times, temps = getHistData(args["starttime"],args["endtime"])
    ys = temps
    fig = Figure()
    fig.set_figwidth(10)
    fig.set_figheight(3)
    axis = fig.add_subplot(1, 1, 1)
    axis.set_title("Temperature [°C]")
    axis.set_xlabel("Time")
    axis.grid(True)
    xs = times
    axis.plot(xs, ys)
    axis.set_xticklabels(xs,fontsize=5)
    xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
    axis.xaxis.set_major_formatter(xfmt)
    canvas = FigureCanvas(fig)
    output = io.BytesIO()
    canvas.print_png(output)
    response = make_response(output.getvalue())
    response.mimetype = 'image/png'
    return response

def fetch_sensor_data():
    sensorURL = "http://192.168.178.34/api/cj3eTcUbi-bitj0r5FwkCBPHABandbPk7jpiFGe0/sensors/24"

    previousTimeStamp = ""

    while(True):
        latestSensorRead = requests.get(sensorURL).json()
        latestSensorState = latestSensorRead["state"]

        if latestSensorState:
            temp = latestSensorState["temperature"]
            time = latestSensorState["lastupdated"]

            if time != previousTimeStamp:
                db.insert({'time': time,'temp': temp})
            
            previousTimeStamp = time
        else:
            print("Error reading sensor")
            print(latestSensorRead)

        Time.sleep(300)

if __name__ == "__main__":
    sensor_thread = threading.Thread(target=fetch_sensor_data, args=())
    sensor_thread.start()
    app.run(host='0.0.0.0', port=9090, debug=False)