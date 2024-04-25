import os
from typing import Callable
import zipfile
import threading
from tqdm import tqdm
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

        self.gui_close_event.clear()
        unzip_thread = threading.Thread(target=unzip_archive, args=(archive_path, output_dir, update_progress, lambda: self.terminate_processing))
        unzip_thread.start()
        self.setup_gui()

        unzip_thread.join()  # Wait for the unzip thread to finish
        if not self.processing_complete:
            raise MessageBoxException(f"The archive {archive_path} was not unzipped properly.")


def unzip_archive(archive_path: str, output_dir: str, update_callback: Callable, should_terminate: Callable):
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.isfile(archive_path):
        return
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        file_names = zip_ref.namelist()
        total_size = sum(zip_ref.getinfo(name).file_size for name in file_names)
        processed_size = 0
        start_time = time.time()
        
        for file in tqdm(file_names, desc="Extracting files"):
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
