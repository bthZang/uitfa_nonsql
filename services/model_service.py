import requests

MODEL_URL = "http://localhost:9992/predict"


def predict(comment: str):
    try:
        res = requests.post(
            MODEL_URL,
            json={"feedback": comment},
            timeout=5
        )

        res.raise_for_status()

        data = res.json()
        prediction = data.get("prediction", {})

        aspect = None
        sentiment = None

        for k, v in prediction.items():
            if v is not None:
                aspect = k
                sentiment = v
                break

        if not sentiment:
            return None

        return {
            "sentiment": sentiment,
            "aspect": [aspect] if aspect else []
        }

    except Exception as e:
        print("Model error:", e)
        return None