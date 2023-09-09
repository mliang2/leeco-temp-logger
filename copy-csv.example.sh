#!/data/data/com.termux/files/usr/bin/bash

scp_opts="-i ~/id_rsa.c2-temperature -P 22 -o ConnectTimeout=30 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error"
scp_target="user@IP:/tmp/"

csv=~/leeco-temp.csv
notification_sound="/system/media/audio/notifications/Iridium.ogg"

if [ -f $csv ]; then
    scp $scp_opts $csv $scp_target &> /dev/null

    # play a sound when csv is uploaded
    # install w/ "apt install play-audio".  NEOS already have termux installed
    if [ -f $notification_sound ]; then
        play-audio $notification_sound
    else
        # fallback
        play-audio /system/media/audio/ui/camera_focus.ogg
    fi
else
    echo "leeco-temp.csv not found"
fi
