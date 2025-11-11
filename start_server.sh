#!/bin/bash
# Start the backend server with correct host binding
cd sokoni_africa_app/africa_sokoni_app_backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

