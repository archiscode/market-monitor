
SIC_DIVISIONS = {
    "43": "Specialised construction activities",
    "46": "Wholesale trade",
    "47": "Retail trade",
    "56": "Food and beverage service activities",
    "62": "Computer programming and consultancy",
    "64": "Financial service activities",
    "68": "Real estate activities",
    "70": "Head offices and management consultancy",
    "71": "Architecture and engineering activities",
    "74": "Other professional and technical activities",
    "96": "Other personal service activities",
}


def get_industry_name(division):
    """Return the industry name for a SIC division."""

    return SIC_DIVISIONS.get(
        str(division),
        "Other or unclassified industry"
    )
