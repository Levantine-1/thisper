import json
from flask import Flask, request, make_response
import requests
import logging
import re
import time

jenkins_server = "jenkins.internal.levantine.io"
app = Flask(__name__)


def check_jenkins_server():
    try:
        response = requests.get("http://" + jenkins_server)
        if response.status_code == 403:  # 403 is the expected response from Jenkins as it requires authentication
            return True
        else:
            app.logger.error("Jenkins server did not respond with a 403 status code.")
            return False
    except requests.exceptions.ConnectionError:
        app.logger.error("Jenkins server is not reachable.")
        return False


@app.route('/', methods=['GET'])
def default_response():
    response = "Hello and welcome! Please use the /build endpoint to trigger a Jenkins job."
    return response


@app.route('/.well-known/acme-challenge/<token>', methods=['GET'])
def acme_challenge(token):
    app.logger.info("ACME Challenge accepted: " + token)
    return token


def run_jenkins_job(url):
    try:
        requests.post(url)
        job_id = get_job_id(url)
        if job_id == 0:
            msg = "Thisper timed out waiting for Jenkins job to start."
            response = make_response(msg, 500)
            return response
        response = make_response(job_id, 200)
    except requests.exceptions.ConnectionError:
        warning_msg = "Jenkins host may not have been configured correctly"
        app.logger.warning(warning_msg)
        response = make_response(warning_msg, 500)
    except json.decoder.JSONDecodeError as e:
        app.logger.error(e)
        msg = ("Unknown Jenkins error, check parameters: 'services' and 'auth_key' in github workflow configs."
               "If that's not it, check job url path in thisper")
        app.logger.error(msg)
        response = make_response(msg, 500)
    return response


def get_job_id(url):
    pattern = r'(.*?)/buildWithParameters.*'
    job_url = re.sub(pattern, r'\1', url)
    lastest_build_url = job_url + "/lastBuild/api/json"

    max_tries = 30  # 30 tries every 1 second = ~30 seconds
    app.logger.info("Waiting for Jenkins job to start...")

    inprogress = False
    while inprogress is not True and max_tries > 0:
        app.logger.debug("Checking Jenkins job status. Remaining tries: " + str(max_tries) + "... ")
        try:
            lastest_job = requests.get(lastest_build_url)
            inprogress = lastest_job.json()['inProgress']

            if inprogress is True:
                job_id = lastest_job.json()['id']
                app.logger.info("Jenkins job started. Build ID: " + job_id)
                return job_id
        except Exception as e:
            app.logger.warning(e)
            app.logger.warning("An error occurred while trying to get the job id. Retrying...")

        time.sleep(1)
        max_tries -= 1
    err_msg = "Thisper timed out waiting for Jenkins job to start."
    app.logger.error(err_msg)
    return 0  # A Jenkins job ID is always a positive integer, so 0 is a safe return value for an error


def sanitize_inputs(**data):
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized_value = value.strip().replace('/', '')
            sanitized_data[key] = sanitized_value
        elif isinstance(value, list):
            sanitized_list = [item.strip().replace('/', '') for item in value]
            sanitized_data[key] = sanitized_list
        else:
            sanitized_data[key] = value

    if 'auth_key' in sanitized_data and len(sanitized_data['auth_key']) < 34:
        app.logger.warning("Possible invalid Jenkins auth key")

    return sanitized_data


# Pass in the following parameters:
#   <job_id> = name of jenkins job
#   <auth_key> = Jenkins api authorization key
@app.route('/deploy_container', methods=['POST'])
def deploy_container():
    if not check_jenkins_server():
        return "Jenkins server is not reachable.", 500
    data = request.get_json()
    sanitized_data = sanitize_inputs(**data)

    required_fields = ['auth_usr', 'auth_key', 'services']
    if any(field not in sanitized_data for field in required_fields):
        return "Invalid request data.", 400

    auth_usr = sanitized_data['auth_usr']
    auth_key = sanitized_data['auth_key']
    services = sanitized_data['services']

    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/DeployContainer/buildWithParameters?services=" + services
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    response = run_jenkins_job(url)
    return response


@app.route('/poll_deploy_job_status', methods=['GET'])
def poll_deploy_job_status():
    data = request.get_json()
    sanitized_data = sanitize_inputs(**data)

    required_fields = ['auth_usr', 'auth_key', 'services', 'job_id']
    if any(field not in sanitized_data for field in required_fields):
        return "Invalid request data.", 400

    auth_usr = sanitized_data['auth_usr']
    auth_key = sanitized_data['auth_key']
    services = sanitized_data['services']
    job_id   = sanitized_data['job_id']

    url              = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/DeployContainer/" + job_id + "/api/json"
    console_text_url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/DeployContainer/" + job_id + "/consoleText"
    status = requests.get(url)
    inprogress = status.json()['inProgress']
    if inprogress is True:
        msg = "Job in progress"
        response = make_response(msg, 202)
        return response
    else:
        response = requests.get(console_text_url)
        flask_response = make_response(response.content)
        flask_response.headers['Content-Type'] = response.headers['Content-Type']
        return flask_response


@app.route('/run_terraform', methods=['POST'])
def run_terraform():
    if not check_jenkins_server():
        return "Jenkins server is not reachable.", 500
    data = request.get_json()
    sanitized_data = sanitize_inputs(**data)

    required_fields = ['auth_usr', 'auth_key', 'services']
    if any(field not in sanitized_data for field in required_fields):
        return "Invalid request data.", 400

    auth_usr = sanitized_data['auth_usr']
    auth_key = sanitized_data['auth_key']
    services = sanitized_data['services']

    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/terraform/job/terraform_" + services + "/buildWithParameters?COMMAND=apply -auto-approve --var-file=./vars/&VAR_FILE=production.tfvars"
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    response = run_jenkins_job(url)
    return response


@app.route('/poll_terraform_job_status', methods=['GET'])
def poll_terraform_job_status():
    data = request.get_json()
    sanitized_data = sanitize_inputs(**data)

    required_fields = ['auth_usr', 'auth_key', 'services', 'job_id']
    if any(field not in sanitized_data for field in required_fields):
        return "Invalid request data.", 400

    auth_usr = sanitized_data['auth_usr']
    auth_key = sanitized_data['auth_key']
    services = sanitized_data['services']
    job_id   = sanitized_data['job_id']

    url              = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/terraform/job/terraform_" + services + "/" + job_id + "/api/json"
    console_text_url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/terraform/job/terraform_" + services + "/" + job_id + "/consoleText"
    status = requests.get(url)
    inprogress = status.json()['inProgress']
    if inprogress is True:
        msg = "Please wait, job still in progress..."
        response = make_response(msg, 202)
        return response
    else:
        response = requests.get(console_text_url)
        flask_response = make_response(response.content)
        flask_response.headers['Content-Type'] = response.headers['Content-Type']
        return flask_response


if __name__ == '__main__':  # These steps will only run if the app is started manually like "/bin/python thisper.py"
    # Anything defined here will be ignored by gunicorn
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
