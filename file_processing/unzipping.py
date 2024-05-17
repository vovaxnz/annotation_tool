from concurrent.futures import ThreadPoolExecutor
import os
import traceback
from typing import Callable
import zipfile
import time
from exceptions import MessageBoxException
from file_processing.progress_bar import ProcessingProgressBar


class ArchiveUnzipper(ProcessingProgressBar):
    def unzip(self, archive_path, output_dir):

        assert os.path.isfile(archive_path), f"Archive {archive_path} not found"

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

        executor = ThreadPoolExecutor()
        future = executor.submit(unzip_archive, archive_path, output_dir, update_progress, lambda: self.terminate_processing)
        self.check_download_completion(future, archive_path)

        self.root.wait_window(self.root)

    def check_download_completion(self, future, archive_path):
        if future.done():
            try:
                future.result()  # This will raise any exceptions caught by the thread
            except Exception as e:
                raise MessageBoxException(f"The archive {archive_path} was not unzipped properly. Error: {traceback.format_exc()}")
            time.sleep(0.5)
            self.root.destroy()
        else:
            self.root.after(100, lambda: self.check_download_completion(future, archive_path))


def unzip_archive(archive_path: str, output_dir: str, update_callback: Callable, should_terminate: Callable):
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.isfile(archive_path):
        raise FileNotFoundError(f"Archive not found {archive_path}")
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        file_names = zip_ref.namelist()
        total_size = sum(zip_ref.getinfo(name).file_size for name in file_names)
        processed_size = 0
        start_time = time.time()
        
        for file in file_names:
            if should_terminate():
                print("Unzip terminated by user.")
                return
            
            zip_ref.extract(file, output_dir)
            processed_size += zip_ref.getinfo(file).file_size
            
            elapsed_time = time.time() - start_time
            speed = processed_size / elapsed_time / (1024**2)  # Speed in MB/s
            percent_done = (processed_size / total_size) * 100
            remaining_time = (total_size - processed_size) / (processed_size / elapsed_time) if processed_size else 0
            update_callback(percent_done, processed_size / (1024**3), speed, remaining_time, processing_complete=False)

        update_callback(100, processed_size / (1024**3), speed, 0, processing_complete=True)
