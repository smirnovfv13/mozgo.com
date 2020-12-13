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
        "reg": "2020-12-04T12:00:00",
        "played_at": "2020-12-07T19:00:00"
    }

]
AUTHORIZATION_HEADER = '''Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjViMmYxZTEzNDAwNjYzN2JlODE3OTQxMjI5ZGM2OGM4ZTg0NTc4NTY4ZDVjMTg5MDM4MTk5M2Y5MDUxMTQ3ZWQxNTc5YmMzM2YxMGZkNGM4In0.eyJhdWQiOiIxIiwianRpIjoiNWIyZjFlMTM0MDA2NjM3YmU4MTc5NDEyMjlkYzY4YzhlODQ1Nzg1NjhkNWMxODkwMzgxOTkzZjkwNTExNDdlZDE1NzliYzMzZjEwZmQ0YzgiLCJpYXQiOjE2MDEwMTgyOTgsIm5iZiI6MTYwMTAxODI5OCwiZXhwIjoxNjMyNTU0Mjk4LCJzdWIiOiIxMjg5Iiwic2NvcGVzIjpbIioiXX0.jI3zBdLXB2eQYIhTcKsVE57ynz50Wla0GvqkcK4fk6hygukwhlHL40rmp4aIhhxj_I24Xaa-BXFZ4s0tYIeY6AWuDJkrl_BPkVUGIxyHhCSZzbEfaf2HaEsYs9Nhy5hHJZb9DbI7MYlHc0bBTs1GW5nl8Yl6DuF9KZzhTVCAaKSwsyo1XW_pD4ygL-v5xO_LA0nA5YecBftMsG6XOEjbmo-FeeCCE5_Jk6IJ5wZf3ZGFd3irTt3MdpfHj9hpIFVgBkaTM9Bgk3f1l3kMUDYyOkgiD0eh8baJ8i8KHRxoHgyZR100LgwzQJO_rcuug6ohXl72txoYQs4UVt_h8w5EDQdXnM06MA9wwoQeahZIg1A0gKiYxrKp9Ao9O8tRUwCsXlPlAmcvZpbSSguHONDCe8Sp-XOpsUpzYXrbB57WaLiTqg-Cmhx8NA9u6MvMWeJowj9gWBNVjo3ftS37w4o0t1m1vPVGUEmZyLtRwLJHneSHaiYDhK1E-U4AyZBYKh1zEjm829XKezX_OgxKUy4N0O4AOMuEZap9eUry2a3CEBE-fpsViBrwrReBOr26LpXmWHiwSxO9ZJ7aymmNHCWPGwkdquYjTDiNpERxfre7ytJUX6Xep1xDHT774Lfs74SAdfj4QzAqUDaSu38cqzXctclUH48cZgpQuedKAyJToyg'''

REG_TIMEOUT = 5 #seconds

SILENT_SECONDS = 3600*3 #number of seconds for keeping API without POSTS
REG_FALSESTART = 0.400 #number of milliseconds to start reg before actual


# конвертер текстовой даты в seconds since epoch
def abstime(timetext):
    timeobj = time.strptime(timetext, "%Y-%m-%dT%H:%M:%S")
    return time.mktime(timeobj)

def log_time_delta(text, perfcntr_started):
    delta_secs = time.perf_counter() - perfcntr_started
    delta_msecs = int(round(delta_secs * 1000))
    print("[TIME] {0} {1}".format(text, delta_msecs))

# исключение регистрации
class RegisterException(Exception):
    def __init__(self, message, status, reason, response):
        super(RegisterException, self).__init__(message)
        self.status = status
        self.reason = reason
        self.response = response

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

    def _printHeaders(self, formattedStr, headers):
        print(formattedStr)
        print("HEADERS")
        for k, v in headers.items():
            print("{} = {}".format(k, v))

    # OPTIONS request. Looks like its obligatory for successful GET.
    def requestOptions(self, url, headers_override = None):
        headers = self._patchedHeaders(headers_override)
        headers.update({
            "accept":"*/*",
            "access-control-request-headers": "authorization,x-user-time-offset",
            "access-control-request-method":"GET"
        })
        self._printHeaders("OPTIONS REQUEST {}".format(url), headers)
        self._doRequest("OPTIONS", url, headers, False)

    # чтение и разбор HTTPResponse
    def _retrieveResponse(self, conn, parse_answer = True):
        response = conn.getresponse()
        answer = response.read()
        conn.close()
        print("{} {}".format(response.status, response.reason))
        print("RESPONSE HEADER {} ".format(str(response.headers)))
        print("RESPONSE BODY {} ".format(str(answer)))
        if response.status >= 300:
            raise RegisterException("HTTP Error", response.status, response.reason, answer.decode)
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
    def requestPost(self, url, body, headers_override = None, perfcntr_started = 0):
        log_time_delta("def requestPost entered", perfcntr_started)
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

        self._printHeaders("POST REQUEST {} ".format(url), headers)
        log_time_delta("headers printed", perfcntr_started)
        print("POST REQUEST BODY {} ".format(str(body)))
        log_time_delta("body printed", perfcntr_started)
        try:
            self._conn.request("POST", url, string_body, headers=headers)
            log_time_delta("POST sent", perfcntr_started)
        except:
            raise RegisterException("Register Exception Raised", -1, -1, "HTTPConnection request Error")
        log_time_delta("before parsing response", perfcntr_started)
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
        self._printHeaders("GET REQUEST {}".format(url), headers)
        return self._doRequest("GET", url, headers)

# класс события на которое регистрируемся
class Event:
    def __init__(self, event_desc):
        self._auth_data = AUTHORIZATION_HEADER
        self._event_regdatetime = event_desc["reg"]
        # вычисляем старт регистрации, с фальстартом
        self._event_mkregtime = abstime(self._event_regdatetime) - REG_FALSESTART
        self._played_at = event_desc["played_at"]
        self._played_at_response = None
        self._event_uuid = None
        self._team_id = None
        self._team_response = None

    # registration date as text "reg": "Y-M-dTH:m:s",
    def getEventRegDateTimeText(self):
        return self._event_regdatetime

    # registration date since epoch
    def getEventRegMkTime(self):
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
        process_started = time.perf_counter()
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

        retry = True
        cycle_started = time.time()
        while retry:
            try:
                log_time_delta("before post", process_started)
                answer = conn.requestPost("/players/applications", request, process_started)
                log_time_delta("after post success", process_started)
                retry = False
                print(answer["registered_at"])
            except RegisterException as rex:
                log_time_delta("after post exception", process_started)
                print("Exception caught HTTP Code {}".format(rex.reason))
                retry = rex.status == 422 or rex.status == 0
                if retry:
                    # registration not available, retry after 50 ms
                    print("retry after {} seconds".format(int(time.time() - cycle_started)))
                    # time.sleep(0.001)
                else:
                    raise RegisterException("Register Exception Raised", rex.status, rex.reason, rex.response)
            log_time_delta("after post cycle end", process_started)
            retry = retry and ( (time.time() - cycle_started) <= REG_TIMEOUT )

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
        job_print('register failed')
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
        event_mkregtime = event.getEventRegMkTime()
        # проверяем Event
        job_ping('checking event', event, conn)
        # добавляем пингующие события, чтобы нас не разлогинили
        ping_time = start_time
        ping = 0
        while event_mkregtime - ping_time > SILENT_SECONDS:
            # пингуем в интервалы выбираемые дихотомией
            ping_time = ping_time + 3600*3
            py_sched.enterabs(ping_time, 2, job_ping,
                              kwargs={"name": "ping {}".format(ping), "event": event, "conn" : conn})
            ping = ping + 1
            print("added ping {0} at {1}".format(ping, time.strftime("%H:%M:%S %d %b", time.localtime(ping_time))))
        # главное событие регистрации по конкретному времени
        py_sched.enterabs(event_mkregtime, 1, job_register,
                          kwargs={"name": "registration {}".format(ping), "event": event, "conn" : conn})
        print("added reg {0} at {1}".format(ping, time.strftime("%H:%M:%S %d %b", time.localtime(event_mkregtime))))
    py_sched.run()
