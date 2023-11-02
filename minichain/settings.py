import os
import yaml

SERVE_PATH = ".public"
DOMAIN = os.environ.get("DOMAIN", "http://localhost:8745")
SERVE_URL = f"{DOMAIN}/.public/"

default_memory = None


def set_default_memory(SemanticParagraphMemory):
    global default_memory
    default_memory = SemanticParagraphMemory()
    print("Set default memory to", default_memory)
    default_memory.reload()

# load the ./minichain/settings.yml file
if not os.path.exists(".minichain/settings.yml"):
    # copy the default settings file from the modules install dir (minichain/default_settings.yml) to the cwd ./minichain/settings.yml
    print("Copying default settings file to .minichain/settings.yml")
    os.makedirs(".minichain", exist_ok=True)
    import shutil

    shutil.copyfile(
        os.path.join(os.path.dirname(__file__), "default_settings.yml"),
        ".minichain/settings.yml",
    )

with open(".minichain/settings.yml", "r") as f:
    yaml = yaml.load(f, Loader=yaml.FullLoader)