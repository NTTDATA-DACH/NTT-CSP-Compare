import os

class Config:
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id"))
    BUCKET_NAME = os.getenv("BUCKET_NAME", "mock-bucket")
    AI_LOCATION = os.getenv("AI_LOCATION", "us-central1")
    TEST_MODE = os.getenv("TEST", "false").lower() == "true"

    # Vertex AI specific
    VERTEX_API_VERSION = "v1"
