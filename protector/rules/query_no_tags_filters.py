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
