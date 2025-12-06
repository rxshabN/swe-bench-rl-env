# USE UBUNTU 24.04
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install Dependencies + SUDO
RUN apt-get update && apt-get install -y \
    python3-pip git sudo \
    build-essential cmake ninja-build \
    libcurl4-openssl-dev libssl-dev libevent-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Configure Ultimate Sudo Access (Passwordless)
# We add the 'ubuntu' user to sudoers with NOPASSWD
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu && \
    chmod 0440 /etc/sudoers.d/ubuntu

# 3. Setup Framework
COPY . /evaluation
WORKDIR /evaluation
RUN pip install --break-system-packages -e .

# 4. Transmission Setup
WORKDIR /home/ubuntu

# Clone the repo
RUN git clone --recurse-submodules https://github.com/transmission/transmission.git repo

WORKDIR /home/ubuntu/repo

# Pre-configure CMake
RUN mkdir -p build && cd build && \
    cmake -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DENABLE_GTK=OFF -DENABLE_QT=OFF -DENABLE_MAC=OFF \
    -DENABLE_TESTS=ON ..

# 5. Fix Permissions & Git
# Ensure the ubuntu user owns the repo and the home directory
RUN chown -R ubuntu:ubuntu /home/ubuntu

# Allow git to operate on this directory regardless of user
RUN git config --system --add safe.directory '*'

# 6. Environment Variables
ENV REPO_PATH=/home/ubuntu/repo
ENV MCP_TESTING_MODE=1
# FIX: Explicitly set HOME so tools don't try to read /root config
ENV HOME=/home/ubuntu

CMD ["hud_eval"]