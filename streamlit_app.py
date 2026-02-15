import streamlit as st
import pandas as pd
import joblib

# --- 1. โหลดโมเดล LG (Version 1.6.1) ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except Exception as e:
    st.error(f"ไม่สามารถโหลดโมเดลได้: {e}")

# --- 2. ตรรกะการคัดกรอง (Hybrid Logic) ---
def bleedguard_triage_logic(row, threshold=0.5):
    # กฎ Override ความเสี่ยงต่ำ
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk (Normal Care)"
    # กฎ Override ความเสี่ยงสูง 
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk (Intensive Follow-up)"
    # ใช้ AI ตัดที่ Threshold
    return "🟡 Moderate Risk" if row['Prob_Risk'] >= threshold else "🟢 Low Risk"

st.set_page_config(layout="wide", page_title="BleedGuard AI")
st.title("BleedGuard AI Triage System (Production)")

# --- 3. ส่วนรับข้อมูล (Input) ---
with st.expander("ข้อมูลประชากรและหัตถการ", expanded=True):
    c1, c2, c3 = st.columns(3)
    age = c1.number_input("Age", 0, 120, 60)
    sex = 1 if c2.selectbox("Sex", ['M', 'F']) == 'M' else 0
    size_cm = c3.number_input("Size_cm (ซม.)", 0.0, 10.0, 1.0, 0.1)

    c4, c5, c6 = st.columns(3)
    loc_right = c4.selectbox("Loc_Right (ฝั่งขวา)", [0, 1])
    med_risk = c5.selectbox("Med_Risk (โรคประจำตัว)", [0, 1])
    surgery = c6.selectbox("Surgery (ประวัติผ่าตัด)", [0, 1])

    c7, c8, c9 = st.columns(3)
    radiation = c7.selectbox("Radiation (ฉายแสง)", [0, 1])
    chemo = c8.selectbox("Chemo (เคมีบำบัด)", [0, 1])
    bx = c9.selectbox("BX (ตัดชิ้นเนื้อ)", [0, 1])

    c10, c11, c12 = st.columns(3)
    cold_p = c10.selectbox("Cold Polypectomy", [0, 1])
    hot_p = c11.selectbox("Hot Polypectomy", [0, 1])
    emr = c12.selectbox("EMR", [0, 1])
    
    clinical_risk_outcome = st.selectbox("Clinical_Risk_Outcome (แพทย์ติดคลิป/ความเสี่ยงหน้างาน)", [0, 1])

# --- 4. การประมวลผล ---
if st.button("ทำการคัดกรอง"):
    # สร้าง DataFrame ให้ตรงตาม Feature Names ของโมเดล
    input_df = pd.DataFrame([{
        'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': loc_right, 'Med_Risk ': med_risk,
        'Surgery ': surgery, 'Radiation': radiation, 'Chemo': chemo, 'BX': bx,
        'Cold Polypectomy': cold_p, 'Hot Polypectomy': hot_p, 'EMR': emr,
        'Prob_Risk': 0.0, 'Sex': sex
    }])

    # ใช้โมเดล LG ทำนายค่า Prob_Risk จริงๆ
    features = input_df.drop(columns=['Prob_Risk'])
    prob = model.predict_proba(features)[0][1]
    input_df.at[0, 'Prob_Risk'] = prob
    input_df.at[0, 'Clinical_Risk_Outcome'] = clinical_risk_outcome

    # แสดงผล
    res = bleedguard_triage_logic(input_df.iloc[0])
    st.subheader(f"ผลลัพธ์: {res}")
    st.write(f"📊 ค่าความน่าจะเป็นจาก AI: **{prob:.4f}**")

