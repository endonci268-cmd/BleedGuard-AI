import streamlit as st
import pandas as pd
import joblib

# --- 1. ตั้งค่าหน้าตาแอป (Dashboard Look) ---
st.set_page_config(page_title="BleedGuard AI | NCI", page_icon="🩺", layout="wide")

# ปรับแต่งสีและสไตล์
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 3.5em;
        background-color: #004d99;
        color: white;
        font-weight: bold;
        font-size: 18px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
    }
    .stExpander { border: 1px solid #004d99; border-radius: 10px; background-color: white; }
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

# --- 3. ฟังก์ชันการตัดสินใจ (Hybrid Logic) ---
def bleedguard_triage_logic(row, threshold=0.5):
    # กฎความเสี่ยงต่ำมาก (Green)
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ ไม่ต้องโทรติดตามเชิงรุก"
    
    # กฎความเสี่ยงวิกฤต (Red)
    # หมายเหตุ: clinical_risk_outcome คือการตัดสินใจหน้างานของแพทย์
    if row['clinical_risk_outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk", "พยาบาลต้องโทรติดตามอาการภายใน 24 ชม. และเน้นย้ำเรื่องอาหาร/การขับถ่าย"

    # ใช้ AI ตัดที่ Threshold
    if row['AI_Prob'] >= threshold:
        return "🟡 Moderate Risk", "แนะนำให้พยาบาลโทรติดตามอาการภายใน 1-3 วัน"
    else:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ"

# --- 4. หน้าจอหลัก ---
st.title("🩺 BleedGuard-AI Triage System")
st.markdown("##### ระบบอัจฉริยะคัดกรองความเสี่ยงภาวะเลือดออกหลังส่องกล้อง (สถาบันมะเร็งแห่งชาติ)")
st.divider()

# แบ่งหน้าจอเป็น 2 ส่วน
col_input, col_result = st.columns([1.8, 1])

with col_input:
    st.subheader("📝 ข้อมูลผู้ป่วยและหัตถการ")
    
    # กลุ่มที่ 1: ข้อมูลพื้นฐาน
    with st.expander("👤 ข้อมูลประชากรและขนาดติ่งเนื้อ", expanded=True):
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("อายุ (Age)", 0, 120, 60)
        sex = c2.selectbox("เพศ (Sex)", ["ชาย (M)", "หญิง (F)"])
        size_cm = c3.number_input("ขนาดติ่งเนื้อ (Size ซม.)", 0.0, 10.0, 1.0, step=0.1)

    # กลุ่มที่ 2: ประวัติความเสี่ยง (รวม Chemo/Radiation ที่หายไป)
    with st.expander("💊 ประวัติการรักษาและยา", expanded=True):
        c4, c5, c6 = st.columns(3)
        med_risk = c4.selectbox("มีโรคประจำตัว/ยาละลายลิ่มเลือด", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        radiation = c5.selectbox("เคยฉายแสง (Radiation)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        chemo = c6.selectbox("เคยรับเคมีบำบัด (Chemo)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        
        c7, c8, c9 = st.columns(3)
        loc_right = c7.selectbox("ติ่งเนื้ออยู่ฝั่งขวา (Loc_Right)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        surgery = c8.selectbox("มีประวัติผ่าตัดในช่องท้อง", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        clinical_risk_outcome = c9.selectbox("แพทย์ติดคลิป/เสี่ยงหน้างาน", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')

    # กลุ่มที่ 3: หัตถการที่ทำ
    with st.expander("✂️ ประเภทหัตถการที่ทำ", expanded=True):
        p1, p2, p3, p4 = st.columns(4)
        bx = p1.checkbox("BX (ตัดชิ้นเนื้อ)")
        cold_p = p2.checkbox("Cold Poly")
        hot_p = p3.checkbox("Hot Poly")
        emr = p4.checkbox("EMR")

with col_result:
    st.subheader("🎯 ผลการวิเคราะห์")
    if st.button("เริ่มทำการคัดกรอง"):
        # 1. คำนวณ Prob_Risk ตามสูตรเดิมเพื่อเป็นปัจจัยนำเข้า AI
        prob_risk_feature = (
            (age / 100 * 0.2) +
            (med_risk * 0.3) +
            (loc_right * 0.1) +
            (surgery * 0.1) +
            (radiation * 0.05) +
            (chemo * 0.05) +
            ((1 if hot_p else 0) * 0.1)
        )
        if prob_risk_feature > 1: prob_risk_feature = 1.0

        # 2. จัดเรียง Features ให้ตรงกับโมเดล LG (13 ตัว)
        input_df = pd.DataFrame([{
            'Age': age,
            'Size_cm ': size_cm,
            'Loc_Right ': loc_right,
            'Med_Risk ': med_risk,
            'Surgery ': surgery,
            'Radiation': radiation,
            'Chemo': chemo,
            'BX': 1 if bx else 0,
            'Cold Polypectomy': 1 if cold_p else 0,
            'Hot Polypectomy': 1 if hot_p else 0,
            'EMR': 1 if emr else 0,
            'Prob_Risk': prob_risk_feature,
            'Sex': 1 if "ชาย" in sex else 0
        }])

        # 3. ทำนายผลด้วย AI
        actual_ai_prob = model.predict_proba(input_df)[0][1]
        
        # 4. ใช้ Hybrid Logic ตัดสินใจ
        row_for_logic = input_df.iloc[0].copy()
        row_for_logic['AI_Prob'] = actual_ai_prob
        row_for_logic['clinical_risk_outcome'] = clinical_risk_outcome
        
        res_text, advice = bleedguard_triage_logic(row_for_logic)

        # 5. แสดงผลสวยงาม
        with st.container():
            st.markdown("<div style='background-color: white; padding: 20px; border-radius: 15px; border: 1px solid #ddd;'>", unsafe_allow_html=True)
            if "🔴" in res_text: st.error(f"### {res_text}")
            elif "🟡" in res_text: st.warning(f"### {res_text}")
            else: st.success(f"### {res_text}")
            
            st.info(f"💡 **คำแนะนำการพยาบาล:**\n\n{advice}")
            
            st.metric("AI Probability Score", f"{actual_ai_prob:.4f}")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("กรอกข้อมูลให้ครบถ้วน แล้วกดปุ่ม **'เริ่มทำการคัดกรอง'** เพื่อดูผลลัพธ์")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute of Thailand")

