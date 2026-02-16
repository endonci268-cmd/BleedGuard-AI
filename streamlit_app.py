import streamlit as st
import pandas as pd
import joblib
import numpy as np
from streamlit_gsheets import GSheetsConnection

# --- 1. การตั้งค่าหน้าจอให้ Responsive ---
st.set_page_config(
    layout="centered", # ใช้ Centered จะดูง่ายกว่าบนมือถือ
    page_title="NCI BleedGuard-AI",
    page_icon="🩺"
)

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดโมเดล AI ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except:
    st.error("ไม่พบไฟล์โมเดลบน GitHub")

# --- 4. ส่วนหัวโปรแกรม (ออกแบบให้ตัวอักษรพอดีกับมือถือ) ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI</h2>
        <p style='font-size: 0.9rem; color: #555;'>ระบบคัดกรองความเสี่ยงภาวะเลือดออกหลังตัดติ่งเนื้อ<br>
        <b>National Cancer Institute, Thailand</b></p>
    </div>
""", unsafe_allow_html=True)

# --- 5. แดชบอร์ดสรุปผล (ใช้ Expander เพื่อประหยัดพื้นที่บนมือถือ) ---
with st.expander("📊 ดูสถิติภาพรวม (Dashboard)", expanded=False):
    try:
        df_existing = conn.read(ttl=0)
        if not df_existing.empty:
            # ใช้ columns แบบ 2x2 บนมือถือ
            red_c = len(df_existing[df_existing['Risk_Level'].str.contains('High', na=False)])
            yellow_c = len(df_existing[df_existing['Risk_Level'].str.contains('Moderate', na=False)])
            green_c = len(df_existing[df_existing['Risk_Level'].str.contains('Low', na=False)])

            col_m1, col_m2 = st.columns(2)
            col_m1.metric("เคสทั้งหมด", len(df_existing))
            col_m1.metric("🔴 High", red_c)
            col_m2.metric("🟡 Moderate", yellow_c)
            col_m2.metric("🟢 Low", green_c)
        else:
            st.info("ยังไม่มีข้อมูลในระบบ")
            df_existing = pd.DataFrame()
    except:
        st.caption("กำลังเชื่อมต่อฐานข้อมูล...")
        df_existing = pd.DataFrame()

# --- 6. ส่วนการกรอกข้อมูล (เน้นกดง่ายบนมือถือ) ---
st.subheader("📝 บันทึกข้อมูลรายใหม่")
with st.form("mobile_form"):
    # เรียงลงมาเป็นแนวตั้งเพื่อให้กรอกง่ายในมือถือ
    age = st.number_input("อายุ / Age", 1, 120, 60)
    sex = st.radio("เพศ / Sex", ["ชาย (Male)", "หญิง (Female)"], horizontal=True)
    size = st.number_input("ขนาดติ่งเนื้อ / Size (cm)", 0.1, 10.0, 1.0, 0.1)
    loc = st.selectbox("ตำแหน่งติ่งเนื้อ / Location", ["ลำไส้ฝั่งขวา (Right)", "ลำไส้ฝั่งซ้าย (Left)"])
    med = st.radio("ยากลุ่มเสี่ยง / High-Risk Meds", ["ไม่มี", "มี"], horizontal=True)
    
    st.divider() # เส้นคั่นเพื่อให้ดูไม่รก
    
    rad = st.radio("ประวัติการฉายแสง / Radiation", ["ไม่มี", "มี"], horizontal=True)
    chemo = st.radio("ประวัติเคมีบำบัด / Chemo", ["ไม่มี", "มี"], horizontal=True)
    method = st.selectbox("หัตถการ / Procedure", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
    clip = st.radio("การติดคลิป / Hemoclip", ["ไม่มี", "มี"], horizontal=True)

    # ปุ่มกดขนาดใหญ่
    submit_btn = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 7. การคำนวณและแสดงผล ---
if submit_btn:
    # เตรียมข้อมูล AI
    input_df = pd.DataFrame([{
        'Age': age, 'Size_cm': size, 
        'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0,
        'EMR': 1 if method == "EMR" else 0,
        'BX': 1 if "Biopsy" in method else 0,
        'Cold_Poly': 1 if "Cold" in method else 0,
        'Hot_Poly': 1 if "Hot" in method else 0,
        'Sex': 1 if "ชาย" in sex else 0,
        'Surgery': 0
    }])

    prob = model.predict_proba(input_df)[0][1]
    
    # Hybrid Logic
    if size >= 2.0 or clip == "มี" or method == "EMR":
        risk_text, color, note = "🔴 High Risk", "red", "ต้องโทรติดตามภายใน 24 ชม."
    elif prob >= 0.5:
        risk_text, color, note = "🟡 Moderate Risk", "orange", "โทรติดตามภายใน 1-3 วัน"
    else:
        risk_text, color, note = "🟢 Low Risk", "green", "ติดตามตามมาตรฐานปกติ"

    # แสดงผลลัพธ์แบบเด่นๆ
    st.markdown(f"""
        <div style='text-align: center; border: 2px solid {color}; padding: 15px; border-radius: 10px;'>
            <h2 style='color: {color};'>{risk_text}</h2>
            <p>คะแนน AI: {prob:.4f}</p>
            <p><b>คำแนะนำ:</b> {note}</p>
        </div>
    """, unsafe_allow_html=True)

    # บันทึกลง Sheets
    new_data = pd.DataFrame([{
        "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Age": age, "Size": size, "Method": method, "Risk_Level": risk_text
    }])
    
    try:
        final_df = pd.concat([df_existing, new_data], ignore_index=True)
        conn.update(data=final_df)
        st.toast("บันทึกข้อมูลสำเร็จ!", icon="✅")
    except:
        st.error("บันทึกล้มเหลว ตรวจสอบ Secrets")
