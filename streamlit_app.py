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

# --- 3. โหลดสมอง AI (ไฟล์ต้องชื่อ bleedguard_model.pkl) ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except Exception as e:
    st.error(f"❌ โหลดโมเดลไม่สำเร็จ: {e}")

# --- 4. Logic การคัดกรอง (อิงตามต้นฉบับ + จุดตัดเพื่อความปลอดภัย) ---
def bleedguard_triage_logic(row, prob, threshold=0.05):
    # 1. กฎความเสี่ยงต่ำพิเศษ (De-escalation)
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk (Standard Care)", "#D2FFD2", "😊"
    
    # 2. กฎความเสี่ยงสูง (Safety First)
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk (Intensive Follow-up)", "#FFD2D2", "😫"
    
    # 3. ใช้ AI ตัดสิน (ถ้าคะแนนถึงเกณฑ์ที่ตั้งไว้)
    if prob >= threshold:
        return "🟡 Moderate Risk (Post-op Call)", "#FFF9C4", "😟"
    else:
        return "🟢 Low Risk", "#D2FFD2", "😊"

# --- 5. ฟังก์ชันดึงเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 6. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI (Endo-STAT)</h2>
        <p style='font-size: 1.1rem; color: #555;'>ระบบบริหารจัดการความเสี่ยงศูนย์ส่องกล้อง สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 7. แดชบอร์ด (Dashboard) ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Triage_Result']).copy()
        st.subheader("📊 สถิติภาพรวมศูนย์ส่องกล้อง")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสสะสมทั้งหมด", f"{len(df_clean)} ราย")
        m2.metric("🔴 High Risk", len(df_clean[df_clean['Triage_Result'].str.contains('High', na=False)]))
        m3.metric("🟡 Moderate Risk", len(df_clean[df_clean['Triage_Result'].str.contains('Moderate', na=False)]))
        m4.metric("🟢 Low Risk", len(df_clean[df_clean['Triage_Result'].str.contains('Low', na=False)]))

        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df_clean, names='Triage_Result', color='Triage_Result',
                             color_discrete_map={'🔴 High Risk (Intensive Follow-up)':'#FF4B4B', '🟡 Moderate Risk (Post-op Call)':'#FBC02D', '🟢 Low Risk':'#00CC96', '🟢 Low Risk (Standard Care)':'#00CC96'},
                             hole=0.4, title="สัดส่วนความเสี่ยง")
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            fig_bar = px.bar(df_clean, x='Method', color='Triage_Result', title="จำนวนหัตถการตามกลุ่มความเสี่ยง")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        df_existing = pd.DataFrame()
except:
    df_existing = pd.DataFrame()

st.divider()

# --- 8. ส่วนบันทึกข้อมูล (Input Features) ---
st.subheader("📝 บันทึกข้อมูลและประมวลผลรายใหม่")
with st.expander("เปิดเพื่อกรอกข้อมูลรายละเอียด", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex = st.selectbox("เพศ", [1, 0], format_func=lambda x: "ชาย" if x == 1 else "หญิง")
        size_cm = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.2)
        loc_right = st.selectbox("ตำแหน่ง (ขวา=1, ซ้าย=0)", [1, 0])
        med_risk = st.selectbox("ยากลุ่มเสี่ยง (มี=1, ไม่มี=0)", [1, 0])
    with col2:
        surgery = st.selectbox("ประวัติผ่าตัด (มี=1)", [1, 0])
        radiation = st.selectbox("ประวัติฉายแสง (มี=1)", [1, 0])
        chemo = st.selectbox("ประวัติเคมีบำบัด (มี=1)", [1, 0])
        bx = st.selectbox("Biopsy (มี=1)", [1, 0])
        cold_p = st.selectbox("Cold Polypectomy (มี=1)", [1, 0])
        hot_p = st.selectbox("Hot Polypectomy (มี=1)", [1, 0])
        emr = st.selectbox("EMR (มี=1)", [1, 0])

# --- 9. การประมวลผล ---
if st.button("📊 ทำการคัดกรองความเสี่ยง", use_container_width=True):
    # เตรียมข้อมูล 13 คอลัมน์ตามโครงสร้างเดิม (รวม Prob_Risk หลอกๆ เพื่อให้รันผ่าน)
    input_data = {
        'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': loc_right, 'Med_Risk ': med_risk,
        'Surgery ': surgery, 'Radiation': radiation, 'Chemo': chemo, 'BX': bx,
        'Cold Polypectomy': cold_p, 'Hot Polypectomy': hot_p, 'EMR': emr,
        'Prob_Risk': 0.0, 'Sex': sex
    }
    
    input_df = pd.DataFrame([input_data])
    
    # เรียงลำดับให้ตรงกับที่ Fit โมเดลมา
    column_order = [
        'Age', 'Size_cm ', 'Loc_Right ', 'Med_Risk ', 'Surgery ', 
        'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 
        'EMR', 'Prob_Risk', 'Sex'
    ]
    input_df = input_df[column_order]

    try:
        # ทำนายผล
        actual_prob = model.predict_proba(input_df)[0][1]
        
        # ใส่ค่ากลับเพื่อใช้ใน Logic (Clinical_Risk_Outcome)
        clinical_risk_outcome = 1 if (size_cm >= 2.0 or emr == 1) else 0
        input_df['Clinical_Risk_Outcome'] = clinical_risk_outcome
        
        # ตัดสินใจผลลัพธ์
        triage_res, b_color, icon = bleedguard_triage_logic(input_df.iloc[0], actual_prob)
        
        # แสดงผล Visual
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_color}; padding: 30px; border-radius: 15px; text-align: center; border: 2px solid #ccc;">
                <h1 style="font-size: 80px; margin: 0;">{icon}</h1>
                <h2 style="margin: 10px 0; color: #333;">{triage_res}</h2>
                <p style="font-size: 1.2rem;">AI Probability Score: <b>{actual_prob:.4f}</b></p>
            </div>
        """, unsafe_allow_html=True)

        # บันทึกข้อมูล
        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")
        method_str = "EMR" if emr else ("Hot Poly" if hot_p else ("Cold Poly" if cold_p else "BX"))
        new_row = pd.DataFrame([{
            "Timestamp": timestamp, "Triage_Result": triage_res, 
            "AI_Score": round(float(actual_prob), 4), "Method": method_str
        }])
        
        df_all = pd.concat([df_existing, new_row], ignore_index=True)
        conn.update(data=df_all)
        st.success("💡 บันทึกข้อมูลและอัปเดตสถิติ Dashboard เรียบร้อยแล้ว")
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
