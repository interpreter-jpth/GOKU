import json
from google import genai
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Receipt Expense Categorizer", page_icon="🧾", layout="centered"
)

st.title("🧾 Receipt Expense Categorizer")
st.write("Upload a receipt to extract data and categorize expenses.")

# ดึง API Key จาก Streamlit Secrets หรือช่องกรอก
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    api_key = st.sidebar.text_input(
        "Enter Gemini API Key", type="password", help="Paste key and press Enter"
    )

uploaded_file = st.file_uploader(
    "Choose a receipt image...", type=["jpg", "jpeg", "png"]
)

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_container_width=True)

if uploaded_file and api_key:
    if st.button("Process Receipt", type="primary"):
        with st.spinner("Analyzing receipt with Gemini AI..."):
            try:
                # ใช้ Client แบบใหม่ตามมาตรฐาน SDK ปัจจุบัน
                client = genai.Client(api_key=api_key.strip())

                prompt = """
                Analyze this receipt and categorize items according to the New Chart of Accounts:
                - 1102: Fresh Food (Market/Supermarket)
                - 1105: Dry Goods (Ingredients)
                - 1106: Dry Goods (Seasonings)
                - 1301: Cleaning & Hygiene
                - 1302: Kitchen Consumables (Includes former 1303 items)
                - 4101: Transportation/Fuel/Delivery Fee

                Rules:
                1. Calculate and distribute any discounts/vouchers proportionally across categories based on gross amounts.
                2. Output ONLY a valid JSON array of objects with the exact keys:
                   - "category_code": string
                   - "category_name": string
                   - "gross_total": float
                   - "discount": float
                   - "net_total": float

                Do not include markdown formatting or extra text outside the JSON array.
                """

                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=[prompt, image]
                )

                clean_json = (
                    response.text.strip()
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )
                data = json.loads(clean_json)

                df = pd.DataFrame(data)

                st.success("Analysis Complete!")
                st.subheader("📊 Expense Summary")
                st.dataframe(df, use_container_width=True)

                tsv_data = df.to_csv(sep="\t", index=False)
                st.subheader("📋 Copy to Clipboard (Paste directly to Excel)")
                st.code(tsv_data, language="text")

            except Exception as e:
                st.error(f"Error processing receipt: {e}")

elif uploaded_file and not api_key:
    st.info("Please set up your API Key in Streamlit Secrets or the sidebar.")
