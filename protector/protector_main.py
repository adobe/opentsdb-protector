#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

import logging
import time
import datetime as dt
from result import Ok, Err
import re
import json
import redis

from protector.guard.guard import Guard
from prometheus_client import Counter, Summary, Histogram, Gauge


class Protector(object):
    """
    The main protector class which checks for malicious queries
    """

    db = None
    ttl = 0

    def __init__(self, rules, blockedlist=[], allowedlist=[], db_config={}, safe_mode=False):
        """
        :param rules: A list of rules to evaluate
        :param blockedlist: A list of blocked metric names
        :param allowedlist: A list of allowed metric names
        :param safe_mode: If set to True, allow the query in case it can not be parsed
        :return:
        """
        self.guard = Guard(rules)

        self.blockedlist = blockedlist
        self.allowedlist = allowedlist
        self.safe_mode = safe_mode

        if db_config.get('expire', 0) > 0:
            self.ttl = db_config['expire']

        self.db = redis.Redis(
            host=db_config['redis']['host'],
            port=db_config['redis']['port'],
            password=db_config['redis']['password'],
            decode_responses=True)

        self.REQUESTS_COUNT = Counter('requests_total', 'Total number of requests', ['method', 'path', 'return_code'])
        self.REQUESTS_BLOCKED = Counter('requests_blocked', 'Total number of blocked requests. Tags: safe mode, matched rule', ['safe_mode', 'rule'])
        self.REQUESTS_ALLOWEDLIST_MATCHED = Counter('requests_allowedlist_matched', 'Total number of allowedlist matched requests')

        self.SAFE_MODE_STATUS = Gauge('safe_mode', 'Safe Mode Status')
        self.SAFE_MODE_STATUS.set(int(self.safe_mode))

        self.DATAPOINTS_SERVED_COUNT = Counter('datapoints_served_count', 'datapoints served count')
        self.TSDB_REQUEST_LATENCY = Histogram('tsdb_request_latency_seconds', 'OpenTSDB Requests latency histogram', ['http_code', 'path', 'method'])

        # Prometheus histogram based on query start time age in days
        self.TSDB_REQUEST_INTERVAL = Histogram('tsdb_request_interval', 'OpenTSDB Requests interval based on query start time', ['interval'],buckets=(1,30,90))

        self.REQUESTS_METRICS = Counter('requests_metrics', 'Total number of requests', ['metric'])

    def check(self, query):

        logging.debug("Checking OpenTSDBQuery: {}".format(query.get_id()))

        if query:
            qs_names = query.get_metric_names()
            for qn in qs_names:
                self.REQUESTS_METRICS.labels(qn).inc()    

            if self.blockedlist:
                for pattern in self.blockedlist:
                    for qn in qs_names:
                        match = re.match(pattern, qn)
                        if match:
                            return Err({"msg": "Metric name: {} is blocked".format(qn), "rule": "blockedlist"})

            if self.allowedlist:
                all_match = True
                for pattern in self.allowedlist:
                    for qn in qs_names:
                        match = re.match(pattern, qn)
                        all_match = all_match and bool(match)
                        if match:
                            logging.info("Allowedlist metric matched: {}".format(qn))

                if all_match:
                    self.REQUESTS_ALLOWEDLIST_MATCHED.inc()
                    return Ok(True)

            self.load_stats(query)
            return self.guard.is_allowed(query)
        else:
            error_msg = "Empty OpenTSDBQuery provided!"
            logging.info(error_msg)
            return Err({"msg": error_msg})

    def set_top_duration(self, key_prefix, interval, duration):

        # Get current day of the month and hour of the day
        d = dt.datetime.now()
        hour = d.hour
        day = d.day

        # Top durations
        top_duration_key = "top_duration_{}_{}".format(day, hour)
        zkey = "{}_{}".format(key_prefix, interval)

        sc = self.db.zscore(top_duration_key, zkey)

        if not sc:
            self.db.zadd(top_duration_key, {zkey: duration})
            if self.ttl:
                self.db.expire(top_duration_key, self.ttl)
        else:
            if float(duration) > float(sc):
                self.db.zadd(top_duration_key, {zkey: duration})
        ###

    def set_top_dps(self, key_prefix, interval, sum_dp):

        # Get current day of the month and hour of the day
        d = dt.datetime.now()
        hour = d.hour
        day = d.day

        # Top datapoints
        top_dps_key = "top_dps_{}_{}".format(day, hour)
        zkey = "{}_{}".format(key_prefix, interval)

        sc = self.db.zscore(top_dps_key, zkey)

        if not sc:
            self.db.zadd(top_dps_key, {zkey: sum_dp})
            if self.ttl:
                self.db.expire(top_dps_key, self.ttl)
        else:
            if int(sum_dp) > int(sc):
                self.db.zadd(top_dps_key, {zkey: sum_dp})
        ###

    def save_stats(self, query, response, duration, timeout=False):

        try:
            self.db.ping()
        except Exception as e:
            logging.error("Redis server connection issue: {}".format(e))
            return

        key_prefix = query.get_id()

        time_raw = time.time()
        current_time = int(round(time_raw))
        current_time_milli = int(round(time_raw * 1000))

        end_time = query.get_end_timestamp()
        start_time = query.get_start_timestamp()
        interval = int((end_time - start_time) / 60)

        logging.info("[{}] start: {}, end: {}, interval: {} minutes".format(query.get_id(), int(query.get_start_timestamp()), end_time, interval))

        # store query
        if not self.db.exists("{}_{}".format(key_prefix, 'query')):
            self.db.set("{}_{}".format(key_prefix, 'query'), json.dumps(query.q), ex=(self.ttl or None))

        # store query summary stats + meta
        summary = {}
        if response is not None:
            summary = response.get_stats()

        sum_dp = summary.get('emittedDPs', 0)

        # Let's record everything!
        stats = {
            'timestamp': current_time, # query execution timestamp
            'start': int(start_time), # range start
            'end': query.get_end(), # range end
            'duration': duration, # time in seconds
            'summary': summary, # summary stats if any (could be empty for some reason!). time in millis.
            'timeout': timeout
        }

        # Push/create stats list
        self.db.rpush("{}_{}".format(key_prefix, 'stats'), json.dumps(stats))

        # Set TTL if supplied
        if self.ttl:
            if self.db.ttl("{}_{}".format(key_prefix, 'stats')) == -1:
                self.db.expire("{}_{}".format(key_prefix, 'stats'), self.ttl)

        if sum_dp > 0:
            self.DATAPOINTS_SERVED_COUNT.inc(sum_dp)

        global_stats = {
            'duration': duration, # last query duration
            'timestamp': current_time # last query timestamp
        }

        if timeout:
            global_stats["timeout_last"] = current_time
        else:
            global_stats["emittedDPs"] = sum_dp

        if not self.db.hexists("{}_{}".format(key_prefix, interval), 'first_occurrence'):
            global_stats['first_occurrence'] = current_time

        self.db.hmset("{}_{}".format(key_prefix, interval), global_stats)

        # Set TTL if supplied
        if self.ttl:
            if self.db.ttl("{}_{}".format(key_prefix, interval)) == -1:
                self.db.expire("{}_{}".format(key_prefix, interval), self.ttl)

        # Total counter, for convenience. Should match LLEN of stats list
        self.db.hincrby("{}_{}".format(key_prefix, interval), "total_counter", 1)

        if timeout:
            self.db.hincrby("{}_{}".format(key_prefix, interval), "timeout_counter", 1)
        else:
            # DPS, if not timeout
            logging.info("[{}] emittedDPs: {}".format(query.get_id(), sum_dp))

            # Save dps stats
            self.set_top_dps(key_prefix, interval, sum_dp)

        logging.info("[{}] duration: {}".format(query.get_id(), duration))

        # Save duration stats
        self.set_top_duration(key_prefix, interval, duration)

        logging.info("[{}] stats saved".format(query.get_id()))

        now_time = int(round(time.time() * 1000))
        logging.debug("Time spent in save_stats: {} ms".format(now_time - current_time_milli))

    def load_stats(self, query):

        try:
            self.db.ping()
        except Exception as e:
            logging.error("Redis server connection issue: {}".format(e))
            return

        end_time = query.get_end_timestamp()

        interval = int((end_time - query.get_start_timestamp()) / 60)
        key = "{}_{}".format(query.get_id(), interval)

        if self.db.exists(key):
            logging.info("[{}] Found previous stats for this interval: {} minutes".format(query.get_id(), interval))
            query.set_stats(self.db.hgetall(key))

    def get_top(self, toptype="duration"):

        if (toptype != "duration" and toptype != "dps"):
            logging.error("Unsupported toptype: {}".format(toptype))
            return

        try:
            self.db.ping()
        except Exception as e:
            logging.error("Redis server connection issue: {}".format(e))
            return

        # Get current day of the month and hour of the day
        d = dt.datetime.now()
        hour = d.hour
        day = d.day

        data = {}
        # Dump all hourly tops for today
        while hour >= 0:
            # Top
            top_key = "top_{}_{}_{}".format(toptype, day, hour)
            sc = self.db.zrange(top_key, 0, -1, True, True)
            data[hour] = sc
            hour = hour - 1

        return json.dumps(data).encode()
