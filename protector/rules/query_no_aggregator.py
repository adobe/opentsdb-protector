from result import Ok, Err
from protector.rules.rule import Rule


class RuleChecker(Rule):
    @staticmethod
    def description():
        return "Prevent queries with aggregator=none"

    @staticmethod
    def reason():
        return ["Such series usually indicate that the query is unfinished and ",
                "was executed by accident. To avoid the error, just remove the dot ",
                "or add another word (e.g. 'my.graphite.series.' -> 'my.graphite.series')"]

    def check(self, query):
        """
        :param query:
        """
        queries = query.get_queries()
        for q in queries:
            if q['aggregator'] == 'none':
                return Err("No aggregator specified")

        return Ok(True)
