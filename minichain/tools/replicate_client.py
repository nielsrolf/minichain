import replicate
import requests


def search_for_model(task):
    pass


def get_model_details(model_id):
    """
    curl -s \
    -H "Authorization: Token $REPLICATE_API_TOKEN" \
    -H 'Content-Type: application/json' \
    "https://api.replicate.com/v1/models/{model_id}"
    """
    response = requests.get(
        "https://api.replicate.com/v1/models/{model_id}".format(model_id=model_id),
        headers={
            "Authorization": "Token $REPLICATE_API_TOKEN",
            "Content-Type": "application/json",
        },
    )
    return response.json()


def use_model(model_id, input):
    model = replicate.models.get("kvfrans/clipdraw")
    version = model.versions.get("latest")
    prediction = replicate.predictions.create(version=version, input=input)
    prediction.wait()
    return prediction.output
