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

    def __init__(self, rules, blacklist=[], whitelist=[], db_config={}, safe_mode=False):
        """
        :param rules: A list of rules to evaluate
        :param blacklist: A list of metric names to blacklist
        :param safe_mode: If set to True, allow the query in case it can not be parsed
        :return:
        """
        self.guard = Guard(rules)

        self.blacklist = blacklist
        self.whitelist = whitelist
        self.safe_mode = safe_mode

        if db_config.get('expire', 0) > 0:
            self.ttl = db_config['expire']

        self.db = redis.Redis(
            host=db_config['redis']['host'],
            port=db_config['redis']['port'],
            password=db_config['redis']['password'])

        self.REQUESTS_COUNT = Counter('requests_total', 'Total number of requests', ['method', 'path', 'return_code'])
        self.REQUESTS_BLOCKED = Counter('requests_blocked', 'Total number of blocked requests. Tags: safe mode, matched rule', ['safe_mode', 'rule'])
        self.REQUESTS_WHITELISTED_MATCHED = Counter('requests_whitelisted_matched', 'Total number of whitelisted matched requests')

        self.SAFE_MODE_STATUS = Gauge('safe_mode', 'Safe Mode Status')
        self.SAFE_MODE_STATUS.set(int(self.safe_mode))

        self.DATAPOINTS_SERVED_COUNT = Counter('datapoints_served_count', 'datapoints served count')
        self.TSDB_REQUEST_LATENCY = Histogram('tsdb_request_latency_seconds', 'OpenTSDB Requests latency histogram', ['http_code'])

    def check(self, query):

        logging.debug("Checking OpenTSDBQuery: {}".format(query.get_id()))

        if query:
            qs_names = query.get_metric_names()

            if self.blacklist:
                for pattern in self.blacklist:
                    for qn in qs_names:
                        match = re.match(pattern, qn)
                        if match:
                            return Err({"msg": "Metric name: {} is blacklisted".format(qn), "rule": "blacklisted"})

            if self.whitelist:
                all_match = True
                for pattern in self.whitelist:
                    for qn in qs_names:
                        match = re.match(pattern, qn)
                        all_match = all_match and bool(match)
                        if match:
                            logging.info("Whitelisted metric matched: {}".format(qn))

                if all_match:
                    self.REQUESTS_WHITELISTED_MATCHED.inc()
                    return Ok(True)

            self.load_stats(query)
            return self.guard.is_allowed(query)
        else:
            error_msg = "Empty OpenTSDBQuery provided!"
            logging.info(error_msg)
            return Err({"msg": error_msg})

    def save_stats(self, query, response, duration):

        try:
            self.db.ping()
        except Exception as e:
            logging.error("Redis server connection issue: {}".format(e))
            return

        time_raw = time.time()
        current_time = int(round(time_raw))
        current_time_milli = int(round(time_raw * 1000))

        end_time = query.get_end_timestamp()
        interval = int((end_time - query.get_start_timestamp()) / 60)
        logging.info("[{}] start: {}, end: {}, interval: {} minutes".format(query.get_id(), int(query.get_start_timestamp()), end_time, interval))

        stats = response.get_stats()
        key_prefix = query.get_id()

        if not self.db.exists("{}_{}".format(key_prefix, 'query')):
            self.db.set("{}_{}".format(key_prefix, 'query'), json.dumps(query.q), ex=(self.ttl or None))

        sum_dp = 0
        for item in stats:
            item.update({'timestamp': current_time, 'start': query.get_start_timestamp(), 'end': query.get_end()})
            self.db.rpush("{}_{}".format(key_prefix, 'stats'), json.dumps(item))
            sum_dp += item['emittedDPs']

        # Set TTL if supplied
        if self.ttl:
            if self.db.ttl("{}_{}".format(key_prefix, 'stats')) == -1:
                self.db.expire("{}_{}".format(key_prefix, 'stats'), self.ttl)

        self.DATAPOINTS_SERVED_COUNT.inc(sum_dp)

        global_stats = {
            'emittedDPs': sum_dp,
            'duration': duration,
            'timestamp': current_time
        }

        if not self.db.hexists("{}_{}".format(key_prefix, interval), 'first_occurrence'):
            global_stats['first_occurrence'] = current_time

        self.db.hmset("{}_{}".format(key_prefix, interval), global_stats)

        # Set TTL if supplied
        if self.ttl:
            if self.db.ttl("{}_{}".format(key_prefix, interval)) == -1:
                self.db.expire("{}_{}".format(key_prefix, interval), self.ttl)

        logging.info("[{}] emittedDPs: {}".format(query.get_id(), sum_dp))
        logging.info("[{}] duration: {}".format(query.get_id(), duration))

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

        logging.info("[{}] stats saved".format(query.get_id()))

        now_time = int(round(time.time() * 1000))
        logging.debug("Time spent in save_stats: {} ms".format(now_time - current_time_milli))

    def save_stats_timeout(self, query, duration):

        try:
            self.db.ping()
        except Exception as e:
            logging.error("Redis server connection issue: {}".format(e))
            return

        current_time = int(round(time.time()))
        end_time = query.get_end_timestamp()
        interval = int((end_time - query.get_start_timestamp()) / 60)
        logging.info("[{}] start: {}, end: {}, interval: {} minutes".format(query.get_id(), int(query.get_start_timestamp()), end_time, interval))

        key = "{}_{}".format(query.get_id(), interval)

        stats = {
            'duration': duration,
            'timestamp': current_time
        }

        self.db.hmset(key, stats)

        # Set TTL if supplied
        if self.ttl:
            if self.db.ttl(key) == -1:
                self.db.expire(key, self.ttl)

        logging.info("[{}] duration: {}".format(query.get_id(), duration))
        logging.info("[{}] stats saved".format(query.get_id()))

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

        return json.dumps(data)
