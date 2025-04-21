import re
from datetime import datetime

import pytz

from locales import Locale
from logger import KuriLogger

NEW_LINE = "\n"
TL_SHIFTER_CHANNEL = {}

SPACE_PATTERN = re.compile(r"[ \t　]+")
NON_DIGIT = re.compile(r"\D")
jst = pytz.timezone("Asia/Tokyo")
datetime_format = "%Y-%m-%d %H:%M:%S %Z"

locale = Locale()
logger = KuriLogger(timezone=jst.zone)

PURIKONE_LIVE_SERVICE_DATE = datetime(year=2018, month=2, day=15)
