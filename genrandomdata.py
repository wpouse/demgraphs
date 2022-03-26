#!/usr/bin/env python3

import argparse
import random
import requests
import time


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', type=int)
    args = parser.parse_args()

    now = time.time()
    for _ in range(1000):
        rtime = int(random.random() * now)
        requests.post(f'http://localhost:{args.port}/', data=f'abc {random.random()} {rtime}\n')
