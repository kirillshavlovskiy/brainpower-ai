# Use the official Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary system libraries (for matplotlib)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libxrender1 \
    libblas3 \
    liblapack3 \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*


RUN pip install pipreqs
RUN pipreqs . --force
# Expose the port (optional)
EXPOSE 7000

RUN python -c "import pip; pip.main(['install', '-r', 'requirements.txt'])"



# NO Command to run the script from exact file
