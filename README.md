# Checkmk Lurk

A script to get data from Checkmk via Livestatus and send it to an API.

# Installation
## 1. Clone Repository 
Cloning is very easy and only requires one step on most of linux devices:
`git clone https://github.com/vwt-digital/ns-checkmk-lurk.git `  
## 2. Edit config
In the config we can do a couple important things like adding the servers and adding the oauth tokens.
### Add a server
In the config we can add the servers which we want te be monitored. There is a slight diffrence between local and remote servers. Just add the servers like the below example

```
SITES = [
    {"name": "SiteName1", "address": "/omd/sites/<site_name>/tmp/run/live", "certificate": None}, # Local namesocket
    {"name": "SiteName2", "address": ("127.0.0.1", 6557), "certificate": "./certs/cert.pem"}, # External site with TLS
    {"name": "SiteName3", "address": ("127.0.0.1", 6557), "certificate": None} # External site without TLS
]
```
*NOTE:  If you have multiple sites on the same host be sure to use different ports for the livestatus connection, and list them seperatly in the server list.*

### Add oauth details
Add the oauth details to te below variables

    OAUTH_CLIENT_ID = ""  
    OAUTH_CLIENT_SECRET = ""  
    OAUTH_CLIENT_SCOPE = ""  
    OAUTH_TOKEN_URL = ""

### Event time
Events made within this time frame will be collected, the time is in seconds so 300 is 5 minutes
`EVENT_TIME = 300` 

## 3. Rename and rights
Now you finished making the config u have to complete the following steps in order to run the script.

1. Change the config.py.example to config.py
2. chmod +x ./setup.sh

## 4. Run the setup

`./setup.sh`
