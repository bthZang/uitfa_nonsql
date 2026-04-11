import pandas as pd
import re
import unicodedata
from datetime import datetime, timezone


# =========================
# CONFIG
# =========================
COLUMN_KEYWORDS = {
    "comment": [
        "ý kiến",
        "nhận xét",
        "feedback",
        "hài lòng",
        "không hài lòng",
    ],
    "lecturer": ["giảng viên", "gv"],
    "course": ["môn"],
    "faculty": ["khoa"],
    "class": ["lớp"],
}


# =========================
# UTILS
# =========================
def normalize(text):
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text


def detect_header_row(raw_df):
    for i in range(min(20, len(raw_df))):
        row = raw_df.iloc[i].astype(str).str.lower()

        row_text = " ".join(row.tolist())

        if (
            "stt" in row_text
            and ("hài lòng" in row_text or "ý kiến" in row_text)
        ):
            return i

    return 0


def find_comment_columns(df):
    pos_col = None
    neg_col = None

    for col in df.columns:
        col_norm = normalize(col)

        if "khong hai long" in col_norm:
            neg_col = col
        elif "hai long" in col_norm:
            pos_col = col

    return pos_col, neg_col

def is_same_as_column(comment, column_name):
    c = normalize(comment).replace("/", "")
    col = normalize(column_name).replace("/", "")
    return c == col


def clean_comment(text):
    if not isinstance(text, str):
        return ""

    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_semester(text):
    text = normalize(text)

    hk = re.search(r"học kỳ\s*(\d+)", text)
    year = re.search(r"(\d{4}\s*-\s*\d{4})", text)

    if hk and year:
        return f"{year.group(1)}-{hk.group(1)}"

    return "unknown"


def extract_global_meta(raw_df):
    text = ""
    for i in range(min(5, len(raw_df))):
        text += " " + " ".join(raw_df.iloc[i].astype(str).tolist())

    return {
        "semester": parse_semester(text)
    }


# =========================
# MAIN
# =========================
def parse_excel(file, labeled=False):
    all_records = []

    xls = pd.ExcelFile(file)

    for sheet in xls.sheet_names:
        try:
            print(f"[INFO] Processing sheet: {sheet}")

            raw_df = xls.parse(sheet, header=None)

            if raw_df.dropna(how="all").empty:
                continue

            global_meta = extract_global_meta(raw_df)

            header_row = detect_header_row(raw_df)
            df = xls.parse(sheet, header=header_row)
            df.columns = [str(c).strip() for c in df.columns]

            df = df.dropna(how="all")
            if df.empty:
                continue

            df = df.ffill()

            pos_col, neg_col = find_comment_columns(df)

            if not pos_col and not neg_col:
                print(f"[WARN] Không tìm thấy cột comment ở sheet {sheet}")
                print("Columns:", list(df.columns))
                continue

            for _, row in df.iterrows():

                comments = []

                if pos_col:
                    c1 = clean_comment(row.get(pos_col, ""))
                    if c1 and not is_same_as_column(c1, pos_col):
                        comments.append(c1)

                if neg_col:
                    c2 = clean_comment(row.get(neg_col, ""))
                    if c2 and not is_same_as_column(c2, neg_col):
                        comments.append(c2)

                for comment in comments:

                    if not comment or comment.lower() == "nan":
                        continue

                    if re.match(r"^\d+([.,]\d+)?%?$", comment):
                        continue

                    if len(comment) < 2:
                        continue

                    now = datetime.now(timezone.utc).isoformat()

                    record = {
                        "meta": {
                            "semester": global_meta.get("semester", "unknown"),
                            "faculty": str(row.get("Khoa", "")).strip(),
                            "course": str(row.get("Môn học", "")).strip(),
                            "class": str(row.get("Lớp", "")).strip(),
                            "lecturer": str(row.get("Họ và tên GV", "")).strip(),
                        },
                        "content": {
                            "comment": comment,
                        },
                        "label": {
                            "sentiment": None,
                            "aspect": [],
                        },
                        "status": {
                            "is_labeled": labeled,
                            "source": "excel",
                            "version": 1,
                        },
                        "timestamps": {
                            "created_at": now,
                            "updated_at": now,
                        },
                    }

                    all_records.append(record)

        except Exception as e:
            print(f"[ERROR] Sheet {sheet}: {e}")

    return all_records