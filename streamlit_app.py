import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SET UP ---
st.set_page_config(page_title="NCI BleedGuard-AI", layout="wide")

st.markdown("""
    <div style="text-align: center;">
        <h1 style="color: #B22222;">🛡️ NCI BleedGuard-AI: The Final Sentinel</h1>
        <p style="font-size: 18px;">สถาบันมะเร็งแห่งชาติ | เป้าหมาย Sensitivity 91%</p>
    </div>
""", unsafe_allow_html=True)

# --- 2. CONNECTION (บังคับดึงข้อมูลสดใหม่) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # ใช้ ttl=0 เพื่อให้ดึงข้อมูลใหม่จาก Google Sheets ทุกครั้ง ไม่ใช้ค่าเก่าในความจำ
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame()

# --- 3. ML LOGIC (Drop Case ID) ---
def predict_bleeding(data):
    if data['clip'] == 1:
        return "🔴 High Risk", "📞 ต้องโทรติดตาม 24, 48, 72 ชม. (พบการติด Hemoclip หน้างาน)", "#FFD2D2"
    
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

    if score >= -2.4:
        return "🟡 Moderate Risk", "📞 โทรติดตามวันที่ 1 และ 3 (กลุ่มเฝ้าระวังพิเศษ)", "#FFF9C4"
    else:
        if data['rad'] == 1 or data['chemo'] == 1:
            return "🟡 Moderate Risk (Oncology Guard)", "📞 โทรติดตามวันที่ 1 (เฝ้าระวังประวัติรักษามะเร็ง)", "#FFF9C4"
        return "🟢 Low Risk", "แนะนำอาหารอ่อน สังเกตอาการตามปกติ", "#D2FFD2"

# --- 4. UI TABS ---
tab1, tab2 = st.tabs(["📋 ประเมินเคสใหม่", "📊 แดชบอร์ดวิจัย"])

with tab1:
    with st.form(key="nci_final_v3"):
        st.subheader("1. ข้อมูลพื้นฐาน")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        case_id_input = c1.text_input("Case ID")
        age_input = c2.number_input("อายุ (ปี)", min_value=0, max_value=120, value=60)
        sex_input = c3.selectbox("เพศ", ["ชาย", "หญิง"])
        size_input = c4.number_input("ขนาดติ่งเนื้อ (cm)", min_value=0.0, step=0.1, value=0.5)

        st.divider()
        st.subheader("2. หัตถการและปัจจัยเสี่ยง")
        p1, p2, p3, p4, p5 = st.columns(5)
        bx_in = p1.checkbox("Biopsy (BX)")
        cold_in = p2.checkbox("Cold Poly")
        hot_in = p3.checkbox("Hot Poly")
        emr_in = p4.checkbox("EMR")
        clip_in = p5.checkbox("ติด Hemoclip")

        r1, r2, r3, r4 = st.columns(4)
        med_in = r1.checkbox("ยาละลายลิ่มเลือด")
        surg_in = r2.checkbox("ประวัติผ่าตัด")
        rad_in = r3.checkbox("ประวัติฉายแสง")
        chemo_in = r4.checkbox("ประวัติเคมีบำบัด")

        submitted = st.form_submit_button("วิเคราะห์และบันทึกข้อมูล")

    if submitted:
        if not case_id_input:
            st.error("กรุณากรอก Case ID")
        else:
            input_data = {
                'age': age_input, 'sex': sex_input, 'size': size_input, 
                'bx': bx_in, 'cold_poly': cold_in, 'hot_poly': hot_in, 
                'emr': emr_in, 'clip': clip_in, 'med': med_in,
                'surgery': surg_in, 'rad': rad_in, 'chemo': chemo_in
            }
            res, advice, color = predict_bleeding(input_data)
            
            # สร้าง Timestamp ปัจจุบัน
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            new_row = pd.DataFrame([{
                "Timestamp": current_time,
                "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input,
                "BX": int(bx_in), "Cold_Poly": int(cold_in), "Hot_Poly": int(hot_in),
                "EMR": int(emr_in), "Clip": int(clip_in), "Medication": int(med_in),
                "Surgery": int(surg_in), "Radiation": int(rad_in), "Chemo": int(chemo_in),
                "Risk_Level": res, "Advice": advice
            }])
            
            try:
                # ดึงข้อมูลเก่า (สดใหม่) มาต่อกับข้อมูลใหม่
                df_old = get_data()
                df_new = pd.concat([df_old, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_new)
                
                st.markdown(f"<div style='background-color:{color}; padding:20px; border-radius:10px; text-align:center; border: 2px solid #B22222;'>"
                            f"<h2 style='color:black;'>{res}</h2><p style='color:black;'>{advice}</p></div>", unsafe_allow_html=True)
                st.success(f"บันทึกสำเร็จเมื่อเวลา {current_time}")
                # บังคับให้หน้าเว็บโหลดใหม่เพื่ออัปเดตตัวเลข
                st.rerun()
            except Exception as e:
                st.error("บันทึกล้มเหลว: ตรวจสอบการเชื่อมต่อ Google Sheets")

with tab2:
    st.subheader("📊 แดชบอร์ดวิจัย (อัปเดต Real-time)")
    
    # เพิ่มปุ่มกดรีเฟรชข้อมูลเองด้วย
    if st.button("🔄 อัปเดตข้อมูลล่าสุด"):
        st.rerun()

    df = get_data()
    
    if not df.empty:
        # 1. แก้ไขเรื่องวันที่ (Timestamp)
        # ตรวจสอบว่าคอลัมน์ Timestamp มีข้อมูลจริง
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df['Date_Only'] = df['Timestamp'].dt.date
        today = datetime.now().date()
        df_today = df[df['Date_Only'] == today]
        
        # 2. จำนวนยอด (Metrics)
        st.write(f"📅 ข้อมูลวันที่: {today.strftime('%d/%m/%Y')}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสทั้งหมดวันนี้", len(df_today))
        m2.metric("🔴 แดง", len(df_today[df_today['Risk_Level'].str.contains("🔴")]))
        m3.metric("🟡 เหลือง", len(df_today[df_today['Risk_Level'].str.contains("🟡")]))
        m4.metric("🟢 เขียว", len(df_today[df_today['Risk_Level'].str.contains("🟢")]))

        st.divider()

        # 3. กราฟ (Charts)
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.write("**สัดส่วนความเสี่ยง (สะสมทั้งหมด)**")
            # นับจำนวนแยกตาม Risk_Level มาทำกราฟ
            risk_stats = df['Risk_Level'].value_counts()
            st.bar_chart(risk_stats)
            
        with col_r:
            st.info(f"🎯 **Sensitivity Target:** 91%\n\n📉 **FN Target:** 3%")
            st.write(f"จำนวนเคสสะสมในฐานข้อมูล: {len(df)} ราย")

        st.divider()

        # 4. ตารางข้อมูล (Display)
        st.write("**📋 บันทึกล่าสุด (Timestamp ตรงตามจริง)**")
        # จัดรูปแบบ Timestamp ให้ดูง่ายในตาราง
        df_display = df[['Timestamp', 'Case_ID', 'Risk_Level', 'Advice']].copy()
        df_display['Timestamp'] = df_display['Timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(
            df_display.sort_values(by="Timestamp", ascending=False),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("ยังไม่มีข้อมูลบันทึกในระบบ")
