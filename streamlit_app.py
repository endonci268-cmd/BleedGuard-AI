import streamlit as st
import pandas as pd
import joblib

# --- 1. ตั้งค่าหน้าตาแอป (Mobile Optimized) ---
st.set_page_config(page_title="BleedGuard AI | NCI", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    /* ปรับขนาดฟอนต์ให้เหมาะกับมือถือ */
    html, body, [class*="st-"] { font-size: 16px; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #004d99;
        color: white;
        font-weight: bold;
    }
    .result-card {
        padding: 20px;
        border-radius: 15px;
        background-color: white;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
        border-top: 8px solid #004d99;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except Exception as e:
    st.error(f"⚠️ ไม่สามารถเชื่อมต่อสมอง AI ได้: {e}")

# --- 3. Hybrid Triage Logic ---
def bleedguard_triage_logic(row, threshold=0.5):
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk", "แนะนำมาตรฐาน: สังเกตอาการตนเอง ไม่ต้องโทรติดตามเชิงรุก"
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk", "เฝ้าระวังเข้มข้น: พยาบาลโทรติดตามภายใน 24 ชม."
    return ("🟡 Moderate Risk", "ติดตามปกติ: โทรติดตามภายใน 1-3 วัน") if row['Prob_Risk'] >= threshold else ("🟢 Low Risk", "สังเกตอาการตามมาตรฐาน")

# --- 4. หน้าจอ UI ---
st.title("🩺 BleedGuard-AI")
st.caption("ระบบคัดกรองความเสี่ยงภาวะเลือดออกหลังส่องกล้อง (NCI)")

# ใช้การจัดลำดับแบบ Single Column บนมือถือโดยอัตโนมัติ
col_input, col_result = st.columns([1.5, 1])

with col_input:
    with st.expander("👤 ข้อมูลผู้ป่วย", expanded=True):
        age = st.number_input("อายุ (ปี)", 0, 120, 60)
        sex = st.selectbox("เพศ", ["ชาย (M)", "หญิง (F)"])
        size_cm = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.0, 10.0, 1.0, step=0.1)

    with st.expander("💊 ประวัติการรักษา (รวม Chemo/RT)", expanded=True):
        # ใช้ 2 คอลัมน์แทน 3 เพื่อให้ในมือถือไม่อัดแน่นเกินไป
        c1, c2 = st.columns(2)
        med_risk = c1.selectbox("ยาต้านเกล็ดเลือด/โรคประจำตัว", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        radiation = c2.selectbox("เคยฉายแสง (Radiation)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        chemo = c1.selectbox("เคยได้รับเคมีบำบัด (Chemo)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        surgery = c2.selectbox("ประวัติผ่าตัดช่องท้อง", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        loc_right = c1.selectbox("ตำแหน่งฝั่งขวา (Loc_Right)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        clip_risk = c2.selectbox("ติดคลิป/ความเสี่ยงหน้างาน", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')

    with st.expander("✂️ ประเภทหัตถการที่ทำ", expanded=True):
        # แก้ปัญหาตัวหนังสือหาย: ใช้การเรียงลงมาแนวตั้งในหน้าจอเล็ก
        bx = st.checkbox("BX (ตัดชิ้นเนื้อ)")
        cold_p = st.checkbox("Cold Polypectomy (ตัดเย็น)")
        hot_p = st.checkbox("Hot Polypectomy (ตัดร้อน)")
        emr = st.checkbox("EMR (ตัดขนาดใหญ่)")

with col_result:
    st.subheader("🎯 ผลการคัดกรอง")
    if st.button("🚀 วิเคราะห์ความเสี่ยง"):
        # คำนวณ Prob_Risk Feature ตามโครงสร้างเดิม
        p_score = ((age/100*0.2) + (med_risk*0.3) + (loc_right*0.1) + (surgery*0.1) + (radiation*0.05) + (chemo*0.05) + ((1 if hot_p else 0)*0.1))
        
        # จัดเรียง 13 Features ให้ตรงโมเดลเป๊ะๆ
        features_df = pd.DataFrame([{
            'Age': age, 'Size_cm ': size_cm, 'Loc_Right ': loc_right, 'Med_Risk ': med_risk,
            'Surgery ': surgery, 'Radiation': radiation, 'Chemo': chemo, 'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cold_p else 0, 'Hot Polypectomy': 1 if hot_p else 0,
            'EMR': 1 if emr else 0, 'Prob_Risk': p_score, 'Sex': 1 if "ชาย" in sex else 0
        }])

        # บังคับลำดับคอลัมน์เพื่อแก้ ValueError
        actual_features = features_df[['Age', 'Size_cm ', 'Loc_Right ', 'Med_Risk ', 'Surgery ', 'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 'EMR', 'Prob_Risk', 'Sex']]
        prob_ai = model.predict_proba(actual_features)[0][1]
        
        row_data = actual_features.iloc[0].copy()
        row_data['Prob_Risk'] = prob_ai
        row_data['Clinical_Risk_Outcome'] = clip_risk
        
        res, advice = bleedguard_triage_logic(row_data)

        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        if "🔴" in res: st.error(f"### {res}")
        elif "🟡" in res: st.warning(f"### {res}")
        else: st.success(f"### {res}")
        
        st.info(f"💡 **พยาบาลควรปฏิบัติ:**\n\n{advice}")
        st.metric("AI Risk Score", f"{prob_ai:.4f}")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.caption("GI Endoscopy Unit | NCI Thailand")
   

