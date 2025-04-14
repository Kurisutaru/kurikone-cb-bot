import re

from locales import Locale

NEW_LINE = "\n"
TL_SHIFTER_CHANNEL = {}

SPACE_PATTERN = re.compile(r'[ \t　]+')
NON_DIGIT = re.compile(r'\D')

locale = Locale()