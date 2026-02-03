import streamlit as st
import os
import pyshorteners
from dotenv import load_dotenv
from pydantic import ValidationError
from utils import normalize_url, build_campaign_url, generate_campaign_data, calculate_roi, validate_url_reachability, generate_qr_code_image, load_history_from_csv, save_history_item_to_csv, validate_api_key

# Load environment variables if available
load_dotenv()

HISTORY_FILE = "history.csv"

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Natural Language to Campaign URL Builder",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# --- State Management ---

def init_session_state():
    # Metrics
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0

    # History
    if 'history' not in st.session_state:
        st.session_state.history = load_history_from_csv(HISTORY_FILE)
    
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

def clear_form_data():
    keys = ['website_url', 'campaign_source', 'campaign_medium', 
            'campaign_name', 'campaign_id', 'campaign_term', 'campaign_content']
    for k in keys:
        st.session_state[k] = ''

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
        
    t_saved, m_saved = calculate_roi(st.session_state.usage_count)
    
    st.metric("Time Saved", f"{t_saved} min")
    st.metric("Money Saved", f"${m_saved}")
    
    st.button("Reset metrics", on_click=reset_metrics)
    
    st.divider()

    st.header("History")
    if st.session_state.history:
        # Show newest first
        for i, item in enumerate(reversed(st.session_state.history)):
            label = item.get('name', 'Untitled')
            url = item.get('url', '')
            with st.expander(f"{label}"):
                st.code(url, language="text")
    else:
        st.caption("No history yet.")

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
        if st.button("Validate Key"):
            with st.spinner("Checking API Key..."):
                if validate_api_key(api_key):
                    st.success("API Key is valid! ✅")
                else:
                    st.error("Invalid API Key ❌")

        st.success("API key loaded ✅")
        
        # Helper to save key locally (Low friction improvement)
        # Check if key is NOT already in environment to avoid redundancy
        if not os.getenv("OPENAI_API_KEY") and api_key_input:
            if st.button("Save to .env (Local Only)"):
                try:
                    with open(".env", "a") as f:
                        f.write(f"\nOPENAI_API_KEY={api_key_input}")
                    st.toast("Saved to .env! It will auto-load next time.")
                except Exception as e:
                    st.error(f"Could not save .env: {e}")
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
            try:
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
            except ValidationError as ve:
                st.error("The AI returned an invalid response format. Please try again with a different description.")
                with st.expander("Debug Info"):
                    st.write(ve)
            except Exception as e:
                st.error(f"Error calling OpenAI: {e}")

st.divider()

# Container for Form Fields
c_p_col1, c_p_col2 = st.columns([3, 1])
with c_p_col1:
    st.subheader("Campaign Parameters")
with c_p_col2:
    st.button("Clear Form", on_click=clear_form_data, type="secondary")

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

    # Validate URL Reachability
    with st.spinner("Validating link..."):
        is_valid = validate_url_reachability(final_url)
    
    if is_valid:
        st.success("✅ Link is reachable")
    else:
        st.warning("⚠️ Link might be unreachable or broken")

    if st.button("Save to History"):
        # Create a friendly label
        h_label = st.session_state.campaign_name or st.session_state.campaign_source or "Untitled Campaign"
        new_item = {
            "name": h_label,
            "url": final_url
        }
        st.session_state.history.append(new_item)
        save_history_item_to_csv(HISTORY_FILE, new_item)
        st.success(f"Saved '{h_label}' to history!")
    
    # QR Code Generation
    with st.expander("Show QR Code"):
        img_byte_arr = generate_qr_code_image(final_url)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(img_byte_arr, caption="Campaign QR Code")
        with c2:
            st.download_button(
                label="Download QR Code",
                data=img_byte_arr,
                file_name="campaign_qr.png",
                mime="image/png"
            )

    # URL Shortener
    st.divider()
    if 'shortened_url' not in st.session_state:
        st.session_state.shortened_url = None
        
    # Reset shortened URL if the main URL changes (simple check: if shortened URL doesn't resolve to current final_url - strictly we can't check easily without decoding, 
    # but we can just clear it if we detect a change in inputs. 
    # Actually, simpler: just let user click again if they change params.
    
    if st.button("Shorten URL (TinyURL)"):
        with st.spinner("Shortening..."):
            try:
                s = pyshorteners.Shortener()
                short_url = s.tinyurl.short(final_url)
                st.session_state.shortened_url = short_url
            except Exception as e:
                st.error(f"Error shortening URL: {e}")

    if st.session_state.get('shortened_url'):
        st.success("Short URL generated:")
        st.code(st.session_state.shortened_url, language="text")

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
