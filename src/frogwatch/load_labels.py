
FW_FOLDERS = "folders"
FW_RESULT = "result"
FW_STATION = "station"
FW_OBSERVATION = "observation"
FW_LABEL = "label"
FW_NAME = "name"
FW_VALUES = "values"
FW_FIELDS = "fields"

def load_labels(body: dict) -> dict[str, dict[str, str]]:
    """Load the mappings from the codes used in the database to the labels
    people are used to seeing, for the coded fields in the schema.
    Returns a dict mapping the field name to a dict mapping each db value to
    its label.
    """
    labels = defaultdict(dict)
    result = body[FW_RESULT]
    station_folders = result[FW_STATION][FW_FOLDERS]
    for folder in station_folders:
        labels = 
    for field in site_info["fields"].values():
        name = field["name"]
        for key, value in field.items():
            labels[name][item["value"]] = item["label"]
    return labels


def load_field_labels(body: dict) -> dict[str, dict[str, str]]:
    """Load the mappings from the codes used in the database to the labels
    people are used to seeing, for the coded fields in the schema.
    Returns a dict mapping the field name to a dict mapping each db value to
    its label.
    """
    labels = defaultdict(dict)
    result = body['result']
    station = result['station']
    site_info = station["folders"][0]
    for field in site_info["fields"].values():
        name = field["name"]
        for key, value in field.items():
            labels[name][item["value"]] = item["label"]
    return labels



