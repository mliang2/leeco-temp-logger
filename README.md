Logs the Leeco Pro3/Openpilot Comma Two temperature info every minute. This has been tested on Comma two running DragonPilot beta2

Requirements:
1. Enable SSH access to your comma two
1. Comfortable w/ basic Linux commands/CLI environment

WARNING: No support/warranty of any kind.  Use at your own risk!

Setting Time Zone:
1. ssh to c2 and run `setprop persist.sys.timezone "America/Los_Angeles"`

Usage:
1. If you DON'T want `leeco-temp-logger.py` to copy the csv, set `self.copy_csv_script = False`
1. If you want script to auto scp the temp data to your local server when connected to wifi:
    1. edit `leeco-temp-logger.py`: update `self.wifi_network_str` to your local network IP range
    1. edit `copy-csv.example.sh` and save it as `copy-csv.sh`
    1. setup ssh keys to allow the c2 to do passwordless scp to your server
1. scp `leeco-temp-logger.py` to `/data/data/com.termux/files/home/`
1. scp `copy-csv.sh` to `/data/data/com.termux/files/home/`
1. ssh into the comma two:
    ```
    chmod 755 /data/data/com.termux/files/home/leeco-temp-logger.py

    # run if script is set to scp csv to local server
    # install CLI tool to play a sound
    apt update
    apt install play-audio

    # Verify script can run in foreground mode.
    /data/data/com.termux/files/home/leeco-temp-logger.py -f

    # make sure command above runs and you see a new line very minute. Press control+c to stop
    # Do NOT proceed to next steps if script fails for whatever reason!

    # if script is set to scp csv to local server, verify server has file copied to it
    # should hear a notification sound when file is scp-ed
    ```
1. Start the logger script on comma two startup. ssh into the comma two:
    ```
    # backup
    cp /data/openpilot/launch_openpilot.sh /data/openpilot/launch_openpilot.sh.orig

    vi /data/openpilot/launch_openpilot.sh

    # Add the following line before the "exec ./launch_chffrplus.sh" line
    /data/data/com.termux/files/home/leeco-temp-logger.py || true

    # launch_openpilot.sh should look like this:
    export PASSIVE="0"
    /data/data/com.termux/files/home/leeco-temp-logger.py || true
    exec ./launch_chffrplus.sh
    ```
1. Reboot the comma two to take effect. Should see `leeco-temp-logger.py` on `ps -ef`
1. CSV will be written every five minutes in `/data/data/com.termux/files/home/leeco-temp.csv`
1. To view the CSV, `scp /data/data/com.termux/files/home/leeco-temp.csv` to your PC and open it w/ Excel, LibreOffice, Google Sheets, notepad, etc
1. To disable the logger:
    1. ssh into comma two and restore `launch_openpilot.sh`.  Run `cp /data/openpilot/launch_openpilot.sh.orig /data/openpilot/launch_openpilot.sh`
    1. `kill` the existing `leeco-temp-logger.py` process.  (`ps -ef | grep leeco-temp-logger.py` and kill the pid)
    1. delete the csv and script files in `/data/data/com.termux/files/home/`
    1. Reboot the comma two
