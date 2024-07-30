import os
import subprocess
import streamlit as st
import tempfile
import uuid
from PIL import Image
import shutil
import logging
import re
import sys

# Placeholder for the actual validation function
def validate_code(code):
    # Implement strict validation rules here
    return True


def execute_and_handle_output(code):
    if not validate_code(code):
        raise ValueError("Invalid code provided.")

    temp_dir = f"/tmp/{str(uuid.uuid4())}"
    os.makedirs(temp_dir, exist_ok=True)

    code_file_path = os.path.join(temp_dir, "script.py")
    with open(code_file_path, 'w') as code_file:
        code_file.write(code)

    try:
        command = [
            "docker", "run", "--rm",
            "-v", f"{temp_dir}:/app/output",
            "my-python-image",
            "python", "/app/output/script.py"
        ]
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Docker command failed with error: {e}")

    return temp_dir


def display_output_files(output_dir):
    st.write("### Output Files")
    for item in os.listdir(output_dir):
        file_path = os.path.join(output_dir, item)
        if item.endswith('.png'):
            image = Image.open(file_path)
            st.image(image, caption=item)
        else:
            with open(file_path, "r") as file:
                content = file.read()
            st.text_area(item, content)

def write_interface_script(code):
    # Define the environment variable with the code to execute

    if "fig" or "plt" in code:
        prefix = """import argparse
import os
parser = argparse.ArgumentParser(description='Generate and save plots.')
parser.add_argument('--plot-path', type=str, help='Path to save the plot images.')
args = parser.parse_args()

"""
        code += """
# Ensure the base directory exists
base_dir = args.plot_path
if base_dir and not os.path.exists(base_dir):
    os.makedirs(base_dir)

# Save the figure to an HTML file
if 'fig' in locals() and fig is not None:
    html_file = os.path.join(base_dir, 'plot.html')
    fig.write_html(html_file)
# Save the plot to an png file
if 'plt' in locals() and plt is not None:
    if args.plot_path:
        plt.savefig(args.plot_path)
        #print(f"Plot saved to {args.plot_path}")
    else:
        print("No plot path provided; plot will not be saved.")

print(f"Plots saved to {base_dir}")"""
        code = prefix + code
    os.environ['CODE_TO_EXECUTE'] = code
    # Run the Streamlit app using subprocess
    subprocess.run(['streamlit', 'run', 'streamlit_script.py'])


def read_streamlit_code():
    code_filepath = './streamlit_app.py'

    with open(code_filepath, 'r') as file:
        script = file.read()
    return script


def read_code():
    code_filepath = './app_script.py'

    with open(code_filepath, 'r') as file:
        script = file.read()
    return script


def execution_python_docker(code):
    pass


def execute_python_code(code, input_values=''):
    modified_code = code
    try:
        p = subprocess.Popen(["python3", "-c", modified_code],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             )
        if input_values:
            input_data = '\n'.join(input_values).encode()  # Concatenate input values
            output, error = p.communicate(input_data)
        else:
            output, error = p.communicate()
        completion_status = int(p.poll())
        output_str: str = output.decode("utf-8")
        print("out", output_str)
        error_str: str = error.decode("utf-8")
        print("err:", error_str)
        print('completion status', completion_status)
        line_number = None
        error_lines = error_str.split('\n')
        while error_lines and not error_lines[-1]:
            error_lines.pop()
        last_line = error_lines[-1] if error_lines else ''
        if "EOFError: EOF when reading a line" in error_str:
            print("EOFError: EOF when reading a line")
            pattern = r'File ".+?", line (\d+), in <module>'
            completion_status = None
            # Check if there are enough lines in the error message
            if len(error_lines) > 1:
                for line in error_lines:
                    match = re.search(pattern, line)
                    if match:
                        line_number = int(match.group(1)) - 1
                        logging.error("Code execution interrupted by input request: ", error_str, 'on the line ',
                                      line_number)
                        break
            return [output_str, completion_status, line_number, last_line]
        elif completion_status == 0:
            pattern_streamlit = r"streamlit run"
            match = re.search(pattern_streamlit, error_str)
            if match:
                logging.error("Streamlit script is launching...: %s", last_line)
                run_streamlit_app(code)
                return [error_str, completion_status, line_number, last_line]
            else:

                logging.debug("Python code executed. Output: %s", output_str)

                # Handling output after subprocess completion
                output_lines = output_str.strip().split('\n')
                image_base64 = None
                clean_output_lines = []

                for line in output_lines:
                    if line.startswith('###IMAGE###:'):
                        image_base64 = line.split('###IMAGE###:')[-1].strip()
                    else:
                        clean_output_lines.append(line)

                output_str = "\n".join(clean_output_lines)
                print("writing_interface...")
                write_interface_script(modified_code)
                # Now you have the standard output in 'output_str', and the image data in 'image_base64'
                print(image_base64)
                return [output_str, 0, None, None, image_base64]

            # We log the error and return if the error string contains "Traceback (most recent call last):"
        else:
            print("error!")
            logging.error("An error occurred during code execution: %s", last_line)
            return [error_str, completion_status, line_number, last_line]

    except subprocess.TimeoutExpired:
        print("Code execution timed out.")
        output_str = "Code execution timed out."
        logging.error("Code execution timed out.")
        return [output_str, None, None, None]
    except Exception as e:
        print(e)
        output_str = str(e)
        logging.error("An error occurred: %s", e)
        return [output_str, None, None, None]


def run_streamlit_app(response):
    code = response
    # Write the new verified code to streamlit_app.py
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as temp:
            temp.write(code)
            temp_path = temp.name
        """
        Starts a Streamlit server for the specified app file.
    
        Parameters:
        - use temp file(.py) created above.
        """
        # Command to run the Streamlit app
        command = ["streamlit", "run", temp_path]
        process = subprocess.Popen(command)
        print(f"Streamlit server started for temp file path")
        process.wait()
        completion_status = int(process.poll())
        return process, completion_status
    except Exception as e:
        print(f"Error updating app.py: {e}")
