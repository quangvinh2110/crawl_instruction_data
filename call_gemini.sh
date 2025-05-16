#!/bin/bash

set -ex

GEMINI_API_KEY=AIzaSyADGi3fdnZ0gi51C4e4kUdV0hwoVwXcU0k nohup python3 call_gemini.py >> log_gemini.txt 2>&1 &