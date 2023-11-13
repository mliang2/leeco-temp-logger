#!/data/data/com.termux/files/usr/bin/bash

scp_opts="-i ~/id_rsa.c2-temperature -P 22 -o PasswordAuthentication=no -o ConnectTimeout=30 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error"
scp_target="user@IP:/tmp/"

csv=~/leeco-temp.csv
ok_sound="/system/media/audio/notifications/Iridium.ogg"
error_sound="/system/media/audio/notifications/Betelgeuse.ogg"

if [ -f $csv ]; then
    scp $scp_opts $csv $scp_target &> /dev/null; scp_rc=$?

    # play a sound when csv is uploaded. See README.md for instructions
    if [ $scp_rc -eq 0 ]; then
        play-audio $ok_sound
        exit 0
    else
        play-audio $error_sound
        exit 1
    fi
else
    echo "leeco-temp.csv not found"
    play-audio $error_sound
    exit 1
fi
