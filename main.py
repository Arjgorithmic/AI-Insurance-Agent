import os
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from tools import TOOLS
from contextManager import fetch_relevant_policies

load_dotenv()

api_key = os.getenv("OpenRouterAPI")
model = os.getenv("AIModel")
base_url = os.getenv("OpenRouterBaseUrl")

llm = ChatOpenAI(
    model=model,
    base_url=base_url,
    api_key=api_key,
    temperature=0.3
)

SYSTEM_MESSAGE = (
    "You are InsureAI, a friendly insurance assistant. "
    "You help users by summarizing policy documents, tracking insurance policies, "
    "and reminding them about renewals. "
    "When policies are added automatically from uploads, they might have incomplete data — "
    "you should not mention missing fields unless the user asks for details. "
    "If the user asks about their policies, just show clear summaries (policy name, provider, summary). "
    "Avoid repeating database structure or suggesting data cleanup unless specifically requested."
)


agent = create_react_agent(llm, TOOLS, prompt=SYSTEM_MESSAGE)

def build_contextual_query(user_input: str) -> str:
    context = fetch_relevant_policies(user_input)
    return f"{context}\n\nUser Query:\n{user_input}"

def run_agent(user_input: str, history: List[BaseMessage]) -> AIMessage:
    try:
        contextual_input = build_contextual_query(user_input)
        result = agent.invoke(
            {"messages": history + [HumanMessage(content=contextual_input)]},
            config={"recursion_limit": 50}
        )
        return result["messages"][-1]
    except Exception as e:
        return AIMessage(content=f"Error: {str(e)}")

if __name__ == "__main__":
    history: List[BaseMessage] = []
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ['quit', 'exit', 'q', ""]:
            print("Goodbye!")
            break
        response = run_agent(user_input, history)
        print("Agent:", response.content)
        history += [HumanMessage(content=user_input), response]
