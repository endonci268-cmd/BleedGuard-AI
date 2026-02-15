import streamlit as st
import pandas as pd
import joblib
import altair as alt
from datetime import datetime

# --- 1. ตั้งค่าหน้าตาแอป (Custom Theme) ---
st.set_page_config(page_title="BleedGuard AI Dashboard", page_icon="📊", layout="wide")

# ระบบเก็บข้อมูลชั่วคราวใน Session
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])

# ตกแต่งสไตล์
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 3. ตรรกะการตัดสินใจ (Hybrid Logic) ---
def bleedguard_triage_logic(row, threshold=0.5):
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 ความเสี่ยงต่ำ (Low Risk)", "แนะนำการดูแลตามมาตรฐานปกติ"
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 ความเสี่ยงสูง (High Risk)", "พยาบาลโทรติดตามภายใน 24 48 72 ชม. และเฝ้าระวังเข้มข้น"
    return ("🟡 ความเสี่ยงปานกลาง (Moderate Risk)", "พยาบาลโทรติดตามภายใน 1-3 วัน") if row['Prob_Risk'] >= threshold else ("🟢 ความเสี่ยงต่ำ (Low Risk)", "แนะนำการดูแลตามมาตรฐานปกติ")

# --- 4. ส่วน Tab เมนู ---
tab1, tab2 = st.tabs(["🩺 ระบบคัดกรอง (Triage System)", "📊 แดชบอร์ด (Dashboard)"])

with tab1:
    st.title("ระบบคัดกรองความเสี่ยง (Triage System)")
    st.write(f"📅 วันที่ปัจจุบัน (Current Date): {datetime.now().strftime('%d/%m/%Y')}")
    
    col_in, col_res = st.columns([1.5, 1])
    
    with col_in:
        with st.expander("📝 ข้อมูลผู้ป่วย (Patient Information)", expanded=True):
            age = st.number_input("อายุ (Age)", 0, 120, 60)
            sex = st.selectbox("เพศ (Sex)", ["ชาย (Male)", "หญิง (Female)"])
            size_cm = st.number_input("ขนาดติ่งเนื้อ (Size in cm)", 0.0, 10.0, 1.0)
            
        with st.expander("💊 ประวัติและความเสี่ยง (Risk Factors)", expanded=True):
            c1, c2 = st.columns(2)
            med = c1.checkbox("ยาละลายลิ่มเลือด/โรคประจำตัว (Medication/Comorbidity)")
            surg = c2.checkbox("ประวัติผ่าตัดช่องท้อง (Abdominal Surgery)")
            rad = c1.checkbox("เคยฉายแสง (Radiation)")
            chemo = c2.checkbox("เคยรับเคมีบำบัด (Chemo)")
            loc = c1.checkbox("ตำแหน่งฝั่งขวา (Right Side)")
            clip = c2.checkbox("แพทย์ติดคลิป/เสี่ยงหน้างาน (Clinical Risk)")
            
        with st.expander("✂️ ประเภทหัตถการ (Procedure Type)", expanded=True):
            bx = st.checkbox("BX")
            cp = st.checkbox("Cold Polypectomy")
            hp = st.checkbox("Hot Polypectomy")
            emr = st.checkbox("EMR")

    with col_res:
        st.subheader("🎯 ผลการวิเคราะห์ (Analysis Result)")
        if st.button("🚀 เริ่มการคัดกรอง (Start Triage)"):
            # คำนวณ Prob_Risk Feature เบื้องต้น
            p_feat = ((age/100*0.2) + (1 if med else 0)*0.3 + (1 if loc else 0)*0.1 + (1 if surg else 0)*0.1 + (1 if rad else 0)*0.05 + (1 if chemo else 0)*0.05 + (1 if hp else 0)*0.1)
            
            # เตรียม Data สำหรับ AI (13 features)
            input_df = pd.DataFrame([{
                'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': 1 if loc else 0, 'Med_Risk ': 1 if med else 0,
                'Surgery ': 1 if surg else 0, 'Radiation': 1 if rad else 0, 'Chemo': 1 if chemo else 0, 'BX': 1 if bx else 0,
                'Cold Polypectomy': 1 if cp else 0, 'Hot Polypectomy': 1 if hp else 0, 'EMR': 1 if emr else 0, 
                'Prob_Risk': p_feat, 'Sex': 1 if "ชาย" in sex else 0
            }])
            
            # AI Prediction จากโมเดลจริง
            prob_ai = model.predict_proba(input_df)[0][1]
            row_final = input_df.iloc[0].copy()
            row_final['Prob_Risk'] = prob_ai
            row_final['Clinical_Risk_Outcome'] = 1 if clip else 0
            
            res_text, advice = bleedguard_triage_logic(row_final)
            
            # บันทึกลง History (พร้อมวันที่และเวลา)
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            new_entry = pd.DataFrame([{
                'Date_Time': now, 'Age': age, 'Size_cm': size_cm, 'Risk_Score': round(prob_ai, 4), 'Result': res_text
            }])
            st.session_state.history = pd.concat([st.session_state.history, new_entry], ignore_index=True)
            
            # แสดงผลสี
            if "🔴" in res_text: st.error(f"### {res_text}")
            elif "🟡" in res_text: st.warning(f"### {res_text}")
            else: st.success(f"### {res_text}")
            st.info(f"💡 **คำแนะนำ (Advice):** {advice}")
            st.metric("คะแนนความเสี่ยง (AI Risk Score)", f"{prob_ai:.4f}")

with tab2:
    st.title("📊 แดชบอร์ดสรุปผล (Dashboard Summary)")
    st.write(f"📅 ข้อมูลประจำวันที่ (Data as of): {datetime.now().strftime('%d/%m/%Y')}")
    
    if not st.session_state.history.empty:
        # สรุปตัวเลขสำคัญ
        m1, m2, m3 = st.columns(3)
        total_cases = len(st.session_state.history)
        high_risk_cases = len(st.session_state.history[st.session_state.history['Result'].str.contains("🔴")])
        
        m1.metric("จำนวนเคสทั้งหมด (Total Cases)", f"{total_cases} ราย")
        m2.metric("กลุ่มเสี่ยงสูง (High Risk Cases)", f"{high_risk_cases} ราย", 
                  delta=f"{(high_risk_cases/total_cases*100):.1f}% ของทั้งหมด", delta_color="inverse")
        m3.metric("คะแนนความเสี่ยงเฉลี่ย (Mean Risk Score)", f"{st.session_state.history['Risk_Score'].mean():.4f}")
        
        st.divider()
        
        # กราฟสรุป
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📊 สัดส่วนระดับความเสี่ยง (Risk Distribution)")
            chart_data = st.session_state.history['Result'].value_counts().reset_index()
            chart = alt.Chart(chart_data).mark_arc(innerRadius=60).encode(
                theta='count', 
                color=alt.Color('Result', scale=alt.Scale(
                    domain=['🔴 ความเสี่ยงสูง (High Risk)', '🟡 ความเสี่ยงปานกลาง (Moderate Risk)', '🟢 ความเสี่ยงต่ำ (Low Risk)'], 
                    range=['#ff4b4b', '#ffa500', '#28a745']))
            )
            st.altair_chart(chart, use_container_width=True)
            
        with g2:
            st.subheader("📈 แนวโน้มคะแนนความเสี่ยง (Risk Score Trend)")
            st.line_chart(st.session_state.history.set_index('Date_Time')['Risk_Score'])
            
        st.subheader("📋 ประวัติการคัดกรองรายวัน (Daily Screening Logs)")
        st.dataframe(st.session_state.history.sort_index(ascending=False), use_container_width=True)
        
        # ปุ่มล้างข้อมูล
        if st.button("🗑️ ล้างข้อมูล Dashboard (Clear All Data)"):
            st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลในระบบ กรุณาทำการคัดกรองในหน้า Triage ก่อนครับ")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute (NCI) Thailand")
