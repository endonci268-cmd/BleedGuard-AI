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
    # ดึงชื่อฟีเจอร์ "ของจริง" จากตัวโมเดลมาเลย เพื่อป้องกันการพิมพ์ผิด
    if hasattr(model, 'feature_names_in_'):
        model_features = model.feature_names_in_.tolist()
    else:
        # ถ้าดึงไม่ได้ ให้ใช้ชื่อตามที่ Error แจ้งมา (พยายามให้ตรงที่สุด)
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
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบสนับสนุนการตัดสินใจเพื่อความปลอดภัยของผู้ป่วย สถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. แดชบอร์ด (Dashboard) ---
try:
    df_existing = conn.read(ttl=0)
    if df_existing is not None and not df_existing.empty:
        df_clean = df_existing.dropna(subset=['Clinical_Risk']).copy()
        st.subheader("📊 สถิติภาพรวมการคัดกรอง")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสสะสมทั้งหมด", f"{len(df_clean)} ราย")
        m2.metric("🔴 High Risk", len(df_clean[df_clean['Clinical_Risk'].str.contains('High', na=False)]))
        m3.metric("🟡 Moderate Risk", len(df_clean[df_clean['Clinical_Risk'].str.contains('Moderate', na=False)]))
        m4.metric("🟢 Low Risk", len(df_clean[df_clean['Clinical_Risk'].str.contains('Low', na=False)]))
except:
    df_existing = pd.DataFrame()

st.divider()

# --- 7. ฟอร์มบันทึกข้อมูล ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form"):
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่ง", ["ขวา (Right)", "ซ้าย (Left)"])
        med = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
    with c2:
        rad = st.radio("ประวัติฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        surgery = st.radio("ประวัติผ่าตัดช่องท้อง", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("มีการติดคลิป", ["ไม่มี", "มี"], horizontal=True)
    
    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 8. ส่วนประมวลผล ---
if submit:
    # สร้างข้อมูลดิบ
    input_data = {
        'Age': age, 'Size_cm': size, 'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0, 'Surgery': 1 if surgery == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0, 'Chemo': 1 if chemo == "มี" else 0,
        'BX': 1 if "BX" in method else 0, 'Cold Polypectomy': 1 if "Cold" in method else 0,
        'Hot Polypectomy': 1 if "Hot" in method else 0, 'EMR': 1 if "EMR" in method else 0,
        'Sex': 1 if sex_input == "ชาย" else 0, 'Prob_Risk': 0
    }
    
    # แปลงเป็น DataFrame
    input_df = pd.DataFrame([input_data])

    # --- จุดแก้ไขสำคัญ: การ Match ชื่อฟีเจอร์แบบยืดหยุ่น ---
    final_df = pd.DataFrame(columns=model_features)
    for col in model_features:
        # พยายามหาชื่อที่ใกล้เคียงที่สุด (ตัดช่องว่างออกทั้งคู่แล้วเทียบกัน)
        clean_col = col.strip()
        matched = False
        for raw_col in input_data.keys():
            if raw_col.strip() == clean_col:
                final_df[col] = [input_data[raw_col]]
                matched = True
                break
        if not matched:
            final_df[col] = [0] # ถ้าหาไม่เจอจริงๆ ให้เป็น 0

    try:
        # ทำนายผลด้วย DataFrame ที่ Match ชื่อเป๊ะๆ แล้ว
        prob = model.predict_proba(final_df)[0][1]
        
        # Hybrid Decision Logic
        is_high = (size >= 2.0 or clip == "มี" or method == "EMR")
        is_mod = (med == "มี" or rad == "มี" or chemo == "มี" or surgery == "มี" or age >= 75)

        if is_high or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            adv = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำกลับบ้านแบบเข้มงวด"
            st_func = st.error
        elif is_mod or prob >= 0.1:
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            adv = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 และสังเกตอุจจาระ/ปวดท้อง"
            st_func = st.warning
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ"
            st_func = st.success

        timestamp = get_thailand_time().strftime("%Y-%m-%d %H:%M:%S")

        st.write("---")
        st.markdown(f"""
            <div style="background-color: {b_col}; border: 2px solid {col}; padding: 30px; border-radius: 20px; text-align: center;">
                <div style="font-size: 80px;">{ico}</div>
                <h1 style="color: {col}; margin: 10px 0;">{res}</h1>
                <p style="color: {col}; font-size: 1.2rem;">AI Score: <b>{prob:.4f}</b> | {timestamp}</p>
            </div>
        """, unsafe_allow_html=True)
        st_func(adv)
        
        # อัปเดต Google Sheets
        new_row = pd.DataFrame([{"Timestamp": timestamp, "Clinical_Risk": res, "AI_Score": prob, "Method": method}])
        df_all = pd.concat([df_existing, new_row], ignore_index=True)
        conn.update(data=df_all)
        st.info("💡 บันทึกข้อมูลเรียบร้อยแล้ว")

    except Exception as e:
        st.error(f"Error during prediction: {e}")
        st.write("ฟีเจอร์ที่ระบบตรวจพบในโมเดล:", model_features)
