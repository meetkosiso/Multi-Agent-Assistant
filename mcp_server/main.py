from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.core.config import AppSettings
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from io import StringIO
import sys
import ast  # For parsing and safety checks
import builtins  # For creating safe builtins

app = FastAPI()

search = DuckDuckGoSearchAPIWrapper()


class ExecuteRequest(BaseModel):
    command: str
    parameters: dict


# Safe builtins whitelist (exclude dangerous functions like open, exec, eval, __import__, etc.)
SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in [
        'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'chr', 'complex', 'dict',
        'divmod', 'enumerate', 'filter', 'float', 'frozenset', 'hash', 'hex', 'id', 'int',
        'isinstance', 'issubclass', 'iter', 'len', 'list', 'map', 'max', 'memoryview', 'min',
        'next', 'object', 'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed', 'round',
        'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
    ]
}


class SafetyVisitor(ast.NodeVisitor):
    """AST visitor to check for disallowed nodes (e.g., imports, dangerous calls)."""

    def visit_Import(self, node):
        raise ValueError("Imports are not allowed")

    def visit_ImportFrom(self, node):
        raise ValueError("Imports are not allowed")

    def visit_Call(self, node):
        # Disallow calls to exec, eval, compile
        if isinstance(node.func, ast.Name) and node.func.id in {'exec', 'eval', 'compile'}:
            raise ValueError(f"Call to '{node.func.id}' is not allowed")
        self.generic_visit(node)


@app.get(f"{AppSettings.API_VERSION}/commands")
def get_commands():
    return [
        {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo",
            "parameters": {
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "code_execution",
            "description": "Execute Python code safely",
            "parameters": {
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"]
            }
        }
    ]


@app.post(f"{AppSettings.API_VERSION}/execute")
def execute(req: ExecuteRequest):
    if req.command == "web_search":
        if "query" not in req.parameters:
            raise HTTPException(400, "Missing 'query' parameter")
        try:
            results = search.run(req.parameters["query"])
            return {"result": results}
        except Exception as e:
            raise HTTPException(500, str(e))
    elif req.command == "code_execution":
        if "code" not in req.parameters:
            raise HTTPException(400, "Missing 'code' parameter")
        try:
            code = req.parameters["code"]
            # Parse and check AST for safety
            tree = ast.parse(code)
            visitor = SafetyVisitor()
            visitor.visit(tree)

            # Compile the code
            exec_compile = compile(tree, "<string>", "exec")

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()

            # Execute in restricted environment
            safe_globals = {"__builtins__": SAFE_BUILTINS}
            exec(exec_compile, safe_globals, {})

            sys.stdout = old_stdout
            return {"result": mystdout.getvalue()}
        except (SyntaxError, ValueError) as e:
            raise HTTPException(400, f"Invalid code: {str(e)}")
        except Exception as e:
            raise HTTPException(500, str(e))
    raise HTTPException(404, "Command not found")
