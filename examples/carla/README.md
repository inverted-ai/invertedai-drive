# InverteAI CARLA simulator integration

## Quick start

- Make sure Docker is installed and running
  - This can be done by running `docker info` in the terminal
- Run the following command to start the Carla server

```sh
docker compose up
```

    - NOTE: You may need to run the above command with `sudo`

- Create a python virtual environment and install dependencies

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- To run the simulation in the notebook

```sh
.venv/bin/jupyter notebook Carla-Demo.ipynb
```

- To run the simulation script

```sh
python Carla-Demo-Script.py
```

## development

- Add the following environment variables to shell

```
IAI_DEV=1
IAI_DEV_URL=http://localhost:8888
```

- Change the port mapping in iai-drive-server

```yaml
ports:
  - "8888:8000"
```

- Docs:

  - For building the html files

  ```sh
  sphinx-build docs/source docs/build/html
  ```

  - For testing and dev

  ```sh
  sphinx-autobuild docs/source docs/build/html --port 8001
  ```