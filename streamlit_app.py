import streamlit as st
import pandas as pd
import joblib
import numpy as np
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
        loc_input = st.selectbox("ตำแหน่ง", ["ขวา (Right)", "ซ้าย (Left)"])
        med_input = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad_input = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo_input = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        surgery_input = st.radio("ประวัติผ่าตัดช่องท้อง", ["ไม่มี", "มี"], horizontal=True)
        method_input = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip_input = st.radio("มีการติดคลิป", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนประมวลผล ---
if submit:
    # 1. เตรียมค่าตัวเลขตามลำดับ A-N (M=Prob_Risk)
    # ลำดับ: Age, Size_cm, Loc_Right, Med_Risk, Surgery, Radiation, Chemo, BX, Cold Poly, Hot Poly, EMR, Prob_Risk, Sex
    
    prob_risk_val = 1.0 if (size >= 2.0 or clip_input == "มี" or method_input == "EMR") else 0.0

    features = [
        float(age),                                # B: Age
        float(size),                               # C: Size_cm
        1.0 if "ขวา" in loc_input else 0.0,         # D: Loc_Right
        1.0 if med_input == "มี" else 0.0,          # E: Med_Risk
        1.0 if surgery_input == "มี" else 0.0,      # F: Surgery
        1.0 if rad_input == "มี" else 0.0,          # G: Radiation
        1.0 if chemo_input == "มี" else 0.0,        # H: Chemo
        1.0 if "BX" in method_input else 0.0,       # I: BX
        1.0 if "Cold" in method_input else 0.0,     # J: Cold Polypectomy
        1.0 if "Hot" in method_input else 0.0,      # K: Hot Polypectomy
        1.0 if "EMR" in method_input else 0.0,      # L: EMR
        float(prob_risk_val),                       # M: Prob_Risk (สำคัญมาก)
        1.0 if sex_input == "ชาย" else 0.0          # N: Sex
    ]
    
    # แปลงเป็น Numpy Array และ Reshape ให้เป็น 1 แถว หลายคอลัมน์ (ข้ามการเช็คชื่อฟีเจอร์)
    input_array = np.array(features).reshape(1, -1)

    try:
        # 2. ทำนายผล (ส่งเป็นค่าตัวเลขล้วนๆ)
        prob = model.predict_proba(input_array)[0][1]
        
       # --- 3. ตัดสินใจระดับความเสี่ยง (รวมเกณฑ์ AI + เกณฑ์ติ่งเนื้อ < 0.5 cm) ---
        
        # กฎเหล็ก 1: ถ้าขนาด < 0.5 cm และไม่มีปัจจัยเสี่ยงอื่น = เขียวแน่นอน (Low Risk)
        if size < 0.5 and med_input == "ไม่มี" and clip_input == "ไม่มี":
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ (ติ่งเนื้อขนาดเล็กความเสี่ยงต่ำ)"
            st_func = st.success

        # กฎเหล็ก 2: ถ้าเข้าเกณฑ์ High Risk ทางคลินิก = แดง (High Risk)
        elif prob_risk_val == 1.0 or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            adv = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำกลับบ้านแบบเข้มงวด"
            st_func = st.error
            
        # กฎเหล็ก 3: ถ้าคะแนน AI เกิน 0.02 (และขนาดไม่อยู่ในกลุ่ม Low) = เหลือง (Moderate Risk)
        elif prob >= 0.02: 
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            adv = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 และสังเกตอาการผิดปกติ (Post-op Call)"
            st_func = st.warning
            
        # นอกนั้นเป็นเขียวปกติ
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ"
            st_func = st.success
            
        # ถ้าต่ำกว่า 0.02 = เขียว
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
        
        # 4. บันทึกลง Google Sheets
        new_row = pd.DataFrame([{"Timestamp": timestamp, "Final_Risk_Level": res, "AI_Score": prob, "Method": method_input}])
        df_all = pd.concat([df_existing, new_row], ignore_index=True)
        conn.update(data=df_all)
        st.info("💡 บันทึกข้อมูลเรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"Error during prediction: {e}")
