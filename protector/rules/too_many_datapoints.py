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


class RuleChecker(Rule):

    def __init__(self, conf_datapoints):
        self.max_datapoints = conf_datapoints

    @staticmethod
    def description():
        return "Prevent too many data points per query"

    @staticmethod
    def reason():
        return ["Such queries can bring down the time series database",
                "or overload the client with too much data transferred over the wire."]

    def check(self, query):
        """
        :param query OpenTSDBQuery
        """
        stats = query.get_stats()
        if stats:

            dps = int(stats.get('emittedDPs', 0))
            if self.max_datapoints < dps:

                return Err("{} data points from that query, which is above the threshold! Limit the number of data points({}) or decrease the interval".format(dps, self.max_datapoints))
        return Ok(True)
