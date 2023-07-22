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
        self.log = '/data/data/com.termux/files/home/leeco-temp.csv'

        poll_interval = 60
        flush_interval = 300

        if poll_interval < 3:
            print("ERROR: poll interval must be at least 3")
            sys.exit(1)

        if (flush_interval / poll_interval) < 2:
            print ("ERROR: flush interval must be at least twice poll_interval")
            sys.exit(1)

        # 1KB holds about 13 lines/minutes of data
        # 24hr requires ~110KB
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

        self.csv_header="time,cpu0_t,cpu1_t,cpu2_t,cpu3_t,mem_t,gpu_t,bat_t,ambient_t,pmic_t,load1,cpu0_%,cpu1_%,cpu2_%,cpu3_%,gpu_%,screen_brightness"
        self.write_csv_header = False

        while 1:
            thermals = self.read_thermal()
            '''
            avg = sum(result.values()) / len(result)
            max_cpu_temp = max(result['cpu0'], result['cpu1'], result['cpu2'], result['cpu3'])
            max_comp_temp = max(max_cpu_temp, result['mem'], result['gpu'])
            print(f"cpu: {max_cpu_temp}, gpu: {result['gpu']}, mem: {result['mem']}, avg: {avg}")
            '''

            self.now = int(time())
            now_ui = datetime.fromtimestamp(self.now).strftime('%y-%m-%d %H:%M:%S')
            temperatures = ','.join(map(str,thermals.values()))
            load1 = self.read_loadavg(0)
            cpu_util = ','.join(map(str,self.read_cpu_util()))
            gpu_util = self.get_gpu_usage_percent()
            screen_brightness = self.get_screen_brightness()
            line = f'{now_ui},{temperatures},{load1},{cpu_util},{gpu_util},{screen_brightness}'
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
        # https://github.com/commaai/openpilot/blob/2476ea213c24dac16531c8798761e34f96e0ded2/selfdrive/thermald/thermald.py#L52C1-L62
        # https://github.com/commaai/openpilot/blob/842ba8e5e6253d17d82a02d3d9994efbbbf2133e/selfdrive/hardware/eon/hardware.py#L382-L383
        dat = {}
        dat['cpu0'] = round(self.read_tz(5) / 10, 1)
        dat['cpu1'] = round(self.read_tz(7) / 10, 1)
        dat['cpu2'] = round(self.read_tz(10) / 10, 1)
        dat['cpu3'] = round(self.read_tz(12) / 10, 1)
        dat['mem'] = round(self.read_tz(2) / 10, 1)
        dat['gpu'] = round(self.read_tz(16) / 10, 1)
        dat['bat'] = round(self.read_tz(29) / 1000, 1)
        dat['ambient'] = round(self.read_tz(25) / 1, 1)
        dat['pmic'] = round(self.read_tz(22) / 1000, 1)
        return dat

    # https://github.com/commaai/openpilot/blob/842ba8e5e6253d17d82a02d3d9994efbbbf2133e/selfdrive/hardware/eon/hardware.py#L399-L405
    def get_gpu_usage_percent(self):
        try:
            used, total = open('/sys/devices/soc/b00000.qcom,kgsl-3d0/kgsl/kgsl-3d0/gpubusy').read().strip().split()
            perc = int(100.0 * int(used) / int(total))
            return min(max(perc, 0), 100)
        except Exception:
            return 0

    # https://github.com/commaai/openpilot/blob/842ba8e5e6253d17d82a02d3d9994efbbbf2133e/selfdrive/hardware/eon/hardware.py#L389-L394
    def get_screen_brightness(self):
        try:
            with open("/sys/class/leds/lcd-backlight/brightness") as f:
                return int(float(f.read()) / 2.55)
        except Exception:
            return 0

    def flush(self, signum=None, frame=None):
        if not os.path.isfile(self.log):
            self.write_csv_header = True

        with open(self.log, 'a') as f:
            if self.write_csv_header:
                f.write(f'{self.csv_header}\n')
                self.write_csv_header = False

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
