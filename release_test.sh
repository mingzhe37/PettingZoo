#!/bin/bash

xvfb-run -as "-screen 0 1024x768x24" pytest ./test/pytest_runner.py
xvfb-run -as "-screen 0 1024x768x24" pytest ./test/all_parameter_combs.py
pytest ./test/unwrapped_test.py

pytest ./test/variable_env_test.py
pytest ./test/doc_examples_test.py
pytest ./test/specific_env_tests.py

bash ./check_style.sh
python3 -m test.print_test
