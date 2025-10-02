#!/bin/bash

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download easyocr models
python -c "import easyocr; easyocr.Reader(['ja', 'en'])"