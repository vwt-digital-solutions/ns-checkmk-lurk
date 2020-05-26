#!/bin/bash

# check if python3-pip is installed
# if not, install it
echo "checking if python3-pip is installed"
sudo dpkg -l | grep -qw python3-pip || sudo apt-get install python3-pip

# installing the requirements
echo "installing the python requirements ..."
sudo python3 -m pip install -r requirements.txt

echo "installing crontabs ..."
# Write out current crontab
crontab -l > checkmk-lurk

# echo new cron lines into cron file
echo "*/5 * * * * /usr/bin/env python3 $(pwd)/script/checkmk-lurk.py --data performance" >> checkmk-lurk
echo "* * * * * /usr/bin/env python3 $(pwd)/script/checkmk-lurk.py --data event" >> checkmk-lurk

# install new cron
crontab checkmk-lurk
rm checkmk-lurk

echo "setup completed!"
