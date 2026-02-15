import streamlit as st
import pandas as pd
import joblib
import altair as alt
from datetime import datetime

# --- 1. การตั้งค่าหน้าตาแอป (Mobile & Dark Mode Optimized) ---
st.set_page_config(page_title="BleedGuard-AI | NCI", page_icon="🩺", layout="centered")

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result', 'Hour'])

# ตกแต่ง CSS เน้นตัวหนังสือใหญ่พิเศษและสู้ Dark Mode
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 20px !important; }
    .main { background-color: #f1f5f9; }
    
    /* หัวข้อหลัก */
    .title-nci { color: #004d99; font-weight: 800; text-align: center; font-size: 26px; line-height: 1.2; }
    .subtitle-nci { color: #64748b; text-align: center; font-size: 18px; margin-bottom: 10px; }
    
    /* กล่องผลลัพธ์บังคับพื้นหลังขาว (High Contrast) */
    .result-card {
        padding: 25px;
        border-radius: 20px;
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 3px solid #004d99;
        margin-top: 20px;
    }
    
    /* ขนาดตัวอักษรระดับความเสี่ยง (ใหญ่พิเศษ) */
    .red-xl { color: #b91c1c !important; font-weight: 900; font-size: 38px; text-align: center; }
    .yellow-xl { color: #854d0e !important; font-weight: 900; font-size: 38px; text-align: center; }
    .green-xl { color: #15803d !important; font-weight: 900; font-size: 38px; text-align: center; }
    
    .stButton>button {
        width: 100%; border-radius: 15px; height: 4.5em; background-color: #004d99; color: white; font-weight: bold; font-size: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 3. ตรรกะการตัดสินใจและเนื้อหาแนะนำ ---
def get_triage_details(row, threshold=0.5):
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return {"title": "🔴 ความเสี่ยงสูง (High Risk)", "class": "red-xl", 
                "follow_up": "📌 ติดตาม: 24, 48, 72 ชม.", "diet": "🥣 อาหาร: Clear Liquid 24 ชม. แรก / งดกากใย 3 วัน", 
                "activity": "🚶 กิจกรรม: งดออกกำลัง/ยกของหนัก 7-14 วัน"}
    if row['Prob_Risk'] >= threshold:
        return {"title": "🟡 ความเสี่ยงปานกลาง (Moderate Risk)", "class": "yellow-xl", 
                "follow_up": "📌 ติดตาม: วันที่ 1, 3 และ 7", "diet": "🍚 อาหาร: อาหารอ่อนย่อยง่าย 2-3 วัน งดของเผ็ด/แอลกอฮอล์", 
                "activity": "🚶 กิจกรรม: งดกิจกรรมเกร็งหน้าท้อง 5-7 วัน"}
    return {"title": "🟢 ความเสี่ยงต่ำ (Low Risk)", "class": "green-xl", 
            "follow_up": "📌 ติดตาม: สังเกตอาการตนเองตามมาตรฐาน", "diet": "🍲 อาหาร: ทานปกติ เลี่ยงอาหารท้องผูก", 
            "activity": "🚶 กิจกรรม: ปกติ งดออกกำลังหนัก 1-2 วัน"}

# --- 4. ส่วนหัวแอป ---
st.markdown("<div class='title-nci'>BleedGuard-AI</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle-nci'>ระบบอัจฉริยะคัดกรองความเสี่ยงภาวะเลือดออกหลังส่องกล้องลำไส้ใหญ่และตัดติ่งเนื้อ<br>ศูนย์ส่องกล้องทางเดินอาหาร สถาบันมะเร็งแห่งชาติ</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🩺 คัดกรอง (Triage)", "📊 แดชบอร์ด (Dashboard)"])

with tab1:
    st.markdown("### 📝 ข้อมูลพื้นฐาน & ปัจจัยเสี่ยง")
    age = st.number_input("อายุ (Age)", 0, 120, 60)
    size_cm = st.number_input("ขนาดติ่งเนื้อ (Size in cm)", 0.0, 10.0, 1.0, step=0.1)
    
    col1, col2 = st.columns(2)
    med = col1.checkbox("ยาละลายลิ่มเลือด/โรคประจำตัว")
    rad = col2.checkbox("เคยฉายแสง (Radiation)")
    chemo = col1.checkbox("เคยรับเคมีบำบัด (Chemo)")
    surg = col2.checkbox("ประวัติผ่าตัดช่องท้อง")
    loc = col1.checkbox("ตำแหน่งฝั่งขวา (Right Side)")
    clip = col2.checkbox("แพทย์ติดคลิป/เสี่ยงหน้างาน")
    
    st.markdown("### ✂️ ประเภทหัตถการ")
    bx = st.checkbox("BX")
    cp = st.checkbox("Cold Poly")
    hp = st.checkbox("Hot Poly")
    emr = st.checkbox("EMR")

    if st.button("🚀 วิเคราะห์ผลการคัดกรอง"):
        p_feat = ((age/100*0.2) + (1 if med else 0)*0.3 + (1 if loc else 0)*0.1 + (1 if surg else 0)*0.1 + (1 if rad else 0)*0.05 + (1 if chemo else 0)*0.05 + (1 if hp else 0)*0.1)
        input_df = pd.DataFrame([{'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': 1 if loc else 0, 'Med_Risk ': 1 if med else 0, 'Surgery ': 1 if surg else 0, 'Radiation': 1 if rad else 0, 'Chemo': 1 if chemo else 0, 'BX': 1 if bx else 0, 'Cold Polypectomy': 1 if cp else 0, 'Hot Polypectomy': 1 if hp else 0, 'EMR': 1 if emr else 0, 'Prob_Risk': p_feat, 'Sex': 1}])
        
        prob_ai = model.predict_proba(input_df)[0][1]
        row_final = input_df.iloc[0].copy()
        row_final['Prob_Risk'] = prob_ai
        row_final['Clinical_Risk_Outcome'] = 1 if clip else 0
        
        details = get_triage_details(row_final)
        
        # บันทึกลง Dashboard
        now = datetime.now()
        new_entry = pd.DataFrame([{'Date_Time': now.strftime("%d/%m/%Y %H:%M"), 'Age': age, 'Size_cm': size_cm, 'Risk_Score': prob_ai, 'Result': details['title'], 'Hour': now.hour}])
        st.session_state.history = pd.concat([st.session_state.history, new_entry], ignore_index=True)
        
        st.markdown(f"""<div class='result-card'><div class='{details['class']}'>{details['title']}</div><hr><div style='font-size:20px; line-height:1.6;'><b>{details['follow_up']}</b><br>{details['diet']}<br>{details['activity']}</div></div>""", unsafe_allow_html=True)

with tab2:
    st.markdown(f"### 📊 แดชบอร์ดสรุปผล (Dashboard Summary)")
    st.markdown(f"📅 **ข้อมูลประจำวันที่:** {datetime.now().strftime('%d/%m/%Y')}")
    
    if not st.session_state.history.empty:
        # --- Metrics ---
        m1, m2, m3 = st.columns(3)
        m1.metric("เคสวันนี้", f"{len(st.session_state.history)} ราย")
        m2.metric("อายุเฉลี่ย", f"{st.session_state.history['Age'].mean():.1f} ปี")
        m3.metric("ขนาดเฉลี่ย", f"{st.session_state.history['Size_cm'].mean():.1f} cm")

        st.divider()
        
        # --- Pie Chart (ตรงสีกับ Triage) ---
        st.subheader("สัดส่วนระดับความเสี่ยง (Risk Proportion)")
        chart_data = st.session_state.history['Result'].value_counts().reset_index()
        pie = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
            theta='count', 
            color=alt.Color('Result', scale=alt.Scale(
                domain=['🔴 ความเสี่ยงสูง (High Risk)', '🟡 ความเสี่ยงปานกลาง (Moderate Risk)', '🟢 ความเสี่ยงต่ำ (Low Risk)'],
                range=['#b91c1c', '#854d0e', '#15803d']
            ))
        )
        st.altair_chart(pie, use_container_width=True)

        # --- Hourly Trend ---
        st.subheader("จำนวนเคสในแต่ละช่วงเวลา (Hourly Trend)")
        trend_data = st.session_state.history.groupby('Hour').
  

   
