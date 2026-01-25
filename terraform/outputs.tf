output "bucket_name" {
  description = "The name of the created bucket"
  value       = google_storage_bucket.app_bucket.name
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "job_name" {
  description = "The name of the Cloud Run Job"
  value       = google_cloud_run_v2_job.default.name
}

output "artifact_registry_repo" {
  description = "The name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.app_repo.name
}

output "project_id" {
  description = "The Google Cloud Project ID"
  value       = var.project_id
}
