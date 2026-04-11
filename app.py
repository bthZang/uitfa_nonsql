from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import FileResponse
from services.parser import parse_excel
from services.mongo_service import (
    insert_many,
    get_unlabeled,
    update_label,
    query_comments
)
from services.export_service import export_unlabeled_to_csv
from services.model_service import predict
from config import collection

app = FastAPI()

@app.post("/import")
async def import_excel(file: UploadFile = File(...)):
    contents = await file.read()
    records = parse_excel(contents)
    count = insert_many(records)

    return {"inserted": count}

@app.post("/import-labeled")
async def import_labeled(file: UploadFile = File(...)):
    contents = await file.read()
    records = parse_excel(contents, labeled=True)
    count = insert_many(records)

    return {"inserted": count}

@app.get("/unlabeled")
def unlabeled(limit: int = 100):
    return get_unlabeled(limit)


@app.post("/model/predict")
def run_model(limit: int = 20):
    docs = collection.find({"status.is_labeled": False}).limit(limit)

    updated = 0
    for d in docs:
        result = predict(d["content"]["comment"])
        update_label(d["_id"], result["sentiment"], result["aspect"])
        updated += 1

    return {"updated": updated}


@app.get("/export")
def export():
    file_path = export_unlabeled_to_csv()
    return FileResponse(file_path, filename="unlabeled.csv")


@app.get("/comments")
def get_comments(
    faculty: str = None,
    course: str = None,
    lecturer: str = None,
    skip: int = 0,
    limit: int = 20
):
    filter_query = {}

    if faculty:
        filter_query["meta.faculty"] = faculty
    if course:
        filter_query["meta.course"] = course
    if lecturer:
        filter_query["meta.lecturer"] = lecturer

    return query_comments(filter_query, skip, limit)


@app.get("/stats")
def stats():
    pipeline = [
        {
            "$group": {
                "_id": "$label.sentiment",
                "count": {"$sum": 1}
            }
        }
    ]
    return list(collection.aggregate(pipeline))