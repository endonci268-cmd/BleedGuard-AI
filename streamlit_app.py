import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz 
import plotly.express as px

# --- 1. SET UP & TIMEZONE ---
st.set_page_config(page_title="NCI BleedGuard-AI", layout="wide")
tz_th = pytz.timezone('Asia/Bangkok') 

st.markdown("""
    <div style="text-align: center;">
        <h1 style="color: #B22222;">🛡️ NCI BleedGuard-AI: The Final Sentinel</h1>
        <p style="font-size: 18px;">สถาบันมะเร็งแห่งชาติ | ระบบคัดกรองความเสี่ยงอัตโนมัติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 2. CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

# --- 3. ML LOGIC ---
def predict_bleeding(data):
    # ฉุกเฉิน/ติดต่อแผนก
    emergency_contact = "📞 สงสัยหรือมีอาการฉุกเฉิน 02-2026888 ต่อ 2326 หรือ Line"
    
    if data['clip'] == 1:
        return "🔴 High Risk", f"📞 ต้องโทรติดตาม 24, 48, 72 ชม. (พบการติด Hemoclip หน้างาน)\n\n{emergency_contact}", "#FF4B4B", "white"
    
    intercept = -2.4
    weights = {'age': 0.012, 'sex_male': 0.658, 'size': 2.429, 'emr': 1.044, 'hot_poly': 0.850, 
               'cold_poly': 0.074, 'rad': 0.704, 'chemo': 0.631, 'med': -0.606, 'bx': -3.987, 'surgery': 0.618, 'loc_right': 0.95}
    
    score = intercept
    score += data['age'] * weights['age']
    score += (weights['sex_male'] if data['sex'] == "ชาย" else 0)
    score += data['size'] * weights['size']
    score += (1 if data['emr'] else 0) * weights['emr']
    score += (1 if data['hot_poly'] else 0) * weights['hot_poly']
    score += (1 if data['rad'] else 0) * weights['rad']
    score += (1 if data['chemo'] else 0) * weights['chemo']
    score += (1 if data['med'] else 0) * weights['med']
    score += (1 if data['bx'] else 0) * weights['bx']
    score += (1 if data['surgery'] else 0) * weights['surgery']
    if data['loc_side'] == "Right Side": score += weights['loc_right']

    if score >= -2.4:
        return "🟡 Moderate Risk", f"📞 โทรติดตามวันที่ 1 และ 3 (กลุ่มเฝ้าระวังพิเศษ)\n\n{emergency_contact}", "#FFFF00", "black"
    else:
        if data['rad'] == 1 or data['chemo'] == 1:
            return "🟡 Moderate Risk (Oncology Guard)", f"📞 โทรติดตามวันที่ 1 (เฝ้าระวังประวัติรักษามะเร็ง)\n\n{emergency_contact}", "#FFFF00", "black"
        return "🟢 Low Risk", f"สังเกตอาการตามปกติ\n\n{emergency_contact}", "#28A745", "white"

# --- 4. UI TABS ---
tab1, tab2 = st.tabs(["📋 ประเมินเคสใหม่", "📊 แดชบอร์ดวิจัย"])

with tab1:
    with st.form(key="nci_final_v9"):
        st.subheader("1. ข้อมูลพื้นฐาน")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        case_id_input = c1.text_input("Case ID")
        age_input = c2.number_input("อายุ (ปี)", min_value=0, value=60)
        sex_input = c3.selectbox("เพศ", ["ชาย", "หญิง"])
        size_input = c4.number_input("ขนาดติ่งเนื้อ (cm)", min_value=0.0, step=0.1, value=0.5)
        loc_side = st.radio("**ตำแหน่งติ่งเนื้อ (loc_right):**", ["Right Side", "Left Side"], horizontal=True)

        st.divider()
        st.subheader("2. หัตถการและปัจจัยเสี่ยง")
        p1, p2, p3, p4, p5 = st.columns(5)
        bx_in, cold_in, hot_in, emr_in, clip_in = p1.checkbox("BX"), p2.checkbox("Cold Poly"), p3.checkbox("Hot Poly"), p4.checkbox("EMR"), p5.checkbox("Clip")
        r1, r2, r3, r4 = st.columns(4)
        med_in, surg_in, rad_in, chemo_in = r1.checkbox("ยาละลายลิ่มเลือด"), r2.checkbox("ผ่าตัด"), r3.checkbox("ฉายแสง"), r4.checkbox("เคมี")

        submitted = st.form_submit_button("วิเคราะห์และบันทึกข้อมูล")

    if submitted:
        if not case_id_input:
            st.error("กรุณากรอก Case ID")
        else:
            input_data = {'age': age_input, 'sex': sex_input, 'size': size_input, 'loc_side': loc_side,
                          'bx': bx_in, 'cold_poly': cold_in, 'hot_poly': hot_in, 'emr': emr_in, 
                          'clip': clip_in, 'med': med_in, 'surgery': surg_in, 'rad': rad_in, 'chemo': chemo_in}
            res, advice, bg_color, text_color = predict_bleeding(input_data)
            
            # แสดงสีแจ้งเตือนหน้าประเมิน
            st.markdown(f"""
                <div style="background-color:{bg_color}; padding:40px; border-radius:10px; text-align:center; margin-top:20px; border: 2px solid #333;">
                    <h1 style="color:{text_color}; margin:0; font-size:45px;">{res}</h1>
                    <p style="color:{text_color}; font-size:22px; font-weight:bold; white-space: pre-line;">{advice}</p>
                </div>
            """, unsafe_allow_html=True)

            current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{"Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input, 
                                     "loc_right": 1 if loc_side == "Right Side" else 0, "BX": int(bx_in), "Cold_Poly": int(cold_in), 
                                     "Hot_Poly": int(hot_in), "EMR": int(emr_in), "Clip": int(clip_in), "Medication": int(med_in), 
                                     "Surgery": int(surg_in), "Radiation": int(rad_in), "Chemo": int(chemo_in), "Risk_Level": res, "Advice": advice}])
            try:
                conn.update(worksheet="Sheet1", data=pd.concat([get_data(), new_row], ignore_index=True))
                st.info(f"บันทึกสำเร็จ: {current_time}")
            except:
                st.error("Error: ไม่สามารถเชื่อมต่อ Google Sheets ได้")

with tab2:
    st.subheader("📊 แดชบอร์ดสรุปผลรายวัน (ระบบคัดกรอง)")
    df = get_data()
    if not df.empty:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        today_df = df[df['Timestamp'].dt.date == datetime.now(tz_th).date()]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสวันนี้", len(today_df)); m2.metric("🔴 แดง", len(today_df[today_df['Risk_Level'].str.contains("🔴")])); m3.metric("🟡 เหลือง", len(today_df[today_df['Risk_Level'].str.contains("🟡")])); m4.metric("🟢 เขียว", len(today_df[today_df['Risk_Level'].str.contains("🟢")]))
        
        st.divider()
        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.write("**สัดส่วนความเสี่ยงสะสม**")
            risk_counts = df['Risk_Level'].value_counts().reset_index()
            risk_counts.columns = ['Risk', 'Count']
            fig = px.pie(risk_counts, values='Count', names='Risk', color='Risk', color_discrete_map={"🔴 High Risk": "#FF4B4B", "🟡 Moderate Risk": "#FFFF00", "🟡 Moderate Risk (Oncology Guard)": "#FFFF00", "🟢 Low Risk": "#28A745"})
            st.plotly_chart(fig, use_container_width=True)
        with c_right:
            st.write("**📋 ตารางบันทึกข้อมูล**")
            st.dataframe(df[['Timestamp', 'Case_ID', 'Risk_Level', 'Advice']].sort_values(by="Timestamp", ascending=False), use_container_width=True, hide_index=True)
