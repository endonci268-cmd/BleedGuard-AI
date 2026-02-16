import streamlit as st
import pandas as pd
import joblib
import numpy as np
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(layout="wide", page_title="NCI BleedGuard-AI", page_icon="🩺")

# --- 2. เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดโมเดล AI ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
    # ลำดับฟีเจอร์ตามไฟล์ CSV (สำคัญมากเพื่อให้ Score ตรง)
    model_features = [
        'Age', 'Size_cm ', 'Loc_Right ', 'Med_Risk ', 'Surgery ', 
        'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 
        'EMR', 'Prob_Risk', 'Sex'
    ]
except Exception as e:
    st.error(f"❌ โหลดโมเดลไม่สำเร็จ: {e}")

# --- 4. ฟังก์ชัน Triage Logic (BX Condition กลับมาแล้ว!) ---
def bleedguard_triage_logic(row, prob, threshold=0.05):
    # กฎ 1: เคสความเสี่ยงต่ำพิเศษ (De-escalation) - ติ่งเนื้อเล็ก + BX + ไม่ใช่ Cold Poly
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk (Standard Care)", "#D2FFD2", "😊"
    
    # กฎ 2: เคสความเสี่ยงสูง (Safety First) - ขนาดใหญ่ หรือ EMR หรือ AI Score สูง
    if prob >= 0.5 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk (Intensive Follow-up)", "#FFD2D2", "😫"
    
    # กฎ 3: เคสความเสี่ยงปานกลาง - AI Score เกินจุดตัด
    if prob >= threshold:
        return "🟡 Moderate Risk (Post-op Call)", "#FFF9C4", "😟"
    
    # อื่นๆ เป็นความเสี่ยงต่ำ
    return "🟢 Low Risk", "#D2FFD2", "😊"

# --- 5. ฟังก์ชันเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 6. ส่วนหัว Dashboard ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI (Endo-STAT)</h2>
        <p style='font-size: 1.1rem; color: #555;'>ระบบบริหารจัดการความเสี่ยงศูนย์ส่องกล้อง สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 7. แสดง Dashboard ทันทีที่เปิดหน้าจอ ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Triage_Result']).copy()
        
        if not df_clean.empty:
            st.subheader("📊 สรุปผลการดำเนินงาน")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("เคสสะสม", f"{len(df_clean)} ราย")
            m2.metric("🔴 High", len(df_clean[df_clean['Triage_Result'].str.contains('High')]))
            m3.metric("🟡 Moderate", len(df_clean[df_clean['Triage_Result'].str.contains('Moderate')]))
            m4.metric("🟢 Low", len(df_clean[df_clean['Triage_Result'].str.contains('Low')]))

            g1, g2 = st.columns(2)
            with g1:
                fig_pie = px.pie(df_clean, names='Triage_Result', hole=0.4, title="สัดส่วนความเสี่ยง")
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                fig_bar = px.histogram(df_clean, x='Triage_Result', color='Triage_Result', title="จำนวนเคสแยกตามกลุ่ม")
                st.plotly_chart(fig_bar, use_container_width=True)
except:
    df_existing = pd.DataFrame()

st.divider()

# --- 8. ฟอร์มกรอกข้อมูล ---
st.subheader("📝 บันทึกและประเมินความเสี่ยงรายใหม่")
with st.expander("เปิดเพื่อกรอกข้อมูล", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex = st.selectbox("เพศ", [1, 0], format_func=lambda x: "ชาย" if x == 1 else "หญิง")
        size_cm = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.2)
        loc_right = st.selectbox("ตำแหน่ง (ขวา=1, ซ้าย=0)", [1, 0])
        med_risk = st.selectbox("ยากลุ่มเสี่ยง (มี=1)", [1, 0])
    with col2:
        surgery = st.selectbox("ประวัติผ่าตัด (มี=1)", [1, 0])
        rad = st.selectbox("ประวัติฉายแสง (มี=1)", [1, 0])
        chemo = st.selectbox("ประวัติเคมีบำบัด (มี=1)", [1, 0])
        bx = st.selectbox("Biopsy (BX=1)", [1, 0])
        cold_p = st.selectbox("Cold Polypectomy (มี=1)", [1, 0])
        hot_p = st.selectbox("Hot Polypectomy (มี=1)", [1, 0])
        emr = st.selectbox("EMR (มี=1)", [1, 0])

# --- 9. การประมวลผล ---
if st.button("📊 ทำการคัดกรอง", use_container_width=True):
    # เตรียมข้อมูลให้ตรงตามโครงสร้าง CSV
    clinical_risk_outcome = 1 if (size_cm >= 2.0 or emr == 1) else 0
    
    input_data = {
        'Age': float(age), 'Size_cm ': float(size_cm), 'Loc_Right ': float(loc_right), 'Med_Risk ': float(med_risk),
        'Surgery ': float(surgery), 'Radiation': float(rad), 'Chemo': float(chemo), 'BX': float(bx),
        'Cold Polypectomy': float(cold_p), 'Hot Polypectomy': float(hot_p), 'EMR': float(emr),
        'Prob_Risk': float(clinical_risk_outcome), # ส่งค่าเบื้องต้นให้โมเดล
        'Sex': float(sex)
    }
    
    input_df = pd.DataFrame([input_data])[model_features]

    try:
        # AI ทำนายผล
        actual_prob = model.predict_proba(input_df)[0][1]
        
        # ส่งค่าให้ Logic ทำงาน (ดึง BX กลับมาใช้ตรงนี้)
        res, b_col, ico = bleedguard_triage_logic(input_data, actual_prob)

        # แสดงผลลัพธ์
        st.markdown(f"""
            <div style="background-color: {b_col}; padding: 30px; border-radius: 15px; text-align: center; border: 2px solid #ccc; margin-top: 20px;">
                <h1 style="font-size: 80px; margin: 0;">{ico}</h1>
                <h2 style="margin: 10px 0;">{res}</h2>
                <p>AI Score: <b>{actual_prob:.4f}</b></p>
            </div>
        """, unsafe_allow_html=True)

        # บันทึกข้อมูล (13 AI columns + 3 Info columns)
        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")
        input_data['Prob_Risk'] = actual_prob
        input_data['Timestamp'] = timestamp
        input_data['Triage_Result'] = res
        input_data['AI_Score'] = round(float(actual_prob), 4)
        
        updated_df = pd.concat([df_existing, pd.DataFrame([input_data])], ignore_index=True)
        conn.update(data=updated_df)
        st.success("✅ บันทึกข้อมูลและอัปเดต Dashboard แล้ว")
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
