from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from core.chroma import add_document


@tool(name="Save and Analyze User Info", description="Analyzes user input and saves it if it's important.")
async def save_userinfo(user_input: str, graph, collection):
    decision_prompt = (
        f"Analyze the following input and decide if it contains important information "
        f"that should be saved for future reference:\n\n'{user_input}'\n\n"
        f"Respond with 'yes' if it should be saved, otherwise respond with 'no'."
    )
    decision = await graph.invoke({"messages": [("user", decision_prompt)]})
    decision_text = decision["messages"][-1].content.strip().lower()

    if decision_text == "yes":
        doc_id = f"analyzed_memory_{hash(user_input)}"
        await add_document(user_input, doc_id, collection)
        return f"Input was considered important and saved with ID: {doc_id}."
    else:
        return "Input was not considered important and was not saved."
    

# Tool accessor
def get_tool() -> StructuredTool:
    return save_userinfo
