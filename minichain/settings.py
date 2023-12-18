import os
import yaml
from typing import Dict, List


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


def load_agents_into_dict(agents: Dict = None, add_functions: List = None):
    agents = agents or {}
    add_functions = add_functions or []
    for agent_name, agent_settings in yaml.get("agents", {}).items():
        if not agent_settings.get("display", False):
            continue
        try:
            print("Loading agent", agent_name)
            class_name = agent_settings.pop("class")
            # class name is e.g. minichain.agents.programmer.Programmer
            # import the agent class
            module_name, class_name = class_name.rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            # create the agent
            print("Creating agent", agent_name, agent_class, agent_settings)
            agent = agent_class(**agent_settings.get("init", {}))
            # add the agent to the agents dict
            agents[agent_name] = agent
        except Exception as e:
            print("Error loading agent", agent_name, e)

    for agent in list(agents.values()):
        agent.functions.extend(add_functions)
    for agent in list(agents.values()):
        agents[agent.name] = agent
    return agents