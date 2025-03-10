#ocr imports
from pix2text import Pix2Text

#webbrowser
import webbrowser
import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    # Render an HTML file (make sure you have an 'index.html' file in the 'templates' folder)
    return render_template('desmos.html')

def plot_equation(equation):
    f = open('./templates/desmos.html', 'w') 
    html_template = f""" 
    <script src="https://www.desmos.com/api/v1.10/calculator.js?apiKey=dcb31709b452b1cf9dc26972add0fda6"></script>
    <div id="calculator" style="width: 600px; height: 400px;"></div>
        <script>
            var elt = document.getElementById('calculator');
            var calculator = Desmos.GraphingCalculator(elt);
            calculator.setExpression({{ id: 'line1', latex: '{equation}', color: '#ff0000' }});
        </script>
    """
    # writing the code into the file 
    f.write(html_template) 
  
    # close the file 
    f.close() 

def get_equation(path):
    p2t = Pix2Text.from_config()
    equation = p2t.recognize_formula(path)
    print(equation)
    return equation

def main():
    equation = get_equation("./input/yx.jpg")
    plot_equation(equation)


if __name__ == '__main__':
    main()
    app.run(debug=True)