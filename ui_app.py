import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import base64

def log_normal_distribution(sample_size):
    mu, sigma = 0, 0.1
    s = np.random.lognormal(mu, sigma, sample_size)
    return s

user_input = st.sidebar.number_input("Enter sample size", min_value=10, max_value=10000, value=1000)
if st.sidebar.button('Generate Sample'):
    sample = log_normal_distribution(user_input)
    
    fig, ax = plt.subplots()
    ax.hist(sample, bins=50, color='skyblue', edgecolor='black')
    ax.set_xlabel('Value')
    ax.set_ylabel('Frequency')
    ax.set_title('Lognormal Distribution Sample')
    st.pyplot(fig)