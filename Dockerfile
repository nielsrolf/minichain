# Start with a base image
FROM python:3.11

# Install dependencies for building Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        curl

# Install node via NVM
ENV NVM_DIR /root/.nvm
ENV NODE_VERSION 20.4.0

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash \
    && . $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

# Add node and npm to path so that they're usable
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Confirm installation
RUN node -v
RUN npm -v

# Install tree
RUN apt-get install -y tree ffmpeg

# # # Clean up
# RUN apt-get clean \
#     && rm -rf /var/lib/apt/lists/x* /tmp/* /var/tmp/*

RUN pip install --upgrade pip
RUN pip install numpy pandas matplotlib seaborn plotly scikit-learn requests beautifulsoup4
RUN pip install librosa pydub yt-dlp soundfile

# install screen
RUN apt-get install -y screen

RUN pip install moviepy

# install jupyter
RUN pip install jupyterlab


RUN pip install git+https://github.com/nielsrolf/minichain

RUN pip install python-jose[cryptography]

# Start minichain api
CMD ["python", "-m", "minichain.api"]