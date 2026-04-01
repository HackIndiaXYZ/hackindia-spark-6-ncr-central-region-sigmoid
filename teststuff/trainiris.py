# save this as train_iris.py in your project root and run it
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

X, y = load_iris(return_X_y=True)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_scaled, y)
joblib.dump(model, 'model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("Saved model.pkl and scaler.pkl")