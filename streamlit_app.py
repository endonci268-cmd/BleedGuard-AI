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
    # ไฟล์โมเดลต้องชื่อ bleedguard_model.pkl อยู่ในโฟลเดอร์เดียวกับโค้ด
    return joblib.load('bleedguard_model.pkl') 

try:
    model = load_model()
except Exception as e:
    st.error(f"❌ ไม่สามารถโหลดไฟล์โมเดลได้: {e}")

# --- 4. ฟังก์ชันดึงเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 5. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI (Endo-STAT)</h2>
        <p style='font-size: 1.1rem; color: #555;'>ระบบบริหารจัดการความเสี่ยงศูนย์ส่องกล้อง สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. แดชบอร์ด (Dashboard) แสดงผลอัตโนมัติ ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        # ล้างข้อมูลแถวที่ไม่มีผลลัพธ์ความเสี่ยง
        df_clean = df_existing.dropna(subset=['Final_Risk_Level']).copy()
        
        st.subheader("📊 สถิติภาพรวมการคัดกรองความเสี่ยง")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสสะสมทั้งหมด", f"{len(df_clean)} ราย")
        m2.metric("🔴 High Risk", len(df_clean[df_clean['Final_Risk_Level'].str.contains('High', na=False)]))
        m3.metric("🟡 Moderate Risk", len(df_clean[df_clean['Final_Risk_Level'].str.contains('Moderate', na=False)]))
        m4.metric("🟢 Low Risk", len(df_clean[df_clean['Final_Risk_Level'].str.contains('Low', na=False)]))

        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df_clean, names='Final_Risk_Level', color='Final_Risk_Level',
                             color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'},
                             hole=0.4, title="สัดส่วนระดับความเสี่ยงในระบบ")
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            fig_bar = px.bar(df_clean, x='Method', color='Final_Risk_Level',
                             color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'},
                             title="จำนวนหัตถการแยกตามระดับความเสี่ยง")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        df_existing = pd.DataFrame()
except:
    df_existing = pd.DataFrame()

st.divider()

# --- 7. ฟอร์มบันทึกข้อมูลคนไข้ ---
st.subheader("📝 บันทึกข้อมูลและประเมินความเสี่ยงรายใหม่")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc_input = st.selectbox("ตำแหน่ง", ["ขวา (Right)", "ซ้าย (Left)"])
        med_input = st.radio("ยากลุ่มเสี่ยง (ละลายลิ่มเลือด)", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad_input = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo_input = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        surgery_input = st.radio("ประวัติผ่าตัดช่องท้อง", ["ไม่มี", "มี"], horizontal=True)
        method_input = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip_input = st.radio("มีการติดคลิป (Hemoclip)", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลด้วย AI และบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนประมวลผล (Hybrid AI & Clinical Logic) ---
if submit:
    # เตรียมค่าตัวแปรตามลำดับ A-N (M=Prob_Risk)
    prob_risk_val = 1.0 if (size >= 2.0 or clip_input == "มี" or method_input == "EMR") else 0.0

    # จัดลง Array เพื่อข้ามปัญหา Feature Name Match
    # ลำดับ: Age, Size_cm, Loc_Right, Med_Risk, Surgery, Radiation, Chemo, BX, Cold Poly, Hot Poly, EMR, Prob_Risk, Sex
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
        float(prob_risk_val),                       # M: Prob_Risk (M-Column)
        1.0 if sex_input == "ชาย" else 0.0          # N: Sex
    ]
    
    input_array = np.array(features).reshape(1, -1)

    try:
        # ทำนายผลจาก AI Model
        prob = model.predict_proba(input_array)[0][1]
        
        # --- การตัดสินใจ (Decision Logic) ---
        
        # 1. เกณฑ์ Low Risk พื้นฐาน: ขนาด < 0.5 cm และไม่มีปัจจัยเสี่ยง
        if size < 0.5 and med_input == "ไม่มี" and clip_input == "ไม่มี":
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ (ติ่งเนื้อขนาดเล็กความเสี่ยงต่ำ)"
            st_func = st.success

        # 2. เกณฑ์ High Risk: เข้าเกณฑ์ Clinical หรือ AI Score สูง
        elif prob_risk_val == 1.0 or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            adv = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำกลับบ้านแบบเข้มงวด"
            st_func = st.error
            
        # 3. เกณฑ์ Moderate Risk: คะแนน AI เกินเกณฑ์ Calibrated Threshold (0.02)
        elif prob >= 0.02: 
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            adv = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 และสังเกตอาการผิดปกติ (Post-op Call)"
            st_func = st.warning
            
        # 4. นอกนั้นเป็น Low Risk ปกติ
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ"
            st_func = st.success

        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")

        # แสดงผลลัพธ์แบบ Visual ค้างหน้าจอ
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {col}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{ico}</div>
                <h1 style="color: {col}; margin: 10px 0;">{res}</h1>
                <p style="color: {col}; font-size: 1.2rem;">AI Score: <b>{prob:.4f}</b> | {timestamp}</p>
            </div>
        """, unsafe_allow_html=True)
        st_func(adv)
        
        # บันทึกลง Google Sheets
        new_row = pd.DataFrame([{
            "Timestamp": timestamp, 
            "Final_Risk_Level": res, 
            "AI_Score": round(float(prob), 4), 
            "Method": method_input,
            "Size_cm": size
        }])
        df_all = pd.concat([df_existing, new_row], ignore_index=True)
        conn.update(data=df_all)
        st.info("💡 บันทึกข้อมูลและอัปเดตสถิติเรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"Error during prediction: {e}")
