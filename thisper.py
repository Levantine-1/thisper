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
        response = wait_for_jenkins_job(url)
        console_text = requests.get(response[0]).text
        status_code = response[1]
        response = make_response(console_text, status_code)
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


def wait_for_jenkins_job(url):
    time.sleep(10)  # Jenkins takes a few seconds to start the job and while a race condition is possible, it's not likely.
    # But since I don't anticipate a high volume of requests, I'm not going to worry about it for now,
    # and keep it stupid simple with a sleep timer

    pattern = r'(.*?)/buildWithParameters.*'
    job_url = re.sub(pattern, r'\1', url)
    last_build_url = job_url + "/lastBuild/api/json"

    last_job = requests.get(last_build_url)
    job_id = last_job.json()['id']
    job_url = job_url + "/" + job_id
    job_console_text_url = job_url + "/consoleText"

    inprogress = True
    max_tries = 120  # 120 tries every 5 seconds = 10 minutes
    app.logger.info("Waiting for Jenkins job to complete. Build ID: " + job_id)
    while inprogress is not False and max_tries > 0:
        app.logger.debug("Checking Jenkins job status. Remaining tries: " + str(max_tries) + "... ")
        last_job = requests.get(job_url + "/api/json")
        inprogress = last_job.json()['inProgress']
        max_tries -= 1
        if inprogress is False:
            if last_job.json()['result'].lower() == "success":
                app.logger.info("Job Completed Successfully")
                return job_console_text_url, 200
            else:
                app.logger.error("Job Failed")
                return job_console_text_url, 500
        time.sleep(5)
    app.logger.error("Thisper timed out waiting for Jenkins job to complete.")
    return job_console_text_url, 500


def sanitize_inputs(data):
    auth_key = data['auth_key'].strip()
    auth_usr = data['auth_usr'].strip()
    services = data['services'].strip()

    if len(auth_key) < 34:
        app.logger.warning("Invalid Auth Key")
        auth_key = "Invalid_Key"

    # Sanitize Inputs
    auth_usr = auth_usr.replace('/', '')
    auth_key = auth_key.replace('/', '')
    services = services.replace('/', '')
    return auth_usr, auth_key, services

# Pass in the following parameters:
#   <job_id> = name of jenkins job
#   <auth_key> = Jenkins api authorization key
@app.route('/deploy_container', methods=['POST'])
def deploy_container():
    if not check_jenkins_server():
        return "Jenkins server is not reachable.", 500
    data = request.get_json()
    auth_usr, auth_key, services = sanitize_inputs(data)
    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/DeployContainer/buildWithParameters?services=" + services
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    if services == "thisper":
        requests.post(url)
        message = "Deploying thisper requires thisper to restart so there will be no console output for this specifc service."
        response = make_response(message, 200)
    else:
        response = run_jenkins_job(url)
    return response

@app.route('/run_terraform', methods=['POST'])
def run_terraform():
    if not check_jenkins_server():
        return "Jenkins server is not reachable.", 500
    data = request.get_json()
    auth_usr, auth_key, services = sanitize_inputs(data)
    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/terraform/job/terraform_" + services + "/buildWithParameters?COMMAND=apply -auto-approve --var-file=./vars/&VAR_FILE=production.tfvars"
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    response = run_jenkins_job(url)
    return response


if __name__ == '__main__':  # These steps will only run if the app is started manually like "/bin/python thisper.py"
    # Anything defined here will be ignored by gunicorn
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
