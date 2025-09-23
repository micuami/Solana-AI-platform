import boto3
import json

def get_secret(secret_name="solana_api_keys", region_name="eu-north-1"):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        raise RuntimeError(f"Error fetching secret {secret_name}: {e}")

    secret = response.get('SecretString')
    if secret:
        return json.loads(secret)
    else:
        return {}