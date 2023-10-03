from pydantic import BaseModel, Field, create_model
import inspect
import json

from minichain.streaming import Stream


class Function:
    def __init__(self, openapi, name, function, description, stream=None):
        """
        Arguments:
            openapi (dict): the openapi.json describing the function
            name (str): the name of the function
            function (any -> FunctionMessage): the function to call. Must return a FunctionMessage
            description (str): the description of the function
        """
        if stream is None:
            stream = Stream()
        self.stream = stream
        self.pydantic_model = None
        try:
            if isinstance(openapi, dict):
                parameters_openapi = openapi
            elif issubclass(openapi, BaseModel):
                parameters_openapi = openapi.schema()
                self.pydantic_model = openapi
            else:
                raise ValueError(
                    "openapi must be a dict or a pydantic BaseModel describing the function parameters."
                )
        except:
            print(openapi, type(openapi))
            breakpoint()
        self.parameters_openapi = parameters_openapi
        self.name = name
        self.function = function
        self.description = description
    
    # def parse(self, response):
    #     """This method is for child classes that want to add extra parsing logic to the response, e.g. python"""
    #     return response

    async def __call__(self, **arguments):
        """Call the function with the given arguments.
        _stream: a function that is expected to be called with new parts of the output of the function string
                (e.g. new lines of a bash command)
        """
        if self.pydantic_model is not None:
            arguments = self.pydantic_model(**arguments).dict()
        response = await self.function(**arguments)
        if not isinstance(response, str):
            response = json.dumps(response)
        await self.stream.set(response)
        print("response", response)
        return response
        # return self.parse(response)

    def register_stream(self, stream):
        self.stream = stream
        for maybe_agent in self.__dict__.values():
            try:
                maybe_agent.register_stream(stream)
            except:
                pass

    @property
    def openapi_json(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_openapi,
        }


def tool(name=None, description=None, **kwargs):
    """A decorator for tools.
    Example:

    @tool()
    def my_tool(some_input: str = Field(..., description="Some input.")):
        return output
    """

    def wrapper(f):
        # Get the function's arguments
        argspec = inspect.getfullargspec(f)

        def f_with_args(**inner_kwargs):
            # merge the arguments from the decorator with the arguments from the function
            merged = {**kwargs, **inner_kwargs}
            return f(**merged)

        # Create a Pydantic model from the function's arguments
        fields = {
            arg: (argspec.annotations[arg], Field(..., description=field.description))
            for arg, field in zip(argspec.args, argspec.defaults)
            if not arg in kwargs.keys()
        }

        pydantic_model = create_model(f.__name__, **fields)
        function = Function(
            name=name or f.__name__,
            description=description or f.__doc__,
            openapi=pydantic_model,
            function=f_with_args,
        )
        return function

    return wrapper
