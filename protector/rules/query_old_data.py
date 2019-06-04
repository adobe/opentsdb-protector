from result import Ok, Err

from protector.rules.rule import Rule
import datetime


class RuleChecker(Rule):
    def __init__(self):
        # Todo: Make this configurable from config file
        self.min_start_date = datetime.datetime.now() - datetime.timedelta(days=90)

    @staticmethod
    def description():
        return "Prevent querying for very old data"

    @staticmethod
    def reason():
        return ["Such queries can bring down the time series database",
                "because it needs to open and parse very old shards from disk"]

    def check(self, query):
        """
        :param query OpenTSDBQuery
        """
        a = query.get_start_timestamp()

        jstart = datetime.datetime.fromtimestamp(float(query.get_start_timestamp()))

        if jstart >= self.min_start_date:
            return Ok(True)

        return Err(("Querying for data before {} is prohibited. "
                    "Your query start date is {}, which is before that.").format(self.min_start_date.strftime("%Y-%m-%d"), jstart.strftime("%Y-%m-%d")))
