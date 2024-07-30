from flask import Flask, request, jsonify
import uuid
import os

app = Flask(__name__)

DEPLOY_DIR = '/path/to/deployment/directory'


@app.route('/deploy', methods=['POST'])
def deploy_code():
    code = request.json['code']
    deployment_id = str(uuid.uuid4())

    # Create a directory for this deployment
    deploy_path = os.path.join(DEPLOY_DIR, deployment_id)
    os.makedirs(deploy_path)

    # Write the code to an index.html file
    with open(os.path.join(deploy_path, 'index.html'), 'w') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Deployed Code</title>
        </head>
        <body>
            <h1>Deployed Code Output</h1>
            <div id="output"></div>
            <script>
                {code}
            </script>
        </body>
        </html>
        """)

    # Return the URL for this deployment
    return jsonify({'url': f'/view/{deployment_id}'})


@app.route('/view/<deployment_id>')
def view_deployment(deployment_id):
    # Serve the index.html file for this deployment
    return send_from_directory(os.path.join(DEPLOY_DIR, deployment_id), 'index.html')


if __name__ == '__main__':
    app.run(debug=True)