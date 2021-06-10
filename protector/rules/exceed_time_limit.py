#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

from result import Ok, Err
from protector.rules.rule import Rule
import time


class RuleChecker(Rule):

    def __init__(self, conf):

        # adaptive multiplier. ie. 1 means query is throttled by an amount of time equal to previous execution time
        # preeempts static throttling
        self.adaptive = conf.get('adaptive', 0)

        # static throttling
        if not self.adaptive:
            self.max_duration = conf.get('limit')
            self.throttle_duration = conf.get('throttle')

    @staticmethod
    def description():
        return "Throttle lengthy queries"

    @staticmethod
    def reason():
        return ["Such queries can bring down the time series database",
                "usually performing long and inefficient scans or aggregations"]

    def check(self, query):
        """
        :param query OpenTSDBQuery
        """
        stats = query.get_stats()
        current_time = int(round(time.time()))

        if stats:
            duration = float(stats.get('duration', 0))
            last_occurence = int(stats.get('timestamp', 0))
            elapsed = current_time - last_occurence

            if self.adaptive:
                adaptive_throttle_duration = duration * self.adaptive
                if elapsed < adaptive_throttle_duration:
                    remaining = adaptive_throttle_duration - elapsed
                    return Err("Adaptive throttling: {}x Last duration: {}s Throttling ends in {}s".format(self.adaptive, duration, remaining))
            else:
                if self.max_duration <= duration:
                    if elapsed < self.throttle_duration:
                        remaining = self.throttle_duration - elapsed
                        return Err("Query duration exceeded: {}s Limit: {}s Throttling ends in {}s".format(duration, self.max_duration, remaining))

        return Ok(True)
