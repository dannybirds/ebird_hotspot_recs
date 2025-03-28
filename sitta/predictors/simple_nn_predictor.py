from datetime import datetime
import pandas as pd
import torch
import torch.utils.data
import numpy as np

from numpy.typing import NDArray

from sitta.data.providers import EBirdDataProvider
from sitta.predictors.base import BasePredictor
from sitta.common.base import Species, TargetArea, TargetAreaType

def make_datapoints_for_location(provider: EBirdDataProvider, locality_id: str, target_date: datetime, day_window: int, years: int) -> pd.DataFrame:
    
    target_area = TargetArea(area_type=TargetAreaType.LOCALITY, area_id=locality_id)
    species_seen = {s.species_code: True for s in provider.get_species_seen(target_area, target_date)}
    seen_df = pd.DataFrame(species_seen, index=pd.Index([target_date]))

    sightings_df = provider.make_historical_sightings_dataframe_for_location(
        target_area,
        datetime(target_date.year - 1, target_date.month, target_date.day),
        num_years=years,
        day_window=day_window
    )
    sightings_df = pd.concat([sightings_df, seen_df], axis=0)
    sightings_df = sightings_df.fillna(False) # type: ignore
    sightings_df = provider.set_sightings_dataframe_names(sightings_df)
    return sightings_df


class SimpleNNDataset(torch.utils.data.Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """
    A dataset class for historical sighting data.
    """
    
    def __init__(self, csv_files: list[str]):
        """
        Initializes the dataset with historical sightings data from per-location CSV files.
        
        """
        labels = pd.DataFrame()
        inputs = pd.DataFrame()
        for f in csv_files:
            df: pd.DataFrame = pd.read_csv(f, index_col='date') # pyright: ignore[reportUnknownMemberType]
            max_idx: int  = max(list(df.index)) # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            labels = pd.concat([labels, df.loc[max_idx]])  # pyright: ignore[reportUnknownArgumentType]
            inputs = pd.concat([inputs, df.drop(max_idx)], axis=1) # pyright: ignore[reportUnknownArgumentType]
        self.inputs: NDArray[np.bool_] = inputs.to_numpy(dtype=np.bool_) # type: ignore
        self.labels: NDArray[np.bool_] = labels.to_numpy(dtype=np.bool_) # type: ignore

    def __len__(self) -> int:
        return self.labels.shape[0]
    
    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return torch.from_numpy(self.inputs[:,idx]).float(), torch.from_numpy(self.labels[idx]).float()  # pyright: ignore[reportUnknownMemberType]



class LogisticRegression(torch.nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__() # pyright: ignore[reportUnknownMemberType]
        self.linear = torch.nn.Linear(input_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = torch.sigmoid(self.linear(x))
        return out

class SimpleNNPredictor(BasePredictor):
    """
    A simple neural network predictor that predicts the probability of a species being seen at a location on a target date.
    """
    
    def __init__(self, provider: EBirdDataProvider, historical_years: int, day_window: int):
        """
        Initializes the predictor with a PyTorch model.
        
        Parameters:
        model (torch.nn.Module): The PyTorch model to use for predictions.
        """
        self.provider = provider
        self.historical_years = historical_years
        self.day_window = day_window
        self.model = None

    def input_dim(self) -> int:
        """
        Returns the input dimension of the model.
        """
        return self.historical_years * (self.day_window * 2 + 1)
    
    def load_model(self, model_file: str) -> None:
        """
        Loads the model from a file.
        
        Parameters:
        model_file (str): The path to the model file.
        
        Returns:
        torch.nn.Module: The loaded model.
        """
        self.model = LogisticRegression(self.input_dim())
        self.model.load_state_dict(torch.load(model_file)) # pyright: ignore[reportUnknownMemberType]


    def predict(self, locality_id: str, target_date: datetime, species: Species | str) -> float:
        """
        Predicts the probability of a species being seen at a location on a target date.
        
        Parameters:
        location_id (str): The eBird location ID.
        target_date (datetime): The target date.
        species (Species): The species to predict for.
        
        Returns:
        float: The predicted probability of the species being seen at the location on the target date.
        """
        if not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")
    
        target_area = TargetArea(area_type=TargetAreaType.LOCALITY, area_id=locality_id)
        sightings_df = self.provider.make_historical_sightings_dataframe_for_location(
            target_area,
            datetime(target_date.year - 1, target_date.month, target_date.day),
            num_years=self.historical_years,
            day_window=self.day_window
        )
        sightings_df = sightings_df.fillna(False) # type: ignore
        sightings_df = self.provider.set_sightings_dataframe_names(sightings_df)
        species_code = species.species_code if isinstance(species, Species) else species
        if species_code not in sightings_df.columns:
            input = torch.zeros((1, self.input_dim())) # pyright: ignore[reportUnknownMemberType]
        else:
            input = torch.from_numpy(sightings_df[species_code].values).float() # pyright: ignore[reportUnknownMemberType]
        
        p = self.model(input)
        return p.item() # pyright: ignore[reportUnknownMemberType]
    
    def train(self, dataset: SimpleNNDataset, num_epochs: int = 10, model_file: str|None = None) -> torch.nn.Module:
        """
        Trains the model on the provided data.
        
        Parameters:
        dataset (SimpleNNDataset): The dataset to train on.
        num_epochs (int): The number of epochs to train for.
        """
        device = torch.accelerator.current_accelerator().type if torch.accelerator.is_available() else "cpu"
        print(f"Using {device} device")
        data_loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)

        model = LogisticRegression(self.input_dim())
        criterion = torch.nn.BCELoss()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        print("Training model...")
        model.to(device)
        print(model)
        for epoch in range(num_epochs):
            for i, (inputs, labels) in enumerate(data_loader):
                # Move tensors to the configured device
                inputs = inputs.to(device)
                labels = labels.to(device)

                # Forward pass
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                # Backward and optimize
                optimizer.zero_grad()
                loss.backward()
                optimizer.step() # pyright: ignore[reportUnknownMemberType]

                if epoch % 100 == 0:
                    print(f'Epoch [{epoch+1}/{num_epochs}], Step [{i+1}/{len(data_loader)}], Loss: {loss.item():.4f}')
                    print(f'{model.linear.weight=}')
        
        if model_file:
            torch.save(model.state_dict(), model_file) # pyright: ignore[reportUnknownMemberType]
            print(f"Model saved to {model_file}")
        return model