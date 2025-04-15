import re

from locales import Locale
from logger import KuriLogger

NEW_LINE = "\n"
TL_SHIFTER_CHANNEL = {}

SPACE_PATTERN = re.compile(r'[ \t　]+')
NON_DIGIT = re.compile(r'\D')

locale = Locale()
logger = KuriLogger()