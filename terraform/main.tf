terraform {
  backend "s3" {
    bucket       = "prod-levantine-terraform-bucket"
    key          = "thisper/terraform.tfstate"
    region       = "us-west-2"
    use_lockfile = true
  }
}

variable "region" {}
variable "environment" {}
variable "vault_address" {}
variable "vault_token" {}
variable "levantine_io_hosted_zone_id" {}

# Still needed here (unlike portfolio, which dropped this entirely): the
# aws.delegate provider in route_53_delegate_records.tf and the
# vault_generic_secret write in data_gateway_secret.tf both genuinely use
# Vault, for reasons unrelated to this repo's own AWS auth. Only the
# *default* AWS provider below moves to OIDC.
provider "vault" {
  address = var.vault_address
  token   = var.vault_token
  # The provider's default behavior mints a short-lived child token per
  # run (for automatic revocation) via auth/token/create -- a capability
  # the CI VAULT_TOKEN secret's policy doesn't grant. Not needed here
  # anyway: this token is already scoped and rotated at the Vault side,
  # and the run is fully ephemeral.
  skip_child_token = true
}

# Auth for the default (non-delegate) AWS provider is via GitHub Actions
# OIDC role assumption (see iam_oidc_role.tf), not a long-lived
# Vault-stored static key. aws-actions/configure-aws-credentials sets
# AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN as env vars
# before terraform runs, which the AWS provider's default credential
# chain picks up automatically -- nothing to configure here.
provider "aws" {
  region = var.region
}