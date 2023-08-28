import replicate
import requests
import os
from minichain.agent import Function
from dotenv import load_dotenv
load_dotenv()


def get_model(model_id):
    model_id, version_id = model_id.split(":")
    model = replicate.models.get(model_id)
    version = model.versions.get(version_id)
    return version


def get_model_details(model_id):
    return get_model(model_id).openapi_schema['components']['schemas']['Input']


def use_model(model_id, input):
    version = get_model(model_id)
    prediction = replicate.predictions.create(version=version, input=input)
    prediction.wait()
    return prediction.output


def replicate_model_as_tool(model_id, name=None):
    openapi = get_model_details(model_id)
    async def replicate_tool(**kwargs):
        """Replicate model"""
        return use_model(model_id, kwargs)
    replicate_tool.__name__ = name or model_id.split(":")[0]
    replicate_tool.__doc__ = "Use the replicate model: " + model_id.split(":")[0]
    replicate_tool = Function(
        openapi=openapi,
        function=replicate_tool,
        name=replicate_tool.__name__,
        description=replicate_tool.__doc__,
    )
    return replicate_tool



