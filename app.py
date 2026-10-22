import json
from google import genai
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Receipt & Purchasing Tracker", page_icon="🧾", layout="centered"
)

st.title("🧾 Receipt & Purchasing Tracker")
st.write(
    "Upload a receipt (Image or Scanned PDF) for Accounting COA & Purchasing Tracker."
)

# ดึง API Key จาก Streamlit Secrets หรือช่องกรอก
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    api_key = st.sidebar.text_input(
        "Enter Gemini API Key", type="password", help="Paste key and press Enter"
    )

uploaded_file = st.file_uploader(
    "Choose a receipt file...", type=["jpg", "jpeg", "png", "pdf"]
)

if uploaded_file:
    file_extension = uploaded_file.name.split(".")[-1].lower()

    if file_extension in ["jpg", "jpeg", "png"]:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Receipt Image", use_container_width=True)
    elif file_extension == "pdf":
        st.info(f"📄 Uploaded PDF: {uploaded_file.name} (Ready for processing)")

if uploaded_file and api_key:
    if st.button("Process Receipt", type="primary"):
        with st.spinner("Analyzing receipt and extracting purchasing data..."):
            uploaded_obj = None
            try:
                client = genai.Client(api_key=api_key.strip())

                file_extension = uploaded_file.name.split(".")[-1].lower()

                if file_extension in ["jpg", "jpeg", "png"]:
                    content_payload = Image.open(uploaded_file)
                elif file_extension == "pdf":
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    uploaded_obj = client.files.upload(file=tmp_path)
                    content_payload = uploaded_obj

                prompt = """
                Analyze this receipt and extract each individual line item with detailed purchasing and accounting info. 
                Categorize each item strictly according to the following Store Account Chart:

                --- CHART OF ACCOUNTS ---
                - 1101: ของสด - ตลาด
                - 1102: ของสด - แม็คโคร / โลตัส
                - 1103: ของสด - วัตถุดิบญี่ปุ่น
                - 1104: ของสด - จากที่อื่นๆ
                - 1105: ของแห้ง - วัตถุดิบ
                - 1106: ของแห้ง - เครื่องปรุง
                - 1107: เครื่องดื่ม non-alcohol
                - 1108: เครื่องดื่ม alcohol
                - 1201: กล่อง & ถุงใส่กลับบ้าน
                - 1202: ของใช้บนโต๊ะอาหาร
                - 1301: ของทำความสะอาด & สุขอนามัย
                - 1302: ของใช้สิ้นเปลืองในครัว
                - 4101-4109: ค่าใช้จ่ายอื่นๆ / อุปกรณ์ / สำนักงาน
                - 2001-2004: ค่าแรง
                - 3001-3005: ค่าใช้จ่ายคงที่
                - 4201-4206: ค่าการตลาดและค่าธรรมเนียม

                --- RULES ---
                1. Extract receipt date (Format: YYYY-MM-DD if possible, or string).
                2. Extract store/supplier name (ชื่อร้านค้า เช่น Makro, Lotus, ตลาดสด).
                3. Extract quantity and unit (e.g., quantity: 2, unit: kg / pack / pcs). If not specified, default quantity to 1 and unit to 'unit'.
                4. Extract price per unit (unit_price) and net total amount for that item (net_amount).
                5. Distribute any discounts proportionally.
                6. Return ONLY a valid JSON array of objects with these exact keys:
                   - "date": string
                   - "store_name": string
                   - "item_name": string
                   - "quantity": float
                   - "unit": string
                   - "unit_price": float
                   - "net_amount": float
                   - "category_code": string
                   - "category_name": string

                Do not include markdown backticks or any introductory/closing text outside the JSON array.
                """

                response = client.models.generate_content(
                    model="gemini-3.8-flash", contents=[prompt, content_payload]
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

                # --- ส่วนที่ 1: ตารางสำหรับบัญชี (Accounting Summary & Copy) ---
                st.subheader("📊 1. Accounting Summary & Clipboard")

                df_summary = (
                    df_items.groupby(["category_code", "category_name"])[
                        ["net_amount"]
                    ]
                    .sum()
                    .reset_index()
                )
                df_summary.columns = [
                    "Category Code",
                    "Category Name",
                    "Net Total",
                ]
                st.dataframe(df_summary, use_container_width=True)

                # Copy สำหรับ Excel (Net Total | Category Code)
                df_copy = df_summary[["Net Total", "Category Code"]]
                tsv_data = df_copy.to_csv(sep="\t", index=False, header=False)
                st.text(
                    "📋 Copy to Clipboard (Net Total | Code for Accounting):"
                )
                st.code(tsv_data, language="text")

                st.markdown("---")

                # --- ส่วนที่ 2: ตารางและดาวน์โหลดสำหรับ Purchasing Tracker ---
                st.subheader(
                    "🛒 2. Purchasing Tracker Data (Monthly Itemized)"
                )
                st.dataframe(df_items, use_container_width=True)

                # แปลงข้อมูลเป็น CSV เพื่อให้กดดาวน์โหลดไปรวมยอดรายเดือน
                csv_data = df_items.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Purchasing CSV for Monthly Tracker",
                    data=csv_data,
                    file_name="purchasing_tracker_data.csv",
                    mime="text/csv",
                )

            except Exception as e:
                st.error(f"Error processing receipt: {e}")

elif uploaded_file and not api_key:
    st.info("Please set up your API Key in Streamlit Secrets or the sidebar.")
