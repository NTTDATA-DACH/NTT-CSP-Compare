output "bucket_name" {
  description = "The name of the created bucket"
  value       = google_storage_bucket.app_bucket.name
}

output "job_name" {
  description = "The name of the Cloud Run Job"
  value       = google_cloud_run_v2_job.pipeline_job.name
}

output "region" {
  description = "The GCP region"
  value       = var.region
}
