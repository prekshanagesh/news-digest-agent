from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_credentials():
    token_path = Path("token.json")

    if not token_path.exists():
        raise FileNotFoundError(
            "token.json not found. Run the pipeline locally first "
            "to generate it, then add its contents to GitHub Secrets."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())

    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail credentials are invalid or expired. "
            "Re-run the pipeline locally to refresh token.json, "
            "then update the GMAIL_TOKEN_JSON secret on GitHub."
        )

    return creds