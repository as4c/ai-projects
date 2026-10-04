import os
import io
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from typing import List, Dict, Optional

# Scopes required for Google Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveService:
    """Service to interact with Google Drive API."""

    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.creds = None

    def authenticate(self):
        """Authenticate with Google Drive API."""
        # Check if token file exists
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)

        # If credentials are not valid, get new ones
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{self.credentials_file}' not found. "
                        "Please download it from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('drive', 'v3', credentials=self.creds)
        return True

    def is_authenticated(self):
        """Check if already authenticated."""
        return self.service is not None

    def list_files(self, folder_id: Optional[str] = None, page_size: int = 50) -> List[Dict]:
        """
        List files and folders from Google Drive.

        Args:
            folder_id: ID of the folder to list files from. None for root.
            page_size: Number of files to retrieve per page.

        Returns:
            List of file/folder dictionaries.
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")

        query_parts = []

        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        else:
            query_parts.append("'root' in parents")

        query_parts.append("trashed=false")
        query = " and ".join(query_parts)

        results = self.service.files().list(
            q=query,
            pageSize=page_size,
            fields="files(id, name, mimeType, size, modifiedTime, iconLink, webViewLink)",
            orderBy="folder,name"
        ).execute()

        items = results.get('files', [])
        return items

    def get_file_metadata(self, file_id: str) -> Dict:
        """Get metadata for a specific file."""
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")

        file = self.service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime, parents, webViewLink"
        ).execute()

        return file

    def download_file(self, file_id: str, destination: str = None) -> bytes:
        """
        Download a file from Google Drive.

        Args:
            file_id: ID of the file to download.
            destination: Optional file path to save the downloaded file.

        Returns:
            File content as bytes.
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")

        request = self.service.files().get_media(fileId=file_id)
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_content = file_data.getvalue()

        if destination:
            with open(destination, 'wb') as f:
                f.write(file_content)

        return file_content

    def export_google_doc(self, file_id: str, mime_type: str = 'text/plain') -> bytes:
        """
        Export Google Docs, Sheets, Slides to downloadable format.

        Args:
            file_id: ID of the Google Doc/Sheet/Slide.
            mime_type: MIME type to export to.
                - Google Docs: 'text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                - Google Sheets: 'text/csv', 'application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                - Google Slides: 'application/pdf', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

        Returns:
            Exported file content as bytes.
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")

        request = self.service.files().export_media(fileId=file_id, mimeType=mime_type)
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        return file_data.getvalue()

    def get_files_in_folder_recursive(self, folder_id: str, max_depth: int = 5, current_depth: int = 0) -> List[Dict]:
        """
        Recursively get all files in a folder and its subfolders.

        Args:
            folder_id: ID of the folder to start from.
            max_depth: Maximum depth to recurse.
            current_depth: Current recursion depth (internal use).

        Returns:
            List of all files found.
        """
        if current_depth >= max_depth:
            return []

        all_files = []
        items = self.list_files(folder_id)

        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # Recursively get files from subfolder
                subfolder_files = self.get_files_in_folder_recursive(
                    item['id'], max_depth, current_depth + 1
                )
                all_files.extend(subfolder_files)
            else:
                all_files.append(item)

        return all_files

    def search_files(self, query: str, page_size: int = 50) -> List[Dict]:
        """
        Search for files by name.

        Args:
            query: Search query string.
            page_size: Number of results to return.

        Returns:
            List of matching files.
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")

        search_query = f"name contains '{query}' and trashed=false"

        results = self.service.files().list(
            q=search_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, size, modifiedTime, iconLink, webViewLink)"
        ).execute()

        return results.get('files', [])
