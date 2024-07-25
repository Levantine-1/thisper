environment = "prod"

# AWS Configs
region = "us-west-2"

# HashiCorp Vault Configs
vault_address = "http://vault.internal.levantine.io:8200"
# NOTE: The vault token is currently added manually to the config file. This will be replaced with a more secure method in the future.
vault_token = "<token>"

# DataGateway Get API Key URL
data_gateway_get_api_key_url = "http://kube-c-00.internal.levantine.io:30080/generateToken"
data_gateway_token_request_email = "thisper@prod.levantine.io"
data_gateway_token_vault_path = "kv/k8clusters/DataGatewayK8Cluster/thisperAPIKey"

# Hosted zone IDs of the root account for subdomain delegation for this account
levantine_io_hosted_zone_id = "Z32CDTOFAQVLJJ"