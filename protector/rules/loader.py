#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

import logging
import importlib


def import_rules(rule_names):
    rules = {}
    for rule_name, rule_param in rule_names.items():
        try:
            rule_module = import_rule("protector.rules.{}".format(rule_name))
            if rule_param is None:
                rules[rule_name] = rule_module.RuleChecker()
            else:
                rules[rule_name] = rule_module.RuleChecker(rule_param)
        except Exception as e:
            logging.error("Could not load rule: %s. Error: %s", rule_name, e.message)
    return rules


def import_rule(path):
    """
    Load the given rule
    :param path: Import path to rule
    """
    rule = importlib.import_module(path)
    return rule
