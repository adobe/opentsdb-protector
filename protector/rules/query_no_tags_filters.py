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
        return "Prevent no tag/filter queries"

    @staticmethod
    def reason():
        return ["Encourage clients to use filters or tags in their queries to restrict the potential data set"]

    def check(self, query):
        """
        :param query: OpenTSDBQuery
        """
        queries = query.get_queries()
        for q in queries:
            if not (len(q.get('tags', [])) or len(q.get('filters', []))):
                return Err("Both tags and filters are empty")

        return Ok(True)
