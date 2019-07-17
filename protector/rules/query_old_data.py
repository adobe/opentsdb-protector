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
import datetime


class RuleChecker(Rule):
    def __init__(self, conf_days):
        self.min_start_date = datetime.datetime.now() - datetime.timedelta(days=conf_days)

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
