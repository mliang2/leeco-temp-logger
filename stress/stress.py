#!/usr/bin/python3
import time
import sys
from itertools import repeat
from multiprocessing import Pool, cpu_count
import argparse

def f(x, runtime=1, sleeptime=0, busycycles=100000):
    timeout = time.time() + runtime
    cnt = 0
    while True:
        if time.time() > timeout:
            break
        if sleeptime and cnt % busycycles == 0:
            time.sleep(sleeptime)
        x*x
        cnt += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", default=60, type=int, help="how long to run, in seconds. Default: %(default)s")
    parser.add_argument("-s", default=0.0, type=float, help="how long to sleep in between test cycles, in sub-second. 0.0 = 100% CPU usage. Default: %(default)s")
    parser.add_argument("-p", default=cpu_count(), type=int, help="How many process to run, default: same as number of CPUs")
    parser.add_argument("-c", default=100000, type=int, help="how many loops per test cycle.  Default: %(default)s)")
    args = parser.parse_args()

    print(f'Running for {args.t}s with sleep time of {args.s}s per {args.c} cycles utilizing {args.p} cores')
    print('Press control+c to abort')
    pool = Pool(args.p)
    pool.starmap(f, zip(range(args.p), repeat(args.t), repeat(args.s), repeat(args.c)))
