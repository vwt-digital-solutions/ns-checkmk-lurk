#!/bin/bash

# Function for exiting script when pip is not installed.
function no_pip {
  echo -e "python3-pip is not installed, run apt-get install python3-pip, and try again!"
  exit	
}

# Function for installing the event crontab.
function install_event_cron {
  echo "Event crontab not yet installed..."

  # Write new crontab file.
  crontab -l > checkmk-lurk-event

  # Write entries to file.
  echo "# Crontab for retrieving event data every minute" >> checkmk-lurk-event
  echo "* * * * * /usr/bin/env python3 $(pwd)/lurk/checkmk_lurk.py --data event" >> checkmk-lurk-event

  # Install new crontab.
  crontab checkmk-lurk-event
  rm checkmk-lurk-event

  echo "Event crontab installed!"
}

# Function for installing the performance crontab.
function install_perf_cron {
  echo "Performance crontab not yet installed..."

  # Write new crontab file.
  crontab -l > checkmk-lurk-perf

  # Write entries to file.
  echo "# Crontab for retrieving performance data every 5 minutes" >> checkmk-lurk-perf
  echo "*/5 * * * * /usr/bin/env python3 $(pwd)/lurk/checkmk_lurk.py --data performance" >> checkmk-lurk-perf

  # Install new crontab.
  crontab checkmk-lurk-perf
  rm checkmk-lurk-perf

  echo "Performance crontab installed!"
}

# Function for installing the host crontab.
function install_host_cron {
  echo "Host crontab not yet installed..."

  # Write new crontab file.
  crontab -l > checkmk-lurk-host

  # Write entries to file.
  echo "# Crontab for retrieving host data every day" >> checkmk-lurk-host
  echo "0 0 * * * /usr/bin/env python3 $(pwd)/lurk/checkmk_lurk.py --data performance" >> checkmk-lurk-host

  # Install new crontab.
  crontab checkmk-lurk-host
  rm checkmk-lurk-host

  echo "Host crontab installed!"
}

# Check if python3-pip is installed if not install it.
echo "checking if python3-pip is installed"
dpkg -l | grep -qw python3-pip || no_pip

# Install the pip requirements.
echo "installing the python requirements ..."
python3 -m pip install -r requirements.txt

echo "Checking if crontabs are already installed ..."

# Check for performance data crontab.
if crontab -l | grep "$(pwd)/lurk/checkmk_lurk.py --data performance" -q;
then
  echo "Performance crontab already installed!"
else
  install_perf_cron
fi

# Check for event data crontab.
if crontab -l | grep "$(pwd)/lurk/checkmk_lurk.py --data event" -q;
then
  echo "Event crontab already installed!"
else
  install_perf_cron
fi

# Check for host data crontab.
if crontab -l | grep "$(pwd)/lurk/checkmk_lurk.py --data host" -q;
then
  echo "Host crontab already installed!"
else
  install_host_cron
fi

mv ./lurk/config.py.example ./lurk/config.py

echo "Setup completed!"
