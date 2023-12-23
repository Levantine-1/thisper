from flask import Flask, request
import requests
import logging
import socket
import subprocess

jenkins_server = "jenkins.internal.levantine.io"
app = Flask(__name__)

@app.before_first_request
def startup_code():
    app.logger.setLevel(logging.INFO)


@app.route('/', methods=['GET'])
def default_response():
    response = "There will be a health check soon, for now just send things to /build"
    return response


@app.route('/.well-known/acme-challenge/<token>', methods=['GET'])
def acme_challenge(token):
    app.logger.info("ACME Challenge accepted: " + token)
    return token


# Pass in the following parameters:
#   <job_id> = name of jenkins job
#   <auth_key> = Jenkins api authorization key
@app.route('/build', methods=['POST'])
def make_request():
    data = request.get_json()
    job = data['job_id'].strip()  # Get data from request
    auth_key = data['auth_key'].strip()
    auth_usr = data['auth_usr'].strip()
    services = data['services'].strip()

    if len(auth_key) < 34:
        app.logger.warning("Invalid Auth Key")
        auth_key = "Invalid_Key"

    # Sanitize Inputs
    job = job.replace('/', '')  # No slashes as it's passed in as an url parameter so at risk for url hijack
    auth_usr = auth_usr.replace('/', '')
    auth_key = auth_key.replace('/', '')
    services = services.replace('/', '')

    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/" + job + "/buildWithParameters?services=" + services
    app.logger.info(url.replace(auth_key, '<REDACTED>'))

    try:
        response = requests.post(url)
    except requests.exceptions.ConnectionError:
        warning_msg = "Jenkins host may not have been configured correctly"
        app.logger.warning(warning_msg)
        response = warning_msg
    return response.text if hasattr(response, 'text') else response


if __name__ == '__main__':  # These steps will only run if the app is started manually like "/bin/python thisper.py"
    # Anything defined here will be ignored by gunicorn
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
