from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
import torch
import torch.utils.data
import numpy as np

from numpy.typing import NDArray

from sitta.common.base import Species
from sitta.data.data_handling import get_species_seen, make_historical_sightings_dataframe_for_location, set_sightings_dataframe_names


class BasePredictor(ABC):
    """
    Abstract base class for predictors that predict whether a species will be seen at a location on a target date.
    """
    
    @abstractmethod
    def predict(self, location_id: str, target_date: datetime, species: Species) -> float:
        """
        Returns the probability of a species being seen at a location.
        """
        pass


def make_datapoints_for_location(location_id: str, target_date: datetime, day_window: int, years: int) -> pd.DataFrame:
    """
    Converts the input data into a format suitable for the model.
    
    Parameters:
    location_id (str): The eBird location ID.
    target_date (datetime): The target date.
    day_window (int): The number of days before and after the target date to include, for all years
    years (int): The number of previous years to look at.
    
    Returns:
    dict: A dictionary containing the input data for the model.
    """

    species_seen = {s.species_code: True for s in get_species_seen(location_id, target_date)}
    seen_df = pd.DataFrame(species_seen, index=pd.Index([target_date]))

    sightings_df = make_historical_sightings_dataframe_for_location(
        location_id,
        datetime(target_date.year - 1, target_date.month, target_date.day),
        num_years=years,
        day_window=day_window
    )
    sightings_df = pd.concat([sightings_df, seen_df], axis=0)
    sightings_df = sightings_df.fillna(False) # type: ignore
    sightings_df = set_sightings_dataframe_names(sightings_df)
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
        return torch.from_numpy(self.inputs[:,idx]), torch.from_numpy(self.labels[idx]) # type: ignore

class SimpleNNPredictor(BasePredictor):
    """
    A simple neural network predictor that predicts the probability of a species being seen at a location on a target date.
    """
    
    def __init__(self, historical_years: int, day_window: int):
        """
        Initializes the predictor with a PyTorch model.
        
        Parameters:
        model (torch.nn.Module): The PyTorch model to use for predictions.
        """
        self.historical_years = historical_years
        self.day_window = day_window

    def input_dim(self) -> int:
        """
        Returns the input dimension of the model.
        """
        return self.historical_years * (self.day_window * 2 + 1)


    def predict(self, location_id: str, target_date: datetime, species: Species) -> float:
        """
        Predicts the probability of a species being seen at a location on a target date.
        
        Parameters:
        location_id (str): The eBird location ID.
        target_date (datetime): The target date.
        species (Species): The species to predict for.
        
        Returns:
        float: The predicted probability of the species being seen at the location on the target date.
        """
        # Convert inputs to tensors and pass through the
        # model to get the prediction
        location_tensor = torch.tensor(location_id, dtype=torch.float32)
        return 0.0