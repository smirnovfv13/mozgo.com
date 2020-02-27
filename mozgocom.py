# -*- coding: utf-8 -*-
__author__ = 'smirnovfv'

import sched
import time
import http.client
import json
import copy


HOST_NAME = "api.base.mozgo.com"
EVENT_TIMES = [
    {
        "reg": "2020-02-27T12:00:00",
        "played_at":"2020-03-02T19:00:00"
    },
    # {
    #     "reg": "2020-02-25T20:58:00",
    #     "played_at":"2020-03-10T19:00:00"
    # }
]
AUTHORIZATION_HEADER = '''Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImM1MjU5MDAzYWUzMjkwZGY4YWFiZjc3ZjI3MGI2NThmZTI0ZWJlYzNjMjk0ODcxNDg1MDY4ODc0MTE4ZjE2MzRiMmE2ODY1ZDMzODUzY2FmIn0.eyJhdWQiOiIxIiwianRpIjoiYzUyNTkwMDNhZTMyOTBkZjhhYWJmNzdmMjcwYjY1OGZlMjRlYmVjM2MyOTQ4NzE0ODUwNjg4NzQxMThmMTYzNGIyYTY4NjVkMzM4NTNjYWYiLCJpYXQiOjE1Njg4MjcxNDMsIm5iZiI6MTU2ODgyNzE0MywiZXhwIjoxNjAwNDQ5NTQzLCJzdWIiOiIxMjg5Iiwic2NvcGVzIjpbIioiXX0.FdhH-Aju73z_ppe35GFBi8mkC9ojzWBpp_v4Uv-VxmKLwjxBLu6w9QpcbwU7dWMQM6MgS7xDZ4vaDDXnbnBKOhuD1xXVEhKx_JpRj6oRiwNYQJWlJGxeXi6PJ1Yef59eBxQwYi5G0xIC8u0Sr4o4UCejJU4kh__QBO6AtNqWBC86KASAw5MR3Pufo3McQpjmEMM6Tr8CQaxiYD51PBd0UEhe66kHwZexWNhb6SsH_1dKU4pxr9QeHvQj8FMJj1arezQ2GVXWQ3_3-xbwH5HZxAQPlvJhI00J9yIvvby_N411jPWe6Z3SZkjMSUWBlqcuMT03cMOGiQH39m5KAOtfEfHL9jlzMQEnfcXYLRTfFre2Ua6aenGqqnbFhwuWi49EjEY-LcGQN45kQM7aXYA5BCQkj-4bvigzRUNw7279NzzjjjXgznwYw4T0NRr5wahJmr8vDq2sM5rVSiT8NUsj4LFimV-Mlb-NahtcnnWkyLDPyLkvYFfGql8K26WFSag8_ZqN_Yd71M0lW7yVG5rwJFAMdhQcuIAZcIyike51fv00r4GpcngW7nSo8_dcCL5XDqF4iws-WJ_SV1o1fYx1AT6PaaLyXqUdxR9ALkNC9m-sWgvl9UTg82AE47Hv3UglPzePG7ufszCaJCGtYW2i5W1jupAj1itbM7Fdrz6XmFw'''

# конвертер текстовой даты в seconds since epoch
def abstime(timetext):
    timeobj = time.strptime(timetext, "%Y-%m-%dT%H:%M:%S")
    return time.mktime(timeobj)


# класс для исполнения запросов
class MozgoComConnection:
    def __init__(self):
        self._conn = http.client.HTTPSConnection(HOST_NAME)
        self._USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.183 Safari/537.36 Vivaldi/1.96.1147.52"
        self._headers = {
            ":authority": "api.base.mozgo.com",
            ":scheme":"https",
            # как ни странно, но с этим заголовком API не работает!
            # "accept-encoding": "gzip, deflate, br",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://portal.mozgo.com",
            "user-agent": self._USER_AGENT
        }

    # merging headers utility
    def _patchedHeaders(self, headers_override):
        headers = copy.copy(self._headers)
        if headers_override:
            headers.update(headers_override)
        return headers

    # OPTIONS request. Looks like its obligatory for successful GET.
    def requestOptions(self, url, headers_override = None):
        headers = self._patchedHeaders(headers_override)
        headers.update({
            "accept":"*/*",
            "access-control-request-headers": "authorization,x-user-time-offset",
            "access-control-request-method":"GET"
        })
        self._doRequest("OPTIONS", url, headers, False)

    # чтение и разбор HTTPResponse
    def _retrieveResponse(self, conn, parse_answer = True):
        response = conn.getresponse()
        answer = response.read()
        conn.close()
        print(response.status, response.reason)
        if response.status >= 300:
            raise Exception("{0} {1} {2}".format(response.status, response.reason, answer.decode()))
        print(str(answer))
        if parse_answer:
            answer_obj = json.loads(answer.decode())
            return answer_obj

    # вспомогательный метод с общими заголовками для GET, OPTIONS
    def _doRequest(self, method, url, headers, parse_answer = True):
        headers.update({
            ":path": url,
            ":method": method
        })
        self._conn.request(method, url, headers=headers)
        return self._retrieveResponse(self._conn, parse_answer)

    # perform a POST request with mozgo.com API a headers
    def requestPost(self, url, body, headers_override = None):
        string_body = json.dumps(body)
        # заголовки для POST значительно отличаются от штатных
        headers = {
            "Accept": "application/json, text/plain, */*",
            # "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Authorization": AUTHORIZATION_HEADER,
            "Connection": "keep-alive",
            "Content-Length": len(string_body),
            "Content-Type": "application/json;charset=UTF-8",
            "Host": "api.base.mozgo.com",
            "Origin": "https://portal.mozgo.com",
            "Referer": "https://portal.mozgo.com /?",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self._USER_AGENT,
            "X-User-Time-Offset": 10800
        }

        self._conn.request("POST", url, string_body, headers=headers)
        return self._retrieveResponse(self._conn)

    # perform a GET request with mozgo.com API a headers
    def requestGet(self, url, headers_override = None):
        headers = self._patchedHeaders(headers_override)
        headers.update({
            "accept": "application/json, text/plain, */*",
            "referer": "https://portal.mozgo.com/?",
            "x-user-time-offset": "10800",
            "authorization": AUTHORIZATION_HEADER
        })
        return self._doRequest("GET", url, headers)


# класс события на которое регистрируемся
class Event:
    def __init__(self, event_desc):
        self._auth_data = AUTHORIZATION_HEADER
        self._event_regdatetime = event_desc["reg"]
        self._event_mkregtime = abstime(self._event_regdatetime)
        self._played_at = event_desc["played_at"]
        self._played_at_response = None
        self._event_uuid = None
        self._team_id = None
        self._team_response = None

    def getEventDateTimeText(self):
        return self._event_regdatetime

    def getEventMkTime(self):
        return self._event_mkregtime

    def getPlayedAt(self):
        return self._played_at

    # UPDATE event identifiers from mozgo.com API
    def update(self, played_at_response, conn):
        self._played_at_response = played_at_response
        self._event_uuid = self._played_at_response["uuid"]
        conn.requestOptions("/players/me?city_id=123")
        self._team_response = conn.requestGet("/players/me?city_id=123")
        self._team_id = self._team_response["teams"][0]["id"]

    # immediate registering for an event
    def register(self, conn):
        if not self._team_response:
            raise Exception("No team data requested")
        request = {
            "event_day_id": self._event_uuid,
            "team_id": self._team_id,
            "captain_phone": self._team_response["phone"],
            "comment":"",
            "captain_email": self._team_response["email"],
            "player_count":6,
            "captain_name": self._team_response["name"],
            "play_for_first_time": False,
            "roistat_first_visit":"331370",
            "roistat_visit":"331370"
        }
        # сайт делает почему-то два ПОСТ-запроса, визуально разницу не уловил...
        answer1 = conn.requestPost("/players/applications", request)
        answer2 = conn.requestPost("/players/applications", request)
        print(answer2["registered_at"])

# задача шедулера - метод вывода текущего времени
def job_print(name):
    curr_time = time.time()
    loc_time = time.localtime(curr_time)
    s_time = time.strftime("%H:%M:%S", loc_time)
    s_day = time.strftime("%d %b", loc_time)
    millis = round(1000 * (curr_time - int(curr_time)))
    print("job {0} entered at {1}.{2} {3}".format(name, s_time, millis, s_day))

# задача шедулера - метод регистрации
def job_register(name, event, conn):
    job_print(name)
    try:
        event.register(conn)
    except Exception as e:
        print(e)

# задача шедулера - метод проверки доступности сайта и подготовки к регистрации
def job_ping(name, event, conn):
    job_print(name)
    try:
        conn.requestOptions("/events/dates/123?sort=played_at")
        answer = conn.requestGet("/events/dates/123?sort=played_at")
        for answrd_evt in answer:
            if answrd_evt["played_at"] == event.getPlayedAt():
                event.update(answrd_evt, conn)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    job_print("start")

    conn = MozgoComConnection()

    # создаем штатный шедулер Python отсчитывающий секунды от epoch
    start_time = time.time()
    py_sched = sched.scheduler(time.time, time.sleep)
    for event_data in EVENT_TIMES:
        event = Event(event_data)
        event_mkregtime = event.getEventMkTime()
        # добавляем пингующие события, чтобы нас не разлогинили
        ping_time = start_time
        ping = 0
        while event_mkregtime - ping_time > 4:
            # пингуем в интервалы выбираемые дихотомией
            ping_time = ping_time + (event_mkregtime - ping_time) / 2
            py_sched.enterabs(ping_time, 2, job_ping,
                              kwargs={"name": "ping {}".format(ping), "event": event, "conn" : conn})
            ping = ping + 1
            print("added ping {0} at {1}".format(ping, time.strftime("%H:%M:%S %d %b", time.localtime(ping_time))))
        # главное событие регистрации по конкретному времени
        py_sched.enterabs(event_mkregtime, 1, job_register,
                          kwargs={"name": "ping {}".format(ping), "event": event, "conn" : conn})
    py_sched.run()
