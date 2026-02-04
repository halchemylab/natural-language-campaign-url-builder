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

## Features in Action

### Screenshot
![Natural Language Campaign URL Builder](./screenshot.png)
*The application interface showing campaign description input, parameter generation, and URL output.*

## ROI Metrics

The sidebar tracks your session usage:
- **Time Saved**: estimated at 3 minutes per manual URL creation avoided.
- **Money Saved**: estimated at $3.00 operational cost per URL.

## Advanced Features

### URL Shortening
- Generate shortened TinyURLs for your campaign URLs with a single click.
- Useful for sharing in limited-character environments (Twitter, SMS, etc.).

### QR Code Generation
- Automatically generate QR codes for campaign URLs.
- Download QR codes as PNG files for print or digital use.

### Campaign History
- Previous campaigns are automatically saved and displayed in the sidebar.
- Click any campaign to view its full URL.
- Data persists in `history.csv`.

### URL Validation
- The app validates that your destination URL is reachable.
- Provides warnings if the link might be broken or unreachable.

### Shareable App URLs
- The app state updates the browser URL as you work.
- You can copy the browser URL and share it with others—they'll see the same campaign configuration when they open it.

## Testing

Run the test suite:
```bash
pytest tests.py
```

Tests cover:
- URL normalization and building
- URL reachability validation
- Campaign data parsing from natural language
- Edge cases and error handling

## Architecture

- **app.py**: Main Streamlit UI and orchestration.
- **utils.py**: Utility functions for URL building, API calls, QR code generation, and data persistence.
- **tests.py**: Unit tests for core functions.
- **requirements.txt**: Python dependencies.

## Error Handling

The application gracefully handles:
- Invalid OpenAI API keys
- Malformed JSON responses from AI
- Unreachable destination URLs
- URL shortening failures
- Network timeouts

## Future Enhancements

- Multi-source campaign builders (Google Ads, Facebook, LinkedIn parameters)
- Batch URL generation from CSV
- Analytics integration (GA4 real-time tracking)
- Campaign templates library

## License

MIT License - Feel free to use and modify as needed.
