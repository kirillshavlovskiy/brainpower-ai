import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import signal
import time

# Define path to Streamlit script
streamlit_script_path = 'app_script.py'


# Function to start Streamlit server
def start_streamlit():
    global streamlit_process
    # Start Streamlit using subprocess
    streamlit_process = subprocess.Popen(['streamlit', 'run', streamlit_script_path],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         preexec_fn=os.setsid)
    print("Streamlit server started.")


# Function to stop Streamlit server
def stop_streamlit():
    # Terminate the process group (including all child processes)
    os.killpg(os.getpgid(streamlit_process.pid), signal.SIGTERM)
    print("Streamlit server stopped.")


class ChangeHandler(FileSystemEventHandler):
    """Handles file changes by performing automatic actions."""

    def __init__(self):
        self.last_modified = time.time()

    def on_modified(self, event):
        if event.src_path == streamlit_script_path:
            current_time = time.time()
            # Debounce to prevent multiple triggers
            if current_time - self.last_modified > 1:
                print(f'Change detected in {event.src_path}. Performing actions...')
                # Example action: Stopping & restarting Streamlit to apply changes
                stop_streamlit()
                start_streamlit()
                self.last_modified = current_time


if __name__ == "__main__":
    # Start the Streamlit server initially
    start_streamlit()

    observer = Observer()
    event_handler = ChangeHandler()
    observer.schedule(event_handler, path=os.path.dirname(streamlit_script_path), recursive=False)
    observer.start()

    print("Monitoring changes. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        stop_streamlit()

    observer.join()