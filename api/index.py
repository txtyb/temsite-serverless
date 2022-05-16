from flask import Flask, request, jsonify, Response
from flask_cors import CORS, cross_origin
from time import time
from datetime import datetime, timedelta, timezone
import json, redis, os, requests


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
    [data['time'], data['tem'], data['rh'], data['warning']] = [timestamp, tem, rh, 0]
    # print(data)
    # if over the warning limit then post
    warningValues = r.get('warningValues')
    if warningValues is not None:
        warningValues = warningValues.decode('utf-8')
        warningValues = json.loads(warningValues)
        [temWarningValue, rhWarningValue] = [warningValues['tem'], warningValues['rh']]
        temFlag = 0
        rhFlag = 0

        if temWarningValue:
            if data['tem'] >= temWarningValue:
                temFlag = 1
        if rhWarningValue:
            if data['rh'] >= rhWarningValue:
                rhFlag = 1
        
        if (temFlag or rhFlag):
            # set data warning prop to 1
            data['warning'] = 1
            # send a warning notification
            sendtofcm(innerSend=1, rowDataTem=data['tem'], rowDataRh=data['rh'], datetime=to_datetime(timestamp), temFlag=temFlag, rhFlag=rhFlag, temWarningValue=temWarningValue, rhWarningValue=rhWarningValue)

    nowdata = list()
    try:
        oldjson = r.get('data').decode('utf-8')
        old = json.loads(oldjson)
        # if only have one data
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


def updateDataWarningProp(tem, rh):
    jsondata = r.get('data')
    if json is None:
        return
    else:
        data = list()
        jsondata = jsondata.decode('utf-8')
        data = json.loads(jsondata)

        for i in data:
            if (tem and rh) is not None:
                flag = ((i['tem'] >= tem) or (i['rh'] >= rh))
            elif ((tem is None) and (rh is not None)):
                flag = (i['rh'] >= rh)
            elif ((rh is None) and (tem is not None)):
                flag = (i['tem'] >= tem)
            else:
                flag = 0
                
            if flag:
                i['warning'] = 1
            else: 
                i['warning'] = 0
        
        r.set('data', json.dumps(data))
        return


@app.route('/api/setWarningValues', methods=['GET'])
def setWarningValues():
    tem = request.args.get('tem', type=float, default=None)
    rh = request.args.get('rh', type=float, default=None)
    dictData = {
        'tem': tem, 
        'rh': rh
    }
    r.set('warningValues', json.dumps(dictData))

    # update data warning prop
    updateDataWarningProp(tem, rh)

    return jsonify(dictData)


@app.route('/api/getWarningValues', methods=['GET'])
def getWarningValues():
    warningValues =  r.get('warningValues')
    dictData =  {
        'tem': None, 
        'rh': None
    }
    if warningValues is not None:
        warningValues = warningValues.decode('utf-8')
        warningValues = json.loads(warningValues)

        if warningValues['tem'] is not None:
            dictData['tem'] = warningValues['tem']
        if warningValues['rh'] is not None:
            dictData['rh'] = warningValues['rh']
    
    return jsonify(dictData)

# set warning flags. If the tem or rh is higher than flag, then temWarning or rhWarning == 1
@app.route('/api/clearWarningValues', methods=['GET'])
def clearWarningValues():
    r.delete('warningValues')

    # update data warning prop
    updateDataWarningProp(None, None)

    return 'OK'


@app.route('/api/get', methods=['GET'])
def get():
    data = list()
    # return time in timestamp by default
    ts = True
    if request.args.get('ts', type=str) in {'False', 'false', '0'}:
        ts = False
    # return n couples of data, default 50
    n = request.args.get('n', type=int, default=None)

    jsondata = r.get('data')
    if jsondata is None:
        return 'Empty'
    jsondata = jsondata.decode('utf-8')

    data = json.loads(jsondata)

    if n:
        if n < len(data):
            data = data[-n:]
    
    # change timestamp to datetime if not ts
    if not ts:
        for i in data:
            i['time'] = to_datetime(i['time'])
    return jsonify(data)


@app.route('/api/del', methods=['GET'])
def deldata():
    r.delete('data')
    r.delete('warningindex')
    return 'OK'


@app.route('/api/gettem', methods=['GET'])
def gettem():
    try:
        jsondata = get().data
    except AttributeError:
        return jsonify([])
    data = json.loads(jsondata)

    # whether to return timestamp
    ts = False
    if request.args.get('ts', type=str) in {'true', 'True', '1'}:
        ts = True

    # temdata = str()
    temlist = list()
    for i in data:
        if ts:
            time = i['time']
        else:
            time = to_datetime(i['time'])
        temlist.append([time, i['tem']])
    # temdata = repr(temlist)
    return jsonify(temlist)


@app.route('/api/getrh', methods=['GET'])
def getrh():
    try:
        jsondata = get().data
    except AttributeError:
        return jsonify([])
    data = json.loads(jsondata)

    # whether to return timestamp
    ts = False
    if request.args.get('ts', type=str) in {'true', 'True', '1'}:
        ts = True
        
    # rhdata = str()
    rhlist = list()
    for i in data:
        if ts:
            time = i['time']
        else:
            time = to_datetime(i['time'])
        rhlist.append([time, i['rh']])
    # rhdata = repr(rhlist)
    return jsonify(rhlist)


# deprecated method
# return a list of indexes, the data with these indexes should be highlighted
# exp: [0, 3, 5]
@app.route('/api/getWarningIndex', methods=['GET'])
def getWarningIndex():
    # read
    data = list()

    jsondata = r.get('warningindex')
    if jsondata is None:
        return 'Empty'
    jsondata = jsondata.decode('utf-8')
    
    data = json.loads(jsondata)
    return jsonify(data)


# deprecated method
@app.route('/api/setWarningIndex', methods=['GET'])
def setWarningIndex():
    setValue = request.args.get('set', type=int, default=None)
    # set
    if setValue is not None:
        try:
            oldjson = r.get('warningindex').decode('utf-8')
            data1 = json.loads(oldjson)
        except AttributeError:
            data1 = list()
        data1.append(setValue)
        r.set('warningindex', json.dumps(data1))
        return jsonify(setValue)


# deprecated method
@app.route('/api/clearWarningIndex', methods=['GET'])
def clearWarningIndex():
    r.delete('warningindex')
    return 'OK'


@app.route('/api/sendtofcm', methods=['POST'])
def sendtofcm(innerSend=None, rowDataTem=None, rowDataRh=None, datetime=None, temFlag=0, rhFlag=0, temWarningValue=None, rhWarningValue=None):
    url = 'https://fcm.googleapis.com/fcm/send'
    authorization = 'key=AAAASwElybY:APA91bFaTT_zKLcLYqB0soW8PJmFFG7x1F3wiR0MGta9lLsU22uAVa0VD_3zzz-OremJKDEWEf52OD554byamcwAmZldgrQKfwAjjbhZz_5DYT-z1gcflUBFSWVQQ9lSE9KwDBNHULvfVKmQwxa7xNwuPHz-VfdTbw'
    token = None
    tmp = r.get('fcmToken')
    if tmp:
        token = tmp.decode('utf-8') 
    if innerSend:
        warningMsg = '%s%s'%('温度过高！' if temFlag else '', ' 湿度过高！' if rhFlag else '')
        warningValueMsg = '您的%s%s'%('温度限制为%.1f℃'%(temWarningValue) if temWarningValue else '', ' 湿度限制为%.1fRh%%'%(rhWarningValue) if rhWarningValue else '')
        body = '{ "to": "%s", "time_to_live": 60, "priority": "high", "data": { "text": { "title": "%s", "message": "%s 温度: %.1f℃, 湿度: %.1fRh%% %s", "clipboard": false } } }'%(token, datetime, warningMsg, rowDataTem, rowDataRh, warningValueMsg)
        headers = {
            # 'Content-Type': 'application/json', 
            'Authorization': authorization 
        }
        response = requests.post(url, headers=headers, json=json.loads(body))
        # print(response.text)
        return
    else:
        body = request.json
        authorization = request.headers.get('Authorization', type=str)
        headers = {
            'Authorization': authorization
        }
        response = requests.post(url, headers=headers, json=body)
        return jsonify(response.text), response.status_code


@app.route('/api/setFcmToken', methods=['GET'])
def setFcmToken():
    token = request.args.get('token', type=str, default=None)
    if token:
        r.set('fcmToken', token)
    return jsonify({
        'msg': 'success', 
        'token': token
    })


@app.route('/api/clearFcmToken', methods=['GET'])
def clearFcmToken():
    r.delete('fcmToken')
    return 'OK'


if __name__ == "__main__": 
    app.run()
