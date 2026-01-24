output "bucket_name" {
  description = "The name of the created bucket"
  value       = google_storage_bucket.app_bucket.name
}

output "region" {
  description = "The GCP region"
  value       = var.region
}
