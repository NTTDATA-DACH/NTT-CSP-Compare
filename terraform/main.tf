terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable Vertex AI API
resource "google_project_service" "vertex_ai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud Run API
resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Enable Artifact Registry API
resource "google_project_service" "artifact_registry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry
resource "google_artifact_registry_repository" "app_repo" {
  provider      = google-beta
  location      = var.region
  repository_id = var.artifact_registry_repo
  description   = "Repository for application container images"
  format        = "DOCKER"
}

# GCS Bucket
resource "google_storage_bucket" "app_bucket" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

# Bucket folders (conceptual, as GCS is flat, but we can create placeholder objects)
resource "google_storage_bucket_object" "raw_folder" {
  name    = "raw/"
  content = " "
  bucket  = google_storage_bucket.app_bucket.name
}

resource "google_storage_bucket_object" "data_folder" {
  name    = "data/"
  content = " "
  bucket  = google_storage_bucket.app_bucket.name
}

resource "google_storage_bucket_object" "public_folder" {
  name    = "public/"
  content = " "
  bucket  = google_storage_bucket.app_bucket.name
}

# Make public folder publicly accessible (if desired for the static site)
# Note: Security risk in production, but for this demo/dashboard it's often required.
# Alternatively, we use signed URLs or backend service access.
# For simplicity, we'll keep it private by default in code, but note the intention.

# Cloud Run Job
resource "google_cloud_run_v2_job" "default" {
  name     = "csp-comparator-job"
  location = var.region

  template {
    template {
      containers {
        image = var.container_image
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "BUCKET_NAME"
          value = google_storage_bucket.app_bucket.name
        }
        env {
          name  = "AI_LOCATION"
          value = var.region
        }
      }
      service_account = var.service_account_email
      max_retries     = 3
    }
  }
}
