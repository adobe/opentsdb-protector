import logging
import time
from result import Ok, Err
import re
import pickledb

from protector.guard.guard import Guard
#from protector.sanitizer.sanitizer import Sanitizer


class Protector(object):
    """
    The main protector class which checks for malicious queries
    """

    db = None

    def __init__(self, rules, blacklist=[], safe_mode=False):
        """
        :param rules: A list of rules to evaluate
        :param safe_mode: If set to True, allow the query in case it can not be parsed
        :return:
        """
        self.guard = Guard(rules)
        #self.sanitizer = Sanitizer()
        self.blacklist = blacklist
        self.safe_mode = safe_mode

        self.db = pickledb.load('/tmp/test.db', False, True)

        # Dump all query ids
        #logging.debug(pprint.pprint(self.db.getall()))

    def check(self, query):
        logging.debug("Checking OpenTSDBQuery: {}".format(query.get_id()))
        #query_sanitized = self.sanitizer.sanitize(query_string)
        #query = self.parser.parse(query_sanitized)

        # Skip check if Safe mode is on
        if self.safe_mode:
            return Ok(True)

        if query:
            qs_names = query.get_metric_names()
            for pattern in self.blacklist:
                for qn in qs_names:
                    match = re.match(pattern, qn)
                    if match:
                        return Err("Metric name: {} is blacklisted".format(qn))

            self.load_stats(query)
            return self.guard.is_allowed(query)
        else:
            error_msg = "Empty OpenTSDBQuery provided!"
            logging.info(error_msg)
            return Err(error_msg)

    def save_stats(self, query, response):

        current_time = int(round(time.time()))
        interval = int((current_time - query.get_start_timestamp()) / 60)
        logging.info("[{}] start: {}, end: {}, interval: {} minutes".format(query.get_id(), int(query.get_start_timestamp()), current_time, interval))

        stats = response.get_stats()
        key = "{}_{}".format(query.get_id(), interval)

        for item in stats:
            item.update({'timestamp': current_time, 'start': query.get_start_timestamp(), 'end': query.get_end()})

        if self.db.exists(query.get_id()):
            self.db.lextend(query.get_id(), stats)
            if not self.db.exists(key):
                self.db.dcreate(key)
        else:
            self.db.lcreate(query.get_id())
            self.db.lextend(query.get_id(), stats)
            self.db.dcreate(key)

        sum_dp = 0
        for x in stats:
            sum_dp += x['emittedDPs']

        self.db.dadd(key, ('emittedDPs', sum_dp))

        logging.info("[{}] emittedDPs: {}".format(query.get_id(), sum_dp))

        self.db.dump()

        logging.info("[{}] stats saved".format(query.get_id()))

    def load_stats(self, query):

        current_time = int(round(time.time()))

        interval = int((current_time - query.get_start_timestamp()) / 60)
        key = "{}_{}".format(query.get_id(), interval)

        if self.db.exists(key):
            logging.info("[{}] Found previous stats for this interval: {} minutes".format(query.get_id(), interval))
            query.set_stats(self.db.get(key))

