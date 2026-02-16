import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(layout="wide", page_title="NCI BleedGuard-AI", page_icon="🩺")

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดสมอง AI ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl') 

try:
    model = load_model()
    # นี่คือลำดับที่ถูกต้องที่สุดอิงจาก Error Message ของคุณครับ
    # ต้องเรียงตามนี้เป๊ะๆ AI ถึงจะยอมอ่าน
    model_features = [
        'Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Surgery', 
        'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 
        'EMR', 'Prob_Risk', 'Sex'
    ]
except Exception as e:
    st.error(f"❌ โหลดโมเดลไม่สำเร็จ: {e}")

# --- 4. ฟังก์ชันดึงเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 5. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบสนับสนุนการตัดสินใจ พัฒนาโดยพยาบาลส่องกล้อง สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. แดชบอร์ด (Dashboard) ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Final_Risk_Level']).copy()
        st.subheader("📊 สถิติภาพรวม")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสสะสม", f"{len(df_clean)} ราย")
        m2.metric("🔴 High", len(df_clean[df_clean['Final_Risk_Level'].str.contains('High', na=False)]))
        m3.metric("🟡 Moderate", len(df_clean[df_clean['Final_Risk_Level'].str.contains('Moderate', na=False)]))
        m4.metric("🟢 Low", len(df_clean[df_clean['Final_Risk_Level'].str.contains('Low', na=False)]))
except:
    df_existing = pd.DataFrame()

st.divider()

# --- 7. ฟอร์มบันทึกข้อมูล ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่ง", ["ขวา (Right)", "ซ้าย (Left)"])
        med = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        surgery = st.radio("ประวัติผ่าตัดช่องท้อง", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนประมวลผล ---
if submit:
    # 1. คำนวณค่า Prob_Risk (คอลัมน์ M) ตามเกณฑ์ทางคลินิก
    prob_risk_val = 1 if (size >= 2.0 or clip == "มี" or method == "EMR") else 0

    # 2. เก็บข้อมูลลงใน Dictionary เบื้องต้น
    raw_data = {
        'Age': age,
        'Size_cm': size,
        'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0,
        'Surgery': 1 if surgery == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0,
        'BX': 1 if "BX" in method else 0,
        'Cold Polypectomy': 1 if "Cold" in method else 0,
        'Hot Polypectomy': 1 if "Hot" in method else 0,
        'EMR': 1 if "EMR" in method else 0,
        'Prob_Risk': prob_risk_val,
        'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    # 3. สร้าง DataFrame และ "บังคับลำดับคอลัมน์" ให้ตรงตาม model_features เป๊ะๆ
    input_df = pd.DataFrame([raw_data])
    input_df = input_df[model_features] # บรรทัดนี้คือการจัดลำดับครับ

    try:
        # ทำนายผล
        prob = model.predict_proba(input_df)[0][1]
        
        # ตัดสินใจระดับความเสี่ยง (ใช้จุดตัด 0.05 เพื่อให้เห็นสีเหลือง 😟)
        if prob_risk_val == 1 or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            adv = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำกลับบ้านแบบเข้มงวด"
            st_func = st.error
        elif prob >= 0.05:
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            adv = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 และสังเกตอาการผิดปกติ"
            st_func = st.warning
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ"
            st_func = st.success

        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")

        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {col}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{ico}</div>
                <h1 style="color: {col}; margin: 10px 0;">{res}</h1>
                <p style="color: {col}; font-size: 1.2rem;">AI Score: <b>{prob:.4f}</b> | {timestamp}</p>
            </div>
        """, unsafe_allow_html=True)
        st_func(adv)
        
        # อัปเดต Google Sheets
        new_row = pd.DataFrame([{"Timestamp": timestamp, "Final_Risk_Level": res, "AI_Score": prob, "Method": method}])
        df_all = pd.concat([df_existing, new_row], ignore_index=True)
        conn.update(data=df_all)
        st.info("💡 ข้อมูลถูกบันทึกเรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"Error: {e}")
