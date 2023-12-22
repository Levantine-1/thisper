from flask import Flask, request
import requests
import logging
import socket
import subprocess

jenkins_server = "jenkins.internal.levantine.io"
app = Flask(__name__)


def test_connection(host):
    try:
        # Resolve URL to an IP
        ip_address = socket.gethostbyname(host)
        app.logger.warning(f"1. URL resolved to IP: {ip_address}")

        # Determine DNS server
        dns_server = socket.gethostbyaddr(ip_address)[0]
        app.logger.warning(f"2. DNS server: {dns_server}")

        # Ping the host
        ping_result = subprocess.run(["ping", "-c", "4", host], capture_output=True)
        app.logger.warning(f"3. Ping Result:\n{ping_result.stdout.decode()}")

        # Curl the host and get return code
        try:
            response = requests.get(f"http://{host}", timeout=5)
            app.logger.warning(f"4. Curl Return Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            app.logger.warning(f"4. Curl Error: {e}")

    except socket.gaierror:
        app.logger.error("Error: Unable to resolve the URL to an IP address.")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")


@app.route('/', methods=['GET'])
def default_response():
    response = "Hello I'm alive! Please make requests to /build"
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

    # Sanitize Inputs
    job = job.replace('/', '') # No slashes as it's passed in as an url parameter so at risk for url hijack
    auth_usr = auth_usr.replace('/', '')
    auth_key = auth_key.replace('/', '')
    services = services.replace('/', '')

    url = "http://" + auth_usr + ":" + auth_key + "@" + jenkins_server + "/job/" + job + "/buildWithParameters?services=" + services
    app.logger.info(url)

    try:
        response = requests.post(url)
    except requests.exceptions.ConnectionError:
        warning_msg = "Jenkins host may not have been configured correctly"
        test_connection(host=jenkins_server)
        app.logger.warning(warning_msg)
        response = warning_msg
    return response.text if hasattr(response, 'text') else response


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=5000)
