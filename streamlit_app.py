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
    # รายชื่อฟีเจอร์ที่สะกดตรงตามที่โมเดลของคุณใช้ตอน Train (อิงจาก Error Message)
    model_features = [
        'Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Surgery', 
        'Radiation', 'Chemo', 'BX', 'Cold Polypectomy', 'Hot Polypectomy', 
        'EMR', 'Sex', 'Prob_Risk'
    ]
except Exception as e:
    st.error(f"❌ โหลดโมเดลไม่สำเร็จ: {e}")

# --- 4. ฟังก์ชันดึงเวลาไทย ---
def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

# --- 5. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI (Endo-STAT)</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบสนับสนุนการตัดสินใจ พัฒนาโดยพยาบาลส่องกล้อง สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. แดชบอร์ด (Dashboard) แสดงผลสถิติภาพรวม ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Clinical_Risk']).copy()
        
        st.subheader("📊 สถิติภาพรวมการคัดกรองความเสี่ยง")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสสะสมทั้งหมด", f"{len(df_clean)} ราย")
        m2.metric("🔴 High Risk", len(df_clean[df_clean['Clinical_Risk'].str.contains('High', na=False)]))
        m3.metric("🟡 Moderate Risk", len(df_clean[df_clean['Clinical_Risk'].str.contains('Moderate', na=False)]))
        m4.metric("🟢 Low Risk", len(df_clean[df_clean['Clinical_Risk'].str.contains('Low', na=False)]))
        
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df_clean, names='Clinical_Risk', color='Clinical_Risk',
                             color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'},
                             hole=0.4, title="สัดส่วนระดับความเสี่ยงสะสม")
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            fig_bar = px.bar(df_clean, x='Method', color='Clinical_Risk',
                             color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟡 Moderate Risk':'#FBC02D', '🟢 Low Risk':'#00CC96'},
                             title="หัตถการแยกตามความเสี่ยง")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        df_existing = pd.DataFrame()
except:
    df_existing = pd.DataFrame()

st.divider()

# --- 7. ฟอร์มบันทึกข้อมูล (Input ตัวเลือกครบถ้วน) ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่ง", ["ขวา (Right)", "ซ้าย (Left)"])
        med = st.radio("ยากลุ่มเสี่ยง (ละลายลิ่มเลือด)", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad = st.radio("ประวัติฉายแสง (Radiation)", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด (Chemo)", ["ไม่มี", "มี"], horizontal=True)
        surgery = st.radio("ประวัติผ่าตัดช่องท้อง (Surgery)", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ (Procedure)", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป (Hemoclip)", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนประมวลผล (อิงตามโมเดล AI 100%) ---
if submit:
    # เตรียมข้อมูลให้ตรงตามฟีเจอร์ในโมเดล
    input_data = {
        'Age': age, 'Size_cm': size, 'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0, 'Surgery': 1 if surgery == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0, 'Chemo': 1 if chemo == "มี" else 0,
        'BX': 1 if "BX" in method else 0, 'Cold Polypectomy': 1 if "Cold" in method else 0,
        'Hot Polypectomy': 1 if "Hot" in method else 0, 'EMR': 1 if "EMR" in method else 0,
        'Sex': 1 if sex_input == "ชาย" else 0, 'Prob_Risk': 0
    }
    
    # บังคับชื่อคอลัมน์และลำดับให้ตรงตามโมเดลเป๊ะๆ
    input_df = pd.DataFrame([input_data]).reindex(columns=model_features, fill_value=0)

    try:
        # ทำนายผลจากโมเดลที่ฝึกมาจริง
        prob = model.predict_proba(input_df)[0][1]
        
        # กฎเกณฑ์ทางคลินิก (High Risk)
        is_high_clin = (size >= 2.0 or clip == "มี" or method == "EMR")

        # --- การตัดสินใจ (Decision Logic อิงตามคะแนนโมเดล) ---
        if is_high_clin or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            adv = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำกลับบ้านแบบเข้มงวด"
            st_func = st.error
        elif prob >= 0.05: # ปรับ Threshold อิงตามผลการทดสอบจริงเพื่อให้เห็นกลุ่ม Moderate
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            adv = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 และสังเกตอุจจาระ/ปวดท้อง"
            st_func = st.warning
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ"
            st_func = st.success

        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")

        # แสดงผลลัพธ์ค้างหน้าจอ
        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {col}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{ico}</div>
                <h1 style="color: {col}; margin: 10px 0;">{res}</h1>
                <p style="color: {col}; font-size: 1.2rem;">
                    <b>AI Model Score:</b> {prob:.4f} | <b>Timestamp:</b> {timestamp}
                </p>
            </div>
        """, unsafe_allow_html=True)
        st_func(adv)
        
        # บันทึกลง Google Sheets
        new_row = pd.DataFrame([{"Timestamp": timestamp, "Clinical_Risk": res, "AI_Score": prob, "Method": method}])
        df_all = pd.concat([df_existing, new_row], ignore_index=True)
        conn.update(data=df_all)
        st.info("💡 ข้อมูลถูกบันทึกเรียบร้อยแล้ว กราฟจะอัปเดตในการเข้าถึงครั้งถัดไป")

    except Exception as e:
        st.error(f"Error during prediction: {e}")
