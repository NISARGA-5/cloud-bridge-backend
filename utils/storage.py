import os
from flask import current_app, send_from_directory

def get_storage():
    t = current_app.config.get('STORAGE_TYPE', 'local')
    if t == 'azure': return AzureStorage()
    if t == 'gcp':   return GCPStorage()
    return LocalStorage()

class LocalStorage:
    def save(self, file_obj, stored_name):
        folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(folder, exist_ok=True)
        file_obj.save(os.path.join(folder, stored_name))
        return stored_name

    def delete(self, storage_path):
        folder = current_app.config['UPLOAD_FOLDER']
        path = os.path.join(folder, storage_path)
        if os.path.exists(path): os.remove(path)

    def send(self, storage_path, original_name):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'],
                                   storage_path, as_attachment=True,
                                   download_name=original_name)

class AzureStorage:
    def __init__(self):
        from azure.storage.blob import BlobServiceClient
        self.container = current_app.config['AZURE_CONTAINER']
        self.client = BlobServiceClient.from_connection_string(
            current_app.config['AZURE_CONNECTION_STRING'])
        try: self.client.create_container(self.container)
        except: pass

    def save(self, file_obj, stored_name):
        blob = self.client.get_blob_client(container=self.container, blob=stored_name)
        blob.upload_blob(file_obj.read(), overwrite=True)
        return stored_name

    def delete(self, storage_path):
        try:
            self.client.get_blob_client(container=self.container, blob=storage_path).delete_blob()
        except: pass

    def send(self, storage_path, original_name):
        from flask import redirect
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        import datetime
        sas = generate_blob_sas(
            account_name=self.client.account_name, container_name=self.container,
            blob_name=storage_path, account_key=self.client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.datetime.utcnow()+datetime.timedelta(minutes=15))
        return redirect(f"https://{self.client.account_name}.blob.core.windows.net/{self.container}/{storage_path}?{sas}")

class GCPStorage:
    def __init__(self):
        from google.cloud import storage as gcs
        self.client = gcs.Client()
        self.bucket = self.client.bucket(current_app.config['GCP_BUCKET_NAME'])

    def save(self, file_obj, stored_name):
        self.bucket.blob(stored_name).upload_from_file(file_obj)
        return stored_name

    def delete(self, storage_path):
        try: self.bucket.blob(storage_path).delete()
        except: pass

    def send(self, storage_path, original_name):
        from flask import redirect
        import datetime
        url = self.bucket.blob(storage_path).generate_signed_url(
            expiration=datetime.timedelta(minutes=15), method='GET',
            response_disposition=f'attachment; filename="{original_name}"')
        return redirect(url)
