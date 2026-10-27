import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


DATA_PATH = "data/training_data.csv"

def train_model():
    df = pd.read_csv(DATA_PATH)

    features = [
        "invoice_amount",
        "previous_invoices",
        "previous_late_payments",
        "previous_late_rate",
        "avg_previous_delay",
    ]

    X = df[features]
    y = df["is_late"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = LogisticRegression(
        max_iter=1000
    )

    model.fit(X_train, y_train)

    joblib.dump(
        model,
        "models/payment_risk.pkl"
    )

    prediction = model.predict(X_test)

    #Evaluate
    accuracy = accuracy_score(
        y_test,
        prediction
    )

    print("\nAccuracy:", round(accuracy, 4))

    print("\nClassification Report:")
    print(classification_report(
        y_test,
        prediction
    ))

    print("\nConfusion Matrix:")
    print(confusion_matrix(
        y_test,
        prediction
    ))

if __name__ == "__main__":
    train_model()