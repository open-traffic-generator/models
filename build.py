"""

The following command produces these artifacts:

    - ./art/openapi.yaml

    - ./art/openapi.json

    - ./art/otg-convergence.proto

"""

import os

import shutil

import openapiart



file_name = "singlehome.py"

src_file = "artifacts/otg/" + file_name

path = "tmp_dir"

new_file_name = path + "/" + file_name

os.makedirs(path, exist_ok = True)



try:

    shutil.copy(src_file, new_file_name)

except:    

    None



openapiart.OpenApiArt(

    api_files=["./api/info.yaml", "./api/api.yaml"],

    protobuf_name="otg",

    artifact_dir="artifacts",

).GeneratePythonSdk(package_name="otg")



try:

    shutil.copy(new_file_name, src_file)

except:    

    None

shutil.rmtree(path)