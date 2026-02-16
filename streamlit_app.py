import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(layout="wide", page_title="NCI BleedGuard-AI", page_icon="🩺")

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดสมอง AI ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
    if hasattr(model, 'feature_names_in_'):
        model_features = model.feature_names_in_.tolist()
    else:
        model_features = ['Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Radiation', 'Chemo', 'Surgery', 'BX', 'Cold_Poly', 'Hot_Poly', 'EMR', 'Sex']
except:
    st.error("❌ ไม่พบไฟล์โมเดล bleedguard_model.pkl")

# --- 4. ฟังก์ชันดึงเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 5. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบคัดกรองความเสี่ยงภาวะเลือดออก สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. Dashboard วิเคราะห์ข้อมูล ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Risk_Level']).copy()
        with st.expander("📊 ดูสถิติภาพรวม (Dashboard)", expanded=False):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("เคสสะสม", len(df_clean))
            m2.metric("🔴 High", len(df_clean[df_clean['Risk_Level'].str.contains('High', na=False)]))
            m3.metric("🟡 Moderate", len(df_clean[df_clean['Risk_Level'].str.contains('Moderate', na=False)]))
            m4.metric("🟢 Low", len(df_clean[df_clean['Risk_Level'].str.contains('Low', na=False)]))
            
            g1, g2 = st.columns(2)
            with g1:
                fig_pie = px.pie(df_clean, names='Risk_Level', color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'})
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                fig_bar = px.bar(df_clean, x='Method', color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'})
                st.plotly_chart(fig_bar, use_container_width=True)
except:
    df_existing = pd.DataFrame()

# --- 7. ฟอร์มบันทึกข้อมูล ---
st.subheader("📝 บันทึกข้อมูลคนไข้")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่ง", ["ขวา", "ซ้าย"])
    with c2:
        med = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
        rad = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนแสดงผลลัพธ์ (ค้างหน้าจอ) ---
if submit:
    # เตรียมข้อมูลสำหรับ AI
    raw_for_ai = {
        'Age': age, 'Size_cm': size, 'Loc_Right': 1 if loc == "ขวา" else 0,
        'Med_Risk': 1 if med == "มี" else 0, 'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 0, 'Surgery': 0, 'BX': 1 if "BX" in method else 0,
        'Cold_Poly': 1 if "Cold" in method else 0, 'Hot_Poly': 1 if "Hot" in method else 0,
        'EMR': 1 if "EMR" in method else 0, 'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    input_df = pd.DataFrame([raw_for_ai])
    for col in model_features:
        if col not in input_df.columns: input_df[col] = 0
    input_df = input_df[model_features]

    try:
        prob = model.predict_proba(input_df)[0][1]
        clin_risk = "High" if (size >= 2.0 or clip == "มี" or method == "EMR") else "Normal"

        # แบ่งกลุ่มตาม Threshold 0.3 และ 0.5
        if clin_risk == "High" or prob >= 0.5:
            risk_text, color, icon, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            advice = "เฝ้าระวังใกล้ชิดในหน่วยงาน, วัด VS ทุก 15-30 นาที, นัด Follow-up ทันทีหากมีอาการ"
            st_func = st.error
        elif prob >= 0.3:
            risk_text, color, icon, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            advice = "สังเกตอาการที่บ้านอย่างใกล้ชิด, เลี่ยงยกของหนัก 3-5 วัน, โทรติดตามอาการภายใน 24 ชม."
            st_func = st.warning
        else:
            risk_text, color, icon, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            advice = "ดูแลตามมาตรฐานการพยาบาลปกติหลังส่องกล้อง, เริ่มอาหารอ่อนได้เมื่อฟื้นตัว"
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

        # การแสดงผลลัพธ์แบบค้างหน้าจอ
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {color}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{icon}</div>
                <h1 style="color: {color}; margin: 10px 0;">{risk_text}</h1>
                <p style="color: {color}; font-size: 1.2rem;">
                    <b>AI Probability Score:</b> {prob:.4f}<br>
                    <b>เวลาที่บันทึก:</b> {timestamp}
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("") # เว้นวรรค
        st_func(f"📋 **คำแนะนำทางการพยาบาล:** {advice}")
        
        st.info("💡 ข้อมูลถูกบันทึกลง Google Sheets และ Dashboard เรียบร้อยแล้ว (กด Refresh หน้าเว็บเพื่ออัปเดตกราฟ)")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
