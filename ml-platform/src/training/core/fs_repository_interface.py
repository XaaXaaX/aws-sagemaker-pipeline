import pandas as pd
from kink import inject
import json
import os
import pickle
import tarfile


@inject()
class FileSystemRepository():
    def __init__(self, input_path: str, output_path: str, config_path: str, model_path: str, analysis: bool = False) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.config_path = config_path
        self.model_path = model_path
        self.analysis = analysis

    def save(self, data: pd.DataFrame, path: str, index: bool = False, force: bool = False) -> None:
        if self.analysis or force:
            data.to_csv(f'{self.output_path}/{path}', index=index)

    def read(self, path: str) -> pd.DataFrame:
        return pd.read_csv(f'{self.input_path}/{path}')
    
    def file_exists(self, file: str) -> bool:
        return os.path.exists(f'{self.input_path}/{file}')

    def save_models(self, dict_package, filename: str):
        path_to_model = f"{self.model_path}/{filename}.pkl"
        with open(path_to_model, "wb") as f:
            pickle.dump(dict_package, f)
        output_tar_gz = f"{self.model_path}/{filename}.tar.gz"
        with tarfile.open(output_tar_gz, "w:gz") as tar:
            tar.add(path_to_model, arcname=os.path.basename(path_to_model))

    def get_hyperparameters(self, path: str):
        with open(f'{self.input_path}/{path}', "r") as f:
            return json.load(f)
    
    def save_metrics(self, metrics: dict, path:str, filename: str):
        metrics_json = json.dumps(metrics, indent=4)
        with open(f"{self.output_path}/{path}/{filename}", 'w') as outfile:
            outfile.write(metrics_json)