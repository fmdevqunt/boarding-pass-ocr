
import json
import re
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from .prompts import ADVISORY_PROMPT
from .config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.0,
    api_key=settings.gemini_api_key,
    model_kwargs={
        "generation_config": {
            "response_mime_type": "application/json"
        }
    }
)

adv_template = PromptTemplate(input_variables=["payload_json"], template=ADVISORY_PROMPT)
adv_chain = adv_template | llm

def extract_json_from_llm_output(raw_output: str) -> str:
    pattern = r'```(?:json)?\s*([\s\S]*?)```'
    match = re.search(pattern, raw_output)
    if match:
        return match.group(1).strip()
    return raw_output.strip()

def generate_advisory(payload: dict) -> dict:
    payload_str = json.dumps(payload, indent=2)
    out = adv_chain.invoke({"payload_json": payload_str})

    #print("Raw LLM output:", out.content)

    cleaned = extract_json_from_llm_output(out.content)
    result = json.loads(cleaned)

    # Validation: all recommended lounge_ids must exist in original all_lounges
    original_ids = {l['lounge_id'] for l in payload['all_lounges']}
    for rec in result.get('recommendations', []):
        if rec['lounge_id'] not in original_ids:
            raise ValueError(f"LLM invented lounge_id '{rec['lounge_id']}' – not in original list")

    return result