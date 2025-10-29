import fireducks.pandas as pd
from kink import inject

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
