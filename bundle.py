"""Build script to create openapi.yaml from model files
"""
import openapiart


openapiart.OpenApiArt(
    api_files=["./api/info.yaml", "./api/api.yaml"],
    # python_module_name="otg_core",
    protobuf_file_name="otg_core",
    protobuf_package_name="otg",
    output_dir="openapiart",
)
