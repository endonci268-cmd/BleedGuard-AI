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
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI (Endo-STAT)</h2>
        <p style='font-size: 1.1rem; color: #555;'>ระบบบริหารจัดการความเสี่ยงศูนย์ส่องกล้อง สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. แดชบอร์ด (Dashboard) ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        # กรองเอาเฉพาะแถวที่มีการประเมินแล้ว
        df_clean = df_existing.dropna(subset=['Triage_Result']).copy()
        
        if not df_clean.empty:
            st.subheader("📊 สถิติภาพรวมการคัดกรอง")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("เคสสะสม", f"{len(df_clean)} ราย")
            m2.metric("🔴 High", len(df_clean[df_clean['Triage_Result'].str.contains('High', na=False)]))
            m3.metric("🟡 Moderate", len(df_clean[df_clean['Triage_Result'].str.contains('Moderate', na=False)]))
            m4.metric("🟢 Low", len(df_clean[df_clean['Triage_Result'].str.contains('Low', na=False)]))

            g1, g2 = st.columns(2)
            with g1:
                fig_pie = px.pie(df_clean, names='Triage_Result', 
                                 color='Triage_Result',
                                 color_discrete_map={
                                     '🔴 High Risk (Intensive Follow-up)': '#FF4B4B',
                                     '🟡 Moderate Risk': '#FBC02D',
                                     '🟢 Low Risk': '#00CC96'
                                 },
                                 hole=0.4, title="สัดส่วนความเสี่ยงผู้ป่วย")
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                # กราฟแสดงแนวโน้มตามวัน (ถ้ามีคอลัมน์ Timestamp)
                df_clean['Date'] = pd.to_datetime(df_clean['Timestamp']).dt.date
                fig_trend = px.line(df_clean.groupby('Date').size().reset_index(name='Counts'), 
                                    x='Date', y='Counts', title="จำนวนการคัดกรองรายวัน")
                st.plotly_chart(fig_trend, use_container_width=True)
except Exception as e:
    st.warning(f"ยังไม่มีข้อมูลในระบบ หรือหัวคอลัมน์ไม่ถูกต้อง: {e}")
    df_existing = pd.DataFrame()

st.divider()

# --- 7. ส่วนฟอร์มบันทึกข้อมูล ---
st.subheader("📝 บันทึกข้อมูลและคัดกรองรายใหม่")
with st.expander("เปิดเพื่อกรอกข้อมูลรายละเอียด", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex = st.selectbox("เพศ", [1, 0], format_func=lambda x: "ชาย" if x == 1 else "หญิง")
        size_cm = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.2)
        loc_right = st.selectbox("ตำแหน่ง (ขวา=1, ซ้าย=0)", [1, 0])
        med_risk = st.selectbox("ยากลุ่มเสี่ยง (มี=1)", [1, 0])
    with col2:
        surgery = st.selectbox("ประวัติผ่าตัด (มี=1)", [1, 0])
        radiation = st.selectbox("ประวัติฉายแสง (มี=1)", [1, 0])
        chemo = st.selectbox("ประวัติเคมีบำบัด (มี=1)", [1, 0])
        bx = st.selectbox("Biopsy (มี=1)", [1, 0])
        cold_p = st.selectbox("Cold Polypectomy (มี=1)", [1, 0])
        hot_p = st.selectbox("Hot Polypectomy (มี=1)", [1, 0])
        emr = st.selectbox("EMR (มี=1)", [1, 0])

# --- 8. การประมวลผลและบันทึกข้อมูล ---
if st.button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True):
    # เตรียมข้อมูล 13 คอลัมน์ตามชื่อเป๊ะๆ ที่ AI จำได้ (รวมช่องว่างท้ายชื่อ)
    input_data = {
        'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': loc_right, 'Med_Risk ': med_risk,
        'Surgery ': surgery, 'Radiation': radiation, 'Chemo': chemo, 'BX': bx,
        'Cold Polypectomy': cold_p, 'Hot Polypectomy': hot_p, 'EMR': emr,
        'Prob_Risk': 0.0, 'Sex': sex
    }
    
    input_df = pd.DataFrame([input_data])
    
    # บังคับเรียงคอลัมน์ตามสมอง AI
    column_order = [
        'Age', 'Size_cm ', 'Loc_Right ', 'Med_Risk ', 'Surgery ', 
        'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 
        'EMR', 'Prob_Risk', 'Sex'
    ]
    input_df = input_df[column_order]

    try:
        # AI คำนวณความเสี่ยง
        actual_prob = model.predict_proba(input_df)[0][1]
        
        # --- Logic การตัดสินใจ (Triage Logic) ---
        if size_cm >= 2.0 or emr == 1:
            triage_res, b_color, icon = "🔴 High Risk (Intensive Follow-up)", "#FFD2D2", "😫"
        elif actual_prob >= 0.05: # จุดตัดสีเหลือง
            triage_res, b_color, icon = "🟡 Moderate Risk", "#FFF9C4", "😟"
        else:
            triage_res, b_color, icon = "🟢 Low Risk", "#D2FFD2", "😊"

        # แสดงผลลัพธ์
        st.markdown(f"""
            <div style="background-color: {b_color}; padding: 30px; border-radius: 15px; text-align: center; border: 2px solid #ccc; margin-top: 20px;">
                <h1 style="font-size: 80px; margin: 0;">{icon}</h1>
                <h2 style="margin: 10px 0;">{triage_res}</h2>
                <p>AI Score: <b>{actual_prob:.4f}</b></p>
            </div>
        """, unsafe_allow_html=True)

        # เตรียมแถวข้อมูลเพื่อบันทึก (13 AI columns + 3 New columns)
        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")
        input_data['Timestamp'] = timestamp
        input_data['Triage_Result'] = triage_res
        input_data['AI_Score'] = round(float(actual_prob), 4)
        
        # บันทึกลง Sheets
        new_row_df = pd.DataFrame([input_data])
        updated_df = pd.concat([df_existing, new_row_df], ignore_index=True)
        conn.update(data=updated_df)
        st.success("✅ บันทึกข้อมูลและอัปเดต Dashboard เรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
