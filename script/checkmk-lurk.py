import argparse
import json
import ssl
import time

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


def get_data(query, address, certificate):
    family = socket.AF_INET if type(address) == tuple else socket.AF_UNIX
    sock = socket.socket(family, socket.SOCK_STREAM)

    if certificate:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

        context.load_verify_locations(certificate)

        sock = context.wrap_socket(sock)

    try:
        sock.connect(address)
    # TODO if site is down send message to API notifying it that the site is down
    except TimeoutError:
        print(f"Timeout, site with address {address} is possibly offline")
        return None
    except ConnectionRefusedError:
        print(f"Connection refused, site with address {address} is possibly offline")
        return None
    except ssl.SSLCertVerificationError:
        print(f"Certificate verification error, site with address {address} with certificate {certificate}")
        return None

    sock.send(query.encode("utf-8"))

    data = []
    while len(data) == 0 or data[-1] != b'':
        data.append(sock.recv(4096))
    sock.close()

    return "".join(item.decode("utf-8") for item in data)


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
    keys = ["id", "name", "timestamp", "type", "hostname", "service_description", "state_type", "output", "long-output"]

    # Foreach site get event data and add to events dict
    for site in config.SITES:
        result = get_data("GET log\n"
                          f"Filter: time >= {int(time.time() - config.EVENT_TIME)}\n"
                          "Filter: host_name != ""\n"
                          "Columns: time type host_name service_description state_type plugin_output "
                          "long_plugin_output\n"
                          "OutputFormat: json\n\n",
                          site["address"],
                          site["certificate"])

        if not result:
            continue

        result = json.loads(result)

        for event_list in result:
            event_list.insert(0, site["name"])
            event_list.insert(0, "temp_id")

            dic = dict(zip(keys, event_list))

            dic["id"] = f"{site['name']}_{dic['timestamp']}_{dic['hostname']}_{dic['service_description']}"
            dic["timestamp"] = dic["timestamp"] * 1000

            events["events"].append(dic)

    # Send events
    send_data("/checkmk-events", events, get_oath_token())


def do_performance():
    # Get performance data
    services = {"services": []}
    keys = ["id", "name", "timestamp", "host_groups", "hostname", "service_description", "perf_data", "event_state"]

    for site in config.SITES:
        result = get_data("GET services\n"
                          "Filter: host_name != ""\n"
                          "Columns: host_groups host_name service_description perf_data state\n"
                          "OutputFormat: json\n\n",
                          site["address"],
                          site["certificate"])

        if not result:
            continue

        result = json.loads(result)

        for service_list in result:
            service_list.insert(0, int(time.time()))
            service_list.insert(0, site["name"])
            service_list.insert(0, "temp_id")

            dic = dict(zip(keys, service_list))

            dic["id"] = f"{site['name']}_{dic['timestamp']}_{dic['hostname']}_{dic['service_description']}"
            dic["timestamp"] = dic["timestamp"] * 1000

            services["services"].append(dic)

    # Send services
    send_data("/checkmk-performances", services, get_oath_token())


# Main function of the script
def main():
    # Construct argument parser
    ap = argparse.ArgumentParser()

    # Add the arguments to the parser
    ap.add_argument("-data", "--data", required=True, help="Select which data to retrieve: event / performance")
    args = vars(ap.parse_args())

    # Check which data should be retrieved
    if args['data'] == "event":
        print("Retrieving event data ...")
        do_events()
    elif args['data'] == "performance":
        print("Retrieving performance data ...")
        do_performance()
    else:
        print("Invalid input, use event / performance for the --data input")


if __name__ == "__main__":
    main()
