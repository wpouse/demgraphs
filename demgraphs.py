#!/usr/bin/env python3

import argparse
import http.server
import json
import sqlite3
import urllib.parse
import time
import datetime


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
            
            limit = 10000
            if 'max_points' in q and int(q['max_points'][0]) < limit:
                limit = int(q['max_points'][0])
            
            #First get the number of rows to make sure we don't exceed limit number of data points. 
            #The LIMIT query just limits the query to the past LIMIT number of rows instead of equally spaced between the two time stamps
            #query = 'SELECT COUNT(*) FROM data WHERE'
            query = 'SELECT * FROM data WHERE'
            selector = None
            if 'selector' in q:
                selector = q['selector'][0].strip()
                query += ' name=:selector AND'
            
            if 'start_date' in q:
                start_date = q['start_date'][0]
                
                start_time = '00:00'
                if 'start_time' in q:
                    start_time = q['start_time'][0]
                t0 = int(datetime.datetime.strptime(start_date + ' ' + start_time, "%Y-%m-%d %H:%M").timestamp())
                query += ' time >= :t0 AND'
            
            end_date = datetime.date.today().strftime("%Y-%m-%d")
            if 'end_date' in q:
                end_date = q['end_date'][0]
                
            end_time = datetime.datetime.now().strftime("%H:%M")
            if 'end_time' in q:
                end_time = q['end_time'][0]
            t1 = int(datetime.datetime.strptime(end_date + ' ' + end_time, "%Y-%m-%d %H:%M").timestamp())
            query += ' time <= :t1'
            
            query += ' ORDER BY time DESC'
            
            if 'start_date' in q:
                self.server.cur.execute(query, {'t1': t1, 't0': t0, 'selector': selector})
            else:
                self.server.cur.execute(query, {'t1': t1, 'selector': selector})
            rows = self.server.cur.fetchall()
            num_rows = len(rows)
            skip_row_num = int(num_rows // limit) #Floor to nearest integer
            if skip_row_num < 2:
                skip_row_num = 1
            rows = rows[::skip_row_num]
            self.send_response(200)
            self.send_header('Content-Type', 'text/json')
            self.end_headers()
            
                
            self.wfile.write(json.dumps(list(rows)).encode())
            
        elif self.path.startswith('/selectors'):
            query = "SELECT DISTINCT name FROM data"
            self.server.cur.execute(query)
            rows = self.server.cur.fetchall()
            print('here')
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
