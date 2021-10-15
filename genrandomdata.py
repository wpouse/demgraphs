#!/usr/bin/env python3

import argparse
import random
import requests


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', type=int)
    args = parser.parse_args()

    for _ in range(1000):
        requests.post(f'http://localhost:{args.port}/', data=f'abc {random.random()} {int(random.random() * 1000 + 1000)}\n')
