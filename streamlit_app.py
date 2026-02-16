import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(layout="wide", page_title="NCI BleedGuard-AI", page_icon="🩺")

# --- 2. การเชื่อมต่อ Google Sheets (ต้องอยู่ด้านบนเพื่อให้ Dashboard เรียกใช้ได้) ---
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
st.markdown(f"""
    <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h2 style='color: #003366; margin-bottom: 0;'>🩺 NCI BleedGuard-AI Dashboard</h2>
        <p style='font-size: 1rem; color: #555;'>ระบบสนับสนุนการตัดสินใจเพื่อความปลอดภัยของผู้ป่วยสถาบันมะเร็งแห่งชาติ</p>
    </div>
""", unsafe_allow_html=True)

# --- 6. Dashboard วิเคราะห์ข้อมูล (ย้ายมาไว้ก่อนฟอร์มเพื่อให้เห็นภาพรวมก่อน) ---
with st.container():
    try:
        # อ่านข้อมูลสดจาก Sheets
        df_existing = conn.read(ttl=0)
        
        if df_existing is not None and not df_existing.empty:
            # ล้างค่าว่างใน Risk_Level
            df_clean = df_existing.dropna(subset=['Risk_Level']).copy()
            
            # --- ส่วน Metrics ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("เคสสะสมทั้งหมด", f"{len(df_clean)} ราย")
            
            high_count = len(df_clean[df_clean['Risk_Level'].str.contains('High', na=False)])
            m2.metric("🔴 High Risk", f"{high_count} ราย", delta=f"{(high_count/len(df_clean)*100):.1f}%", delta_color="inverse")
            
            low_count = len(df_clean[df_clean['Risk_Level'].str.contains('Low', na=False)])
            m3.metric("🟢 Low Risk", f"{low_count} ราย")
            
            avg_age = df_clean['Age'].mean()
            m4.metric("อายุเฉลี่ย", f"{avg_age:.1f} ปี")

            # --- ส่วนกราฟ ---
            g1, g2 = st.columns(2)

            with g1:
                st.write("### สัดส่วนระดับความเสี่ยง")
                fig_pie = px.pie(df_clean, names='Risk_Level', 
                                 color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟢 Low Risk':'#00CC96'},
                                 hole=0.4)
                fig_pie.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)

            with g2:
                st.write("### จำนวนเคสแยกตามหัตถการ")
                fig_bar = px.bar(df_clean, x='Method', color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'#FF4B4B', '🟢 Low Risk':'#00CC96'},
                                 barmode='group')
                fig_bar.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- กราฟแนวโน้มรายวัน ---
            st.write("### แนวโน้มการบันทึกข้อมูลรายวัน")
            df_clean['Date'] = pd.to_datetime(df_clean['Timestamp']).dt.date
            trend_data = df_clean.groupby('Date').size().reset_index(name='Count')
            fig_trend = px.area(trend_data, x='Date', y='Count', line_shape='spline')
            fig_trend.update_layout(height=250)
            st.plotly_chart(fig_trend, use_container_width=True)
            
        else:
            st.info("💡 ยังไม่มีข้อมูลบันทึกในระบบ")
            df_existing = pd.DataFrame()
    except Exception as e:
        st.warning("กำลังเตรียมข้อมูล Dashboard...")
        df_existing = pd.DataFrame()

st.write("---")

# --- 7. ฟอร์มบันทึกข้อมูล ---
st.subheader("📝 บันทึกข้อมูลคนไข้รายใหม่")
with st.form("input_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("อายุ (ปี)", 1, 120, 60)
        sex_input = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)
        size = st.number_input("ขนาดติ่งเนื้อ (cm)", 0.1, 10.0, 1.0, step=0.1)
        loc = st.selectbox("ตำแหน่งติ่งเนื้อ", ["ขวา", "ซ้าย"])
    
    with col2:
        med = st.radio("ยากลุ่มเสี่ยง", ["ไม่มี", "มี"], horizontal=True)
        rad = st.radio("ประวัติการฉายแสง", ["ไม่มี", "มี"], horizontal=True)
        chemo = st.radio("ประวัติเคมีบำบัด", ["ไม่มี", "มี"], horizontal=True)
        method = st.selectbox("หัตถการ", ["Biopsy (BX)", "Cold Polypectomy", "Hot Polypectomy", "EMR"])
        clip = st.radio("การติดคลิป", ["ไม่มี", "มี"], horizontal=True)

    submit = st.form_submit_button("📊 ประมวลผลและบันทึกข้อมูล", use_container_width=True)

if submit:
    # 7.1 เตรียมข้อมูลส่งให้ AI
    raw_for_ai = {
        'Age': age, 'Size_cm': size,
        'Loc_Right': 1 if loc == "ขวา" else 0,
        'Med_Risk': 1 if med == "มี" else 0,
        'Radiation': 1 if rad == "มี" else 0,
        'Chemo': 1 if chemo == "มี" else 0,
        'Surgery': 0, 'BX': 1 if "BX" in method else 0,
        'Cold_Poly': 1 if "Cold" in method else 0,
        'Hot_Poly': 1 if "Hot" in method else 0,
        'EMR': 1 if method == "EMR" else 0,
        'Sex': 1 if sex_input == "ชาย" else 0
    }
    
    input_df = pd.DataFrame([raw_for_ai])
    for col in model_features:
        if col not in input_df.columns: input_df[col] = 0
    input_df = input_df[model_features]

    try:
        # AI คำนวณ
        prob = model.predict_proba(input_df)[0][1]
        
        # Hybrid Logic
        clin_risk = "High" if (size >= 2.0 or clip == "มี" or method == "EMR") else "Normal"
        risk_text = "🔴 High Risk" if (clin_risk == "High" or prob >= 0.5) else "🟢 Low Risk"
        color = "red" if "High" in risk_text else "green"

        # เวลาไทย
        now_th = get_thailand_time()
        timestamp_str = now_th.strftime("%Y-%m-%d %H:%M:%S")

        # บันทึกลง Google Sheets
        new_data = pd.DataFrame([{
            "Timestamp": timestamp_str,
            "Age": age, "Sex": sex_input, "Size_cm": size,
            "Loc_Right": 1 if loc == "ขวา" else 0,
            "Med_Risk": 1 if med == "มี" else 0,
            "Surgery": 0, "Radiation": 1 if rad == "มี" else 0,
            "Chemo": 1 if chemo == "มี" else 0,
            "BX": 1 if "BX" in method else 0,
            "Cold_Poly": 1 if "Cold" in method else 0,
            "Hot_Poly": 1 if "Hot" in method else 0,
            "EMR": 1 if method == "EMR" else 0,
            "Clinical_Risk": clin_risk,
            "AI_Score": round(float(prob), 4),
            "Risk_Level": risk_text,
            "Method": method # เพิ่มเพื่อให้กราฟดึงข้อมูลหัตถการได้ง่าย
        }])

        updated_df = pd.concat([df_existing, new_data], ignore_index=True)
        conn.update(data=updated_df)
        
        st.success(f"บันทึกสำเร็จ! ผลลัพธ์: {risk_text}")
        st.balloons()
        st.rerun() # รีโหลดหน้าเพื่ออัปเดตกราฟ
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
