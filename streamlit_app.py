import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. การตั้งค่าหน้าจอ (Wide Mode เพื่อพรีเซนต์สวยๆ) ---
st.set_page_config(layout="wide", page_title="NCI BleedGuard-AI", page_icon="🩺")

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดสมอง AI (.pkl) ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
    if hasattr(model, 'feature_names_in_'):
        model_features = model.feature_names_in_.tolist()
    else:
        # กรณีหาชื่อตัวแปรไม่เจอ ให้ใช้ลำดับมาตรฐาน
        model_features = ['Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Radiation', 'Chemo', 'Surgery', 'BX', 'Cold_Poly', 'Hot_Poly', 'EMR', 'Sex']
except:
    st.error("❌ ไม่พบไฟล์โมเดล bleedguard_model.pkl กรุณาตรวจสอบบน GitHub")

# --- 4. ฟังก์ชันดึงเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 5. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบสนับสนุนการตัดสินใจเพื่อความปลอดภัยของผู้ป่วยสถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. Dashboard วิเคราะห์ข้อมูล ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Risk_Level']).copy()
        with st.expander("📊 ดูสถิติภาพรวม (Dashboard)", expanded=False):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("เคสสะสมทั้งหมด", len(df_clean))
            m2.metric("🔴 High Risk", len(df_clean[df_clean['Risk_Level'].str.contains('High', na=False)]))
            m3.metric("🟡 Moderate Risk", len(df_clean[df_clean['Risk_Level'].str.contains('Moderate', na=False)]))
            m4.metric("🟢 Low Risk", len(df_clean[df_clean['Risk_Level'].str.contains('Low', na=False)]))
            
            g1, g2 = st.columns(2)
            with g1:
                fig_pie = px.pie(df_clean, names='Risk_Level', color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'},
                                 hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                fig_bar = px.bar(df_clean, x='Method', color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'})
                st.plotly_chart(fig_bar, use_container_width=True)
except:
    df_existing = pd.DataFrame()

# --- 7. ฟอร์มบันทึกข้อมูล (ตัวเลือกครบตามสั่ง) ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่งติ่งเนื้อ", ["ขวา (Right)", "ซ้าย (Left)"])
        med = st.radio("ยากลุ่มเสี่ยง (ละลายลิ่มเลือด)", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad = st.radio("ประวัติฉายแสง (Radiation)", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด (Chemo)", ["ไม่มี", "มี"], horizontal=True)
        surgery = st.radio("ประวัติผ่าตัดช่องท้อง (Surgery)", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ (Procedure)", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป (Hemoclip)", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนแสดงผลลัพธ์แบบค้างหน้าจอและ Emoji อารมณ์ ---
if submit:
    # เตรียมข้อมูลส่งให้ AI
    raw_for_ai = {
        'Age': age, 'Size_cm': size, 'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0, 'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0, 'Surgery': 1 if surgery == "มี" else 0, 
        'BX': 1 if "BX" in method else 0, 'Cold_Poly': 1 if "Cold" in method else 0, 
        'Hot_Poly': 1 if "Hot" in method else 0, 'EMR': 1 if "EMR" in method else 0, 
        'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    input_df = pd.DataFrame([raw_for_ai])
    for col in model_features:
        if col not in input_df.columns: input_df[col] = 0
    input_df = input_df[model_features]

    try:
        prob = model.predict_proba(input_df)[0][1]
        clin_risk = "High" if (size >= 2.0 or clip == "มี" or method == "EMR") else "Normal"

        # แบ่งกลุ่มตาม Threshold 0.1 และ 0.5 พร้อมคำแนะนำใหม่ตามสั่ง
        if clin_risk == "High" or prob >= 0.5:
            risk_text, color, icon, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            advice = """
            **📋 แผนการพยาบาล (High Risk):**
            1. **ติดตามอย่างใกล้ชิด:** ในช่วง 24, 48 และ 72 ชั่วโมง (โทรติดตามอาการ/นัดตรวจ)
            2. **คำแนะนำกลับบ้าน:** งดออกกำลังกายและยกของหนัก 7-14 วัน, ทานอาหารอ่อน, สังเกตอาการปวดท้องหรือถ่ายเป็นเลือด หากผิดปกติให้มา รพ. ทันที
            """
            st_func = st.error
        elif prob >= 0.1: # ปรับเป็น 0.1 เพื่อให้กลุ่ม Moderate แสดงผลง่ายขึ้น
            risk_text, color, icon, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            advice = """
            **📋 แผนการพยาบาล (Moderate Risk):**
            1. **ติดตามอาการ:** ในวันที่ 1, 3 และ 7 หลังทำหัตถการ (Post-op Call)
            2. **คำแนะนำกลับบ้าน:** สังเกตลักษณะอุจจาระและอาการปวดท้องอย่างใกล้ชิด, เลี่ยงยกของหนัก 3-5 วัน
            """
            st_func = st.warning
        else:
            risk_text, color, icon, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            advice = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ, เริ่มอาหารอ่อนได้เมื่อฟื้นตัวดี, สังเกตอาการทั่วไป"
            st_func = st.success

        # บันทึกเวลาไทย
        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")

        # บันทึกลง Google Sheets
        new_data = pd.DataFrame([{
            "Timestamp": timestamp, "Age": age, "Sex": sex_input, "Size_cm": size,
            "Clinical_Risk": clin_risk, "AI_Score": round(float(prob), 4),
            "Risk_Level": risk_text, "Method": method
        }])
        updated_df = pd.concat([df_existing, new_data], ignore_index=True)
        conn.update(data=updated_df)

        # การแสดงผลลัพธ์ (ค้างหน้าจอ)
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {color}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{icon}</div>
                <h1 style="color: {color}; margin: 10px 0;">{risk_text}</h1>
                <p style="color: {color}; font-size: 1.2rem;">
                    <b>AI Probability Score:</b> {prob:.4f} | <b>เวลาที่บันทึก:</b> {timestamp}
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("") 
        st_func(advice)
        st.info("💡 ข้อมูลถูกบันทึกลงระบบและ Dashboard เรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
