import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. การตั้งค่าหน้าจอ (Wide Mode เพื่อให้กราฟสวย) ---
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
    st.error("❌ ไม่พบไฟล์ bleedguard_model.pkl กรุณาตรวจสอบบน GitHub")

# --- 4. ฟังก์ชันดึงเวลาไทย (Asia/Bangkok) ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 5. ส่วนหัวโปรแกรม ---
st.markdown(f"""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI Dashboard</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบสนับสนุนการคัดกรองความเสี่ยงภาวะเลือดออก สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. Dashboard วิเคราะห์ข้อมูล ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Risk_Level']).copy()
        
        # --- Metrics หลัก ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสสะสมทั้งหมด", f"{len(df_clean)} ราย")
        
        red_c = len(df_clean[df_clean['Risk_Level'].str.contains('High', na=False)])
        m2.metric("🔴 High Risk", f"{red_c} ราย", delta=f"{(red_c/len(df_clean)*100):.1f}%", delta_color="inverse")
        
        yel_c = len(df_clean[df_clean['Risk_Level'].str.contains('Moderate', na=False)])
        m3.metric("🟡 Moderate Risk", f"{yel_c} ราย")
        
        gre_c = len(df_clean[df_clean['Risk_Level'].str.contains('Low', na=False)])
        m4.metric("🟢 Low Risk", f"{gre_c} ราย")

        # --- กราฟวิเคราะห์ ---
        g1, g2 = st.columns(2)
        with g1:
            st.write("### 🥧 สัดส่วนระดับความเสี่ยง")
            fig_pie = px.pie(df_clean, names='Risk_Level', 
                             color='Risk_Level',
                             color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'},
                             hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        with g2:
            st.write("### 📊 หัตถการแยกตามความเสี่ยง")
            fig_bar = px.bar(df_clean, x='Method', color='Risk_Level',
                             color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'})
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("💡 ยังไม่มีข้อมูลในระบบ เริ่มบันทึกข้อมูลด้านล่าง")
except Exception as e:
    st.warning(f"รอการเชื่อมต่อฐานข้อมูล... ({e})")
    df_existing = pd.DataFrame()

st.divider()

# --- 7. ฟอร์มบันทึกข้อมูลคนไข้ ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("main_form", clear_on_submit=True):
    f1, f2 = st.columns(2)
    with f1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่งติ่งเนื้อ", ["ขวา", "ซ้าย"])
    
    with f2:
        med = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
        rad = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป", ["ไม่มี", "มี"], horizontal=True)

    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนประมวลผล (Logic แดง-เหลือง-เขียว) ---
if submit:
    # เตรียมข้อมูลส่งให้ AI
    raw_for_ai = {
        'Age': age, 'Size_cm': size, 'Loc_Right': 1 if loc == "ขวา" else 0,
        'Med_Risk': 1 if med == "มี" else 0, 'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0, 'Surgery': 0, 
        'BX': 1 if "BX" in method else 0, 'Cold_Poly': 1 if "Cold" in method else 0,
        'Hot_Poly': 1 if "Hot" in method else 0, 'EMR': 1 if "EMR" in method else 0,
        'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    # กันพัง: ปรับชื่อคอลัมน์ให้ตรงใจ AI
    input_df = pd.DataFrame([raw_for_ai])
    for col in model_features:
        if col not in input_df.columns: input_df[col] = 0
    input_df = input_df[model_features]

    try:
        # AI คำนวณ
        prob = model.predict_proba(input_df)[0][1]
        
        # Hybrid Logic (3 สี)
        clin_risk = "High" if (size >= 2.0 or clip == "มี" or method == "EMR") else "Normal"
        
        if clin_risk == "High" or prob >= 0.7:
            risk_text, b_col, t_col, status_box = "🔴 High Risk", "#FFD2D2", "#990000", st.error
            advice = "**⚠️ คำแนะนำ:** เฝ้าระวังใกล้ชิด, วัด Vital Signs บ่อยครั้ง, งดออกกำลังกายหนัก 7 วัน"
        elif prob >= 0.4:
            risk_text, b_col, t_col, status_box = "🟡 Moderate Risk", "#FFF9C4", "#827717", st.warning
            advice = "**⚠️ คำแนะนำ:** สังเกตอาการถ่ายดำ/ปวดท้องที่บ้าน, เลี่ยงยกของหนัก 3-5 วัน"
        else:
            risk_text, b_col, t_col, status_box = "🟢 Low Risk", "#D2FFD2", "#006600", st.success
            advice = "**✅ คำแนะนำ:** ปฏิบัติตัวตามมาตรฐานปกติหลังส่องกล้อง"

        # แสดงผล
        st.balloons()
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {t_col}; padding: 20px; border-radius: 15px; text-align: center;">
                <h1 style="color: {t_col}; margin: 0;">{risk_text}</h1>
                <p style="color: {t_col};">AI Score: <b>{prob:.4f}</b> | Clinical Triage: <b>{clin_risk}</b></p>
            </div>
        """, unsafe_allow_html=True)
        status_box(advice)

        # บันทึกลง Sheets
        now_th = get_thailand_time()
        new_data = pd.DataFrame([{
            "Timestamp": now_th.strftime("%Y-%m-%d %H:%M:%S"),
            "Age": age, "Sex": sex_input, "Size_cm": size, "Loc_Right": 1 if loc == "ขวา" else 0,
            "Med_Risk": 1 if med == "มี" else 0, "Surgery": 0, "Radiation": 1 if rad == "มี" else 0,
            "Chemo": 1 if chemo == "มี" else 0, "BX": 1 if "BX" in method else 0,
            "Cold_Poly": 1 if "Cold" in method else 0, "Hot_Poly": 1 if "Hot" in method else 0,
            "EMR": 1 if method == "EMR" else 0, "Clinical_Risk": clin_risk,
            "AI_Score": round(float(prob), 4), "Risk_Level": risk_text, "Method": method
        }])
        
        updated_df = pd.concat([df_existing, new_data], ignore_index=True)
        conn.update(data=updated_df)
        st.success("✅ บันทึกข้อมูลเรียบร้อย!")
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
