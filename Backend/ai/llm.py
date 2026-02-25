""" LLM Setup File """

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic # pip install -U langchain-anthropic
from langchain.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()


llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
)

system_msg = SystemMessage("Speak Like a Pirate")
human_msg = HumanMessage("How are you?")

messages = [system_msg, human_msg]

response = llm.invoke(messages)

print(response.content)

