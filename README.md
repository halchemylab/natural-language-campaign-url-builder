# Natural Language to Campaign URL Builder

A Streamlit application that converts natural language marketing campaign descriptions into ready-to-use UTM-tagged URLs using OpenAI.

## Features

- **Natural Language Input**: Describe your campaign (e.g., "Facebook spring sale for running shoes") and get a structured draft instantly.
- **Smart Parsing**: Uses OpenAI to extract standard UTM parameters (Source, Medium, Name, ID, Term, Content).
- **Live Editing**: URL updates immediately as you modify fields.
- **State Persistence**: The application URL updates as you type, allowing you to share deep links to specific campaign configurations.
- **ROI Tracking**: Tracks time and money saved based on usage.

## Setup

1. **Prerequisites**: Python 3.11+

2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```

3. **OpenAI API Key**:
   You can provide the API key in one of three ways:
   - Enter it in the application Sidebar.
   - Create a `.env` file in the root directory: `OPENAI_API_KEY=sk-...`
   - Use Streamlit Secrets (`.streamlit/secrets.toml`).

## Running the App

```bash
streamlit run app.py
```

## Usage

1. Open the app in your browser (usually http://localhost:8501).
2. Enter your OpenAI API Key in the sidebar (if not set in env).
3. Type a description of your campaign in the text box.
   - Example: *"Email newsletter sent to https://mysite.com/blog, weekly digest, source newsletter, medium email"*
4. Click **Generate Draft**.
5. Review and edit the populated fields.
6. Copy the final generated URL from the code block.

## Configuration

- **Model**: Select between `gpt-4o-mini` (default, faster/cheaper) or other available models.
- **Temperature**: Adjust creativity (lower is more deterministic).

## ROI Metrics

The sidebar tracks your session usage:
- **Time Saved**: estimated at 3 minutes per manual URL creation avoided.
- **Money Saved**: estimated at $3.00 operational cost per URL.
