# -*- coding: utf-8 -*-
__author__ = 'smirnovfv'

import time
from mozgocom import MozgoComConnection, Event

TRY_LIMIT = 1000

def _ping_post(name, conn, event):
    def _post(conn):
        request = event.makeRegisterBody()
        conn.requestPost("/players/applications", request, 0)
        return conn.getResponseHeaders()
    return _ping(name, conn, _post)

def _ping_get(name, conn, event):
    def _get(conn):
        conn.requestGet("/events/dates/123?sort=played_at")
        return conn.getResponseHeaders()
    return _ping(name, conn, _get)

def _ping(name, conn, f):
    print(name)
    try:
        response_headers = f(conn)
        server_timestamp_str = response_headers.get('date')
        server_timestamp_o = time.strptime(server_timestamp_str, '%a, %d %b %Y %H:%M:%S %Z')
        return server_timestamp_o
    except Exception as e:
        print('ping failed')
        print(e)

def _collect_latency(conn, event, request_func):
    current_try = 1
    offset_found = False
    desync_stat = []
    while (current_try < TRY_LIMIT):
        before_post_time = time.time() - 3600 * 3
        before_post_time_struct = time.gmtime(before_post_time)
        # make a query
        server_time_struct = request_func("{} try".format(current_try), conn, event)
        server_time = time.mktime(server_time_struct)
        after_post_time = time.time() - 3600 * 3
        desync = server_time - before_post_time
        print('before {} server {} after {} latency {} desync {}'.format(
            before_post_time,
            server_time,
            after_post_time,
            round(1000 * (after_post_time - before_post_time)),
            desync
        ))
        if desync < -1:
            desync_stat.append(-1 * (desync + 1))
        offset_found = len(desync_stat) > 20
        if offset_found:
            break
        current_try += 1
    return desync_stat

if __name__ == '__main__':
    print("start")

    conn = MozgoComConnection(verbose=False)
    event = Event({
        "reg": "2020-12-14T12:00:00",
        "played_at": "2020-12-22T19:00:00"
    })
    event.bindTeam(conn)

    dssg = _collect_latency(conn, event, _ping_get)
    dssp = _collect_latency(conn, event, _ping_post)
    print(dssg)
    print('min {} max {} avg {} total {}'.format(min(dssg), max(dssg), sum(dssg)/len(dssg), len(dssg)))
    print(dssp)
    print('min {} max {} avg {} total {}'.format(min(dssp), max(dssp), sum(dssp)/len(dssp), len(dssp)))
