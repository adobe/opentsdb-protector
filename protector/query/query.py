#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

from datetime import datetime, timedelta
import time
import json
import hashlib
import re


class OpenTSDBQuery(object):
    """
    Common methods for working with OpenTSDB Queries
    """
    q = {}
    id = None
    stats = {}

    def __init__(self, data):

        self.q = json.loads(data)

        if not self.q.get("queries", []) or not self.q.get("start", None):
            raise Exception("Invalid OpenTSDB query: %s" % data)

        self.id = self._hash()

        self._show_stats()
        self._show_query()

    def get_start_raw(self):
        return self.q.get("start")

    def get_end(self):
        return self.q.get("end", None)

    def get_queries(self):
        return self.q.get("queries")

    def get_start_timestamp(self):

        start = self.get_start_raw()

        if str(start).isdigit():

            if len(str(start)) > 12:
                # Milliseconds -> seconds
                return int(start) / 1000
            else:
                # Seconds
                return int(start)
        else:

            # OpenTSDB: http://opentsdb.net/docs/build/html/user_guide/query/dates.html
            # ms - Milliseconds
            # s - Seconds
            # m - Minutes
            # h - Hours
            # d - Days (24 hours)
            # w - Weeks (7 days)
            # n - Months (30 days)
            # y - Years (365 days)

            m = re.search('^(\d+)(ms|s|m|h|d|w|n|y)-ago$', str(start))
            if m:
                tabl = {'ms': 'milliseconds', 's': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks', 'n': 'months', 'y': 'years'}

                unit = str(m.group(2))
                val = int(m.group(1))
                delta_unsupported = {'n': 30, 'y': 365}

                if unit in delta_unsupported.keys():
                    val = val * delta_unsupported[unit]
                    unit = 'd'

                par = {tabl[unit]: val}
                then = datetime.now() - timedelta(**par)
                return time.mktime(then.timetuple())
            else:
                raise Exception("Start date parse error. Value: {}".format(str(start)))

    def get_end_timestamp(self):

        end = self.get_end()

        if end:

            if len(str(end)) > 12:
                # Milliseconds -> seconds
                return int(end) / 1000
            else:
                # Seconds
                return int(end)
        else:
            return int(round(time.time()))

    def get_metric_names(self):
        qs = self.q.get("queries")
        qs_names = []
        for i in qs:
            qs_names.append(i["metric"])
        return qs_names

    def get_id(self):
        return self.id

    def _show_stats(self):
        self.q.update({"showStats": True})

    def _show_query(self):
        self.q.update({"showQuery": True})

    def _hash(self):

        temp = self.q.copy()
        # cleaning up some keys that should not identify a query
        for unused_key in ('start', 'end', 'timezone', 'options', 'padding'):
            temp.pop(unused_key, None)
        
        return hashlib.md5(json.dumps(temp)).hexdigest()

    def set_stats(self, stats):
        self.stats = stats

    def get_stats(self):
        return self.stats

    def to_json(self):
        return json.dumps(self.q)


class OpenTSDBResponse(object):
    """
    Common methods for working with OpenTSDB responses
    """
    r = []
    stats = []

    def __init__(self, data):

        self.stats = []
        self.r = []

        rlist = json.loads(data)
        #if not len(rlist):
        #    raise Exception("OpenTSDB response: Empty")

        for item in rlist:
            if not item.get("stats", []):
                raise Exception("OpenTSDB query stats not present in response!")
            self.stats.append(item.get('stats'))

        self.r = rlist

    def get_stats(self):
        return self.stats

    def to_json(self):
        return json.dumps(self.r)
