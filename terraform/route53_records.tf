

resource "aws_route53_record" "configure_bastion_r53_record_levantine_io" {
  zone_id = data.aws_route53_zone.local_env_levantine_io.zone_id
  name    = "thisper.${var.environment}.levantine.io"
  type    = "A"
  ttl     = 300
  records = [data.aws_instance.bastion_instance.public_ip]
}