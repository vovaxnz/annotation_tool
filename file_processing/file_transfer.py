import time
import os
import threading
from typing import Callable
from config import file_server_url, api_token
import requests
from exceptions import MessageBoxException
from file_processing.progress_bar import ProcessingProgressBar


class FileTransferClient(ProcessingProgressBar):
    def download(self, uid, file_name, save_path):
        self.processed_percent = 0
        self.processed_gb = 0
        self.speed = 0
        self.remaining_time = 0
        self.processing_complete = False

        def update_progress(percent, size_gb, speed, remaining_time, processing_complete):
            self.processed_percent = percent
            self.processed_gb = size_gb
            self.speed = speed
            self.remaining_time = remaining_time
            self.processing_complete = processing_complete

        self.gui_close_event.clear()
        download_thread = threading.Thread(target=download_file, args=(uid, file_name, save_path, update_progress, lambda: self.terminate_processing))
        download_thread.start()

        download_thread.join()  # Wait for the download thread to finish
        if not os.path.isfile(save_path):
            raise MessageBoxException(f"Unable to download file {uid}:{file_name}")


def download_file(uid, file_name, save_path, update_callback: Callable = None, should_terminate: Callable = None):
    with requests.post(f"{file_server_url}/download/{uid}/{file_name}", headers={'Authorization': f'Bearer {api_token}'}, stream=True) as r:
        if r.status_code != 200:
            return
        total_size_in_bytes = int(r.headers.get('content-length', 0))
        downloaded_size = 0
        start_time = time.time()

        with open(save_path, 'wb') as file:
            for data in r.iter_content(1024):
                if should_terminate is not None and should_terminate():
                    print("Download terminated by user.")
                    return
                file.write(data)
                if update_callback is not None:
                    downloaded_size += len(data)
                    elapsed_time = time.time() - start_time
                    speed = downloaded_size / elapsed_time / (1024**2)  # Speed in MB/s
                    remaining_time = (total_size_in_bytes - downloaded_size) / (downloaded_size / elapsed_time)
                    percent_done = (downloaded_size / total_size_in_bytes) * 100
                    update_callback(percent_done, downloaded_size / (1024**3), speed, remaining_time, processing_complete=False)
        if update_callback is not None:
            update_callback(percent_done, downloaded_size / (1024**3), speed, remaining_time, processing_complete=True)


def upload_file(uid, file_path):
    # Ensure the file exists and is accessible
    try:
        files = {'file': open(file_path, 'rb')}
    except IOError:
        return "Error: The file does not exist or cannot be accessed."

    full_url = f"{file_server_url}/upload/{uid}"
    response = requests.post(full_url, files=files, headers={'Authorization': f'Bearer {api_token}'})

    # Close the file to prevent resource leakage
    files['file'].close()

    if response.status_code == 200:
        print(response.json())
    else:
        # Server responded with an error
        try:
            # Attempt to decode JSON error message
            print(response.json())
        except ValueError:
            # Non-JSON response
            print(f"Error: Server responded with status code {response.status_code}")


if __name__ == "__main__":
    ftc = FileTransferClient()
    ftc.download(
        uid="a7db9516-fa4d-458e-a57e-e836f3d5b94c", 
        file_name="archive.zip", 
        save_path="archive.zip", 
    )