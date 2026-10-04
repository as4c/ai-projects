import streamlit as st
import pandas as pd

st.title("My First Streamlit App")

# Text input
name = st.text_input("Enter your name")
st.write(f"Hello, {name}!")

# Slider
age = st.slider("Select your age", 0, 100, 25)

# Selectbox
option = st.selectbox("Pick a color", ["Red", "Green", "Blue"])

# Display data
df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
st.dataframe(df)

# Charts
st.line_chart(df)

# Button
if st.button("Click me"):
    st.balloons()
