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
    # ตรวจสอบชื่อไฟล์ใน GitHub ให้ตรงนะครับ
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except Exception as e:
    st.error(f"ไม่พบไฟล์โมเดล bleedguard_model.pkl: {e}")

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
        # --- A. เตรียมข้อมูลสำหรับ AI (ต้องครบ 12 ตัวตามลำดับ) ---
        loc_right = 1 if loc_side == "Right Side" else 0
        
        # มัดรวมปัจจัย 12 ตัว (ห้ามขาด ห้ามเกิน ห้ามสลับลำดับ)
        features_list = [
            age_input,        # 1
            sex_input,        # 2
            size_input,       # 3
            loc_right,        # 4
            int(med_in),      # 5
            int(surg_in),     # 6
            int(rad_in),      # 7
            int(chemo_in),    # 8
            int(bx_in),       # 9
            int(cold_in),     # 10
            int(hot_in),      # 11
            int(emr_in)       # 12
        ]
        
        # แปลงเป็น Numpy Array (ลบชื่อคอลัมน์ออกเพื่อป้องกัน ValueError)
        input_array = np.array(features_list).reshape(1, -1)
        
        try:
            # ทำนาย AI Probability
            prob = model.predict_proba(input_array)[0][1]
            
            # --- B. NEW LOGIC (Sensitivity 100%) ---
            res, advice, bg_color, text_color = "", "", "", "#FFFFFF"
            
            # 🔴 กฎสีแดง (Override)
            if size_input >= 2.0 or emr_in or rad_in:
                res, bg_color, advice = "🔴 High Risk", "#FF4B4B", "เฝ้าระวังเข้มงวด: โทรติดตามอาการวันที่ 1, 2 และ 3"
            # 🟡 กฎสีเหลือง (AI Threshold 0.12 หรือติดคลิป)
            elif clip_in or prob > 0.12:
                res, bg_color, advice, text_color = "🟡
