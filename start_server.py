#!/usr/bin/env python3
"""
Simple script to start the web interface server
"""

import uvicorn
from web_interface import app

if __name__ == "__main__":
    print("🌐 Starting web interface on http://127.0.0.1:8080")
    print("📊 Dashboard: http://127.0.0.1:8080/")
    print("🔧 API Docs: http://127.0.0.1:8080/docs")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info") 