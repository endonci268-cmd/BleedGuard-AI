import streamlit as st
import pandas as pd
import joblib
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. การตั้งค่าหน้าจอ (Mobile Friendly) ---
st.set_page_config(
    layout="centered", 
    page_title="NCI BleedGuard-AI",
    page_icon="🩺"
)

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. โหลดสมอง AI (.pkl) ---
@st.cache_resource
def load_model():
    return joblib.load('bleedguard_model.pkl')

try:
    model = load_model()
    # ดึงรายชื่อตัวแปรที่โมเดลต้องการ
    if hasattr(model, 'feature_names_in_'):
        model_features = model.feature_names_in_.tolist()
    else:
        model_features = ['Age', 'Size_cm', 'Loc_Right', 'Med_Risk', 'Radiation', 'Chemo', 'Surgery', 'BX', 'Cold_Poly', 'Hot_Poly', 'EMR', 'Sex']
except:
    st.error("❌ ไม่พบไฟล์โมเดล bleedguard_model.pkl")

# --- 4. ส่วนหัวโปรแกรม ---
st.markdown("""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI</h2>
        <p style='font-size: 0.9rem; color: #555;'>ระบบคัดกรองความเสี่ยงภาวะเลือดออกหลังตัดติ่งเนื้อ<br>
        <b>สถาบันมะเร็งแห่งชาติ (NCI Thailand)</b></p>
    </div>
""", unsafe_allow_html=True)

# --- 5. แดชบอร์ดสรุปผล (แก้ปัญหา Dashboard ไม่ขึ้น) ---
with st.expander("📊 สถิติภาพรวม (Dashboard)", expanded=True):
    try:
        # อ่านข้อมูลจากหน้าหลัก (Sheet1) และบังคับให้อัปเดตสด (ttl=0)
        df_existing = conn.read(ttl=0)
        
        if df_existing is not None and not df_existing.empty:
            # ลบแถวที่ไม่มีข้อมูลสำคัญออกก่อนนับ
            df_clean = df_existing.dropna(subset=['Risk_Level'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("เคสสะสมทั้งหมด", len(df_clean))
            
            # นับจำนวนตามระดับความเสี่ยง
            high_count = df_clean['Risk_Level'].str.contains('High', na=False).sum()
            low_count = df_clean['Risk_Level'].str.contains('Low', na=False).sum()
            
            c2.metric("🔴 High Risk", f"{high_count} ราย")
            c3.metric("🟢 Low Risk", f"{low_count} ราย")
            
            # แสดงตาราง 3 เคสล่าสุด
            st.write("---")
            st.caption("ข้อมูลล่าสุดในระบบ:")
            st.dataframe(df_clean.tail(3)[['Timestamp', 'Age', 'Risk_Level']], use_container_width=True)
        else:
            st.info("💡 ยังไม่มีข้อมูลบันทึกในระบบ เริ่มคีย์เคสแรกด้านล่างได้เลยครับ")
            df_existing = pd.DataFrame()
    except Exception as e:
        st.warning(f"Dashboard กำลังรอข้อมูลใหม่... (Error: {e})")
        df_existing = pd.DataFrame()

# --- 6. ฟอร์มกรอกข้อมูล (อิงตามตัวแปรของคุณ) ---
st.subheader("📝 บันทึกข้อมูลคนไข้")
with st.form("bleedguard_form"):
    age = st.number_input("อายุ / Age (ปี)", 1, 120, 60)
    sex_input = st.radio("เพศ / Sex", ["ชาย", "หญิง"], horizontal=True)
    size = st.number_input("ขนาดติ่งเนื้อ / Size (cm)", 0.1, 10.0, 1.0, step=0.1)
    loc = st.selectbox("ตำแหน่งติ่งเนื้อ", ["ขวา (Right)", "ซ้าย (Left)"])
    med = st.radio("ยากลุ่มเสี่ยง (ละลายลิ่มเลือด)", ["ไม่มี", "มี"], horizontal=True)
    rad = st.radio("ประวัติการฉายแสง (Radiation)", ["ไม่มี", "มี"], horizontal=True)
    chemo = st.radio("ประวัติเคมีบำบัด (Chemo)", ["ไม่มี", "มี"], horizontal=True)
    method = st.selectbox("หัตถการ / Procedure", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
    clip = st.radio("มีการติดคลิป (Hemoclip)", ["ไม่มี", "มี"], horizontal=True)

    submit_btn = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

# --- 7. การคำนวณและบันทึก (แก้ปัญหาเวลาไม่ตรง) ---
if submit_btn:
    # 7.1 เตรียมข้อมูลส่งให้ AI
    raw_for_ai = {
        'Age': age, 'Size_cm': size,
        'Loc_Right': 1 if "ขวา" in loc else 0,
        'Med_Risk': 1 if med == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0,
        'Surgery': 0, 
        'BX': 1 if "BX" in method else 0,
        'Cold_Poly': 1 if "Cold" in method else 0,
        'Hot_Poly': 1 if "Hot" in method else 0,
        'EMR': 1 if method == "EMR" else 0,
        'Sex': 1 if sex_input == "ชาย" else 0
    }

    # ป้องกันชื่อตัวแปรไม่ตรงใจ AI
    input_df = pd.DataFrame([raw_for_ai])
    for col in model_features:
        if col not in input_df.columns: input_df[col] = 0
    input_df = input_df[model_features]

    try:
        # AI คำนวณคะแนน
        prob = model.predict_proba(input_df)[0][1]
        
        # Hybrid Logic (Clinical + AI)
        clin_risk = "High" if (size >= 2.0 or clip == "มี" or method == "EMR") else "Normal"
        if clin_risk == "High" or prob >= 0.5:
            risk_text, color = "🔴 High Risk", "red"
        else:
            risk_text, color = "🟢 Low Risk", "green"

        # ปรับเวลาเป็นประเทศไทย (UTC+7)
        th_time = datetime.now() + timedelta(hours=7)
        timestamp_str = th_time.strftime("%Y-%m-%d %H:%M:%S")

        # 7.2 บันทึกลง Google Sheets ตามชื่อคอลัมน์เป๊ะๆ
        new_data = pd.DataFrame([{
            "Timestamp": timestamp_str,
            "Age": age, "Sex": sex_input, "Size_cm": size,
            "Loc_Right": 1 if "ขวา" in loc else 0,
            "Med_Risk": 1 if med == "มี" else 0,
            "Surgery": 0, "Radiation": 1 if rad == "มี" else 0,
            "Chemo": 1 if chemo == "มี" else 0,
            "BX": 1 if "BX" in method else 0,
            "Cold_Poly": 1 if "Cold" in method else 0,
            "Hot_Poly": 1 if "Hot" in method else 0,
            "EMR": 1 if method == "EMR" else 0,
            "Clinical_Risk": clin_risk,
            "AI_Score": round(float(prob), 4),
            "Risk_Level": risk_text
        }])

        # รวมข้อมูลเก่าและใหม่แล้วบันทึก
        updated_df = pd.concat([df_existing, new_data], ignore_index=True)
        conn.update(data=updated_df)
        
        # แสดงผลลัพธ์
        st.markdown(f"""
            <div style='text-align: center; border: 2px solid {color}; padding: 15px; border-radius: 10px; margin-top: 10px;'>
                <h2 style='color: {color};'>{risk_text}</h2>
                <p>AI Score: {prob:.4f} | เวลาบันทึก: {timestamp_str}</p>
            </div>
        """, unsafe_allow_html=True)
        st.balloons()
        st.success("✅ บันทึกข้อมูลลง Google Sheets เรียบร้อย!")
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
