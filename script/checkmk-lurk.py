import json
import time
import os
import config
import requests
import socket


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


def get_data(query, address):
    family = socket.AF_INET if type(address) == tuple else socket.AF_UNIX
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.connect(address)

    sock.sendall(query.encode())
    sock.shutdown(socket.SHUT_WR)

    data = []
    while len(data) == 0 or data[-1] != b'':
        data.append(sock.recv(4096))
    sock.close()

    response = "".join(item.decode() for item in data)

    return response


def send_data(path, data, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    request = requests.post(config.API_URL + path,
                            json=data,
                            headers=headers)

    return request.status_code == 201


def do_events():
    # Get events
    events = {"events": []}
    keys = ["id", "name", "timestamp", "host_groups", "hostname", "service_description", "event_state"]

    # Foreach site get event data and add to events dict
    for site in config.SITES:
        result = json.loads(
            get_data("GET log\n"
                     f"Filter: time >= 1589874962\n"
                     "Filter: host_name != ""\n"
                     "Columns: time host_groups host_name service_description state\n"
                     "OutputFormat: json\n",
                     site["address"])
        )
        for event_list in result:
            site_name = os.getenv("OMD_SITE")
            event_list.insert(0, site_name)
            event_list.insert(0, "temp_id")
            dic = dict(zip(keys, event_list))
            dic["id"] = f"{site_name}_{dic['timestamp']}_{dic['hostname']}_{'event_state'}"

            events["events"].append(dic)

    # Send events
    send_data("/checkmk-event", events, get_oath_token())
