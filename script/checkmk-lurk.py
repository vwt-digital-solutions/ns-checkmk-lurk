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

    return request.status_code == 200

