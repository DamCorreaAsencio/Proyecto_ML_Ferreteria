import joblib
from pathlib import Path

# Load model and check its features
MODEL_PATH = Path("model/rf_demand.pkl")
model = joblib.load(MODEL_PATH)

print("Model type:", type(model))
if hasattr(model, 'feature_names_in_'):
    print("\nFeatures expected by model:")
    for i, feat in enumerate(model.feature_names_in_):
        print(f"  {i}: {feat}")
else:
    print("\nModel doesn't have feature_names_in_ attribute")
    print("Number of features:", model.n_features_in_ if hasattr(model, 'n_features_in_') else "unknown")

# Load encoders
ENCODERS_PATH = Path("model/encoders.pkl")
encoders = joblib.load(ENCODERS_PATH)
print("\nEncoders available:")
for key in encoders.keys():
    print(f"  - {key}")
