from flask import Flask, request
import requests
import logging
import re
import time

jenkins_server = "jenkins.internal.levantine.io"
app = Flask(__name__)

@app.before_first_request
def startup_code():
    app.logger.setLevel(logging.INFO)


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
        job_console_text_url, ec = wait_for_jenkins_job(url)
        response_text = requests.get(job_console_text_url).text
        response = response_text, ec
    except requests.exceptions.ConnectionError:
        warning_msg = "Jenkins host may not have been configured correctly"
        app.logger.warning(warning_msg)
        response = warning_msg, ec = 500
    return response, ec


def wait_for_jenkins_job(url):
    pattern = r'(.*?)/buildWithParameters.*'
    job_url = re.sub(pattern, r'\1', url)
    last_build_url = job_url + "/lastBuild/api/json"

    last_job = requests.get(last_build_url)
    job_id = last_job.json()['id']
    job_url = job_url + "/" + job_id
    job_console_text_url = job_url + "/consoleText"

    inprogress = True
    max_tries = 120  # 120 tries every 5 seconds = 10 minutes
    while inprogress != "false" and max_tries > 0:
        last_job = requests.get(job_url + "/api/json")
        inprogress = last_job.json()['inProgress']
        max_tries -= 1
        if inprogress == "false":
            if last_job.json()['result'] == "SUCCESS":
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
    data = request.get_json()
    auth_usr, auth_key, services = sanitize_inputs(data)
    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/DeployContainer/buildWithParameters?services=" + services
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    response, ec = run_jenkins_job(url)
    return response, ec

@app.route('/run_terraform', methods=['POST'])
def run_terraform():
    data = request.get_json()
    auth_usr, auth_key, services = sanitize_inputs(data)
    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/terraform/terraform_" + services + "/buildWithParameters?COMMAND=apply -auto-approve --var-file=./vars/&VAR_FILE=production.tfvars"
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    response, ec = run_jenkins_job(url)
    return response, ec


if __name__ == '__main__':  # These steps will only run if the app is started manually like "/bin/python thisper.py"
    # Anything defined here will be ignored by gunicorn
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
