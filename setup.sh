#!/bin/bash

###################################
# Installing notifications script #
###################################

# Check if the config.py file exist, if not exit
if [ ! -f "$(pwd)"/lurk/config.py ]; then
    echo "Cannot find $(pwd)/lurk/config.py, exiting..."
    exit
fi

echo "Setting up notifications to ODH"
# Copy notifications script to notifications folder on checkmk
cp -f "$(pwd)"/checkmk-notifications/Notifications_to_ODH.py "$HOME"/local/share/check_mk/notifications/Notifications_to_ODH.py &&
# Copy config to notifications folder on checkmk
cp -f "$(pwd)"/lurk/config.py "$HOME"/local/share/check_mk/notifications/config.py &&
# Set executing permissions to the files
chmod +x "$HOME"/local/share/check_mk/notifications/Notifications_to_ODH.py &&
chmod +x "$HOME"/local/share/check_mk/notifications/config.py

echo "Notifications are now being send to ODH"

##################################
# Installing checkmk lurk script #
##################################

# Function for exiting script when pip is not installed.
function no_pip {
  echo -e "python3-pip is not installed, run apt-get install python3-pip, and try again!"
  exit	
}

# Function for installing the event crontab.
function install_event_cron {
  echo "Event crontab not yet installed..."

  # Write entries to file.
  echo "# Crontab for retrieving event data every minute" >> ~/etc/cron.d/checkmk_lurk_event
  echo "* * * * * /usr/bin/env python3 $(pwd)/lurk/checkmk_lurk.py --data event" >> ~/etc/cron.d/checkmk_lurk_event

  omd restart crontab

  echo "Event crontab installed!"
}

# Function for installing the performance crontab.
function install_perf_cron {
  echo "Performance crontab not yet installed..."

  # Write entries to file.
  echo "# Crontab for retrieving performance data every 5 minutes" >> ~/etc/cron.d/checkmk_lurk_perf
  echo "*/5 * * * * /usr/bin/env python3 $(pwd)/lurk/checkmk_lurk.py --data performance" >> ~/etc/cron.d/checkmk_lurk_perf

  omd restart crontab

  echo "Performance crontab installed!"
}

# Function for installing the host crontab.
function install_host_cron {
  echo "Host crontab not yet installed..."

  # Write entries to file.
  echo "# Crontab for retrieving host data every day" >> ~/etc/cron.d/checkmk_lurk_host
  echo "0 0 * * * /usr/bin/env python3 $(pwd)/lurk/checkmk_lurk.py --data host" >> ~/etc/cron.d/checkmk_lurk_host

  omd restart crontab

  echo "Host crontab installed!"
}

# Setting permissions to config
chmod 600 "$(pwd)"/lurk/config.py

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
  install_event_cron
fi

# Check for host data crontab.
if crontab -l | grep "$(pwd)/lurk/checkmk_lurk.py --data host" -q;
then
  echo "Host crontab already installed!"
else
  install_host_cron
fi

echo "Setup of checkmk lurk completed!"
