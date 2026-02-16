import streamlit as st
import pandas as pd
import joblib

# --- 1. โหลดโมเดล ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 2. Logic การคัดกรอง (อิงตามต้นฉบับที่คุณส่งมา) ---
def bleedguard_triage_logic(row, prob, threshold=0.1): # ปรับ threshold ให้เห็นสีเหลืองง่ายขึ้น
    # กฎ 1: ขนาดเล็ก + BX + ไม่ใช่ Cold Poly = เขียว
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk (Normal Care)", "#D2FFD2", "😊"
    
    # กฎ 2: Clinical High Risk = แดง
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk (Intensive Follow-up)", "#FFD2D2", "😫"
    
    # กฎ 3: ตัดตามค่า AI
    if prob >= threshold:
        return "🟡 Moderate Risk", "#FFF9C4", "😟"
    else:
        return "🟢 Low Risk", "#D2FFD2", "😊"

st.set_page_config(layout="wide")
st.title("🩺 BleedGuard AI Triage System (Production)")

# --- 3. ส่วน Input Features ---
with st.expander("📝 ข้อมูลคนไข้และหัตถการ", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex = st.selectbox("เพศ", [0, 1], format_func=lambda x: "ชาย" if x == 1 else "หญิง")
        size_cm = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.2)
        loc_right = st.selectbox("ตำแหน่ง (ขวา=1, ซ้าย=0)", [1, 0])
        med_risk = st.selectbox("ยากลุ่มเสี่ยง (มี=1, ไม่มี=0)", [1, 0])
    with col2:
        surgery = st.selectbox("ประวัติผ่าตัด (มี=1)", [1, 0])
        radiation = st.selectbox("ประวัติฉายแสง (มี=1)", [1, 0])
        chemo = st.selectbox("ประวัติเคมีบำบัด (มี=1)", [1, 0])
        bx = st.selectbox("Biopsy (BX=1)", [1, 0])
        cold_polypectomy = st.selectbox("Cold Polypectomy (มี=1)", [1, 0])
        hot_polypectomy = st.selectbox("Hot Polypectomy (มี=1)", [1, 0])
        emr = st.selectbox("EMR (มี=1)", [1, 0])

# --- 4. การประมวลผล ---
if st.button("📊 ทำการคัดกรอง"):
    # คำนวณ Clinical Risk Outcome เบื้องต้น (ตามกฎ High Risk)
    clinical_risk_outcome = 1 if (size_cm >= 2.0 or emr == 1) else 0

    # สร้าง DataFrame ให้ชื่อคอลัมน์สะกด "เป๊ะ" ตามที่โมเดลเห็นตอน Fit (มีช่องว่างท้ายชื่อ)
    input_data = {
        'Age': age, 
        'Size_cm ': size_cm,       # มีช่องว่าง
        'Loc_Right ': loc_right,   # มีช่องว่าง
        'Med_Risk ': med_risk,     # มีช่องว่าง
        'Surgery ': surgery,       # มีช่องว่าง
        'Radiation': radiation, 
        'Chemo': chemo, 
        'BX': bx,
        'Cold Polypectomy': cold_polypectomy, 
        'Hot Polypectomy': hot_polypectomy, 
        'EMR': emr,
        'Sex': sex
    }
    
    input_df = pd.DataFrame([input_data])
    
    try:
        # ทำนายค่าความน่าจะเป็น
        actual_prob = model.predict_proba(input_df)[0][1]
        
        # ใส่ค่าเพิ่มเพื่อใช้ใน Logic
        input_df['Prob_Risk'] = actual_prob
        input_df['Clinical_Risk_Outcome'] = clinical_risk_outcome

        # เรียกใช้ Logic การคัดกรอง
        result, b_color, icon = bleedguard_triage_logic(input_df.iloc[0], actual_prob)
        
        # --- 5. แสดงผลลัพธ์ ---
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_color}; padding: 30px; border-radius: 15px; text-align: center; border: 2px solid #ccc;">
                <h1 style="font-size: 80px; margin: 0;">{icon}</h1>
                <h2 style="margin: 10px 0;">{result}</h2>
                <p style="font-size: 1.2rem;">AI Probability Score: <b>{actual_prob:.4f}</b></p>
            </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
        st.write("ตรวจสอบชื่อฟีเจอร์ที่โมเดลต้องการอีกครั้ง")
