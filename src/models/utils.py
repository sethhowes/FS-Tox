import pandas as pd
import duckdb
import os


def construct_query(input_filepath, representations):
    if len(representations) == 1:
        return "SELECT * FROM '" + os.path.join(
            input_filepath, f"{representations[0]}.parquet'"
        )

    base_query = "SELECT * FROM "
    joins = []

    for i in range(len(representations) - 1):
        join = f"'{input_filepath}/{representations[i]}.parquet' INNER JOIN '{input_filepath}/{representations[i+1]}.parquet' ON {representations[i]}.canonical_smiles == {representations[i+1]}.canonical_smiles"
        joins.append(join)

    return base_query + " ".join(joins)


def load_assays(input_filepath, dataset, assay):
    # Create a DuckDB connection
    con = duckdb.connect()

    if dataset:
        # Convert the dataset tuple to a string in the format ('item1', 'item2', ...)
        if len(dataset) == 1:
            dataset_str = f"('{dataset[0]}')"
        else:
            dataset_str = str(dataset)

        # Query all parquet files in the directory, and include a "filename" column
        query = f"SELECT * FROM read_parquet('{input_filepath}/*', filename=true) WHERE source_id IN {dataset_str}"

        # Execute the query
        result = con.execute(query).df()

        # Retrieve the filenames for the relevant assays
        filenames = result["filename"].unique()

        # Create list of dataframes for each assay
        dfs = []

        # Read each assay into a dataframe
        for filename in filenames:
            df = pd.read_parquet(filename)

            # Drop the source_id and selfies columns
            df.drop(["source_id", "selfies"], axis=1, inplace=True)

            # Get file basename
            assay_basename = os.path.basename(filename)

            # Remove the file extension
            assay_basename = os.path.splitext(assay_basename)[0]

            dfs.append((df, assay_basename))

        return dfs

    # Create query for a single assay 
    query = f"SELECT * FROM '{input_filepath}/{assay[0]}*.parquet'"

    # Execute the query
    df = con.execute(query).df()

    # Drop the source_id and selfies columns
    df.drop(["source_id", "selfies"], axis=1, inplace=True)

    # Output the dataframe and the assay filename as a tuple in a list
    return [(df, assay[0])]


def load_representations(representation_query):
    # Create a database connection
    con = duckdb.connect()

    # Execute the query
    representations_df = con.execute(representation_query).df()

    # Drop all columns starting with 'canonical_smiles'
    canonical_cols = [
        col for col in representations_df.columns if col.startswith("canonical_smiles_")
    ]
    representations_df = representations_df.drop(canonical_cols, axis=1)

    # Drop the columns starting with 'representation_'
    representation_cols = [
        col for col in representations_df.columns if col.startswith("representation")
    ]
    representations_df = representations_df.drop(representation_cols, axis=1)

    # Return the resultant dataframe
    return representations_df


def mod_test_train_split(merged_df):
    # Split data into train and test - y-test not needed at scoring takes place in separate script
    y_train = merged_df.loc[merged_df["test_train"] == 0, "ground_truth"]
    y_test = merged_df.loc[merged_df["test_train"] == 1, "ground_truth"]
    X_train = merged_df.loc[merged_df["test_train"] == 0].drop(
        ["canonical_smiles", "ground_truth", "test_train", "assay_id"], axis=1
    )
    X_test = merged_df.loc[merged_df["test_train"] == 1].drop(
        ["canonical_smiles", "ground_truth", "test_train", "assay_id"], axis=1
    )

    return X_train, X_test, y_train, y_test

