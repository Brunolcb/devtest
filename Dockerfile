# Dockerfile
FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
 && apt-get install sqlite3 \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry using the official installation script
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    mv /root/.local/bin/poetry /usr/local/bin/poetry

# Ensure Poetry is on the PATH
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory
WORKDIR /workspace


# Copy dependency files first for caching, then install dependencies.
# If your project root contains additional files, adjust accordingly.
#COPY pyproject.toml poetry.lock* ./
#RUN poetry install --no-root

# Optionally, copy the rest of your project files.
COPY . /workspace

# Default command: open a bash shell with Poetry activated.
CMD ["poetry", "run", "bash", "uvicorn", "sqlite3"]

