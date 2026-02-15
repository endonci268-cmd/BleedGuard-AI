import streamlit as st
import pandas as pd
import joblib
import altair as alt
from datetime import datetime

# --- 1. ตั้งค่าหน้าตาแอป (Mobile & Dark Mode Optimized) ---
st.set_page_config(page_title="BleedGuard-AI | NCI", page_icon="🩺", layout="centered")

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])

# ตกแต่ง CSS เพื่อให้อ่านง่ายในทุกสภาวะแสง
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 18px !important; }
    .main { background-color: #ffffff; }
    
    /* กล่องผลลัพธ์บังคับพื้นหลังขาวเพื่อสู้กับ Dark Mode */
    .result-card {
        padding: 20px;
        border-radius: 15px;
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #e2e8f0;
        box-shadow: 0px 10px 15px -3px rgba(0,0,0,0.1);
        margin-top: 20px;
    }
    
    /* หัวข้อภาษาไทย-อังกฤษ */
    .title-nci { color: #004d99; font-weight: 800; text-align: center; font-size: 24px; line-height: 1.2; }
    .subtitle-nci { color: #64748b; text-align: center; font-size: 16px; margin-bottom: 20px; }
    
    /* สีข้อความระดับความเสี่ยง */
    .red-bold { color: #b91c1c !important; font-weight: 800; font-size: 26px; }
    .yellow-bold { color: #854d0e !important; font-weight: 800; font-size: 26px; }
    .green-bold { color: #15803d !important; font-weight: 800; font-size: 26px; }
    
    /* สไตล์ปุ่มกด */
    .stButton>button {
        width: 100%;
        border-radius: 15px;
        height: 4em;
        background-color: #004d99;
        color: white;
        font-weight: bold;
        font-size: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 3. ตรรกะการตัดสินใจและเนื้อหาแนะนำ (Refined Content) ---
def get_triage_details(row, threshold=0.5):
    # เลเยอร์ 1: ความเสี่ยงวิกฤต (High Risk)
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return {
            "title": "🔴 ความเสี่ยงสูง (High Risk)",
            "class": "red-bold",
            "follow_up": "📌 การติดตาม: โทรติดตามอาการที่ 24, 48 และ 72 ชั่วโมง",
            "diet": "🥣 อาหาร: งดอาหารกากใยสูง 3 วัน ให้เริ่มด้วยอาหารเหลวใส (Clear Liquid) ใน 24 ชม. แรก",
            "activity": "🚶 กิจกรรม: งดออกกำลังกายหนัก/ยกของหนัก 7-14 วัน, งดเดินทางไกล"
        }
    
    # เลเยอร์ 2: ความเสี่ยงปานกลาง (Moderate Risk)
    if row['Prob_Risk'] >= threshold:
        return {
            "title": "🟡 ความเสี่ยงปานกลาง (Moderate Risk)",
            "class": "yellow-bold",
            "follow_up": "📌 การติดตาม: โทรติดตามอาการในวันที่ 1, 3 และ 7",
            "diet": "🍚 อาหาร: อาหารอ่อนย่อยง่าย (Soft Diet) ใน 2-3 วันแรก งดแอลกอฮอล์และของเผ็ดจัด",
            "activity": "🚶 กิจกรรม: งดกิจกรรมที่ต้องออกแรงเกร็งหน้าท้อง 5-7 วัน"
        }
    
    # เลเยอร์ 3: ความเสี่ยงต่ำ (Low Risk)
    return {
        "title": "🟢 ความเสี่ยงต่ำ (Low Risk)",
        "class": "green-bold",
        "follow_up": "📌 การติดตาม: แนะนำการสังเกตอาการตนเองตามมาตรฐาน (Standard Care)",
        "diet": "🍲 อาหาร: รับประทานอาหารได้ตามปกติ (Regular Diet) หลีกเลี่ยงอาหารที่ทำให้ท้องผูก",
        "activity": "🚶 กิจกรรม: ทำกิจวัตรประจำวันได้ตามปกติ งดออกกำลังกายหนักเพียง 1-2 วัน"
    }

# --- 4. ส่วนหน้าจอหลัก ---
st.markdown("<div class='title-nci'>ระบบอัจฉริยะคัดกรองความเสี่ยงภาวะเลือดออกหลังส่องกล้องลำไส้ใหญ่และตัดติ่งเนื้อ (BleedGuard-AI)</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle-nci'>ศูนย์ส่องกล้องทางเดินอาหาร สถาบันมะเร็งแห่งชาติ</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🩺 คัดกรอง (Triage)", "📊 แดชบอร์ด (Dashboard)"])

with tab1:
    st.markdown("#### 📋 กรอกข้อมูลข้อมูลหัตถการ")
    age = st.number_input("อายุ (Age)", 0, 120, 60)
    size_cm = st.number_input("ขนาดติ่งเนื้อ (Size in cm)", 0.0, 10.0, 1.0, step=0.1)
    
    st.markdown("#### ⚠️ ปัจจัยความเสี่ยง")
    c1, c2 = st.columns(2)
    med = c1.checkbox("ยาละลายลิ่มเลือด/โรคประจำตัว")
    rad = c2.checkbox("เคยฉายแสง (Radiation)")
    chemo = c1.checkbox("เคยรับเคมีบำบัด (Chemo)")
    surg = c2.checkbox("เคยผ่าตัดช่องท้อง")
    loc = c1.checkbox("ตำแหน่งฝั่งขวา (Right)")
    clip = c2.checkbox("แพทย์ติดคลิป/เสี่ยงหน้างาน")
    
    st.markdown("#### ✂️ หัตถการที่ทำ")
    bx = st.checkbox("BX (ชิ้นเนื้อ)")
    cp = st.checkbox("Cold Poly")
    hp = st.checkbox("Hot Poly")
    emr = st.checkbox("EMR")

    if st.button("🚀 วิเคราะห์ผลการคัดกรอง"):
        # คำนวณเบื้องต้นสำหรับ Model
        p_feat = ((age/100*0.2) + (1 if med else 0)*0.3 + (1 if loc else 0)*0.1 + (1 if surg else 0)*0.1 + (1 if rad else 0)*0.05 + (1 if chemo else 0)*0.05 + (1 if hp else 0)*0.1)
        
        # เตรียม Data 13 features
        input_df = pd.DataFrame([{
            'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': 1 if loc else 0, 'Med_Risk ': 1 if med else 0,
            'Surgery ': 1 if surg else 0, 'Radiation': 1 if rad else 0, 'Chemo': 1 if chemo else 0, 'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cp else 0, 'Hot Polypectomy': 1 if hp else 0, 'EMR': 1 if emr else 0, 
            'Prob_Risk': p_feat, 'Sex': 1 # ค่าตั้งต้น
        }])
        
        # AI Prediction
        prob_ai = model.predict_proba(input_df)[0][1]
        row_final = input_df.iloc[0].copy()
        row_final['Prob_Risk'] = prob_ai
        row_final['Clinical_Risk_Outcome'] = 1 if clip else 0
        
        details = get_triage_details(row_final)
        
        # แสดงผลใน Card สีขาวที่อ่านง่ายเสมอ
        st.markdown(f"""
            <div class='result-card'>
                <p class='{details['class']}'>{details['title']}</p>
                <hr>
                <p style='color: #1e293b;'><b>{details['follow_up']}</b></p>
                <p style='color: #1e293b;'>{details['diet']}</p>
                <p style='color: #1e293b;'>{details['activity']}</p>
                <p style='color: #64748b; font-size: 14px; margin-top: 10px;'>คะแนน AI: {prob_ai:.4f}</p>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.subheader("📊 ข้อมูลสรุปประจำวัน")
    # ส่วนสรุปภาพรวม Dashboard เหมือนเดิม...
    st.info("ระบบกำลังบันทึกข้อมูลเพื่อแสดงผลแนวโน้มรายวัน")
  
  
    
