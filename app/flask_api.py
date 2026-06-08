"""
flask_api.py
HR Analytics Platform — REST API
Serves ML predictions and analytics data.
"""

import os, joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
DATA_DIR = os.path.join(BASE_DIR, 'data', 'cleaned')

# Load models and preprocessing objects
try:
    model = joblib.load(os.path.join(MODELS_DIR, 'best_model.pkl'))
    imputer = joblib.load(os.path.join(MODELS_DIR, 'imputer.pkl'))
    scaler = joblib.load(os.path.join(MODELS_DIR, 'scaler.pkl'))
    label_encoder = joblib.load(os.path.join(MODELS_DIR, 'label_encoder.pkl'))
    feature_columns = joblib.load(os.path.join(MODELS_DIR, 'feature_columns.pkl'))
    # Load dataset for analytics endpoints
    df = pd.read_csv(os.path.join(DATA_DIR, 'ml_features.csv'))
except Exception as e:
    print(f"Warning: Could not load models or data. Ensure pipeline was run. Error: {e}")
    df = pd.DataFrame()

@app.route('/predict-performance', methods=['POST'])
def predict_performance():
    """Predict performance for a new employee"""
    try:
        data = request.json
        input_df = pd.DataFrame([data])
        
        # Preprocessing matching training
        categorical_cols = input_df.select_dtypes(include=['object', 'category']).columns.tolist()
        numeric_cols = input_df.select_dtypes(exclude=['object', 'category']).columns.tolist()
        
        input_encoded = pd.get_dummies(input_df, columns=categorical_cols)
        
        # Ensure all columns from training are present
        for col in feature_columns:
            if col not in input_encoded.columns:
                input_encoded[col] = 0
                
        input_encoded = input_encoded[feature_columns]
        
        # Identify numeric columns from training (to apply imputer/scaler correctly)
        numeric_cols = [c for c in feature_columns if '_' not in c and c != 'DepartmentID'] # Simplification for demo
        
        # Fill missing numeric cols with 0 before imputing (in case they weren't in input at all)
        for col in numeric_cols:
             if col not in input_encoded.columns:
                 input_encoded[col] = np.nan
                 
        try:
            # Re-fetch exact numeric cols from imputer feature names in in if available, but scaler is easier
            num_cols = scaler.feature_names_in_
            input_encoded[num_cols] = imputer.transform(input_encoded[num_cols])
            input_encoded[num_cols] = scaler.transform(input_encoded[num_cols])
        except Exception as e:
            pass # fallback if feature_names_in_ not supported
        
        # Predict
        pred = model.predict(input_encoded)
        prob = model.predict_proba(input_encoded)
        
        label = label_encoder.inverse_transform(pred)[0]
        
        return jsonify({
            'status': 'success',
            'prediction': label,
            'probabilities': {cls: float(p) for cls, p in zip(label_encoder.classes_, prob[0])}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/employee-details', methods=['GET'])
def employee_details():
    emp_id = request.args.get('emp_id', type=int)
    if emp_id:
        emp = df[df['EmployeeID'] == emp_id]
        if not emp.empty:
            return jsonify(emp.to_dict('records')[0])
    return jsonify({'error': 'Employee not found'}), 404

@app.route('/department-analysis', methods=['GET'])
def department_analysis():
    if df.empty: return jsonify([])
    dept_summary = df.groupby('DepartmentID').agg({
        'EmployeeID': 'count',
        'MonthlyIncome': 'mean',
        'satisfaction_score': 'mean',
        'AttendanceRate': 'mean'
    }).rename(columns={'EmployeeID': 'Headcount'})
    return jsonify(dept_summary.to_dict('index'))

@app.route('/top-performers', methods=['GET'])
def top_performers():
    if df.empty: return jsonify([])
    n = request.args.get('n', default=10, type=int)
    top = df[df['PerformanceLabel'] == 'High'].sort_values(by='satisfaction_score', ascending=False).head(n)
    return jsonify(top[['EmployeeID', 'EmployeeName', 'JobRole', 'satisfaction_score']].to_dict('records'))

@app.route('/promotion-candidates', methods=['GET'])
def promotion_candidates():
    if df.empty: return jsonify([])
    candidates = df[(df['PerformanceLabel'] == 'High') & (df['YearsSinceLastPromotion'] >= 3)]
    return jsonify(candidates[['EmployeeID', 'EmployeeName', 'JobRole', 'YearsSinceLastPromotion']].to_dict('records'))

@app.route('/training-insights', methods=['GET'])
def training_insights():
    try:
        et = pd.read_csv(os.path.join(DATA_DIR, 'employee_training.csv'))
        insights = et.groupby('TrainingID')['AssessmentScore'].mean().to_dict()
        return jsonify(insights)
    except:
        return jsonify({'error': 'Training data not found'})

@app.route('/retention-risk', methods=['GET'])
def retention_risk():
    if df.empty: return jsonify([])
    risk = df[(df['satisfaction_score'] < 2.0) & (df['Attrition'] == 'No')]
    return jsonify(risk[['EmployeeID', 'EmployeeName', 'JobRole', 'satisfaction_score']].to_dict('records'))

@app.route('/bulk-predict', methods=['POST'])
def bulk_predict():
    """Predict performance for a batch of employees (Bulk CSV)"""
    try:
        data = request.json # Expects a list of dictionaries
        if not isinstance(data, list):
            return jsonify({'status': 'error', 'message': 'Expected a JSON array of records'}), 400
            
        input_df = pd.DataFrame(data)
        original_ids = input_df.get('EmployeeID', pd.Series(range(1, len(input_df)+1)))
        original_names = input_df.get('EmployeeName', pd.Series([f"Emp {i}" for i in range(1, len(input_df)+1)]))
        
        # Preprocessing matching training
        categorical_cols = input_df.select_dtypes(include=['object', 'category']).columns.tolist()
        input_encoded = pd.get_dummies(input_df, columns=categorical_cols)
        
        # Ensure all columns from training are present
        for col in feature_columns:
            if col not in input_encoded.columns:
                input_encoded[col] = 0
                
        input_encoded = input_encoded[feature_columns]
        
        numeric_cols = [c for c in feature_columns if '_' not in c and c != 'DepartmentID']
        for col in numeric_cols:
             if col not in input_encoded.columns:
                 input_encoded[col] = np.nan
                 
        try:
            num_cols = scaler.feature_names_in_
            input_encoded[num_cols] = imputer.transform(input_encoded[num_cols])
            input_encoded[num_cols] = scaler.transform(input_encoded[num_cols])
        except Exception:
            pass
            
        # Predict
        pred = model.predict(input_encoded)
        prob = model.predict_proba(input_encoded)
        
        labels = label_encoder.inverse_transform(pred)
        
        results = []
        for i in range(len(input_df)):
            # Calculate heuristic scores based on input (safely getting defaults if missing)
            sat = float(input_df.iloc[i].get('satisfaction_score', 3.0))
            tenure = float(input_df.iloc[i].get('YearsAtCompany', 5.0))
            att = float(input_df.iloc[i].get('AttendanceRate', 95.0))
            lbl = labels[i]
            
            promo_score = min(100, int((tenure * 5) + (sat * 10) + (10 if lbl == 'High' else 0)))
            attrition_score = min(100, int(100 - (sat * 20) - (att * 0.1) + (10 if lbl == 'Low' else 0)))
            
            conf = float(max(prob[i]))
            
            results.append({
                'EmployeeID': int(original_ids.iloc[i]),
                'EmployeeName': str(original_names.iloc[i]),
                'Prediction': lbl,
                'Confidence': conf,
                'PromotionReadiness': promo_score,
                'AttritionRisk': attrition_score,
                'Department': str(input_df.iloc[i].get('Department', 'Unknown')),
                'JobRole': str(input_df.iloc[i].get('JobRole', 'Unknown')),
                'MonthlyIncome': float(input_df.iloc[i].get('MonthlyIncome', 50000)),
                'AttendanceRate': att,
                'SatisfactionScore': sat,
                'TrainingScore': float(input_df.iloc[i].get('TrainingTimesLastYear', 0)) * 20
            })
            
        return jsonify({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
