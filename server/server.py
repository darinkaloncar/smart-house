from flask import Flask, jsonify, request
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
import json


app = Flask(__name__)


# InfluxDB Configuration
token = "K4Q54mHR_djZ9c2iF36m2TTKHdItfU6okDIZi_D4PfS2uVJsPOvyACgISyDLb__U049H3k2PFMPekwaGH2EmRQ=="
org = "MyOrg"
url = "http://localhost:8086"
bucket = "iot-db"
influxdb_client = InfluxDBClient(url=url, token=token, org=org)

def on_message(client, userdata, msg):
    print("MQTT:", msg.topic, msg.payload)
    try:
        data = json.loads(msg.payload.decode())
        save_to_db(data)
    except Exception as e:
        print("JSON ERROR:", e)



# MQTT Configuration
mqtt_client = mqtt.Client()
mqtt_client.connect("127.0.0.1", 1883, 60)
print("Subscribing to ALL topics...")
mqtt_client.loop_start()


def on_connect(client, userdata, flags, rc):
    print("MQTT CONNECTED:", rc)
    client.subscribe("#")


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


def save_to_db(data):
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    point = (
        Point(data["measurement"])
        .tag("simulated", data["simulated"])
        .tag("runs_on", data["runs_on"])
        .tag("name", data["name"])
        .field("measurement", data["value"])
    )
    write_api.write(bucket=bucket, org=org, record=point)


# Route to store dummy data
@app.route('/store_data', methods=['POST'])
def store_data():
    try:
        data = request.get_json()
        store_data(data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def handle_influx_query(query):
    try:
        query_api = influxdb_client.query_api()
        tables = query_api.query(query, org=org)

        container = []
        for table in tables:
            for record in table.records:
                container.append(record.values)

        return jsonify({"status": "success", "data": container})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/simple_query', methods=['GET'])
def retrieve_simple_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")"""
    return handle_influx_query(query)


@app.route('/aggregate_query', methods=['GET'])
def retrieve_aggregate_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")
    |> mean()"""
    return handle_influx_query(query)


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)
