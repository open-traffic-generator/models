"""
The following command produces these artifacts:
    - ./art/openapi.yaml
    - ./art/openapi.json
    - ./art/otg-convergence.proto
"""
import sys
import os
import subprocess

# supported values - local openapiart path or None
USE_OPENAPIART_DIR = None

# supported values - branch name or None
USE_OPENAPIART_BRANCH = "add_strict_check_for_descriptions"

OPENAPIART_REPO = "https://github.com/open-traffic-generator/openapiart.git"


if USE_OPENAPIART_DIR is not None:
    sys.path.insert(0, USE_OPENAPIART_DIR)
elif USE_OPENAPIART_BRANCH is not None:
    local_path = "openapiart"
    if not os.path.exists(local_path):
        subprocess.check_call("git clone {} && cd {} && git checkout {} && cd ..".format(OPENAPIART_REPO, local_path, USE_OPENAPIART_BRANCH), shell=True)
    sys.path.insert(0, local_path)

import openapiart

openapiart.OpenApiArt(
    api_files=["./api/info.yaml", "./api/api.yaml"],
    protobuf_name="otg",
    artifact_dir="artifacts",
    generate_version_api=True,
).GeneratePythonSdk(package_name="otg")
