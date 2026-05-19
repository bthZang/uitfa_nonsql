from config import collection
from bson import ObjectId
from services.model_service import predict

def insert_many(records):
    if not records:
        return 0
    result = collection.insert_many(records)
    return len(result.inserted_ids)

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

def query_comments(
    faculty: str = None,
    course: str = None,
    lecturer: str = None,
    semester: str = None,
    academic_year: str = None,
    class_name: str = None,
    cursor: str = None,
    limit: int = 20
):
    filter_query = {}

    if faculty:
        filter_query["meta.faculty"] = faculty
    if course:
        filter_query["meta.course"] = course
    if lecturer:
        filter_query["meta.lecturer"] = lecturer
    if semester:
        filter_query["meta.semester"] = semester
    if academic_year:
        filter_query["meta.academic_year"] = academic_year
    if class_name:
        filter_query["meta.class"] = class_name
    if cursor:
        filter_query["_id"] = {"$gt": ObjectId(cursor)}

    docs = list(
        collection.find(
            filter_query,
            {
                "meta": 1,
                "content": 1,
                "label": 1,
                "predict": 1,
                "status": 1
            }
        )
        .sort("_id", 1)
        .limit(limit)
    )

    for d in docs:
        current_predict = d.get("predict", {})

        should_predict = (
            not d.get("status", {}).get("is_labeled", False)
            and (
                not d.get("status", {}).get("is_predicted", False)
                or current_predict.get("sentiment") in [
                    None,
                    "unknown",
                    "error"
                ]
            )
        )

        if should_predict:
            result = predict(d["content"]["comment"])

            if result and result["sentiment"] not in [
                None,
                "unknown",
                "error"
            ]:
                collection.update_one(
                    {"_id": d["_id"]},
                    {
                        "$set": {
                            "predict.sentiment": result["sentiment"],
                            "predict.aspect": result["aspect"],
                            "status.is_predicted": True
                        }
                    }
                )

                d["predict"] = result
                d["status"]["is_predicted"] = True

        d["_id"] = str(d["_id"])

    next_cursor = docs[-1]["_id"] if docs else None

    return {
        "data": docs,
        "next_cursor": next_cursor,
        "count": len(docs)
    }