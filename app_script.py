import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import os


def shape_function(x, y):
    return x**2 - y**2 -100


xmin = -100
xmax = 100
ymin = -100
ymax = 100

x = np.linspace(xmin, xmax, 400)
y = np.linspace(ymin, ymax, 400)
x, y = np.meshgrid(x, y)

z = shape_function(x, y)

fig = go.Figure(data=[go.Surface(x=x, y=y, z=z, colorscale='viridis')])
fig.update_layout(title='Shape Function Plot', scene=dict(
                    xaxis_title='X Axis',
                    yaxis_title='Y Axis',
                    zaxis_title='Z Axis'))
