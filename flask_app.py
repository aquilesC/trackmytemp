import os
from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["DEBUG"] = True

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="aquic",
    password=os.environ['DBPASS'],
    hostname="localhost",
    databasename="sensors",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
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
    value = db.Column(db.Integer)
    measure_time = db.Column(db.Time())
    def __init__(self):
        self.measure_time = datetime.now()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("main.html", sensors=Sensor.query.all())

    sensor = Sensor(name=request.form['contents'])
    sensor.creation = datetime.now()
    db.session.add(sensor)
    db.session.commit()

    return redirect(url_for('index'))

@app.route("/<int:sensor_id>", methods=["GET",])
def show_sensor(sensor_id):
    if request.method != "GET":
        return "Wrong Method"

    return render_template("sensor.html", sensor=Sensor.query.get(sensor_id))

@app.route("/meas/<int:sensor_id>", methods=["GET", "POST"])
def measurement(sensor_id):
    if request.method == "GET":
        s = Sensor.query.get(sensor_id)
        m = Measurement.query.filter_by(sensor_id=sensor_id)
        return render_template("measurement.html", sensor=s, measurements=m)

    elif request.method == "POST":
        value = request.form
        m = Measurement()
        m.value=value['value']
        m.sensor_id=sensor_id
        db.session.add(m)
        db.session.commit()
        return redirect(url_for('index'))




if __name__ == '__main__':
    app.run('0.0.0.0', 8080, False)
