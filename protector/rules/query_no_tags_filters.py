from result import Ok, Err
from protector.rules.rule import Rule


class RuleChecker(Rule):
    @staticmethod
    def description():
        return "Prevent no tag/filter queries"

    @staticmethod
    def reason():
        return ["Drop queries mean data loss. This is a risky operation that should be restricted to admin users"]

    def check(self, query):
        """
        :param query:
        """
        queries = query.get_queries()
        for q in queries:
            if not (len(q.get('tags',[])) or len(q.get('filters',[]))):
                return Err("Both tags and filters are empty")

        return Ok(True)
