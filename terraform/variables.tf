data "aws_instance" "bastion_instance" {
  filter {
    name   = "tag:Name"
    values = ["Bastion"]
  }
}

data "aws_route53_zone" "local_env_levantine_io" {
  name = "${var.environment}.levantine.io."
}