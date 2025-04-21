from typing import get_args

from enums import HelpTopic


def test_help_topic():
    help_topic = HelpTopic()
    keys = help_topic.get_keys()

    assert "cb-report-symbol" in get_args(keys)
    assert (
        help_topic.get_value("cb-report-symbol") == help_topic.DATA["cb-report-symbol"]
    )
