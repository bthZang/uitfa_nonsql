import requests

MODEL_URL = "http://localhost:8002/predict"


def predict(comment: str):
    try:
        res = requests.post(
            MODEL_URL,
            json={"text": comment},
            timeout=5
        )
        data = res.json()

        return {
            "sentiment": data.get("sentiment"),
            "aspect": data.get("aspect", [])
        }

    except Exception as e:
        print("Model error:", e)
        return {
            "sentiment": "unknown",
            "aspect": []
        }