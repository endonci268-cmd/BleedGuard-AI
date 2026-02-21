import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import pytz
from datetime import datetime

# --- CONFIG PAGE ---
st.set_page_config(page_title="BleedGuard AI - NCI", layout="wide", page_icon="🩺")
tz_th = pytz.timezone('Asia/Bangkok')

# --- 1. LOAD MODEL ---
@st.cache_resource
def load_trained_model():
    return joblib.load('bleedguard_stack_model.pkl')

try:
    model = load_trained_model()
except Exception as e:
    st.error(f"⚠️ โหลดโมเดลไม่ได้: {e}")
    model = None

# --- 2. GSHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame()

# --- 3. UI: TABS ---
tab1, tab2 = st.tabs(["🩺 ประเมินรายเคส", "📊 สรุปผลภาพรวม"])

with tab1:
    st.title("🎗️ BleedGuard AI Triage")
    st.info("ระบบสนับสนุนการตัดสินใจเพื่อเฝ้าระวังภาวะเลือดออกหลังส่องกล้อง สถาบันมะเร็งแห่งชาติ")

    with st.form("triage_form", clear_on_submit=True):
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

        submit = st.form_submit_button("🩺 ประมวลผลและบันทึกข้อมูล")

    if submit and model is not None:
        loc_right = 1 if loc_side == "Right Side" else 0
        features_list = [
            age_input, sex_input, size_input, loc_right, 
            int(emr_in), int(bx_in), int(cold_in), int(hot_in), 
            int(rad_in), int(chemo_in), int(surg_in), int(med_in)
        ]
        
        input_array = np.array(features_list).reshape(1, -1)
        
        try:
            prob = model.predict_proba(input_array)[0][1]
            
            # --- Logic การคัดแยก ---
            if size_input >= 2.0 or emr_in or rad_in:
                res, bg_color, advice, text_color = "🔴 High Risk", "#FF4B4B", "เฝ้าระวังเข้มงวด: โทรติดตามอาการวันที่ 1, 2 และ 3", "#FFFFFF"
            elif clip_in or prob > 0.12:
                res, bg_color, advice, text_color = "🟡 Moderate Risk", "#FFFF00", "เฝ้าระวังต่อเนื่อง: โทรติดตามอาการในวันที่ 2", "#000000"
            else:
                res, bg_color, advice, text_color = "🟢 Low Risk", "#28A745", "ไม่ต้องโทรติดตาม: ให้คำแนะนำการสังเกตอาการด้วยตนเอง", "#FFFFFF"

            # --- Gauge Chart แสดงค่า Probability ---
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = prob,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "AI Risk Score"},
                gauge = {
                    'axis': {'range': [0, 1]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, 0.12], 'color': "green"},
                        {'range': [0.12, 0.5], 'color': "yellow"},
                        {'range': [0.5, 1], 'color': "red"}]
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

            # --- ผลการประเมิน ---
            st.markdown(f"""
                <div style="background-color:{bg_color}; padding:30px; border-radius:15px; text-align:center; border: 2px solid #333;">
                    <h1 style="color:{text_color}; margin:0;">{res}</h1>
                    <p style="color:{text_color}; font-size:20px; font-weight:bold;">{advice}</p>
                </div>
            """, unsafe_allow_html=True)

            # --- บันทึกข้อมูล ---
            current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input, 
                "loc_right": loc_right, "Medication": int(med_in), "Surgery": int(surg_in), 
                "Radiation": int(rad_in), "Chemo": int(chemo_in), "BX": int(bx_in), 
                "Cold_Poly": int(cold_in), "Hot_Poly": int(hot_in), "EMR": int(emr_in), 
                "Clip": int(clip_in), "Risk_Level": res, "Advice": advice
            }])
            
            updated_df = pd.concat([get_data(), new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success(f"บันทึกข้อมูลเคส {case_id_input} ลงฐานข้อมูลแล้ว")
                
        except Exception as e:
            st.error(f"AI ประมวลผลผิดพลาด: {e}")

with tab2:
    st.header("📈 สถิติการคัดกรอง")
    df = get_data()
    if not df.empty:
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("เคสทั้งหมด", len(df))
        c2.metric("🔴 เสี่ยงสูง", len(df[df['Risk_Level'].str.contains("🔴")]))
        c3.metric("🟡 เสี่ยงปานกลาง", len(df[df['Risk_Level'].str.contains("🟡")]))
        c4.metric("🟢 ปกติ", len(df[df['Risk_Level'].str.contains("🟢")]))

        # กราฟ
        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = px.pie(df, names='Risk_Level', color='Risk_Level', hole=0.4,
                             color_discrete_map={"🔴 High Risk": "#FF4B4B", "🟡 Moderate Risk": "#FFFF00", "🟢 Low Risk": "#28A745"})
            st.plotly_chart(fig_pie)
        with col_b:
            st.subheader("5 เคสล่าสุด")
            st.table(df[['Case_ID', 'Risk_Level', 'Timestamp']].tail(5))
    else:
        st.info("ยังไม่มีข้อมูลเพื่อแสดงผล")
