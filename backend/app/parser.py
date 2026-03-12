import json
from .prompts import PARSE_PROMPT
from .models import BoardingPass
from .config import settings
from langchain_core.prompts import PromptTemplate
import os
import re
import json

from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain_google_vertexai import VertexAI

# ###Vertex AI → uses GOOGLE_APPLICATION_CREDENTIALS (service account JSON)
# ####Gemini Developer API → uses GEMINI_API_KEY or GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.0,
    api_key=settings.gemini_api_key
)


parse_template = PromptTemplate(input_variables=["raw_text"], template=PARSE_PROMPT)
parse_chain = parse_template | llm

def parse_text_to_boardingpass(raw_text: str) -> BoardingPass:
  
    prompt_str = parse_template.format(raw_text=raw_text) 

    out = parse_chain.invoke({"raw_text": raw_text})
    clean=extract_json_from_ai_message(out)
    try:
        parsed = json.loads(clean)
    except Exception as e:
        raise ValueError("LLM parsing failed to return JSON") from e
    bp = BoardingPass(**parsed)
    return bp


def extract_json_from_ai_message(ai_msg):
    # ai_msg is an AIMessage, so get the text
    text = ai_msg.content
    text = re.sub(r"^```json\s*", "", text.strip())
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
