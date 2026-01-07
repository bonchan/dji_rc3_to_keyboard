import requests
import json
from tqdm import tqdm

class FlightHubClient:
    def __init__(self, org_key, base_url="https://api.example.com/sv1.torage/api/0"):
        # The organization key is passed securely upon initialization
        self.org_key = org_key
        self.headers = {
            "X-Organization-Key": org_key,
            "Content-Type": "application/json"
        }
        self.base_url = base_url
        print(f'FlightHubClient initialized at {base_url}')

    def _request2(self, method, endpoint, params=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs = {}

        if params is not None:
            kwargs['params'] = params

        response = requests.request(method, url, headers=self.headers, params=params, **kwargs)
        response.raise_for_status() # Raise exception for 4xx/5xx status codes
        return response.json()


    def _request(self, method, endpoint, params=None, json_data=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Prepare the keyword arguments for the request call
        kwargs = {}
        if method in ['POST', 'PUT']:
            # For POST/PUT, if json_data is explicitly provided, use it.
            # Otherwise, default to an empty dictionary {} to satisfy 
            # the Content-Type: application/json header.
            kwargs['json'] = json_data if json_data is not None else {}
        
        # Pass standard query parameters if provided
        if params is not None:
            kwargs['params'] = params
        
        tqdm.write(f"Making {method} request to {url} with body: {kwargs.get('json', 'N/A')}")
        
        # Pass headers from self.headers and the dynamic kwargs
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status() # Raise exception for 4xx/5xx status codes
        return response.json()
    
    # Generic method to handle GET requests with pagination
    def get_paginated_data(self, endpoint, params=None):
        page = 1
        all_data = []
        
        while True:
            current_params = params.copy() if params else {}
            current_params['page'] = page
            
            response_data = self._request("GET", endpoint, params=current_params)
            
            # Assuming API response structure: {"data": {"list": [...], "pagination": {...}}}
            records = response_data.get('data', {}).get('list', [])
            all_data.extend(records)

            # Check if there are more pages (Simplistic check for demonstration)
            if not records: 
                break
                
            page += 1

        return all_data
    
    def get_organization_project_list(self):
        endpoint = "/manage/api/v1.0/projects"
        return self.get_paginated_data(endpoint)

    def get_wayline_files_page(self, project_uuid, page, size):
        endpoint = f"/storage/api/v1.0/projects/{project_uuid}/wayline-files"
        params = {'page': page, 'size': size}
        return self._request("GET", endpoint, params=params)
    
    def get_file_information (self, file_id):
        endpoint = f"/storage/api/v1.0/files/{file_id}"
        return self._request("GET", endpoint)

    def get_projects_topologies(self, project_uuid):
        endpoint = f"/manage/api/v1.0/projects/{project_uuid}/topologies"
        return self._request("GET", endpoint)
    
    def get_projects_devices(self, project_uuid):
        endpoint = f"/manage/api/v1.0/projects/{project_uuid}/devices"
        return self._request("GET", endpoint)
    
    def get_temporary_upload_token(self, project_uuid):
        endpoint = f"/storage/api/v1.0/projects/{project_uuid}/security-token"
        return self._request("POST", endpoint)
    
    def notify_of_route_file_upload(self, project_uuid, object_key, name):
        endpoint = f"/storage/api/v1.0/projects/{project_uuid}/wayline-file-upload-callback"

        payload = {
            "object_key": object_key,
            "name": name
        }

        return self._request("POST", endpoint, json_data=payload)


    