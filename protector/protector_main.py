import logging
import time
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

    def __init__(self, rules, blacklist=[], db_config={}, safe_mode=False):
        """
        :param rules: A list of rules to evaluate
        :param blacklist: A list of metric names to blacklist
        :param safe_mode: If set to True, allow the query in case it can not be parsed
        :return:
        """
        self.guard = Guard(rules)

        self.blacklist = blacklist
        self.safe_mode = safe_mode

        self.db = redis.Redis(
            host=db_config['redis']['host'],
            port=db_config['redis']['port'],
            password=db_config['redis']['password'])

        self.REQUESTS_COUNT = Counter('requests_total', 'Total number of requests')
        self.REQUESTS_BLOCKED = Counter('requests_blocked', 'Total number of blocked requests')
        self.REQUESTS_BLACKLISTED_MATCHED = Counter('requests_blacklisted_matched', 'Total number of blacklisted matched requests')

        self.EXCEED_TIME_LIMIT_COUNT = Counter('exceed_time_limit_count', 'exceed_time_limit rule match count')
        self.QUERY_NO_AGGREGATOR_COUNT = Counter('query_no_aggregator_count', 'query_no_aggregator rule match count')
        self.QUERY_NO_TAGS_FILTERS_COUNT = Counter('query_no_tags_filters_count', 'query_no_tags_filters rule match count')
        self.QUERY_OLD_DATA_COUNT = Counter('query_old_data_count', 'query_old_data rule match count')
        self.TOO_MANY_DATAPOINTS_COUNT = Counter('too_many_datapoints_count', 'too_many_datapoints rule match count')
        self.EXCEED_FREQUENCY_COUNT = Counter('exceed_frequency_count', 'exceed_frequency rule match count')

        self.DATAPOINTS_SERVED_COUNT = Counter('datapoints_served_count', 'datapoints served count')

        self.TSDB_REQUEST_LATENCY = Histogram('tsdb_request_latency_seconds', 'OpenTSDB Requests latency histogram')

    def check(self, query):

        # Skip check if Safe mode is on
        if self.safe_mode:
            return Ok(True)

        logging.debug("Checking OpenTSDBQuery: {}".format(query.get_id()))

        if query:
            qs_names = query.get_metric_names()
            for pattern in self.blacklist:
                for qn in qs_names:
                    match = re.match(pattern, qn)
                    if match:
                        self.REQUESTS_BLACKLISTED_MATCHED.inc()
                        return Err({"msg": "Metric name: {} is blacklisted".format(qn)})

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
            self.db.set("{}_{}".format(key_prefix, 'query'), json.dumps(query.q))

        sum_dp = 0
        for item in stats:
            item.update({'timestamp': current_time, 'start': query.get_start_timestamp(), 'end': query.get_end()})
            self.db.rpush("{}_{}".format(key_prefix, 'stats'), json.dumps(item))
            sum_dp += item['emittedDPs']

        self.DATAPOINTS_SERVED_COUNT.inc(sum_dp)

        global_stats = {
            'emittedDPs': sum_dp,
            'duration': duration,
            'timestamp': current_time
        }
        self.db.hmset("{}_{}".format(key_prefix, interval), global_stats)

        logging.info("[{}] emittedDPs: {}".format(query.get_id(), sum_dp))
        logging.info("[{}] duration: {}".format(query.get_id(), duration))

        # self.db.bgsave() - Unsupported without persistence layer in Azure
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

        self.db.rpush(key, json.dumps(stats))

        logging.info("[{}] duration: {}".format(query.get_id(), duration))

        # self.db.bgsave() - Unsupported without persistence layer in Azure

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

