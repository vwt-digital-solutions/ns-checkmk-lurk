# Checkmk Lurk

A script to get data from Checkmk via Livestatus and send it to an API.

# Installation
## 1. Clone Repository 
Cloning is very easy and only requires one step on most of linux devices:
`git clone https://github.com/vwt-digital-solutions/ns-checkmk-lurk.git `  
## 2. Edit config
In the config file you will specify where Checkmk Lurk needs to obtain it's data from and where it should be send to.
### Add a server
In the config we can add the servers where we want to get the data from. In the example below is shown how to configure the script when using external servers with or without TLS and how to configure it for sites that use the namesocket.

The site certificates for livestatus are located here `etc/ssl/sites/[site].pem`. 

``web-domain``, ``username``, ``secret`` and ``ca-certificate`` are all used for the web API from Checkmk. If you don't want to use any external CA certificates set ``ca-certificate`` to ``None``.

You can find your user secret here: ``$OMD_ROOT/var/check_mk/web/<USERNAME>/<USERNAME>.secret`` where ``<USERNAME>`` is the username of the user.
```
SITES = [
    {"name": "SiteName1", "address": "/omd/sites/slave1/tmp/run/live", "certificate": None, "web-domain": "localhost",
    "username": "automation", "secret": "secret-key", "ca-certificate": None},  # Local namesocket

    {"name": "SiteName2", "address": ("127.0.0.1", 6557), "certificate": "./certs/cert.pem", "web-domain": "main.server.com",
    "username": "automation", "secret": "secret-key", "ca-certificate": "./certs/ca-certificates.crt"},  # External site with TLS

    {"name": "SiteName3", "address": ("127.0.0.1", 6557), "certificate": None, "web-domain": "127.0.0.1",
    "username": "automation", "secret": "secret-key", "ca-certificate": "./certs/ca-certificates.crt"}  # External site without TLS
]
```
*NOTE:  If you have multiple sites on the same host be sure to use different ports for the livestatus connection, and list them seperatly in the server list.*

### API url
This is the url of the API where the data will be send to.

`API_URL = ""`

### Add OAuth details
These are used to obtain the bearer token which is used as authorization method to connect with the API.

    OAUTH_CLIENT_ID = ""  
    OAUTH_CLIENT_SECRET = ""  
    OAUTH_CLIENT_SCOPE = ""  
    OAUTH_TOKEN_URL = ""

### Event time
Events made within this time frame will be collected, the time is in seconds so 300 is 5 minutes.

`EVENT_TIME = 300` 

### Logging
It is also possible to select the logging level and where the logs should be stored to.

This is where you should specify the logfile. 

`LOGGING_FILE = ""`

Set this boolean to True or False depending on if you want debug log level enabled or not.

`LOGGING_DEBUG = True`

## 3. Rename and rights
Once the configuration file is configured correctly you need to run the following commands.

1. Set executable permissions to the setup file `chmod +x ./setup.sh`.
2. Change the config name `mv ./lurk/config.py.example ./lurk/config.py`.

## 4. Run the setup
This will setup the crontabs, install the python modules and change the config file name.

`./setup.sh`
