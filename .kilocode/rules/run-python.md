# run-python.md

- when developing, by default, use `pixi run -e dev` to run any python code
- if the user says "run in release", use `pixi run`
- we are using `pixi` to manage the python environment, so NEVER try to use `pip` to install any package, instead, add the package to `pyproject.toml` and run `pixi install` to install it
