#!/usr/bin/python3

import os
import signal
import sys
from datetime import datetime
from time import sleep
from time import time

class TempLogger:
    def __init__(self, debug=False):
        self.unflushed_data = ''
        self.now = int(time())
        self.last_flush = self.now
        self.log = '/data/data/com.termux/files/home/leeco-temp.log'

        poll_interval = 60
        flush_interval = 300

        if poll_interval < 3:
            print("ERROR: poll interval must be at least 3")
            sys.exit(1)

        if (flush_interval / poll_interval) < 2:
            print ("ERROR: flush interval must be at least twice poll_interval")
            sys.exit(1)

        # 1KB holds about 14 lines/minutes of data
        # 24hr requires ~103KB
        max_log_size = 1024*1024
        if os.path.isfile(self.log) and os.stat(self.log).st_size > max_log_size:
            if os.path.isfile(f'{self.log}.1'):
                os.rename(f'{self.log}.1', f'{self.log}.2')
                os.rename(self.log, f'{self.log}.1')

        # for per CPU core utilization
        self.current_cpu_stat = None
        self.last_cpu_stat = None

        signal.signal(signal.SIGINT, self.flush)
        signal.signal(signal.SIGTERM, self.flush)

        while 1:
            thermals = self.read_thermal()
            '''
            avg = sum(result.values()) / len(result)
            max_cpu_temp = max(result['cpu0'], result['cpu1'], result['cpu2'], result['cpu3'])
            max_comp_temp = max(max_cpu_temp, result['mem'], result['gpu'])
            print(f"cpu: {max_cpu_temp}, gpu: {result['gpu']}, mem: {result['mem']}, avg: {avg}")
            '''

            self.now = int(time())
            now_ui = datetime.utcfromtimestamp(self.now).strftime('%y-%m-%d_%H:%M:%S')
            temperatures = ','.join(map(str,thermals.values()))
            load1 = self.read_loadavg(0)
            cpu_util = ','.join(map(str,self.read_cpu_util()))
            line = f'{now_ui},{temperatures},{load1},{cpu_util}'
            self.unflushed_data += f"\n{line}"

            if debug:
                print(line)

            if self.now - self.last_flush >= flush_interval:
                self.flush()

            sleep(poll_interval)

    def read_tz(self, x):
        with open("/sys/devices/virtual/thermal/thermal_zone%d/temp" % x) as f:
            ret = max(0, int(f.read()))
        return ret

    def read_loadavg(self, field):
        with open("/proc/loadavg") as fh:
            ret = float(fh.read().split(' ')[field])
        return ret

    def read_cpu_util(self):
        '''
        Tracking format:
        [
          [ cpu0_total, cpu0_idle],
          [ cpu1_total, cpu1_idle],
          ...
        ]

        Return format:
        [ cpu0_util, cpu1_util, ...]
        '''

        with open('/proc/stat') as fh:
            self.current_cpu_stat = []
            for line in fh:
                if line.startswith('cpu') and not line.startswith('cpu '):
                #if line.startswith('cpu '):
                    fields = [int(column) for column in line.strip().split()[1:]]
                    total = sum(fields)
                    idle = fields[3]
                    self.current_cpu_stat.append([total, idle])

        # print(self.current_cpu_stat)
        output = []
        if self.last_cpu_stat is None:
            # first one, fill w/ dummy data
            for i in range(0, len(self.current_cpu_stat)):
                output.append(0)
        else:
            for i in range(0, len(self.current_cpu_stat)):
                total = self.current_cpu_stat[i][0]
                idle = self.current_cpu_stat[i][1]

                last_total = self.last_cpu_stat[i][0]
                last_idle = self.last_cpu_stat[i][1]

                idle_delta = idle - last_idle
                total_delta = total - last_total
                used_delta = total_delta - idle_delta

                utilization = int(100 * used_delta / total_delta)
                output.append(utilization)

        self.last_cpu_stat = self.current_cpu_stat

        return output


    def read_thermal(self):
        # https://github.com/Kuchar09/openpilot/blob/master/selfdrive/thermald.py#L209-L215
        dat = {}
        dat['cpu0'] = self.read_tz(5) / 10.
        dat['cpu1'] = self.read_tz(7) / 10.
        dat['cpu2'] = self.read_tz(10) / 10.
        dat['cpu3'] = self.read_tz(12) / 10.
        dat['mem'] = self.read_tz(2) / 10.
        dat['gpu'] = self.read_tz(16) / 10.
        dat['bat'] = self.read_tz(29) / 1000
        return dat

    def flush(self, signum=None, frame=None):
        with open(self.log, 'a') as f:
            f.write(self.unflushed_data)

        #print('flush done')
        self.last_flush = self.now
        self.unflushed_data = ''
        if signum is not None:
            # print("here")
            sys.exit()

if __name__ == '__main__':
    # foreground mode
    if len(sys.argv) > 1 and sys.argv[1] == '-f':
        TempLogger(debug=True)
    else:
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print("fork #1 failed: %d (%s)" % (e.errno, e.strerror), file=sys.stderr)
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0o022)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent; print eventual PID before exiting
                print("Daemon PID %d" % pid)
                sys.exit(0)
        except OSError as e:
            print("fork #1 failed: %d (%s)" % (e.errno, e.strerror), file=sys.stderr)
            sys.exit(1)

        # start main loop
        TempLogger()
