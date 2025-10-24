# Machine Learning using AWS Sagemeaker

The Repository explores the Machine Learning process including Data Understanding, Prep  ratiopn, training, evaluation and prediction.

The Example use a online retail stock dataset to showcase the ML process, for simplicity the example will prepare a recomendation ML model based on user activities.

## Managing deps and requeirements file

Once the `pyproject.toml` file is updated run the following commands to generate the `uv.lock`
```shell
 > uv lock
```

## Running the code

```shell
    > uv run --env-file=.env ./core/main.py
```

Note: some parameters are passed via env file such as logLevel (ex. INFO, DEBUG, etc.)

## Local Container Build & Run

Each project is a collection of modules which is independently built via dockerfile.

For example, to build processing module first go to the corresponding directory

```shell
cd ml-platform/src/processing
```

Use the following command to build the image and tag it for further uses

```shell
docker buildx build --platform linux/amd64 --no-cache -t processing .
```

Run a container based on built image

```shell
docker run --rm  -it -v ../../../data:/opt/ml/processing/input/data -v ../../../data:/opt/ml/processing/output/data -e LOGLEVEL=INFO -e MODE=DEVELOPMENT processing:latest
```

### Usefull commands

```shell
 > docker rmi $(docker images -a -q) --force 
```

```shell
 > docker system prune --all
```


| ItemId  | Intention_rate | Time_Period | 
| ------- | -------------- | ----------- |
| 1111111 | 1 * X1  |



Source Dataset 
https://www.kaggle.com/code/shwetakolekar/retailrocket-recommender-system/input