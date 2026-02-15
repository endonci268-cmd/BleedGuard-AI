import streamlit as st
import pandas as pd
import joblib
import altair as alt
from datetime import datetime

# --- 1. ตั้งค่าหน้าตาแอป (Mobile & Dark Mode Optimized) ---
st.set_page_config(page_title="BleedGuard-AI | NCI", page_icon="🩺", layout="centered")

# ระบบเก็บข้อมูลสำหรับ Dashboard
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])

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
    .red-xl { color: #b91c1c !important; font-weight: 900; font-size: 38px; text-align: center; margin-bottom: 10px; }
    .yellow-xl { color: #854d0e !important; font-weight: 900; font-size: 38px; text-align: center; margin-bottom: 10px; }
    .green-xl { color: #15803d !important; font-weight: 900; font-size: 38px; text-align: center; margin-bottom: 10px; }
    
    .advice-title { font-size: 22px; font-weight: bold; color: #004d99; margin-top: 15px; }
    .advice-content { font-size: 20px; color: #1e293b; line-height: 1.4; margin-bottom: 8px; }

    /* ปรับปุ่มให้ใหญ่และกดง่าย */
    .stButton>button {
        width: 100%;
        border-radius: 15px;
        height: 4.5em;
        background-color: #004d99;
        color: white;
        font-weight: bold;
        font-size: 24px;
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
        return {
            "title": "🔴 ความเสี่ยงสูง (High Risk)",
            "class": "red-xl",
            "follow_up": "📌 ติดตาม: โทรติดตามที่ 24, 48 และ 72 ชั่วโมง",
            "diet": "🥣 อาหาร: งดกากใย 3 วัน / Clear Liquid ใน 24 ชม. แรก",
            "activity": "🚶 กิจกรรม: งดออกกำลังหนัก/ยกของหนัก 7-14 วัน"
        }
    if row['Prob_Risk'] >= threshold:
        return {
            "title": "🟡 ความเสี่ยงปานกลาง (Moderate)",
            "class": "yellow-xl",
            "follow_up": "📌 ติดตาม: โทรติดตามในวันที่ 1, 3 และ 7",
            "diet": "🍚 อาหาร: อาหารอ่อนย่อยง่าย 2-3 วัน งดของเผ็ด/แอลกอฮอล์",
            "activity": "🚶 กิจกรรม: งดกิจกรรมที่เกร็งหน้าท้อง 5-7 วัน"
        }
    return {
        "title": "🟢 ความเสี่ยงต่ำ (Low Risk)",
        "class": "green-xl",
        "follow_up": "📌 ติดตาม: แนะนำการสังเกตอาการตนเองตามมาตรฐาน",
        "diet": "🍲 อาหาร: รับประทานได้ตามปกติ เลี่ยงอาหารท้องผูก",
        "activity": "🚶 กิจกรรม: ทำกิจวัตรได้ปกติ งดออกกำลังหนัก 1-2 วัน"
    }

# --- 4. ส่วนหัวแอป ---
st.markdown("<div class='title-nci'>ระบบอัจฉริยะคัดกรองความเสี่ยงภาวะเลือดออกหลังส่องกล้องลำไส้ใหญ่และตัดติ่งเนื้อ (BleedGuard-AI)</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle-nci'>ศูนย์ส่องกล้องทางเดินอาหาร สถาบันมะเร็งแห่งชาติ</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🩺 การคัดกรอง (Triage)", "📊 แดชบอร์ด (Dashboard)"])

with tab1:
    st.markdown(f"📅 **วันที่ปัจจุบัน:** {datetime.now().strftime('%d/%m/%Y')}")
    
    st.markdown("### 📝 ข้อมูลพื้นฐาน")
    age = st.number_input("อายุ (Age)", 0, 120, 60)
    size_cm = st.number_input("ขนาดติ่งเนื้อ (Size in cm)", 0.0, 10.0, 1.0, step=0.1)
    
    st.divider()
    st.markdown("### 💊 ปัจจัยเสี่ยงและประวัติการรักษา")
    med = st.checkbox("ยาละลายลิ่มเลือด/โรคประจำตัวร่วม")
    rad = st.checkbox("เคยฉายแสง (Radiation)")
    chemo = st.checkbox("เคยรับเคมีบำบัด (Chemo)")
    surg = st.checkbox("เคยผ่าตัดช่องท้อง (Surgery)")
    loc = st.checkbox("ตำแหน่งฝั่งขวา (Right Side)")
    clip = st.checkbox("แพทย์ติดคลิป/ความเสี่ยงหน้างาน")
    
    st.divider()
    st.markdown("### ✂️ ประเภทหัตถการ")
    bx = st.checkbox("BX (ตัดชิ้นเนื้อ)")
    cp = st.checkbox("Cold Polypectomy")
    hp = st.checkbox("Hot Polypectomy")
    emr = st.checkbox("EMR")

    if st.button("🚀 วิเคราะห์ผลการคัดกรอง"):
        # คำนวณ Prob_Risk สำหรับโมเดล
        p_feat = ((age/100*0.2) + (1 if med else 0)*0.3 + (1 if loc else 0)*0.1 + (1 if surg else 0)*0.1 + (1 if rad else 0)*0.05 + (1 if chemo else 0)*0.05 + (1 if hp else 0)*0.1)
        
        input_df = pd.DataFrame([{
            'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': 1 if loc else 0, 'Med_Risk ': 1 if med else 0,
            'Surgery ': 1 if surg else 0, 'Radiation': 1 if rad else 0, 'Chemo': 1 if chemo else 0, 'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cp else 0, 'Hot Polypectomy': 1 if hp else 0, 'EMR': 1 if emr else 0, 
            'Prob_Risk': p_feat, 'Sex': 1
        }])
        
        prob_ai = model.predict_proba(input_df)[0][1]
        row_final = input_df.iloc[0].copy()
        row_final['Prob_Risk'] = prob_ai
        row_final['Clinical_Risk_Outcome'] = 1 if clip else 0
        
        details = get_triage_details(row_final)
        
        # บันทึกลง Dashboard
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        new_data = pd.DataFrame([{'Date_Time': now, 'Risk_Score': prob_ai, 'Result': details['title']}])
        st.session_state.history = pd.concat([st.session_state.history, new_data], ignore_index=True)
        
        # แสดงผลลัพธ์ตัวใหญ่พิเศษ
        st.markdown(f"""
            <div class='result-card'>
                <div class='{details['class']}'>{details['title']}</div>
                <div class='advice-title'>📋 แผนการพยาบาล:</div>
                <div class='advice-content'>{details['follow_up']}</div>
                <div class='advice-content'>{details['diet']}</div>
                <div class='advice-content'>{details['activity']}</div>
                <hr>
                <p style='text-align:right; font-size:16px; color:#64748b;'>AI Risk Score: {prob_ai:.4f}</p>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.markdown(f"### 📊 แดชบอร์ดสรุปผลประจำวันที่ {datetime.now().strftime('%d/%m/%Y')}")
    
    if not st.session_state.history.empty:
        total = len(st.session_state.history)
        high = len(st.session_state.history[st.session_state.history['Result'].str.contains("🔴")])
        
        col1, col2 = st.columns(2)
        col1.metric("เคสทั้งหมด", f"{total} ราย")
        col2.metric("เสี่ยงสูง", f"{high} ราย", delta=f"{(high/total*100):.1f}%")
        
        st.divider()
        st.markdown("**📋 บันทึกรายการล่าสุด (Daily Logs)**")
        st.dataframe(st.session_state.history.sort_index(ascending=False), use_container_width=True)
        
        # กราฟวงกลม
        chart_data = st.session_state.history['Result'].value_counts().reset_index()
        chart = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
            theta='count', 
            color=alt.Color('Result', scale=alt.Scale(range=['#b91c1c', '#854d0e', '#15803d']))
        )
        st.altair_chart(chart, use_container_width=True)
        
        if st.button("🗑️ ล้างข้อมูล Dashboard"):
            st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลการคัดกรองสำหรับวันนี้")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute")
   
