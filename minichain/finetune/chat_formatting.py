from typing import Dict, List, Optional, Tuple, Union
import json
import xml.etree.ElementTree as ET
import os
from minichain.finetune.pydantic_to_example import pydantic_to_example


def function_call_formatter(function_call: Dict) -> str:
    pass


def message_formatter(message: Dict, function_call_formatter) -> str:
    pass


def functions_formatter(functions: List[Dict], function_call_formatter=None) -> str:
    pass


def conversation_formatter(messages: Dict, functions: List, message_formatter, functions_formatter, function_call_formatter) -> str:
    """Adds the function definitions to the system message and formats the chat using the specified formatters"""
    system_prompt_addition = "\n\nYou have access to the following functions:\n"
    for function in functions:
        system_prompt_addition += f"{functions_formatter(function, function_call_formatter)}\n"
    system_prompt_addition += "\nRespond in the following syntax:\n"
    system_prompt_addition += "<function_call> ...arguments </function_call>\n"
    
    text = ""
    for message in messages:
        if message['role'] == 'system':
            message = message.copy()
            message['content'] += system_prompt_addition
            system_prompt_addition = ""
        text += message_formatter(message, function_call_formatter)
    return text
    

def get_messages(conversation):
    return [i.as_json()['chat'] for i in conversation.messages]



def dict_to_xml(tag, d):
    """
    Convert a dictionary or list to an XML string.
    Args:
    - tag: the root tag name
    - d: the dictionary or list to convert
    """
    elem = ET.Element(tag)
    if isinstance(d, dict):
        for key, val in d.items():
            child = dict_to_xml(key, val)
            elem.append(child)
    elif isinstance(d, list):
        for item in d:
            child = dict_to_xml('item', item)
            elem.append(child)
    else:
        elem.text = str(d)
    return elem


def convert_to_xml(data):
    """
    Convert a JSON-like structure to an XML string.
    Args:
    - data: the JSON-like structure (dict or list)
    """
    xml_elem = dict_to_xml('function_call', data)
    # convert to string with newline pretty-printing
    ET.indent(xml_elem)
    return ET.tostring(xml_elem, encoding='unicode', method='xml', short_empty_elements=False)


def function_call_to_xml(function_call: Dict) -> str:
    return convert_to_xml(function_call)


def function_call_to_json(function_call: Dict, function_call_formatter=None) -> str:
    return json.dumps(function_call, indent=4)


def message_to_chatml(message: Dict, function_call_formatter) -> str:
    content = message['content']
    role = message['role']
    if message.get('function_call') is not None:
        content += function_call_formatter(message['function_call'])
    if message.get('name') is not None:
        role += f" {message['name']}"
    
    text = f"""<|im_start|>{role}
{content}<|im_end|>
"""
    return text


def functions_to_openapi(function: Dict, function_call_formatter) -> str:
    data = {
        "name": function.name,
        "arguments": function.pydantic_model.model_json_schema(),
    }
    return json.dumps(data, indent=4)


def debug(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            for arg in args:
                print(arg)
                input()
            for key, value in kwargs.items():
                print(key, value)
                input()
    return wrapper



def functions_to_example(function: Dict, function_call_formatter) -> str:
    """Generate an example function call with values replaced by type + description infos"""
    text = f"{function.name} - {function.description}\n"
    function_call = {
        "name": function.name,
        "arguments": pydantic_to_example(function.pydantic_model)
    }
    text += function_call_formatter(function_call) + "\n"
    return text


def all_formatters():
    for function_call_formatter in [function_call_to_json, function_call_to_xml]:
        for message_formatter in [message_to_chatml]:
            for functions_formatter in [functions_to_openapi, functions_to_example]:
                name = f"{message_formatter.__name__}_{functions_formatter.__name__}_{function_call_formatter.__name__}"
                yield name, lambda messages, functions: conversation_formatter(messages, functions, message_formatter, functions_formatter, function_call_formatter)


from minichain import settings
from minichain.functions import tool, Field
@tool()
async def upload_file_to_chat(
    file: str = Field(..., description="The path to the file to upload."),
):
    """Upload a file to the chat."""
    return f"displaying file: {file}"

agents = settings.load_agents_into_dict()
def get_conversation_functions(conversation):
    return agents[conversation.meta['agent']].functions
    

def message_db_to_dataset(message_db, dataset_dir):
    os.makedirs(dataset_dir, exist_ok=True)
    for format_name, formatter in all_formatters():
        base_dir = os.path.join(dataset_dir, format_name)
        os.makedirs(base_dir, exist_ok=True)
        for i, conversation in enumerate(message_db.conversations):
            functions = get_conversation_functions(conversation)
            text = formatter(get_messages(conversation), functions)
            with open(os.path.join(base_dir, f"{i}.txt"), "w") as f:
                f.write(text)
            
def example():
    from minichain.message_handler import MessageDB
    messages_folder = "/Users/nielswarncke/Documents/agi/minichain/demo/text-entropy-heatmap/.minichain/messages"
    message_db = MessageDB(messages_folder)
    example_text = conversation_formatter(
        get_messages(message_db.conversations[0]),
        # [add, send_message],
        message_to_chatml,
        functions_to_example, 
        # functions_to_openapi,
        function_call_to_xml
    )
    print(example_text)
        
if __name__ == "__main__":
    from minichain.message_handler import MessageDB
    messages_folder = "/Users/nielswarncke/Documents/agi/minichain/demo/text-entropy-heatmap/.minichain/messages"
    message_db = MessageDB(messages_folder)
    message_db_to_dataset(message_db, "./dataset")
    