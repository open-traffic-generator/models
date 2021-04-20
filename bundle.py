"""Build script to create openapi.yaml from model files
"""
from bundler import Bundler
import os


bundler = Bundler(
    output_dir=os.path.dirname(__file__),
    api_files=[
        './api/info.yaml',
        './api/api.yaml',
        './api/advanced-api.yaml']
)

bundler.bundle()
