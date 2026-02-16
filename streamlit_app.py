# --- 3. ตัดสินใจระดับความเสี่ยง (รวมเกณฑ์ AI + เกณฑ์ติ่งเนื้อ < 0.5 cm) ---
        
        # กฎเหล็ก 1: ถ้าขนาด < 0.5 cm และไม่มีปัจจัยเสี่ยงอื่น = เขียวแน่นอน (Low Risk)
        if size < 0.5 and med_input == "ไม่มี" and clip_input == "ไม่มี":
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ (ติ่งเนื้อขนาดเล็กความเสี่ยงต่ำ)"
            st_func = st.success

        # กฎเหล็ก 2: ถ้าเข้าเกณฑ์ High Risk ทางคลินิก = แดง (High Risk)
        elif prob_risk_val == 1.0 or prob >= 0.5:
            res, col, ico, b_col = "🔴 High Risk", "#990000", "😫", "#FFD2D2"
            adv = "**📋 แผนการพยาบาล:** ติดตามใกล้ชิด 24, 48, 72 ชม. และให้คำแนะนำกลับบ้านแบบเข้มงวด"
            st_func = st.error
            
        # กฎเหล็ก 3: ถ้าคะแนน AI เกิน 0.02 (และขนาดไม่อยู่ในกลุ่ม Low) = เหลือง (Moderate Risk)
        elif prob >= 0.02: 
            res, col, ico, b_col = "🟡 Moderate Risk", "#827717", "😟", "#FFF9C4"
            adv = "**📋 แผนการพยาบาล:** ติดตามอาการวันที่ 1, 3, 7 และสังเกตอาการผิดปกติ (Post-op Call)"
            st_func = st.warning
            
        # นอกนั้นเป็นเขียวปกติ
        else:
            res, col, ico, b_col = "🟢 Low Risk", "#006600", "😊", "#D2FFD2"
            adv = "**✅ แผนการพยาบาล:** ดูแลตามมาตรฐานปกติ"
            st_func = st.success
