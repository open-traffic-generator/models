""" 
The following command produces these artifacts:
    - ./art/openapi.yaml
    - ./art/openapi.json
    - ./art/otg-convergence.proto
"""
import openapiart


openapiart.OpenApiArt(
    api_files=["./api/info.yaml", "./api/api.yaml"],
    protobuf_name="otg",
    artifact_dir="art",
).GeneratePythonSdk(package_name="otg")
