import argparse
import json
import logging
import ssl
import time
import config
import requests
import socket

from ast import literal_eval


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
        logging.info(f"LIVESTATUS | Timeout Error, site with address {address} is possibly offline.")
        return None
    except ConnectionRefusedError:
        logging.info(f"LIVESTATUS | Connection Refused Error, site with address {address} is possibly offline.")
        return None
    except ssl.SSLCertVerificationError:
        logging.info(f"LIVESTATUS | Certificate Verification Error, site with address {address} with certificate "
                     f"{certificate}.")
        return None

    sock.send(query.encode("utf-8"))

    data = []
    while len(data) == 0 or data[-1] != b'':
        data.append(sock.recv(4096))
    sock.close()

    return "".join(item.decode("utf-8") for item in data)


def get_data_web_api(domain, site, action, username, secret, ca_certificate):
    url = f"https://{domain}/{site}/check_mk/webapi.py?action={action}&_username={username}&_secret={secret}" \
          f"&output_format=json"
    try:
        return requests.get(url, verify=(True if not ca_certificate else ca_certificate)).json()
    except requests.exceptions.SSLError:
        logging.info(f"WEB API | SSL Error, site ({site}) with domain {domain} with certificate {ca_certificate}.")
        return None
    except requests.exceptions.ConnectionError:
        logging.info(f"WEB API | Connection Error, site ({site}) with domain {domain} is possibly offline.")
        return None
    except json.decoder.JSONDecodeError:
        logging.info(f"WEB API | JSON Decode Error, site ({site}) with domain {domain} is giving unexpected output "
                     f"that's unparsable. Please check your username and secret.")
        return None


def send_data(path, data, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    request = requests.post(config.API_URL + path,
                            json=data,
                            headers=headers)

    logging.info(f"Sent data to API. Response status code: {request.status_code}")

    return request.status_code == 201


def convert_int_or_float(value):
    try:
        return literal_eval(value)
    except SyntaxError:
        return value
    except ValueError:
        return value


def parse_perf_data(data):
    ret = []

    variables = data.split(" ")

    for variable in variables:
        var_name = variable.split("=")[0]
        var_value = variable.split("=")[1]

        values = var_value.split(";")

        if len(values) == 5:
            ret.append({
                "var_name": var_name,
                "actual": convert_int_or_float(values[0]),
                "warning": convert_int_or_float(values[1]),
                "critical": convert_int_or_float(values[2]),
                "min": convert_int_or_float(values[3]),
                "max": convert_int_or_float(values[4]),
            })
        else:
            ret.append({
                "var_name": var_name,
                "actual": convert_int_or_float(values[0])
            })

    return ret


def do_events():
    # Get events
    events = {"events": []}
    keys = ["id", "name", "timestamp", "type", "hostname", "service_description", "state_type", "output", "long_output",
            "event_state"]

    # Foreach site get event data and add to events dict
    for site in config.SITES:
        result = get_data("GET log\n"
                          f"Filter: time >= {int(time.time() - config.EVENT_TIME)}\n"
                          "Filter: host_name != ""\n"
                          "Columns: time type host_name service_description state_type plugin_output "
                          "long_plugin_output state\n"
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
    logging.info(f"Sending {len(events['events'])} events to API.")
    send_data("/checkmk-events", events, get_oath_token())


def do_performance():
    # Get performance data
    services = {"services": []}
    keys = ["id", "name", "timestamp", "host_groups", "hostname", "service_description", "perf_data", "service_state"]

    for site in config.SITES:
        result = get_data("GET services\n"
                          "Filter: host_name != ""\n"
                          "Filter: perf_data != ""\n"
                          "Filter: perf_data != null\n"
                          "And: 3\n"
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
            dic["perf_data"] = parse_perf_data(dic["perf_data"]) if dic["perf_data"] != "" else dic["perf_data"]

            services["services"].append(dic)

    # Send services
    logging.info(f"Sending {len(services['services'])} services to API.")
    send_data("/checkmk-performances", services, get_oath_token())


def do_hosts():
    hosts = {"hosts": []}

    for site in config.SITES:
        # Get hosts
        output = get_data_web_api(site["web-domain"], site["name"], "get_all_hosts", site["username"], site["secret"],
                                  site["ca-certificate"])

        # Parse hosts
        if output:
            for host in output["result"]:

                hosts["hosts"].append(
                    {
                        "id": site["name"] + "_" + host,
                        "name": site["name"],
                        "hostname": host,
                        "hostgroups": json.loads(get_data("GET hosts\nColumns: groups\nOutputFormat: json\n\n",
                                                          site["address"],
                                                          site["certificate"]
                                                          ))[0][0],
                        "address": site["web-domain"]
                    }
                )

                for var in output["result"][host]["attributes"]:
                    hosts["hosts"][len(hosts["hosts"]) - 1][var] = output["result"][host]["attributes"][var]

    # Send hosts
    logging.info(f"Sending info from {len(hosts['hosts'])} hosts to API.")
    send_data("/checkmk-hosts", hosts, get_oath_token())


# Main function of the script
def main():
    # Construct argument parser
    ap = argparse.ArgumentParser()
    logging.basicConfig(
        filename=config.LOGGING_FILE,
        level=logging.DEBUG if config.LOGGING_DEBUG else logging.INFO,
        format='%(asctime)s %(levelname)s\t| %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S')

    # Add the arguments to the parser
    ap.add_argument("-data", "--data", required=True, help="Select which data to retrieve: event / performance / host")
    args = vars(ap.parse_args())

    # Check which data should be retrieved
    if args['data'] == "event":
        logging.info("Retrieving event data.")
        do_events()
    elif args['data'] == "performance":
        logging.info("Retrieving performance data.")
        do_performance()
    elif args['data'] == "host":
        logging.info("Retrieving host data.")
        do_hosts()
    else:
        logging.info("Invalid argument is specified.")


if __name__ == "__main__":
    main()
