from flask import Flask, request, jsonify
from time import time
import json

# DEBUG = True

app = Flask(__name__)

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

    dump = list()
    with open('data.json', 'r') as f:
        try:
            old = json.loads(f.read())
            old.append(data)
        except json.JSONDecodeError:
            pass
    dump = old
    with open('data.json', 'w') as f:
        f.write(json.dumps(dump, indent=4))

    return jsonify(data)


@app.route('/api/get', methods=['GET'])
def get():
    data = list()
    with open('data.json', 'r') as f:
        data = json.loads(f.read())
    return jsonify(data)


if __name__ == "__main__": 
    app.run()