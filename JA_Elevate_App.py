import streamlit as st
import pandas as pd
from io import BytesIO
import re


def is_zip_code(series):
    """Check if a column contains ZIP codes (5-digit or 9-digit format)."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    zip_pattern = re.compile(r'^\d{5}(-\d{4})?$')
    matches = sample.apply(lambda x: bool(zip_pattern.match(x.strip())))
    return matches.mean() > 0.5


def is_id_format(series):
    """Check if a column contains IDs in X-XXXXXXXX format."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    id_pattern = re.compile(r'^\d-\d{8}$')
    matches = sample.apply(lambda x: bool(id_pattern.match(x.strip())))
    return matches.mean() > 0.5


def is_phone_number(series):
    """Check if a column contains phone numbers."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    # Match various phone formats: 555-123-4567, (555) 123-4567, 5551234567
    phone_pattern = re.compile(r'^[\(]?\d{3}[\)\-\.\s]?\d{3}[\-\.\s]?\d{4}$')
    matches = sample.apply(lambda x: bool(phone_pattern.match(x.strip())))
    return matches.mean() > 0.5


def is_date_column(series):
    """Check if a column contains date/datetime values."""
    # Check if already datetime dtype
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    # Skip columns that are purely numeric (int/float) - these are NOT dates
    if pd.api.types.is_numeric_dtype(series):
        return False

    # Try to parse as dates only for object/string columns
    sample = series.dropna().head(100)
    if len(sample) == 0:
        return False

    # Convert to string for pattern matching
    sample_str = sample.astype(str)
    
    # Check if values look like dates (contain separators like /, -, or month names)
    # This prevents plain numbers from being interpreted as dates
    date_pattern = re.compile(
        r'(\d{1,4}[-/]\d{1,2}[-/]\d{1,4})|'  # Date with separators: 2024-01-15, 01/15/2024
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|'  # Short year formats
        r'([A-Za-z]{3,9}[\s,.-]+\d{1,2}[\s,.-]+\d{2,4})|'  # Jan 15, 2024
        r'(\d{1,2}[\s,.-]+[A-Za-z]{3,9}[\s,.-]+\d{2,4})'   # 15 Jan 2024
    )
    
    looks_like_date = sample_str.apply(lambda x: bool(date_pattern.search(str(x).strip())))
    
    # Require at least 50% to look like actual date strings
    if looks_like_date.mean() < 0.5:
        return False

    try:
        converted = pd.to_datetime(sample, errors='coerce')
        success_rate = converted.notna().sum() / len(sample)
        return success_rate > 0.5
    except Exception:
        return False


def detect_excluded_columns(df):
    """Detect columns that look numeric but should be excluded."""
    excluded = {}
    for col in df.columns:
        if is_id_format(df[col]):
            excluded[col] = 'ID'
        elif is_zip_code(df[col]):
            excluded[col] = 'ZIP Code'
        elif is_phone_number(df[col]):
            excluded[col] = 'Phone Number'
        elif is_date_column(df[col]):
            excluded[col] = 'Date'
    return excluded


def clean_for_numeric(series):
    """Clean common formatting before numeric conversion."""
    if series.dtype == 'object':
        cleaned = (
            series.astype(str)
            .str.strip()
            .str.replace(r'[\$,€%]', '', regex=True)
            .str.replace(r'^\s*$', 'NaN', regex=True)
        )
        return pd.to_numeric(cleaned, errors='coerce')
    return pd.to_numeric(series, errors='coerce')


def convert_numeric_columns(df, excluded_cols, force_include, force_exclude):
    """
    Dynamically convert columns to numeric where appropriate.
    
    Args:
        df: DataFrame to process
        excluded_cols: Dict of auto-excluded columns {col: reason}
        force_include: List of columns to force as numeric
        force_exclude: List of columns to force as non-numeric
    
    Returns:
        Tuple of (processed_df, auto_numeric_cols, final_excluded)
    """
    auto_numeric = []
    final_excluded = {}
    
    for col in df.columns:
        # Skip if force excluded
        if col in force_exclude:
            df[col] = df[col].astype(str)
            continue
        
        # Force include overrides auto-exclusion
        if col in force_include:
            df[col] = clean_for_numeric(df[col])
            auto_numeric.append(col)
            continue
        
        # Check if auto-excluded
        if col in excluded_cols:
            df[col] = df[col].astype(str)
            final_excluded[col] = excluded_cols[col]
            continue
        
        # Try numeric conversion
        converted = clean_for_numeric(df[col])
        non_null_count = len(df[col].dropna())
        
        if non_null_count > 0:
            success_rate = converted.notna().sum() / non_null_count
            if success_rate > 0.5:
                df[col] = converted
                auto_numeric.append(col)
            else:
                df[col] = df[col].astype(str)
        else:
            df[col] = df[col].astype(str)
    
    return df, auto_numeric, final_excluded


# Page configuration
st.set_page_config(
    page_title="CDP - Student Counts & Aggregations",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CDP - Student Counts & Aggregations")
st.markdown(
    "Upload an Excel file to get student counts aggregated by Group By Column."
)

# File uploader
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

# Initialize session state for tracking file changes and overrides
if 'last_file_name' not in st.session_state:
    st.session_state.last_file_name = None
if 'force_include' not in st.session_state:
    st.session_state.force_include = []
if 'force_exclude' not in st.session_state:
    st.session_state.force_exclude = []

# Reset overrides when a new file is uploaded
if uploaded_file is not None:
    if st.session_state.last_file_name != uploaded_file.name:
        st.session_state.last_file_name = uploaded_file.name
        st.session_state.force_include = []
        st.session_state.force_exclude = []

if uploaded_file is not None:
    # Get available sheet names from the Excel file
    excel_file = pd.ExcelFile(uploaded_file)
    sheet_names = excel_file.sheet_names
    
    # Configuration section
    st.subheader("⚙️ Configuration")
    col1, col2 = st.columns(2)

    with col1:
        # Find default index for "School Info" if it exists
        default_sheet_idx = 0
        for i, name in enumerate(sheet_names):
            if name.lower() == "school info":
                default_sheet_idx = i
                break
        sheet_name = st.selectbox(
            "Select Sheet",
            options=sheet_names,
            index=default_sheet_idx
        )
    with col2:
        rows_to_skip = st.number_input(
            "Header Rows to Skip",
            min_value=0,
            max_value=10,
            value=2
        )

    # Load the data
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Skip header rows if specified
        if rows_to_skip > 0:
            df = df.iloc[rows_to_skip:].reset_index(drop=True)

        # Detect columns that should be excluded (IDs, ZIPs, phones)
        excluded_cols = detect_excluded_columns(df)

        # Get available columns for override selection
        all_columns = df.columns.tolist()
        excluded_col_names = list(excluded_cols.keys())
        potential_text_cols = [
            c for c in all_columns if c not in excluded_col_names
        ]

        # Manual override controls
        st.subheader("🎛️ Column Type Overrides")
        st.caption(
            "Override auto-detection if needed. Force include columns "
            "that should be numeric, or force exclude columns that shouldn't."
        )

        override_col1, override_col2 = st.columns(2)

        with override_col1:
            available_for_include = (
                excluded_col_names +
                [c for c in all_columns if c not in excluded_col_names]
            )
            force_include = st.multiselect(
                "Force Include as Numeric",
                options=available_for_include,
                default=st.session_state.force_include,
                help="Force-treat as numeric (overrides auto-exclusion)",
                key="force_include_select"
            )
            st.session_state.force_include = force_include

        with override_col2:
            force_exclude = st.multiselect(
                "Force Exclude from Numeric",
                options=all_columns,
                default=st.session_state.force_exclude,
                help="Force-treat as text (won't be for aggregation)",
                key="force_exclude_select"
            )
            st.session_state.force_exclude = force_exclude

        # Convert column types dynamically
        df, auto_numeric_cols, final_excluded = convert_numeric_columns(
            df, excluded_cols, force_include, force_exclude
        )

        # Display auto-detection feedback
        st.subheader("🔍 Auto-Detected Column Types")

        feedback_col1, feedback_col2 = st.columns(2)

        with feedback_col1:
            if auto_numeric_cols:
                count = len(auto_numeric_cols)
                st.success(
                    f"**Numeric columns detected ({count}):**\n\n" +
                    "\n".join([f"• {col}" for col in auto_numeric_cols])
                )
            else:
                st.warning("No numeric columns were auto-detected.")

        with feedback_col2:
            if final_excluded:
                excluded_msg = "**Auto-excluded columns:**\n\n"
                for col, reason in final_excluded.items():
                    excluded_msg += f"• {col} ({reason})\n"
                st.info(excluded_msg)
            else:
                st.info("No columns were auto-excluded.")

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

                # Fill missing values instead of removing rows
                # This helps identify data that needs to be filled in the source Excel
                # Handle both actual NaN and string "nan" (from earlier string conversion)
                categorical_missing = (
                    df[school_type_col].isna().sum() + 
                    df[school_type_col].astype(str).str.lower().str.strip().isin(['nan', '']).sum()
                )
                numeric_missing = df[student_count_col].isna().sum()
                
                # Fill categorical column: handle actual NaN, string "nan", and empty strings
                df[school_type_col] = df[school_type_col].fillna("Empty")
                df[school_type_col] = df[school_type_col].astype(str).str.strip()
                df[school_type_col] = df[school_type_col].replace(
                    ['nan', 'NaN', 'NAN', ''], 'Empty'
                )
                
                # Fill numeric column with 0
                df[student_count_col] = df[student_count_col].fillna(0)
                
                if categorical_missing > 0 or numeric_missing > 0:
                    st.warning(
                        f"⚠️ Found missing data: {categorical_missing} empty values in "
                        f"'{school_type_col}' (filled with 'Empty'), "
                        f"{numeric_missing} empty values in '{student_count_col}' (filled with 0). "
                        f"Consider updating the source Excel file."
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
                result_df.columns = [school_type_col, f'Total {student_count_col}']
                result_df = result_df.sort_values(
                    f'Total {student_count_col}', ascending=False
                )

                # Display results
                st.dataframe(
                    result_df, use_container_width=True, hide_index=True
                )

                # Show total
                total_col_name = f'Total {student_count_col}'
                total_students = result_df[total_col_name].sum()
                st.metric(
                    f"Total {student_count_col} (All {school_type_col})",
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
                    file_name="Results.xlsx",
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
