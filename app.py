import json
from google import genai
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Receipt Expense Categorizer", page_icon="🧾", layout="centered"
)

st.title("🧾 Receipt Expense Categorizer")
st.write("Upload a receipt (Image or Scanned PDF) to extract and categorize expenses.")

# ดึง API Key จาก Streamlit Secrets หรือช่องกรอก
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    api_key = st.sidebar.text_input(
        "Enter Gemini API Key", type="password", help="Paste key and press Enter"
    )

# รองรับไฟล์ PDF เพิ่มเติมจากเดิม (jpg, jpeg, png)
uploaded_file = st.file_uploader(
    "Choose a receipt file...", type=["jpg", "jpeg", "png", "pdf"]
)

if uploaded_file:
    # ตรวจสอบประเภทไฟล์ที่อัปโหลด
    file_extension = uploaded_file.name.split(".")[-1].lower()

    if file_extension in ["jpg", "jpeg", "png"]:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Receipt Image", use_container_width=True)
        file_content_for_gemini = image
    elif file_extension == "pdf":
        st.info(f"📄 Uploaded PDF: {uploaded_file.name} (Ready for processing)")
        # อ่านไฟล์ PDF เป็นไบต์ส่งให้ Gemini โดยตรง
        file_content_for_gemini = {
            "mime_type": "application/pdf",
            "data": uploaded_file.getvalue(),
        }

if uploaded_file and api_key:
    if st.button("Process Receipt", type="primary"):
        with st.spinner("Analyzing receipt with Gemini AI..."):
            try:
                client = genai.Client(api_key=api_key.strip())

                prompt = """
                Analyze this receipt and extract each individual line item. Categorize each item strictly according to the following Store Account Chart (หมวดหมู่ บัญชีร้าน):

                --- CHART OF ACCOUNTS ---
                1. ต้นทุนอาหาร (Food Cost):
                   - 1101: ของสด - ตลาด (ผักสด, ผลไม้, เครื่องต้มยำ, ไข่ไก่, กุ้ง/ปลาสดจากตลาด)
                   - 1102: ของสด - แม็คโคร / โลตัส (เนื้อสัตว์สไลซ์/บด, นมสด, เนยแท้, ชีส, อาหารทะเลแช่แข็ง)
                   - 1103: ของสด - วัตถุดิบญี่ปุ่น (ปลาแซลมอนนำเข้า, เนื้อวัววากิว, วาซาบิสด, ไข่กุ้ง Ebiko, ชาเขียวเกรดพรีเมียม)
                   - 1104: ของสด - จากที่อื่นๆ (MAKOTOYA, FUJI, KOBEYA)
                   - 1105: ของแห้ง - วัตถุดิบ (ข้าวสาร, แป้งทอดกรอบ, แป้งทำขนม, เส้นก๋วยเตี๋ยว/พาสต้า, เกล็ดขนมปัง, ผงชา)
                   - 1106: ของแห้ง - เครื่องปรุง (น้ำมันพืช, ซอสโชยุ, มิริน, น้ำปลา, น้ำตาล, เกลือ, ผงชูรส, ผงปรุงรส, เครื่องเทศแห้ง)
                   - 1107: เครื่องดื่ม non-alcohol (เมล็ดกาแฟ, ใบชา, ไซรัป, ผงโกโก้, น้ำผลไม้กล่อง, โซดา, น้ำแข็ง)
                   - 1108: เครื่องดื่ม alcohol (เบียร์, สาเก, เหล้า, ไวน์)

                2. ของใช้บริการและบรรจุภัณฑ์ (Packaging & Service Supplies):
                   - 1201: กล่อง & ถุงใส่กลับบ้าน (กล่องอาหาร, ถ้วยซุป, แก้วกาแฟ/แก้วน้ำใช้แล้วทิ้ง, ฝาแก้ว, ถุงพลาสติกหิ้ว, ถุงกระดาษ, สายรัดกล่อง, สติกเกอร์โลโก้ร้าน)
                   - 1202: ของใช้บนโต๊ะอาหาร (กระดาษทิชชู่บนโต๊ะ/ทิชชู่เปียก, ตะเกียบใช้แล้วทิ้ง, ช้อน-ส้อมพลาสติก, หลอดพลาสติก/กระดาษ, ไม้จิ้มฟัน, ถุงใส่ตะเกียบ, แผ่นรองจานกระดาษ)

                3. ของใช้และของทำความสะอาด (Store Supplies):
                   - 1301: ของทำความสะอาด & สุขอนามัย (น้ำยาล้างจาน, น้ำยาถูพื้น, น้ำยาเช็ดกระจก, น้ำยาฆ่าเชื้อ, ถุงขยะ ดำ/ใส, ถุงมือยาง, สก๊อตช์ไบรต์, ฝอยขัดหม้อ, ผ้าเช็ดโต๊ะ, ทิชชู่ห้องน้ำ, สบู่ล้างมือ)
                   - 1302: ของใช้สิ้นเปลืองในครัว (ฟอยล์ห่ออาหาร, พลาสติกถนอมอาหาร Cling Wrap, กระดาษซับน้ำมัน, ถุงร้อน/ถุงเย็นใส่ของในครัว)

                4. ค่าใช้จ่ายอื่นๆ (Variable Cost):
                   - 4101: ค่าเดินทาง น้ำมัน - ซื้อของ
                   - 4102: ค่าเดินทาง น้ำมัน - ผู้บริหาร
                   - 4103: ค่าซ่อมร้าน
                   - 4104: ภาชนะและอุปกรณ์บนโต๊ะอาหาร (จาน, ชาม, แก้ว)
                   - 4105: อุปกรณ์เครื่องครัวเล็ก (กระทะ, หม้อ, มีด)
                   - 4106: อุปกรณ์อื่นๆ
                   - 4107: เครื่องครัวขนาดใหญ่และเครื่องใช้ไฟฟ้า
                   - 4108: ยูนิฟอร์มพนักงาน
                   - 4109: ของใช้สำนักงาน (ผ้าหมึกพิมพ์สลิป, ตลับหมึกเครื่อง POS, กระดาษใบเสร็จ, กระดาษจดออเดอร์, กระดาษสลิป PO, ปากกา)

                5. ค่าแรง (Labor Cost):
                   - 2001: เงินเดือนพนักงาน
                   - 2002: ค่าจ้างรายวัน
                   - 2003: สวัสดิการพนักงาน
                   - 2004: เงินเดือนผู้บริหาร

                6. ค่าใช้จ่ายคงที่ (Fixed Cost):
                   - 3001: ค่าเช่าร้าน
                   - 3002: ค่าน้ำประปา, ค่าไฟฟ้า, ค่าแก๊ส
                   - 3003: ค่าโทร และ อินเทอร์เน็ต
                   - 3004: ค่าระบบ
                   - 3005: ค่าบัญชี

                7. ค่าการตลาดและค่าธรรมเนียม:
                   - 4201: ค่า GP แอปเดลิเวอรี
                   - 4202: ค่าโฆษณา
                   - 4203: ค่าธรรมเนียมระบบรับชำระเงิน
                   - 4204: ค่าสิ่งพิมพ์
                   - 4205: DOHAN
                   - 4206: ดื่มพนักงาน

                --- RULES ---
                1. If discounts or vouchers exist on the receipt, distribute them proportionally across the items and categories based on gross amounts.
                2. Return ONLY a valid JSON array of objects representing each individual item on the receipt, with these exact keys:
                   - "item_name": string (ชื่อสินค้า)
                   - "category_code": string (รหัสหมวดหมู่ เช่น "1102")
                   - "category_name": string (ชื่อหมวดหมู่)
                   - "gross_amount": float (ยอดเงินก่อนส่วนลดของรายการนี้)
                   - "discount": float (ส่วนลดเฉลี่ยตามสัดส่วน)
                   - "net_amount": float (ยอดสุทธิหลังหักส่วนลด)

                Do not include markdown backticks or any introductory/closing text outside the JSON array.
                """

                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[prompt, file_content_for_gemini],
                )

                clean_json = (
                    response.text.strip()
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )
                items_data = json.loads(clean_json)

                df_items = pd.DataFrame(items_data)

                st.success("Analysis Complete!")

                # 1. รายการสินค้าทั้งหมด
                st.subheader("📋 รายการสินค้าทั้งหมด (Itemized Breakdown)")
                st.dataframe(df_items, use_container_width=True)

                # 2. สรุปยอดรวมแยกตามหมวดหมู่
                st.subheader("📊 สรุปยอดรวมแยกตามหมวดหมู่ (Category Summary)")
                df_summary = (
                    df_items.groupby(["category_code", "category_name"])[
                        ["gross_amount", "discount", "net_amount"]
                    ]
                    .sum()
                    .reset_index()
                )
                df_summary.columns = [
                    "Category Code",
                    "Category Name",
                    "Gross Total",
                    "Discount",
                    "Net Total",
                ]
                st.dataframe(df_summary, use_container_width=True)

                # 3. คัดลอกข้อมูล (Net Total ซ้าย, Category Code ขวา)
                df_copy = (
                    df_items.groupby("category_code")["net_amount"]
                    .sum()
                    .reset_index()
                )
                df_copy = df_copy[["net_amount", "category_code"]]

                tsv_data = df_copy.to_csv(sep="\t", index=False, header=False)
                st.subheader("📋 Copy to Clipboard (Net Total | Category Code)")
                st.code(tsv_data, language="text")

            except Exception as e:
                st.error(f"Error processing receipt: {e}")

elif uploaded_file and not api_key:
    st.info("Please set up your API Key in Streamlit Secrets or the sidebar.")
