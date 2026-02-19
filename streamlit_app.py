import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SET UP ---
st.set_page_config(page_title="NCI BleedGuard-AI", layout="wide")

st.markdown("""
    <div style="text-align: center;">
        <h1 style="color: #B22222;">🛡️ NCI BleedGuard-AI: The Final Sentinel</h1>
        <p style="font-size: 18px;">เป้าหมาย Sensitivity 91% | False Negative 3%</p>
    </div>
""", unsafe_allow_html=True)

# --- 2. CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(worksheet="Sheet1")
    except:
        return pd.DataFrame()

# --- 3. ML LOGIC (DROPPING CASE ID) ---
def predict_bleeding(data):
    # Rule 1: Clinical Override (ติดคลิป = แดงทันที)
    if data['clip'] == 1:
        return "🔴 High Risk", "📞 ต้องโทรติดตาม 24, 48, 72 ชม. (พบการติด Hemoclip หน้างาน)", "#FFD2D2"
    
    # Rule 2: ML Calculation (Case ID is NOT included here)
    intercept = -2.4
    weights = {
        'age': 0.012, 'sex_male': 0.658, 'size': 2.429, 
        'emr': 1.044, 'hot_poly': 0.850, 'cold_poly': 0.074,
        'rad': 0.704, 'chemo': 0.631, 'med': -0.606, 
        'bx': -3.987, 'surgery': 0.618
    }
    
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

    # Decision
    if score >= -2.4:
        return "🟡 Moderate Risk", "📞 โทรติดตามวันที่ 1 และ 3 (กลุ่มเฝ้าระวังพิเศษ)", "#FFF9C4"
    else:
        if data['rad'] == 1 or data['chemo'] == 1:
            return "🟡 Moderate Risk (Oncology Guard)", "📞 โทรติดตามวันที่ 1 (เฝ้าระวังประวัติรักษามะเร็ง)", "#FFF9C4"
        return "🟢 Low Risk", "แนะนำอาหารอ่อน สังเกตอาการตามปกติ", "#D2FFD2"

# --- 4. UI TABS ---
tab1, tab2 = st.tabs(["📋 ประเมินเคสใหม่", "📊 แดชบอร์ดวิจัย"])

with tab1:
    with st.form(key="nci_form"):
        st.subheader("1. ข้อมูลพื้นฐาน")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        case_id = c1.text_input("Case ID (ไม่นำมาคำนวณคะแนน)")
        age = c2.number_input("อายุ (ปี)", min_value=0, value=60)
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

        submitted = st.form_submit_button("วิเคราะห์และบันทึกข้อมูล", variant="primary")

    if submitted:
        if not case_id:
            st.error("กรุณากรอก Case ID")
        else:
            input_data = {
                'age': age, 'sex': sex, 'size': size, 'bx': bx, 'cold_poly': cold_poly,
                'hot_poly': hot_poly, 'emr': emr, 'clip': clip, 'med': med,
                'surgery': surgery, 'rad': rad, 'chemo': chemo
            }
            res, advice, color = predict_bleeding(input_data)
            
            # Record Data
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Case_ID": case_id, "Age": age, "Sex": sex, "Size": size,
                "BX": int(bx), "Cold_Poly": int(cold_poly), "Hot_Poly": int(hot_poly),
                "EMR": int(emr), "Clip": int(clip), "Medication": int(med),
                "Surgery": int(surgery), "Radiation": int(rad), "Chemo": int(chemo),
                "Risk_Level": res, "Advice": advice
            }])
            
            df_old = get_data()
            df_new = pd.concat([df_old, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_new)
            
            st.markdown(f"<div style='background-color:{color}; padding:20px; border-radius:10px; text-align:center; border: 2px solid #B22222;'>"
                        f"<h2 style='color:black;'>{res}</h2><p style='color:black; font-size:18px;'>{advice}</p></div>", unsafe_allow_html=True)
            st.success("บันทึกข้อมูลสำเร็จ!")

with tab2:
    st.subheader("📊 สรุปผลการพยาบาล")
    df = get_data()
    
    if not df.empty:
        # สรุปรายวัน
        df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
        today = datetime.now().date()
        df_today = df[df['Date'] == today]
        
        st.write(f"📅 **ประจำวันที่:** {today}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสทั้งหมดวันนี้", len(df_today))
        m2.metric("🔴 แดง", len(df_today[df_today['Risk_Level'].str.contains("🔴")]))
        m3.metric("🟡 เหลือง", len(df_today[df_today['Risk_Level'].str.contains("🟡")]))
        m4.metric("🟢 เขียว", len(df_today[df_today['Risk_Level'].str.contains("🟢")]))

        st.divider()
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.write("**สัดส่วนความเสี่ยงสะสม**")
            st.bar_chart(df['Risk_Level'].value_counts())
        with col_r:
            st.info(f"🎯 **Target Sensitivity:** 91%\n\n📉 **Target FN Rate:** 3%")
            st.write(f"จำนวนเคสสะสมทั้งหมด: {len(df)} ราย")

        st.divider()
        st.write("**📋 ตารางบันทึกการประเมิน (ล่าสุดอยู่บน)**")
        # โชว์เฉพาะ Timestamp, Case_ID, Risk_Level, Advice
        st.dataframe(
            df[['Timestamp', 'Case_ID', 'Risk_Level', 'Advice']].sort_values(by="Timestamp", ascending=False),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("ยังไม่มีข้อมูลบันทึกในระบบ")
