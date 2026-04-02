# Use a slim base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install git and dependencies, clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Clone ParamSpider repository
RUN git clone https://github.com/devanshbatham/paramspider

# Change the working directory to the cloned repository
WORKDIR /app/paramspider

# Install ParamSpider dependencies using pip
RUN pip install --no-cache-dir .

# Set the entrypoint to run paramspider
ENTRYPOINT ["paramspider"]
