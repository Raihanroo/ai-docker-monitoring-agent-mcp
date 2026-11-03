import asyncio
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
MODEL = "gemini-3.5-flash"
SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server/server.py"],
)


def mcp_tool_to_gemini(tool):
    return types.FunctionDeclaration(
        name=tool.name,
        description=tool.description or "",
        parameters_json_schema=tool.inputSchema,
    )


async def ask(question: str) -> str:
    gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            gemini_tools = types.Tool(
                function_declarations=[mcp_tool_to_gemini(t) for t in tools]
            )
            config = types.GenerateContentConfig(tools=[gemini_tools])
            contents = [types.Content(role="user", parts=[types.Part(text=question)])]

            while True:
                response = None
                for attempt in range(5):
                    try:
                        response = gemini.models.generate_content(
                            model=MODEL, contents=contents, config=config
                        )
                        break
                    except genai_errors.ServerError:
                        print(f"  [retry] model busy, attempt {attempt + 1}/5", flush=True)
                        await asyncio.sleep(10 * (attempt + 1))
                if response is None:
                    raise RuntimeError("Gemini unavailable after 5 retries")
                candidate = response.candidates[0].content
                contents.append(candidate)

                calls = [p.function_call for p in candidate.parts if p.function_call]
                if not calls:
                    return response.text

                results = []
                for call in calls:
                    print(f"  [tool] {call.name}({dict(call.args or {})})")
                    result = await session.call_tool(call.name, dict(call.args or {}))
                    text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
                    results.append(
                        types.Part.from_function_response(
                            name=call.name, response={"result": text}
                        )
                    )
                contents.append(types.Content(role="user", parts=results))


async def main():
    question = " ".join(sys.argv[1:]) or "Are all services running properly?"
    print(await ask(question))


if __name__ == "__main__":
    asyncio.run(main())
