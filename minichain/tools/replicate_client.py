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


def replace_files_by_data_recursive(data):
    if isinstance(data, str) and os.path.isfile(data):
        # Check if the file is in a subdir of cwd
        abs_path = os.path.abspath(data)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            raise Exception("Permission denied - you can only access files in the current working directory.")
        return open(data, "rb")
    elif isinstance(data, dict):
        for key, value in data.items():
            data[key] = replace_files_by_data_recursive(value)
        return data
    elif isinstance(data, list):
        return [replace_files_by_data_recursive(i) for i in data]
    else:
        return data

from urllib.request import urlretrieve
import uuid

def replace_urls_by_url_and_local_file_recursive(data, download_dir):
    print("replace_urls_by_url_and_local_file_recursive", download_dir)
    if isinstance(data, str) and data.startswith("http"):
        # Download the file and return a dict with url and local file
        extension = data.split(".")[-1]
        os.makedirs(download_dir, exist_ok=True)
        file_id = str(len(os.listdir(download_dir)) + 1)
        local_file = f"{download_dir}/{file_id}.{extension}"
        urlretrieve(data, local_file)
        return {
            "url": data,
            "local_file": local_file,
        }
    elif isinstance(data, dict):
        for key, value in data.items():
            data[key] = replace_urls_by_url_and_local_file_recursive(value, download_dir=download_dir)
        return data
    elif isinstance(data, list):
        return [replace_urls_by_url_and_local_file_recursive(i, download_dir=download_dir) for i in data]
    else:
        return data




def replicate_model_as_tool(model_id, download_dir, name=None):
    print("replicate_model_as_tool", download_dir)
    openapi = get_model_details(model_id)
    async def replicate_tool(**kwargs):
        """Replicate model"""
        # Upload all files referenced in the input
        kwargs = replace_files_by_data_recursive(kwargs)
        output = use_model(model_id, kwargs)
        return replace_urls_by_url_and_local_file_recursive(output, download_dir=download_dir)
    replicate_tool.__name__ = name or model_id.split(":")[0]
    replicate_tool.__doc__ = "Use the replicate model: " + model_id.split(":")[0]
    replicate_tool = Function(
        openapi=openapi,
        function=replicate_tool,
        name=replicate_tool.__name__,
        description=replicate_tool.__doc__,
    )
    return replicate_tool



