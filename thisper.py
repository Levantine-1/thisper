from flask import Flask, request
import requests
import logging

jenkins_server = "jenkins.levantine.io"

app = Flask(__name__)


@app.route('/', methods=['GET'])
def default_response():
    response = "Hello I'm alive! Please make requests to /build"
    return response


@app.route('/build', methods=['POST'])
def make_request():
    job = request.form['job_id'].strip()  # Get data from request
    auth_key = request.form['auth_key'].strip()

    # Sanitize Inputs
    job = job.replace('/', '')
    auth_key = auth_key.replace('/', '')  # No slashes as it's passed in as an url parameter so at risk for url hijack

    url = "http://" + "github_actions_bmt:" + auth_key + "@" + jenkins_server + "/job/" + job + "/build"
    app.logger.info(url)
    response = requests.post(url)
    return response.text


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.run(port=5000)
