FROM ubuntu:22.04

# install basic packages
RUN apt-get update && apt-get install -y \
	curl \
	wget \
	git \
	vim \
	nano \
	unzip \
	zip \
	python3 \
	python3-pip \
	python3-venv \
	python3-dev \
	build-essential \
	openssh-server \
	sudo \
	gcc \
	jq \
	g++ \
	make \
	iproute2 \
	cmake \
	libnss3 \
	libnss3-dev \
	libcairo2-dev \
	libjpeg-dev \
	libgif-dev \
	cmake \
	libblkid-dev \
	e2fslibs-dev \
	libboost-all-dev \
	libaudit-dev \
	libopenjp2-7-dev \
	&& rm -rf /var/lib/apt/lists/*
RUN wget https://poppler.freedesktop.org/poppler-21.09.0.tar.xz \
	&& tar -xvf poppler-21.09.0.tar.xz \
	&& cd poppler-21.09.0 \
	&& mkdir build \
	&& cd build \
	&& cmake -DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_INSTALL_PREFIX=/usr \
	-DTESTDATADIR=$PWD/testfiles \
	-DENABLE_UNSTABLE_API_ABI_HEADERS=ON \
	.. \
	&& make \
	&& make install

# Setup a spot for the api code
WORKDIR /usr/local/src/skiff/app/api

ARG GITHUB_ACCESS_TOKEN

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel
COPY requirements.txt .

RUN pip install -r requirements.txt


# Copy over the source code
COPY app app/
COPY config config/
COPY main.py main.py
COPY main_v2.py main_v2.py
COPY papermage /usr/local/src/papermage

RUN cd /usr/local/src/papermage && python3 -m pip install -e .[dev,predictors,visualizers]

# symlink python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Kick things off
ENTRYPOINT [ "uvicorn" ]
CMD ["main_v2:app", "--host", "0.0.0.0"]
