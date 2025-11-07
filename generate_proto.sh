#!/bin/bash
# Generate Python code from proto files
uv run python -m grpc_tools.protoc \
    -I proto \
    --python_out=proto \
    --grpc_python_out=proto \
    proto/browser_copilot.proto

