import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jarvis")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# LLM streaming configuration
STREAM_ENABLED = True
STREAM_OPTIONS = {"include_usage": True}

#configure pheonix otel
os.environ['PHOENIX_PROJECT_NAME'] = "Jarvis"
tracer_provider = register(
    endpoint="http://phoenix:4317",  # Sends traces using gRPC
    auto_instrument=True,
) 

# Initialize LangChain instrumentation for Phoenix
LangChainInstrumentor().instrument()

if __name__ == "__main__":
    print(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")

# Google Calendar configuration
GOOGLE_AUTH_KEY = os.getenv("GOOGLE_AUTH_KEY")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# Google Calendar Service function
def get_calendar_service():
    logger.info(f"Initializing Google Calendar service with auth key path: {GOOGLE_AUTH_KEY}")
    
    # Check if the credentials file exists
    creds_file = Path(GOOGLE_AUTH_KEY)
    if not creds_file.exists():
        error_msg = f"Google Calendar credentials file not found at: {GOOGLE_AUTH_KEY}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info("Google Calendar credentials file found")
    
    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_AUTH_KEY, scopes=GOOGLE_CALENDAR_SCOPES
        )
        logger.info("Google Calendar credentials loaded successfully")
        
        service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar service created successfully")
        
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Google Calendar service: {str(e)}")
        raise


