import streamlit as st
import pandas as pd
import joblib

# --- 1. ตั้งค่าหน้าตาแอปให้ดูเป็นมืออาชีพ ---
st.set_page_config(page_title="BleedGuard-AI | NCI", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #004d99; color: white; font-weight: bold; }
    .result-box { padding: 20px; border-radius: 10px; border: 1px solid #ddd; background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. โหลดโมเดล LG จากไฟล์ .pkl ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except Exception as e:
    st.error(f"⚠️ ไม่สามารถเชื่อมต่อสมอง AI ได้: {e}")

# --- 3. ตรรกะการคัดกรองแบบ Hybrid (NCI Standard) ---
def bleedguard_triage_logic(row, threshold=0.5):
    # เลเยอร์ 1: ความเสี่ยงต่ำมาก (De-escalation)
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ ไม่ต้องโทรติดตามเชิงรุก"
    
    # เลเยอร์ 2: ความเสี่ยงวิกฤต (Safety First)
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk", "พยาบาลต้องโทรติดตามอาการภายใน 24 ชม. และเน้นย้ำเรื่องอาหาร/การขับถ่าย"

    # เลเยอร์ 3: ใช้ผลจาก AI ตัดที่ Threshold
    if row['Prob_Risk'] >= threshold:
        return "🟡 Moderate Risk", "แนะนำให้พยาบาลโทรติดตามอาการภายใน 1-3 วัน"
    else:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ"

# --- 4. ส่วนหน้าจอรับข้อมูล (UI) ---
st.title("🩺 BleedGuard-AI Triage System")
st.markdown("##### ระบบสนับสนุนการตัดสินใจเพื่อเฝ้าระวังภาวะเลือดออกหลังส่องกล้อง สถาบันมะเร็งแห่งชาติ")
st.divider()

col_input, col_result = st.columns([2, 1])

with col_input:
    with st.expander("📝 ข้อมูลประชากรและหัตถการ", expanded=True):
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age (อายุ)", 0, 120, 60)
        sex = c2.selectbox("Sex (เพศ)", ["ชาย (M)", "หญิง (F)"])
        size_cm = c3.number_input("Size (ขนาดติ่งเนื้อ ซม.)", 0.0, 10.0, 1.0, 0.1)

        c4, c5, c6 = st.columns(3)
        loc_right = c4.selectbox("Loc_Right (ฝั่งขวา)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        med_risk = c5.selectbox("Med_Risk (โรคประจำตัว/ยา)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        surgery = c6.selectbox("Surgery (ประวัติผ่าตัด)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')

        st.write("**ประเภทหัตถการ:**")
        p1, p2, p3, p4 = st.columns(4)
        bx = p1.checkbox("BX")
        cold_p = p2.checkbox("Cold Poly")
        hot_p = p3.checkbox("Hot Poly")
        emr = p4.checkbox("EMR")
        
        clinical_risk_outcome = st.selectbox("Clinical Risk (แพทย์ติดคลิป/ความเสี่ยงหน้างาน)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')

with col_result:
    st.subheader("🎯 ผลการวิเคราะห์")
    if st.button("เริ่มการคัดกรอง"):
        # จัดเรียงปัจจัยให้ตรงกับที่โมเดล LG ต้องการเป๊ะๆ (13 Features)
        features_df = pd.DataFrame([{
            'Age': age,
            'Size_cm ': size_cm,
            'Loc_Right ': loc_right,
            'Med_Risk ': med_risk,
            'Surgery ': surgery,
            'Radiation': 0, # ค่าคงที่ตามโมเดล
            'Chemo': 0,      # ค่าคงที่ตามโมเดล
            'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cold_p else 0,
            'Hot Polypectomy': 1 if hot_p else 0,
            'EMR': 1 if emr else 0,
            'Prob_Risk': 0.0, # Placeholder
            'Sex': 1 if "ชาย" in sex else 0
        }])

        # 1. คำนวณ Prob_Risk จริงๆ จาก AI
        input_for_model = features_df.drop(columns=['Prob_Risk'])
        actual_prob = model.predict_proba(input_for_model)[0][1]
        
        # 2. นำค่าที่ได้มาใส่ในตรรกะตัดสินใจ
        final_row = features_df.iloc[0].copy()
        final_row['Prob_Risk'] = actual_prob
        final_row['Clinical_Risk_Outcome'] = clinical_risk_outcome
        
        res_text, advice = bleedguard_triage_logic(final_row)

        # 3. แสดงผลด้วยสีและกล่องข้อความ
        with st.container():
            if "🔴" in res_text: st.error(f"### {res_text}")
            elif "🟡" in res_text: st.warning(f"### {res_text}")
            else: st.success(f"### {res_text}")
            
            st.info(f"💡 **คำแนะนำ:** {advice}")
            st.metric("AI Risk Score", f"{actual_prob:.4f}")
    else:
        st.write("กรุณากรอกข้อมูลและกดปุ่มด้านซ้าย")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute")
  

