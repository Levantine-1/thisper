import json
import logging
import os
from datetime import datetime

import requests
from flask import Flask, request, make_response
from flask_cors import CORS

data_gateway_url = os.getenv('DATA_GATEWAY_URL')
data_gateway_token = os.getenv('DATA_GATEWAY_API_KEY')

app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "http://levantine.io"}})
CORS(app)


@app.route('/', methods=['GET'])
def default_response():
    response = "Hello! I am alive! Please check the documentation for the correct usage of thisper at: https://github.com/Levantine-1/thisper"
    return response


@app.route('/.well-known/acme-challenge/<token>', methods=['GET'])
def acme_challenge(token):
    app.logger.info("ACME Challenge accepted: " + token)
    return token


@app.route('/analytics', methods=['POST'])
def record_analytics():  # Just forward the json data to the data gateway
    url = data_gateway_url + "/analytics"
    incoming_data = request.get_json()
    if incoming_data is None:
        return make_response("No data received", 400)

    # Inject more data into the incoming data json
    incoming_data['timedate'] = str(datetime.now().strftime('%Y%m%d.%H%M%S'))
    incoming_data['ip_addr'] = str(request.remote_addr)

    payload = json.dumps(incoming_data)
    headers = {
        'Authorization': data_gateway_token,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    flask_response = make_response(response.content, response.status_code)
    # flask_response.headers['Content-Type'] = response.headers['Content-Type'] # The upstream data gateway does not return a content-type header at this time.
    return flask_response


if __name__ == '__main__':  # These steps will only run if the app is started manually like "/bin/python thisper.py"
    # Anything defined here will be ignored by gunicorn
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
