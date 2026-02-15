import streamlit as st
import pandas as pd
import joblib
import altair as alt
from datetime import datetime

# --- 1. ตั้งค่าหน้าตาแอป (Mobile Friendly & NCI Theme) ---
st.set_page_config(page_title="BleedGuard-AI | NCI", page_icon="🩺", layout="centered")

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])

# ตกแต่ง CSS เน้นตัวหนังสือชัดเจนและสีสันสื่อความหมาย
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 18px !important; color: #1e293b; }
    .main { background-color: #ffffff; }
    
    /* หัวข้อใหญ่บนมือถือ */
    .main-title { color: #004d99; font-size: 24px; font-weight: bold; text-align: center; line-height: 1.3; margin-bottom: 5px; }
    .sub-title { color: #64748b; font-size: 16px; text-align: center; margin-bottom: 20px; }

    /* ปุ่มกดขนาดใหญ่ */
    .stButton>button {
        width: 100%;
        border-radius: 15px;
        height: 4em;
        background-color: #004d99;
        color: white;
        font-weight: bold;
        font-size: 22px;
        margin-top: 10px;
    }

    /* สีข้อความผลลัพธ์ */
    .res-green { color: #28a745; font-size: 26px; font-weight: bold; text-align: center; }
    .res-yellow { color: #ffc107; font-size: 26px; font-weight: bold; text-align: center; }
    .res-red { color: #dc3545; font-size: 26px; font-weight: bold; text-align: center; }
    .advice-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #004d99; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 3. Hybrid Triage Logic ---
def bleedguard_triage_logic(row, threshold=0.5):
    # กฎเขียว (Low Risk)
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 ความเสี่ยงต่ำ (Low Risk)", "ดูแลตามมาตรฐาน ไม่ต้องโทรติดตามเชิงรุก", "res-green"
    
    # กฎแดง (High Risk)
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 ความเสี่ยงสูง (High Risk)", "พยาบาลต้องโทรติดตามภายใน 24 ชม. และเฝ้าระวังเข้มข้น", "res-red"
    
    # AI Prediction
    if row['Prob_Risk'] >= threshold:
        return "🟡 ความเสี่ยงปานกลาง (Moderate Risk)", "แนะนำให้พยาบาลโทรติดตามภายใน 1-3 วัน", "res-yellow"
    else:
        return "🟢 ความเสี่ยงต่ำ (Low Risk)", "ดูแลตามมาตรฐานปกติ", "res-green"

# --- 4. ส่วนหัวเว็บแอป (Header) ---
st.markdown("<div class='main-title'>ระบบอัจฉริยะคัดกรองความเสี่ยงภาวะเลือดออกหลังส่องกล้องลำไส้ใหญ่และตัดติ่งเนื้อ (BleedGuard-AI)</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>ศูนย์ส่องกล้องทางเดินอาหาร สถาบันมะเร็งแห่งชาติ</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🩺 การคัดกรอง (Triage)", "📊 แดชบอร์ด (Dashboard)"])

with tab1:
    st.markdown("#### 📝 ข้อมูลผู้ป่วยและหัตถการ")
    age = st.number_input("อายุ (Age)", 0, 120, 60)
    sex = st.radio("เพศ (Sex)", ["ชาย (Male)", "หญิง (Female)"], horizontal=True)
    size_cm = st.number_input("ขนาดติ่งเนื้อ (Size in cm)", 0.0, 10.0, 1.0, step=0.1)
    
    st.divider()
    st.markdown("#### 💊 ประวัติและความเสี่ยง")
    med = st.checkbox("ยาละลายลิ่มเลือด/โรคประจำตัวร่วม")
    rad = st.checkbox("เคยฉายแสง (Radiation)")
    chemo = st.checkbox("เคยรับเคมีบำบัด (Chemo)")
    surg = st.checkbox("เคยผ่าตัดช่องท้อง (Surgery)")
    loc = st.checkbox("ตำแหน่งฝั่งขวา (Right Side)")
    clip = st.checkbox("แพทย์ติดคลิป/ความเสี่ยงหน้างาน")
    
    st.divider()
    st.markdown("#### ✂️ ประเภทหัตถการ")
    bx = st.checkbox("BX (ตัดชิ้นเนื้อ)")
    cp = st.checkbox("Cold Polypectomy")
    hp = st.checkbox("Hot Polypectomy")
    emr = st.checkbox("EMR")

    if st.button("🚀 วิเคราะห์ความเสี่ยง"):
        # คำนวณเบื้องต้นเพื่อส่งเข้าโมเดล
        p_feat = ((age/100*0.2) + (1 if med else 0)*0.3 + (1 if loc else 0)*0.1 + (1 if surg else 0)*0.1 + (1 if rad else 0)*0.05 + (1 if chemo else 0)*0.05 + (1 if hp else 0)*0.1)
        
        # เตรียม Data 13 features (ต้องเรียงลำดับให้ตรงกับ bleedguard_model.pkl)
        input_df = pd.DataFrame([{
            'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': 1 if loc else 0, 'Med_Risk ': 1 if med else 0,
            'Surgery ': 1 if surg else 0, 'Radiation': 1 if rad else 0, 'Chemo': 1 if chemo else 0, 'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cp else 0, 'Hot Polypectomy': 1 if hp else 0, 'EMR': 1 if emr else 0, 
            'Prob_Risk': p_feat, 'Sex': 1 if "ชาย" in sex else 0
        }])
        
        # AI Prediction
        prob_ai = model.predict_proba(input_df)[0][1]
        row_final = input_df.iloc[0].copy()
        row_final['Prob_Risk'] = prob_ai
        row_final['Clinical_Risk_Outcome'] = 1 if clip else 0
        
        res_text, advice, color_class = bleedguard_triage_logic(row_final)
        
        # บันทึกประวัติลง Dashboard
        now = datetime.now().strftime("%d/%m %H:%M")
        st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([{'Date_Time': now, 'Risk_Score': prob_ai, 'Result': res_text}])], ignore_index=True)
        
        # --- แสดงผลลัพธ์เน้นสีข้อความ ---
        st.divider()
        st.markdown(f"<div class='{color_class}'>{res_text}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='advice-box'><b>💡 คำแนะนำทางการพยาบาล:</b><br>{advice}</div>", unsafe_allow_html=True)
        st.metric("คะแนนความเสี่ยงจาก AI", f"{prob_ai:.4f}")

with tab2:
    st.markdown("### 📊 สรุปภาพรวมรายวัน")
    if not st.session_state.history.empty:
        st.write(f"จำนวนเคสที่คัดกรองวันนี้: **{len(st.session_state.history)} ราย**")
        st.divider()
        st.dataframe(st.session_state.history[['Date_Time', 'Result']].sort_index(ascending=False), use_container_width=True)
        
        if st.button("🗑️ ล้างข้อมูล Dashboard"):
            st.session_state.history = pd.DataFrame(columns=['Date_Time', 'Age', 'Size_cm', 'Risk_Score', 'Result'])
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลการคัดกรอง")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute")
