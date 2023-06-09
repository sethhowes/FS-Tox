import logging
import os
import click
import duckdb
import pandas as pd
from sklearn.linear_model import LogisticRegression
import pickle

from utils import (
    construct_query,
    mod_test_train_split,
    load_representations,
    load_assays,
)


def train(
    representation_filepath, assay_filepath, output_filepath, representation, dataset
):
    log_fmt = "%(asctime)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    logger = logging.getLogger(__name__)
    logger.info("loading features...")

    # Create a SQL query as a string to select relevant representations
    representation_query = construct_query(representation_filepath, representation)

    # Load representations from parquet files
    representation_df = load_representations(representation_query)

    # Load the assays
    assay_dfs = load_assays(assay_filepath, dataset)

    logger.info("fitting models to assay data...")

    # Evaluate each assay
    for i, (assay_df, assay_filename) in enumerate(assay_dfs):
        # Merge the representations and assays
        merged_df = pd.merge(
            representation_df, assay_df, on="canonical_smiles", how="inner"
        )

        # Conduct test train split
        X_train, _, y_train, _ = mod_test_train_split(merged_df)

        # Create a Logistic Regression object
        log_reg = LogisticRegression(max_iter=1000)

        # Fit the model to the training data
        log_reg.fit(X_train, y_train)

        # Create a filename for the model
        model_path = f"{output_filepath}/{assay_filename}_logistic_{representation}.pkl"

        # Save model to a pickle file
        with open(model_path, "wb") as f:
            pickle.dump(log_reg, f)

    logger.info(f"successfully trained {i+1} logistic models.")
