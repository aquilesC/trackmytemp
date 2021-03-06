from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for, make_response
from flask_sqlalchemy import SQLAlchemy

import json
import plotly
import time
import numpy as np

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

@app.route("/sens/<int:sensor_id>")
def show_sensor(sensor_id):
    s = Sensor.query.get(sensor_id)
    return render_template("sensor.html", sensor=s)

@app.route("/meas/<int:sensor_id>", methods=["GET", "POST"])
def measurement(sensor_id):
    if request.method == "GET":
        s = Sensor.query.get(sensor_id)
        m = Measurement.query.filter_by(sensor_id=sensor_id)
        return render_template("measurement.html", sensor=s, measurements=m)

    elif request.method == "POST":
        value = request.values.get('value', np.nan)
        m = Measurement()
        m.value=float(value)
        m.sensor_id=sensor_id
        db.session.add(m)
        db.session.commit()
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

@app.route("/new_plot/<int:sensor_id>")
def new_plot(sensor_id):
    sensor = Sensor.query.get(sensor_id)
    last_24_hours = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()-24*60*60))
    measurements = Measurement.query.filter_by(sensor_id=sensor_id).filter(Measurement.measure_time >= last_24_hours).order_by(Measurement.measure_time.desc())
    t = []
    v = []
    for m in measurements:
        t.append(m.measure_time)
        v.append(m.value)

    last_time = t[0]
    average_value = np.mean(v[:5])
    graphs = [
        dict(
            data=[
                dict(
                    x=t,
                    y=v,
                    type='scatter',
                ),
            ],
            layout=dict(
                title=sensor.name
            )
        ),
    ]

    # Add "ids" to each of the graphs to pass up to the client
    # for templating
    ids = [sensor.name]

    # Convert the figures to JSON
    # PlotlyJSONEncoder appropriately converts pandas, datetime, etc
    # objects to their JSON equivalents
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('new_plot.html',
                           ids=ids,
                           graphJSON=graphJSON,
                           sensor = sensor,
                           last_time = last_time,
                           average_value = average_value)

@app.route("/range_plot/<int:sensor_id>")
def range_plot(sensor_id):
    import plotly.plotly as py
    import plotly.graph_objs as go

    sensor = Sensor.query.get(sensor_id)
    measurements = Measurement.query.filter_by(sensor_id=sensor_id).order_by(Measurement.measure_time.desc())
    t = []
    v = []
    for m in measurements:
        t.append(m.measure_time)
        v.append(m.value)

    last_time = t[0]
    average_value = np.mean(v[:5])

    trace = go.Scatter(x=t, y=v)
    data = [trace]
    last_24_hours = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()-24*60*60))
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    layout = dict(
        title='{} Values'.format(sensor.name),
        xaxis=dict(
            range=list([last_24_hours, now]),
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label='1d',
                         step='day',
                         stepmode='backward'),
                    dict(count=7,
                         label='1w',
                         step='day',
                         stepmode='backward'),
                    dict(count=1,
                         label='1m',
                         step='month',
                         stepmode='backward'),
                    dict(step='all')
                ]),
            ),
            rangeslider={'visible':True,
                         'bgcolor':"#f8faaa",},
            type='date',
        )
    )

    fig = dict(data=data, layout=layout)
    plot_div = plotly.offline.plot(fig, include_plotlyjs=True, output_type='div')


    # Add "ids" to each of the graphs to pass up to the client
    # for templating
    ids = [sensor.name]

    return render_template('range_plot.html',
                           ids=ids,
                           plot_div=plot_div,
                           sensor = sensor,
                           last_time = last_time,
                           average_value = average_value)


if __name__ == '__main__':
    app.run('0.0.0.0', 8080, False)
    app.debug = True
