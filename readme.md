# Open Traffic Generator Models

[![license](https://img.shields.io/badge/license-MIT-green.svg)](https://en.wikipedia.org/wiki/MIT_License)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![release)](https://img.shields.io/github/v/release/open-traffic-generator/models)](https://github.com/open-traffic-generator/models/releases/latest)
[![Models CI/CD](https://github.com/open-traffic-generator/models/workflows/Models%20CI/CD/badge.svg)](https://github.com/open-traffic-generator/models/actions)

Open Traffic Generator API defines a standard, model-driven and vendor-neutral 
interface for emulating layer 2-7 network devices and generating test traffic.

This repository is a collaborative effort and produces artifacts to offer a foundation for other tools and/or implementations that want to use a `model first` approach.

[Ixia-c](https://github.com/open-traffic-generator/ixia-c) is a reference implementation of traffic generator described by these data models and API.

The focus of this repository is the following:
- a [modeling guide](./MODEL-GUIDE.md) outlining best practices
- a consistent set of OpenAPI vendor-neutral data and API models
- [continuous build process](./.github/workflows/workflow.yml) that generates and validates artifacts
- a [generated OpenAPI artifact](./artifacts/openapi.yaml)

> The models in this repo are under development and are subject to change, especially the models under the `device` node.  All efforts will be made to keep them backwards compatible.

## Setup 

Please make sure that the client setup meets [Python Prerequisites](#python-prerequisites).

- Clone this project, `cd` inside it and make changes to spec following the [modelling guide](MODEL-GUIDE).

- Generate bundled spec called `openapi.yaml` inside `artifacts/`.
  ```sh
  python -m pip install -r requirements.txt
  python build.py
  ```

- To preview documentation and interact with schema, copy contents of `openapi.yaml` inside https://editor.swagger.io/.

- Upon pushing changes, `artifacts/openapi.yaml` and `artifacts/otg.proto` will be auto-generated and committed back to repository.

#### Python Prerequisites

- Please make sure you have `python` and `pip` installed on your system.

  You may have to use `python3` or `absolute path to python executable` depending on Python Installation on system, instead of `python`.

  ```sh
  python -m pip --help
  ```
  
  Please see [pip installation guide](https://pip.pypa.io/en/stable/installing/), if you don't see a help message.

- It is recommended that you use a python virtual environment for development.

  ```sh
  python -m pip install --upgrade virtualenv
  # create virtual environment inside `env/` and activate it.
  python -m virtualenv .env
  # on linux
  source .env/bin/activate
  # on windows
  .env\Scripts\activate on Windows
  ```

  **NOTE:** If you do not wish to activate virtual env, you use `env/bin/python` (or `env\scripts\python` on Windows) instead of `python`.

## Contributing
The open-traffic-generator organization welcomes new members to join this open
source community project and contribute to its development.



