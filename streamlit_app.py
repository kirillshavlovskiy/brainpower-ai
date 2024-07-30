# filename: streamlit_script.py
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from sympy import symbols, lambdify
from sympy.parsing.sympy_parser import parse_expr
from mpl_toolkits.mplot3d import Axes3D

# Define the symbols used in the formula
x, y, z = symbols('x y z')

# Sidebar for input
st.sidebar.header("Input your formula and parameters")
formula_str = st.sidebar.text_area("Enter the formula (in terms of x, y, z):", value='x**2 + y**2')
min_range = st.sidebar.number_input("Enter the minimum value for x and y:", value=-10.0)
max_range = st.sidebar.number_input("Enter the maximum value for x and y:", value=10.0)
scale = st.sidebar.number_input("Enter the number of points to plot:", value=100, step=1, format='%d')

# Hints and examples
st.sidebar.info("Valid functions include operations and functions like +, -, *, /, sin, cos, exp, etc.")
st.sidebar.info("Example for 2D plot: x**2")
st.sidebar.info("Example for 3D plot: x**2 + y**2")

# Main area for plot and button
if st.button("Plott"):
    expr = parse_expr(formula_str)
    message = ""

if expr.has(x, y, z):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    x_vals = np.linspace(min_range, max_range, scale)
    y_vals = np.linspace(min_range, max_range, scale)
    x_vals, y_vals = np.meshgrid(x_vals, y_vals)
    z_vals = lambdify((x, y), expr, "numpy")
    ax.plot_surface(x_vals, y_vals, z_vals(x_vals, y_vals))
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')
elif expr.has(x, y):
    x_vals = np.linspace(min_range, max_range, scale)
    y_vals = lambdify(x, expr, "numpy")
    plt.plot(x_vals, y_vals(x_vals))
    plt.xlabel('x')
    plt.ylabel('y')
elif expr.has(x):
    x_vals = np.linspace(min_range, max_range, scale)
    y_vals = lambdify(x, expr, "numpy")
    plt.plot(x_vals, y_vals(x_vals))
    plt.xlabel('x')
    plt.ylabel('y')
else:
    message = "Invalid formula"
    st.error(message)

if message == "":
    st.pyplot(fig)