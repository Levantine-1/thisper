#!/bin/bash
# This script triggers a Jenkins job through Thisper and polls the job status until it's complete.
# The script uses the following environment variables:
#   1. url: The Jenkins URL
#   2. service_name: The service name
#   3. trigger_path: The Jenkins job trigger path
#   4. poll_path: The Jenkins job poll path
# The script uses the following secrets (encrypted environment variables):
#   1. JENKINS_AUTH_KEY: The Jenkins authentication key

# Although this script can be deployed in any repo, it is primarily maintained in the Thisper repository.
# https://github.com/Levantine-1/thisper
# And then it is copied to other github repositories as needed in the github actions workflow directory.

# This script was written in bash because the github runner is a linux machine and has curl installed by default.
# It was originally going to be written in python, but I could not be certain that the github runner would have
# the python modules I needed. And I didn't want to install them in the github runner if I needed to.

trigger_jenkins_job(){
  data='{"auth_usr": "github", "auth_key": "'"${JENKINS_AUTH_KEY}"'", "services": "'"${service_name}"'"}'
  header='Content-Type: application/json'
  job_id=$(eval curl --request POST --location "${url}/${trigger_path}" --header "'"${header}"'" --data "'"${data}"'" --silent)
  echo "${job_id}" # Return the job ID
}

poll_job_status(){
  job_id=$1
  timeout=600  # Timeout in seconds (e.g., 10 minutes)
  start_time=$(date +%s)

  url="${url}/${poll_path}"
  data='{"auth_usr": "github", "auth_key": "'"${JENKINS_AUTH_KEY}"'", "services": "'"${service_name}"'", "job_id": "'"${job_id}"'"}'
  header='Content-Type: application/json'

  echo "$poll_path - $service_name - jenkinsJobID: $job_id started, monitoring job status ..."
  while true; do
    rc=$(eval curl --request GET --location "${url}" --header "'"${header}"'" --data "'"${data}"'" -w "%{http_code}" -o /dev/null --silent)
    if [[ $rc -eq 200 ]]; then
      echo "Job completed successfully, outputting logs ..."
      eval curl --request GET --location "${url}" --header "'"${header}"'" --data "'"${data}"'" --silent
      break
    elif [[ $rc -eq 202 ]]; then
      echo "Job in progress, please wait ..."
    elif [[ $rc -eq 503 ]]; then
      echo "Thisper did not respond. This could be because Thisper is restarting in the case of a deployment."
      echo "If this continues, please check the Thisper service."
    else
      echo "Unknown error, server returned HTTP status code: ${rc} - Retrying ..."
    fi

    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [[ $elapsed_time -ge $timeout ]]; then
      eval curl --request GET --location "${url}" --header "'"${header}"'" --data "'"${data}"'" --silent
      echo "Timeout reached. Job didn't finish within the specified time."
      exit 1
    fi
    sleep 5
  done
}

main(){
  job_id=$(trigger_jenkins_job)
  poll_job_status "${job_id}"
}

main