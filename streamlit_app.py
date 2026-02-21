import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import pytz
from datetime import datetime

# --- การตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="BleedGuard AI - NCI", layout="wide")
tz_th = pytz.timezone('Asia/Bangkok')

# --- 1. โหลดโมเดล ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
except:
    st.error("ไม่พบไฟล์ bleedguard_model.pkl กรุณาตรวจสอบใน GitHub")

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(worksheet="Sheet1", ttl="0")

# --- 3. ส่วนหน้าจอหลัก (Tabs) ---
tab1, tab2 = st.tabs(["🩺 ระบบประเมินความเสี่ยง", "📊 Dashboard & Database"])

with tab1:
    st.title("🎗️ BleedGuard: ระบบคัดกรองเลือดออกหลังส่องกล้อง")
    
    with st.form("triage_form"):
        c1, c2 = st.columns(2)
        with c1:
            case_id_input = st.text_input("รหัสผู้ป่วย (Case ID)")
            age_input = st.number_input("อายุ (Age)", 0, 120, 60)
            sex_input = st.selectbox("เพศ (Sex)", [0, 1], format_func=lambda x: "ชาย" if x==1 else "หญิง")
            size_input = st.number_input("ขนาดติ่งเนื้อ (Size cm)", 0.0, 10.0, 1.0, step=0.1)
            loc_side = st.selectbox("ตำแหน่ง (Location)", ["Left Side", "Right Side"])
            med_in = st.checkbox("ใช้ยาละลายลิ่มเลือด (Medication)")
            surg_in = st.checkbox("ประวัติผ่าตัดลำไส้ (Surgery)")
            
        with c2:
            rad_in = st.checkbox("ประวัติฉายแสง (Radiation)")
            chemo_in = st.checkbox("ประวัติเคมีบำบัด (Chemo)")
            bx_in = st.checkbox("Biopsy (BX)")
            cold_in = st.checkbox("Cold Snare Polypectomy")
            hot_in = st.checkbox("Hot Polypectomy")
            emr_in = st.checkbox("EMR")
            clip_in = st.checkbox("มีการติด Hemoclip (Clip)")

        submit = st.form_submit_button("เริ่มประเมินความเสี่ยง")

    if submit:
        # เตรียมข้อมูลสำหรับ AI
        loc_right = 1 if loc_side == "Right Side" else 0
        input_df = pd.DataFrame([[age_input, sex_input, size_input, loc_right, int(med_in), int(surg_in), 
                                  int(rad_in), int(chemo_in), int(bx_in), int(cold_in), int(hot_in), int(emr_in)]],
                                columns=['age', 'sex', 'size_cm', 'loc_right', 'med_risk', 'surgery', 
                                         'radiation', 'chemo', 'bx', 'cold_snare', 'hot_poly', 'emr'])
        
        # คำนวณ AI Prob
        prob = model.predict_proba(input_df)[0][1]
        
        # --- 🌟 NEW LOGIC (Sensitivity 100%) 🌟 ---
        res, advice, bg_color, text_color = "", "", "", "#FFFFFF"
        
        if size_input >= 2.0 or emr_in or rad_in:
            res = "🔴 High Risk"
            advice = "เฝ้าระวังเข้มงวด: โทรติดตามอาการวันที่ 1, 2 และ 3"
            bg_color = "#FF4B4B"
        elif clip_in or prob > 0.12:
            res = "🟡 Moderate Risk"
            advice = "เฝ้าระวังต่อเนื่อง: โทรติดตามอาการในวันที่ 2"
            bg_color = "#FFFF00"
            text_color = "#000000"
        else:
            res = "🟢 Low Risk"
            advice = "คำแนะนำทั่วไป: ให้สังเกตอาการด้วยตนเอง ไม่ต้องโทรตาม"
            bg_color = "#28A745"

        # แสดงสีแจ้งเตือนหน้าประเมิน
        st.markdown(f"""
            <div style="background-color:{bg_color}; padding:40px; border-radius:10px; text-align:center; margin-top:20px; border: 2px solid #333;">
                <h1 style="color:{text_color}; margin:0; font-size:45px;">{res}</h1>
                <p style="color:{text_color}; font-size:22px; font-weight:bold; white-space: pre-line;">{advice}</p>
                <p style="color:{text_color}; font-size:16px;">AI Score: {prob:.4f}</p>
            </div>
        """, unsafe_allow_html=True)

        # บันทึกลง Google Sheets
        current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame([{
            "Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input, 
            "loc_right": loc_right, "BX": int(bx_in), "Cold_Poly": int(cold_in), 
            "Hot_Poly": int(hot_in), "EMR": int(emr_in), "Clip": int(clip_in), "Medication": int(med_in), 
            "Surgery": int(surg_in), "Radiation": int(rad_in), "Chemo": int(chemo_in), "Risk_Level": res, "Advice": advice
        }])
        
        try:
            old_data = get_data()
            updated_df = pd.concat([old_data, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast(f"บันทึกข้อมูลสำเร็จเมื่อ {current_time}")
        except:
            st.error("Error: ไม่สามารถบันทึกข้อมูลลง Google Sheets ได้ (โปรดตรวจสอบการเชื่อมต่อ)")

with tab2:
    st.subheader("📊 แดชบอร์ดสรุปผลรายวัน (ระบบคัดกรอง)")
    df = get_data()
    if not df.empty:
        # กรองข้อมูลวันนี้
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        today_date = datetime.now(tz_th).date()
        today_df = df[df['Timestamp'].dt.date == today_date]
        
        # แสดง Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสวันนี้", len(today_df))
        m2.metric("🔴 แดง", len(today_df[today_df['Risk_Level'].str.contains("🔴")]))
        m3.metric("🟡 เหลือง", len(today_df[today_df['Risk_Level'].str.contains("🟡")]))
        m4.metric("🟢 เขียว", len(today_df[today_df['Risk_Level'].str.contains("🟢")]))
        
        st.divider()
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.write("**สัดส่วนความเสี่ยงสะสม**")
            risk_counts = df['Risk_Level'].value_counts().reset_index()
            risk_counts.columns = ['Risk', 'Count']
            fig = px.pie(risk_counts, values='Count', names='Risk', color='Risk',
                         color_discrete_map={
                             "🔴 High Risk": "#FF4B4B", 
                             "🟡 Moderate Risk": "#FFFF00", 
                             "🟢 Low Risk": "#28A745"
                         })
            st.plotly_chart(fig, use_container_width=True)
            
        with c_right:
            st.write("**📋 ตารางบันทึกข้อมูล**")
            st.dataframe(df[['Timestamp', 'Case_ID', 'Risk_Level', 'Advice']].sort_values(by="Timestamp", ascending=False), 
                         use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")
