import pandas as pd
from bson import ObjectId
from config import collection


def import_labeled_excel(file_path, mode="update"):
    df = pd.read_excel(file_path)

    updated = 0
    skipped = 0

    for _, row in df.iterrows():
        sentiment = row.get("sentiment")
        aspect = row.get("aspect")

        if pd.isna(sentiment) or pd.isna(aspect):
            skipped += 1
            continue

        doc_id = ObjectId(str(row["_id"]))

        existing = collection.find_one({"_id": doc_id})

        if not existing:
            skipped += 1
            continue

        # mode insert: skip if labeled
        if mode == "insert" and existing.get("status", {}).get("is_labeled"):
            skipped += 1
            continue

        collection.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "label.sentiment": str(sentiment),
                    "label.aspect": [
                        x.strip()
                        for x in str(aspect).split(",")
                        if x.strip()
                    ],
                    "status.is_labeled": True
                }
            }
        )

        updated += 1

    return {
        "updated": updated,
        "skipped": skipped
    }