import pandas as pd
from config import collection


def export_unlabeled_to_csv(file_path="unlabeled.csv"):
    data = list(collection.find({"status.is_labeled": False}))

    rows = []
    for d in data:
        rows.append({
            "comment": d["content"]["comment"],
            "faculty": d["meta"]["faculty"],
            "course": d["meta"]["course"],
            "lecturer": d["meta"]["lecturer"],
        })

    df = pd.DataFrame(rows)
    df.to_csv(file_path, index=False)
    return file_path