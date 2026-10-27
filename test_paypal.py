from app.paypal.client import PayPalClient


paypal = PayPalClient()

token = paypal.get_access_token()

print("PayPal authentication successful!")
print("Token:", token[:20] + "...")