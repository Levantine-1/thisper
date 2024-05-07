# THISPER
Telephone + Whisper = Thisper

Thisper is a Python-flask based web application that serves as an interface to interact with Jenkins jobs. The application is designed to monitor and return the status of specific Jenkins jobs, such as deploying a container or running Terraform.

I created this because I did not want to expose jenkins to the internet, and I didn't like how the API token is passed in at the URL level.

This way the token can be stored in the message body, so it's protected by SSL encryption between GitHub actions and the Thisper service. Thisper and Jenkins exist on the same network, so it should be a bit safer.

## Functionality

The application exposes a route that accepts a job type and job ID as parameters. The job type can be either `deployContainer` or `runTerraform`. The application then constructs a URL to the Jenkins job's API and makes a GET request to retrieve the job's status. If the job is in progress, it returns a message indicating so. If the job is not in progress, it retrieves and returns the console text of the job.

## Deployment

The application is deployed using GitHub Actions, as defined in the `.github/workflows/deploy.yml` file. The deployment process involves applying Terraform templates, building and pushing a Docker container to Amazon ECR, and deploying the container.

## Development

The application is developed in Python and uses pip for package management. It can be run locally using the command `python thisper.py`, and it will be available at `http://0.0.0.0:5000`.

