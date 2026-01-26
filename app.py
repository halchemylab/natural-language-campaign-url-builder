import streamlit as st
import os
import json
import urllib.parse
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables if available
load_dotenv()

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Natural Language to Campaign URL Builder",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants for ROI calculations
TIME_SAVED_PER_RUN_MIN = 3
MONEY_SAVED_PER_RUN_USD = 3

# --- Helper Functions ---

def get_api_key():
    """
    Retrieves API Key from multiple sources in priority order:
    1. Sidebar Input
    2. Streamlit Secrets
    3. Environment Variables
    """
    # Check sidebar input (handled in UI code, passed here if needed, but usually we pull from state)
    # This function primarily checks secrets and env for default values or fallback
    
    if "api_key_input" in st.session_state and st.session_state.api_key_input:
        return st.session_state.api_key_input
    
    # Check Streamlit secrets
    if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
        
    # Check environment variable
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
        
    return None

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
    
    try:
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
        return json.loads(content)
    except Exception as e:
        st.error(f"Error calling OpenAI: {e}")
        return None

# --- State Management ---

def init_session_state():
    # Metrics
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    
    # Check for query params to preload state
    # This enables sharing URLs with pre-filled forms
    query_params = st.query_params
    
    defaults = {
        'website_url': '',
        'campaign_source': '',
        'campaign_medium': '',
        'campaign_name': '',
        'campaign_id': '',
        'campaign_term': '',
        'campaign_content': ''
    }

    for key, default_val in defaults.items():
        if key not in st.session_state:
            # Load from query param if available, else default
            st.session_state[key] = query_params.get(key, default_val)

def reset_metrics():
    st.session_state.usage_count = 0

# --- Main Application ---

init_session_state()

# 1. Sidebar
with st.sidebar:
    st.header("ROI Metrics")
    
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric("Runs", st.session_state.usage_count)
    with m_col2:
        pass # Spacer
        
    t_saved = st.session_state.usage_count * TIME_SAVED_PER_RUN_MIN
    m_saved = st.session_state.usage_count * MONEY_SAVED_PER_RUN_USD
    
    st.metric("Time Saved", f"{t_saved} min")
    st.metric("Money Saved", f"${m_saved}")
    
    st.button("Reset metrics", on_click=reset_metrics)
    
    st.divider()
    
    st.header("Configuration")
    
    # API Key Handling
    existing_key = get_api_key()
    
    api_key_input = st.text_input(
        "OpenAI API Key", 
        type="password", 
        value=existing_key if existing_key else "",
        key="api_key_input",
        help="Enter your OpenAI API key. It is not stored permanently."
    )
    
    api_key = api_key_input
    
    if api_key:
        st.success("API key loaded ✅")
    else:
        st.error("API key missing ❌")

    model_option = st.selectbox(
        "Model",
        options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        index=0
    )
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2)
    
    with st.expander("How it works"):
        st.markdown("""
        1. **Describe** your campaign in the text box.
        2. **Generate** a draft. AI extracts the details.
        3. **Edit** fields to tweak. URL updates instantly.
        """)

# 2. Main Area
st.title("✨ Natural Language to Campaign URL Builder")
st.markdown("Describe a campaign in plain English. Generate a URL. Edit fields and instantly get an updated share link.")

# Container for input
with st.container():
    st.subheader("Describe your campaign")
    nl_prompt = st.text_area(
        "Campaign Description",
        height=100,
        placeholder="Facebook ads driving to https://example.com/products, spring sale, medium cpc, source facebook, content carousel_v2, term running shoes",
        label_visibility="collapsed"
    )
    
    generate_btn = st.button("Generate Draft", type="primary", disabled=not api_key)

    if generate_btn and nl_prompt:
        with st.spinner("Analyzing campaign details..."):
            result = generate_campaign_data(nl_prompt, api_key, model_option, temperature)
            if result:
                # Update state
                st.session_state.website_url = result.get('website_url') or ""
                st.session_state.campaign_source = result.get('campaign_source') or ""
                st.session_state.campaign_medium = result.get('campaign_medium') or ""
                st.session_state.campaign_name = result.get('campaign_name') or ""
                st.session_state.campaign_id = result.get('campaign_id') or ""
                st.session_state.campaign_term = result.get('campaign_term') or ""
                st.session_state.campaign_content = result.get('campaign_content') or ""
                
                st.session_state.usage_count += 1
                st.rerun()

st.divider()

# Container for Form Fields
st.subheader("Campaign Parameters")

col1, col2 = st.columns(2)

with col1:
    st.text_input("Website URL *", key="website_url", help="The destination URL (e.g. https://example.com)")
    st.text_input("Campaign Source *", key="campaign_source", help="The referrer: (e.g. google, newsletter)")
    st.text_input("Campaign Medium *", key="campaign_medium", help="Marketing medium: (e.g. cpc, banner, email)")

with col2:
    st.text_input("Campaign Name *", key="campaign_name", help="Product, promo code, or slogan (e.g. spring_sale)")
    st.text_input("Campaign ID", key="campaign_id", help="The ads campaign id.")
    st.text_input("Campaign Term", key="campaign_term", help="Identify the paid keywords")
    st.text_input("Campaign Content", key="campaign_content", help="Use to differentiate ads")

# Validation warning for Name/ID
if not st.session_state.campaign_name and not st.session_state.campaign_id:
    st.warning("⚠️ Either 'Campaign Name' or 'Campaign ID' is usually required for analytics tracking.")

# 3. URL Generation Logic
final_url = build_campaign_url(
    st.session_state.website_url,
    st.session_state.campaign_source,
    st.session_state.campaign_medium,
    st.session_state.campaign_name,
    st.session_state.campaign_id,
    st.session_state.campaign_term,
    st.session_state.campaign_content
)

# 4. Display Result
st.subheader("Generated URL")
if final_url:
    st.code(final_url, language="text")
    st.caption("Click the copy icon in the top right of the code box above.")
else:
    st.info("Enter details above to generate a URL.")

# 5. Sync State to URL Query Params (Shareable App URL)
# This allows the user to copy the *browser* URL and share the current configuration
query_params_update = {
    'website_url': st.session_state.website_url,
    'campaign_source': st.session_state.campaign_source,
    'campaign_medium': st.session_state.campaign_medium,
    'campaign_name': st.session_state.campaign_name,
    'campaign_id': st.session_state.campaign_id,
    'campaign_term': st.session_state.campaign_term,
    'campaign_content': st.session_state.campaign_content
}

# Only update if values are non-empty to keep URL clean, or if we need to clear them
# We strictly map session state to query params here.
clean_params = {k: v for k, v in query_params_update.items() if v}
st.query_params.update(clean_params)

# If a key is in query params but empty in state, remove it from query params
for key in query_params_update.keys():
    if not query_params_update[key] and key in st.query_params:
        del st.query_params[key]
