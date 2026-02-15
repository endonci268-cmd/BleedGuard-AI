import streamlit as st
import pandas as pd
import joblib

# --- 1. ตั้งค่าหน้าตาแอปให้สวยงาม ---
st.set_page_config(page_title="BleedGuard-AI | NCI", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #004d99; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

model = load_model()

# --- 3. Hybrid Triage Logic ---
def bleedguard_triage_logic(row, threshold=0.5):
    # กฎความเสี่ยงต่ำมาก (De-escalation)
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ ไม่ต้องโทรติดตามเชิงรุก"
    
    # กฎความเสี่ยงวิกฤต (Safety First)
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk", "พยาบาลต้องโทรติดตามอาการภายใน 24 ชม. และเน้นย้ำเรื่องอาหาร/การขับถ่าย"

    # ใช้ผลจาก AI ตัดที่ Threshold 0.5
    if row['Prob_Risk'] >= threshold:
        return "🟡 Moderate Risk", "แนะนำให้พยาบาลโทรติดตามอาการภายใน 1-3 วัน"
    else:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ"

# --- 4. ส่วน UI รับข้อมูล ---
st.title("🩺 BleedGuard-AI Triage System")
st.markdown("##### ระบบสนับสนุนการตัดสินใจเพื่อเฝ้าระวังภาวะเลือดออกหลังส่องกล้อง สถาบันมะเร็งแห่งชาติ")
st.divider()

col_in, col_out = st.columns([2, 1])

with col_in:
    with st.container(border=True):
        st.subheader("📝 ข้อมูลผู้ป่วยและหัตถการ")
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age (อายุ)", 0, 120, 60)
        sex = c2.selectbox("Sex (เพศ)", ["ชาย (M)", "หญิง (F)"])
        size_cm = c3.number_input("Size (ขนาดติ่งเนื้อ ซม.)", 0.0, 10.0, 1.0)

        c4, c5, c6 = st.columns(3)
        loc_right = c4.selectbox("Loc_Right (ฝั่งขวา)", [0, 1])
        med_risk = c5.selectbox("Med_Risk (ยา/โรคประจำตัว)", [0, 1])
        surgery = c6.selectbox("Surgery (ประวัติผ่าตัด)", [0, 1])

        st.write("**ปัจจัยเพิ่มเติมและหัตถการ:**")
        p1, p2, p3, p4 = st.columns(4)
        bx = p1.checkbox("BX")
        cold_p = p2.checkbox("Cold Poly")
        hot_p = p3.checkbox("Hot Poly")
        emr = p4.checkbox("EMR")
        
        clinical_risk_outcome = st.selectbox("Clinical Risk (แพทย์ติดคลิป/ความเสี่ยงหน้างาน)", [0, 1])

with col_out:
    st.subheader("🎯 ผลการวิเคราะห์")
    if st.button("เริ่มการคัดกรอง"):
        # จัดเรียงลำดับปัจจัยให้ตรงกับที่โมเดล LG ต้องการเป๊ะๆ (13 Features)
        # หมายเหตุ: ชื่อคอลัมน์ที่มีช่องว่างท้ายชื่อ ต้องคงไว้ตามโมเดลต้นฉบับ
        features_df = pd.DataFrame([{
            'Age': age,
            'Size_cm ': size_cm,
            'Loc_Right ': loc_right,
            'Med_Risk ': med_risk,
            'Surgery ': surgery,
            'Radiation': 0, 
            'Chemo': 0,
            'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cold_p else 0,
            'Hot Polypectomy': 1 if hot_p else 0,
            'EMR': 1 if emr else 0,
            'Prob_Risk': 0.0, # ตัวแปรนี้โมเดล LG ของคุณมองเป็นหนึ่งใน Feature
            'Sex': 1 if "ชาย" in sex else 0
        }])

        # คำนวณ Prob_Risk จาก AI
        # เราต้องส่ง Feature ทั้งหมดยกเว้นคอลัมน์ผลลัพธ์ แต่เนื่องจากโมเดลคุณรวม Prob_Risk เป็น Feature 
        # เราจะส่ง 12 ตัวแรก (ตัด Prob_Risk ออกชั่วคราวเพื่อทำนาย)
        # แต่จาก Traceback โมเดลคุณต้องการ 13 ตัว ให้เราเรียงตามนี้:
        
        # ตรวจสอบลำดับคอลัมน์อีกครั้งให้ตรงกับ bleedguard_model.pkl
        actual_features = features_df[['Age', 'Size_cm ', 'Loc_Right ', 'Med_Risk ', 'Surgery ', 
                                       'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 
                                       'Hot Polypectomy', 'EMR', 'Prob_Risk', 'Sex']]
        
        # ทำนายความน่าจะเป็น
        prob_score = model.predict_proba(actual_features)[0][1]
        
        # ใส่ค่ากลับเข้า Data สำหรับ Hybrid Logic
        final_data = features_df.iloc[0].copy()
        final_data['Prob_Risk'] = prob_score
        final_data['Clinical_Risk_Outcome'] = clinical_risk_outcome
        
        res_text, advice = bleedguard_triage_logic(final_data)

        # แสดงผล
        if "🔴" in res_text: st.error(f"### {res_text}")
        elif "🟡" in res_text: st.warning(f"### {res_text}")
        else: st.success(f"### {res_text}")
        
        st.info(f"💡 **คำแนะนำ:** {advice}")
        st.metric("AI Risk Score", f"{prob_score:.4f}")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute")
