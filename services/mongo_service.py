from config import collection


def insert_many(records):
    if not records:
        return 0
    result = collection.insert_many(records)
    return len(result.inserted_ids)


def get_unlabeled(limit=100):
    docs = list(
        collection.find(
            {"status.is_labeled": False},
            {"content.comment": 1}
        ).limit(limit)
    )

    for doc in docs:
        doc["_id"] = str(doc["_id"])

    return docs


def update_label(_id, sentiment, aspect):
    collection.update_one(
        {"_id": _id},
        {
            "$set": {
                "label.sentiment": sentiment,
                "label.aspect": aspect,
                "status.is_labeled": True
            }
        }
    )


def query_comments(filter_query, skip, limit):
    return list(collection.find(filter_query).skip(skip).limit(limit))