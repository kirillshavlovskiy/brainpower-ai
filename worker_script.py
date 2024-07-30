# Check if there's an input file
if os.path.exists('input.json'):
    with open('input.json', 'r') as f:
        user_input = json.load(f)['input']

    # Check if user input is not empty
    if user_input:
        process = subprocess.Popen(['python3', 'streamlit_app_script.py', user_input],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
        ...
    else:
        print("User input is empty. Can't start subprocess.")