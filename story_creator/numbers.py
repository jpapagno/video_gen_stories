"""English number readings for narration; deterministic and entirely local."""
import re

SMALL = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = [(10**15, "quadrillion"), (10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (1000, "thousand")]
MONTHS = "January February March April May June July August September October November December".split()


def cardinal(value):
    if value < 0:
        return "minus " + cardinal(-value)
    if value < 20:
        return SMALL[value]
    if value < 100:
        tens, remainder = divmod(value, 10)
        return TENS[tens] + ("-" + SMALL[remainder] if remainder else "")
    if value < 1000:
        hundreds, remainder = divmod(value, 100)
        return SMALL[hundreds] + " hundred" + (" and " + cardinal(remainder) if remainder else "")
    if value >= 10**18:
        return " ".join(SMALL[int(digit)] for digit in str(value))
    for scale, name in SCALES:
        if value >= scale:
            quotient, remainder = divmod(value, scale)
            joiner = " and " if remainder < 100 else " "
            return cardinal(quotient) + " " + name + (joiner + cardinal(remainder) if remainder else "")


def ordinal(value):
    words = cardinal(value)
    match = re.search(r"[a-z]+$", words)
    last = match.group()
    special = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
    ending = special.get(last, last[:-1] + "ieth" if last.endswith("y") else last + "th")
    return words[:match.start()] + ending


def spell_numbers(text):
    months = "|".join(MONTHS)

    def date(match):
        day = int(match[2])
        return match[1] + " the " + ordinal(day) if 1 <= day <= 31 else match[0]

    text = re.sub(rf"\b({months})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", date, text, flags=re.I)

    def day_first(match):
        day = int(match[1])
        return "the " + ordinal(day) + " of " + match[2] if 1 <= day <= 31 else match[0]

    text = re.sub(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({months})\b", day_first, text, flags=re.I)

    def clock(match):
        hour, minute = int(match[1]), int(match[2])
        if hour > 23 or minute > 59:
            return match[0]
        spoken_hour = cardinal(hour % 12 or 12)
        if minute == 0:
            return spoken_hour + " o’clock"
        if minute == 15:
            return "quarter past " + spoken_hour
        if minute == 30:
            return "half past " + spoken_hour
        if minute == 45:
            return "quarter to " + cardinal((hour + 1) % 12 or 12)
        return spoken_hour + (" oh " if minute < 10 else " ") + cardinal(minute)

    text = re.sub(r"\b(\d{1,2}):(\d{2})\b", clock, text)
    text = re.sub(r"\b(\d+)\s*[-–]\s*(\d+)\b", r"\1 to \2", text)

    def number(match):
        token = match[0].replace(",", "")
        percent = token.endswith("%")
        token = token.rstrip("%")
        suffix = re.search(r"(st|nd|rd|th)$", token, re.I)
        if suffix:
            result = ordinal(int(token[:-2]))
        elif "." in token:
            whole, fraction = token.split(".")
            result = ("minus " if whole.startswith("-") else "") + cardinal(abs(int(whole)))
            result += " point " + " ".join(SMALL[int(digit)] for digit in fraction)
        else:
            result = cardinal(int(token))
        return result + (" per cent" if percent else "")

    return re.sub(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?(?:st|nd|rd|th)?%?(?!\w)", number, text, flags=re.I)
