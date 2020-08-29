from flask import Flask

app = Flask(__name__)


@app.route("/environment")
def env_endpoint():
    return "TODO :)"


if __name__ == "__main__":
    app.run()
