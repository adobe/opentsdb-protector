from result import Ok, Err
from protector.rules.rule import Rule
import time


class RuleChecker(Rule):

    def __init__(self, conf_freq):
        self.min_freq = conf_freq

    @staticmethod
    def description():
        return "Prevent query flooding"

    @staticmethod
    def reason():
        return ["Such queries can bring down the time series database",
                "usually performing long and inefficient scans or aggregations"]

    def check(self, query):
        """
        :param query OpenTSDBQuery
        """
        stats = query.get_stats()
        if stats:

            current_time = int(round(time.time()))
            timestamp = int(stats.get('timestamp', 0))
            if (current_time - timestamp) <= self.min_freq:
                return Err("Query frequency exceeded: {}s Limit: {}s".format(current_time - timestamp, self.min_freq))
        return Ok(True)
