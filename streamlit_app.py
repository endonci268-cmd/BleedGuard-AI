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
    # ตรวจสอบชื่อไฟล์โมเดลใน GitHub ให้ตรงนะครับ
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
            case_id_input = st.text_input("รหัสผู้ป่วย (Case ID)", placeholder="NCI-XXX")
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
        # --- A. เตรียมข้อมูลสำหรับ AI (ส่งเป็น Array เพื่อเลี่ยง Error ชื่อคอลัมน์) ---
        loc_right = 1 if loc_side == "Right Side" else 0
        
        # มัดรวมปัจจัย 12 ตัว (เรียงลำดับตามที่ใช้ใน Colab)
        features_list = [
            age_input, sex_input, size_input, loc_right, 
            int(med_in), int(surg_in), int(rad_in), int(chemo_in), 
            int(bx_in), int(cold_in), int(hot_in), int(emr_in)
        ]
        
        # 🌟 แปลงเป็น Numpy Array เพื่อแก้ปัญหา ValueError เรื่อง Feature Names
        input_array = np.array(features_list).reshape(1, -1)
        
        # ทำนาย AI Probability
        prob = model.predict_proba(input_array)[0][1]
        
        # --- B. NEW LOGIC (Sensitivity 100%) ---
        res, advice, bg_color, text_color = "", "", "", "#FFFFFF"
        
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

        # --- D. บันทึกลง GOOGLE SHEETS (17 คอลัมน์) ---
        current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
        
        new_row = pd.DataFrame([{
            "Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input, 
            "loc_right": loc_right, "Medication": int(med_in), "Surgery": int(surg_in), 
            "Radiation": int(rad_in), "Chemo": int(chemo_in), "BX": int(bx_in), 
            "Cold_Poly": int(cold_in), "Hot_Poly": int(hot_in), "EMR": int(emr_in), 
            "Clip": int(clip_in), "Risk_Level": res, "Advice": advice
        }])
        
        try:
            df_old = get_data()
            updated_df = pd.concat([df_old, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast(f"บันทึกข้อมูลสำเร็จ: {current_time}")
        except:
            st.error("⚠️ ไม่สามารถบันทึกข้อมูลลง Google Sheets ได้")

with tab2:
    st.header("📊 แดชบอร์ดสรุปผลการคัดกรอง")
    try:
        df = get_data()
        if not df.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("เคสสะสมทั้งหมด", len(df))
            m2.metric("🔴 เสี่ยงสูง", len(df[df['Risk_Level'].str.contains("🔴")]))
            m3.metric("🟡 เสี่ยงปานกลาง", len(df[df['Risk_Level'].str.contains("🟡")]))
            m4.metric("🟢 เสี่ยงต่ำ", len(df[df['Risk_Level'].str.contains("🟢")]))
            
            st.divider()
            c_left, c_right = st.columns([1, 1])
            with c_left:
                fig = px.pie(df, names='Risk_Level', color='Risk_Level',
                             color_discrete_map={"🔴 High Risk": "#FF4B4B", "🟡 Moderate Risk": "#FFFF00", "🟢 Low Risk": "#28A745"})
                st.plotly_chart(fig, use_container_width=True)
            with c_right:
                st.dataframe(df[['Timestamp', 'Case_ID', 'Risk_Level', 'Advice']].sort_values(by="Timestamp", ascending=False), 
                             hide_index=True, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลในฐานข้อมูล")
    except:
        st.info("รอข้อมูลจากการบันทึกครั้งแรกเพื่อสร้าง Dashboard")
