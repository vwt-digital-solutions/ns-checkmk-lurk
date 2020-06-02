#!/bin/bash

# function for exiting script when pip is not installed
function no_pip {
  echo -e "\e[31mpython3-pip is not installed, run apt-get install python3-pip, and try again!\e[0m" 
  exit	
}

# function for installing the event crontab
function install_event_cron {
  echo "event crontab not yet installed ..."

  # write new crontab file
  crontab -l > checkmk-lurk-event

  #write entry's to file
  echo "# Crontab for retrieving event data every minute" >> checkmk-lurk-event
  echo "* * * * * /usr/bin/env python3 $(pwd)/script/checkmk-lurk.py --data event" >> checkmk-lurk-event

  # install new cron
  crontab checkmk-lurk-event
  rm checkmk-lurk-event

  echo "event crontab installed!"
}

# function for installing the performance crontab
function install_perf_cron {
  echo "performance crontab not yet installed ..."

  # write new crontab file
  crontab -l > checkmk-lurk-perf

  #write entry's to file
  echo "# Crontab for retrieving performance data every 5 minutes" >> checkmk-lurk-perf
  echo "*/5 * * * * /usr/bin/env python3 $(pwd)/script/checkmk-lurk.py --data performance" >> checkmk-lurk-perf

  # install new cron
  crontab checkmk-lurk-perf
  rm checkmk-lurk-perf

  echo "performance crontab installed!"
}

# check if python3-pip is installed
# if not, install it
echo "checking if python3-pip is installed"
dpkg -l | grep -qw python3-pip || no_pip

# installing the requirements
echo "installing the python requirements ..."
python3 -m pip install -r requirements.txt

echo "Checking if crontabs are already installed ..."

# check for performance data crontab
crontab -l | grep $(pwd)'/script/checkmk-lurk.py --data performance' && echo "performance crontab already installed!" || install_perf_cron
# check for event data crontab
crontab -l | grep $(pwd)'/script/checkmk-lurk.py --data event' && echo "event crontab already installed!" || install_event_cron

echo "setup completed!"
