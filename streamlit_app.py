import streamlit as st
import pandas as pd
import joblib

# --- 1. ตั้งค่าหน้าตาแอป (Custom Theme) ---
st.set_page_config(page_title="BleedGuard AI | NCI", page_icon="🩺", layout="wide")

# การตกแต่ง CSS เพื่อความสวยงาม
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #004d99;
        color: white;
        font-weight: bold;
        font-size: 18px;
    }
    .stExpander { border: 1px solid #004d99; border-radius: 10px; background-color: white; }
    .result-card {
        padding: 20px;
        border-radius: 15px;
        background-color: white;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
        border-left: 10px solid #004d99;
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

# --- 3. ตรรกะการตัดสินใจ (Hybrid Logic) ---
def bleedguard_triage_logic(row, threshold=0.5):
    # กฎเขียว (De-escalation)
    if row['Size_cm '] < 0.5 and row['BX'] == 1 and row['Cold Polypectomy'] == 0:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ ไม่ต้องโทรติดตามเชิงรุก"
    
    # กฎแดง (Safety First)
    if row['Clinical_Risk_Outcome'] == 1 or row['Size_cm '] >= 2.0 or row['EMR'] == 1:
        return "🔴 High Risk", "พยาบาลต้องโทรติดตามอาการภายใน 24 ชม. และเน้นย้ำเรื่องอาหาร/การขับถ่าย"

    # กฎ AI (Logistic Regression)
    if row['Prob_Risk'] >= threshold:
        return "🟡 Moderate Risk", "แนะนำให้พยาบาลโทรติดตามอาการภายใน 1-3 วัน"
    else:
        return "🟢 Low Risk", "แนะนำการดูแลตามมาตรฐานปกติ"

# --- 4. หน้าจอหลัก (UI) ---
st.title("🩺 BleedGuard-AI Triage System")
st.markdown("##### ระบบสนับสนุนการตัดสินใจเพื่อเฝ้าระวังภาวะเลือดออกหลังส่องกล้อง สถาบันมะเร็งแห่งชาติ")
st.divider()

col_input, col_result = st.columns([1.8, 1])

with col_input:
    st.subheader("📝 ข้อมูลผู้ป่วยและหัตถการ")
    
    with st.expander("👤 ข้อมูลประชากรและลักษณะติ่งเนื้อ", expanded=True):
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("อายุ (Age)", 0, 120, 60)
        sex = c2.selectbox("เพศ (Sex)", ["ชาย (M)", "หญิง (F)"])
        size_cm = c3.number_input("ขนาดติ่งเนื้อ (Size ซม.)", 0.0, 10.0, 1.0, step=0.1)

    with st.expander("💊 ประวัติการรักษา (Chemo / RT / Surgery)", expanded=True):
        c4, c5, c6 = st.columns(3)
        med_risk = c4.selectbox("มีโรคประจำตัว/ยาต้านเกล็ดเลือด", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        radiation = c5.selectbox("เคยฉายแสง (Radiation)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        chemo = c6.selectbox("เคยรับเคมีบำบัด (Chemo)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        
        c7, c8, c9 = st.columns(3)
        loc_right = c7.selectbox("ตำแหน่งฝั่งขวา (Loc_Right)", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        surgery = c8.selectbox("มีประวัติผ่าตัดในช่องท้อง", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')
        clip_risk = c9.selectbox("แพทย์ติดคลิป/ความเสี่ยงหน้างาน", [0, 1], format_func=lambda x: 'ใช่' if x==1 else 'ไม่ใช่')

    with st.expander("✂️ ประเภทหัตถการที่ทำ", expanded=True):
        p1, p2, p3, p4 = st.columns(4)
        bx = p1.checkbox("BX (ชิ้นเนื้อ)")
        cold_p = p2.checkbox("Cold Poly")
        hot_p = p3.checkbox("Hot Poly")
        emr = p4.checkbox("EMR")

with col_result:
    st.subheader("🎯 ผลการคัดกรอง")
    if st.button("🚀 เริ่มการวิเคราะห์"):
        # 1. เตรียมข้อมูลนำเข้า (ต้องเรียงลำดับ 13 ตัวตามโมเดลเป๊ะๆ)
        # เราใช้สูตรเดิมคำนวณ Prob_Risk เพื่อเป็น Feature ให้โมเดล AI ของคุณตามโครงสร้างเดิม
        prob_score_feature = ((age/100*0.2) + (med_risk*0.3) + (loc_right*0.1) + (surgery*0.1) + (radiation*0.05) + (chemo*0.05) + ((1 if hot_p else 0)*0.1))
        
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
            'Prob_Risk': prob_score_feature,
            'Sex': 1 if "ชาย" in sex else 0
        }])

        # 2. ให้ AI (LG) ทำนายผลจริง
        # บังคับเรียงลำดับคอลัมน์ให้ตรงกับ bleedguard_model.pkl
        actual_features = input_df[['Age', 'Size_cm ', 'Loc_Right ', 'Med_Risk ', 'Surgery ', 'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 'EMR', 'Prob_Risk', 'Sex']]
        prob_ai = model.predict_proba(actual_features)[0][1]
        
        # 3. ใช้ Hybrid Logic ตัดสินใจ
        row_data = actual_features.iloc[0].copy()
        row_data['Prob_Risk'] = prob_ai # ใช้ Prob จาก AI จริง
        row_data['Clinical_Risk_Outcome'] = clip_risk
        
        res, advice = bleedguard_triage_logic(row_data)

        # 4. แสดงผลสวยงาม
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        if "🔴" in res: st.error(f"### {res}")
        elif "🟡" in res: st.warning(f"### {res}")
        else: st.success(f"### {res}")
        
        st.info(f"💡 **คำแนะนำการพยาบาล:**\n\n{advice}")
        st.metric("AI Risk Probability", f"{prob_ai:.4f}")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("กรอกข้อมูลให้ครบและกดปุ่มด้านซ้ายเพื่อดูผล")

st.divider()
st.caption("GI Endoscopy Unit | National Cancer Institute of Thailand")
