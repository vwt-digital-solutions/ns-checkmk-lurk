#!/usr/bin/env python3
# Notifications to ODH

import os
import sys
import requests
import importlib.util

omd_root = os.environ.get("OMD_ROOT")
spec = importlib.util.spec_from_file_location("config", f"{omd_root}/ns-checkmk-lurk/lurk/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def get_oath_token():
    data = {
        "client_id": config.OAUTH_CLIENT_ID,
        "client_secret": config.OAUTH_CLIENT_SECRET,
        "scope": config.OAUTH_CLIENT_SCOPE,
        "grant_type": "client_credentials"
    }
    request = requests.post(config.OAUTH_TOKEN_URL,
                            data=data).json()

    return request["access_token"]


def send_data(path, data, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    request = requests.post(config.API_URL + path,
                            json=data,
                            headers=headers)

    sys.stdout.write(f"Sent data to API. Response status code: {request.status_code}\n")

    return request.status_code == 201


# All the notification information can be found in the environment variables starting with "NOTIFY_"
notification_dict = {}
for env in os.environ:
    if "NOTIFY_" in env:
        env_var = os.environ.get(env)
        if env_var == '':
            env_var = "None"
        env_info = {env: env_var}
        notification_dict.update(env_info)

contact_name = os.environ.get("NOTIFY_CONTACTNAME")
micro_time = os.environ.get("NOTIFY_MICROTIME")
hostname = os.environ.get("NOTIFY_HOSTNAME")
notification_id_string = f"{contact_name}_{micro_time}_{hostname}"

notification_id = {"id": notification_id_string}
notification_dict.update(notification_id)

notification_data = {
    "notifications": [notification_dict]
}

sys.stdout.write("Sending data to REST API\n")

send_data("/checkmk-notifications", notification_data, get_oath_token())

sys.stdout.write("Data sent to REST API\n")
