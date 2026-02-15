import streamlit as st
import pandas as pd
import joblib

# --- โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

def bleedguard_triage_logic(row, threshold=0.5):
    # 1. กฎ Override ความเสี่ยงต่ำ (De-escalation) 
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk (Normal Care)"
    # 2. กฎ Override ความเสี่ยงสูง (Safety First) 
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk (Intensive Follow-up)"
    # 3. ใช้ AI ตัดที่ Threshold 
    return "🟡 Moderate Risk" if row['Prob_Risk'] >= threshold else "🟢 Low Risk"

st.set_page_config(layout="wide")
st.title("BleedGuard AI Triage System (Production)")

# --- (ส่วน Input Features เหมือนเดิมของคุณทั้งหมด) ---
# ... [ก๊อปปี้ส่วน expander ต่างๆ จากโค้ดเดิมมาวาง] ...

# --- การประมวลผลด้วยโมเดลจริง ---
if st.button("ทำการคัดกรอง"):
    # สร้าง DataFrame ให้ตรงตามที่โมเดล LG ต้องการ (13 columns) 
    input_df = pd.DataFrame([{
        'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': loc_right, 'Med_Risk ': med_risk,
        'Surgery ': surgery, 'Radiation': radiation, 'Chemo': chemo, 'BX': bx,
        'Cold Polypectomy': cold_polypectomy, 'Hot Polypectomy': hot_polypectomy, 'EMR': emr,
        'Prob_Risk': 0.0, # ค่าว่างไว้รอคำนวณ
        'Sex': sex
    }])

    # ใช้โมเดล LG ทำนายค่า Prob_Risk จริงๆ 
    # (ลบคอลัมน์ Prob_Risk ออกชั่วคราวก่อนส่งเข้าโมเดล เพราะเป็นเป้าหมายไม่ใช่ปัจจัยนำเข้า)
    features = input_df.drop(columns=['Prob_Risk'])
    actual_prob = model.predict_proba(features)[0][1]
    
    input_df.at[0, 'Prob_Risk'] = actual_prob
    input_df.at[0, 'Clinical_Risk_Outcome'] = clinical_risk_outcome

    # แสดงผล
    triage_result = bleedguard_triage_logic(input_df.iloc[0])
    st.subheader(f"ผลลัพธ์: {triage_result}")
    st.write(f"📊 ค่าความน่าจะเป็นจาก AI (Prob_Risk): {actual_prob:.4f}")