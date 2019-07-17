#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

class Rule(object):
    @staticmethod
    def description():
        """
        :return: A short description of the rule
        """
        pass

    @staticmethod
    def reason():
        """
        When and why the rule is useful.

        This should return a list of lines instead of a long string.
        It's easier to format line breaks this way.

        :return: The reason for the rule
        """
        pass

    def check(self, query):
        """
        Check if a given query is permitted
        :param query:
        :return: result.Ok() if permitted, result.Err() if not.
        """
        pass
