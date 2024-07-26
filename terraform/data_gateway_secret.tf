variable "data_gateway_get_api_key_url" {}
variable "data_gateway_token_request_email" {}
variable "data_gateway_token_vault_path" {}

data "http" "get_api_key" {
  url = var.data_gateway_get_api_key_url
  method = "POST"
  request_headers = {
    Content-Type = "application/json"
  }
  request_body = jsonencode({
    "email": var.data_gateway_token_request_email
  })
}

locals {
  api_key = try(data.http.get_api_key.response_body, "")
}

resource "vault_generic_secret" "store_data_gateway_api_key" {
  path = var.data_gateway_token_vault_path
  data_json = <<EOT
{
  "api_key": "${local.api_key}"
}
EOT
}