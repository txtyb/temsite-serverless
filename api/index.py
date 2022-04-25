from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from time import time
import json, redis, os

REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PORT = os.environ['REDIS_PORT']
REDIS_PASSWD = os.environ['REDIS_PASSWD']

# DEBUG = True
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWD)

app = Flask(__name__)

cors = CORS(app)

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
    try:
        jsondata = r.get('data').decode('utf-8')
    except AttributeError:
        return "Empty"
    data = json.loads(jsondata)
    return jsonify(data)


@app.route('/api/del', methods=['GET'])
def deldata():
    r.delete('data')
    return 'OK'


@app.route('/api/gettem', methods=['GET'])
def gettem():
    jsondata = r.get('data').decode('utf-8')
    data = json.loads(jsondata)
    temdata = str()
    tmplist = list()
    for i in data:
        tmplist.append([i['time'], i['tem']])
    temdata = repr(tmplist)
    return temdata


if __name__ == "__main__": 
    app.run()
