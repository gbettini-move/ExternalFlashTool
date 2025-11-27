HEADER_MAP = {

    "Timestamp (UTC)":     "time",
    "Temperature [°C]":    "temperature",
    "Vertical Axis":       "verticalAxis",
    "Alpha 1 [°]":         "alpha1",
    "Alpha 2 [°]":         "alpha2",
    "Alpha 3 [°]":         "alpha3",
    "Acc. Peak [mg]":      "axePeak",
    "Acc. RMS [mg]":       "axeRms",
    "Avg. Samples":        "avgSamp",
    "Full scale":          "range",
    "Acc. Threshold [mg]": "axeTh",

}

def search_in(rec_content: dict, header: str):

    key = HEADER_MAP.get(header)
    if key is None:
        return None # header not recognized
    else:
        return rec_content.get(key)
    