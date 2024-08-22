import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
import time
import traceback
from typing import Callable
from config import settings
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

        executor = ThreadPoolExecutor()
        future = executor.submit(download_file_secure, uid, file_name, save_path, update_progress, lambda: self.terminate_processing)
        self.check_download_completion(future, uid, file_name)

        self.root.wait_window(self.root)

    def check_download_completion(self, future, uid, file_name):
        if future.done():
            try:
                future.result()  # This will raise any exceptions caught by the thread
            except Exception as e:
                raise MessageBoxException(f"Unable to download file {uid}/{file_name}. Error: {traceback.format_exc()}")
            time.sleep(0.5)
            self.root.destroy()
        else:
            self.root.after(100, lambda: self.check_download_completion(future, uid, file_name))

def download_file(uid, file_name, save_path, update_callback: Callable = None, should_terminate: Callable = None, ignore_404=False):
    downloaded_size = 0
    headers = {
        'Authorization': f'Bearer {settings.token}',
        'Range': f'bytes={downloaded_size}-'
    }
    with requests.get(f"{settings.file_url}/download/{uid}/{file_name}", headers=headers, stream=True) as r:

        if r.status_code not in (200, 206):
            if ignore_404 and r.status_code == 404:
                return
            else:
                raise MessageBoxException(f"Unable to download file {uid}:{file_name}. Error: {str(r.json())}")
        total_size_in_bytes = int(r.headers.get('content-length', 0))
        start_time = time.time()

        with open(save_path, 'wb') as file:
            for data in r.iter_content(1024 * 8):
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


def download_file_secure(uid, file_name, save_path, update_callback: Callable = None, should_terminate: Callable = None, ignore_404=False):

    manifest_url = f"{settings.file_url}/download-secure/{uid}/{file_name}"
    response = requests.get(manifest_url, headers={'Authorization': f'Bearer {settings.token}'})

    if response.status_code != 200:
        if ignore_404 and response.status_code == 404:
            return
        else:
            raise MessageBoxException(
                f"Unable to download manifest for {uid}:{file_name}. Error: {str(response.json())}")

    manifest = response.json()
    total_size_in_bytes = manifest['file_size']
    chunk_size = 1024 * 1024  # Must match server's chunk size
    downloaded_size = 0
    start_time = time.time()

    with open(save_path, 'wb') as file:
        for chunk in manifest['chunks']:
            chunk_index = chunk['index']
            chunk_checksum = chunk['checksum']
            chunk_url = f"{settings.file_url}/download_chunk/{uid}/{file_name}/{chunk_index}"

            while True:
                r = requests.get(chunk_url, headers={'Authorization': f'Bearer {settings.token}'}, stream=True)
                if r.status_code != 200:
                    raise MessageBoxException(f"Failed to download chunk {chunk_index}. Error: {r.text}")

                chunk_data = r.content
                if hashlib.sha256(chunk_data).hexdigest() != chunk_checksum:
                    print(f"Checksum mismatch for chunk {chunk_index}, retrying...")
                    continue

                file.write(chunk_data)
                downloaded_size += len(chunk_data)
                break  # Chunk downloaded and verified successfully

            if should_terminate is not None and should_terminate():
                print("Download terminated by user.")
                return

            if update_callback is not None:
                elapsed_time = time.time() - start_time
                speed = downloaded_size / elapsed_time / (1024 ** 2)
                remaining_time = (total_size_in_bytes - downloaded_size) / (downloaded_size / elapsed_time)
                percent_done = (downloaded_size / total_size_in_bytes) * 100
                update_callback(percent_done, downloaded_size / (1024 ** 3), speed, remaining_time,
                                processing_complete=False)

    if update_callback is not None:
        update_callback(100, downloaded_size / (1024 ** 3), speed, 0, processing_complete=True)


def upload_file(uid, file_path):
    # Ensure the file exists and is accessible
    try:
        files = {'file': open(file_path, 'rb')}
    except IOError:
        return "Error: The file does not exist or cannot be accessed."

    full_url = f"{settings.file_url}/upload/{uid}"
    response = requests.post(full_url, files=files, headers={'Authorization': f'Bearer {settings.token}'})

    # Close the file to prevent resource leakage
    files['file'].close()

    if response.status_code != 200:
        try:
            error_message = f"Status code: {response.status_code}, {response.json()}"
        except ValueError:
            error_message = f"Status code: {response.status_code}"
        raise MessageBoxException(f"Error: Server responded with {error_message} while uploading {file_path}")


if __name__ == "__main__":
    ft = FileTransferClient()
    ft.download(
        uid="987cfc9c-1dfa-4547-b89f-8df9abed92d6",
        file_name="archive.zip",
        save_path="archive.zip",
    )
