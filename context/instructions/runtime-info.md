you are tasked to do something with InvokeAI, here is some useful information

# Useful information for InvokeAI tasks

- you have a running InvokeAI instance at one the the following url (not all of them are available):
  - `http://127.0.0.1:9090`
  - `http://192.168.11.189:61001`
- all web cli tools said in `context\hints\howto-use-webapi-tools.md` are available, use them to interact with the InvokeAI instance
- for python, use `pixi run -e dev <your-python-command>` to run your command, we are using `pixi` as the python package manager
- temporary files should be stored in `<workspace>/tmp`