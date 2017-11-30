import numpy as np

from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.wrappers import Response


app = Flask(__name__, instance_relative_config=True)
app.config["DEBUG"] = False

app.config.from_pyfile('config.py')
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Sensor(db.Model):

    __tablename__ = "sensors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(4096))
    measurements = db.relationship('Measurement', backref='sensors', lazy=True)
    creation = db.Column(db.Time())


class Measurement(db.Model):

    __tablename__ = "measurements"

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('sensors.id'), nullable=False)
    value = db.Column(db.Float)
    measure_time = db.Column(db.DateTime)
    def __init__(self):
        self.measure_time = datetime.now()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("main.html", sensors=Sensor.query.all())

    #sensor = Sensor(name=request.form['contents'])
    #sensor.creation = datetime.now()
    #db.session.add(sensor)
    #db.session.commit()

    return redirect(url_for('index'))

@app.route("/meas/<int:sensor_id>", methods=["GET", "POST"])
def measurement(sensor_id):
    if request.method == "GET":
        s = Sensor.query.get(sensor_id)
        m = Measurement.query.filter_by(sensor_id=sensor_id)
        return render_template("measurement.html", sensor=s, measurements=m)

    elif request.method == "POST":
        value = request.values.get('value', np.nan)
        print(float(value))
        # m = Measurement()
        # m.value=float(value)
        # m.sensor_id=sensor_id
        # db.session.add(m)
        # db.session.commit()
        return redirect(url_for('index'))

@app.route("/plot/<int:sensor_id>")
def measurement_plot(sensor_id):
    import io
    import matplotlib
    matplotlib.rc('xtick', labelsize=15)
    matplotlib.rc('ytick', labelsize=15)

    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure

    from matplotlib.dates import DateFormatter

    sensor = Sensor.query.get(sensor_id)
    measurements = Measurement.query.filter_by(sensor_id=sensor_id).order_by(Measurement.measure_time.desc()).limit(2000)
    t = []
    v = []
    for m in measurements:
        t.append(m.measure_time)
        v.append(m.value)

    fig = Figure()
    fig.set_size_inches(18.5, 10.5)
    ax = fig.add_subplot(111)
    ax.plot_date(t, v, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M'))
    ax.set_xlabel('Time', fontsize=20)
    ax.set_ylabel(sensor.name, fontsize=20)
    fig.autofmt_xdate()
    canvas = FigureCanvas(fig)
    png_output = io.BytesIO()
    canvas.print_png(png_output)
    response = make_response(png_output.getvalue())

    response.headers['Content-Type'] = 'image/png'

    return response



if __name__ == '__main__':
    app.run('0.0.0.0', 8080, False)
    app.debug = True