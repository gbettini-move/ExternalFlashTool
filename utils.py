HEADER_MAP = {

    "Page n.":         "Page n.",
    "Record n.":       "Record n.",
    "Date":            "time",
    "Time":            "time",
    "Temperature":     "temperature",
    "Vertical Axis":   "verticalAxis",
    "Alpha 1":         "alpha1",
    "Alpha 2":         "alpha2",
    "Alpha 3":         "alpha3",
    "Acc. Peak":       "axePeak",
    "Acc. RMS":        "axeRms",
    "Avg. Samples":    "avgSamp",
    "Full scale":      "range",
    "Acc. Threshold":  "axeTh",

}

def search_in(rec_content: dict, header: str):

    key = HEADER_MAP.get(header)
    if key is None:
        return None # header not recognized
    if header == "Date":
        return rec_content.get(key)[:10]
    if header == "Time":
        return rec_content.get(key)[11:]
    else:
        return rec_content.get(key)
    