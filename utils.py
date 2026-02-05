import urllib.parse
import json
import requests
import qrcode
import io
import csv
import os
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional, Tuple, Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential

# Constants for ROI calculations
TIME_SAVED_PER_RUN_MIN = 3
MONEY_SAVED_PER_RUN_USD = 3

def calculate_roi(usage_count: int) -> Tuple[int, int]:
    """
    Calculates time and money saved based on usage count.
    Returns a tuple (time_saved_min, money_saved_usd).
    """
    return (
        usage_count * TIME_SAVED_PER_RUN_MIN,
        usage_count * MONEY_SAVED_PER_RUN_USD
    )

def generate_qr_code_image(url: str) -> bytes:
    """
    Generates a QR code for the given URL and returns it as bytes.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def validate_api_key(api_key: str) -> bool:
    """
    Validates the OpenAI API key by making a lightweight API call.
    Returns True if valid, False otherwise.
    """
    if not api_key:
        return False
    try:
        client = OpenAI(api_key=api_key)
        # listing models is a lightweight call to check auth
        client.models.list(limit=1)
        return True
    except Exception:
        return False

def load_history_from_csv(file_path: str) -> List[Dict[str, str]]:
    """Loads history from a CSV file."""
    if not os.path.exists(file_path):
        return []
    
    history = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append(row)
    except Exception:
        return []
    return history

def save_history_item_to_csv(file_path: str, item: Dict[str, str]) -> None:
    """Appends a history item to the CSV file."""
    fieldnames = ['name', 'url']
    file_exists = os.path.exists(file_path)
    
    try:
        with open(file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(item)
    except Exception:
        pass

class CampaignData(BaseModel):
    website_url: str
    campaign_source: str
    campaign_medium: str
    campaign_name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_term: Optional[str] = None
    campaign_content: Optional[str] = None

def normalize_url(url: str) -> str:
    """Ensures URL has a scheme."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url

def validate_url_reachability(url: str) -> bool:
    """
    Checks if the URL is reachable (returns 200-399 status code).
    Uses a short timeout and handles common issues.
    """
    if not url:
        return False
    
    try:
        # User-Agent to avoid blocking by some servers
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # Try HEAD first for efficiency
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        
        # If HEAD not allowed, try GET (stream=True to avoid downloading body)
        if response.status_code == 405:
             response = requests.get(url, headers=headers, timeout=3, stream=True)

        return 200 <= response.status_code < 400
    except Exception:
        return False

def build_campaign_url(
    base_url: str,
    source: str,
    medium: str,
    campaign_name: Optional[str],
    campaign_id: Optional[str],
    term: Optional[str],
    content: Optional[str]
) -> str:
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

def lint_utm_parameter(value: Optional[str]) -> List[str]:
    """
    Checks a UTM parameter value against common best practices.
    Returns a list of warning messages.
    """
    if not value:
        return []
    
    warnings = []
    
    # 1. Check for uppercase
    if any(char.isupper() for char in value):
        warnings.append("Contains uppercase letters (lowercase is preferred for consistency)")
    
    # 2. Check for spaces
    if ' ' in value:
        warnings.append("Contains spaces (use underscores or hyphens instead)")
    
    # 3. Check for special characters (other than - or _)
    import re
    if re.search(r'[^a-zA-Z0-9\-_]', value):
        warnings.append("Contains special characters (stick to alphanumeric, -, and _)")
        
    return warnings

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_campaign_data(
    prompt: str,
    api_key: str,
    model: str,
    temperature: float
) -> Dict[str, Any]:
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
