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
