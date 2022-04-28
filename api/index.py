from flask import Flask, request, jsonify, Response
from flask_cors import CORS, cross_origin
from time import time
from datetime import datetime, timedelta, timezone
import json, redis, os


REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PORT = os.environ['REDIS_PORT']
REDIS_PASSWD = os.environ['REDIS_PASSWD']

# DEBUG = True
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWD)

app = Flask(__name__)

cors = CORS(app)

# convert datetime from timestamp to '2020-1-1 11:11:11 +0800' etc.
def to_datetime(timestamp, tz=8):
    tz = timezone(timedelta(hours=tz))
    datetimestr = datetime.strftime(datetime.fromtimestamp(timestamp, tz=tz), '%Y-%m-%d %H:%M:%S %z')
    return datetimestr


@app.route('/test')
def test():
    return ("<h1>Flask</h1><p>You visited: /%s" % ('test'))


@app.route('/')
def home():
    return 'Hi'


@app.route('/api/put', methods=['GET'])
def put():
    data = dict()
    tem = request.args.get('tem', type=float)
    rh = request.args.get('rh', type=float)
    timestamp = int(time())
    [data['time'], data['tem'], data['rh']] = [timestamp, tem, rh]
    # print(data)

    nowdata = list()
    try:
        oldjson = r.get('data').decode('utf-8')
        old = json.loads(oldjson)
        # id only have one data
        if type(old) == dict:
            olddict = old
            old = list()
            old.append(olddict)
            old.append(data)
        else:
            old.append(data)
    # if empty
    except AttributeError:
        old = data
    
    nowdata = old
    r.set('data', json.dumps(nowdata))
    
    return jsonify(data)


@app.route('/api/get', methods=['GET'])
def get():
    data = list()
    # return n couples of data, default 50
    n = 50
    if request.args.get('n', type=int):
        n = request.args.get('n', type=int)
    try:
        jsondata = r.get('data').decode('utf-8')
    except AttributeError:
        return 'Empty'
    data = json.loads(jsondata)

    if n < len(data):
        data = data[-n:]
    return jsonify(data)


@app.route('/api/del', methods=['GET'])
def deldata():
    r.delete('data')
    return 'OK'


@app.route('/api/gettem', methods=['GET'])
def gettem():
    jsondata = get().data
    if jsondata == 'Empty':
        return jsondata
    data = json.loads(jsondata)

    # whether to return timestamp
    ts = False
    if request.args.get('ts', type=str) in {'true', 'True', '1'}:
        ts = True

    temdata = str()
    temlist = list()
    for i in data:
        if ts:
            time = i['time']
        else:
            time = to_datetime(i['time'])
        temlist.append([time, i['tem']])
    temdata = repr(temlist)
    return temdata


@app.route('/api/getrh', methods=['GET'])
def getrh():
    jsondata = get().data
    if jsondata == 'Empty':
        return jsondata
    data = json.loads(jsondata)

    # whether to return timestamp
    ts = False
    if request.args.get('ts', type=str) in {'true', 'True', '1'}:
        ts = True
        
    rhdata = str()
    rhlist = list()
    for i in data:
        if ts:
            time = i['time']
        else:
            time = to_datetime(i['time'])
        rhlist.append([time, i['rh']])
    rhdata = repr(rhlist)
    return rhdata


if __name__ == "__main__": 
    app.run()
