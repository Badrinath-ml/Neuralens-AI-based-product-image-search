import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from config import get_settings

settings = get_settings()


def _escape_template_literals(text: str) -> str:
    """Escape curly braces so JSON in the system prompt is not parsed as template variables."""
    return text.replace("{", "{{").replace("}", "}}")


class ProductAssistant:
    def __init__(self, contextual_system_prompt: str):
        token = settings.huggingfacehub_api_token or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        self.llm = ChatOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=token,
            model="openai/gpt-oss-120b:fireworks-ai",
            temperature=0.2,
        )
        safe_system_prompt = _escape_template_literals(contextual_system_prompt)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", safe_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ])
        self.output_parser = StrOutputParser()
        self.chain = self.prompt | self.llm | self.output_parser
