if submit:
        # 1. แปลงค่า (มั่นใจว่าได้ตัวเลข)
        loc_right = 1 if loc_side == "Right Side" else 0
        
        # 2. มัดรวม 12 ปัจจัย (ห้ามสลับที่ ห้ามหาย)
        features_list = [
            age_input, sex_input, size_input, loc_right, 
            int(med_in), int(surg_in), int(rad_in), int(chemo_in), 
            int(bx_in), int(cold_in), int(hot_in), int(emr_in)
        ]
        
        # 3. ตรวจสอบจำนวนก่อนส่ง (ถ้าไม่ครบ 12 ระบบจะแจ้งเตือน)
        if len(features_list) != 12:
            st.error(f"Error: จำนวนปัจจัยไม่ครบ (มีแค่ {len(features_list)} จาก 12)")
        else:
            # แปลงเป็น Numpy Array
            input_array = np.array(features_list).reshape(1, -1)
            
            # ทำนายผล
            try:
                prob = model.predict_proba(input_array)[0][1]
                
                # --- (เข้าสู่ส่วน Logic แสดงสี 🔴🟡🟢 ต่อไป) ---
                # ...
            except Exception as e:
                st.error(f"AI ไม่สามารถประมวลผลได้: {e}")
