#!/usr/bin/env python3

import argparse
import http.server
import json
import sqlite3
import urllib.parse
import time
import datetime
from jinja2 import Environment, PackageLoader, select_autoescape



def consql(db):
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS data (name text, value real, time integer)')
    cur.execute('CREATE INDEX IF NOT EXISTS tindex ON data(time)')
    con.commit()
    return con, cur


class ServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        if url_parsed.path == '/data':
            
            data_dict = self._getData(urllib.parse.parse_qs(url_parsed.query))
            self.send_response(200)
            self.send_header('Content-Type', 'text/json')
            self.end_headers()
            
                
            self.wfile.write(json.dumps(data_dict).encode())
            
        elif url_parsed.path == '/selectors':
            query = "SELECT DISTINCT name FROM data"
            self.server.cur.execute(query)
            rows = self.server.cur.fetchall()
            self.send_response(200)
            self.send_header('Content-Type', 'text/json')
            self.end_headers()
            
            self.wfile.write(json.dumps(list(rows)).encode())
        elif url_parsed.path == '/' or url_parsed.path == '/index.html':
        
            parsed_query = urllib.parse.parse_qs(url_parsed.query)
            self.send_response(200)
            self.end_headers()
            
            templatingVariables = self._setHTMLInputs(parsed_query)
            self.wfile.write(self.server.index_template.render(templatingVariables).encode())
        return
        
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
    
    def _getDataSelectors(self, selectors):
        query = "SELECT DISTINCT name FROM data"
        self.server.cur.execute(query)
        rows = self.server.cur.fetchall()
        dataSelectors = {}
        for name in rows:
            split_name = name[0].split('.', 1)
            if len(split_name) == 2:
                group_name, data_name = split_name
            else:
                group_name = 'Other'
                data_name = split_name[0]
            if group_name not in dataSelectors:
                dataSelectors[group_name] = set()
            if name[0] in selectors:
                dataSelectors[group_name].add((data_name, True)) # Second element is whether it should be selected in HTML element
            else:
                dataSelectors[group_name].add((data_name, False))
        return dataSelectors
        
    def _setHTMLInputs(self, parsed_query):
        q = parsed_query
        templatingVariables = {'url_value': self.path, 'start_date': '', 'start_time': '', 'end_date': '', 'end_time': '', 'showData': False}
        selectors = []
        for queryHTML in q:
            if queryHTML in templatingVariables:
                templatingVariables[queryHTML] = q[queryHTML]
            if 'selector' in q:
                selectors = q['selector'][0].split(",")
        templatingVariables['groupNamesDict'] = self._getDataSelectors(selectors)
        if selectors:
            templatingVariables['datasetDict'] = self._getData(q)
            templatingVariables['showData'] = True
        return templatingVariables
    
    def _getData(self, parsed_query):
        q = parsed_query
        data_dict = {}
        limit = 10000
        if 'max_points' in q and int(q['max_points'][0]) < limit:
            limit = int(q['max_points'][0])
        
        #First get the number of rows to make sure we don't exceed limit number of data points. 
        #The LIMIT query just limits the query to the past LIMIT number of rows instead of equally spaced between the two time stamps
        #query = 'SELECT COUNT(*) FROM data WHERE'
        query = 'SELECT * FROM data WHERE'
        
        start_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d") #Set default start_date to yesterday
        if 'start_date' in q:
            start_date = q['start_date'][0]
            
        start_time = '00:00'
        if 'start_time' in q:
            start_time = q['start_time'][0]
        t0 = int(datetime.datetime.strptime(start_date + ' ' + start_time, "%Y-%m-%d %H:%M").timestamp())
        print(t0)
        query += ' time >= :t0 AND'
        
        end_date = datetime.date.today().strftime("%Y-%m-%d")
        if 'end_date' in q:
            end_date = q['end_date'][0]
            
        end_time = datetime.datetime.now().strftime("%H:%M")
        if 'end_time' in q:
            end_time = q['end_time'][0]
        t1 = int(datetime.datetime.strptime(end_date + ' ' + end_time, "%Y-%m-%d %H:%M").timestamp())
        query += ' time <= :t1'

        selectors = q['selector'][0].split(",")
        query += ' AND ('
        for n in range(len(selectors)):
            selector = selectors[n]
            query += 'name=' + "'" + selector +"'"
            if n != len(selectors)-1:
                query += ' OR '
        query += ')'
        query += ' ORDER BY time DESC'
        print(query, t0, t1)
        self.server.cur.execute(query, {'t1': t1, 't0': t0})
        rows = self.server.cur.fetchall()
        #print(rows)
        for (name, value, time) in rows:
            if name in data_dict:
                data_dict[name].append((1000*time,value))
            else:
                data_dict[name] = [(1000*time,value)]
        return data_dict

def server(port, db):
    env = Environment(
    loader=PackageLoader("demgraphs"),
    autoescape=select_autoescape(
    enabled_extensions=('html', 'xml'),
    default_for_string=True,
    )
    )
    #with env.get_template("index_template.html") as f:
    #with open('index.html') as f:
        #index_template = f
        #index = f.read().encode()
    with http.server.HTTPServer(('localhost', port), ServerHandler) as server:
        server.con, server.cur = consql(db)
        server.index_template = env.get_template("index_template.html")
        server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', type=int)
    parser.add_argument('--db', type=str)
    args = parser.parse_args()

    print('Starting server.')
    server(args.port, args.db)
