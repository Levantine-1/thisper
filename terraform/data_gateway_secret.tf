variable "data_gateway_get_api_key_url" {}

data "http" "get_api_key" {
  url = var.data_gateway_get_api_key_url
  request_method = "POST"
  request_headers = {
    Content-Type = "application/json"
  }
  request_body = jsonencode({
    "email": "thisper@levantine.io"
  })
}

locals {
  api_key = try(data.http.get_api_key.response_body, "")
}

resource "vault_generic_secret" "store_data_gateway_api_key" {
  path = "kv/k8clusters/DataGatewayK8Cluster/thisperAPIKey"
  data_json = <<EOT
{
  "api_key": "${local.api_key}"
}
EOT
}