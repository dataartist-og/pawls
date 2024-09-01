#!/bin/bash
# Start Nginx
nginx

# Start API
cd /usr/local/src/skiff/app/api
uvicorn main:app --host 0.0.0.0 &

# Start UI development server
cd /usr/local/src/skiff/app/ui
yarn start &

# Keep container running
tail -f /dev/null