import re
from datetime import datetime

import pytz

TL_SHIFTER_CHANNEL = {}
GUILD_LOCALE = {}
NEW_LINE = "\n"


SPACE_PATTERN = re.compile(r"[ \t　]+")
NON_DIGIT = re.compile(r"\D")
TL_SHIFTER_TIME_FORMAT = re.compile(r"(\d{1,2}):(\d{1,2})")
jst = pytz.timezone("Asia/Tokyo")
datetime_format = "%Y-%m-%d %H:%M:%S %Z"

PURIKONE_LIVE_SERVICE_DATE = datetime(year=2018, month=2, day=15)
