variable "project_id" {}
variable "location" {
    default = "us-central1"
}
variable "container_image" {
  default = "gcr.io/david-tessier-sandbox/dlp-demo"
}

variable "gcp_service_list" {
  description = "List of GCP service to be enabled for the project."
  type        = list
}

variable "region" {
  description = "Google Cloud region to deploy resources"
  type        = string
  default     = "us-central1"
}

variable "pubsub_subscription" {
  description = "Pub/Sub subscription name"
  type        = string
  default     = "dlp-subscription"
}

variable "dlp_rolesList" {
  type =list(string)
  default = ["roles/dlp.admin","roles/dlp.serviceAgent"]
}
