#!/bin/bash
# This script triggers a Jenkins job through Thisper and polls the job status until it's complete.
# The script takes two arguments:
#   1. The URL path to trigger the Jenkins job
#   2. The URL path to poll the job status
# The script uses the following environment variables:
#   1. url: The Jenkins URL
#   2. service_name: The service name
# The script uses the following secrets:
#   1. JENKINS_AUTH_KEY: The Jenkins authentication key

# Although this script can be deployed in any repo, it is primarily maintained in the Thisper repository.
# https://github.com/Levantine-1/thisper
# And then it is copied to other github repositories as needed in the github actions workflow directory.

# This script was written in bash because the github runner is a linux machine and has curl installed by default.
# It was originally going to be written in python, but I could not be certain that the github runner would have
# the python modules I needed. And I didn't want to install them in the github runner if I needed to.

trigger_jenkins_job(){
  url_path=$1
  data="{\"auth_usr\": \"github\", \"auth_key\": \"${{ secrets.JENKINS_AUTH_KEY }}\", \"service_name\": \"${{ env.service_name }}\"}"
  header='Content-Type: application/json'
  job_id=$(curl --request POST --location "${{ env.url }}/${url_path}" --header "${header}" --data "${data}" --silent)
  echo "${job_id}" # Return the job ID
}

poll_job_status(){
  job_id=$1
  poll_url_path=$2
  timeout=600  # Timeout in seconds (e.g., 10 minutes)
  start_time=$(date +%s)

  url="${{ env.url }}/${poll_url_path}"
  data="{\"auth_usr\": \"github\", \"auth_key\": \"${{ secrets.JENKINS_AUTH_KEY }}\", \"service_name\": \"${{ env.service_name }}\", \"job_id\": \"${job_id}\"}"
  rc_params="-w \"%{http_code}\" -o /dev/null"
  header='Content-Type: application/json'

  while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [[ $elapsed_time -ge $timeout ]]; then
      echo "Timeout reached. Job didn't finish within the specified time."
      curl --request GET --location "${url}" --header "${header}" --data "${data}" --silent
      exit 1
    fi

    rc=$(curl --request GET --location "${url}" --header "${header}" --data "${data}" "${rc_params}" --silent)
    if [[ $rc -eq 202 ]]; then
      echo "Job in progress, please wait ..."
    elif [[ $rc -eq 200 ]]; then
      echo "Job completed successfully, outputting logs ..."
      curl --request GET --location "${url}" --header "${header}" --data "${data}" --silent
      break
    else
      echo "Job failed. Check Jenkins logs for more information."
      curl --request GET --location "${url}" --header "${header}" --data "${data}" --silent
      exit 1
    fi
  done
}

main(){
  trigger_url_path=$1
  poll_url_path=$2

  job_id=$(trigger_jenkins_job "${trigger_url_path}")
  poll_job_status "${job_id}" "${poll_url_path}"
}

main "$@"