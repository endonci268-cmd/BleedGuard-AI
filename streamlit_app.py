import streamlit as st
import pandas as pd
import joblib
import altair as alt # สำหรับทำกราฟสวยๆ

# --- 1. ตั้งค่าหน้าตาแอป ---
st.set_page_config(page_title="BleedGuard-AI Dashboard", page_icon="📊", layout="wide")

# ระบบเก็บข้อมูลชั่วคราวใน Session
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Time', 'Age', 'Size', 'Risk_Score', 'Result'])

# ตกแต่ง CSS
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 3. ฟังก์ชันตัดสินใจ (Hybrid Logic) ---
def bleedguard_triage_logic(row, threshold=0.5):
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk", "สังเกตอาการตามมาตรฐาน"
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk", "โทรติดตามภายใน 24 ชม."
    return ("🟡 Moderate Risk", "โทรติดตามภายใน 1-3 วัน") if row['Prob_Risk'] >= threshold else ("🟢 Low Risk", "สังเกตอาการปกติ")

# --- 4. การแบ่ง Tab (Triage vs Dashboard) ---
tab1, tab2 = st.tabs(["🩺 ระบบคัดกรอง (Triage)", "📊 แดชบอร์ดสรุปผล (Dashboard)"])

with tab1:
    st.title("ระบบคัดกรองรายบุคคล")
    col_in, col_res = st.columns([1.5, 1])
    
    with col_in:
        with st.expander("📝 ข้อมูลผู้ป่วย", expanded=True):
            age = st.number_input("อายุ", 0, 120, 60)
            sex = st.selectbox("เพศ", ["ชาย", "หญิง"])
            size_cm = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.0, 10.0, 1.0)
            
        with st.expander("💊 ประวัติและความเสี่ยง", expanded=True):
            c1, c2 = st.columns(2)
            med = c1.checkbox("ยาละลายลิ่มเลือด/โรคประจำตัว")
            surg = c2.checkbox("ประวัติผ่าตัดช่องท้อง")
            rad = c1.checkbox("เคยฉายแสง (RT)")
            chemo = c2.checkbox("เคยรับเคมีบำบัด")
            loc = c1.checkbox("ตำแหน่งฝั่งขวา")
            clip = c2.checkbox("แพทย์ติดคลิป/เสี่ยงหน้างาน")
            
        with st.expander("✂️ หัตถการ", expanded=True):
            bx = st.checkbox("BX")
            cp = st.checkbox("Cold Poly")
            hp = st.checkbox("Hot Poly")
            emr = st.checkbox("EMR")

    with col_res:
        st.subheader("🎯 ผลการวิเคราะห์")
        if st.button("เริ่มการคัดกรอง"):
            # คำนวณ Prob_Risk Feature
            p_feat = ((age/100*0.2) + (1 if med else 0)*0.3 + (1 if loc else 0)*0.1 + (1 if surg else 0)*0.1 + (1 if rad else 0)*0.05 + (1 if chemo else 0)*0.05 + (1 if hp else 0)*0.1)
            
            # เตรียม Data สำหรับ AI (13 features เรียงตามลำดับ)
            input_df = pd.DataFrame([{
                'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': 1 if loc else 0, 'Med_Risk ': 1 if med else 0,
                'Surgery ': 1 if surg else 0, 'Radiation': 1 if rad else 0, 'Chemo': 1 if chemo else 0, 'BX': 1 if bx else 0,
                'Cold Polypectomy': 1 if cp else 0, 'Hot Polypectomy': 1 if hp else 0, 'EMR': 1 if emr else 0, 
                'Prob_Risk': p_feat, 'Sex': 1 if sex == "ชาย" else 0
            }])
            
            # AI Prediction
            prob_ai = model.predict_proba(input_df)[0][1]
            row_final = input_df.iloc[0].copy()
            row_final['Prob_Risk'] = prob_ai
            row_final['Clinical_Risk_Outcome'] = 1 if clip else 0
            
            res_text, advice = bleedguard_triage_logic(row_final)
            
            # บันทึกลง History
            new_data = pd.DataFrame([{
                'Time': pd.Timestamp.now().strftime("%H:%M:%S"),
                'Age': age, 'Size': size_cm, 'Risk_Score': round(prob_ai, 4), 'Result': res_text
            }])
            st.session_state.history = pd.concat([st.session_state.history, new_data], ignore_index=True)
            
            # แสดงผล
            if "🔴" in res_text: st.error(f"### {res_text}")
            elif "🟡" in res_text: st.warning(f"### {res_text}")
            else: st.success(f"### {res_text}")
            st.info(f"💡 {advice}")
            st.metric("AI Risk Score", f"{prob_ai:.4f}")

with tab2:
    st.title("ภาพรวมการคัดกรองในรอบวันนี้")
    
    if not st.session_state.history.empty:
        # ส่วนตัวเลข Metric
        m1, m2, m3 = st.columns(3)
        total = len(st.session_state.history)
        high_risk_count = len(st.session_state.history[st.session_state.history['Result'].str.contains("🔴")])
        
        m1.metric("จำนวนคนไข้ทั้งหมด", f"{total} ราย")
        m2.metric("พบกลุ่มเสี่ยงสูง", f"{high_risk_count} ราย", delta=f"{high_risk_count/total*100:.1f}%", delta_color="inverse")
        m3.metric("คะแนนเฉลี่ย", f"{st.session_state.history['Risk_Score'].mean():.4f}")
        
        st.divider()
        
        # ส่วนกราฟ
        g1, g2 = st.columns(2)
        
        with g1:
            st.subheader("สัดส่วนระดับความเสี่ยง")
            chart_data = st.session_state.history['Result'].value_counts().reset_index()
            chart = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
                theta='count', color=alt.Color('Result', scale=alt.Scale(domain=['🔴 High Risk', '🟡 Moderate Risk', '🟢 Low Risk'], range=['#ff4b4b', '#ffa500', '#28a745']))
            )
            st.altair_chart(chart, use_container_width=True)
            
        with g2:
            st.subheader("การกระจายของคะแนน Risk Score")
            st.bar_chart(st.session_state.history['Risk_Score'])
            
        st.subheader("📋 รายการคนไข้ล่าสุด")
        st.dataframe(st.session_state.history.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลการคัดกรองในรอบนี้ กรุณากรอกข้อมูลในหน้าคัดกรองก่อนครับ")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute")
