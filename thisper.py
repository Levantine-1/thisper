import json
from flask import Flask, request, make_response, jsonify
import requests
import logging
import re
import time
import os

jenkins_server = os.getenv('JENKINS_SERVER')
data_gateway_url = os.getenv('DATA_GATEWAY_URL')
data_gateway_token = os.getenv('DATA_GATEWAY_TOKEN')

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
    response = "Hello! I am alive! Please check the documentation for the correct usage of thisper at: https://github.com/Levantine-1/thisper"
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
        except json.decoder.JSONDecodeError as e:
            app.logger.error(e)
            app.logger.error("Error, Jenkins job may not exist, please check the URL path in the deployment workflow. Check the string concatenation.")
            break
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


def check_required_fields(request_data, required_fields):
    missing_fields = [field for field in required_fields if field not in request_data]
    if missing_fields:
        message = f"Missing required fields: {', '.join(missing_fields)}"
        return False, message
    else:
        return True, None


@app.route('/trigger_jenkins_job', methods=['POST'])
def trigger_jenkins_job():
    if not check_jenkins_server():
        return "Jenkins server is not reachable.", 500
    request_data = request.get_json()
    sanitized_data = sanitize_inputs(**request_data)

    required_fields = ['auth_usr', 'auth_key', 'services', 'job_type']
    checked_data_is_valid, message = check_required_fields(sanitized_data, required_fields)
    if not checked_data_is_valid:
        return make_response(message, 400)

    auth_usr = sanitized_data['auth_usr']
    auth_key = sanitized_data['auth_key']
    services = sanitized_data['services']
    job_type = sanitized_data['job_type']

    if job_type == "deployContainer":
        url_path = "/job/DeployContainer/buildWithParameters?services=" + services
    elif job_type == "runTerraform":
        url_path = "/job/terraform/job/terraform_" + services + "/buildWithParameters?COMMAND=apply -auto-approve --var-file=./vars/&VAR_FILE=production.tfvars"
    else:
        msg = "Invalid job type:" + job_type
        response = make_response(msg, 400)
        return response

    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + url_path
    app.logger.info(url.replace(auth_key, '<REDACTED>'))
    response = run_jenkins_job(url)
    return response


@app.route('/monitor_jenkins_job', methods=['GET'])
def monitor_jenkins_job():
    data = request.get_json()
    sanitized_data = sanitize_inputs(**data)

    required_fields = ['auth_usr', 'auth_key', 'services', 'job_type', 'job_id']
    check_data_is_valid, message = check_required_fields(sanitized_data, required_fields)
    if not check_data_is_valid:
        return make_response(message, 400)

    auth_usr = sanitized_data['auth_usr']
    auth_key = sanitized_data['auth_key']
    services = sanitized_data['services']
    job_type = sanitized_data['job_type']
    job_id   = sanitized_data['job_id']

    if job_type == "deployContainer":
        url_path = "/job/DeployContainer/" + job_id
    elif job_type == "runTerraform":
        url_path = "/job/terraform/job/terraform_" + services + "/" + job_id
    else:
        msg = "Invalid job type:" + job_type
        response = make_response(msg, 400)
        return response

    monitor_job_url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + url_path + "/api/json"
    console_txt_url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + url_path + "/consoleText"

    status = requests.get(monitor_job_url)
    inprogress = status.json()['inProgress']
    if inprogress is True:
        msg = "Job in progress"
        response = make_response(msg, 202)
        return response
    else:
        build_result = status.json()['result']
        if build_result == "SUCCESS":
            app.logger.info(job_type + "Build: " + job_id + " completed successfully")
            return_code = 200
        else:
            app.logger.error(job_type + "Build: " + job_id + " failed")
            return_code = 500

        response = requests.get(console_txt_url)
        flask_response = make_response(response.content, return_code)
        flask_response.headers['Content-Type'] = response.headers['Content-Type']
        return flask_response


# def get_vault_secret(secret_path):
#     response = hvault_client.secrets.kv.v2.read_secret_version(path=secret_path)
#     print(response)
#     return response

@app.route('/analytics', methods=['POST'])
def record_analytics():
    url = data_gateway_url + "/analytics"

    payload = json.dumps({
        "ipAddr": "192.168.1.1",
        "timedate": "2023-10-01T14:30:00",
        "request": "GET /api/data",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    headers = {
        'Authorization': data_gateway_token,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    return ""



if __name__ == '__main__':  # These steps will only run if the app is started manually like "/bin/python thisper.py"
    # Anything defined here will be ignored by gunicorn
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
