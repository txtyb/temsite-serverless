from flask import Flask

DEBUG = True

app = Flask(__name__)

@app.route('/test')
def test():
    return ("<h1>Flask</h1><p>You visited: /%s" % ('test'))

@app.route('/')
def home():
    return 'Hi'

if __name__ == "__main__": 
    app.run()