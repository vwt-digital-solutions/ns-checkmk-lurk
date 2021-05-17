import argparse
import json
import logging
import os
import socket
import ssl
import sys
import time
from ast import literal_eval
from copy import deepcopy
from datetime import datetime

import config
import requests
from pympler.asizeof import asizeof


def get_oath_token():
    data = {
        "client_id": config.OAUTH_CLIENT_ID,
        "client_secret": config.OAUTH_CLIENT_SECRET,
        "scope": config.OAUTH_CLIENT_SCOPE,
        "grant_type": "client_credentials",
    }
    request = requests.post(config.OAUTH_TOKEN_URL, data=data).json()

    return request["access_token"]


def get_data(query, address, certificate):
    family = socket.AF_INET if isinstance(address, tuple) else socket.AF_UNIX
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
    except TimeoutError:
        logging.info(
            f"LIVESTATUS | Timeout Error, site with address {address} is possibly offline."
        )
        return None
    except ConnectionRefusedError:
        logging.info(
            f"LIVESTATUS | Connection Refused Error, site with address {address} is possibly offline."
        )
        return None
    except ssl.SSLCertVerificationError:
        logging.info(
            f"LIVESTATUS | Certificate Verification Error, site with address {address} with certificate "
            f"{certificate}."
        )
        return None

    sock.send(query.encode("utf-8"))

    data = []
    while len(data) == 0 or data[-1] != b"":
        data.append(sock.recv(4096))
    sock.close()

    return "".join(item.decode("utf-8") for item in data)


def get_data_web_api(domain, site, action, username, secret, ca_certificate):
    url = (
        f"https://{domain}/{site}/check_mk/webapi.py?action={action}&_username={username}&_secret={secret}"
        f"&output_format=json"
    )
    try:
        return requests.get(
            url, verify=(True if not ca_certificate else ca_certificate)
        ).json()
    except requests.exceptions.SSLError:
        logging.info(
            f"WEB API | SSL Error, site ({site}) with domain {domain} with certificate {ca_certificate}."
        )
        return None
    except requests.exceptions.ConnectionError:
        logging.info(
            f"WEB API | Connection Error, site ({site}) with domain {domain} is possibly offline."
        )
        return None
    except json.decoder.JSONDecodeError:
        logging.info(
            f"WEB API | JSON Decode Error, site ({site}) with domain {domain} is giving unexpected output "
            f"that's unparsable. Please check your username and secret."
        )
        return None


def send_data(path, data, token):
    headers = {"Authorization": f"Bearer {token}"}

    request = requests.post(config.API_URL + path, json=data, headers=headers)

    logging.info(f"Sent data to API. Response status code: {request.status_code}")

    return request.status_code == 201


def convert_int_or_float(value):
    try:
        return literal_eval(value)
    except SyntaxError:
        return value
    except ValueError:
        return value


def get_current_timestamp():
    return int(time.time() * 1000)


def parse_perf_data(data):
    ret = []

    variables = data.split(" ")

    for variable in variables:
        if variable == "":
            continue

        var_name = variable.split("=")[0]
        var_value = variable.split("=")[1]

        values = var_value.split(";")

        if len(values) == 5:
            ret.append(
                {
                    "var_name": var_name,
                    "actual": convert_int_or_float(values[0]),
                    "warning": convert_int_or_float(values[1]),
                    "critical": convert_int_or_float(values[2]),
                    "min": convert_int_or_float(values[3]),
                    "max": convert_int_or_float(values[4]),
                }
            )
        else:
            ret.append(
                {"var_name": var_name, "actual": convert_int_or_float(values[0])}
            )

    return ret


def parse_size(data):
    mb_size = 1000000
    max_size = 8.0
    output_list = []

    if (asizeof(data) / mb_size) > max_size:
        list_name = list(data.keys())[0]
        new = {list_name: []}

        for item in data[list_name]:
            new[list_name].append(item)
            if asizeof(new) / mb_size > max_size:
                del new[list_name][-1]
                output_list.append(deepcopy(new))
                new[list_name] = [item]
        output_list.append(deepcopy(new))
        return output_list
    return [data]


def parse_old_hosts(old_hosts, new_output, site, host_list):
    # Make list of hosts that are no longer visible via the WEB API
    difference = [
        host
        for host in old_hosts
        if host not in [host for host in new_output["result"]]
    ]

    for host in difference:
        logging.info(f"Decommissioned host found: {site['name']}_{host}")

        host_list["hosts"].append(
            {
                "id": site["name"] + "_" + host,
                "name": site["name"],
                "hostname": host,
                "decommissioned": True,
                "timestamp": get_current_timestamp(),
            }
        )


def parse_host_tags(site, output, host_list, host):
    # Do check here for real tag name
    all_tags = get_data_web_api(
        site["web-domain"],
        site["name"],
        "get_hosttags",
        site["username"],
        site["secret"],
        site["ca-certificate"],
    )

    timestamp = datetime.utcnow().isoformat()
    logging.debug(
        f"[time:{timestamp}] [action:get_hosttags] [webDomain:{site['web-domain']}] [siteName:{site['name']}] "
        + f"[host:{host}] {json.dumps(output['result'][host]['attributes'])}"
    )  # Debug logging

    for var in output["result"][host]["attributes"]:
        if all_tags:
            value = output["result"][host]["attributes"][var]

            real_name = next(
                (
                    tag
                    for tag in all_tags["result"]["tag_groups"]
                    if tag["id"] == var.strip("tag_")
                ),
                None,
            )
            if real_name:
                real_value = next(
                    (val for val in real_name["tags"] if val["id"] == value), None
                )

                host_list["hosts"][len(host_list["hosts"]) - 1][var] = {
                    "value": value,
                    "realname": real_name["title"],
                    "realvalue": real_value["title"],
                }
            else:
                host_list["hosts"][len(host_list["hosts"]) - 1][var] = {
                    "value": output["result"][host]["attributes"][var]
                }
        else:
            host_list["hosts"][len(host_list["hosts"]) - 1][var] = {
                "value": output["result"][host]["attributes"][var]
            }


def do_events():
    # Get events
    events = {"events": []}
    keys = [
        "id",
        "name",
        "timestamp",
        "type",
        "hostname",
        "service_description",
        "state_type",
        "output",
        "long_output",
        "event_state",
    ]

    # Foreach site get event data and add to events dict
    for site in config.SITES:
        result = get_data(
            "GET log\n"
            f"Filter: time >= {int(time.time() - config.EVENT_TIME)}\n"
            "Filter: host_name != "
            "\n"
            "Columns: time type host_name service_description state_type plugin_output "
            "long_plugin_output state\n"
            "OutputFormat: json\n\n",
            site["address"],
            site["certificate"],
        )

        timestamp = datetime.utcnow().isoformat()
        logging.debug(
            f"[time:{timestamp}] [action:get_all_events] [webDomain:{site['web-domain']}] "
            + f"[siteName:{site['name']}] {json.dumps(result)}"
        )  # Debug logging

        if not result:
            continue

        result = json.loads(result)

        for event_list in result:
            event_list.insert(0, site["name"])
            event_list.insert(0, "temp_id")

            dic = dict(zip(keys, event_list))

            dic[
                "id"
            ] = f"{site['name']}_{dic['timestamp']}_{dic['hostname']}_{dic['service_description']}"
            dic["timestamp"] = dic["timestamp"] * 1000

            events["events"].append(dic)

    # Send events
    size_parsed = parse_size(events)

    for events in size_parsed:
        logging.info(f"Sending {len(events['events'])} events to API.")
        send_data("/checkmk-events", events, get_oath_token())


def do_performance():
    # Get performance data
    services = {"services": []}
    keys = [
        "id",
        "name",
        "timestamp",
        "host_groups",
        "hostname",
        "service_description",
        "perf_data",
        "service_state",
    ]

    for site in config.SITES:
        result = get_data(
            "GET services\n"
            "Filter: host_name != "
            "\n"
            "Filter: perf_data != "
            "\n"
            "Filter: perf_data != null\n"
            "And: 3\n"
            "Columns: host_groups host_name service_description perf_data state\n"
            "OutputFormat: json\n\n",
            site["address"],
            site["certificate"],
        )

        timestamp = datetime.utcnow().isoformat()
        logging.debug(
            f"[time:{timestamp}] [action:get_all_performances] [webDomain:{site['web-domain']}] "
            + f"[siteName:{site['name']}] {json.dumps(result)}"
        )  # Debug logging

        if not result:
            continue

        result = json.loads(result)

        for service_list in result:
            service_list.insert(0, int(time.time()))
            service_list.insert(0, site["name"])
            service_list.insert(0, "temp_id")

            dic = dict(zip(keys, service_list))

            dic[
                "id"
            ] = f"{site['name']}_{dic['timestamp']}_{dic['hostname']}_{dic['service_description']}"
            dic["timestamp"] = dic["timestamp"] * 1000
            dic["perf_data"] = (
                parse_perf_data(dic["perf_data"])
                if dic["perf_data"] != ""
                else dic["perf_data"]
            )

            services["services"].append(dic)

            # After each 50th message, check if byte size is not more than 50000; else post towards API and start again
            if (
                len(services["services"]) % 50 == 0
                and sys.getsizeof(str(services)) > 500000
            ):
                logging.info(f"Sending {len(services['services'])} services to API.")
                send_data("/checkmk-performances", services, get_oath_token())
                services = {"services": []}

        if len(services["services"]) > 0:
            logging.info(f"Sending {len(services['services'])} services to API.")
            send_data("/checkmk-performances", services, get_oath_token())


def do_hosts():
    hosts = {"hosts": []}
    changed_hosts = {}

    for site in config.SITES:
        # Get hosts
        output = get_data_web_api(
            site["web-domain"],
            site["name"],
            "get_all_hosts",
            site["username"],
            site["secret"],
            site["ca-certificate"],
        )

        # Parse hosts
        if output:
            changed_hosts[site["name"]] = output["result"]

            # Check if there are hosts gone (decommissioned)
            # Load old hosts
            try:
                with open(
                    config.HOST_FILE_STORAGE + f"/{site['name']}.json"
                ) as json_file:
                    old_hosts = json.load(json_file)
            except FileNotFoundError:
                old_hosts = None

            if old_hosts:
                parse_old_hosts(old_hosts, output, site, hosts)

            for host in output["result"]:
                timestamp = datetime.utcnow().isoformat()
                logging.debug(
                    f"[time:{timestamp}] [action:get_all_hosts] [webDomain:{site['web-domain']}] "
                    + f"[siteName:{site['name']}] [host:{host}] {json.dumps(output['result'][host])}"
                )  # Debug logging

                hosts["hosts"].append(
                    {
                        "id": site["name"] + "_" + host,
                        "name": site["name"],
                        "hostname": host,
                        "hostgroups": json.loads(
                            get_data(
                                "GET hosts\nColumns: groups\nOutputFormat: json\n\n",
                                site["address"],
                                site["certificate"],
                            )
                        )[0][0],
                        "address": site["web-domain"],
                        "decommissioned": False,
                        "timestamp": get_current_timestamp(),
                    }
                )

                parse_host_tags(site, output, hosts, host)

    # Send hosts
    size_parsed = parse_size(hosts)

    for hosts in size_parsed:
        logging.info(f"Sending info from {len(hosts['hosts'])} hosts to API.")
        sent = send_data("/checkmk-hosts", hosts, get_oath_token())

        if sent and output:
            # Data is successfully sent so now the host files can be updated to their current state
            for site in changed_hosts:
                # After deleted hosts are correctly added, update the file with host information
                with open(config.HOST_FILE_STORAGE + f"/{site}.json", "w+") as file:
                    json.dump(changed_hosts[site], file)


# Main function of the script
def main():
    # Construct argument parser
    ap = argparse.ArgumentParser()
    logging.basicConfig(
        filename=config.LOGGING_FILE,
        level=logging.DEBUG if config.LOGGING_DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s\t| %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )

    # Do checks if config.py is properly configured and if user running script is owner of config
    current_user = os.geteuid()
    file_info = os.stat(os.path.dirname(os.path.realpath(__file__)) + "/config.py")
    permissions = int(oct(file_info.st_mode)[-3:])

    if current_user != file_info.st_uid:
        logging.info(
            "User running the script isn't the owner of config.py. "
            "Please change the ownership or run under different user."
        )
        return 1
    if permissions != 600:
        logging.info(
            f"Config.py has wrong file permissions. Please change them to 600. Current file permissions: "
            f"{permissions}"
        )
        return 1

    # Add the arguments to the parser
    ap.add_argument(
        "-data",
        "--data",
        required=True,
        help="Select which data to retrieve: event / performance / host",
    )
    args = vars(ap.parse_args())

    # Check which data should be retrieved
    if args["data"] == "event":
        logging.info("Retrieving event data.")
        do_events()
    elif args["data"] == "performance":
        logging.info("Retrieving performance data.")
        do_performance()
    elif args["data"] == "host":
        logging.info("Retrieving host data.")
        do_hosts()
    else:
        logging.info("Invalid argument is specified.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
