from pydantic import BaseModel
from typing import List, Any, Type
import json

from minichain.utils.debug import debug

@debug
def describe_field(field):
    """Describe a Pydantic model field."""
    # breakpoint()
    description = field.description or ''
    default = field.default
    field_type = field.annotation
    if "Union[" in str(field_type):
        types = str(field_type).replace("Union[", "").replace("]", "").split(", ")
        if any('NoneType' in t for t in types):
            types.remove('NoneType')
            default = "null"
        return describe_field_type(types[0], default, description)
    if "typing.Optional[" in str(field_type):
        field_type = field_type.__args__[0]
        default = "null"
        return describe_field_type(field_type, default, description)
    try:
        example = {"#type": describe_field_type(field_type, default, description)}
        example.update(pydantic_to_example(field_type))
        return example
    except Exception as e:
        pass
    if hasattr(field_type, '__origin__') and issubclass(field_type.__origin__, List):
        # List field
        item_type = field_type.__args__[0]
        return [describe_field_type(item_type, None, "Example item")]
    else:
        # Basic types (int, str, bool, etc.)
        return describe_field_type(field_type, default, description)

def describe_field_type(field_type, default, description):
    """Generate a description for a basic field type."""
    type_name = field_type.__name__ if hasattr(field_type, '__name__') else str(field_type)
    value = f"{type_name}"
    # required?
    # avoid using PydanticUndefined default
    if default is None or str(default) == 'PydanticUndefined':
        value += " (required)"
    else:
        value += f" (default: {default})"
    if description:
        value += f" - {description}"
    return value

def pydantic_to_example(model: Type[BaseModel]) -> Any:
    """Generate a JSON schema description for a Pydantic model."""
    schema = {}
    for field_name, field in model.model_fields.items():
        schema[field_name] = describe_field(field)
    return schema

# # Example Usage with a Sample Pydantic Model
# class SubModel(BaseModel):
#     sub_field: int = 5
#     sub_description: str = "A sub field"

# class MainModel(BaseModel):
#     name: str = "Example"
#     count: int
#     is_active: bool = True
#     nested_model: SubModel
#     numbers: List[int] = []

# # Generating JSON Schema for MainModel
# json_schema = pydantic_to_example(MainModel)

# # Displaying the generated JSON schema
# print(json.dumps(json_schema, indent=2))
