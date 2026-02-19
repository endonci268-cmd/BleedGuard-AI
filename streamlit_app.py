import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="NCI BleedGuard Database", layout="wide")
st.title("🛡️ NCI BleedGuard-AI & Dashboard")

# --- เชื่อมต่อ Google Sheets ---
# (ต้องไปตั้งค่า Secrets ใน Streamlit Cloud ด้วยลิงก์ Google Sheets ของคุณ)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ML Logic (FN=3) ---
def predict_bleeding(data):
    # (ใช้ Logic เดิมที่คุณเลือก Threshold -2.4)
    intercept = -2.4
    weights = {'size': 2.429, 'emr': 1.044, 'rad': 0.704, 'chemo': 0.631, 'med': -0.606, 'bx': -3.987}
    
    # Clinical Overrides
    if data['clip'] == 1 or data['size'] >= 1.0:
        return "🔴 High Risk", "📞 ติดตาม 24, 48, 72 ชม.", "#FFD2D2"
    
    score = intercept + (data['size'] * weights['size']) + (data['emr'] * weights['emr']) # ... (เพิ่มปัจจัยอื่นให้ครบ)
    
    if score >= -2.4:
        return "🟡 Moderate Risk", "📞 ติดตามวันที่ 1 และ 3", "#FFF9C4"
    return "🟢 Low Risk", "สังเกตอาการตามปกติ", "#D2FFD2"

# --- ส่วนรับข้อมูลและบันทึก ---
tab1, tab2 = st.tabs(["📋 ประเมินคนไข้ใหม่", "📊 แดชบอร์ดสรุปผล"])

with tab1:
    with st.form("assessment_form"):
        hn = st.text_input("HN / Case ID")
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", value=0.5)
        clip = st.checkbox("ติด Hemoclip")
        # ... (เพิ่ม Checkbox อื่นๆ)
        recorder = st.text_input("ชื่อผู้บันทึก")
        submit = st.form_submit_button("วิเคราะห์และบันทึกลงฐานข้อมูล")

    if submit:
        res, advice, color = predict_bleeding({'size': size, 'clip': int(clip), 'emr': 0, 'rad': 0, 'chemo': 0, 'med': 0, 'bx': 0})
        
        # บันทึกข้อมูลใหม่ลง Google Sheets
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "HN": hn, "Size": size, "Risk_Level": res, "Advice": advice, "Recorder_Name": recorder
        }])
        
        # ดึงข้อมูลเก่ามาต่อกับข้อมูลใหม่แล้วอัปเดตกลับไป
        existing_data = conn.read(worksheet="records")
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(worksheet="records", data=updated_df)
        
        st.success("บันทึกข้อมูลสำเร็จ!")
        st.balloons()

with tab2:
    st.subheader("📈 สถิติความเสี่ยงแยกตามระดับ")
    df = conn.read(worksheet="records")
    if not df.empty:
        # แสดงผลแดชบอร์ด
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("ตารางข้อมูลล่าสุด")
            st.dataframe(df.sort_values(by="Timestamp", ascending=False))
        with col_b:
            st.write("สัดส่วนระดับความเสี่ยง")
            st.bar_chart(df['Risk_Level'].value_counts())
    else:
        st.info("ยังไม่มีข้อมูลในฐานข้อมูล")
