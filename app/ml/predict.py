import joblib
import pandas as pd


MODEL_PATH = "models/payment_risk.pkl"
model = joblib.load(MODEL_PATH)


def predict_late_payment(
    invoice_amount,
    previous_invoices,
    previous_late_payments,
    previous_late_rate,
    avg_previous_delay,
):

    # Create features for the new invoice
    data = pd.DataFrame([
        {
            "invoice_amount": invoice_amount,
            "previous_invoices": previous_invoices,
            "previous_late_payments": previous_late_payments,
            "previous_late_rate": previous_late_rate,
            "avg_previous_delay": avg_previous_delay,
        }
    ])

    # Get probability of late payment
    probability = model.predict_proba(data)[0][1]

    # Determine risk level
    if probability >= 0.70:
        risk = "HIGH"
    elif probability >= 0.40:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "late_probability": round(probability, 4),
        "risk_level": risk,
    }


if __name__ == "__main__":

    result = predict_late_payment(
        invoice_amount=1500,
        previous_invoices=5,
        previous_late_payments=4,
        previous_late_rate=0.8,
        avg_previous_delay=3.2,
    )

    print("\nPAYMENT RISK PREDICTION")
    print("Late probability:", result["late_probability"])
    print("Risk level:", result["risk_level"])