#!/usr/bin/env python3

import argparse
import http.server
import json
import sqlite3
import urllib.parse


def consql(db):
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS data (name text, value real, time integer)')
    cur.execute('CREATE INDEX IF NOT EXISTS tindex ON data(time)')
    con.commit()
    return con, cur


class ServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/data'):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            query = 'SELECT * FROM data'
            limit = 1000
            if 'max_points' in q and int(q['max_points'][0]) < limit:
                limit = int(q['max_points'][0])
            selector = None
            if 'selector' in q:
                selector = q['selector'][0].strip()
                query += ' WHERE name=:selector'
            query += ' ORDER BY time DESC LIMIT :limit'
            self.server.cur.execute(query, {'limit': limit, 'selector': selector})
            rows = self.server.cur.fetchall()
            self.send_response(200)
            self.send_header('Content-Type', 'text/json')
            self.end_headers()
            self.wfile.write(json.dumps(list(rows)).encode())
        elif self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.server.index)

    def do_POST(self):
        data = self.rfile.readline().strip().decode('utf-8').split(' ')
        if len(data) != 3:
            self.send_response(400)
            self.end_headers()
            return
        self.server.cur.execute('INSERT INTO data VALUES (?, ?, ?)', data)
        self.server.con.commit()
        self.send_response(200)
        self.end_headers()


def server(port, db):
    with open('index.html') as f:
        index = f.read().encode()
    with http.server.HTTPServer(('localhost', port), ServerHandler) as server:
        server.con, server.cur = consql(db)
        server.index = index
        server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', type=int)
    parser.add_argument('--db', type=str)
    args = parser.parse_args()

    print('Starting server.')
    server(args.port, args.db)
