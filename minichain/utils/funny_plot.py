"""
This module contains a function to create a funny plot that looks like a smiley face.
"""

import matplotlib.pyplot as plt
import numpy as np

def create_funny_plot():
    """
    This function creates a funny plot that looks like a smiley face.
    """
    # Create a figure and a set of subplots
    _, axes = plt.subplots()

    # Create a range of values from -10 to 10 (1000 points)
    x_values = np.linspace(-10, 10, 1000)

    # Create a function for a smile (a simple parabola)
    y_values = -x_values**2 + 100

    # Plot the smile
    axes.plot(x_values, y_values)

    # Create a function for the left eye (a circle)
    x_left_eye = np.linspace(-7, -3, 100)
    y_left_eye = (3-np.sqrt(9-(x_left_eye+5)**2))+50

    # Plot the left eye
    axes.plot(x_left_eye, y_left_eye, 'o')

    # Create a function for the right eye (a circle)
    x_right_eye = np.linspace(3, 7, 100)
    y_right_eye = (3-np.sqrt(9-(x_right_eye-5)**2))+50

    # Plot the right eye
    axes.plot(x_right_eye, y_right_eye, 'o')

    # Display the plot
    plt.show()
    axes.plot(x_values, y_values)

    # Create a function for the left eye (a circle)
    x_left_eye = np.linspace(-7, -3, 100)
    y_left_eye = (3-np.sqrt(9-(x_left_eye+5)**2))+50

    # Plot the left eye
    axes.plot(x_left_eye, y_left_eye, 'o')

    # Create a function for the right eye (a circle)
    x_right_eye = np.linspace(3, 7, 100)
    y_right_eye = (3-np.sqrt(9-(x_right_eye-5)**2))+50

    # Plot the right eye
    axes.plot(x_right_eye, y_right_eye, 'o')

    # Display the plot
    plt.show()
    axes.plot(x_values, y_values)

    # Create a function for the left eye (a circle)
    x_left_eye = np.linspace(-7, -3, 100)
    y_left_eye = (3-np.sqrt(9-(x_left_eye+5)**2))+50

    # Plot the left eye
    axes.plot(x_left_eye, y_left_eye, 'o')

    # Create a function for the right eye (a circle)
    x_right_eye = np.linspace(3, 7, 100)
    y_right_eye = (3-np.sqrt(9-(x_right_eye-5)**2))+50

    # Plot the right eye
    axes.plot(x_right_eye, y_right_eye, 'o')

    # Display the plot
    plt.show()
    ax.plot(x_values, y_values)

    # Create a function for the left eye (a circle)
    x_left_eye = np.linspace(-7, -3, 100)
    y_left_eye = (3-np.sqrt(9-(x_left_eye+5)**2))+50

    # Plot the left eye
    ax.plot(x_left_eye, y_left_eye, 'o')

    # Create a function for the right eye (a circle)
    x_right_eye = np.linspace(3, 7, 100)
    y_right_eye = (3-np.sqrt(9-(x_right_eye-5)**2))+50

    # Plot the right eye
    ax.plot(x_right_eye, y_right_eye, 'o')

    # Display the plot
    plt.show()
    ax.plot(x_left_eye, y_left_eye, 'o')

    # Create a function for the right eye (a circle)
    x_right_eye = np.linspace(3, 7, 100)
    y_right_eye = (3-np.sqrt(9-(x_right_eye-5)**2))+50

    # Plot the right eye
    ax.plot(x_right_eye, y_right_eye, 'o')

    # Display the plot
    plt.show()
