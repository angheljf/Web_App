import streamlit as st
import pandas as pd
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="JA Elevate - Student Counts",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CDP - Student Counts & Aggregations")
st.markdown(
    "Upload an Excel file to get student counts aggregated by School Type."
)

# File uploader
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file is not None:
    # Configuration section
    st.subheader("⚙️ Configuration")
    col1, col2 = st.columns(2)

    with col1:
        sheet_name = st.text_input("Sheet Name", value="School Info")
    with col2:
        rows_to_skip = st.number_input(
            "Header Rows to Skip",
            min_value=0,
            max_value=10,
            value=2
        )

    # Load the data
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

        # Skip header rows if specified
        if rows_to_skip > 0:
            df = df.iloc[rows_to_skip:].reset_index(drop=True)

        # Convert column types
        numeric_cols = [
            '# of Visit Days',
            '# of Students Pending',
            'Verified Students (from Program Verification Form)'
        ]

        for col in df.columns:
            if col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = df[col].astype(str)

        # Column preview section
        st.subheader("📋 Column Preview")
        st.write("**Available Columns:**", df.columns.tolist())
        st.dataframe(df.head(10), use_container_width=True)

        # Column selection dropdowns
        st.subheader("🔧 Column Selection")
        col3, col4 = st.columns(2)

        # Separate columns by type
        text_cols = df.select_dtypes(
            include=['object', 'string']
        ).columns.tolist()
        numeric_cols_list = df.select_dtypes(
            include=['number']
        ).columns.tolist()

        # Smart defaults - try to find matching column names
        default_school_type_idx = 0
        default_student_count_idx = 0

        for i, col in enumerate(text_cols):
            if "school type" in col.lower():
                default_school_type_idx = i

        for i, col in enumerate(numeric_cols_list):
            if "students" in col.lower() or "pending" in col.lower():
                default_student_count_idx = i

        with col3:
            if not text_cols:
                st.warning("⚠️ No text columns found in the data.")
                school_type_col = None
            else:
                school_type_col = st.selectbox(
                    "Select Group By Column (Text)",
                    options=text_cols,
                    index=default_school_type_idx
                )

        with col4:
            if not numeric_cols_list:
                st.warning("⚠️ No numeric columns found in the data.")
                student_count_col = None
            else:
                student_count_col = st.selectbox(
                    "Select Value Column (Numeric)",
                    options=numeric_cols_list,
                    index=default_student_count_idx
                )

        # Process button
        if st.button("🚀 Generate Student Counts", type="primary"):
            # Validate columns
            validation_passed = True

            if school_type_col is None:
                st.error("❌ No text column selected for School Type.")
                validation_passed = False

            if student_count_col is None:
                st.error("❌ No numeric column selected for Student Count.")
                validation_passed = False

            if validation_passed:
                # Check if student count column is numeric
                try:
                    df[student_count_col] = pd.to_numeric(
                        df[student_count_col], errors='coerce'
                    )
                except Exception as e:
                    st.error(
                        f"❌ Could not convert '{student_count_col}' "
                        f"to numeric values. Error: {e}"
                    )
                    validation_passed = False

            if validation_passed:
                # Data cleaning
                st.subheader("🧹 Data Cleaning Applied")

                # Strip whitespace from School Type column
                df[school_type_col] = (
                    df[school_type_col].astype(str).str.strip()
                )

                # Standardize Private Schools
                df[school_type_col] = df[school_type_col].replace(
                    ['PRVT', 'Prvt'],
                    'Private School (includes Montessori, Homeschool, etc)'
                )

                # Standardize Charter Schools
                df[school_type_col] = df[school_type_col].replace(
                    'Charter School',
                    'Charter'
                )

                st.success(
                    "✅ Whitespace trimmed and school types standardized "
                    "(PRVT/Prvt → Private School, Charter School → Charter)"
                )

                # Aggregate by School Type
                st.subheader("📊 Student Counts by School Type")

                result_df = (
                    df.groupby(school_type_col)[student_count_col]
                    .sum()
                    .reset_index()
                )
                result_df.columns = ['School Type', 'Total Students']
                result_df = result_df.sort_values(
                    'Total Students', ascending=False
                )

                # Display results
                st.dataframe(
                    result_df, use_container_width=True, hide_index=True
                )

                # Show total
                total_students = result_df['Total Students'].sum()
                st.metric(
                    "Total Students (All School Types)",
                    f"{total_students:,.0f}"
                )

                # Download button
                st.subheader("📥 Download Results")

                # Create Excel file in memory
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(
                        writer, index=False, sheet_name='Student Counts'
                    )
                output.seek(0)

                st.download_button(
                    label="📥 Download as Excel",
                    data=output,
                    file_name="student_counts_by_school_type.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    )
                )

    except ValueError as e:
        st.error(f"❌ Error reading sheet '{sheet_name}': {e}")
        st.info("💡 Please check that the sheet name is correct.")
    except Exception as e:
        st.error(f"❌ An error occurred: {e}")

else:
    st.info("👆 Please upload an Excel file to get started.")
