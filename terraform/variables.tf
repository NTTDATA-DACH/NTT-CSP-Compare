variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "Name of the GCS bucket"
  type        = string
}

variable "container_image" {
  description = "Container image URI for the pipeline job"
  type        = string
}

variable "service_account_email" {
  description = "Service Account email to run the job as"
  type        = string
  default     = "" # Optional: if not provided, Compute Engine default might be used or created elsewhere
}
