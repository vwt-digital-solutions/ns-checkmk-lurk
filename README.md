[![CodeFactor](https://www.codefactor.io/repository/github/vwt-digital-solutions/ns-checkmk-lurk/badge)](https://www.codefactor.io/repository/github/vwt-digital-solutions/ns-checkmk-lurk)

# Checkmk Lurk

This repository contains two scripts; a script to get data from Checkmk via Livestatus and send it to an API and a script that sends the notifications produced by Checkmk to an API.

# Installation

## Pre-setup
Every step should be executed with the OMD admin account. The account name is the same as the site name in which Checkmk resides.
It can be found in the folder `/OMD/sites`. When using Linux switching to this user can be done with the following command:
`sudo su omd-admin-accountname -`.
## 1. Get latest version
The [tags](https://github.com/vwt-digital-solutions/ns-checkmk-lurk/tags) show the latest version of the scripts. There are two ways to get the latest version.
### Via code
Use the following to get the right tag via code:
```
git clone https://github.com/vwt-digital-solutions/ns-checkmk-lurk.git
cd ns-checkmk-lurk
git fetch --all --tags
latest_tag=$(git describe --tags `git rev-list --tags --max-count=1`)
git checkout $latest_tag
```

### Via UI
Click on the last made tag and download the source code. Unzip the downloaded folder and it is ready to go.

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

### Host data location
We need to save host data of each site so that we can check if a site has been decommissioned or not. You need to specify in the variable below in which directory the files need to be created. 

*NOTE: The user running the crontab needs to have writing permissions to the specified directory.*

`HOST_FILE_STORAGE = "./hosts"`

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
2. Change the config name `mv ./lurk/config.py.example ./lurk/config.py` and fill in the config according to 
[section 2](https://github.com/vwt-digital-solutions/ns-checkmk-lurk#2-edit-config).
3. Change the permissions of the config so that no other users can access it
 `chmod 600 ./lurk/config.py`.

## 4. Run the setup
This will setup the crontabs and install the python modules.

`./setup.sh`

## 5. Setup notifications
When the setup has run, the steps on the
 [checkmk site](https://docs.checkmk.com/latest/en/notifications.html) have to be followed to setup the
 notifications with the installed script. For the `Notification Method` choose `Notifications to ODH`.
