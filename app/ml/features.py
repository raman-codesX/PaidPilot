import pandas as pd


RAW_PATH = "data/synthetic_invoices_raw.csv"
OUTPUT_PATH = "data/training_data.csv"


def build_features():

    df = pd.read_csv(RAW_PATH)

    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["due_date"] = pd.to_datetime(df["due_date"])
    df["payment_date"] = pd.to_datetime(df["payment_date"])

    #creating target label
    is_late = (
        df["payment_date"] > df["due_date"]
    ).astype(int)

    # Sort chronologically within each client.
    df = df.sort_values(
        ["customer_id", "invoice_date"]
    ).reset_index(drop=True)

    # Current invoice's payment delay.
    # This is used ONLY to create the target.
    df["payment_delay"] = (
        df["payment_date"] - df["due_date"]
    ).dt.days

    # Previous invoice count.
    df["previous_invoices"] = (
        df.groupby("customer_id")
        .cumcount()
    )

    # Previous late payments.
    df["previous_late_payments"] = (
        df.groupby("customer_id")["is_late"]
        .transform(
            lambda x: x.shift(1).fillna(0).cumsum()
        )
    )

    # Previous late-payment rate.
    df["previous_late_rate"] = (
        df["previous_late_payments"]
        / df["previous_invoices"].replace(0, 1)
    )

    # Previous average payment delay.
    df["avg_previous_delay"] = (
        df.groupby("customer_id")["payment_delay"]
        .transform(
            lambda x: x.shift(1).expanding().mean()
        )
        .fillna(0)
    )

    # Features the model is allowed to see.
    feature_columns = [
        "invoice_amount",
        "previous_invoices",
        "previous_late_payments",
        "previous_late_rate",
        "avg_previous_delay",
    ]

    # Keep target separately.
    output = df[
        feature_columns + ["is_late"]
    ].copy()

    output.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print("Created:", OUTPUT_PATH)
    print("Rows:", len(output))
    print("\nFeatures:")
    print(feature_columns)

    print("\nTarget distribution:")
    print(output["is_late"].value_counts())

    print("\nFirst 10 rows:")
    print(output.head(10))


if __name__ == "__main__":
    build_features()