import urllib.parse
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

# Constants for ROI calculations
TIME_SAVED_PER_RUN_MIN = 3
MONEY_SAVED_PER_RUN_USD = 3

def calculate_roi(usage_count):
    """
    Calculates time and money saved based on usage count.
    Returns a tuple (time_saved_min, money_saved_usd).
    """
    return (
        usage_count * TIME_SAVED_PER_RUN_MIN,
        usage_count * MONEY_SAVED_PER_RUN_USD
    )

class CampaignData(BaseModel):
    website_url: str
    campaign_source: str
    campaign_medium: str
    campaign_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_term: Optional[str] = None
    campaign_content: Optional[str] = None

def normalize_url(url):
    """Ensures URL has a scheme."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url

def build_campaign_url(base_url, source, medium, campaign_name, campaign_id, term, content):
    """
    Constructs the final URL.
    - Preserves existing query params in base_url.
    - Overwrites existing utm_ params with new values if provided.
    - Appends new utm_ params.
    """
    if not base_url:
        return ""
    
    base_url = normalize_url(base_url)
    
    try:
        parsed_url = urllib.parse.urlparse(base_url)
    except Exception:
        return base_url # Return as is if parsing fails
        
    # Get existing params
    query_params = dict(urllib.parse.parse_qsl(parsed_url.query))
    
    # New params to merge
    utm_params = {
        'utm_source': source,
        'utm_medium': medium,
        'utm_campaign': campaign_name,
        'utm_id': campaign_id,
        'utm_term': term,
        'utm_content': content
    }
    
    # Clean up empty new params
    utm_params = {k: v for k, v in utm_params.items() if v}
    
    # Update query params (overwrite collisions with new values)
    query_params.update(utm_params)
    
    # Rebuild query string
    new_query = urllib.parse.urlencode(query_params, safe='/')
    
    # Rebuild full URL
    final_url = urllib.parse.urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    
    return final_url

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_campaign_data(prompt, api_key, model, temperature):
    """Calls OpenAI to parse the natural language prompt."""
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are an expert marketing URL operations assistant. 
    Convert the user's natural language campaign description into structured UTM parameters.
    
    Rules:
    - website_url: Extract the destination URL. If missing scheme, assume https://.
    - campaign_source (utm_source): Required. Lowercase.
    - campaign_medium (utm_medium): Required. Lowercase.
    - campaign_name (utm_campaign): Required (or campaign_id). Convert spaces to underscores. Keep lowercase unless specified.
    - campaign_id (utm_id): Optional.
    - campaign_term (utm_term): Optional.
    - campaign_content (utm_content): Optional.
    
    Return JSON only matching the schema.
    """
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "campaign_parameters",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "website_url": {"type": "string"},
                        "campaign_source": {"type": "string"},
                        "campaign_medium": {"type": "string"},
                        "campaign_name": {"type": ["string", "null"]},
                        "campaign_id": {"type": ["string", "null"]},
                        "campaign_term": {"type": ["string", "null"]},
                        "campaign_content": {"type": ["string", "null"]}
                    },
                    "required": ["website_url", "campaign_source", "campaign_medium", "campaign_name", "campaign_id", "campaign_term", "campaign_content"],
                    "additionalProperties": False
                }
            }
        },
        temperature=temperature
    )
    
    content = response.choices[0].message.content
    return CampaignData.model_validate_json(content).model_dump()
