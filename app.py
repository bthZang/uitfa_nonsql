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
from config import db, collection
import hashlib
from datetime import datetime

app = FastAPI()

@app.post("/import")
async def import_excel(file: UploadFile = File(...)):
    contents = await file.read()

    file_hash = calculate_file_hash(contents)

    existing = db.import_files.find_one({"file_hash": file_hash})
    if existing:
        return {
            "message": "File already imported",
            "file_name": existing.get("file_name"),
            "total_records": existing.get("total_records", 0)
        }

    insert_result = db.import_files.insert_one({
        "file_name": file.filename,
        "file_hash": file_hash,
        "status": "PROCESSING",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    try:
        # parse
        records = parse_excel(contents)

        # insert data
        count = insert_many(records)

        # update SUCCESS
        db.import_files.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {
                "status": "SUCCESS",
                "total_records": count,
                "updated_at": datetime.utcnow()
            }}
        )

        return {"inserted": count}

    except Exception as e:
        # update FAILED
        db.import_files.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {
                "status": "FAILED",
                "error": str(e),
                "updated_at": datetime.utcnow()
            }}
        )
        raise e

@app.post("/import-labeled")
async def import_labeled(file: UploadFile = File(...)):
    contents = await file.read()

    file_hash = calculate_file_hash(contents)

    existing = db.import_files.find_one({"file_hash": file_hash})
    if existing:
        return {
            "message": "File already imported",
            "file_name": existing.get("file_name"),
        }

    insert_result = db.import_files.insert_one({
        "file_name": file.filename,
        "file_hash": file_hash,
        "status": "PROCESSING",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    try:
        records = parse_excel(contents, labeled=True)
        count = insert_many(records)

        db.import_files.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {
                "status": "SUCCESS",
                "total_records": count,
                "updated_at": datetime.utcnow()
            }}
        )

        return {"inserted": count}

    except Exception as e:
        db.import_files.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {
                "status": "FAILED",
                "error": str(e),
                "updated_at": datetime.utcnow()
            }}
        )
        raise e

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

def calculate_file_hash(content: bytes):
    return hashlib.md5(content).hexdigest()