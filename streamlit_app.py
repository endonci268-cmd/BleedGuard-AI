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
        <p style="font-size: 18px;">สถาบันมะเร็งแห่งชาติ | รวมปัจจัยตำแหน่งติ่งเนื้อ (Location)</p>
    </div>
""", unsafe_allow_html=True)

# --- 2. CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

# --- 3. ML LOGIC (เพิ่ม Location Weight) ---
def predict_bleeding(data):
    if data['clip'] == 1:
        return "🔴 High Risk", "📞 ต้องโทรติดตาม 24, 48, 72 ชม. (พบการติด Hemoclip หน้างาน)", "red"
    
    # ML Weights (เพิ่ม Location Odds Ratio)
    intercept = -2.4
    weights = {
        'age': 0.012, 'sex_male': 0.658, 'size': 2.429, 'emr': 1.044, 
        'hot_poly': 0.850, 'cold_poly': 0.074, 'rad': 0.704, 'chemo': 0.631, 
        'med': -0.606, 'bx': -3.987, 'surgery': 0.618,
        'loc_right': 0.92  # ตัวอย่างน้ำหนักสำหรับ Right-side colon (Cecum/Ascending)
    }
    
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
    
    # คิดคะแนนตำแหน่งติ่งเนื้อ (ถ้าอยู่ด้านขวา เสี่ยงสูงกว่า)
    if data['location'] in ["Cecum", "Ascending", "Hepatic Flexure"]:
        score += weights['loc_right']

    if score >= -2.4:
        return "🟡 Moderate Risk", "📞 โทรติดตามวันที่ 1 และ 3 (กลุ่มเฝ้าระวังพิเศษ)", "yellow"
    else:
        if data['rad'] == 1 or data['chemo'] == 1:
            return "🟡 Moderate Risk (Oncology Guard)", "📞 โทรติดตามวันที่ 1 (เฝ้าระวังประวัติรักษามะเร็ง)", "yellow"
        return "🟢 Low Risk", "แนะนำอาหารอ่อน สังเกตอาการตามปกติ", "green"

# --- 4. UI TABS ---
tab1, tab2 = st.tabs(["📋 ประเมินเคสใหม่", "📊 แดชบอร์ดวิจัย"])

with tab1:
    with st.form(key="nci_master_v5"):
        st.subheader("1. ข้อมูลพื้นฐานและพยาธิสภาพ")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        case_id_input = c1.text_input("Case ID")
        age_input = c2.number_input("อายุ (ปี)", min_value=0, max_value=120, value=60)
        sex_input = c3.selectbox("เพศ", ["ชาย", "หญิง"])
        size_input = c4.number_input("ขนาดติ่งเนื้อ (cm)", min_value=0.0, step=0.1, value=0.5)

        # เพิ่มตำแหน่งติ่งเนื้อ
        st.markdown("**ตำแหน่งติ่งเนื้อ (Location):**")
        loc_col1, loc_col2 = st.columns(2)
        location_input = loc_col1.selectbox("เลือกตำแหน่ง", 
            ["Cecum", "Ascending", "Hepatic Flexure", "Transverse", "Splenic Flexure", "Descending", "Sigmoid", "Rectum"])

        st.divider()
        st.subheader("2. หัตถการและปัจจัยเสี่ยง")
        p1, p2, p3, p4, p5 = st.columns(5)
        bx_in, cold_in, hot_in, emr_in, clip_in = p1.checkbox("BX"), p2.checkbox("Cold Poly"), p3.checkbox("Hot Poly"), p4.checkbox("EMR"), p5.checkbox("Clip")
        
        r1, r2, r3, r4 = st.columns(4)
        med_in, surg_in, rad_in, chemo_in = r1.checkbox("ยาละลายลิ่มเลือด"), r2.checkbox("ผ่าตัด"), r3.checkbox("ฉายแสง"), r4.checkbox("เคมี")

        submitted = st.form_submit_button("วิเคราะห์และบันทึกข้อมูล")

    if submitted:
        if not case_id_input:
            st.error("กรุณากรอก Case ID ก่อนดำเนินการ")
        else:
            input_data = {
                'age': age_input, 'sex': sex_input, 'size': size_input, 'location': location_input,
                'bx': bx_in, 'cold_poly': cold_in, 'hot_poly': hot_in, 'emr': emr_in, 
                'clip': clip_in, 'med': med_in, 'surgery': surg_in, 'rad': rad_in, 'chemo': chemo_in
            }
            res, advice, color_type = predict_bleeding(input_data)
            
            # แสดงสีผลลัพธ์
            if color_type == "red":
                st.error(f"### {res}\n{advice}")
            elif color_type == "yellow":
                st.warning(f"### {res}\n{advice}")
            else:
                st.success(f"### {res}\n{advice}")

            # บันทึกข้อมูล (เพิ่มคอลัมน์ Location)
            current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, 
                "Size": size_input, "Location": location_input, # <--- เพิ่มตรงนี้
                "BX": int(bx_in), "Cold_Poly": int(cold_in), "Hot_Poly": int(hot_in), 
                "EMR": int(emr_in), "Clip": int(clip_in), "Medication": int(med_in), 
                "Surgery": int(surg_in), "Radiation": int(rad_in), "Chemo": int(chemo_in),
                "Risk_Level": res, "Advice": advice
            }])
            
            try:
                df_all = pd.concat([get_data(), new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_all)
                st.info(f"บันทึกข้อมูลสำเร็จเมื่อ {current_time}")
            except:
                st.error("เชื่อมต่อฐานข้อมูลล้มเหลว")

with tab2:
    st.subheader("📊 แดชบอร์ดวิจัย")
    df = get_data()
    if not df.empty:
        # Metrics รายวัน
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        today_df = df[df['Timestamp'].dt.date == datetime.now(tz_th).date()]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสวันนี้", len(today_df))
        m2.metric("🔴 แดง", len(today_df[today_df['Risk_Level'].str.contains("🔴")]))
        m3.metric("🟡 เหลือง", len(today_df[today_df['Risk_Level'].str.contains("🟡")]))
        m4.metric("🟢 เขียว", len(today_df[today_df['Risk_Level'].str.contains("🟢")]))

        st.divider()
        col_chart, col_data = st.columns([1, 1])
        with col_chart:
            # กราฟสีตรงตามระบบ
            risk_counts = df['Risk_Level'].value_counts().reset_index()
            risk_counts.columns = ['Risk', 'Count']
            fig = px.pie(risk_counts, values='Count', names='Risk', color='Risk', 
                         color_discrete_map={"🔴 High Risk": "#FF4B4B", "🟡 Moderate Risk": "#FFFF00", 
                                             "🟡 Moderate Risk (Oncology Guard)": "#FFFF00", "🟢 Low Risk": "#28A745"})
            st.plotly_chart(fig, use_container_width=True)
        with col_data:
            # โชว์ข้อมูลสำคัญ
            st.dataframe(df[['Timestamp', 'Case_ID', 'Location', 'Risk_Level', 'Advice']].sort_values(by="Timestamp", ascending=False), use_container_width=True, hide_index=True)
