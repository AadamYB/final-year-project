from flask import Flask
from flask import request
from flask import json

app = Flask(__name__)

@app.route('/')
def api_root():
    return "Server is running and receiving events!"

@app.route('/events', methods = ['POST'])
def api_events():
    # event_data = request.get_json()
    # return json.jsonify({"message": "Webhook received!"}), 200
    # if request.headers['Content-Type'] == 'application/json':
    #     event_data = request.get_json()
    #     print(event_data)
    #     return json.jsonify(event_data), 200
    event = request.json
    if event:
        title = event.get('pull_request', {}).get('title')
        print("Received Webhook event: " , title)
        return json.dumps(event), 200
    return json.dumps({"message": "No event data received"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
