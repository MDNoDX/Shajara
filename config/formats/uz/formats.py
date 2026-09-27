# Uzbek (Latin). Dates in the interface are rendered by apps.core.dates, which
# supports partial genealogy dates; these formats cover Django's own output.
DATE_FORMAT = r"j-E Y-\y\i\l"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = r"j-E Y-\y\i\l, H:i"
YEAR_MONTH_FORMAT = r"Y-\y\i\l F"
MONTH_DAY_FORMAT = "j-E"
SHORT_DATE_FORMAT = "d.m.Y"
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
FIRST_DAY_OF_WEEK = 1
DATE_INPUT_FORMATS = ["%d.%m.%Y", "%Y-%m-%d"]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "\xa0"
NUMBER_GROUPING = 3
