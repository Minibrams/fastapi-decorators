#!/bin/bash

pip install -e .
python -m unittest discover -s tests/unit_tests
python -m unittest discover -s tests/integration_tests
