from minichain.functions import tool
from minichain import settings
import shutil
import os

from pydantic import BaseModel, Field

@tool()
async def deploy_static_website(
    path: str = Field(
        None, description="The path to the file or directory that should be served"
    )
):
    """Serve a file or directory via a public static file server"""
    new_public_path = path.split("/")[-1]
    target, v = os.path.join(settings.SERVE_PATH, new_public_path ), 0
    while os.path.exists(target):
        new_public_path = path.split("/")[-1] + f"_{v}"
        target = os.path.join(settings.SERVE_PATH, new_public_path )
        v += 1
    shutil.copytree(path, target)
    public_url = settings.SERVE_URL + new_public_path
    return f"Your file(s) are now available [here]({public_url})"