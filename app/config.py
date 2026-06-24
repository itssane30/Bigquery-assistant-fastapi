import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Google Cloud / Vertex AI
    PROJECT_ID = os.environ.get("PROJECT_ID")
    LOCATION = os.environ.get("LOCATION")
    MODEL = os.environ.get("MODEL")
    
    # BigQuery
    BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET")
    BIGQUERY_SCOPES = ["https://www.googleapis.com/auth/bigquery"]

    # BigQuery MCP server (Google-managed remote server)
    BIGQUERY_MCP_URL = os.environ.get("BIGQUERY_MCP_URL")

    # Flask
    PORT = int(os.environ.get("PORT", 8080))
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Agent loop
    MAX_AGENT_STEPS = int(os.environ.get("MAX_AGENT_STEPS", 6))

    @classmethod
    def validate(cls) -> None:
        """Fail fast and loudly if required config is missing."""
        missing = [name for name in ("PROJECT_ID","BIGQUERY_DATASET","LOCATION","MODEL","BIGQUERY_MCP_URL","PORT","MAX_AGENT_STEPS") if not getattr(cls, name)]
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                f"Check your .env file."
            )
