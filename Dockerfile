# Start with Ubuntu as the base image
FROM ghcr.io/all-hands-ai/runtime:cca617c826a9759e2cf087c5c53cbe20

RUN adduser --system --no-create-home --shell /bin/false --group --disabled-login nginx


# # Install basic packages and dependencies
RUN apt-get update && apt-get install -y \
	cmake libnss3 libnss3-dev libcairo2-dev \
	libjpeg-dev libgif-dev libblkid-dev e2fslibs-dev \
	libboost-all-dev libaudit-dev libopenjp2-7-dev \
	nodejs npm nginx \
	&& rm -rf /var/lib/apt/lists/*

# Install Poppler
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

# Set up directories
WORKDIR /usr/local/src/skiff/app

COPY api/papermage /usr/local/src/papermage

RUN /openhands/miniforge3/bin/pip install --upgrade pip setuptools wheel

RUN cd /usr/local/src/papermage && /openhands/miniforge3/bin/pip install -e .[dev,predictors,visualizers]


# Copy API files
COPY api/requirements.txt api/
RUN pip install -r api/requirements.txt

COPY api/app api/app/
COPY api/config api/config/
COPY api/main.py api/main.py
COPY api/main_v2.py api/main_v2.py
# Set up UI
WORKDIR /usr/local/src/skiff/app/ui
COPY ui/package.json ui/yarn.lock ./
RUN yarn install

COPY ui .
# RUN yarn build

# Set up Nginx
COPY proxy/nginx.conf /etc/nginx/nginx.conf
COPY proxy/local.conf /etc/nginx/conf.d/default.conf
# RUN mkdir -p /var/www/skiff/ui && cp -r /usr/local/src/skiff/app/ui/build/* /var/www/skiff/ui/

# Set up entrypoint script
COPY entrypoint.sh /app_entrypoint.sh
RUN chmod +x /app_entrypoint.sh

EXPOSE 80

# RUN sed -i 's/user  nginx;/user  root;/' /etc/nginx/nginx.conf
# RUN sed -i 's/server ui:3000/server localhost:3000/' /etc/nginx/conf.d/default.conf

# Create a new Nginx configuration
# RUN echo 'server {\n\
# 	listen 80;\n\
# 	server_name localhost;\n\
# 	location / {\n\
# 	proxy_pass http://localhost:3000;\n\
# 	}\n\
# 	location /api/ {\n\
# 	proxy_pass http://localhost:8000;\n\
# 	}\n\
# 	}' > /etc/nginx/conf.d/default.conf

# Ensure Nginx can write to its log files
RUN chown -R root:root /var/log/nginx /var/lib/nginx

CMD ["/app_entrypoint.sh"]