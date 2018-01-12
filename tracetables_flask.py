# coding=utf-8
from flask import Flask, render_template, request
import backend

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def main(name="Rahul"):
    code = request.form["code"] if request.method == 'POST' else ""
    print(code)
    print(backend.main(code)[1].print_trace_table())
    return render_template('index.html', name=name, code=code, table=backend.main(code)[1].print_trace_table())


if __name__ == '__main__':
    app.run()
