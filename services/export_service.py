import pandas as pd
from config import collection


def export_csv(mode="labeling"):
    rows = []

    if mode == "labeling":
        data = list(
            collection.find({"status.is_labeled": False})
        )

        for d in data:
            rows.append({
                "_id": str(d["_id"]),
                "feedback": d["content"]["comment"],
                "aspect": "",
                "sentiment": "",
            })

        file_path = "labeling_data.xlsx"

    elif mode == "training":
        data = list(
            collection.find({"status.is_labeled": True})
        )

        for d in data:
            rows.append({
                "feedback": d["content"]["comment"],
                "aspect": ",".join(
                    d["label"].get("aspect", [])
                ),
                "sentiment": d["label"].get("sentiment", ""),
            })

        file_path = "training_data.xlsx"

    else:
        raise ValueError("Invalid mode")

    df = pd.DataFrame(rows)
    df.to_excel(file_path, index=False)
    return file_path