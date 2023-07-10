#!/usr/bin/python3

import os
import signal
import sys
from time import sleep
from time import time

class TempLogger:
  def __init__(self):
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

    # 1KB holds about 20 lines/minutes of data
    # 24hr requires ~72KB
    max_log_size = 1024*512 # 7 days of data
    if os.path.isfile(self.log) and os.stat(self.log).st_size > max_log_size:
        if os.path.isfile(f'{self.log}.1'):
            os.rename(f'{self.log}.1', f'{self.log}.2')
        os.rename(self.log, f'{self.log}.1')

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
      temperatures = ','.join(map(str,thermals.values()))
      load1 = self.read_loadavg(0)
      line = f'{self.now},{temperatures},{load1}'
      self.unflushed_data += f"\n{line}"

      #print(line)

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
  os.umask(0)
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
