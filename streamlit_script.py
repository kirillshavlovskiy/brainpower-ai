# filename: docker_streamlit_app.py
import tempfile
from streamlit import components
import streamlit as st
import os
import subprocess
from PIL import Image


# Initialize session state variables
if 'code' not in st.session_state:
    st.session_state['code'] = ''
def validate_code(code):  # Implement strict validation rules here
    return True

# Create a sidebar with a code editor


def execute_and_handle_docker_output(code):
    try:
        temp_dir = tempfile.mkdtemp(prefix='code_executor_')
        code_file_path = os.path.join(temp_dir, "script.py")
        plot_png_path = os.path.join(temp_dir, "plot.png")

        with open(code_file_path, 'w') as code_file:
            code_file.write(code)

        command = [
            "docker", "run", "--rm", "-v", f"{temp_dir}:/app/output",
            "my-python-image_plots", "python", "/app/output/script.py", "--plot-path", "/app/output/plot.png"
        ]

        result = subprocess.run(command, text=True, capture_output=True, check=True)
        stdout_output = result.stdout.strip()
        plot_png_created = os.path.exists(plot_png_path)

        return stdout_output, temp_dir, plot_png_created
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr
        return f"Subprocess failed: {stderr_output}", None, False
    except Exception as e:
        return f"Error occurred during execution: {str(e)}", None, False

def display_output_files(output_dir):
    st.write("### Output Files")
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            with open(file_path, 'rb') as file:
                img = Image.open(file)
                st.image(img, use_column_width=True, caption=filename)
        else:
            with open(file_path, 'r') as file:
                content = file.read()
            st.text(filename)
            st.code(content)

def main():
    # Initialize session state variables
    if 'code' not in st.session_state:
        st.session_state['code'] = ''

    # Create a sidebar with a code editor
    with st.sidebar:
        st.title("Code Editor")
        code_editor = st.text_area(label="Enter your Python code:", value=st.session_state['code'], height=400)
        execute_button = st.button("Execute")

    # Function to execute code and display output
    def execute_code(code):
        if validate_code(code):
            # Execute the code
            response = execute_and_handle_docker_output(code)
            if len(response) > 2:
                output, output_dir, plot_png_created = response

            # Display the output
            st.write("### Output")
            st.text(output)
            st.write("")
            if output_dir:
                display_output_files(output_dir)
            else:
                st.write("No output was created.")
        else:
            st.write("Invalid code")

    # Execute code if the execute button is pressed
    if execute_button:
        st.session_state['code'] = code_editor
        execute_code(st.session_state['code'])

    # Automatically execute code if it exists in session state
    if st.session_state['code']:
        execute_code(st.session_state['code'])

if __name__ == "__main__":
    main()
