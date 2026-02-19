import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SET UP & CONFIG ---
st.set_page_config(page_title="NCI BleedGuard-AI (Final)", layout="wide")

st.markdown("""
    <div style="text-align: center;">
        <h1 style="color: #B22222;">🛡️ NCI BleedGuard-AI: The Final Sentinel</h1>
        <p style="font-size: 18px;">สถาบันมะเร็งแห่งชาติ | เป้าหมาย FN = 3 (Threshold -2.4)</p>
    </div>
""", unsafe_allow_html=True)

# --- 2. เชื่อมต่อ GOOGLE SHEETS (ระบุชื่อ Sheet1) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ระบุชื่อ worksheet ว่า Sheet1 ตามที่พี่แจ้งครับ
        return conn.read(worksheet="Sheet1")
    except:
        return pd.DataFrame()

# --- 3. ML LOGIC (ตัด Case ID ออกจากการคำนวณ) ---
def predict_bleeding(data):
    # กฎเหล็กคลินิก (Override)
    if data['clip'] == 1:
        return "🔴 High Risk", "📞 ต้องโทรติดตาม 24, 48, 72 ชม. (พบการติด Hemoclip หน้างาน)", "#FFD2D2"
    
    # ML Weights: Case ID จะไม่ถูกนำมาใส่ใน weights นี้เด็ดขาด
    intercept = -2.4
    weights = {
        'age': 0.012, 'sex_male': 0.658, 'size': 2.429, 
        'emr': 1.044, 'hot_poly': 0.850, 'cold_poly': 0.074,
        'rad': 0.704, 'chemo': 0.631, 'med': -0.606, 
        'bx': -3.987, 'surgery': 0.618
    }
    
    # คำนวณคะแนนโดยใช้เฉพาะปัจจัยเสี่ยง (ไม่ใช้ Case ID)
    score = intercept
    score += data['age'] * weights['age']
    score += (weights['sex_male'] if data['sex'] == "ชาย" else 0)
    score += data['size'] * weights['size']
    score += (1 if data['emr'] else 0) * weights['emr']
    score += (1 if data['hot_poly'] else 0) * weights['hot_poly']
    score += (1 if data['cold_poly'] else 0) * weights['cold_poly']
    score += (1 if data['rad'] else 0) * weights['rad']
    score += (1 if data['chemo'] else 0) * weights['chemo']
    score += (1 if data['med'] else 0) * weights['med']
    score += (1 if data['bx'] else 0) * weights['bx']
    score += (1 if data['surgery'] else 0) * weights['surgery']

    if score >= -2.4:
        return "🟡 Moderate Risk", "📞 โทรติดตามวันที่ 1 และ 3 (กลุ่มเฝ้าระวังพิเศษ)", "#FFF9C4"
    else:
        if data['rad'] == 1 or data['chemo'] == 1:
            return "🟡 Moderate Risk (Oncology Guard)", "📞 โทรติดตามวันที่ 1 (เฝ้าระวังประวัติรักษามะเร็ง)", "#FFF9C4"
        return "🟢 Low Risk", "แนะนำอาหารอ่อน สังเกตอาการตามปกติ", "#D2FFD2"

# --- 4. UI INTERFACE ---
tab1, tab2 = st.tabs(["📋 ประเมินและบันทึกเคส", "📊 แดชบอร์ดสถิติวิจัย"])

with tab1:
    with st.form("main_assessment_form"):
        st.subheader("1. ข้อมูลพื้นฐาน")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        case_id = c1.text_input("Case ID (เพื่อการบันทึกข้อมูลเท่านั้น)")
        age = c2.number_input("อายุ (ปี)", min_value=0, max_value=120, value=60)
        sex = c3.selectbox("เพศ", ["ชาย", "หญิง"])
        size = c4.number_input("ขนาดติ่งเนื้อ (cm)", min_value=0.0, step=0.1, value=0.5)

        st.divider()
        st.subheader("2. หัตถการและปัจจัยเสี่ยง")
        p1, p2, p3, p4, p5 = st.columns(5)
        bx = p1.checkbox("Biopsy (BX)")
        cold_poly = p2.checkbox("Cold Poly")
        hot_poly = p3.checkbox("Hot Poly")
        emr = p4.checkbox("EMR")
        clip = p5.checkbox("ติด Hemoclip")

        r1, r2, r3, r4 = st.columns(4)
        med = r1.checkbox("ยาละลายลิ่มเลือด")
        surgery = r2.checkbox("ประวัติผ่าตัด")
        rad = r3.checkbox("ประวัติฉายแสง")
        chemo = r4.checkbox("ประวัติเคมีบำบัด")

        submit = st.form_submit_button("วิเคราะห์และบันทึกข้อมูล", variant="primary")

    if submit:
        # ส่งข้อมูลไปคำนวณ (โดยไม่ส่ง Case ID เข้าไปใน logic การคิดคะแนน)
        input_data = {
            'age': age, 'sex': sex, 'size': size, 'bx': bx, 'cold_poly': cold_poly,
            'hot_poly': hot_poly, 'emr': emr, 'clip': clip, 'med': med,
            'surgery': surgery, 'rad': rad, 'chemo': chemo
        }
        res, advice, color = predict_bleeding(input_data)
        
        # บันทึกข้อมูลลง Sheet1
        new_data = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Case_ID": case_id, "Age": age, "Sex": sex, "Size": size,
            "BX": int(bx), "Cold_Poly": int(cold_poly), "Hot_Poly": int(hot_poly),
            "EMR": int(emr), "Clip": int(clip), "Medication": int(med),
            "Surgery": int(surgery), "Radiation": int(rad), "Chemo": int(chemo),
            "Risk_Level": res, "Advice": advice
        }])
        
        df_old = get_data()
        df_new = pd.concat([df_old, new_data], ignore_index=True)
        conn.update(worksheet="Sheet1", data=df_new)
        
        st.markdown(f"<div style='background-color:{color}; padding:20px; border-radius:10px; text-align:center; border: 2px solid #B22222;'>"
                    f"<h2 style='color:black;'>{res}</h2><p style='color:black;'>{advice}</p></div>", unsafe_allow_html=True)
        st.success(f"บันทึกเคส {case_id} ลง Sheet1 เรียบร้อย!")

with tab2:
    st.subheader("📈 แดชบอร์ดติดตามข้อมูล (Sheet1)")
    df = get_data()
    if not df.empty:
        st.dataframe(df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลบันทึกในระบบ")
