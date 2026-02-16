import streamlit as st
import pandas as pd
import plotly.express as px # เพิ่มตัวนี้เพื่อทำกราฟ
from streamlit_gsheets import GSheetsConnection

# --- ส่วน Dashboard ใหม่ ---
with st.expander("📊 วิเคราะห์ข้อมูลเชิงลึก (NCI Dashboard)", expanded=True):
    try:
        df_existing = conn.read(ttl=0)
        if df_existing is not None and not df_existing.empty:
            df_clean = df_existing.dropna(subset=['Risk_Level'])
            
            # --- แถวที่ 1: Metrics หลัก ---
            m1, m2, m3 = st.columns(3)
            m1.metric("จำนวนเคสรวม", f"{len(df_clean)} ราย")
            high_count = len(df_clean[df_clean['Risk_Level'].str.contains('High', na=False)])
            m2.metric("🔴 High Risk", f"{high_count} ราย", delta=f"{(high_count/len(df_clean)*100):.1f}%")
            m3.metric("🟢 Low Risk", f"{len(df_clean)-high_count} ราย")

            st.write("---")

            # --- แถวที่ 2: กราฟ ---
            g1, g2 = st.columns(2)

            with g1:
                st.markdown("**สัดส่วนความเสี่ยง (Risk Distribution)**")
                # ทำกราฟวงกลม
                fig_pie = px.pie(df_clean, names='Risk_Level', 
                                 color='Risk_Level',
                                 color_discrete_map={'🔴 High Risk':'red', '🟢 Low Risk':'green'},
                                 hole=0.4)
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

            with g2:
                st.markdown("**ประเภทหัตถการ (Procedures)**")
                # ทำกราฟแท่งนับประเภท Method
                method_counts = df_clean['Method'].value_counts().reset_index()
                fig_bar = px.bar(method_counts, x='Method', y='count', color='Method', text_auto=True)
                fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- แถวที่ 3: กราฟเส้นแนวโน้มรายวัน ---
            st.markdown("**แนวโน้มการบันทึกเคสรายวัน (Daily Trend)**")
            df_clean['Date'] = pd.to_datetime(df_clean['Timestamp']).dt.date
            trend_data = df_clean.groupby('Date').size().reset_index(name='Count')
            fig_trend = px.line(trend_data, x='Date', y='Count', markers=True)
            fig_trend.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_trend, use_container_width=True)

        else:
            st.info("💡 รอการบันทึกข้อมูลเพื่อแสดงผลกราฟวิเคราะห์")
    except Exception as e:
        st.warning(f"ยังไม่สามารถดึงข้อมูลมาแสดงกราฟได้: {e}")
