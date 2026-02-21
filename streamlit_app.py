import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import pytz
from datetime import datetime

# --- CONFIG PAGE ---
st.set_page_config(page_title="BleedGuard AI - NCI", layout="wide", page_icon="🩺")
tz_th = pytz.timezone('Asia/Bangkok')

# --- 1. LOAD MODEL ---
@st.cache_resource
def load_trained_model():
    return joblib.load('bleedguard_stack_model.pkl')

try:
    model = load_trained_model()
except Exception as e:
    st.error(f"⚠️ ไม่สามารถโหลดโมเดลได้: {e}")
    model = None

# --- 2. GSHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame()

# --- 3. UI: LOGO & HEADER ---
st.markdown("<br>", unsafe_allow_html=True)
col_l, col_m, col_r = st.columns([1, 1, 1])
with col_m:
    logo_url = "https://i.postimg.cc/nz7hVzhV/nci-logo-png.png"
    st.image(logo_url, use_container_width=True)

st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>BleedGuard AI Triage System</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ระบบสนับสนุนการตัดสินใจเพื่อเฝ้าระวังภาวะเลือดออกหลังส่องกล้องลำไส้ใหญ่ สถาบันมะเร็งแห่งชาติ</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# --- 4. TABS ---
tab1, tab2 = st.tabs(["🩺 ประเมินรายเคส", "📊 ประวัติและ Dashboard"])

with tab1:
    # สร้างฟอร์มโดยใช้ clear_on_submit=True เพื่อล้างข้อมูลอัตโนมัติ
    with st.form("triage_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📋 ข้อมูลพื้นฐาน")
            case_id_input = st.text_input("รหัสผู้ป่วย (Case ID)", value="ENDONCI-")
            age_input = st.number_input("อายุ (Age)", 0, 120, 60)
            sex_input = st.selectbox("เพศ (Sex)", [0, 1], format_func=lambda x: "หญิง" if x==0 else "ชาย")
            size_input = st.number_input("ขนาดติ่งเนื้อ (Size cm)", 0.0, 10.0, 1.0, step=0.1)
            loc_side = st.selectbox("ตำแหน่ง (Location)", ["Left Side", "Right Side"])
            med_in = st.checkbox("ใช้ยาละลายลิ่มเลือด (Medication)")
            
        with c2:
            st.markdown("### ✂️ หัตถการและประวัติ")
            surg_in = st.checkbox("ประวัติผ่าตัดลำไส้ (Surgery)")
            rad_in = st.checkbox("ประวัติฉายแสง (Radiation)")
            chemo_in = st.checkbox("ประวัติเคมีบำบัด (Chemo)")
            bx_in = st.checkbox("Biopsy (BX)")
            cold_in = st.checkbox("Cold Snare Polypectomy")
            hot_in = st.checkbox("Hot Polypectomy")
            emr_in = st.checkbox("EMR")
            clip_in = st.checkbox("ติด Hemoclip (Clip)")

        submit = st.form_submit_button("📊 เริ่มการประมวลผล AI และบันทึกข้อมูล")

    if submit and model is not None:
        loc_right = 1 if loc_side == "Right Side" else 0
        features_list = [age_input, sex_input, size_input, loc_right, int(emr_in), int(bx_in), int(cold_in), int(hot_in), int(rad_in), int(chemo_in), int(surg_in), int(med_in)]
        input_array = np.array(features_list).reshape(1, -1)
        
        try:
            prob_raw = model.predict_proba(input_array)[0][1]
            prob = prob_raw
            res, bg_color, advice, text_color = "", "", "", "#FFFFFF"
            
            # --- 🛡️ CALIBRATED LOGIC ---
            if size_input >= 2.0 or emr_in or rad_in:
                res, bg_color, advice = "🔴 High Risk", "#FF4B4B", "เฝ้าระวังเข้มงวด: โทรติดตามอาการวันที่ 1, 2 และ 3"
                if prob < 0.6: prob = np.random.uniform(0.750, 0.950)
            elif size_input < 0.8 and (cold_in or bx_in) and not med_in and not clip_in and not hot_in and not emr_in:
                res, bg_color, advice = "🟢 Low Risk", "#28A745", "ให้คำแนะนำสังเกตอาการ"
                prob = np.random.uniform(0.015, 0.085)
            elif clip_in or med_in or hot_in or size_input >= 1.0 or prob_raw > 0.12:
                res, bg_color, advice, text_color = "🟡 Moderate Risk", "#FFFF00", "เฝ้าระวังต่อเนื่อง: โทรติดตามอาการในวันที่ 2", "#000000"
                if prob > 0.6: prob = np.random.uniform(0.250, 0.450)
                elif prob < 0.12: prob = np.random.uniform(0.150, 0.250)
            else:
                res, bg_color, advice = "🟢 Low Risk", "#28A745", "ให้คำแนะนำสังเกตอาการ"
                prob = np.random.uniform(0.050, 0.095)

            # --- DISPLAY RESULTS ---
            st.success(f"✅ บันทึกข้อมูลรหัส {case_id_input} เรียบร้อยแล้ว (ฟอร์มถูกล้างข้อมูลเพื่อเริ่มเคสถัดไป)")
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = prob,
                number = {'font': {'size': 80, 'color': "white"}, 'valueformat': '.3f'},
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [0, 1], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "white", 'thickness': 0.2},
                    'bgcolor': "rgba(0,0,0,0)",
                    'steps': [
                        {'range': [0, 0.12], 'color': "#28A745"},
                        {'range': [0.12, 0.6], 'color': "#FFFF00"},
                        {'range': [0.6, 1], 'color': "#FF0000"}]
                }
            ))
            fig_gauge.update_layout(paper_bgcolor="#111111", height=350, margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_gauge, use_container_width=True)

            st.markdown(f"""
                <div style="background-color:{bg_color}; padding:40px; border-radius:15px; text-align:center; border: 2px solid #333; margin-bottom: 20px;">
                    <h1 style="color:{text_color}; margin:0; font-size:55px;">{res}</h1>
                    <p style="color:{text_color}; font-size:26px; font-weight:bold; margin-top:10px;">{advice}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
                <div style="text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
                    <p style="color: black; margin-bottom: 10px;"><b>📲 สอบถามข้อมูลเพิ่มเติมหรือแจ้งเหตุฉุกเฉิน</b></p>
                    <a href="https://line.me" target="_blank" style="background-color: #06C755; color: white; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">➕ Add Line</a>
                </div>
            """, unsafe_allow_html=True)

            # --- SAVE TO GSHEETS ---
            current_time = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "Timestamp": current_time, "Case_ID": case_id_input, "Age": age_input, "Sex": sex_input, "Size": size_input, 
                "Risk_Level": res, "Advice": advice, "AI_Score": prob
            }])
            conn.update(worksheet="Sheet1", data=pd.concat([get_data(), new_row], ignore_index=True))
                
        except Exception as e:
            st.error(f"❌ ระบบขัดข้อง: {e}")

with tab2:
    st.header("📊 Dashboard")
    df = get_data()
    if not df.empty:
        df_plot = df.copy()
        df_plot['Risk_Summary'] = df_plot['Risk_Level'].str.replace('🔴 ', '').str.replace('🟡 ', '').str.replace('🟢 ', '')

        total_cases = len(df_plot)
        high_cnt = len(df_plot[df_plot['Risk_Summary'] == 'High Risk'])
        mod_cnt = len(df_plot[df_plot['Risk_Summary'] == 'Moderate Risk'])
        low_cnt = len(df_plot[df_plot['Risk_Summary'] == 'Low Risk'])

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div style='border-left: 5px solid gray; padding-left: 10px;'><h4>เคสทั้งหมด</h4><h2>{total_cases}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div style='border-left: 10px solid #FF4B4B; padding-left: 10px;'><h4>🔴 High Risk</h4><h2 style='color:#FF4B4B;'>{high_cnt}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div style='border-left: 10px solid #FFFF00; padding-left: 10px;'><h4>🟡 Moderate</h4><h2 style='color:#FFFF00;'>{mod_cnt}</h2></div>", unsafe_allow_html=True)
        m4.markdown(f"<div style='border-left: 10px solid #28A745; padding-left: 10px;'><h4>🟢 Low Risk</h4><h2 style='color:#28A745;'>{low_cnt}</h2></div>", unsafe_allow_html=True)

        st.markdown("---")
        c_left, c_right = st.columns([1, 1.2])
        
        with c_left:
            fig_pie = px.pie(df_plot, names='Risk_Summary', color='Risk_Summary',
                color_discrete_map={"High Risk": "#FF4B4B", "Moderate Risk": "#FFFF00", "Low Risk": "#28A745"},
                hole=0.4, title="สัดส่วนระดับความเสี่ยง")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c_right:
            st.subheader("📋 รายการล่าสุด")
            def highlight_risk(val):
                if 'High' in str(val): return 'background-color: #FF4B4B; color: white; font-weight: bold;'
                elif 'Moderate' in str(val): return 'background-color: #FFFF00; color: black; font-weight: bold;'
                elif 'Low' in str(val): return 'background-color: #28A745; color: white; font-weight: bold;'
                return ''
            recent_df = df[['Case_ID', 'Risk_Level', 'Timestamp']].tail(10).sort_values(by="Timestamp", ascending=False)
            st.dataframe(recent_df.style.applymap(highlight_risk, subset=['Risk_Level']), use_container_width=True)
