terraform {
  required_version = ">= 1.2.0"
  required_providers {
    google = {
      source = "hashicorp/google"
      version = ">= 4.32.0"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.location
}

locals {
  name_prefix = "cloud-dlp-demo"
  bq_name_prefix = "cloud_dlp_demo"
  data_file = "${path.module}/data/sensitive-data.csv"
}

# Creates zip file of function code & requirments.txt
data "archive_file" "source" {
    type        = "zip"
    source_dir  = "${path.module}/../dlp-redaction-python/src"
    output_path = "/tmp/dlpfunction.zip"
}

# Add zip file to the Cloud Function's source code bucket
resource "google_storage_bucket_object" "zip" {
    source       = data.archive_file.source.output_path
    content_type = "application/zip"
    # Append to  MD5 checksum of the files's content to force the zip to be updated as soon as a change occurs
    name         = "src-${data.archive_file.source.output_md5}.zip"
    bucket       = google_storage_bucket.function_bucket.name
}

# Enable services in Project.
resource "google_project_service" "gcp_services" {
  count   = length(var.gcp_service_list)
  project = var.project_id
  service = var.gcp_service_list[count.index]

  disable_dependent_services = true
}

resource "google_storage_bucket" "raw" {
    name = "${local.name_prefix}-raw-bucket"
    location = var.location
    uniform_bucket_level_access = true
}

resource "google_storage_bucket" "redacted" {
    name = "${local.name_prefix}-redacted-bucket"
    location = var.location
    uniform_bucket_level_access = true
}

# Create bucket to store cloud function source code
resource "google_storage_bucket" "function_bucket" {
  name = "${var.project_id}-function"
  location = var.region
   uniform_bucket_level_access = true 
}

# Create 1st Cloud function triggered by a `Finalize` event on the quarantine bucket
resource "google_cloudfunctions_function" "function" {
    name                  = "${local.name_prefix}-function"
    runtime               = "python37"  

    # Get the source code of the cloud function as a Zip compression
    source_archive_bucket = google_storage_bucket.function_bucket.name
    source_archive_object = google_storage_bucket_object.zip.name

    # Entry point of  the function name in the cloud function `main.py` source code
    entry_point      = "entry"
    
    event_trigger {
        event_type = "google.storage.object.finalize"
        resource   = google_storage_bucket.raw.name  # quarantine bucket where files are uploaded for processing
    }
}

data "google_project" "project" {
}

output "project_number" {
  value = data.google_project.project.number
}

resource "google_project_iam_member" "set_viewer_role" {
  project  =  var.project_id 
  role =  "roles/viewer"
  member   = "serviceAccount:service-${data.google_project.project.number}@dlp-api.iam.gserviceaccount.com" 
} 


# Retrieve default app engine service account

data "google_app_engine_default_service_account" "default" {
}

output "default_account" {
  value = data.google_app_engine_default_service_account.default.email
}

# Grant DLP permissions to app engine  service account

resource "google_project_iam_member" "set_dlp_roles" {
  project  =  var.project_id 
  count = length(var.dlp_rolesList)
  role =  var.dlp_rolesList[count.index]
  member   = "serviceAccount:${data.google_app_engine_default_service_account.default.email}"
} 

resource "google_bigquery_dataset" "this" {
  dataset_id                  = "${local.bq_name_prefix}_dlp_results"
  friendly_name               = "${local.name_prefix}-dlp-results"
  description                 = "This is a test description"
  location                    = "US"
 
  labels = {
    env = "demo"
  }
}


