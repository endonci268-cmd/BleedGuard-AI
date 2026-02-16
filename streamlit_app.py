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
    # กรุณาตั้งชื่อไฟล์ให้ตรงกับที่คุณอัปโหลดไว้บน GitHub
    return joblib.load('bleedguard_model.pkl') 

try:
    model = load_model()
    # กำหนดชื่อคอลัมน์ให้ตรงตามภาพที่คุณส่งมาเป๊ะๆ
    model_features = [
        'Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Surgery', 
        'Radiation', 'Chemo', 'BX', 'Cold Polyp', 'Hot Polype', 'EMR', 'Sex'
    ]
except:
    st.error("❌ ไม่พบไฟล์โมเดล bleedguard_model.pkl")

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

# --- 6. ฟอร์มบันทึกข้อมูล ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่ง", ["ขวา (Right)", "ซ้าย (Left)"])
        med = st.radio("ยากลุ่มเสี่ยง (ละลายลิ่มเลือด)", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        surgery = st.radio("ประวัติผ่าตัดช่องท้อง", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 7. ส่วนประมวลผล (Hybrid Decision) ---
if submit:
    # แมปข้อมูลให้ตรงกับชื่อฟีเจอร์ในโมเดล (ตามรูปภาพ)
    input_data = {
        'Age': age,
        'Size_cm': size,
        'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0,
        'Surgery': 1 if surgery == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0,
        'BX': 1 if "BX" in method else 0,
        'Cold Polyp': 1 if "Cold" in method else 0,
        'Hot Polype': 1 if "Hot" in method else 0,
        'EMR': 1 if "EMR" in method else 0,
        'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    input_df = pd.DataFrame([input_data])[model_features]

    try:
        prob = model.predict_proba(input_df)[0][1]
        
        # กฎเกณฑ์ทางคลินิก (Clinical Rules) เพื่อช่วย AI ตัดสินใจ
        is_high = (size >= 2.0 or clip == "มี" or method == "EMR")
        is_mod = (med == "มี" or rad == "มี" or chemo == "มี" or surgery == "มี" or age >= 75)

        if is_high or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            advice = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำการปฏิบัติตัวเข้มงวด"
            st_func = st.error
        elif is_mod or prob >= 0.1: # จุดตัดสีเหลืองที่ 0.1
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            advice = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 หลังทำหัตถการ และสังเกตอุจจาระ/ปวดท้อง"
            st_func = st.warning
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            advice = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ, สังเกตอาการทั่วไป"
            st_func = st.success

        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")

        # บันทึกลง Google Sheets (ใช้ชื่อคอลัมน์ตามหัวตารางในรูป)
        new_row = pd.DataFrame([{
            "Timestamp": timestamp, "Age": age, "Size_cm": size, "Med_Risk": med,
            "Clinical_Risk": res, "AI_Score": round(float(prob), 4), "Method": method
        }])
        
        # แสดงผลค้างหน้าจอ
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {col}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{ico}</div>
                <h1 style="color: {col}; margin: 10px 0;">{res}</h1>
                <p style="color: {col}; font-size: 1.2rem;">AI Score: <b>{prob:.4f}</b> | เวลา: {timestamp}</p>
            </div>
        """, unsafe_allow_html=True)
        st_func(advice)
        
        # อัปเดตข้อมูล (Dashboard จะเห็นหลัง refresh)
        df_all = pd.concat([conn.read(ttl=0), new_row], ignore_index=True)
        conn.update(data=df_all)
        st.info("💡 ข้อมูลถูกบันทึกเรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"Error: {e}")
