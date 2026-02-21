import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import pytz
from datetime import datetime

# --- CONFIG PAGE ---
st.set_page_config(page_title="BleedGuard AI - NCI", layout="wide")
tz_th = pytz.timezone('Asia/Bangkok')

# --- 1. LOAD MODEL ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except Exception as e:
    st.error(f"ไม่พบไฟล์โมเดล: {e}")

# --- 2. GSHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(worksheet="Sheet1", ttl="0")

# --- 3. UI: TABS ---
tab1, tab2 = st.tabs(["🩺 ระบบประเมินความเสี่ยง", "📊 Dashboard & Database"])

with tab1:
    st.title("🎗️ BleedGuard: ระบบคัดกรองเลือดออกหลังส่องกล้อง")
    st.subheader("สถาบันมะเร็งแห่งชาติ (National Cancer Institute)")

    with st.form("triage_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📋 ข้อมูลผู้ป่วย")
            case_id_input = st.text_input("รหัสผู้ป่วย (Case ID)", placeholder="เช่น NCI-001")
            age_input = st.number_input("อายุ (Age)", 0, 120, 60)
            sex_input = st.selectbox("เพศ (Sex)", [0, 1], format_func=lambda x: "หญิง" if x==0 else "ชาย")
            size_input = st.number_input("ขนาดติ่งเนื้อ (Size cm)", 0.0, 10.0, 1.0, step=0.1)
            loc_side = st.selectbox("ตำแหน่ง (Location)", ["Left Side", "Right Side"])
            med_in = st.checkbox("ใช้ยาละลายลิ่มเลือด (Medication)")
            surg_in = st.checkbox("ประวัติผ่าตัดลำไส้ (Surgery)")
            
        with c2:
            st.markdown("### ✂️ หัตถการและประวัติ")
            rad_in = st.checkbox("ประวัติฉายแสง (Radiation)")
            chemo_in = st.checkbox("ประวัติเคมีบำบัด (Chemo)")
            bx_in = st.checkbox("Biopsy (BX)")
            cold_in = st.checkbox("Cold Snare Polypectomy")
            hot_in = st.checkbox("Hot Polypectomy")
            emr_in = st.checkbox("EMR")
            clip_in = st.checkbox("มีการติด Hemoclip (Clip)")

        submit = st.form_submit_button("ประเมินผลและบันทึกข้อมูล")

    if submit:
        # --- A. เตรียมข้อมูล (เรียงลำดับตาม Colab เป๊ะๆ) ---
        loc_right = 1 if loc_side == "Right Side" else 0
        
        # 🚨 แก้ไขลำดับที่นี่ตามที่พี่แจ้งมาจาก Colab
        features_list = [
            age_input,          # 'age'
            sex_input,          # 'sex'
            size_input,         # 'size_cm'
            loc_right,          # 'loc_right'
            int(emr_in),        # 'emr'
            int(bx_in),         # 'bx'
            int(cold_in),       # 'cold_snare'
            int(hot_in),        # 'hot_poly'
            int(rad_in),        # 'radiation'
            int(chemo_in),      # 'chemo'
            int(surg_in),       # 'surgery'
            int(med_in)         # 'med_risk'
        ]
        
        # ส่งเป็น DataFrame พร้อมระบุชื่อคอลัมน์ให้ตรงเป๊ะ (วิธีนี้ชัวร์ที่สุด)
        input_df = pd.DataFrame([features_list], columns=[
            'age', 'sex', 'size_cm', 'loc_right', 'emr', 'bx', 'cold_snare', 
            'hot_poly', 'radiation', 'chemo', 'surgery', 'med_risk'
        ])
        
        try:
            # ทำนาย AI Probability
            prob = model.predict_proba(input_df)[0][1]
            
            # --- B. NEW LOGIC (Sensitivity 100%) ---
            res, bg_color, advice, text_color = "", "", "", "#FFFFFF"
            
            if size_input >= 2.0 or emr_in or rad_in:
                res, bg_color, advice = "🔴 High Risk", "#FF4B4B", "เฝ้าระวังเข้มงวด: โทรติดตามอาการวันที่ 1, 2 และ 3"
            elif clip_in or prob > 0.12:
                res, bg_color, advice, text_color = "🟡 Moderate Risk", "#FFFF00", "เฝ้าระวังต่อเนื่อง: โทรติดตามอาการในวันที่ 2", "#000000"
            else:
                res, bg_color, advice = "🟢 Low Risk", "#28A745", "ไม่ต้องโทรติดตาม: ให้คำแนะนำการสังเกตอาการด้วยตนเอง"

            # --- C. แสดงผลหน้าจอ ---
            st.markdown(f"""
                <div style="background-color:{bg_color}; padding:40px; border-radius:10px; text-align:center; margin-top:20px; border: 2px solid #333;">
                    <h1 style="color:{text_color}; margin:0; font-size:45px;">{res}</h1>
                    <p style="color:{text_color}; font-size:22px; font-weight:bold; white-space: pre-line;">{advice}</p>
                    <p style="color:{text_color}; font-size:16px;">AI Probability: {prob:.4f}</p>
                </div>
            """, unsafe_allow_html=True)

            # --- D. บันทึก (17 คอลัมน์) ---
            current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input, 
                "loc_right": loc_right, "Medication": int(med_in), "Surgery": int(surg_in), 
                "Radiation": int(rad_in), "Chemo": int(chemo_in), "BX": int(bx_in), 
                "Cold_Poly": int(cold_in), "Hot_Poly": int(hot_in), "EMR": int(emr_in), 
                "Clip": int(clip_in), "Risk_Level": res, "Advice": advice
            }])
            
            conn.update(worksheet="Sheet1", data=pd.concat([get_data(), new_row], ignore_index=True))
            st.toast("บันทึกข้อมูลเรียบร้อย!")
                
        except Exception as e:
            st.error(f"AI Error: {e}")

with tab2:
    st.header("📊 Dashboard")
    df = get_data()
    if not df.empty:
        st.dataframe(df.sort_values(by="Timestamp", ascending=False))
