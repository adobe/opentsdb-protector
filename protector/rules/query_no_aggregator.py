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
    @staticmethod
    def description():
        return "Prevent queries with aggregator=none"

    @staticmethod
    def reason():
        return ["Disable fetching of raw data from the database"]

    def check(self, query):
        """
        :param query:
        """
        queries = query.get_queries()
        for q in queries:
            if q['aggregator'] == 'none':
                return Err("No aggregator specified")

        return Ok(True)
