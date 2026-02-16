import streamlit as st
import pandas as pd
import joblib
import numpy as np
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าจอให้เหมาะกับมือถือ ---
st.set_page_config(layout="centered", page_title="NCI BleedGuard-AI", page_icon="🩺")

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดสมอง AI (.pkl) ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
    # ดึงรายชื่อตัวแปรที่โมเดลต้องการจากไฟล์ตรงๆ
    if hasattr(model, 'feature_names_in_'):
        model_features = model.feature_names_in_.tolist()
    else:
        model_features = ['Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Radiation', 'Chemo', 'Surgery', 'BX', 'Cold_Poly', 'Hot_Poly', 'EMR', 'Sex']
except:
    st.error("❌ ไม่พบไฟล์ bleedguard_model.pkl")

# --- 4. ส่วนหัวโปรแกรม ---
st.markdown("<h2 style='text-align: center; color: #003366;'>🩺 NCI BleedGuard-AI</h2>", unsafe_allow_html=True)
st.write("---")

# --- 5. Dashboard (ดึงข้อมูลจาก Sheets มาโชว์) ---
with st.expander("📊 สถิติภาพรวม (Dashboard)", expanded=False):
    try:
        df_existing = conn.read(ttl=0)
        if not df_existing.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("เคสทั้งหมด", len(df_existing))
            c2.metric("🔴 High", len(df_existing[df_existing['Risk_Level'] == '🔴 High Risk']))
            c3.metric("🟢 Low", len(df_existing[df_existing['Risk_Level'] == '🟢 Low Risk']))
    except:
        df_existing = pd.DataFrame()

# --- 6. ฟอร์มกรอกข้อมูล (อิงตามตัวแปรของคุณ) ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form"):
    age = st.number_input("อายุ (ปี)", 1, 120, 60)
    sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
    size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0)
    loc = st.selectbox("ตำแหน่งติ่งเนื้อ", ["ขวา", "ซ้าย"])
    med = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
    rad = st.radio("ประวัติการฉายแสง", ["ไม่มี", "มี"], horizontal=True)
    chemo = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
    method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
    clip = st.radio("การติดคลิป (Clinical Risk)", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 7. การคำนวณและบันทึก (ให้ตรงกับชื่อคอลัมน์ที่ระบุมา) ---
if submit:
    # เตรียมข้อมูลส่งให้ AI
    raw_for_ai = {
        'Age': age, 'Size_cm': size,
        'Loc_Right': 1 if loc == "ขวา" else 0,
        'Med_Risk': 1 if med == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0,
        'Surgery': 0, 'BX': 1 if "BX" in method else 0,
        'Cold_Poly': 1 if "Cold" in method else 0,
        'Hot_Poly': 1 if "Hot" in method else 0,
        'EMR': 1 if method == "EMR" else 0,
        'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    # กันพัง: ปรับลำดับ/ชื่อให้ตรงกับ AI
    input_df = pd.DataFrame([raw_for_ai])
    for col in model_features:
        if col not in input_df.columns: input_df[col] = 0
    input_df = input_df[model_features]

    # AI คำนวณ
    prob = model.predict_proba(input_df)[0][1]
    
    # Hybrid Logic (Clinical Risk)
    clin_risk = "High" if (size >= 2.0 or clip == "มี" or method == "EMR") else "Normal"
    risk_text = "🔴 High Risk" if (clin_risk == "High" or prob >= 0.5) else "🟢 Low Risk"

    # บันทึกลง Google Sheets ตามชื่อคอลัมน์ที่คุณระบุมาเป๊ะๆ
    data_to_save = pd.DataFrame([{
        "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Age": age,
        "Sex": sex_input,
        "Size_cm": size,
        "Loc_Right": 1 if loc == "ขวา" else 0,
        "Med_Risk": 1 if med == "มี" else 0,
        "Surgery": 0,
        "Radiation": 1 if rad == "มี" else 0,
        "Chemo": 1 if chemo == "มี" else 0,
        "BX": 1 if "BX" in method else 0,
        "Cold_Poly": 1 if "Cold" in method else 0,
        "Hot_Poly": 1 if "Hot" in method else 0,
        "EMR": 1 if method == "EMR" else 0,
        "Clinical_Risk": clin_risk,
        "AI_Score": round(float(prob), 4),
        "Risk_Level": risk_text
    }])

    try:
        updated_df = pd.concat([df_existing, data_to_save], ignore_index=True)
        conn.update(data=updated_df)
        st.success(f"บันทึกสำเร็จ! ผลคือ {risk_text}")
        st.balloons()
    except Exception as e:
        st.error(f"บันทึกล้มเหลว: {e}")
