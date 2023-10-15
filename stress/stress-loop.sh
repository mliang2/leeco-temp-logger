#!/data/data/com.termux/files/usr/bin/bash
# run the stress test for 1 hour, rest for 10 minutes, repeat 24 times

dirname=$(dirname $0)
for i in $(seq 1 24); do
    echo "Running loop #${i}"
    $dirname/stress.py -t 3600
    echo "Resting for 10 minutes"
    sleep 600
done

echo "All done"
