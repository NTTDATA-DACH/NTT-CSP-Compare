import os

class Config:
    TEST_MODE = os.getenv("TEST", "false").lower() == "true"

    if TEST_MODE:
        GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id"))
        BUCKET_NAME = os.getenv("BUCKET_NAME", "mock-bucket")
        AI_LOCATION = os.getenv("AI_LOCATION", "global")
    else:
        GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT"))
        BUCKET_NAME = os.getenv("BUCKET_NAME")
        AI_LOCATION = os.getenv("AI_LOCATION")

        missing_vars = []
        if not GCP_PROJECT_ID:
            missing_vars.append("GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT")
        if not BUCKET_NAME:
            missing_vars.append("BUCKET_NAME")
        if not AI_LOCATION:
            missing_vars.append("AI_LOCATION")

        if missing_vars:
            raise ValueError(
                "Error: Missing required environment variables for non-test mode: "
                f"{', '.join(missing_vars)}"
            )

    # Vertex AI specific
    VERTEX_API_VERSION = "v1"
