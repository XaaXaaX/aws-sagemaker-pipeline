import pandas as pd
from kink import inject
import json
import pickle


@inject()
class FileSystemRepository():
    def __init__(self, input_path: str, output_path: str, analysis: bool = False) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.analysis = analysis

    def save(self, data: pd.DataFrame, path: str, index: bool = False, force: bool = False) -> None:
        if self.analysis or force:
            data.to_csv(f'{self.output_path}/{path}', index=index)

    def read(self, path: str) -> pd.DataFrame:
        return pd.read_csv(f'{self.input_path}/{path}')

    def load_model(self, path: str, filename: str):
        with open(f"{self.input_path}/{path}/{filename}.pkl", "rb") as f:
            return pickle.load(f)
        
    def get_hyperparameters(self, path: str):
        with open(f'{self.input_path}/{path}', "r") as f:
            return json.load(f)

    def save_metrics(self, metrics: dict, filename: str):
        metrics_json = json.dumps(metrics, indent=4)
        with open(f"{self.output_path}/{filename}", 'w') as outfile:
            outfile.write(metrics_json)