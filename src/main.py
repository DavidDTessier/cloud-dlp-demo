import os

import json

from google.cloud import logging_v2 as logging
from google.cloud import dlp_v2 as dlpV2
from google.cloud import storage


LOG_SEVERITY_DEFAULT = 'DEFAULT'
LOG_SEVERITY_INFO = 'INFO'
LOG_SEVERITY_ERROR = 'ERROR'
LOG_SEVERITY_WARNING = 'WARNING'
LOG_SEVERITY_DEBUG = 'DEBUG'

APP_LOG_NAME = os.getenv('LOG_NAME', 'DLP-redaction-demo')

RAW_BUCKET = 'cloud-dlp-demo-raw-bucket'
REDACTED_BUCKET = 'cloud-dlp-demo-redacted-bucket'
BQ_DATASET_ID = 'cloud_dlp_demo_dlp_results'
PROJECT_ID = '[REPLACE_WITH_GCP_PROJECT_NAME]' # ADD GCP PROJECT ID

# End of user-configurable constants
# --------------------

# Initialize the Google Cloud client libraries
dlp = dlpV2.DlpServiceClient()
storage_client = storage.Client()


def log(message, severity=LOG_SEVERITY_DEFAULT, log_name=APP_LOG_NAME):
    logger_client = logging.Client()
    logger = logger_client.logger(log_name)

    return logger.log_text(message, severity=severity)

def create_DLP_inspection_template(project_id):
    log('Function triggered for creating the De-Identification Config Template that will be used for the CLoud DLP job.', severity=LOG_SEVERITY_INFO)

    # Convert the project id into a full resource id.
    parent_val = f"projects/{project_id}"

    # Construct the configuration dictionary. Keys which are None may
    # optionally be omitted entirely.
    deidentify_config = {
        'info_type_transformations': {
            'transformations':[
            {
              'info_types':[
                {
                  'name':'FIRST_NAME'
                }
              ],
              'primitive_transformation':{
                 'replace_config': {
                    'new_value': { 'string_value': 'FN' }
                }
              }
            },
            {
              'info_types':[
                {
                  'name':'LAST_NAME'
                }
              ],
              'primitive_transformation':{
                 'replace_config': {
                    'new_value': { 'string_value': 'LN' }
                }
              }
            },
            {
              'info_types':[
                {
                  'name':'PHONE_NUMBER'
                }
              ],
              'primitive_transformation':{
                'replace_config': {
                  'new_value': { 'string_value': '1' } 
                }
              }
            },
            {
              'info_types':[
                {
                  'name':'EMAIL_ADDRESS'
                }
              ],
              'primitive_transformation':{
                'character_mask_config': {
                  'masking_character':'*',
                  'number_to_mask': 4,
                  'reverse_order': True
                }
              }
            },
            {
              'info_types':[
                {
                  'name':'STREET_ADDRESS'
                }
              ],
              'primitive_transformation':{
                'character_mask_config': {
                  'masking_character':'L',
                  'number_to_mask': 4,
                  'reverse_order': True
                }
              }
            }
          ]
        }
    }
    
    
   

    log("Request Body:", severity=LOG_SEVERITY_INFO)
    log(json.dumps(deidentify_config), severity=LOG_SEVERITY_INFO)

    deidentify_template = {
        "deidentify_config": deidentify_config,
        "display_name": "Demo DeIdentification Template",
    }

  
    # Create the DeIdentification template
    try:
        # Make the request
        response = dlp.create_deidentify_template(request={
                'parent': parent_val,
                'deidentify_template': deidentify_template,
        })
        log('Template created by create_DLP_inspection_template', severity=LOG_SEVERITY_INFO)
        return response.name
    except Exception as e:
        log(e, severity=LOG_SEVERITY_ERROR)
        
def create_DLP_job(project_id, file_name, raw_bucket_name, deidentified_bucket_name, bq_dataset_id):
    log('Function triggered for file [{}] to start a DLP job'.format(file_name), severity=LOG_SEVERITY_INFO)

    deidentify_template_name = create_DLP_inspection_template(project_id)

    log(json.dumps(deidentify_template_name), severity=LOG_SEVERITY_INFO)

    # Convert the project id into a full resource id.
    parent = f"projects/{project_id}"

    # Construct the configuration dictionary.
    inspect_job = {
        'inspect_config' : {
          'info_types': [
            {
               'name':'FIRST_NAME'
            },
            {
               'name':'LAST_NAME'
            },
            {
               'name':'STREET_ADDRESS'
            },
            {
               'name':'EMAIL_ADDRESS'
            },
            {
               'name':'PHONE_NUMBER'
            }
            
          ]
        },
        'storage_config': {
            'cloud_storage_options': {
                'file_set': {
                    'url':
                        'gs://{bucket_name}/{file_name}'.format(
                            bucket_name=raw_bucket_name, file_name=file_name)
                }
            }
        },
        'actions': [
          {
            'deidentify': {
              'transformation_config': {
                'deidentify_template' : deidentify_template_name
              },
              'cloud_storage_output' : 'gs://{bucket_name}/deidentified_content/'.format(bucket_name=deidentified_bucket_name),
               'transformation_details_storage_config': {
                    'table': {
                        'project_id': '{project_id}'.format(project_id=project_id),
                        'dataset_id':'{dataset_id}'.format(dataset_id=bq_dataset_id)
                    }
               }
               
            }
          }]
         #{
          #  'save_findings': {
           #     'output_config': {
            #        'table': {
             #           'project_id':'projects/{project_id}'.format(project_id=project_id),
              #          'dataset_id':'{dataset_id}'.format(dataset_id=bq_dataset_id)
               #     }
                #}     
            #}
       # }]
    }

    # Create the DLP job and let the DLP api processes it.
    try:
        response = dlp.create_dlp_job(parent=(parent), inspect_job=(inspect_job))
        log('Job created by create_DLP_job', severity=LOG_SEVERITY_INFO)
        return response
    except Exception as e:
        log(e, severity=LOG_SEVERITY_ERROR)

def entry(data, done):
    """This function is triggered by new files uploaded to the designated Cloud Storage quarantine/staging bucket.

          It creates a dlp job for the uploaded file.
        Arg:
          data: The Cloud Storage Event
        Returns:
            None. Debug information is printed to the log.
        """
    # Get the targeted file in the quarantine bucket
    file_name = data['name']
    log (file_name, severity=LOG_SEVERITY_INFO)
    log('Function triggered for file [{}] to start a DLP job'.format(file_name),
    severity=LOG_SEVERITY_INFO)
      
    response = create_DLP_job(project_id=PROJECT_ID,file_name=file_name,raw_bucket_name=RAW_BUCKET, deidentified_bucket_name=REDACTED_BUCKET, bq_dataset_id=BQ_DATASET_ID)

    log (f"DLP Job {response.name} has a state {response.state}.", LOG_SEVERITY_INFO)
