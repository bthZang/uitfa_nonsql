from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import FileResponse
from services.parser import parse_excel
from services.mongo_service import (
    insert_many,
    update_label,
    query_comments
)
from services.export_service import export_csv
from services.model_service import predict
from services.import_service import import_labeled_excel
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
        "use_case": "raw_import",
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
async def import_labeled(
    file: UploadFile = File(...),
    mode: str = "update"
):
    contents = await file.read()

    file_hash = calculate_file_hash(contents)

    insert_result = db.import_files.insert_one({
        "file_name": file.filename,
        "file_hash": file_hash,
        "use_case": "labeled_import",
        "mode": mode,
        "status": "PROCESSING",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    try:
        temp_path = "temp_labeled.xlsx"

        with open(temp_path, "wb") as f:
            f.write(contents)

        result = import_labeled_excel(temp_path, mode)

        db.import_files.update_one(
            {"_id": insert_result.inserted_id},
            {
                "$set": {
                    "status": "SUCCESS",
                    "total_records": result["updated"],
                    "skipped_records": result["skipped"],
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {
            "message": "Labeled data imported successfully",
            **result
        }

    except Exception as e:
        db.import_files.update_one(
            {"_id": insert_result.inserted_id},
            {
                "$set": {
                    "status": "FAILED",
                    "error": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        raise e
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
def export(mode: str = "labeling"):
    file_path = export_csv(mode)
    return FileResponse(file_path, filename=file_path)


@app.get("/comments")
def get_comments(
    faculty: str = None,
    course: str = None,
    lecturer: str = None,
    class_name: str = None,
    semester: str = None,
    academic_year: str = None,
    cursor: str = None,
    limit: int = Query(default=20, le=100)
):
    return query_comments(
        faculty=faculty,
        course=course,
        lecturer=lecturer,
        class_name=class_name,
        semester=semester,
        academic_year=academic_year,
        cursor=cursor,
        limit=limit
    )

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